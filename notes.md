# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md).
Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## Active

- None.

## Done

- History squashed to 1 root commit. Only author: CodeSigils.
- v0.12.2 built, packaged, released. CI pipeline fully operational (build, test, lint, release, nightly, staleness).
- Release uses upstream best-practice template: version summary, install guide, integrity verification, upstream changelog links.
- Dependabot configured and running (actions/dependency bumps).
- Author attribution guard: email-based, skips dependabot[bot] and GitHub merge committer.
- .mailmap consolidates agent and merge commit identities.
- `paths-ignore` on push trigger: doc-only pushes skip builds.
- Branch protection (ruleset): deletion + non_fast_forward only.
