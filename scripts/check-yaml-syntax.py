#!/usr/bin/env python3
"""Validate YAML syntax of all GitHub Actions workflow files.

Returns non-zero exit code if any file has invalid YAML.
Can be extended later to enforce additional conventions."""

import yaml
import sys
import glob

files = sorted(glob.glob(".github/workflows/*.yml"))
errors = 0

for f in files:
    with open(f) as fh:
        try:
            yaml.safe_load(fh)
            print(f"PASS  {f}")
        except yaml.YAMLError as e:
            print(f"FAIL  {f}: {e}")
            errors += 1

if errors:
    sys.exit(f"{errors} workflow YAML file(s) failed validation")
