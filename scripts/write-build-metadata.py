#!/usr/bin/env python3
"""Write deterministic, machine-readable provenance metadata for a package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--package-revision", default="")
    parser.add_argument("--ubuntu-version", required=True)
    parser.add_argument("--ubuntu-codename", required=True)
    parser.add_argument("--ubuntu-image-digest", required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    package_version = args.source_version
    if args.package_revision:
        package_version += f"-{args.package_revision}"
    metadata = {
        "artifact": {
            "architecture": args.architecture,
            "name": args.artifact.name,
            "sha256": sha256(args.artifact),
        },
        "build_environment": {
            "ubuntu_codename": args.ubuntu_codename,
            "ubuntu_image_digest": f"sha256:{args.ubuntu_image_digest}",
            "ubuntu_version": args.ubuntu_version,
        },
        "package_version": package_version,
        "packaging_repository_commit": args.repository_commit,
        "schema_version": 1,
        "upstream": {
            "commit": args.source_commit or None,
            "repository": "https://github.com/neovim/neovim",
            "tag": f"v{args.source_version}",
        },
    }
    args.output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
