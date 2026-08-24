#!/usr/bin/env python3
"""Verify that release packages and metadata describe one coherent candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_metadata import ARTIFACTS, BuildInputs, build_metadata, file_sha256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("."))
    parser.add_argument("--version", required=True)
    parser.add_argument("--package-revision", default="")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--ubuntu-version", required=True)
    parser.add_argument("--ubuntu-codename", required=True)
    parser.add_argument("--ubuntu-image-digest", required=True)
    parser.add_argument("--checksum-output", type=Path, default=Path("SHA256SUMS"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_version = args.version
    if args.package_revision:
        if not args.package_revision.isdigit() or args.package_revision.startswith("0"):
            print("Release candidate verification failed:", file=sys.stderr)
            print("- package revision must be a positive integer", file=sys.stderr)
            return 1
        package_version += f"-{args.package_revision}"
    inputs = BuildInputs(
        source_version=args.version,
        source_commit=args.source_commit,
        package_version=package_version,
        repository_commit=args.repository_commit,
        ubuntu_version=args.ubuntu_version,
        ubuntu_codename=args.ubuntu_codename,
        ubuntu_image_digest=args.ubuntu_image_digest,
    )
    errors = inputs.validation_errors(allow_nightly=False)
    checksums: list[str] = []

    for architecture, filename in ARTIFACTS.items():
        artifact = args.directory / filename
        metadata_path = args.directory / f"BUILD-METADATA-{architecture}.json"
        if not artifact.is_file():
            errors.append(f"missing artifact: {artifact}")
            continue
        if not metadata_path.is_file():
            errors.append(f"missing metadata: {metadata_path}")
            continue
        try:
            actual = json.loads(metadata_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"could not read {metadata_path}: {error}")
            continue
        expected = build_metadata(inputs, artifact, architecture)
        if actual != expected:
            errors.append(f"metadata does not match candidate inputs: {metadata_path}")
        checksums.append(f"{file_sha256(artifact)}  {artifact.name}")

    if errors:
        print("Release candidate verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    checksum_path = args.checksum_output
    if not checksum_path.is_absolute():
        checksum_path = args.directory / checksum_path
    checksum_path.write_text("\n".join(checksums) + "\n")
    print("PASS: release packages and metadata form one coherent candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
