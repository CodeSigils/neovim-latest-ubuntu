# notes.md — Agent scratchpad

## 2026-05-26 — Doc drift cleanup + nightly auto-close

### Doc drifts fixed
1. build-plan.md §5 — Added `.mailmap` to paths-ignore table
2. build-plan.md §5 — Added `workflow_dispatch` trigger row
3. build-plan.md §5 — Lint description expanded to all 5 checks
4. README.md — Added `docs/reproducibility.md` link

### Nightly improvement
Added `report-success` job to nightly.yml: auto-closes nightly failure
issue when the build recovers. Closes the feedback loop — old failure
issues don't linger and new failures always get a fresh issue.

### Current CI architecture
- **build.yml**: Stable/tagged releases, push/PR/schedule/dispatch
- **nightly.yml**: Master builds, schedule daily + dispatch only, lint + build + report-failure + report-success
- **staleness.yml**: AGENTS.md drift guard, fires on every main push
- **check-author.yml**: Canonical authorship enforcement, fires on every main push
- **codeql.yml**: Security analysis, push/PR/schedule
- **check-upstream.yml**: New release detection, weekly schedule

### Upstream release watch
- check-upstream.yml runs weekly (Mon 06:30 UTC)
- On detection: auto-creates PR with version bump
