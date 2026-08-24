"""Regression tests for cross-workflow architecture and policy contracts."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def load_workflow(name: str) -> dict:
    return yaml.safe_load((REPO / ".github/workflows" / name).read_text())


class WorkflowPolicyTests(unittest.TestCase):
    """Validate release invariants that are easy to break independently."""

    def test_stable_release_is_candidate_first_and_uses_published_state(self) -> None:
        build = load_workflow("build.yml")
        source = (REPO / ".github/workflows/build.yml").read_text()
        planner = (REPO / "scripts/plan-release.py").read_text()
        self.assertIn("schedule", build.get("on", build.get(True)))
        self.assertEqual(build["jobs"]["package"]["uses"], "./.github/workflows/package.yml")
        self.assertIn("needs.package.result == 'success'", build["jobs"]["release"]["if"])
        self.assertIn("--draft", source)
        self.assertIn("--draft=false", source)
        self.assertIn("releases/tags", planner)
        self.assertNotIn("git tag -l", source)
        self.assertFalse((REPO / ".github/workflows/check-upstream.yml").exists())

    def test_maintenance_releases_auto_publish_and_feature_releases_require_review(self) -> None:
        planner = (REPO / "scripts/plan-release.py").read_text()
        build = (REPO / ".github/workflows/build.yml").read_text()
        self.assertIn('mode in {"scheduled", "tag"}', planner)
        self.assertIn("version.feature_release", planner)
        self.assertIn("release-reviewed", build)
        self.assertIn("release-auto", build)

    def test_release_requires_both_architectures_and_metadata(self) -> None:
        build = (REPO / ".github/workflows/build.yml").read_text()
        for required in (
            "nvim-linux-x86_64.deb",
            "nvim-linux-arm64.deb",
            "BUILD-METADATA-amd64.json",
            "BUILD-METADATA-arm64.json",
            "Architecture",
        ):
            self.assertIn(required, build)
        self.assertIn("verify-release-candidate.py", build)
        self.assertIn("unexpected or incomplete asset set", build)

    def test_packaging_matrix_is_shared_by_stable_and_nightly(self) -> None:
        package = load_workflow("package.yml")
        matrix = package["jobs"]["build"]["strategy"]["matrix"]["include"]
        self.assertEqual(
            matrix,
            [
                {
                    "arch": "x86_64",
                    "runner": "${{ vars.RUNNER_X86_64 || 'ubuntu-latest' }}",
                    "deb_arch": "amd64",
                    "deb_file": "nvim-linux-x86_64.deb",
                },
                {
                    "arch": "aarch64",
                    "runner": "${{ vars.RUNNER_AARCH64 || 'ubuntu-24.04-arm' }}",
                    "deb_arch": "arm64",
                    "deb_file": "nvim-linux-arm64.deb",
                },
            ],
        )
        nightly = load_workflow("nightly.yml")
        self.assertEqual(nightly["jobs"]["package"]["uses"], "./.github/workflows/package.yml")
        self.assertEqual(
            nightly["jobs"]["package"]["with"]["source_commit"],
            "${{ needs.resolve.outputs.source_commit }}",
        )

    def test_source_is_pinned_and_stable_builds_use_release_mode(self) -> None:
        build_script = (REPO / "build.sh").read_text()
        package_source = (REPO / ".github/workflows/package.yml").read_text()
        package = load_workflow("package.yml")
        self.assertIn("SOURCE_COMMIT", build_script)
        self.assertIn('BUILD_TYPE="Release"', build_script)
        self.assertIn('BUILD_TYPE="RelWithDebInfo"', build_script)
        self.assertIn("source_commit", package_source)
        triggers = package.get("on", package.get(True))
        self.assertTrue(triggers["workflow_call"]["inputs"]["source_commit"]["required"])
        self.assertNotIn("-e GH_TOKEN", package_source)

    def test_lintian_is_a_regression_gate_not_silently_ignored(self) -> None:
        package = (REPO / ".github/workflows/package.yml").read_text()
        checker = (REPO / "scripts/check-lintian.sh").read_text()
        allowlist = (REPO / "scripts/lintian-allowlist.txt").read_text()
        self.assertIn("check-lintian.sh", package)
        self.assertIn("New lintian findings", checker)
        self.assertIn("unstripped-binary-or-object", allowlist)

    def test_policy_workflow_covers_all_maintenance_surfaces(self) -> None:
        policy = load_workflow("policy.yml")
        triggers = policy.get("on", policy.get(True))
        expected = {
            "*.md",
            "docs/**",
            "deps/**",
            "Containerfile",
            "build.sh",
            "test.sh",
            "scripts/**",
            "tests/**",
            "pyproject.toml",
            "requirements-dev.txt",
            ".gitattributes",
            ".gitignore",
            ".mailmap",
            ".githooks/**",
            ".github/actions/**",
            ".github/workflows/**",
            ".github/dependabot.yml",
            "LICENSE",
        }
        for event in ("push", "pull_request"):
            self.assertEqual(set(triggers[event]["paths"]), expected)
        quality = (REPO / ".github/actions/quality-gates/action.yml").read_text()
        self.assertIn("actionlint@sha256:", quality)
        self.assertIn("python3 -m unittest discover", quality)
        self.assertIn("ruff check", quality)
        self.assertIn("zizmor --offline", quality)

    def test_validation_only_changes_do_not_start_native_package_builds(self) -> None:
        build = load_workflow("build.yml")
        triggers = build.get("on", build.get(True))
        expected_ignored = {
            "pyproject.toml",
            "requirements-dev.txt",
            "tests/**",
            "scripts/check-dependencies.py",
            "scripts/check-markdown-links.py",
            "scripts/check-release-readiness.sh",
            "scripts/check-repository-settings.py",
            "scripts/check-yaml-syntax.py",
            "scripts/report-action-freshness.py",
        }
        for event in ("push", "pull_request"):
            ignored = set(triggers[event]["paths-ignore"])
            self.assertTrue(expected_ignored <= ignored)

    def test_failure_issues_are_exception_only_and_self_healing(self) -> None:
        stable = (REPO / ".github/workflows/build.yml").read_text()
        nightly = (REPO / ".github/workflows/nightly.yml").read_text()
        self.assertIn("Stable release automation failed", stable)
        self.assertIn("Resolved by successful release", stable)
        self.assertIn("Nightly build failed", nightly)
        self.assertIn("The nightly build has recovered", nightly)
        self.assertNotIn("New upstream Neovim release detected", stable)

    def test_stable_ci_uses_independent_version_expectations(self) -> None:
        package = (REPO / ".github/workflows/package.yml").read_text()
        build_script = (REPO / "build.sh").read_text()
        test_script = (REPO / "test.sh").read_text()
        self.assertIn("EXPECTED_SOURCE_VERSION", build_script)
        self.assertIn("EXPECTED_PACKAGE_VERSION", build_script)
        self.assertIn("CPACK_DEBIAN_PACKAGE_RELEASE", build_script)
        self.assertIn("$(cat output/EXPECTED_SOURCE_VERSION)", package)
        self.assertIn("$(cat output/EXPECTED_PACKAGE_VERSION)", package)
        self.assertIn("grep -Fq", test_script)

    def test_documentation_avoids_known_drift_sources(self) -> None:
        documentation = [
            REPO / "README.md",
            REPO / "RELEASING.md",
            REPO / "SECURITY.md",
            *(REPO / "docs").glob("*.md"),
        ]
        combined = "\n".join(path.read_text() for path in documentation)
        self.assertFalse((REPO / "docs/build-plan.md").exists())
        self.assertNotIn("build-plan.md", combined)
        self.assertIn("8-point automated test suite", (REPO / "README.md").read_text())
        self.assertNotIn("7-point automated test suite", combined)
        self.assertNotIn("Neovim LTS", combined)

    def test_dependency_freshness_report_is_non_blocking(self) -> None:
        workflow = load_workflow("dependency-freshness.yml")
        triggers = workflow.get("on", workflow.get(True))
        self.assertIn("schedule", triggers)
        self.assertEqual(
            workflow["permissions"],
            {"actions": "read", "contents": "read", "issues": "read"},
        )
        report = (REPO / "scripts/report-action-freshness.py").read_text()
        self.assertIn("update available", report)
        self.assertIn("could not be verified", report)
        self.assertIn("latest_cache", report)
        self.assertIn(
            "check-repository-settings.py",
            (REPO / ".github/workflows/dependency-freshness.yml").read_text(),
        )

    def test_workflows_use_the_configurable_x86_runner_and_node24(self) -> None:
        for path in (REPO / ".github/workflows").glob("*.yml"):
            workflow = load_workflow(path.name)
            source = path.read_text()
            if "runs-on:" in source:
                self.assertNotIn("runs-on: ubuntu-", source, path.name)
            if "uses:" in source:
                self.assertEqual(
                    workflow.get("env", {}).get("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"),
                    True,
                    path.name,
                )

    def test_codeql_runs_for_dependency_update_pull_requests(self) -> None:
        codeql = (REPO / ".github/workflows/codeql.yml").read_text()
        self.assertNotIn("github.actor != 'dependabot[bot]'", codeql)


if __name__ == "__main__":
    unittest.main(verbosity=2)
