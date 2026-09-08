"""Small read-only GitHub CLI API helper used by maintenance reports."""

from __future__ import annotations

import json
import subprocess
import time

MAX_API_ATTEMPTS = 3
TRANSIENT_ERRORS = ("connection", "timeout", "temporarily", "could not resolve")


def gh_json(path: str) -> dict | list:
    """Fetch JSON with bounded retries for transient CLI/network failures."""
    for attempt in range(MAX_API_ATTEMPTS):
        result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"GitHub returned invalid JSON for {path}: {error}") from error

        error = result.stderr.strip() or f"gh api failed: {path}"
        if not any(term in error.lower() for term in TRANSIENT_ERRORS):
            raise RuntimeError(error)
        if attempt >= MAX_API_ATTEMPTS - 1:
            raise RuntimeError(error)
        time.sleep(2**attempt)
    raise AssertionError("unreachable")
