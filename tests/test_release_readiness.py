#!/usr/bin/env python3
"""Tests for scripts/check-release-readiness.sh."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "check-release-readiness.sh"


def run(cmd: list[str] | str, cwd: Path, **kwargs) -> subprocess.CompletedProcess[str]:
    """Execute a command in a given working directory and return the result."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=isinstance(cmd, str),
        **kwargs,
    )


def write_executable(path: Path, content: str) -> None:
    """Write a file with executable permissions set."""
    path.write_text(textwrap.dedent(content).lstrip())
    path.chmod(0o755)


class ReleaseReadinessTests(unittest.TestCase):
    """Integration tests for the release readiness gate script."""

    def make_repo(self, tmp_path: Path, *, version: str = "1.2.3") -> Path:
        """Create a throwaway git repo mimicking the project layout."""
        work = tmp_path / "work"
        remote = tmp_path / "origin.git"
        work.mkdir()
        run("git init --bare origin.git", tmp_path, check=True)
        run("git init -b main", work, check=True)
        run("git config user.name CodeSigils", work, check=True)
        run("git config user.email toolsoftrade.web@gmail.com", work, check=True)

        (work / "scripts").mkdir()
        write_executable(
            work / "build.sh",
            f"""
            #!/usr/bin/env bash
            VERSION="${{1:-${{VERSION:-{version}}}}}"
            echo "$VERSION" >/dev/null
            """,
        )
        write_executable(work / "test.sh", "#!/usr/bin/env bash\ntrue\n")
        write_executable(work / "scripts" / "check-dependencies.py", "#!/usr/bin/env python3\nprint('deps ok')\n")
        write_executable(work / "scripts" / "check-yaml-syntax.py", "#!/usr/bin/env python3\nprint('yaml ok')\n")
        shutil.copy2(SCRIPT, work / "scripts" / "check-release-readiness.sh")

        run("git add .", work, check=True)
        run("git commit -m init", work, check=True)
        run(f"git remote add origin {remote}", work, check=True)
        run("git push -u origin main", work, check=True)
        return work

    def make_fake_bin(self, tmp_path: Path, *, upstream: str = "v1.2.3", release_exists: bool = False) -> Path:
        """Create mock curl/gh binaries that return controlled test responses."""
        fake = tmp_path / "bin"
        fake.mkdir()
        write_executable(
            fake / "curl",
            f"""
            #!/usr/bin/env bash
            printf '{{"tag_name":"{upstream}","html_url":"https://example.test/{upstream}"}}\\n'
            """,
        )
        release_view_exit = "exit 0" if release_exists else "exit 1"
        write_executable(
            fake / "gh",
            f"""
            #!/usr/bin/env bash
            set -euo pipefail
            case "${{1:-}} ${{2:-}}" in
              "auth status") exit 0 ;;
              # Mock fixture — values are placeholders, not assertions.
            # The script only checks that these variables EXIST, not their values.
            "variable list") printf 'UBUNTU_VERSION\\t26.04\\nUBUNTU_CODENAME\\tResolute Raccoon\\n'; exit 0 ;;
              "release view") {release_view_exit} ;;
              *) printf 'unexpected gh call: %s\\n' "$*" >&2; exit 1 ;;
            esac
            """,
        )
        return fake

    def test_script_requires_version(self) -> None:
        """The script should fail with a usage message when no version is given."""
        result = run(["bash", str(SCRIPT)], REPO)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)

    def test_existing_local_tag_blocks_release(self) -> None:
        """If the tag already exists locally, the gate should refuse to proceed."""
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            repo = self.make_repo(tmp_path)
            fake = self.make_fake_bin(tmp_path)
            run("git tag v1.2.3", repo, check=True)
            env = os.environ | {"PATH": f"{fake}:{os.environ['PATH']}"}

            result = run(["bash", "scripts/check-release-readiness.sh", "1.2.3"], repo, env=env)

        self.assertEqual(result.returncode, 1)
        self.assertIn("NOT READY", result.stdout)
        self.assertIn("Local tag already exists: v1.2.3", result.stdout)

    def test_ready_when_policy_checks_pass(self) -> None:
        """When all policy checks pass, the gate should report READY."""
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            repo = self.make_repo(tmp_path)
            fake = self.make_fake_bin(tmp_path)
            env = os.environ | {"PATH": f"{fake}:{os.environ['PATH']}"}

            result = run(["bash", "scripts/check-release-readiness.sh", "1.2.3"], repo, env=env)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("READY: safe to publish v1.2.3", result.stdout)
        self.assertIn("git tag v1.2.3", result.stdout)
        self.assertIn("git push origin v1.2.3", result.stdout)

    def test_package_revision_suffix_accepted(self) -> None:
        """Tags with a -N revision suffix should be accepted as valid versions."""
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            repo = self.make_repo(tmp_path, version="1.2.3")
            fake = self.make_fake_bin(tmp_path, upstream="v1.2.3")
            env = os.environ | {"PATH": f"{fake}:{os.environ['PATH']}"}

            result = run(
                ["bash", "scripts/check-release-readiness.sh", "1.2.3-1"], repo, env=env
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("READY: safe to publish v1.2.3-1", result.stdout)
        self.assertIn("git tag v1.2.3-1", result.stdout)
        self.assertIn("git push origin v1.2.3-1", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
