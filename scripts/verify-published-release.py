#!/usr/bin/env python3
"""Verify the immutable, public release contract after publication.

The GitHub Actions job supplies release and tag JSON obtained with read-only
API calls and a clean directory containing the public assets.  Keeping the
logic fixture-driven makes the remote gate deterministic and easy to test.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import release_metadata

SHA_RE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def verify_release_identity(release: dict, *, expected_tag: str, expected_commit: str) -> None:
    if release.get("tag_name") != expected_tag:
        raise ValueError("release tag does not match the planned tag")
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("release is still draft or prerelease")
    if release.get("immutable") is not True:
        raise ValueError("GitHub does not confirm that the release is immutable")
    if release.get("target_commitish") not in (None, "", expected_commit):
        raise ValueError("release target commit does not match the workflow commit")


def verify_remote_assets(release: dict) -> None:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("release payload has no asset list")
    if not all(isinstance(item, dict) and isinstance(item.get("name"), str) for item in assets):
        raise ValueError("release payload contains an invalid asset entry")
    names = {item["name"] for item in assets}
    if names != release_metadata.REQUIRED_RELEASE_ASSETS:
        raise ValueError(
            f"unexpected release assets: {sorted(names ^ release_metadata.REQUIRED_RELEASE_ASSETS)}"
        )
    if len(assets) != len(release_metadata.REQUIRED_RELEASE_ASSETS):
        raise ValueError("release contains duplicate assets")
    if any(
        item.get("state") != "uploaded" or type(size := item.get("size")) is not int or size <= 0
        for item in assets
    ):
        raise ValueError("release contains an incomplete or empty asset")


def verify_tag(tag: dict, expected_commit: str) -> None:
    tag_object = tag.get("object", {})
    if (
        not isinstance(tag_object, dict)
        or tag_object.get("type") != "commit"
        or tag_object.get("sha") != expected_commit
    ):
        raise ValueError("tag does not resolve directly to the published workflow commit")


def verify_checksums(asset_dir: Path) -> None:
    lines = (asset_dir / release_metadata.CHECKSUMS_FILE).read_text().splitlines()
    seen: set[str] = set()
    for line in lines:
        match = SHA_RE.fullmatch(line)
        if not match:
            raise ValueError(f"invalid checksum line: {line!r}")
        digest, name = match.groups()
        if name not in release_metadata.DEB_ASSETS or name in seen:
            raise ValueError(f"invalid checksum entry: {name}")
        path = asset_dir / name
        if not path.is_file() or release_metadata.file_sha256(path) != digest:
            raise ValueError(f"checksum mismatch for {name}")
        seen.add(name)
    if seen != release_metadata.DEB_ASSETS:
        raise ValueError("SHA256SUMS does not cover both packages")


def verify_downloaded_assets(asset_dir: Path) -> None:
    local_names = {path.name for path in asset_dir.iterdir() if path.is_file()}
    if local_names != release_metadata.REQUIRED_RELEASE_ASSETS:
        raise ValueError(
            "downloaded asset set differs from release: "
            f"{sorted(local_names ^ release_metadata.REQUIRED_RELEASE_ASSETS)}"
        )


def verify(
    *, release: dict, tag: dict, asset_dir: Path, expected_tag: str, expected_commit: str
) -> None:
    verify_release_identity(release, expected_tag=expected_tag, expected_commit=expected_commit)
    verify_remote_assets(release)
    verify_tag(tag, expected_commit)
    verify_checksums(asset_dir)
    verify_downloaded_assets(asset_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-json", type=Path, required=True)
    parser.add_argument("--tag-json", type=Path, required=True)
    parser.add_argument("--asset-dir", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        verify(
            release=read_json(args.release_json),
            tag=read_json(args.tag_json),
            asset_dir=args.asset_dir,
            expected_tag=args.tag,
            expected_commit=args.commit,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: published release verification failed: {error}", file=sys.stderr)
        return 1
    print(f"verified published release {args.tag} ({args.commit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
