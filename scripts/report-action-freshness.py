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
    """Return the SHA for the highest semantic tag in the requested major line."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "neovim-latest-ubuntu-action-freshness",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    }
    candidates: list[tuple[tuple[int, int, int], str]] = []
    for page in range(1, 21):
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/tags?per_page=100&page={page}",
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            tags = json.load(response)
        if not tags:
            break
        for tag in tags:
            name = tag.get("name", "")
            match = re.fullmatch(
                rf"v{re.escape(major)}\.(\d+)(?:\.(\d+))?(?:[-+].*)?", name
            )
            if match:
                minor = int(match.group(1))
                patch = int(match.group(2) or 0)
                candidates.append(((int(major), minor, patch), tag["commit"]["sha"]))
    if not candidates:
        raise ValueError(f"no tag found for major v{major}")
    return max(candidates, key=lambda item: item[0])[1]


def main() -> int:
    token = os.environ.get("GH_TOKEN", "")
    entries: list[tuple[str, str, str, str]] = []
    for path in sorted(Path(".github").rglob("*.yml")):
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            match = PINNED.search(line)
            if match:
                entries.append((str(path), str(line_number), *match.groups()))

    rows: list[str] = []
    latest_cache: dict[tuple[str, str], str | Exception] = {}
    unknown_count = 0
    for path, line, repo, pinned, major in entries:
        cache_key = (repo, major)
        if cache_key not in latest_cache:
            try:
                latest_cache[cache_key] = latest_sha(repo, major, token)
            except (OSError, ValueError, KeyError, urllib.error.HTTPError) as error:
                latest_cache[cache_key] = error
        result = latest_cache[cache_key]
        if isinstance(result, Exception):
            unknown_count += 1
            rows.append(f"| `{repo}` | `{major}` | unknown | `{path}:{line}` ({result}) |")
            continue
        latest = result
        state = "current" if pinned == latest else "update available"
        rows.append(f"| `{repo}` | `{major}` | {state} | `{path}:{line}` |")

    output = "## GitHub Action freshness\n\n| Action | Major | Status | Location |\n|---|---:|---|---|\n"
    output += "\n".join(rows) if rows else "No pinned actions found."
    if unknown_count:
        output += (
            f"\n\n> Warning: freshness could not be verified for {unknown_count} action reference(s) "
            "because the GitHub API was unavailable or rate-limited."
        )
    print(output)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(output + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
