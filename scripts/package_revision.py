#!/usr/bin/env python3
"""Select and claim the next Debian package revision for a packaging rebuild."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import github_api
import release_metadata

RUN_MARKER = re.compile(r"<!--\s*packaging-rebuild-run:\s*(\d+)\s*-->")


@dataclass(frozen=True)
class ReleaseRecord:
    """The release state relevant to revision selection."""

    tag: str
    draft: bool
    body: str


class RevisionConflict(ValueError):
    """Raised when a package revision cannot be claimed safely."""


def _records(releases: Iterable[Mapping[str, Any]]) -> list[ReleaseRecord]:
    records: list[ReleaseRecord] = []
    for release in releases:
        if not isinstance(release, Mapping):
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str):
            continue
        body = release.get("body")
        records.append(
            ReleaseRecord(
                tag=tag,
                draft=bool(release.get("draft", False)),
                body=body if isinstance(body, str) else "",
            )
        )
    return records


def parse_revision_tag(tag: str, base: str) -> int | None:
    """Return the positive revision encoded in *tag* for *base*, if any."""
    match = release_metadata.RELEASE_TAG.fullmatch(tag)
    if not match:
        return None
    major, minor, patch, revision = match.groups()
    if revision is None or f"{major}.{minor}.{patch}" != base:
        return None
    return int(revision)


def _used_revisions(base: str, records: Iterable[ReleaseRecord]) -> set[int]:
    revisions: set[int] = set()
    for record in records:
        revision = parse_revision_tag(record.tag, base)
        if revision is not None:
            revisions.add(revision)
    return revisions


def used_revisions(base: str, releases: Iterable[Mapping[str, Any]]) -> set[int]:
    """Collect every well-formed revision already claimed for *base*.

    Draft and published releases both reserve a revision. Malformed tags and
    revisions for other upstream versions are ignored.
    """
    return _used_revisions(base, _records(releases))


def _next_revision(base: str, records: Iterable[ReleaseRecord]) -> int:
    return max(_used_revisions(base, records), default=0) + 1


def select_next_revision(base: str, releases: Iterable[Mapping[str, Any]]) -> int:
    """Select the next unused revision without backfilling gaps."""
    return _next_revision(base, _records(releases))


def tag_for_revision(base: str, revision: int) -> str:
    """Return the canonical release tag for a package revision."""
    return f"v{base}-{revision}"


def rebuild_marker(run_id: str) -> str:
    """Build the hidden release-body marker that identifies the owning run."""
    if not re.fullmatch(r"\d+", run_id):
        raise ValueError("run id must be numeric")
    return f"<!-- packaging-rebuild-run: {run_id} -->"


def _claimed_by_run(body: str, run_id: str) -> bool:
    return any(match.group(1) == run_id for match in RUN_MARKER.finditer(body))


def evaluate_claim(
    *,
    base: str,
    revision: int,
    releases: Iterable[Mapping[str, Any]],
    run_id: str,
    tag_exists: bool = False,
) -> str:
    """Decide whether this run may create or resume the selected revision.

    Returns ``create`` for an unused revision at the head of the sequence and
    ``resume`` only for this run's own draft. Every other state is a conflict.
    """
    if revision < 1:
        raise RevisionConflict(f"revision must be a positive integer, got {revision}")
    records = _records(releases)
    next_revision = _next_revision(base, records)
    tag = tag_for_revision(base, revision)
    matching = next(
        (record for record in records if record.tag in {tag, tag.removeprefix("v")}),
        None,
    )
    if matching is not None:
        if matching.draft and _claimed_by_run(matching.body, run_id):
            if revision == next_revision - 1:
                return "resume"
            raise RevisionConflict(
                f"draft release {tag} belongs to this run but is no longer the next revision "
                f"(next unused revision is {next_revision})"
            )
        state = "draft" if matching.draft else "published"
        raise RevisionConflict(f"{state} release {tag} is already claimed by another run")
    if tag_exists:
        raise RevisionConflict(f"git tag {tag} already exists")
    if revision != next_revision:
        raise RevisionConflict(
            f"revision {revision} is stale; the next unused revision is {next_revision}"
        )
    return "create"


def claim_from_github(*, repository: str, base: str, revision: int, run_id: str) -> str:
    """Read repository release state through the authenticated GitHub API."""
    releases = github_api.gh_json_pages(f"repos/{repository}/releases")
    tag = tag_for_revision(base, revision)
    encoded = urllib.parse.quote(tag, safe="")
    reference = github_api.gh_json_optional(f"repos/{repository}/git/ref/tags/{encoded}")
    return evaluate_claim(
        base=base,
        revision=revision,
        releases=releases,
        run_id=run_id,
        tag_exists=reference is not None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--base", required=True)
    parser.add_argument("--revision", required=True, type=int)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.repository or not args.run_id:
        print(
            "error: --repository and --run-id (or GITHUB_* variables) are required", file=sys.stderr
        )
        return 2
    try:
        action = claim_from_github(
            repository=args.repository,
            base=args.base,
            revision=args.revision,
            run_id=args.run_id,
        )
    except (KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: could not verify packaging revision claim: {error}", file=sys.stderr)
        return 1
    print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
