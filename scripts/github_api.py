"""Small read-only GitHub CLI API helper used by maintenance reports."""

from __future__ import annotations

import json
import subprocess
import time

MAX_API_ATTEMPTS = 3
API_TIMEOUT_SECONDS = 30
TRANSIENT_ERRORS = ("connection", "timeout", "temporarily", "could not resolve")
# gh reports a missing resource in stderr rather than through an exit code that
# distinguishes it from other failures.
NOT_FOUND_MARKER = "HTTP 404"


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


def gh_json_optional(path: str) -> dict | list | None:
    """Fetch JSON, returning None when GitHub reports the resource is missing."""
    try:
        return gh_json(path)
    except RuntimeError as error:
        if NOT_FOUND_MARKER in str(error):
            return None
        raise


def _json_stream(text: str, path: str) -> list:
    """Decode the concatenated JSON documents that `gh api --paginate` emits."""
    decoder = json.JSONDecoder()
    values: list = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        try:
            value, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"GitHub returned invalid JSON for {path}: {error}") from error
        values.append(value)
    return values


def gh_json_pages(path: str) -> list:
    """Fetch every REST page and flatten array responses."""
    for attempt in range(MAX_API_ATTEMPTS):
        output, error = _run(["gh", "api", "--paginate", path], path)
        if output is not None:
            flattened: list = []
            for page in _json_stream(output, path):
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
