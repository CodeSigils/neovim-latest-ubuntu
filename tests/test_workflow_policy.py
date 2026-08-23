#!/usr/bin/env python3
"""Regression tests for cross-workflow policy contracts."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


class WorkflowPolicyTests(unittest.TestCase):
    """Validate workflow contracts that are easy to break independently."""

    def test_upstream_check_is_notification_only(self) -> None:
        """Dynamic latest builds must not rely on bot version-edit commits."""
        upstream = (REPO / ".github/workflows/check-upstream.yml").read_text()
        self.assertIn("Create or update release notification issue", upstream)
        self.assertNotIn("auto/update-v", upstream)
        self.assertNotIn("git commit", upstream)
        self.assertIn("issues: write", upstream)

    def test_required_workflow_labels_are_validated_in_build_lint(self) -> None:
        """Workflow-created labels should be guarded by the label validation script."""
        build = yaml.safe_load((REPO / ".github/workflows/build.yml").read_text())
        lint_steps = build["jobs"]["lint"]["steps"]
        uses = "\n".join(step.get("uses", "") for step in lint_steps)
        self.assertIn("./.github/actions/quality-gates", uses)
        quality = (REPO / ".github/actions/quality-gates/action.yml").read_text()
        self.assertIn("python3 scripts/check-labels.py", quality)

    def test_label_validation_covers_workflow_created_labels(self) -> None:
        """Every workflow-created label should be present in check-labels.py."""
        label_script = (REPO / "scripts/check-labels.py").read_text()
        workflows = "\n".join(path.read_text() for path in (REPO / ".github/workflows").glob("*.yml"))
        labels = set(re.findall(r"--label ([A-Za-z0-9_.-]+)|labels: \['([^']+)'\]", workflows))
        flattened = {item for pair in labels for item in pair if item}

        for label in flattened:
            self.assertIn(f'"{label}"', label_script)

    def test_readme_dependency_contract_has_lightweight_ci(self) -> None:
        """README dependency edits should be checked without running package builds."""
        docs_path = REPO / ".github/workflows/docs-consistency.yml"
        docs = yaml.safe_load(docs_path.read_text())
        triggers = docs.get("on", docs.get(True))
        required_paths = {
            "README.md",
            "RELEASING.md",
            "SECURITY.md",
            "docs/**",
            "deps/**",
            "Containerfile",
            "build.sh",
            "test.sh",
            "scripts/check-dependencies.py",
            "tests/test_workflow_policy.py",
            "scripts/check-markdown-links.py",
            ".github/workflows/docs-consistency.yml",
        }

        for event in ("push", "pull_request"):
            self.assertTrue(required_paths <= set(triggers[event]["paths"]))

        steps = docs["jobs"]["dependency-consistency"]["steps"]
        runs = [step.get("run") for step in steps if "run" in step]
        self.assertEqual(
            runs,
            [
                "python3 scripts/check-dependencies.py",
                "python3 -m unittest tests.test_workflow_policy",
                "python3 scripts/check-markdown-links.py",
            ],
        )
        self.assertEqual(docs["permissions"], {"contents": "read"})

        build = yaml.safe_load((REPO / ".github/workflows/build.yml").read_text())
        build_triggers = build.get("on", build.get(True))
        for event in ("push", "pull_request"):
            self.assertIn(
                ".github/workflows/docs-consistency.yml",
                build_triggers[event]["paths-ignore"],
            )

    def test_release_requires_the_complete_successful_build_matrix(self) -> None:
        """A failed architecture must never produce a partial GitHub Release."""
        build = yaml.safe_load((REPO / ".github/workflows/build.yml").read_text())
        release = build["jobs"]["release"]
        release_condition = release["if"]
        runs = "\n".join(
            step.get("run", "") for step in release["steps"] if "run" in step
        )

        self.assertIn("needs.build.result == 'success'", release_condition)
        self.assertNotIn("!cancelled()", release_condition)
        self.assertIn("nvim-linux-x86_64.deb", runs)
        self.assertIn("nvim-linux-arm64.deb", runs)
        self.assertIn("Architecture", runs)
        self.assertIn("Reject an existing release for this immutable tag", "\n".join(
            step.get("name", "") for step in release["steps"]
        ))

    def test_nightly_recovery_only_targets_automated_failure_issues(self) -> None:
        """Recovery must not close unrelated issues carrying the nightly label."""
        nightly = (REPO / ".github/workflows/nightly.yml").read_text()
        self.assertIn('startswith("Nightly build failed —")', nightly)

    def test_build_matrix_enforces_expected_artifact_identity(self) -> None:
        """Each runner must emit exactly the package for its declared architecture."""
        build = yaml.safe_load((REPO / ".github/workflows/build.yml").read_text())
        matrix = build["jobs"]["build"]["strategy"]["matrix"]["include"]

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
        nightly = yaml.safe_load(
            (REPO / ".github/workflows/nightly.yml").read_text()
        )
        self.assertEqual(
            nightly["jobs"]["build"]["strategy"]["matrix"]["include"], matrix
        )

    def test_stable_ci_uses_independent_version_expectations(self) -> None:
        """Generated package metadata must not be its own CI oracle."""
        workflow = (REPO / ".github/workflows/build.yml").read_text()
        build_script = (REPO / "build.sh").read_text()
        test_script = (REPO / "test.sh").read_text()

        self.assertIn("EXPECTED_SOURCE_VERSION", build_script)
        self.assertIn("EXPECTED_PACKAGE_VERSION", build_script)
        self.assertIn("CPACK_DEBIAN_PACKAGE_RELEASE", build_script)
        self.assertIn("$(cat output/EXPECTED_SOURCE_VERSION)", workflow)
        self.assertIn("$(cat output/EXPECTED_PACKAGE_VERSION)", workflow)
        self.assertIn("grep -Fq", test_script)

    def test_dependabot_does_not_have_an_unsafe_auto_merge_workflow(self) -> None:
        """Without a universal required gate, dependency PRs stay manual."""
        self.assertFalse(
            (REPO / ".github/workflows/dependabot-auto-merge.yml").exists()
        )

    def test_documentation_avoids_known_drift_sources(self) -> None:
        """Implemented plans, stale counts, and volatile snapshots stay out of docs."""
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

        resources = (REPO / "docs/resources.md").read_text()
        for stale_snapshot in (
            "13 of 18",
            "130 minutes",
            "first ~48 hours",
            "~5 min per Dependabot PR",
        ):
            self.assertNotIn(stale_snapshot, resources)

        reproducibility = (REPO / "docs/reproducibility.md").read_text()
        self.assertNotRegex(
            reproducibility,
            r"`VERSION`.*`[0-9]+[.][0-9]+[.][0-9]+` in `build[.]sh`",
        )

    def test_build_defaults_to_latest_and_uses_structured_api_parsing(self) -> None:
        """Local builds must not silently fall back to an obsolete release."""
        build = (REPO / "build.sh").read_text()
        self.assertIn('VERSION:-latest', build)
        self.assertIn("curl --fail", build)
        self.assertIn("jq -r '.tag_name // empty'", build)

    def test_dependency_freshness_report_is_scheduled_and_non_blocking(self) -> None:
        """Action freshness is reported separately from build correctness."""
        workflow = yaml.safe_load(
            (REPO / ".github/workflows/dependency-freshness.yml").read_text()
        )
        triggers = workflow.get("on", workflow.get(True))
        self.assertIn("schedule", triggers)
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        report = (REPO / "scripts/report-action-freshness.py").read_text()
        self.assertIn("update available", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
