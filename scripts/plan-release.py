#!/usr/bin/env python3
"""Resolve an exact upstream source and decide whether CI should publish it."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

STABLE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([1-9]\d*))?$")
CORE_ASSETS = {"nvim-linux-x86_64.deb", "nvim-linux-arm64.deb", "SHA256SUMS"}
REQUIRED_ASSETS = CORE_ASSETS | {
    "BUILD-METADATA-amd64.json",
    "BUILD-METADATA-arm64.json",
    "SBOM-amd64.spdx.json",
    "SBOM-arm64.spdx.json",
}
# This release predates metadata/SBOM publication. Keep its historical contract
# explicit without weakening validation for new releases.
LEGACY_RELEASE_ASSETS = {"v0.12.5": CORE_ASSETS}
HTTP_NOT_FOUND = 404


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
    requires_review: bool
    should_build: bool
    source_commit: str
    tag: str
    version: str


def parse_version(value: str) -> Version:
    match = STABLE.fullmatch(value)
    if not match:
        raise ValueError("expected a stable X.Y.Z or package-revision X.Y.Z-N version")
    major, minor, patch, revision = match.groups()
    base = f"{major}.{minor}.{patch}"
    suffix = f"-{revision}" if revision else ""
    return Version(base, f"v{base}{suffix}", revision or "", int(patch) == 0)


class GitHub:
    def __init__(self, token: str) -> None:
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "neovim-latest-ubuntu-release-planner",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        }

    def get(self, path: str) -> dict:
        request = urllib.request.Request(f"https://api.github.com/{path}", headers=self.headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def optional(self, path: str) -> dict | None:
        try:
            return self.get(path)
        except urllib.error.HTTPError as error:
            if error.code == HTTP_NOT_FOUND:
                return None
            raise


def upstream_commit(client: GitHub, tag: str) -> str:
    encoded = urllib.parse.quote(tag, safe="")
    reference = client.get(f"repos/neovim/neovim/git/ref/tags/{encoded}")["object"]
    for _ in range(4):
        if reference["type"] == "commit":
            sha = reference["sha"]
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
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
    required_assets = LEGACY_RELEASE_ASSETS.get(tag, REQUIRED_ASSETS)
    return all(
        name in assets
        and assets[name].get("state") == "uploaded"
        and assets[name].get("size", 0) > 0
        for name in required_assets
    )


def make_plan(
    *,
    client: GitHub,
    mode: str,
    requested: str,
    publish_requested: bool,
    repository: str,
) -> Plan:
    if requested in ("", "latest"):
        upstream = client.get("repos/neovim/neovim/releases/latest")
        requested = upstream.get("tag_name", "")
    version = parse_version(requested)

    # Explicit versions must correspond to an actual upstream stable release.
    upstream_tag = f"v{version.base}"
    encoded = urllib.parse.quote(upstream_tag, safe="")
    release = client.optional(f"repos/neovim/neovim/releases/tags/{encoded}")
    if not release or release.get("draft") or release.get("prerelease"):
        raise ValueError(f"{upstream_tag} is not a published upstream stable release")

    publish = mode in {"scheduled", "tag"} or publish_requested
    complete = release_is_complete(client, repository, version.tag)
    should_build = not (publish and complete)
    reason = (
        "release already published with required assets" if not should_build else "build candidate"
    )
    return Plan(
        package_revision=version.package_revision,
        publish=publish,
        reason=reason,
        requires_review=publish and version.feature_release,
        should_build=should_build,
        source_commit=upstream_commit(client, upstream_tag),
        tag=version.tag,
        version=version.base,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("ci", "scheduled", "manual", "tag"), required=True)
    parser.add_argument("--version", default="latest")
    parser.add_argument("--publish", action="store_true")
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
            client=GitHub(os.environ.get("GH_TOKEN", "")),
            mode=args.mode,
            requested=args.version,
            publish_requested=args.publish,
            repository=args.repository,
        )
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: could not create release plan: {error}", file=sys.stderr)
        return 1

    payload = asdict(plan)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.github_output:
        with args.github_output.open("a") as output:
            for key, value in payload.items():
                rendered = str(value).lower() if isinstance(value, bool) else value
                output.write(f"{key}={rendered}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
