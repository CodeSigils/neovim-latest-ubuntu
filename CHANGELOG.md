# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Nightly builds: new `.github/workflows/nightly.yml` runs daily at 06:00 UTC, building Neovim's `master` branch on both `x86_64` and `aarch64`. Artifacts are uploaded (no release page). `build.sh` now supports `VERSION=nightly`.
- Nightly artifact cleanup: artifacts auto-expire after 30 days (`retention-days: 30`) — prevents clutter from 2 builds/day × 365 days.
- Nightly failure alerts: failed nightly builds create a GitHub issue with label `nightly`, linking to the failed run. Duplicate-protected — no new issue if one is already open.
- Auto-update PR on new upstream release: the `check-upstream` workflow now opens a PR with version bumps, CHANGELOG entry, and documentation updates when a newer Neovim release is detected (instead of just filing an issue).
- CodeQL scanning for GitHub Actions workflows: runs weekly and on every PR/push to `main`.
- Multi-arch CI matrix: builds now run on both `x86_64` (`ubuntu-24.04`) and `aarch64` (`ubuntu-24.04-arm`) in parallel. Releases attach both `.deb` files with a combined `SHA256SUMS`.
- Release note automation: Release step now uses `generate_release_notes: true` — GitHub auto-generates release body from commit history.
- Staleness guard CI enforcement: new `.github/workflows/staleness.yml` runs the AGENTS.md §11.3 pre-action gate and §11.5 offline drift scan on every push/PR to `main`. Drift (missing files, leaked artifacts, stale dates, missing docs) fails CI.
- Nightly build documentation: added Nightly Builds section to `RELEASING.md` and §8.7 to `AGENTS.md` covering triggers, artifact download, and key differences from stable releases.
- Anti-drift hardening: added C11 (RELEASING.md covers nightly) and C12 (nightly.yml exists) to AGENTS.md claim inventory. Pre-action gate, offline drift scan, and CI all enforce these new claims.
- Dependency source-of-truth manifests: added `deps/ubuntu-build-deps.txt` for manual host prerequisites and `deps/ubuntu-ci-extra-deps.txt` for CI/container-only extras.
- Dependency consistency check: added `scripts/check-dependencies.py` and wired it into build and staleness CI so README prerequisites, dependency manifests, Containerfile wiring, and build/test script expectations stay aligned.

### Changed

- Containerfile base image pin updated from amd64-specific digest to multi-arch manifest list digest — same `Containerfile` now works on both architectures.
- ARM builds now enforce pass requirement: `continue-on-error: true` removed. Both architectures must succeed for a release to proceed.
- Containerfile optimization: `COPY --chmod=755` eliminates separate `RUN chmod` layer; combined `ENV` lines.
- AGENTS.md repository layout tree expanded: added `.gitattributes` and all 4 workflow files (`build.yml`, `check-upstream.yml`, `codeql.yml`, `nightly.yml`).
- docs/resources.md: replaced dead Baeldung (403) and LinuxVox (520) URLs with working alternatives.
- RELEASING.md: added Nightly Builds section with manual trigger and artifact download instructions.
- README.md: corrected ARM DEB artifact name from `nvim-linux-arm64.deb` to `nvim-linux-aarch64.deb` (matches `$(uname -m)` output); updated build environment from "Debian clang" to "Ubuntu gcc" (matches 24.04 container); removed `unzip` from prerequisites table (not used in build pipeline).
- RELEASING.md: clarified nightly artifact retention as "30 days (workflow-configured)" instead of "GitHub's default 90 days".
- Containerfile now installs build and CI/container dependencies from the committed `deps/*.txt` manifests instead of duplicating package names inline.
- Authorship guard tightened from blacklist-style agent attribution blocking to strict canonical maintainer author/committer enforcement.
- README.md and RELEASING.md now point to dependency manifests as source-of-truth files while keeping user-facing install commands readable.
- docs/resources.md now prioritizes official Neovim, Debian, Ubuntu, CMake, and Podman documentation and removes general third-party packaging tutorials from the curated list.

### Fixed

- docs/reproducibility.md: corrected verification checklist count from "six" to "seven" checks.
- docs/build-plan.md: synced stale documentation — build command from `make` to direct `cmake -B build -G Ninja`, Ubuntu reference from 22.04 to 24.04, build.sh parameters from one variable to two (VERSION + OUTPUT_DIR).
- docs/resources.md: corrected attribution from `code-of-hephaestus/neovim-builds` to `reaper8055/neovim-builds`.
- .mailmap: added agent identity mappings for Claude, ChatGPT, and Copilot — all canonicalised to maintainer identity.
- AGENTS.md: various stale claim fixes and added agent attribution guard (CI-enforced `check-author.yml`).
- README.md manual build example: added missing `git` prerequisite to match the documented `git clone` flow.
- docs/build-plan.md: corrected remaining ARM artifact reference from `nvim-linux-arm64.deb` to `nvim-linux-aarch64.deb`.

## [0.12.2] — 2026-05-22

### Added

- Build pipeline: `build.sh` (parameterised build script), `Containerfile` (Podman build environment), `test.sh` (verification script).
- GitHub Actions CI workflow (`.github/workflows/build.yml`) — triggers on tag push `v*`, main push, and manual dispatch.
- AGENTS.md — project knowledge base with research findings, agent instructions, build documentation, stale-drift guard, and decision log.
- CHANGELOG.md — this file, user-facing release history.
- `RELEASING.md` — release process guide for maintainers (tag push, manual dispatch, local build, troubleshooting).
- Lint job (shellcheck + hadolint) in CI — runs before build, blocks on failures.
- SHA256 checksums (`SHA256SUMS`) generated for release artifacts, included in upload and GitHub Release assets.

### Changed

- Build script parameterised: `VERSION` env var, positional arg, and `latest` alias (auto-fetches latest stable via GitHub API).
- Test script auto-detects version from `.deb` control file via `dpkg-deb -f`.
- Containerfile updated to auto-build on `podman run` (no manual shell entry).
- Containerfile base image pinned to `ubuntu:24.04@sha256:cdb5fd928fce...` for reproducible builds.

### Fixed

- Containerfile missing `sudo` — required by `test.sh` for `dpkg` operations.
- `.gitignore` wildcard `nvim-linux64.deb` expanded to `nvim-linux-*.deb` (covers both x86_64 and aarch64).
- AGENTS.md stale claims (build artifact name, layout status, inline script examples).
- CI artifact verification used invalid `find -exit 0` predicate (not a valid GNU findutils option). Replaced with `ls` glob check in `build.sh` and CI workflow. Every CI run previously failed at the verify step regardless of build success.
- CI never extracted Neovim version from git tags — tag pushes (`v0.13.0`) always built default `0.12.2`. Now uses a priority chain: `workflow_dispatch` input → git tag version → default `0.12.2`.
