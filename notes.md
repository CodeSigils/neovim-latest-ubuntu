# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md).
Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## 2026-05-26 — CI trigger optimizations + check-upstream fix

- Added `staleness.yml`, `check-author.yml`, `.mailmap` to Build's
  `paths-ignore` so editing these files doesn't trigger the full build.
  Each excluded workflow has its own `on.push` trigger.
- Fixed `check-upstream.yml` version comparison to strip `-N` suffix
  before comparing against upstream tags.
- Enabled delete-branch-on-merge in repo settings.
