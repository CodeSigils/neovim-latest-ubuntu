#!/usr/bin/env python3
"""Check dependency lists stay aligned across README, container image, and scripts.

Ensures that:
- README prerequisites match deps/ubuntu-build-deps.txt exactly
- All build scripts reference packages that exist in the manifests
- Containerfile installs from the manifest files
- No overlap between build and CI-extra manifests
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
BUILD_SH = REPO / "build.sh"
TEST_SH = REPO / "test.sh"
CONTAINERFILE = REPO / "Containerfile"
BUILD_DEPS = REPO / "deps" / "ubuntu-build-deps.txt"
CI_EXTRA_DEPS = REPO / "deps" / "ubuntu-ci-extra-deps.txt"


def load_dep_file(path: Path) -> list[str]:
    """Load a dependency manifest, skipping blank lines and comments."""
    items: list[str] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


def parse_readme_manual_deps() -> list[str]:
    """Extract the apt install package list from the README prerequisites block."""
    text = README.read_text()
    heading = re.search(r"^### Prerequisites$", text, re.MULTILINE)
    if not heading:
        raise SystemExit("FAIL: Could not find README prerequisites heading")
    snippet = text[heading.end() : heading.end() + 500]
    match = re.search(
        r"```bash\nsudo apt install (?P<deps>[^\n]+)\n```",
        snippet,
        re.MULTILINE,
    )
    if not match:
        raise SystemExit("FAIL: Could not find README prerequisites apt install block")
    return match.group("deps").split()


def ensure(condition: bool, message: str, errors: list[str]) -> None:
    """Append message to errors if condition is False."""
    if not condition:
        errors.append(message)


def main() -> int:
    """Run all dependency consistency checks, return 0 on pass."""
    errors: list[str] = []

    build_deps = load_dep_file(BUILD_DEPS)
    ci_extra_deps = load_dep_file(CI_EXTRA_DEPS)
    readme_deps = parse_readme_manual_deps()
    readme_set = set(readme_deps)
    build_set = set(build_deps)
    ci_extra_set = set(ci_extra_deps)

    ensure(
        readme_deps == build_deps,
        (
            "FAIL: README prerequisites do not exactly match deps/ubuntu-build-deps.txt\n"
            f"  README: {readme_deps}\n"
            f"  deps:   {build_deps}"
        ),
        errors,
    )

    build_sh_text = BUILD_SH.read_text()
    test_sh_text = TEST_SH.read_text()
    container_text = CONTAINERFILE.read_text()

    ensure(
        "git clone" in build_sh_text,
        "FAIL: build.sh no longer uses git clone; revisit host build deps",
        errors,
    )
    ensure(
        "git" in build_set,
        "FAIL: git is required by build.sh but missing from ubuntu-build-deps.txt",
        errors,
    )
    ensure(
        "sudo " in test_sh_text,
        "FAIL: test.sh no longer uses sudo; revisit CI extra deps",
        errors,
    )
    ensure(
        "sudo" in ci_extra_set,
        "FAIL: sudo is required by test.sh but missing from ubuntu-ci-extra-deps.txt",
        errors,
    )

    ensure(
        "COPY deps/ /tmp/deps/" in container_text,
        "FAIL: Containerfile must copy deps/ manifests into the image",
        errors,
    )
    ensure(
        "ubuntu-build-deps.txt" in container_text,
        "FAIL: Containerfile must install deps/ubuntu-build-deps.txt",
        errors,
    )
    ensure(
        "ubuntu-ci-extra-deps.txt" in container_text,
        "FAIL: Containerfile must install deps/ubuntu-ci-extra-deps.txt",
        errors,
    )

    overlap = sorted(build_set & ci_extra_set)
    ensure(
        not overlap,
        f"FAIL: dependency manifests overlap unexpectedly: {overlap}",
        errors,
    )

    combined = build_set | ci_extra_set
    ensure(
        readme_set <= combined,
        "FAIL: README packages must be a subset of combined dependency manifests",
        errors,
    )

    if errors:
        print("\n".join(errors))
        return 1

    print("PASS: dependency manifests, README prerequisites, Containerfile, build.sh, and test.sh are aligned.")
    print(f"  manual build deps: {', '.join(build_deps)}")
    print(f"  CI extra deps: {', '.join(ci_extra_deps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
