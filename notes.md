# Agent notes

## Session: 2026-05-26 — paths-ignore: exclude git metadata, hooks, dependabot

Extended Build's `paths-ignore` with 4 additional file categories that
have zero build impact:

- `.gitignore` and `.gitattributes` — git configuration only
- `.githooks/**` — local git hooks
- `.github/dependabot.yml` — Dependabot service config

Patched build.yml, CHANGELOG.md, AGENTS.md (CI efficiency + decision log),
docs/build-plan.md (table + §8.1).

Pushing only these changes (no non-excluded files touched) will **not**
trigger a Build — only Staleness, CodeQL, and Author Attribution will run.
