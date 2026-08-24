"""Integration tests for the Lintian regression allowlist."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECKER = REPO / "scripts/check-lintian.sh"


class LintianGateTests(unittest.TestCase):
    def run_gate(self, output: str, allowlist: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake = root / "lintian"
            fake.write_text(f"#!/usr/bin/env bash\necho {output!r}\nexit 2\n")
            fake.chmod(0o755)
            deb = root / "package.deb"
            deb.touch()
            allowed = root / "allowlist.txt"
            allowed.write_text(allowlist)
            return subprocess.run(
                ["bash", str(CHECKER), str(deb), str(allowed)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=os.environ | {"PATH": f"{root}:{os.environ['PATH']}"},
                check=False,
            )

    def test_reviewed_finding_is_allowed(self) -> None:
        result = self.run_gate("E: neovim: known-finding", "known-finding\n")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("reviewed compatibility-package baseline", result.stdout)

    def test_new_finding_blocks_release(self) -> None:
        result = self.run_gate("E: neovim: new-finding", "known-finding\n")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("New lintian findings", result.stdout)

    def test_operational_failure_cannot_be_mistaken_for_a_clean_report(self) -> None:
        result = self.run_gate("lintian: package could not be read", "known-finding\n")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("failed without reporting a parseable", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
