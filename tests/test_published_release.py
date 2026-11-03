from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "published", REPO / "scripts/verify-published-release.py"
)
assert SPEC and SPEC.loader
published = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(published)


class PublishedReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.commit = "a" * 40
        expected = published.release_metadata.REQUIRED_RELEASE_ASSETS
        for name in expected - {"SHA256SUMS"}:
            (self.directory / name).write_text(f"{name}\n")
        sums = []
        for name in ("nvim-linux-x86_64.deb", "nvim-linux-arm64.deb"):
            digest = hashlib.sha256((self.directory / name).read_bytes()).hexdigest()
            sums.append(f"{digest}  {name}")
        (self.directory / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        self.release = {
            "tag_name": "v1.2.3",
            "draft": False,
            "immutable": True,
            "prerelease": False,
            "target_commitish": self.commit,
            "assets": [{"name": name, "state": "uploaded", "size": 1} for name in expected],
        }
        self.tag = {"object": {"type": "commit", "sha": self.commit}}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _verify(self, *, release: dict | None = None, tag: dict | None = None) -> None:
        published.verify(
            release=self.release if release is None else release,
            tag=self.tag if tag is None else tag,
            asset_dir=self.directory,
            expected_tag="v1.2.3",
            expected_commit=self.commit,
        )

    def test_valid_public_release(self) -> None:
        self._verify()

    def test_rejects_draft_or_prerelease_release(self) -> None:
        for field in ("draft", "prerelease"):
            with self.subTest(field=field):
                release = {**self.release, field: True}
                with self.assertRaisesRegex(ValueError, "draft or prerelease"):
                    self._verify(release=release)

    def test_rejects_mutable_release(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not confirm"):
            self._verify(release={**self.release, "immutable": False})

    def test_rejects_release_without_immutable_confirmation(self) -> None:
        release = dict(self.release)
        del release["immutable"]

        with self.assertRaisesRegex(ValueError, "does not confirm"):
            self._verify(release=release)

    def test_rejects_incomplete_remote_asset(self) -> None:
        for field, value in (("state", "new"), ("size", 0), ("size", True)):
            with self.subTest(field=field):
                assets = [dict(item) for item in self.release["assets"]]
                assets[0][field] = value
                with self.assertRaisesRegex(ValueError, "incomplete or empty asset"):
                    self._verify(release={**self.release, "assets": assets})

    def test_rejects_extra_remote_asset(self) -> None:
        self.release["assets"].append({"name": "unexpected.txt", "state": "uploaded", "size": 1})
        with self.assertRaisesRegex(ValueError, "unexpected release assets"):
            self._verify()

    def test_rejects_duplicate_remote_asset(self) -> None:
        release = {
            **self.release,
            "assets": [*self.release["assets"], self.release["assets"][0]],
        }

        with self.assertRaisesRegex(ValueError, "duplicate assets"):
            self._verify(release=release)

    def test_rejects_malformed_remote_asset(self) -> None:
        release = {**self.release, "assets": [*self.release["assets"], None]}

        with self.assertRaisesRegex(ValueError, "invalid asset entry"):
            self._verify(release=release)

    def test_rejects_tag_drift(self) -> None:
        self.tag["object"]["sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "tag does not resolve"):
            self._verify()

    def test_rejects_non_commit_tag(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not resolve directly"):
            self._verify(tag={"object": {"type": "tag", "sha": self.commit}})

    def test_rejects_malformed_tag_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not resolve directly"):
            self._verify(tag={"object": None})

    def test_rejects_invalid_checksum_line(self) -> None:
        (self.directory / "SHA256SUMS").write_text("not a checksum\n")

        with self.assertRaisesRegex(ValueError, "invalid checksum line"):
            self._verify()

    def test_rejects_checksum_mismatch(self) -> None:
        (self.directory / "nvim-linux-x86_64.deb").write_text("changed\n")

        with self.assertRaisesRegex(ValueError, "checksum mismatch for nvim-linux-x86_64.deb"):
            self._verify()

    def test_rejects_incomplete_checksum_coverage(self) -> None:
        checksum = (self.directory / "SHA256SUMS").read_text().splitlines()[0]
        (self.directory / "SHA256SUMS").write_text(f"{checksum}\n")

        with self.assertRaisesRegex(ValueError, "does not cover both packages"):
            self._verify()

    def test_rejects_checksum_entry_outside_package_set(self) -> None:
        checksums = (self.directory / "SHA256SUMS").read_text()
        (self.directory / "SHA256SUMS").write_text(
            f"{checksums}{'0' * 64}  nvim-linux-riscv64.deb\n"
        )

        with self.assertRaisesRegex(ValueError, "invalid checksum entry"):
            self._verify()

    def test_rejects_duplicate_checksum_entry(self) -> None:
        checksums = (self.directory / "SHA256SUMS").read_text()
        checksum = checksums.splitlines()[0]
        (self.directory / "SHA256SUMS").write_text(f"{checksums}{checksum}\n")

        with self.assertRaisesRegex(ValueError, "invalid checksum entry"):
            self._verify()

    def test_rejects_downloaded_asset_set_drift(self) -> None:
        (self.directory / "unexpected.txt").write_text("unexpected\n")

        with self.assertRaisesRegex(ValueError, "downloaded asset set differs"):
            self._verify()

    def test_cli_fixtures_are_json_objects(self) -> None:
        path = self.directory / "release.json"
        path.write_text(json.dumps(self.release))
        self.assertEqual(published.read_json(path)["tag_name"], "v1.2.3")


if __name__ == "__main__":
    unittest.main()
