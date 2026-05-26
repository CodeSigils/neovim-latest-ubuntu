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

## Active

- None.
