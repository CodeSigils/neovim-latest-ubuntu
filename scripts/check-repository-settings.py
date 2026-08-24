#!/usr/bin/env python3
"""Audit remote GitHub settings that release safety depends on."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

REQUIRED_LABELS = {"dependencies", "github-actions", "new-release", "nightly"}
REQUIRED_VARIABLES = {
    "RUNNER_AARCH64",
    "RUNNER_X86_64",
    "UBUNTU_CODENAME",
    "UBUNTU_SHA256",
    "UBUNTU_VERSION",
}


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def repository_name() -> str:
    repository = os.environ.get("GITHUB_REPOSITORY")
    if repository:
        return repository
    result = run(["git", "remote", "get-url", "origin"])
    if result.returncode != 0:
        raise RuntimeError(f"could not read origin remote: {result.stderr.strip()}")
    match = re.search(r"github[.]com[:/]([^/]+/[^/.]+)(?:[.]git)?$", result.stdout.strip())
    if not match:
        raise RuntimeError("origin remote is not a GitHub repository URL")
    return match.group(1)


def gh_json(path: str) -> dict | list:
    command = ["gh", "api", path]
    result = run(command)
    if result.returncode != 0:
        raise RuntimeError(f"GitHub API request failed for {path}: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"GitHub returned invalid JSON for {path}: {error}") from error


def audit(
    repository: str, variables: set[str], immutable_releases_enabled: bool | None
) -> list[str]:
    errors: list[str] = []

    label_data = gh_json(f"repos/{repository}/labels?per_page=100")
    labels = {label["name"] for label in label_data}
    missing_labels = sorted(REQUIRED_LABELS - labels)
    if missing_labels:
        errors.append("missing labels: " + ", ".join(missing_labels))

    missing_variables = sorted(REQUIRED_VARIABLES - variables)
    if missing_variables:
        errors.append("missing Actions variables: " + ", ".join(missing_variables))

    release_auto = gh_json(f"repos/{repository}/environments/release-auto")
    if release_auto.get("protection_rules"):
        errors.append("release-auto must not have deployment protection rules")

    release_reviewed = gh_json(f"repos/{repository}/environments/release-reviewed")
    review_rules = [
        rule
        for rule in release_reviewed.get("protection_rules", [])
        if rule.get("type") == "required_reviewers"
    ]
    if not review_rules or not review_rules[0].get("reviewers"):
        errors.append("release-reviewed must require at least one reviewer")

    if immutable_releases_enabled is False:
        errors.append("immutable releases must be enabled")

    return errors


def main() -> int:
    try:
        repository = repository_name()
        if os.environ.get("GITHUB_ACTIONS") == "true":
            variables = {
                name for name in REQUIRED_VARIABLES if os.environ.get(f"REPOSITORY_VARIABLE_{name}")
            }
            immutable_releases_enabled = None
        else:
            variable_data = gh_json(f"repos/{repository}/actions/variables")
            variables = {item["name"] for item in variable_data["variables"]}
            immutable_data = gh_json(f"repos/{repository}/immutable-releases")
            immutable_releases_enabled = immutable_data.get("enabled") is True
        errors = audit(repository, variables, immutable_releases_enabled)
    except (KeyError, RuntimeError, TypeError) as error:
        print(f"FAIL: could not audit repository settings: {error}", file=sys.stderr)
        return 1

    if errors:
        print("FAIL: repository settings drift detected:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    checked = "labels, Actions variables, and release environments"
    if immutable_releases_enabled is not None:
        checked += ", plus immutable-release enforcement"
    print(f"PASS: configured {checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
