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
- Added paths-ignore to push trigger (doc/metadata only — NOT workflows)
- Switched from `security-and-quality` to `security-extended` query suite
- Removed speculative CLI caching (wrong path, uncertain benefit)
- IMPORTANT: Must NOT exclude workflow files from CodeQL paths-ignore.
  CodeQL exists to analyze workflow files for security issues. Excluding
  them defeats the purpose. Only doc/metadata files.

### Bug caught: CodeQL v1 paths-ignore was too aggressive
Original setup copied build.yml's paths-ignore verbatim, which excluded
all `.github/workflows/*.yml` files. This meant CodeQL would skip analysis
whenever a workflow file changed — the opposite of what it should do.
Fixed in v2: only `*.md`, `LICENSE`, `docs/**`, `.gitignore`,
`.gitattributes`, `.githooks/**`, `.mailmap`, `.github/dependabot.yml`.

### Current paths-ignore (build.yml)
All *.md, LICENSE, docs/**, .gitignore, .gitattributes, .mailmap,
.githooks/**, .github/dependabot.yml, nightly.yml, staleness.yml,
check-author.yml, codeql.yml, check-upstream.yml

### Current CI architecture
- **build.yml**: Stable/tagged releases, push/PR/schedule/dispatch
- **nightly.yml**: Master builds, schedule daily + dispatch only, lint + build + report-failure + report-success
- **staleness.yml**: AGENTS.md drift guard, fires on every main push
- **check-author.yml**: Canonical authorship enforcement, fires on every main push
- **codeql.yml**: Security analysis, push/PR/schedule (doc-only pushes skipped)
- **check-upstream.yml**: New release detection, weekly schedule

### Upstream release watch
- check-upstream.yml runs weekly (Mon 06:30 UTC)
- On detection: auto-creates PR with version bump
