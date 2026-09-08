"""Tests for low-cost documentation and dependency-maintenance tools."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def load_script(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


markdown_links = load_script("markdown_links", "check-markdown-links.py")
action_freshness = load_script("action_freshness", "report-action-freshness.py")
dependabot_report = load_script("dependabot_report", "report-dependabot-prs.py")
stale_report = load_script("stale_report", "report-stale-branches.py")
github_api = load_script("github_api_test", "github_api.py")


class MaintenanceToolTests(unittest.TestCase):
    def test_paginated_api_results_are_flattened(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout='[[{"id": 1}], [{"id": 2}]]', stderr=""
        )
        with patch.object(github_api.subprocess, "run", return_value=completed) as run:
            self.assertEqual(
                github_api.gh_json_pages("repos/owner/repo/items"), [{"id": 1}, {"id": 2}]
            )
        self.assertIn("--paginate", run.call_args.args[0])
        self.assertIn("--slurp", run.call_args.args[0])

    def test_paginated_api_retries_transient_cli_failure(self) -> None:
        responses = [
            subprocess.CompletedProcess(
                args=["gh"], returncode=1, stdout="", stderr="connection reset"
            ),
            subprocess.CompletedProcess(
                args=["gh"], returncode=0, stdout='[[{"id": 1}]]', stderr=""
            ),
        ]
        with (
            patch.object(github_api.subprocess, "run", side_effect=responses),
            patch.object(github_api.time, "sleep"),
        ):
            self.assertEqual(github_api.gh_json_pages("repos/owner/repo/items"), [{"id": 1}])

    def test_paginated_api_rejects_non_array_page(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout='[{"id": 1}]', stderr=""
        )
        with (
            patch.object(github_api.subprocess, "run", return_value=completed),
            self.assertRaisesRegex(RuntimeError, "non-array page"),
        ):
            github_api.gh_json_pages("repos/owner/repo/items")

    def test_markdown_enumeration_respects_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init", "-q", root], check=True)
            (root / ".gitignore").write_text("cache/\n")
            (root / "tracked.md").write_text("tracked\n")
            (root / "visible.md").write_text("visible\n")
            (root / "cache").mkdir()
            (root / "cache" / "ignored.md").write_text("ignored\n")
            subprocess.run(["git", "-C", root, "add", "tracked.md"], check=True)
            previous = Path.cwd()
            try:
                os.chdir(root)
                paths = markdown_links.markdown_paths()
            finally:
                os.chdir(previous)

        self.assertEqual(paths, [Path("tracked.md"), Path("visible.md")])

    def test_action_freshness_accepts_only_stable_tags(self) -> None:
        self.assertEqual(action_freshness.stable_tag_version("v7.2.1", "7"), (7, 2, 1))
        self.assertEqual(action_freshness.stable_tag_version("v7.2", "7"), (7, 2, 0))
        self.assertIsNone(action_freshness.stable_tag_version("v7.3.0-rc.1", "7"))
        self.assertIsNone(action_freshness.stable_tag_version("v8.0.0", "7"))

    def test_dependabot_classifier_reports_failed_checks(self) -> None:
        responses = {
            "repos/owner/repo/pulls?state=open&per_page=100": [
                {
                    "number": 7,
                    "user": {"login": "dependabot[bot]"},
                    "head": {"ref": "deps", "sha": "a"},
                }
            ],
            "repos/owner/repo/pulls/7/files?per_page=100": [{"filename": "requirements-dev.txt"}],
            "repos/owner/repo/commits/a/check-runs?per_page=100": {
                "check_runs": [{"name": "policy", "status": "completed", "conclusion": "failure"}]
            },
        }
        with (
            patch.object(dependabot_report, "gh_json_pages", side_effect=responses.__getitem__),
            patch.object(dependabot_report, "gh_json", side_effect=responses.__getitem__),
        ):
            self.assertEqual(
                dependabot_report.classify("owner/repo"), ["#7 checks-failed: deps (files=1)"]
            )

    def test_dependabot_classifier_reports_pending_checks(self) -> None:
        responses = {
            "repos/owner/repo/pulls?state=open&per_page=100": [
                {
                    "number": 8,
                    "user": {"login": "dependabot[bot]"},
                    "head": {"ref": "deps", "sha": "b"},
                }
            ],
            "repos/owner/repo/pulls/8/files?state=open&per_page=100": [],
            "repos/owner/repo/pulls/8/files?per_page=100": [],
            "repos/owner/repo/commits/b/check-runs?per_page=100": {
                "check_runs": [{"name": "build", "status": "in_progress", "conclusion": None}]
            },
        }
        with (
            patch.object(dependabot_report, "gh_json_pages", side_effect=responses.__getitem__),
            patch.object(dependabot_report, "gh_json", side_effect=responses.__getitem__),
        ):
            self.assertEqual(
                dependabot_report.classify("owner/repo"), ["#8 waiting-for-checks: deps (files=0)"]
            )

    def test_stale_report_excludes_main_and_open_pr_heads(self) -> None:
        old = "2000-01-01T00:00:00Z"
        responses = {
            "repos/owner/repo/branches?per_page=100": [
                {"name": "main", "commit": {"sha": "main-sha"}},
                {"name": "open", "commit": {"sha": "open-sha"}},
                {"name": "stale", "commit": {"sha": "stale-sha"}},
            ],
            "repos/owner/repo/pulls?state=open&per_page=100": [{"head": {"ref": "open"}}],
            "repos/owner/repo/commits/stale-sha": {"commit": {"committer": {"date": old}}},
        }
        with (
            patch.object(stale_report, "gh_json_pages", side_effect=responses.__getitem__),
            patch.object(stale_report, "gh_json", side_effect=responses.__getitem__),
        ):
            result = stale_report.report("owner/repo", days=30)
        self.assertEqual(result, [f"stale (last commit {old})"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
