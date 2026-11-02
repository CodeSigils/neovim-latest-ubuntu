"""Unit tests for Debian packaging-revision selection and claiming."""

from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "package_revision", REPO / "scripts/package_revision.py"
)
assert SPEC and SPEC.loader
package_revision = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = package_revision
SPEC.loader.exec_module(package_revision)


def release(tag: str, *, draft: bool = False, body: str = "") -> dict:
    return {"tag_name": tag, "draft": draft, "body": body}


class RevisionSelectionTests(unittest.TestCase):
    def test_no_prior_revision_starts_at_one(self) -> None:
        self.assertEqual(package_revision.select_next_revision("0.12.5", []), 1)

    def test_successive_revisions_continue(self) -> None:
        releases = [release("v0.12.5-1"), release("v0.12.5-2")]
        self.assertEqual(package_revision.select_next_revision("0.12.5", releases), 3)

    def test_gaps_are_not_backfilled(self) -> None:
        releases = [release("v0.12.5-1"), release("v0.12.5-3")]
        self.assertEqual(package_revision.select_next_revision("0.12.5", releases), 4)
        self.assertNotIn(2, package_revision.used_revisions("0.12.5", releases))

    def test_malformed_and_legacy_releases_are_ignored(self) -> None:
        releases = [
            release("v0.12.5"),
            release("v0.12.5-0"),
            release("v0.12.5-01"),
            release("v0.12.5-abc"),
            release("v0.12.5-1.2"),
            release("v0.12.4-9"),
            release("nightly"),
        ]
        self.assertEqual(package_revision.select_next_revision("0.12.5", releases), 1)

    def test_drafts_reserve_a_revision(self) -> None:
        releases = [release("v0.12.5-2", draft=True)]
        self.assertEqual(package_revision.select_next_revision("0.12.5", releases), 3)

    def test_unrelated_base_revisions_do_not_affect_selection(self) -> None:
        releases = [release("v0.12.4-9"), release("v0.13.0-1")]
        self.assertEqual(package_revision.select_next_revision("0.12.5", releases), 1)


class RevisionClaimTests(unittest.TestCase):
    def test_claim_creates_the_next_unused_revision(self) -> None:
        action = package_revision.evaluate_claim(
            base="0.12.5",
            revision=1,
            releases=[release("v0.12.5")],
            run_id="100",
        )
        self.assertEqual(action, "create")

    def test_claim_resumes_this_runs_draft(self) -> None:
        releases = [
            release(
                "v0.12.5-1",
                draft=True,
                body=package_revision.rebuild_marker("100"),
            )
        ]
        action = package_revision.evaluate_claim(
            base="0.12.5",
            revision=1,
            releases=releases,
            run_id="100",
        )
        self.assertEqual(action, "resume")

    def test_claim_rejects_another_runs_draft(self) -> None:
        releases = [
            release(
                "v0.12.5-1",
                draft=True,
                body=package_revision.rebuild_marker("200"),
            )
        ]
        with self.assertRaises(package_revision.RevisionConflict):
            package_revision.evaluate_claim(
                base="0.12.5",
                revision=1,
                releases=releases,
                run_id="100",
            )

    def test_claim_rejects_a_published_release(self) -> None:
        with self.assertRaises(package_revision.RevisionConflict):
            package_revision.evaluate_claim(
                base="0.12.5",
                revision=1,
                releases=[release("v0.12.5-1")],
                run_id="100",
            )

    def test_claim_rejects_a_stale_revision(self) -> None:
        with self.assertRaises(package_revision.RevisionConflict):
            package_revision.evaluate_claim(
                base="0.12.5",
                revision=1,
                releases=[release("v0.12.5-1"), release("v0.12.5-2")],
                run_id="100",
            )

    def test_claim_rejects_this_runs_draft_when_not_at_the_head(self) -> None:
        releases = [
            release(
                "v0.12.5-1",
                draft=True,
                body=package_revision.rebuild_marker("100"),
            ),
            release("v0.12.5-2"),
        ]
        with self.assertRaises(package_revision.RevisionConflict):
            package_revision.evaluate_claim(
                base="0.12.5",
                revision=1,
                releases=releases,
                run_id="100",
            )

    def test_claim_rejects_an_existing_git_tag(self) -> None:
        with self.assertRaises(package_revision.RevisionConflict):
            package_revision.evaluate_claim(
                base="0.12.5",
                revision=1,
                releases=[],
                run_id="100",
                tag_exists=True,
            )

    def test_claim_rejects_a_non_positive_revision(self) -> None:
        with self.assertRaises(package_revision.RevisionConflict):
            package_revision.evaluate_claim(
                base="0.12.5",
                revision=0,
                releases=[],
                run_id="100",
            )

    def test_marker_requires_a_numeric_run_id(self) -> None:
        self.assertEqual(
            package_revision.rebuild_marker("42"),
            "<!-- packaging-rebuild-run: 42 -->",
        )
        with self.assertRaises(ValueError):
            package_revision.rebuild_marker("run-42")


class RevisionApiTests(unittest.TestCase):
    def test_api_failure_is_raised_for_the_caller_to_fail_closed(self) -> None:
        with (
            patch.object(
                package_revision.github_api,
                "gh_json_pages",
                side_effect=RuntimeError("release API unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            package_revision.claim_from_github(
                repository="CodeSigils/neovim-latest-ubuntu",
                base="0.12.5",
                revision=1,
                run_id="100",
            )

    def test_cli_exits_non_zero_when_claim_state_is_unavailable(self) -> None:
        stderr = io.StringIO()
        with (
            patch.object(
                sys,
                "argv",
                [
                    "package_revision.py",
                    "--repository",
                    "CodeSigils/neovim-latest-ubuntu",
                    "--base",
                    "0.12.5",
                    "--revision",
                    "1",
                    "--run-id",
                    "100",
                ],
            ),
            patch.object(
                package_revision,
                "claim_from_github",
                side_effect=RuntimeError("release API unavailable"),
            ),
            redirect_stderr(stderr),
        ):
            exit_code = package_revision.main()
        self.assertEqual(exit_code, 1)
        self.assertIn("could not verify packaging revision claim", stderr.getvalue())

    def test_cli_prints_the_claim_action(self) -> None:
        stdout = io.StringIO()
        with (
            patch.object(
                sys,
                "argv",
                [
                    "package_revision.py",
                    "--repository",
                    "CodeSigils/neovim-latest-ubuntu",
                    "--base",
                    "0.12.5",
                    "--revision",
                    "1",
                    "--run-id",
                    "100",
                ],
            ),
            patch.object(package_revision, "claim_from_github", return_value="resume"),
            redirect_stdout(stdout),
        ):
            exit_code = package_revision.main()
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "resume")


if __name__ == "__main__":
    unittest.main(verbosity=2)
