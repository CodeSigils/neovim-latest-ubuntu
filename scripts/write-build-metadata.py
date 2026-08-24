#!/usr/bin/env python3
"""Write deterministic, machine-readable provenance metadata for a package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_metadata import ARTIFACTS, BuildInputs, build_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--package-version", required=True)
    parser.add_argument("--ubuntu-version", required=True)
    parser.add_argument("--ubuntu-codename", required=True)
    parser.add_argument("--ubuntu-image-digest", required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def validate(args: argparse.Namespace, inputs: BuildInputs) -> None:
    """Reject incomplete or ambiguous provenance inputs."""
    if not args.artifact.is_file():
        raise ValueError(f"artifact does not exist: {args.artifact}")
    if args.architecture not in ARTIFACTS:
        raise ValueError(f"unsupported architecture: {args.architecture}")
    errors = inputs.validation_errors(allow_nightly=True)
    if errors:
        raise ValueError("; ".join(errors))


def main() -> int:
    args = parse_args()
    inputs = BuildInputs(
        source_version=args.source_version,
        source_commit=args.source_commit,
        package_version=args.package_version,
        repository_commit=args.repository_commit,
        ubuntu_version=args.ubuntu_version,
        ubuntu_codename=args.ubuntu_codename,
        ubuntu_image_digest=args.ubuntu_image_digest,
    )
    try:
        validate(args, inputs)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    metadata = build_metadata(inputs, args.artifact, args.architecture)
    args.output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
