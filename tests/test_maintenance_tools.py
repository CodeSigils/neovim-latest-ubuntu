"""Tests for low-cost documentation and dependency-maintenance tools."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_script(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


markdown_links = load_script("markdown_links", "check-markdown-links.py")
action_freshness = load_script("action_freshness", "report-action-freshness.py")


class MaintenanceToolTests(unittest.TestCase):
    def test_markdown_enumeration_respects_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init", "-q", root], check=True)
            (root / ".gitignore").write_text("cache/\n")
            (root / "tracked.md").write_text("tracked\n")
            (root / "visible.md").write_text("visible\n")
            (root / "cache").mkdir()
            (root / "cache" / "ignored.md").write_text("ignored\n")
            subprocess.run(["git", "-C", root, "add", "tracked.md"], check=True)
            previous = Path.cwd()
            try:
                os.chdir(root)
                paths = markdown_links.markdown_paths()
            finally:
                os.chdir(previous)

        self.assertEqual(paths, [Path("tracked.md"), Path("visible.md")])

    def test_action_freshness_accepts_only_stable_tags(self) -> None:
        self.assertEqual(action_freshness.stable_tag_version("v7.2.1", "7"), (7, 2, 1))
        self.assertEqual(action_freshness.stable_tag_version("v7.2", "7"), (7, 2, 0))
        self.assertIsNone(action_freshness.stable_tag_version("v7.3.0-rc.1", "7"))
        self.assertIsNone(action_freshness.stable_tag_version("v8.0.0", "7"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
