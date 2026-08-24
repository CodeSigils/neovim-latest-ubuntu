# Authoritative References

This page is a maintainer index, not a snapshot of current tool versions. Version numbers, runner availability, and
release state belong in executable configuration or generated package metadata, where CI can verify them. Prefer the
primary sources below when changing the build or release design.

## Neovim build and packaging

- [Neovim BUILD.md](https://github.com/neovim/neovim/blob/master/BUILD.md) — supported build flow and prerequisites.
- [Neovim CPack configuration](https://github.com/neovim/neovim/blob/master/cmake.packaging/CMakeLists.txt) — package
  metadata, dependencies, filenames, and maintainer scripts inherited by this project.
- [Neovim release workflow](https://github.com/neovim/neovim/blob/master/.github/workflows/release.yml) — upstream
  release build types and automation patterns.
- [Neovim releases](https://github.com/neovim/neovim/releases/latest) — stable release authority.
- [Removal of upstream `.deb` release assets](https://github.com/neovim/neovim/pull/22773) — historical scope decision
  that motivates this convenience package.

The repository deliberately wraps upstream CMake/CPack rather than maintaining a parallel `debian/` tree. Reconsider
that choice only if the project becomes an apt repository or distribution package.

## Debian and Ubuntu packaging

- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/) — normative binary-package requirements.
- [Debian Developer's Reference: best packaging practices](https://www.debian.org/doc/manuals/developers-reference/best-pkging-practices.html)
  — maintainer scripts and operational practice.
- [Guide for Debian Maintainers](https://www.debian.org/doc/manuals/debmake-doc/) — modern packaging workflow.
- [Ubuntu packaging documentation](https://documentation.ubuntu.com/project/contributors/new-package/) —
  Ubuntu-specific contributor guidance.
- [Ubuntu 26.04 LTS release notes](https://documentation.ubuntu.com/release-notes/26.04/) — target-distribution changes.
- [Lintian manual](https://lintian.debian.org/manual/index.html) — package-policy diagnostics and overrides.

Project rules derived from these sources:

- Maintainer scripts must remain non-interactive and idempotent.
- Runtime shared-library dependencies must be declared; CPack derives them with `dpkg-shlibdeps`.
- Install, runtime, alternatives registration, and removal are release gates.
- Lintian findings remain visible. Fix project-owned findings and baseline only reviewed upstream-content findings.
- This convenience package is not represented as a Debian or Ubuntu archive package.

## CMake and reproducible builds

- [CPack DEB generator](https://cmake.org/cmake/help/latest/cpack_gen/deb.html) — Debian generator inputs,
  `SOURCE_DATE_EPOCH`, dependency generation, and debug-symbol behavior.
- [CPack module](https://cmake.org/cmake/help/latest/module/CPack.html) — shared package variables and install scripts.
- [Reproducible Builds documentation](https://reproducible-builds.org/docs/) — terminology and build techniques.
- [Ubuntu snapshot service](https://snapshot.ubuntu.com/) — dated apt repositories for replay-oriented builds.

`SOURCE_DATE_EPOCH`, an exact upstream commit, a digest-pinned base image, and an optional dated apt snapshot reduce
variation. They do not establish byte-for-byte reproducibility until independent rebuilds demonstrate it.

## Supply-chain and SBOM guidance

- [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
  — build-provenance and SBOM attestations.
- [actions/attest](https://github.com/actions/attest) — supported attestation inputs and verification model.
- [Anchore SBOM action](https://github.com/anchore/sbom-action) — Syft-based SPDX generation used by the package matrix.
- [SPDX 2.3 specification](https://spdx.github.io/spdx-spec/v2.3/) — published SBOM format.

Release packages have separate build-provenance and SBOM attestations. `SHA256SUMS`, build metadata, and the SBOMs are
also release assets so verification does not depend on a single interface.

## GitHub Actions and runners

- [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) — triggers,
  expressions, permissions, and reusable workflows.
- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
  — event-specific filtering behavior.
- [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
  — feature-release approval gates.
- [GitHub-hosted runner images](https://github.com/actions/runner-images) — available x86_64 and ARM64 labels.
- [Immutable releases](https://docs.github.com/en/code-security/supply-chain-security/end-to-end-supply-chain/securing-accounts#immutable-releases)
  — release immutability behavior.

Do not copy runner-image package versions into prose. The workflow variables and actual run metadata are the authority.
GitHub does not apply path filters to tag pushes, so the emergency tag path always runs the stable workflow.

## Container tooling

- [Podman build manual](https://docs.podman.io/en/latest/markdown/podman-build.1.html)
- [Docker build reference](https://docs.docker.com/reference/cli/docker/buildx/build/)
- [Official Ubuntu container image](https://hub.docker.com/_/ubuntu)

Both Podman and Docker can build the `Containerfile`; CI uses Docker on GitHub-hosted runners.

## Maintenance rule

Add a reference only when it explains an implemented decision or an active maintenance task. Prefer a durable landing
page over a version-specific subsection, and remove copied facts once executable configuration can express them.
