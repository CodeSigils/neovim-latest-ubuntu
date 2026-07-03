# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Workflow label validation (`scripts/check-labels.py`) to catch missing labels used by release and nightly automation.
- Cross-workflow policy tests for label validation and check-upstream/check-author compatibility.

### Changed

- Author attribution guard now allows `github-actions[bot]` only on `auto/update-v*` upstream-version PR branches.
- `lintian` is installed in the pinned target container instead of being installed during each package-policy audit step.
- **check-upstream** schedule changed from weekly to daily for faster awareness of new upstream releases.
- **Version defaults** consolidated to `latest` throughout CI and build infrastructure — `build.sh` becomes the single
  source of truth for default version. Containerfile `ENV VERSION` removed; `build.yml` hardcoded fallback removed.

## [0.12.3] — 2026-06-11

### Added

- Support for Neovim v0.12.3. See
  [upstream release](https://github.com/neovim/neovim/releases/tag/v0.12.3).
- Package revision suffix support: tags now accept `vX.Y.Z-N` format (e.g. `v0.12.2-1`) for rebuilds of the same Neovim
  version. The release readiness gate, version extraction, and upstream release link all handle the suffix correctly.
- Release readiness gate: added `scripts/check-release-readiness.sh` plus tests to verify release policy before tagging.
- Nightly builds: new `.github/workflows/nightly.yml` runs daily at 06:00 UTC, building Neovim's `master` branch on both
  `x86_64` and `aarch64`. Artifacts are uploaded (no release page). `build.sh` now supports `VERSION=nightly`.
- Nightly artifact cleanup: artifacts auto-expire after 30 days (`retention-days: 30`) — prevents clutter from 2
  builds/day × 365 days.
- Nightly failure alerts: failed nightly builds create a GitHub issue with label `nightly`, linking to the failed run.
  Duplicate-protected — no new issue if one is already open.
- Nightly success auto-close: when the nightly build recovers after a failure, the open failure issue is automatically
  commented and closed. This keeps the feedback loop clean — old issues don't linger, new failures always create an issue.
- CodeQL performance: added paths-ignore to skip doc-only pushes, switched to `security-extended` query suite (less noise
  on YAML workflows), removed workflow files from paths-ignore (CodeQL must fire when any workflow changes).
- Auto-update PR on new upstream release: the `check-upstream` workflow now opens a PR with version bumps, CHANGELOG
  entry, and documentation updates when a newer Neovim release is detected (instead of just filing an issue).
- CodeQL scanning for GitHub Actions workflows: runs weekly and on every PR/push to `main`.
- Multi-arch CI matrix: stable builds now run on both `x86_64` (`ubuntu-latest`) and `aarch64` (`ubuntu-24.04-arm`) in
  parallel. Releases attach both `.deb` files with a combined `SHA256SUMS`.
- Release body template: Release notes now use a curated static body with install, integrity-check, upstream release
  notes, and `:help news` links.
- Nightly build documentation: added Nightly Builds section to `RELEASING.md` and §8.7 to `AGENTS.md` covering triggers,
  artifact download, and key differences from stable releases.
- Dependency source-of-truth manifests: added `deps/ubuntu-build-deps.txt` for manual host prerequisites and
  `deps/ubuntu-ci-extra-deps.txt` for CI/container-only extras.
- Dependency consistency check: added `scripts/check-dependencies.py` and wired it into build CI so README
  prerequisites, dependency manifests, Containerfile wiring, and build/test script expectations stay aligned.
- Non-blocking `lintian` package-policy audit in the build workflow so Debian/Ubuntu packaging findings are visible
  without blocking CPack convenience-package builds.
- Lintian audit now captures and reports lintian's non-zero findings exit code explicitly instead of relying on
  `continue-on-error`, avoiding a misleading red step annotation while preserving advisory output.
- Build workflow now runs on pull requests to `main` for code/workflow changes, while doc-only PRs use `paths-ignore` to
  skip the expensive build workflow.

### Changed

- Nightly build runner labels updated from `ubuntu-24.04` to `ubuntu-latest` for x86_64 and report-failure jobs. Updated
  comment to reflect that `ubuntu-latest` now maps to ubuntu-26.04.
- Nightly build now runs hadolint and shellcheck in a lint job before building (catches Containerfile/bash issues
  early).
- Build workflow `paths-ignore` extended: `.github/workflows/check-author.yml`, `.github/workflows/nightly.yml`,
  `.mailmap`, `.gitignore`, `.gitattributes`, `.githooks/**`, and `.github/dependabot.yml` changes no longer trigger the
  full container build.
- Build workflow lintian audit now loops over all `.deb` files instead of auditing only the first one alphabetically.
  Aligned with Debian Developer's Reference §6 best practices.
- `check-upstream.yml` version comparison now strips `-N` revision suffix before comparing against our tags — prevents
  false-positive new-release PRs when the latest local tag has a revision suffix (e.g. `v0.12.2-1`).
- RELEASING.md now documents release-version policy: stable GitHub Releases track upstream Neovim tags exactly, existing
  tags are immutable, and packaging suffix tags require explicit workflow support before use.
- Containerfile base image pin updated from amd64-specific digest to multi-arch manifest list digest — same
  `Containerfile` now works on both architectures.
- ARM builds now enforce pass requirement: `continue-on-error: true` removed. Both architectures must succeed for a
  release to proceed.
- Containerfile optimization: `COPY --chmod=755` eliminates separate `RUN chmod` layer; combined `ENV` lines.
- Repository layout documentation expanded for `.gitattributes` and workflow files.
- docs/resources.md: replaced dead Baeldung (403) and LinuxVox (520) URLs with working alternatives.
- RELEASING.md: added Nightly Builds section with manual trigger and artifact download instructions.
- README.md: corrected ARM DEB artifact naming guidance; updated build environment from "Debian clang" to "Ubuntu gcc"
  for the then-current container; removed `unzip` from prerequisites table (not used in build pipeline).
- RELEASING.md: clarified nightly artifact retention as "30 days (workflow-configured)" instead of "GitHub's default 90
  days".
- Containerfile now installs build and CI/container dependencies from the committed `deps/*.txt` manifests instead of
  duplicating package names inline.
- Authorship guard tightened from blacklist-style agent attribution blocking to strict canonical maintainer
  author/committer enforcement.
- README.md and RELEASING.md now point to dependency manifests as source-of-truth files while keeping user-facing
  install commands readable.
- docs/resources.md now prioritizes official Neovim, Debian, Ubuntu, CMake, and Podman documentation and removes general
  third-party packaging tutorials from the curated list.
- CodeQL workflow now uses `github/codeql-action` v4.
- README.md and RELEASING.md now document that the package intentionally installs as `neovim`, how `apt` may compare it
  with Ubuntu archive candidates, and how to inspect/hold/unhold it.
- ARM64 release-asset documentation now uses the actual CPack/GitHub Release filename, `nvim-linux-arm64.deb`; `aarch64`
  remains only for the build-matrix/runner architecture label.
- README release badge and SECURITY supported-version link now point directly to the latest release page instead of
  generic release indexes.
- **Base image**: Containerfile now uses `ubuntu:26.04@sha256:f3d28607...` (Ubuntu 26.04 LTS Resolute Raccoon). The
  build environment now runs on the current Ubuntu LTS.
- **CI runners** remain `ubuntu-24.04` / `ubuntu-24.04-arm` (GitHub has not yet released `ubuntu-26.04` runners). The
  container provides the actual build environment.
- All documentation references updated from Ubuntu 24.04 to 26.04.
- **Ubuntu version centralization**: Set `UBUNTU_VERSION` and `UBUNTU_CODENAME` as GitHub repo variables — single source
  of truth for CI. Containerfile uses `ARG UBUNTU_VERSION` (configurable via `--build-arg`).
- **CI runners**: x86_64 switched to `ubuntu-latest` (auto-rolls with GitHub's LTS); ARM64 remains `ubuntu-24.04-arm`.
  Documentation uses "Ubuntu LTS" where version was just descriptive context, reducing stale-reference maintenance.

### Fixed

- Release page upstream resource links: replaced a broken Neovim changelog URL and XML news URL with the upstream
  release notes page and HTML `:help news` page.
- Documentation audit: corrected stale release-template, runner-label, authorship, and reproducibility snippets.
- PR trigger efficiency: doc-only pull requests now skip the expensive build workflow using the same path filters as
  doc-only pushes. Verified with temporary PR #10; non-build checks still ran and passed.
- docs/reproducibility.md: corrected verification checklist count from "six" to "seven" checks.
- docs/build-plan.md: synced stale documentation — build command now reflects Neovim's upstream Makefile wrapper, Ubuntu
  reference from 22.04 to 24.04, build.sh parameters from one variable to two (VERSION + OUTPUT_DIR).
- docs/resources.md: corrected attribution from `code-of-hephaestus/neovim-builds` to `reaper8055/neovim-builds`.
- .mailmap: added agent identity mappings for Claude, ChatGPT, and Copilot — all canonicalised to maintainer identity.
- Added agent attribution guard (CI-enforced `check-author.yml`).
- README.md manual build example: added missing `git` prerequisite to match the documented `git clone` flow.
- docs/build-plan.md: corrected remaining ARM artifact reference to match the actual release asset name,
  `nvim-linux-arm64.deb`.
- docs/build-plan.md and docs/reproducibility.md: aligned stale build-command and ARM filename notes with the current
  `build.sh`/CPack behavior.
- docs/reproducibility.md: corrected stale ARM filename explanation; the build matrix uses `aarch64`, while actual
  `.deb` filenames and Debian metadata use `arm64`.

## [0.12.2] — 2026-05-22

### Added

- Build pipeline: `build.sh` (parameterised build script), `Containerfile` (Podman build environment), `test.sh`
  (verification script).
- GitHub Actions CI workflow (`.github/workflows/build.yml`) — triggers on tag push `v*`, main push, and manual
  dispatch.
- CHANGELOG.md — this file, user-facing release history.
- `RELEASING.md` — release process guide for maintainers (tag push, manual dispatch, local build, troubleshooting).
- Lint job (shellcheck + hadolint) in CI — runs before build, blocks on failures.
- SHA256 checksums (`SHA256SUMS`) generated for release artifacts, included in upload and GitHub Release assets.

### Changed

- Build script parameterised: `VERSION` env var, positional arg, and `latest` alias (auto-fetches latest stable via
  GitHub API).
- Test script auto-detects version from `.deb` control file via `dpkg-deb -f`.
- Containerfile updated to auto-build on `podman run` (no manual shell entry).
- Containerfile base image pinned to `ubuntu:24.04@sha256:cdb5fd928fce...` for reproducible builds.

### Fixed

- Containerfile missing `sudo` — required by `test.sh` for `dpkg` operations.
- `.gitignore` wildcard `nvim-linux64.deb` expanded to `nvim-linux-*.deb` (covers generated `.deb` artifacts for both
  x86_64 and ARM64 builds).
- AGENTS.md stale claims (build artifact name, layout status, inline script examples).
- CI artifact verification used invalid `find -exit 0` predicate (not a valid GNU findutils option). Replaced with `ls`
  glob check in `build.sh` and CI workflow. Every CI run previously failed at the verify step regardless of build
  success.
- CI never extracted Neovim version from git tags — tag pushes (`v0.13.0`) always built default `0.12.2`. Now uses a
  priority chain: `workflow_dispatch` input → git tag version → default `0.12.2`.
