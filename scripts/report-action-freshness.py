#!/usr/bin/env python3
"""Report pinned GitHub Action SHAs that lag their major-version branch."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PINNED = re.compile(
    r"uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{40})\s+#\s*v?([0-9]+)"
)


def latest_sha(repo: str, major: str, token: str) -> str:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/commits/{major}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "neovim-latest-ubuntu-action-freshness",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)["sha"]


def main() -> int:
    token = os.environ.get("GH_TOKEN", "")
    entries: list[tuple[str, str, str, str]] = []
    for path in sorted(Path(".github").rglob("*.yml")):
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            match = PINNED.search(line)
            if match:
                entries.append((str(path), str(line_number), *match.groups()))

    rows: list[str] = []
    for path, line, repo, pinned, major in entries:
        try:
            latest = latest_sha(repo, major, token)
        except (OSError, ValueError, KeyError, urllib.error.HTTPError) as error:
            rows.append(f"| `{repo}` | `{major}` | unknown | `{path}:{line}` ({error}) |")
            continue
        state = "current" if pinned == latest else "update available"
        rows.append(f"| `{repo}` | `{major}` | {state} | `{path}:{line}` |")

    output = "## GitHub Action freshness\n\n| Action | Major | Status | Location |\n|---|---:|---|---|\n"
    output += "\n".join(rows) if rows else "No pinned actions found."
    print(output)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(output + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
