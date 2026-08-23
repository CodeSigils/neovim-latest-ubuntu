#!/usr/bin/env python3
"""Validate relative Markdown links resolve within the repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    errors: list[str] = []
    for path in sorted(Path(".").rglob("*.md")):
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", line):
                target = target.split("#", 1)[0].strip("<>")
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                if not (path.parent / target).resolve().exists():
                    errors.append(f"{path}:{line_number}: missing relative link {target}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("PASS: all relative Markdown links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
