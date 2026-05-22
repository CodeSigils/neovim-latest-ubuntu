# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12.2] — 2026-05-22

### Added

- Build pipeline: `build.sh` (parameterised build script), `Containerfile` (Podman build environment), `test.sh` (verification script).
- GitHub Actions CI workflow (`.github/workflows/build.yml`) — triggers on tag push `v*`, main push, and manual dispatch.
- AGENTS.md — project knowledge base with research findings, agent instructions, build documentation, stale-drift guard, and decision log.
- CHANGELOG.md — this file, user-facing release history.

### Changed

- Build script parameterised: `VERSION` env var, positional arg, and `latest` alias (auto-fetches latest stable via GitHub API).
- Test script auto-detects version from `.deb` control file via `dpkg-deb -f`.
- Containerfile updated to auto-build on `podman run` (no manual shell entry).

### Fixed

- Containerfile missing `sudo` — required by `test.sh` for `dpkg` operations.
- `.gitignore` wildcard `nvim-linux64.deb` expanded to `nvim-linux-*.deb` (covers both x86_64 and aarch64).
- AGENTS.md stale claims (build artifact name, layout status, inline script examples).
