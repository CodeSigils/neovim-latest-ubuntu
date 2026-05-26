# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md).
Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## 2026-05-25 — Release version policy note

- Documented that GitHub Releases currently track upstream Neovim tags exactly.
- Existing tags/releases are immutable; do not reuse `v0.12.2` for rebuilds.
- Packaging suffix tags require explicit package-revision support before use.

## 2026-05-25 — Release readiness gate

- Added `scripts/check-release-readiness.sh` as a read-only pre-tag gate.
- Added `tests/test_release_readiness.py` and wired it into the build workflow lint job.

## 2026-05-26 — Mock values in test_release_readiness.py

- Confirmed: mock values for UBUNTU_VERSION and UBUNTU_CODENAME are placeholders, not assertions.
- The script only checks that repo variables EXIST, not their values — no need for abstraction.
- Added clarifying comment to the mock so nobody worries about stale values.

## 2026-05-26 — Package revision suffix support

- Updated `scripts/check-release-readiness.sh` to accept `X.Y.Z-N` version format (strips suffix for upstream comparison, uses BASE_VERSION for build.sh/CHANGELOG checks).
- Added test `test_package_revision_suffix_accepted` to `tests/test_release_readiness.py`.
- Updated `.github/workflows/build.yml` version extraction: strips `-N` suffix before passing to container; adds upstream tag extraction step for release body link.
- Updated AGENTS.md §8.3 Version Parameterization, Decision Log, and Last updated date.
- Updated RELEASING.md tag policy to document the two supported formats.
- Added CHANGELOG.md entry under [Unreleased] > Added.
