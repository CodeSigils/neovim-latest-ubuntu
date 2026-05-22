# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight, task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md). Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## 2026-05-22

- Refactored agent instructions from raw planning doc into structured AGENTS.md.
- Notes.md simplified to changelog. See `AGENTS.md` for full build and research workflow.
- Added repository layout map, current status audit, guardrails, and decision log to AGENTS.md.
- Added `resources/` and `nvim-linux64.deb` to `.gitignore`.
- Fixed stale claims in AGENTS.md (build artifacts, current status, repo layout). Added §10 Staleness & Drift Guard with freshness checks, update protocol, and anti-drift rule.
- Completed first research cycle: Neovim build system, CPack DEB packaging, Debian packaging approaches. Updated AGENTS.md with §3.5 Research Findings (build pipeline, CPack config, approach comparison). Added Diataxis documentation structure to §4.
- Updated AGENTS.md §3.1 with parallel agent dispatch strategy, §3.2 with expanded evaluation criteria, §9 Decision Log with new entries.
- Documentation phase: transformed README into Diataxis how-to guide (Quick Start, Build from Source, Prerequisites, Compilation Details, License). Created LICENSE file (Apache 2.0). Moved LICENSE from [future] to root in AGENTS.md layout.
- Created docs/ structure: docs/resources.md (curated Ubuntu packaging resources with evaluation scores), docs/research/ (gitignored raw artifacts). Replaced old resources/ gitignore entry with docs/research/. Updated AGENTS.md Repository Layout, §3.1 (curation workflow), Guardrails, and §9 Decision Log to reference docs/ structure.
- Updated docs with Neovim CI/release packaging research: PR #22773 (.deb removal from CI), release.yml pipeline details, neovim-releases reference, neovim-builds third-party reference. Added to docs/resources.md and AGENTS.md §3.5.5.
- Fixed stale docs across all files: README Quick Start (build first, then install — no pre-built .deb yet), AGENTS.md §5.3 output naming (neovim- → nvim-linux), .gitignore (added _CPack_Packages/), notes.md (removed stale research scribbles), docs/resources.md (updated neovim-builds status/latest release).
- Research correction cycle: expanded AGENTS.md §3.5.1 from 2 to 3 approaches (CPack, debian/, hybrid) with proper nuance — upstream BUILD.md still recommends CPack for local .deb despite CI dropping it. Added BUILD.md position note to §3.5.2. Added Debian Vim Maintainers salsa.debian.org reference to §3.5.5. Added Decision Log entry. CPack approach confirmed for personal .deb scope.
- Added Ninja build system rationale to AGENTS.md §3.5.2, README.md Build section, and docs/resources.md. Ninja is auto-detected by Neovim's Makefile, used in Neovim CI, and is the industry-recommended CMake generator for faster builds and automatic parallelisation.
- Added "Consult project documentation" step 0 to AGENTS.md §4 Planning Phase — agents must re-read AGENTS.md §3.5, docs/resources.md, and README.md before creating a plan.
- Created docs/build-plan.md with full build pipeline, test strategy, container testing, and versioning. User overrode .omo/plans/ location to docs/. Updated AGENTS.md §4 step 2, Repository Layout, and freshness check accordingly.
- Created build.sh (parameterised build script), Containerfile (Podman build env), and test.sh (verification script). Updated AGENTS.md Repository Layout and Current Status. Updated docs/build-plan.md status table to Done.
- **First build ran successfully**: Neovim v0.12.2 built inside Podman container (ubuntu:24.04) — 20MB nvim-linux-x86_64.deb produced.
- **Verification passed**: test.sh all 5 checks — install, version match, ldd, update-alternatives registration, clean uninstall.
- Added `sudo` to Containerfile for test.sh compatibility.
- Hardened AGENTS.md §10 Staleness & Drift Guard: claim inventory (C1-C10), pre-action gate with hard failure on drift, update protocol, offline scan, renewal rule, zero-tolerance anti-drift rule.
- Improved .gitignore wildcard to `nvim-linux-*.deb`.
- build.sh: added VERSION env var support + `latest` alias (GitHub API auto-fetch).
- test.sh: auto-extracts version from .deb via `dpkg-deb -f`.
- Containerfile: auto-build CMD (builds immediately, no bash shell).
- CI workflow created: `.github/workflows/build.yml` (tag/main/manual triggers, .deb upload, Release creation).
- Release Phase documented: AGENTS.md §8, README.md (download from Releases), docs/build-plan.md §7.
- README discoverability refresh: first-screen value prop, comparison table (vs apt/AppImage/Snap), reordered Quick Start to working build command, explicit Download from Releases section.
- AGENTS.md stale claim fixes (C9 + §9): structure status → "stable", guardrail artifact name → nvim-linux-*.deb.
- docs/build-plan.md inline scripts synced to match actual build.sh/test.sh (version auto-detect, latest alias, check framework).
- Git repo initialized (main branch, all tracked files ready for first commit).
- CHANGELOG.md created (Keep a Changelog format, user-facing release history).
- notes.md refactored to pure scratchpad / task-level record (not user-facing).
- AGENTS.md updated: CHANGELOG section in §7, release tasks include CHANGELOG update in §8.5.

