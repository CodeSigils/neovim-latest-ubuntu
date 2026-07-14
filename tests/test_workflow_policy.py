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

    def test_auto_update_bot_commits_are_allowed_only_on_auto_update_branches(self) -> None:
        """check-upstream bot commits must be compatible with the author guard."""
        upstream = (REPO / ".github/workflows/check-upstream.yml").read_text()
        author = (REPO / ".github/workflows/check-author.yml").read_text()

        self.assertIn('git config user.name "github-actions[bot]"', upstream)
        self.assertIn("CHECKED_BRANCH", author)
        self.assertRegex(author, r"auto/update-v\*")
        self.assertIn('github-actions[bot]', author)

    def test_required_workflow_labels_are_validated_in_build_lint(self) -> None:
        """Workflow-created labels should be guarded by the label validation script."""
        build = yaml.safe_load((REPO / ".github/workflows/build.yml").read_text())
        lint_steps = build["jobs"]["lint"]["steps"]
        runs = "\n".join(step.get("run", "") for step in lint_steps)

        self.assertIn("python3 scripts/check-labels.py", runs)

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
            "deps/**",
            "Containerfile",
            "build.sh",
            "test.sh",
            "scripts/check-dependencies.py",
            ".github/workflows/docs-consistency.yml",
        }

        for event in ("push", "pull_request"):
            self.assertTrue(required_paths <= set(triggers[event]["paths"]))

        steps = docs["jobs"]["dependency-consistency"]["steps"]
        runs = [step.get("run") for step in steps if "run" in step]
        self.assertEqual(runs, ["python3 scripts/check-dependencies.py"])
        self.assertEqual(docs["permissions"], {"contents": "read"})

        build = yaml.safe_load((REPO / ".github/workflows/build.yml").read_text())
        build_triggers = build.get("on", build.get(True))
        for event in ("push", "pull_request"):
            self.assertIn(
                ".github/workflows/docs-consistency.yml",
                build_triggers[event]["paths-ignore"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
