# Architecture — Neovim Latest Ubuntu `.deb`

**Document type:** Architecture (invariants and code map)
**Status:** Implemented
**Last updated:** 2026-08

## Purpose

This file is a short architectural checklist for the repository. It records durable design decisions without repeating
procedural details from the workflows, scripts, or `docs/reproducibility.md`.

Use it to answer two questions quickly:

1. What are the main moving parts?
2. What must remain true as the project evolves?

## Minimal code map

- `Containerfile` — pinned Ubuntu build/test environment.
- `build.sh` — builds Neovim from upstream source into a `.deb` using upstream CMake/CPack.
- `test.sh` — verifies install, runtime, alternatives registration, and clean removal.
- `.github/workflows/build.yml` — stable detection, release planning, candidate orchestration, and publication.
- `.github/workflows/package.yml` — reusable lint, native architecture matrix, package verification, and artifacts.
- `.github/workflows/nightly.yml` — daily artifact-only builds from Neovim master using the reusable package workflow.
- `.github/actions/quality-gates/action.yml` — shared lint and policy checks used by stable and nightly builds.
- `.github/workflows/policy.yml` — lightweight repository-wide maintenance and documentation gate.
- `.github/workflows/codeql.yml`, `check-author.yml` — security scanning and repo guardrails.
- `.github/dependabot.yml` — automated dependency updates for GitHub Actions.
- `.github/workflows/dependency-freshness.yml` — weekly action-freshness and remote release-configuration audit.
- `scripts/check-repository-settings.py` — labels, Actions variables, environment protection, and immutability drift gate.
- `scripts/plan-release.py` — authenticated upstream resolution and published-release state planning.
- `scripts/write-build-metadata.py` — deterministic per-architecture provenance metadata.
- `scripts/verify-release-candidate.py` — independent package/metadata binding and combined-checksum gate.
- `scripts/check-lintian.sh`, `scripts/lintian-allowlist.txt` — package-policy regression baseline.
- `requirements-dev.txt`, `pyproject.toml` — pinned repository-validation tools and Python quality policy.
- `docs/` — architecture, reproducibility, and curated reference material.
- `deps/` — source-of-truth dependency manifests for build and CI/container tooling.

## Architectural invariants

1. **Upstream alignment**
   - Stable releases are resolved from published upstream releases and built from the exact commit behind the tag.
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
   - Published releases require both packages, combined checksums, and per-architecture build metadata.

5. **Deterministic scripting**
   - `build.sh` and `test.sh` must remain ShellCheck-clean and avoid host-dependent behavior.
   - `Containerfile` must remain Hadolint-clean or document any justified exceptions.

6. **Verification gate**
   - No package is considered valid unless it passes the full `test.sh` checklist on its target architecture.
   - Minimum verification includes install, version check, headless smoke, health check, shared-library check,
     alternatives registration, and clean removal.

7. **Cross-architecture consistency**
   - Stable and nightly callers use one reusable package workflow; x86_64 and ARM64 use the same containerized logic.
   - Both channels resolve an exact upstream commit before invoking upstream build code.
   - Differences between architectures should be limited to target-ISA-specific build outputs.

8. **Package-policy regression control**
   - Reviewed upstream CPack Lintian tags are recorded in a small allowlist.
   - Existing compatibility-package limitations remain visible; any new Lintian error or warning tag blocks release.

9. **Security posture**
   - CI includes ShellCheck, Hadolint, CodeQL, and Dependabot.
   - CodeQL analyzes workflow changes on every pull request, including Dependabot updates; scheduled analysis remains
     the backstop for the default branch.
   - Security-related checks must not be bypassed by doc-only optimization rules.

10. **Scope boundary**
    - This repository is a convenience packaging pipeline for Ubuntu-targeted Neovim `.deb` releases.
    - It is not a Debian archive package, not a PPA replacement, and not a universal Linux packaging solution.

11. **Candidate-first publication**
    - A Git tag is not evidence that a package shipped; published GitHub Releases with their required assets are the
      release state authority.
    - Both architecture candidates must pass before a draft release or release tag is created.
    - Candidate metadata is independently matched to package hashes and build inputs before publication.
    - A draft with an unexpected or incomplete asset set is never published.
    - Maintenance releases publish automatically. Feature releases use the protected `release-reviewed` environment.
    - Routine success creates no issue; automation failures create a self-healing maintainer issue.

## Design rationale

### Upstream CPack instead of a Debian packaging tree

Neovim ships and maintains CMake/CPack packaging configuration with its source. Reusing it keeps this project aligned
with upstream and avoids maintaining a parallel `debian/` tree or a CPack/debhelper hybrid. A full Debian packaging
layout should be reconsidered only if the project expands into an apt repository or distribution archive.

### Verification inside the target container

The generated package can require newer runtime libraries than the GitHub-hosted runner provides. Installing and
testing inside the same pinned Ubuntu container used for compilation verifies the package against its actual target
environment and prevents host-runner library skew. The host remains useful for orchestration, linting, and artifact
storage; it is not the canonical runtime-test environment.

### Lintian regression policy

This remains an upstream CPack convenience package rather than a Debian archive submission. Known CPack findings are
therefore reviewed and recorded by tag, but they are no longer silently ignored. A newly introduced Lintian tag fails
the package matrix and requires either a fix or an explicit, documented baseline decision.

### Candidate-first automation

Cross-repository release events are not delivered directly to this repository, so a daily authenticated poll is the
smallest reliable detector. Detection, exact source resolution, package construction, verification, and publication
remain in one workflow graph. This avoids relying on a tag event created by an automation token and keeps the tested
artifacts attached to the release job that publishes them.

Publication uses two GitHub environments. `release-auto` has no approval rule and handles maintenance releases;
`release-reviewed` requires maintainer approval for feature releases. The approval occurs after the full candidate
matrix, so human attention is spent only on the final policy decision.

## When to update this file

Update this file only when an architectural invariant changes, for example:

- The project stops using upstream CPack.
- The canonical build environment changes from the pinned Ubuntu container model.
- The verification gate changes materially.
- The project expands scope beyond Ubuntu-targeted convenience packaging.

For implementation details, see:

- [`docs/reproducibility.md`](reproducibility.md)
- [`docs/resources.md`](resources.md)
- [`RELEASING.md`](../RELEASING.md)
