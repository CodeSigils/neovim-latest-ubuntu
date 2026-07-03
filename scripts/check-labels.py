#!/usr/bin/env python3
"""Validate repository labels required by workflow automation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

REQUIRED_LABELS = {
    "dependencies",
    "github-actions",
    "new-release",
    "nightly",
}


def main() -> int:
    """Check GitHub labels through gh using the current workflow token or login."""
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if remote_result.returncode != 0:
            print("FAIL: could not determine repository from git remote", file=sys.stderr)
            print(remote_result.stderr, file=sys.stderr)
            return remote_result.returncode
        match = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?$", remote_result.stdout.strip())
        if not match:
            print("FAIL: origin remote is not a GitHub repository URL")
            return 1
        repository = match.group(1)

    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/labels", "--paginate"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print("FAIL: could not list repository labels with gh api", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return result.returncode

    labels = {item["name"] for item in json.loads(result.stdout)}
    missing = sorted(REQUIRED_LABELS - labels)
    if missing:
        print("FAIL: missing required repository labels: " + ", ".join(missing))
        return 1

    print("PASS: required repository labels exist: " + ", ".join(sorted(REQUIRED_LABELS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
