#!/usr/bin/env python3
"""Validate YAML syntax of all GitHub Actions workflow files.

Returns non-zero exit code if any file has invalid YAML.
Can be extended later to enforce additional conventions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def main() -> int:
    """Check all workflow YAML files parse correctly."""
    errors = 0
    for path in sorted(Path(".github/workflows").glob("*.yml")):
        with path.open() as fh:
            try:
                yaml.safe_load(fh)
                print(f"PASS  {path}")
            except yaml.YAMLError as e:
                print(f"FAIL  {path}: {e}")
                errors += 1

    if errors:
        print(f"{errors} workflow YAML file(s) failed validation", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
