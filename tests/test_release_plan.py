"""Unit tests for the automated stable-release planner."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("release_plan", REPO / "scripts/plan-release.py")
assert SPEC and SPEC.loader
release_plan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_plan
SPEC.loader.exec_module(release_plan)


class FakeGitHub:
    def __init__(self, *, latest: str = "v0.12.5", existing: bool = False) -> None:
        self.latest = latest
        self.existing = existing

    def get(self, path: str) -> dict:
        if path.endswith("releases/latest"):
            return {"tag_name": self.latest}
        if "/git/ref/tags/" in path:
            return {"object": {"type": "tag", "sha": "a" * 40}}
        if "/git/tags/" in path:
            return {"object": {"type": "commit", "sha": "b" * 40}}
        raise AssertionError(f"unexpected API request: {path}")

    def optional(self, path: str) -> dict | None:
        if path.startswith("repos/neovim/neovim/releases/tags/"):
            return {"draft": False, "prerelease": False}
        if self.existing:
            return {
                "draft": False,
                "assets": [
                    {"name": name, "size": 1, "state": "uploaded"}
                    for name in release_plan.CORE_ASSETS
                ],
            }
        return None


class ReleasePlanTests(unittest.TestCase):
    def test_package_revision_is_separate_from_upstream_version(self) -> None:
        version = release_plan.parse_version("v0.12.5-2")
        self.assertEqual(version.base, "0.12.5")
        self.assertEqual(version.tag, "v0.12.5-2")
        self.assertEqual(version.package_revision, "2")

    def test_invalid_or_prerelease_version_is_rejected(self) -> None:
        for value in ("nightly", "0.12", "0.12.5-rc1", "v0.12.5-0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release_plan.parse_version(value)

    def test_new_maintenance_release_builds_and_auto_publishes(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(),
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertTrue(plan.should_build)
        self.assertTrue(plan.publish)
        self.assertFalse(plan.requires_review)
        self.assertEqual(plan.source_commit, "b" * 40)

    def test_feature_release_requires_environment_review(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(latest="v0.13.0"),
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertTrue(plan.requires_review)

    def test_existing_complete_release_skips_expensive_build(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(existing=True),
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertFalse(plan.should_build)
        self.assertIn("already published", plan.reason)

    def test_empty_or_incomplete_assets_do_not_suppress_a_rebuild(self) -> None:
        client = FakeGitHub(existing=True)
        original_optional = client.optional

        def incomplete(path: str) -> dict | None:
            result = original_optional(path)
            if result and path.startswith("repos/CodeSigils/"):
                result["assets"][0]["size"] = 0
            return result

        client.optional = incomplete  # type: ignore[method-assign]
        plan = release_plan.make_plan(
            client=client,
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertTrue(plan.should_build)

    def test_ci_build_never_publishes(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(),
            mode="ci",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertTrue(plan.should_build)
        self.assertFalse(plan.publish)


if __name__ == "__main__":
    unittest.main(verbosity=2)
