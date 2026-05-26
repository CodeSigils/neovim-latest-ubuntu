# notes.md — Agent scratchpad

## 2026-05-26 — Doc drift cleanup

Fixed 4 doc drifts found during audit:
1. docs/build-plan.md §5 — paths-ignore table missing `.mailmap`
2. docs/build-plan.md §5 — No `workflow_dispatch` trigger row
3. docs/build-plan.md §5 — Lint description only had 2 of 5 checks
4. README.md — Documentation section missing `docs/reproducibility.md`

All fixes verified against actual state. Git tree clean pending commit.

### Upstream release watch

- check-upstream.yml runs weekly (Mon 06:30 UTC)
- On detection: auto-creates PR with version bump
