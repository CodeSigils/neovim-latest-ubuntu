# notes.md — Agent scratchpad

## 2026-05-26 — Doc drift cleanup + nightly auto-close + CodeQL perf

### Doc drifts fixed
1. build-plan.md §5 — Added `.mailmap` to paths-ignore table
2. build-plan.md §5 — Added `workflow_dispatch` trigger row
3. build-plan.md §5 — Lint description expanded to all 5 checks
4. README.md — Added `docs/reproducibility.md` link

### Nightly improvement
Added `report-success` job to nightly.yml: auto-closes nightly failure
issue when the build recovers. Closes the feedback loop.

### CodeQL performance
Added paths-ignore to skip doc-only pushes (same patterns as build.yml).
Switched from `security-and-quality` to `security-extended` query suite.
Added CLI caching via actions/cache for ~10-15s saving.

Also added `codeql.yml` to build.yml's paths-ignore — editing it has
zero build impact (independent push/PR/schedule triggers).

### Current paths-ignore (build.yml)
*.md, LICENSE, docs/**, .gitignore, .gitattributes, .mailmap,
.githooks/**, .github/dependabot.yml, nightly.yml, staleness.yml,
check-author.yml, codeql.yml

### Current CI architecture
- **build.yml**: Stable/tagged releases, push/PR/schedule/dispatch
- **nightly.yml**: Master builds, schedule daily + dispatch only, lint + build + report-failure + report-success
- **staleness.yml**: AGENTS.md drift guard, fires on every main push
- **check-author.yml**: Canonical authorship enforcement, fires on every main push
- **codeql.yml**: Security analysis, push/PR/schedule (config skip via paths-ignore)
- **check-upstream.yml**: New release detection, weekly schedule

### Upstream release watch
- check-upstream.yml runs weekly (Mon 06:30 UTC)
- On detection: auto-creates PR with version bump
