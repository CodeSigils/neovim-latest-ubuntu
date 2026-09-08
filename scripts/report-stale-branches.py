#!/usr/bin/env python3
"""Report remote branches with no open PR and no recent commit.

This is deliberately report-only. Deletion remains an explicit maintainer or
post-merge repository setting, never an automated action from this workflow.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time

MAX_API_ATTEMPTS = 3


def gh_json(path: str) -> list | dict:
    for attempt in range(MAX_API_ATTEMPTS):
        result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return json.loads(result.stdout)
        error = result.stderr.strip() or f"gh api failed: {path}"
        lowered = error.lower()
        transient = any(term in lowered for term in ("connection", "timeout", "temporarily", "could not resolve"))
        if not transient or attempt >= MAX_API_ATTEMPTS - 1:
            raise RuntimeError(error)
        time.sleep(2**attempt)


def report(repository: str, days: int) -> list[str]:
    branches = gh_json(f"repos/{repository}/branches?per_page=100")
    pulls = gh_json(f"repos/{repository}/pulls?state=open&per_page=100")
    open_heads = {item["head"]["ref"] for item in pulls}
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
    stale: list[str] = []
    for branch in branches:
        name = branch["name"]
        if name == "main" or name in open_heads:
            continue
        commit = gh_json(f"repos/{repository}/commits/{branch['commit']['sha']}")
        date = commit["commit"]["committer"]["date"]
        if dt.datetime.fromisoformat(date.replace("Z", "+00:00")) < cutoff:
            stale.append(f"{name} (last commit {date})")
    return stale


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")
    try:
        stale = report(args.repository, args.days)
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: could not inspect branches: {error}", file=sys.stderr)
        return 1
    if stale:
        print("Stale branches (report only):")
        print("\n".join(f"- {item}" for item in stale))
    else:
        print(f"PASS: no branch without an open PR has been inactive for {args.days} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
