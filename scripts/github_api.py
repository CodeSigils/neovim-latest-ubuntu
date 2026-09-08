"""Small read-only GitHub CLI API helper used by maintenance reports."""

from __future__ import annotations

import json
import subprocess
import time

MAX_API_ATTEMPTS = 3
API_TIMEOUT_SECONDS = 30
TRANSIENT_ERRORS = ("connection", "timeout", "temporarily", "could not resolve")


def _run(command: list[str], path: str) -> tuple[str | None, str | None]:
    """Run gh with a bounded timeout and return stdout or a retryable error."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=API_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None, f"gh api timed out: {path}"
    if result.returncode == 0:
        return result.stdout, None
    return None, result.stderr.strip() or f"gh api failed: {path}"


def gh_json(path: str) -> dict | list:
    """Fetch JSON with bounded retries for transient CLI/network failures."""
    for attempt in range(MAX_API_ATTEMPTS):
        output, error = _run(["gh", "api", path], path)
        if output is not None:
            try:
                return json.loads(output)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"GitHub returned invalid JSON for {path}: {error}") from error

        assert error is not None
        if not any(term in error.lower() for term in TRANSIENT_ERRORS):
            raise RuntimeError(error)
        if attempt >= MAX_API_ATTEMPTS - 1:
            raise RuntimeError(error)
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def gh_json_pages(path: str) -> list:
    """Fetch every REST page and flatten array responses."""
    for attempt in range(MAX_API_ATTEMPTS):
        output, error = _run(["gh", "api", "--paginate", "--slurp", path], path)
        if output is not None:
            try:
                pages = json.loads(output)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"GitHub returned invalid JSON for {path}: {error}") from error
            if not isinstance(pages, list):
                raise RuntimeError(f"GitHub pagination returned a non-list for {path}")
            flattened: list = []
            for page in pages:
                if not isinstance(page, list):
                    raise RuntimeError(f"GitHub pagination returned a non-array page for {path}")
                flattened.extend(page)
            return flattened

        assert error is not None
        if not any(term in error.lower() for term in TRANSIENT_ERRORS):
            raise RuntimeError(error)
        if attempt >= MAX_API_ATTEMPTS - 1:
            raise RuntimeError(error)
        time.sleep(2**attempt)
    raise AssertionError("unreachable")
