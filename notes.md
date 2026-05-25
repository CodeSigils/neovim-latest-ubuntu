# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md).
Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## Active

- None.

## Done

- v0.12.2 built, packaged, released. CI pipeline fully operational (build, test, lint, release, staleness, nightly).
- Dependabot bumps merged (actions/download-artifact 7→8, actions/github-script 7→9).
- Author attribution guard hardened: uses email as authoritative identifier, skips dependabot[bot] and GitHub merge committer.
- .mailmap added mapping agent identities to canonical author.
- `paths-ignore` on push trigger: doc-only pushes skip builds.
