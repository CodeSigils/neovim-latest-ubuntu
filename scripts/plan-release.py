#!/usr/bin/env python3
"""Resolve an exact upstream source and decide whether CI should publish it."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

import github_api
import package_revision
import release_metadata

RISK_PATHS: Final = (
    "CMakeLists.txt",
    "cmake/**",
    "cmake.deps/**",
)


@dataclass(frozen=True)
class Version:
    base: str
    tag: str
    package_revision: str
    feature_release: bool


@dataclass(frozen=True)
class Plan:
    package_revision: str
    publish: bool
    reason: str
    rebuild_reason: str
    requires_review: bool
    should_build: bool
    source_commit: str
    tag: str
    version: str


@dataclass(frozen=True)
class RiskAssessment:
    requires_review: bool
    summary: str


@dataclass(frozen=True)
class BuildState:
    version: Version
    publish: bool
    should_build: bool
    source_commit: str


def parse_version(value: str) -> Version:
    match = release_metadata.RELEASE_TAG.fullmatch(value)
    if not match:
        raise ValueError("expected a stable X.Y.Z or package-revision X.Y.Z-N version")
    major, minor, patch, revision = match.groups()
    base = f"{major}.{minor}.{patch}"
    suffix = f"-{revision}" if revision else ""
    return Version(base, f"v{base}{suffix}", revision or "", int(patch) == 0)


class GitHub:
    def get(self, path: str) -> dict:
        result = github_api.gh_json(path)
        if not isinstance(result, dict):
            raise ValueError(f"GitHub returned a non-object response for {path}")
        return result

    def optional(self, path: str) -> dict | None:
        result = github_api.gh_json_optional(path)
        if result is None:
            return None
        if not isinstance(result, dict):
            raise ValueError(f"GitHub returned a non-object response for {path}")
        return result

    def pages(self, path: str) -> list[dict]:
        result = github_api.gh_json_pages(path)
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise ValueError(f"GitHub returned a non-list response for {path}")
        return result

    def text(self, path: str) -> str:
        return github_api.gh_text(path)


def upstream_commit(client: GitHub, tag: str) -> str:
    encoded = urllib.parse.quote(tag, safe="")
    reference = client.get(f"repos/neovim/neovim/git/ref/tags/{encoded}")["object"]
    for _ in range(4):
        if reference["type"] == "commit":
            sha = reference["sha"]
            if not release_metadata.FULL_SHA.fullmatch(sha):
                raise ValueError(f"upstream returned an invalid commit SHA: {sha}")
            return sha
        if reference["type"] != "tag":
            raise ValueError(f"upstream tag resolves to unsupported object: {reference['type']}")
        reference = client.get(f"repos/neovim/neovim/git/tags/{reference['sha']}")["object"]
    raise ValueError("upstream tag indirection is too deep")


def release_is_complete(client: GitHub, repository: str, tag: str) -> bool:
    encoded = urllib.parse.quote(tag, safe="")
    release = client.optional(f"repos/{repository}/releases/tags/{encoded}")
    if not release or release.get("draft") or release.get("prerelease"):
        return False
    assets = {asset["name"]: asset for asset in release.get("assets", [])}
    required_assets = release_metadata.LEGACY_RELEASE_ASSETS.get(
        tag, release_metadata.REQUIRED_RELEASE_ASSETS
    )
    return all(
        name in assets
        and assets[name].get("state") == "uploaded"
        and assets[name].get("size", 0) > 0
        for name in required_assets
    )


def source_commit_from_release(client: GitHub, repository: str) -> str:
    """Read the exact upstream commit from the most recent published package."""
    release = client.get(f"repos/{repository}/releases/latest")
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("published release does not contain an asset list")
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("name") != "BUILD-METADATA-amd64.json":
            continue
        asset_id = asset.get("id")
        if not isinstance(asset_id, int):
            raise ValueError("build metadata asset has no numeric ID")
        metadata = json.loads(client.text(f"repos/{repository}/releases/assets/{asset_id}"))
        if not isinstance(metadata, dict):
            raise ValueError("build metadata is not a JSON object")
        upstream = metadata.get("upstream")
        if not isinstance(upstream, dict):
            raise ValueError("build metadata has no upstream record")
        commit = upstream.get("commit")
        if isinstance(commit, str) and release_metadata.FULL_SHA.fullmatch(commit):
            return commit
        raise ValueError("build metadata has an invalid upstream commit")

    tag = release.get("tag_name")
    if not isinstance(tag, str):
        raise ValueError("published release has no tag")
    return upstream_commit(client, f"v{parse_version(tag).base}")


def requires_risk_review(client: GitHub, repository: str, candidate_commit: str) -> RiskAssessment:
    """Classify upstream changes that can alter the package build or installation."""
    try:
        baseline_commit = source_commit_from_release(client, repository)
        comparison = client.get(
            f"repos/neovim/neovim/compare/{baseline_commit}...{candidate_commit}"
        )
        files = comparison.get("files")
        if not isinstance(files, list):
            raise ValueError("upstream comparison did not include changed files")
        risk_files = [
            filename
            for change in files
            if isinstance(change, dict)
            and isinstance(filename := change.get("filename"), str)
            and any(Path(filename).match(pattern) for pattern in RISK_PATHS)
        ]
    except (json.JSONDecodeError, KeyError, OSError, RuntimeError, ValueError) as error:
        return RiskAssessment(True, f"review required: unable to classify upstream risk ({error})")

    comparison_label = f"{baseline_commit[:12]}...{candidate_commit[:12]}"
    if risk_files:
        return RiskAssessment(
            True,
            f"review required: {comparison_label} changes packaging-critical paths: {', '.join(risk_files)}",
        )
    return RiskAssessment(
        False, f"auto-publish: {comparison_label} has no packaging-critical changes"
    )


def _validate_rebuild_reason(mode: str, requested: str, rebuild_reason: str) -> str:
    if "\r" in rebuild_reason or "\n" in rebuild_reason:
        raise ValueError("packaging rebuild reason must be a single line")
    rebuild_reason = rebuild_reason.strip()
    if rebuild_reason and mode != "manual":
        raise ValueError("packaging rebuilds require an explicit manual dispatch")
    if rebuild_reason and requested not in ("", "latest"):
        raise ValueError(
            "packaging rebuilds select the latest upstream release; do not specify a version"
        )
    return rebuild_reason


def _github_output_lines(payload: dict[str, object]) -> list[str]:
    """Serialize scalar planner outputs without allowing environment-file injection."""
    lines: list[str] = []
    for key, value in payload.items():
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        if "\r" in rendered or "\n" in rendered:
            raise ValueError(f"GitHub output {key} must be a single line")
        lines.append(f"{key}={rendered}\n")
    return lines


def _requested_version(client: GitHub, requested: str) -> Version:
    if requested in ("", "latest"):
        upstream = client.get("repos/neovim/neovim/releases/latest")
        requested = upstream.get("tag_name", "")
    return parse_version(requested)


def _ensure_upstream_release(client: GitHub, version: Version) -> str:
    """Return the upstream tag after confirming it is a published stable release."""
    upstream_tag = f"v{version.base}"
    encoded = urllib.parse.quote(upstream_tag, safe="")
    release = client.optional(f"repos/neovim/neovim/releases/tags/{encoded}")
    if not release or release.get("draft") or release.get("prerelease"):
        raise ValueError(f"{upstream_tag} is not a published upstream stable release")
    return upstream_tag


def _select_rebuild_version(client: GitHub, repository: str, version: Version) -> Version:
    """Replace the upstream version with the next unused package revision."""
    releases = client.pages(f"repos/{repository}/releases")
    revision = package_revision.select_next_revision(version.base, releases)
    tag = package_revision.tag_for_revision(version.base, revision)
    encoded_tag = urllib.parse.quote(tag, safe="")
    if client.optional(f"repos/{repository}/git/ref/tags/{encoded_tag}") is not None:
        raise ValueError(f"{tag} already exists as a git tag; refusing to reuse a revision")
    return Version(
        base=version.base,
        tag=tag,
        package_revision=str(revision),
        feature_release=version.feature_release,
    )


def _assess_plan(
    client: GitHub,
    repository: str,
    *,
    state: BuildState,
    rebuild_reason: str,
) -> RiskAssessment:
    if state.publish and state.should_build:
        assessment = requires_risk_review(client, repository, state.source_commit)
    elif state.should_build:
        assessment = RiskAssessment(False, "build candidate")
    else:
        assessment = RiskAssessment(False, "release already published with required assets")

    if state.version.package_revision and state.publish and state.should_build:
        reason = f"review required: packaging-only revision {state.version.tag}"
        if rebuild_reason:
            reason = f"{reason} (reason: {rebuild_reason})"
        return RiskAssessment(True, f"{reason}; {assessment.summary}")
    if rebuild_reason and state.should_build:
        return RiskAssessment(
            False,
            f"packaging-only revision {state.version.tag} ({rebuild_reason}); {assessment.summary}",
        )
    return assessment


def make_plan(  # noqa: PLR0913
    *,
    client: GitHub,
    mode: str,
    requested: str,
    publish_requested: bool,
    repository: str,
    rebuild_reason: str = "",
) -> Plan:
    rebuild_reason = _validate_rebuild_reason(mode, requested, rebuild_reason)
    version = _requested_version(client, requested)
    if version.package_revision and not rebuild_reason and mode == "manual":
        raise ValueError(
            "packaging revisions are selected by the rebuild workflow; provide a rebuild reason"
        )

    upstream_tag = _ensure_upstream_release(client, version)
    if rebuild_reason:
        version = _select_rebuild_version(client, repository, version)

    publish = mode in {"scheduled", "tag"} or publish_requested
    complete = release_is_complete(client, repository, version.tag)
    should_build = not (publish and complete)
    source_commit = upstream_commit(client, upstream_tag)
    assessment = _assess_plan(
        client,
        repository,
        state=BuildState(
            version=version,
            publish=publish,
            should_build=should_build,
            source_commit=source_commit,
        ),
        rebuild_reason=rebuild_reason,
    )
    return Plan(
        package_revision=version.package_revision,
        publish=publish,
        reason=assessment.summary,
        rebuild_reason=rebuild_reason,
        requires_review=publish and should_build and assessment.requires_review,
        should_build=should_build,
        source_commit=source_commit,
        tag=version.tag,
        version=version.base,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("ci", "scheduled", "manual", "tag"), required=True)
    parser.add_argument("--version", default="latest")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--rebuild-reason", default="")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--github-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.repository:
        print("error: --repository or GITHUB_REPOSITORY is required", file=sys.stderr)
        return 2
    try:
        plan = make_plan(
            client=GitHub(),
            mode=args.mode,
            requested=args.version,
            publish_requested=args.publish,
            repository=args.repository,
            rebuild_reason=args.rebuild_reason,
        )
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: could not create release plan: {error}", file=sys.stderr)
        return 1

    payload = asdict(plan)
    try:
        output_lines = _github_output_lines(payload)
        if args.github_output:
            with args.github_output.open("a") as output:
                output.writelines(output_lines)
    except (OSError, ValueError) as error:
        print(f"error: could not write release-plan output: {error}", file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
