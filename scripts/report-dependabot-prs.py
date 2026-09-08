#!/usr/bin/env python3
"""Report Dependabot PR readiness without mutating branches or pull requests."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

MAX_API_ATTEMPTS = 3
SENSITIVE_PREFIXES = (
    ".github/workflows/build.yml",
    ".github/workflows/package.yml",
    ".github/workflows/nightly.yml",
    ".github/actions/",
    "scripts/",
    "Containerfile",
    "build.sh",
    "test.sh",
)


def gh_json(path: str) -> dict | list:
    for attempt in range(MAX_API_ATTEMPTS):
        result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return json.loads(result.stdout)
        error = result.stderr.strip() or f"gh api failed: {path}"
        lowered = error.lower()
        transient = any(
            term in lowered
            for term in ("connection", "timeout", "temporarily", "could not resolve")
        )
        if not transient or attempt >= MAX_API_ATTEMPTS - 1:
            raise RuntimeError(error)
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def classify(repository: str) -> list[str]:
    pulls = gh_json(f"repos/{repository}/pulls?state=open&per_page=100")
    report: list[str] = []
    for pull in pulls:
        if pull.get("user", {}).get("login") != "dependabot[bot]":
            continue
        number = pull["number"]
        files = gh_json(f"repos/{repository}/pulls/{number}/files?per_page=100")
        names = [item["filename"] for item in files]
        sensitive = [name for name in names if name.startswith(SENSITIVE_PREFIXES)]
        checks = gh_json(
            f"repos/{repository}/commits/{pull['head']['sha']}/check-runs?per_page=100"
        )["check_runs"]
        pending = [check["name"] for check in checks if check.get("status") != "completed"]
        failed = [
            check["name"]
            for check in checks
            if check.get("conclusion") not in ("success", "skipped")
        ]
        if sensitive:
            state = "manual-review-sensitive-path"
        elif pending:
            state = "waiting-for-checks"
        elif failed:
            state = "checks-failed"
        else:
            state = "ready-for-maintainer-merge"
        report.append(f"#{number} {state}: {pull['head']['ref']} (files={len(names)})")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    try:
        report = classify(args.repository)
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: could not classify Dependabot PRs: {error}", file=sys.stderr)
        return 1
    print("Dependabot triage (report only):")
    print("\n".join(f"- {line}" for line in report) or "- no open Dependabot PRs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
