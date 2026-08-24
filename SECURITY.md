# Security Policy

## Scope

This policy covers the build pipeline scripts in this repository (`build.sh`, `test.sh`, `Containerfile`, CI workflows,
and related automation).

**Neovim itself** is an upstream project with its own security reporting process at
<https://github.com/neovim/neovim/security>.

## Supported Versions

The [latest release](https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest) is the only supported version.
Older releases are not backported — upgrade to the latest to receive fixes.

## Reporting a Vulnerability

If you discover a security issue in the pipeline or generated artifacts, please report it via **GitHub's private
vulnerability reporting**:

1. Go to
   [https://github.com/CodeSigils/neovim-latest-ubuntu/security](https://github.com/CodeSigils/neovim-latest-ubuntu/security/advisories/new)
2. Click **"Report a vulnerability"**
3. Provide a description, steps to reproduce, and impact

Reports are acknowledged and triaged as maintainer availability permits. Keep vulnerability details private until a fix
or coordinated disclosure plan is available.

## Build Pipeline Security

Published `.deb` artifacts are built inside a **containerised, pinned build environment**:

- **Pinned base image** — `Containerfile` uses a specific Ubuntu LTS image pinned via SHA256 digest, with repo-level
  variables able to override `UBUNTU_VERSION`, `UBUNTU_CODENAME`, and `UBUNTU_SHA256` in CI. This pins the base image;
  apt-installed packages are still resolved from Ubuntu repositories at image-build time.
- **Parameterised base image** — `UBUNTU_VERSION`, `UBUNTU_CODENAME`, and `UBUNTU_SHA256` are governed by repo-level
  variables in CI, with public hardcoded fallbacks for fork compatibility.
- **Optional apt snapshot** — release operators can pass `UBUNTU_APT_SNAPSHOT` to pin Ubuntu package indexes for a
  replay-focused build; normal scheduled builds intentionally follow the current Ubuntu repositories.
- **Build-environment isolation** — compilation and packaging run inside `docker build` then `docker run`, reducing
  coupling to hosted-runner state. The container is not treated as a security sandbox for untrusted upstream code.
  Quality jobs use read-only repository permissions; publication and failure-reporting jobs receive only their explicit
  release, attestation, or issue permissions.
- **Verification inside the container** — `test.sh` runs inside the same container that built the `.deb`, ensuring
  runtime library versions match the build environment. The 8-check test suite covers install, package and runtime
  version matches, smoke test, runtime health, library dependencies, `update-alternatives` registration, and clean
  uninstall.
- **Integrity and inventory** — releases produced by the current pipeline publish `SHA256SUMS`, per-architecture build
  metadata, and SPDX SBOMs. `actions/attest` creates separate build-provenance and SBOM attestations using GitHub OIDC
  and Sigstore. The legacy `v0.12.5` release predates this expanded asset contract.
- **Exact upstream source** — stable release tags are dereferenced through the authenticated GitHub API and the build
  fetches the resulting full commit SHA rather than trusting a mutable tag name during compilation. Nightly builds
  likewise resolve and record the exact `master` commit before starting.
- **Token containment** — the workflow token is used by orchestration only and is not passed into the container that
  executes upstream build code. Checkout credentials are not persisted in any job workspace.
- **Build metadata** — releases produced by the current pipeline record upstream and packaging commits, target image
  digest, architecture, package version, and artifact hash. Publication recomputes and verifies those bindings.
- **Package policy** — stable packages use standard CPack metadata, documentation, commit-derived package timestamps,
  and stripping. The remaining reviewed upstream-content Lintian findings stay visible; any new tag blocks publication.

## Automated Scanners & Agents

| Guard                          | What it checks                                                                              | Frequency                                                      | Blocks build?                                              |
| ------------------------------ | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------- |
| **Dependabot**                 | Keeps GitHub Actions and pinned Python validation tools current; PRs require human review   | Weekly                                                         | No (creates PR)                                            |
| **Repository maintenance**     | Reports action freshness and audits labels, Actions variables, and release environments     | Weekly and manual                                              | Yes for configuration drift; freshness remains report-only |
| **Ruff**                       | Python correctness, modernization, and deterministic formatting                             | Every policy/build gate                                        | Yes                                                        |
| **Zizmor**                     | GitHub Actions security, token persistence, and template-injection risks                    | Every policy/build gate                                        | Yes                                                        |
| **CodeQL** (security-extended) | Static analysis of workflow YAML for injection, token leaks, unsafe patterns                | Non-ignored pushes, all PRs (including Dependabot), and weekly | Yes                                                        |
| **Shellcheck**                 | Shell correctness and error handling in scripts and the commit-message hook                 | Every applicable policy/package gate                           | Yes                                                        |
| **Hadolint**                   | `Containerfile` — Dockerfile anti-patterns, layer hygiene                                   | Every applicable policy/package gate                           | Yes                                                        |
| **Syft**                       | Generates a per-architecture SPDX package inventory                                         | Every native package build                                     | Yes                                                        |
| **YAML syntax validation**     | Workflow files and local composite actions parse correctly                                  | Every applicable policy/package gate                           | Yes                                                        |
| **actionlint**                 | GitHub Actions schema, expressions, shell fragments, and workflow semantics                 | Every policy/build gate                                        | Yes                                                        |
| **Dependency consistency**     | README, manifest files, Containerfile, and scripts agree on prerequisites                   | Every applicable policy/package gate                           | Yes                                                        |
| **Release planner**            | Published upstream release, exact source commit, published local assets, and approval class | Daily and on stable CI                                         | Yes                                                        |
| **Release readiness gate**     | Emergency tag-path preflight: upstream tag, release absence, clean synchronized git state   | Manual recovery only                                           | No (outside CI)                                            |
| **Author attribution guard**   | Commits use the canonical human maintainer identity and contain no AI-agent trailers        | Pushes to `main` and pull requests targeting `main`            | Yes                                                        |
| **Build matrix**               | x86_64 + aarch64 both must pass; release is blocked if either fails                         | Every build                                                    | Yes                                                        |

## Distribution & Package Policy

- **No apt repository mixing** — this project does not instruct users to add third-party apt sources, PPAs, or Debian
  Sid repositories to their system. The `.deb` is downloaded over HTTPS and installed via `dpkg -i`.
- **Single installable package** — upstream-pinned bundled dependencies are built with Neovim. CPack derives and
  declares the remaining target-Ubuntu shared-library dependencies; the current package is not described as fully
  static.
- **Package-manager ownership** — the package uses the name `neovim`, matching Ubuntu's archive package, so apt can
  track, replace, hold, and remove it normally. Its maintainer scripts register and unregister the documented
  `update-alternatives` entries.
- **Candidate-first releases** — scheduled or explicitly requested publication builds and verifies both architectures
  before creating a draft release and tag. Tag pushes remain an emergency compatibility path. Published tags and
  assets created after immutable releases were enabled are protected by repository enforcement. The legacy `v0.12.5`
  release predates the setting and is not retroactively immutable.
- **HTTPS-only distribution** — published release and workflow artifacts are served via TLS from GitHub. There is no
  plain-HTTP mirror, no PPA, and no custom repository endpoint.
- **Fork compatibility** — all CI expressions have hardcoded fallbacks so forks work without configuring repo-level
  variables. No secrets or privileged credentials are baked into the pipeline.

## Pull-request gate policy

The workflows are designed so that every code or workflow change has a directly applicable validation path:

- Build-affecting changes run the full lint, x86_64, and ARM64 matrix.
- Documentation, workflow, script, test, and dependency-manifest changes run the repository policy workflow. Changes
  that can affect generated packages also run the native package matrix; documentation and validation-only changes do
  not spend package-build minutes.
- Workflow changes run CodeQL and the author-attribution guard.
- Dependabot pull requests are intentionally not auto-merged; they receive the same CodeQL analysis and require a
  maintainer decision.

Repository branch-protection settings are managed in GitHub rather than in this repository. Maintainers should require
the applicable validation checks before merging, while allowing documentation-only changes to use the lightweight gate.
If branch protection is intentionally disabled for a fork, the workflow results remain available as an auditable manual
gate.

## Supply Chain Visibility

The full build pipeline is defined in this repository and readable by anyone:

- `build.sh` — parameterised build script
- `Containerfile` — pinned, containerized build environment
- `test.sh` — 8-check verification
- `.github/workflows/build.yml` — stable detection and release orchestration
- `.github/workflows/package.yml` — reusable native build and verification matrix

Build tools are installed from the configured Ubuntu LTS repositories inside the pinned base image. Neovim source is
fetched from the official GitHub repository at an exact release or resolved nightly commit; upstream's own build
system then resolves the dependency revisions selected by that source commit.
