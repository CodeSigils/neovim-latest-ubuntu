"""Tests for build metadata and release-candidate binding."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WRITER = REPO / "scripts/write-build-metadata.py"
VERIFIER = REPO / "scripts/verify-release-candidate.py"
SOURCE_COMMIT = "a" * 40
REPOSITORY_COMMIT = "b" * 40
IMAGE_DIGEST = "c" * 64


class ReleaseCandidateTests(unittest.TestCase):
    def write_metadata(
        self, directory: Path, architecture: str, artifact_name: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(WRITER),
                "--artifact",
                artifact_name,
                "--architecture",
                architecture,
                "--source-version",
                "1.2.3",
                "--source-commit",
                SOURCE_COMMIT,
                "--package-version",
                "1.2.3",
                "--ubuntu-version",
                "26.04",
                "--ubuntu-codename",
                "Resolute Raccoon",
                "--ubuntu-image-digest",
                IMAGE_DIGEST,
                "--repository-commit",
                REPOSITORY_COMMIT,
                "--output",
                f"BUILD-METADATA-{architecture}.json",
            ],
            cwd=directory,
            text=True,
            capture_output=True,
            check=False,
        )

    def verify(self, directory: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(VERIFIER),
                "--directory",
                str(directory),
                "--version",
                "1.2.3",
                "--source-commit",
                SOURCE_COMMIT,
                "--repository-commit",
                REPOSITORY_COMMIT,
                "--ubuntu-version",
                "26.04",
                "--ubuntu-codename",
                "Resolute Raccoon",
                "--ubuntu-image-digest",
                IMAGE_DIGEST,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def make_candidate(self, directory: Path) -> None:
        for architecture, artifact_name in (
            ("amd64", "nvim-linux-x86_64.deb"),
            ("arm64", "nvim-linux-arm64.deb"),
        ):
            (directory / artifact_name).write_bytes(f"package-{architecture}".encode())
            result = self.write_metadata(directory, architecture, artifact_name)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_coherent_candidate_writes_combined_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.make_candidate(directory)
            result = self.verify(directory)
            checksums = (directory / "SHA256SUMS").read_text().splitlines()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(checksums), 2)
        self.assertTrue(checksums[0].endswith("  nvim-linux-x86_64.deb"))
        self.assertTrue(checksums[1].endswith("  nvim-linux-arm64.deb"))

    def test_tampered_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.make_candidate(directory)
            (directory / "nvim-linux-arm64.deb").write_bytes(b"tampered")
            result = self.verify(directory)

        self.assertEqual(result.returncode, 1)
        self.assertIn("metadata does not match candidate inputs", result.stderr)

    def test_nightly_metadata_records_master_ref_and_exact_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            artifact = directory / "nvim-linux-x86_64.deb"
            artifact.write_bytes(b"nightly")
            command = [
                "python3",
                str(WRITER),
                "--artifact",
                artifact.name,
                "--architecture",
                "amd64",
                "--source-version",
                "nightly",
                "--source-commit",
                SOURCE_COMMIT,
                "--package-version",
                "0.14.0~dev-1",
                "--ubuntu-version",
                "26.04",
                "--ubuntu-codename",
                "Resolute Raccoon",
                "--ubuntu-image-digest",
                IMAGE_DIGEST,
                "--repository-commit",
                REPOSITORY_COMMIT,
                "--output",
                "metadata.json",
            ]
            result = subprocess.run(
                command,
                cwd=directory,
                text=True,
                capture_output=True,
                check=False,
            )
            metadata = json.loads((directory / "metadata.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(metadata["upstream"]["ref"], "refs/heads/master")
        self.assertEqual(metadata["upstream"]["commit"], SOURCE_COMMIT)
        self.assertEqual(metadata["package_version"], "0.14.0~dev-1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
