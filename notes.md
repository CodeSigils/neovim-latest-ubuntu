# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md).
Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## 2026-05-26 — check-upstream.yml: handle revision suffix tags

- `check-upstream.yml` "Get our latest built version" step now strips `-N` suffix
  from the version string before comparing against upstream.
- Without this, a `v0.12.2-1` tag would be read as `0.12.2-1` which differs from
  upstream's `0.12.2`, falsely triggering a new-release PR.
