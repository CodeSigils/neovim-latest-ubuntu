# Architecture — Neovim Latest Ubuntu `.deb`

**Document type:** Architecture (invariants and code map)
**Status:** Implemented
**Last updated:** 2026-07

## Purpose

This file is a short architectural checklist for the repository. It does not repeat the procedural detail from
`docs/build-plan.md` or `docs/reproducibility.md`.

Use it to answer two questions quickly:

1. What are the main moving parts?
2. What must remain true as the project evolves?

## Minimal code map

- `Containerfile` — pinned Ubuntu build/test environment.
- `build.sh` — builds Neovim from upstream source into a `.deb` using upstream CMake/CPack.
- `test.sh` — verifies install, runtime, alternatives registration, and clean removal.
- `.github/workflows/build.yml` — main CI pipeline: lint, build, test, package-policy audit, release.
- `.github/workflows/nightly.yml` — daily nightly builds from Neovim master.
- `.github/workflows/check-upstream.yml` — auto-detects new upstream Neovim releases and creates version-bump PRs.
- `.github/workflows/codeql.yml`, `check-author.yml` — security scanning and repo guardrails.
- `.github/dependabot.yml` — automated dependency updates for GitHub Actions.
- `docs/` — design and explanation documents (`build-plan.md`, `reproducibility.md`, `resources.md`).
- `deps/` — source-of-truth dependency manifests for build and CI/container tooling.

## Architectural invariants

1. **Upstream alignment**
   - Neovim is built from upstream source tags.
   - Packaging uses upstream CMake/CPack flow, not a custom `debian/` packaging tree.
   - This repository does not replace or fork Neovim packaging logic; it wraps and automates the upstream flow.

2. **Ubuntu distro boundary**
   - Ubuntu builds do not mix Debian sid or other Debian suites into apt sources.
   - Build and runtime dependencies come from Ubuntu's own repositories inside the container.

3. **Canonical build environment**
   - The pinned Ubuntu container image is the canonical build and test environment.
   - Host-side builds are convenience only; CI/container results are authoritative.

4. **Explicit artifact paths**
   - CPack output must go to an explicit directory (`/output` in container, `output/` on host).
   - Each architecture fails fast if its expected `.deb` artifact is missing.

5. **Deterministic scripting**
   - `build.sh` and `test.sh` must remain ShellCheck-clean and avoid host-dependent behavior.
   - `Containerfile` must remain Hadolint-clean or document any justified exceptions.

6. **Verification gate**
   - No package is considered valid unless it passes the full `test.sh` checklist on its target architecture.
   - Minimum verification includes install, version check, headless smoke, health check, shared-library check,
     alternatives registration, and clean removal.

7. **Cross-architecture consistency**
   - x86_64 and ARM64 use the same containerized build logic, the same verification logic, and the same release process.
   - Differences between architectures should be limited to target-ISA-specific build outputs.

8. **Policy visibility over policy enforcement**
   - `lintian` findings are surfaced in CI for visibility.
   - `lintian` is advisory unless the project explicitly decides to promote specific findings to blocking.

9. **Security posture**
   - CI includes ShellCheck, Hadolint, CodeQL, and Dependabot.
   - Security-related checks must not be bypassed by doc-only optimization rules.

10. **Scope boundary**
    - This repository is a convenience packaging pipeline for Ubuntu-targeted Neovim `.deb` releases.
    - It is not a Debian archive package, not a PPA replacement, and not a universal Linux packaging solution.

## When to update this file

Update this file only when an architectural invariant changes, for example:

- The project stops using upstream CPack.
- The canonical build environment changes from the pinned Ubuntu container model.
- The verification gate changes materially.
- The project expands scope beyond Ubuntu-targeted convenience packaging.

For implementation details, see:

- `docs/build-plan.md`
- `docs/reproducibility.md`
- `docs/resources.md`
