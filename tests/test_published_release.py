from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "published", REPO / "scripts/verify-published-release.py"
)
published = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(published)


class PublishedReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.commit = "a" * 40
        for name in published.EXPECTED_ASSETS - {"SHA256SUMS"}:
            (self.directory / name).write_text(f"{name}\n")
        sums = []
        for name in ("nvim-linux-x86_64.deb", "nvim-linux-arm64.deb"):
            digest = hashlib.sha256((self.directory / name).read_bytes()).hexdigest()
            sums.append(f"{digest}  {name}")
        (self.directory / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        self.release = {
            "tag_name": "v1.2.3",
            "draft": False,
            "prerelease": False,
            "target_commitish": self.commit,
            "assets": [
                {"name": name, "state": "uploaded", "size": 1} for name in published.EXPECTED_ASSETS
            ],
        }
        self.tag = {"object": {"type": "commit", "sha": self.commit}}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_valid_public_release(self) -> None:
        published.verify(
            release=self.release,
            tag=self.tag,
            asset_dir=self.directory,
            expected_tag="v1.2.3",
            expected_commit=self.commit,
        )

    def test_rejects_extra_remote_asset(self) -> None:
        self.release["assets"].append({"name": "unexpected.txt", "state": "uploaded", "size": 1})
        with self.assertRaisesRegex(ValueError, "unexpected release assets"):
            published.verify(
                release=self.release,
                tag=self.tag,
                asset_dir=self.directory,
                expected_tag="v1.2.3",
                expected_commit=self.commit,
            )

    def test_rejects_tag_drift_and_checksum_mismatch(self) -> None:
        self.tag["object"]["sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "tag does not resolve"):
            published.verify(
                release=self.release,
                tag=self.tag,
                asset_dir=self.directory,
                expected_tag="v1.2.3",
                expected_commit=self.commit,
            )

    def test_cli_fixtures_are_json_objects(self) -> None:
        path = self.directory / "release.json"
        path.write_text(json.dumps(self.release))
        self.assertEqual(published.read_json(path)["tag_name"], "v1.2.3")


if __name__ == "__main__":
    unittest.main()
