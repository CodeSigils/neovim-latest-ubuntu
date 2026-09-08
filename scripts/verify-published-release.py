#!/usr/bin/env python3
"""Verify the immutable, public release contract after publication.

The GitHub Actions job supplies release and tag JSON obtained with read-only
API calls and a clean directory containing the public assets.  Keeping the
logic fixture-driven makes the remote gate deterministic and easy to test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_ASSETS = {
    "nvim-linux-x86_64.deb",
    "nvim-linux-arm64.deb",
    "SHA256SUMS",
    "BUILD-METADATA-amd64.json",
    "BUILD-METADATA-arm64.json",
    "SBOM-amd64.spdx.json",
    "SBOM-arm64.spdx.json",
}
SHA_RE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def verify(  # noqa: PLR0912
    *, release: dict, tag: dict, asset_dir: Path, expected_tag: str, expected_commit: str
) -> None:
    if release.get("tag_name") != expected_tag:
        raise ValueError("release tag does not match the planned tag")
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("release is still draft or prerelease")
    if "immutable" in release and release["immutable"] is not True:
        raise ValueError("GitHub reports the release is mutable")
    if release.get("target_commitish") not in (None, "", expected_commit):
        raise ValueError("release target commit does not match the workflow commit")

    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("release payload has no asset list")
    names = {item.get("name") for item in assets if isinstance(item, dict)}
    if names != EXPECTED_ASSETS:
        raise ValueError(f"unexpected release assets: {sorted(names ^ EXPECTED_ASSETS)}")
    if any(item.get("state") != "uploaded" or item.get("size", 0) <= 0 for item in assets):
        raise ValueError("release contains an incomplete or empty asset")

    tag_object = tag.get("object", {})
    if tag_object.get("type") != "commit" or tag_object.get("sha") != expected_commit:
        raise ValueError("tag does not resolve directly to the published workflow commit")

    checksum_file = asset_dir / "SHA256SUMS"
    lines = checksum_file.read_text().splitlines()
    seen: set[str] = set()
    for line in lines:
        match = SHA_RE.fullmatch(line)
        if not match:
            raise ValueError(f"invalid checksum line: {line!r}")
        digest, name = match.groups()
        if name not in {"nvim-linux-x86_64.deb", "nvim-linux-arm64.deb"} or name in seen:
            raise ValueError(f"invalid checksum entry: {name}")
        path = asset_dir / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"checksum mismatch for {name}")
        seen.add(name)
    if seen != {"nvim-linux-x86_64.deb", "nvim-linux-arm64.deb"}:
        raise ValueError("SHA256SUMS does not cover both packages")

    local_names = {path.name for path in asset_dir.iterdir() if path.is_file()}
    if local_names != EXPECTED_ASSETS:
        raise ValueError(f"downloaded asset set differs from release: {sorted(local_names ^ EXPECTED_ASSETS)}")


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
