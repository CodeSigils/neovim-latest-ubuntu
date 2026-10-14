"""Unit tests for the automated stable-release planner."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("release_plan", REPO / "scripts/plan-release.py")
assert SPEC and SPEC.loader
release_plan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_plan
SPEC.loader.exec_module(release_plan)


@dataclass
class FakeGitHub:
    latest: str = "v0.12.5"
    existing: bool = False
    existing_assets: set[str] | None = None
    baseline_commit: str = "c" * 40
    changed_files: list[str] | None = None
    invalid_metadata: bool = False
    metadata_available: bool = True
    tag_requests: list[str] = field(default_factory=list)

    def get(self, path: str) -> dict:
        if path == "repos/neovim/neovim/releases/latest":
            return {"tag_name": self.latest}
        if "/git/ref/tags/" in path:
            self.tag_requests.append(path)
            return {"object": {"type": "tag", "sha": "a" * 40}}
        if "/git/tags/" in path:
            return {"object": {"type": "commit", "sha": "b" * 40}}
        if path.endswith("releases/latest"):
            return {
                "tag_name": "v0.12.5",
                "assets": (
                    [{"name": "BUILD-METADATA-amd64.json", "id": 1}]
                    if self.metadata_available
                    else []
                ),
            }
        if "/compare/" in path:
            return {"files": [{"filename": name} for name in self.changed_files or []]}
        raise AssertionError(f"unexpected API request: {path}")

    def text(self, path: str) -> str:
        if path.endswith("releases/assets/1"):
            if self.invalid_metadata:
                return "not json"
            return '{"upstream": {"commit": "' + self.baseline_commit + '"}}'
        raise AssertionError(f"unexpected asset request: {path}")

    def optional(self, path: str) -> dict | None:
        if path.startswith("repos/neovim/neovim/releases/tags/"):
            return {"draft": False, "prerelease": False}
        if self.existing:
            assets = (
                self.existing_assets
                if self.existing_assets is not None
                else release_plan.LEGACY_RELEASE_ASSETS.get(
                    self.latest, release_plan.REQUIRED_ASSETS
                )
            )
            return {
                "draft": False,
                "assets": [{"name": name, "size": 1, "state": "uploaded"} for name in assets],
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

    def test_low_risk_feature_release_auto_publishes(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(latest="v0.13.0"),
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertFalse(plan.requires_review)

    def test_packaging_critical_upstream_change_requires_review(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(latest="v0.13.0", changed_files=["cmake/Install.cmake"]),
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertTrue(plan.requires_review)
        self.assertIn("cmake/Install.cmake", plan.reason)

    def test_unavailable_risk_comparison_requires_review(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(invalid_metadata=True),
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertTrue(plan.requires_review)
        self.assertIn("unable to classify", plan.reason)

    def test_legacy_release_baseline_resolves_its_annotated_tag(self) -> None:
        client = FakeGitHub(latest="v0.13.0", metadata_available=False)
        plan = release_plan.make_plan(
            client=client,
            mode="scheduled",
            requested="latest",
            publish_requested=False,
            repository="CodeSigils/neovim-latest-ubuntu",
        )
        self.assertFalse(plan.requires_review)
        self.assertIn("repos/neovim/neovim/git/ref/tags/v0.12.5", client.tag_requests)

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

    def test_new_releases_require_metadata_and_sboms(self) -> None:
        plan = release_plan.make_plan(
            client=FakeGitHub(
                latest="v0.12.6",
                existing=True,
                existing_assets=release_plan.CORE_ASSETS,
            ),
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
