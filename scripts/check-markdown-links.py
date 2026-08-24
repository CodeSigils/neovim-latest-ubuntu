#!/usr/bin/env python3
"""Validate relative Markdown links resolve within the repository."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


def markdown_paths() -> list[Path]:
    """Return tracked and unignored untracked Markdown files."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return sorted(Path(raw.decode()) for raw in result.stdout.split(b"\0") if raw)


def main() -> int:
    root = Path.cwd().resolve()
    errors: list[str] = []
    try:
        paths = markdown_paths()
    except RuntimeError as error:
        print(f"FAIL: could not enumerate Markdown files: {error}", file=sys.stderr)
        return 1
    for path in sorted(paths):
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            for raw_target in re.findall(r"\[[^]]+\]\(([^)]+)\)", line):
                target = unquote(raw_target.split("#", 1)[0].split("?", 1)[0].strip("<>"))
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(root):
                    errors.append(
                        f"{path}:{line_number}: relative link escapes repository {target}"
                    )
                elif not resolved.exists():
                    errors.append(f"{path}:{line_number}: missing relative link {target}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("PASS: all relative Markdown links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
