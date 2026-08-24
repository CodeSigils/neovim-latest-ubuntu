"""Unit tests for release-critical GitHub settings policy."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "repository_settings", REPO / "scripts/check-repository-settings.py"
)
assert SPEC and SPEC.loader
repository_settings = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = repository_settings
SPEC.loader.exec_module(repository_settings)


def configured_response(path: str) -> dict | list:
    if "/labels?" in path:
        return [{"name": name} for name in repository_settings.REQUIRED_LABELS]
    if path.endswith("/environments/release-auto"):
        return {"protection_rules": []}
    if path.endswith("/environments/release-reviewed"):
        return {
            "protection_rules": [{"type": "required_reviewers", "reviewers": [{"type": "User"}]}]
        }
    raise AssertionError(f"unexpected API path: {path}")


class RepositorySettingsTests(unittest.TestCase):
    def test_expected_configuration_passes(self) -> None:
        with patch.object(repository_settings, "gh_json", side_effect=configured_response):
            self.assertEqual(
                repository_settings.audit(
                    "owner/repo", repository_settings.REQUIRED_VARIABLES, True
                ),
                [],
            )

    def test_release_protection_and_immutability_drift_are_reported(self) -> None:
        def drifted(path: str) -> dict | list:
            result = configured_response(path)
            if path.endswith("/environments/release-reviewed"):
                return {"protection_rules": []}
            return result

        with patch.object(repository_settings, "gh_json", side_effect=drifted):
            errors = repository_settings.audit(
                "owner/repo", repository_settings.REQUIRED_VARIABLES, False
            )

        self.assertIn("release-reviewed must require at least one reviewer", errors)
        self.assertIn("immutable releases must be enabled", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
