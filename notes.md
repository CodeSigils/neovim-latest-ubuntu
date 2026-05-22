# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight, task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md). Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## 2026-05-22

- Refactored agent instructions from raw planning doc into structured AGENTS.md.
- Notes.md simplified to changelog. See `AGENTS.md` for full build and research workflow.
- Added repository layout map, current status audit, guardrails, and decision log to AGENTS.md.
- Added `resources/` and `nvim-linux64.deb` to `.gitignore`.
- Fixed stale claims in AGENTS.md (build artifacts, current status, repo layout). Added §10 Staleness & Drift Guard with freshness checks, update protocol, and anti-drift rule.
- Completed first research cycle: Neovim build system, CPack DEB packaging, Debian packaging approaches. Updated AGENTS.md with §3.5 Research Findings.
- Created docs/ structure: docs/resources.md (curated Ubuntu packaging resources), docs/research/ (gitignored raw artifacts).
- Created docs/build-plan.md with full build pipeline, test strategy, container testing, and versioning.
- Created build.sh (parameterised build script), Containerfile (Podman build env), and test.sh (verification script).
- **First build ran successfully**: Neovim v0.12.2 built inside Podman container (ubuntu:24.04) — 20MB nvim-linux-x86_64.deb produced.
- **Verification passed**: test.sh all 5 checks — install, version match, ldd, update-alternatives registration, clean uninstall.
- CI workflow created: `.github/workflows/build.yml` (tag/main/manual triggers, .deb upload, Release creation).
- Git repo initialized (main branch, all tracked files ready for first commit).
- CHANGELOG.md created (Keep a Changelog format, user-facing release history).
- notes.md refactored to pure scratchpad / task-level record (not user-facing).

## 2026-05-22 — CI Fixes Applied

- **Fixed build.sh**: Changed `cpack` output handling to use explicit `-B "$OUTPUT_DIR"` flag instead of copying from implicit build/ location. This ensures deterministic artifact placement.
- **Fixed Containerfile**: Added `RUN chmod +x` for build-neovim script and fixed CMD to pass VERSION and OUTPUT_DIR args.
- **Fixed CI workflow**: 
  - Created `output/` directory before running container
  - Explicitly pass `VERSION` env var via docker run
  - Added artifact verification step (fail-fast check)
  - Updated upload paths from root level to `output/*.deb`
- **Rationale**: CPack writes artifacts to current working directory by default. Explicit `-B` flag ensures artifacts appear in the right place for CI to find them.

## 2026-05-22 — Documentation Updated

- **AGENTS.md**: Updated header status ("CI verified, build & release pipeline operational"), enhanced Current Status, added Decision Log entries for CI fixes
- **README.md**: Fixed Containerized Build instructions (now creates and uses ./output/ directory)
- **docs/build-plan.md**: Enhanced §3.4 (Package step with `-B` explanation), added §5 (CI Artifact Handling), updated §6 (Files to Create with CI updates)
- **notes.md**: Cleaned up (removed verbose CI analysis section, retained task-level record only)

All documentation now reflects actual implementation and CI fixes. Ready for commit and push to GitHub.

## 2026-05-22 — README Improvements & Release Created

- **README badges**: Added Build status, License, and Release badges at top
- **README fixes**: Fixed placeholder URL (neovim-latest-ubuntu/neovim-latest-ubuntu → CodeSigils/neovim-latest-ubuntu)
- **README additions**: Added ARM64 note, About This Project metadata table, Documentation links section
- **GitHub Release**: Created v0.12.2 release with binary (nvim-linux-x86_64.deb, 20MB)
- **Release notes**: Comprehensive notes including installation, verification checks, build details, reproducibility info
- **Download link**: https://github.com/CodeSigils/neovim-latest-ubuntu/releases/download/v0.12.2/nvim-linux-x86_64.deb

All documentation now reflects actual implementation. Project complete and ready for users.
