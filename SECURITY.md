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

Reports are acknowledged within 72 hours. You should receive a timeline for review within 5 business days.

## Build Pipeline Security

All `.deb` artifacts are built inside a **containerised, pinned build environment**:

- **Pinned base image** — `Containerfile` uses a specific Ubuntu LTS image pinned via SHA256 digest, with repo-level
  variables able to override `UBUNTU_VERSION`, `UBUNTU_CODENAME`, and `UBUNTU_SHA256` in CI. This pins the base image;
  apt-installed packages are still resolved from Ubuntu repositories at image-build time.
- **Parameterised base image** — `UBUNTU_VERSION`, `UBUNTU_CODENAME`, and `UBUNTU_SHA256` are governed by repo-level
  variables in CI, with public hardcoded fallbacks for fork compatibility.
- **Optional apt snapshot** — release operators can pass `UBUNTU_APT_SNAPSHOT` to pin Ubuntu package indexes for a
  reproducibility-focused build; normal scheduled builds intentionally follow the current Ubuntu repositories.
- **Container isolation** — compilation and packaging run inside `docker build` then `docker run`, limiting their access
  to the hosted runner. Repository lint and orchestration scripts still execute on the host runner with read-only
  repository permissions.
- **Verification inside the container** — `test.sh` runs inside the same container that built the `.deb`, ensuring
  runtime library versions match the build environment. The 8-check test suite covers install, package and runtime
  version matches, smoke test, runtime health, library dependencies, `update-alternatives` registration, and clean
  uninstall.
- **Integrity attestation** — every release publishes `SHA256SUMS` alongside the `.deb`. Build provenance is attested
  via `actions/attest` (Sigstore-backed OIDC).
- **Exact upstream source** — stable release tags are dereferenced through the authenticated GitHub API and the build
  fetches the resulting full commit SHA rather than trusting a mutable tag name during compilation.
- **Build metadata** — every release records upstream and packaging commits, target image digest, architecture, package
  version, and artifact hash in machine-readable metadata.
- **Lintian regression gate** — reviewed upstream CPack findings remain visible in an allowlist; any new finding tag
  blocks publication.

## Automated Scanners & Agents

| Guard | What it checks | Frequency | Blocks build? |
|---|---|---|---|
| **Dependabot** | Keeps GitHub Actions dependencies current; PRs require human review and merge | Weekly | No (creates PR) |
| **Dependency freshness** | Reports pinned action SHAs that lag their documented major version | Weekly | No (report only) |
| **CodeQL** (security-extended) | Static analysis of workflow YAML for injection, token leaks, unsafe patterns | Non-ignored pushes, all PRs (including Dependabot), and weekly | Yes |
| **Shellcheck** | Shell correctness, quoting, error handling (`build.sh`, `test.sh`, and stable-build `scripts/*.sh`) | Every build | Yes |
| **Hadolint** | `Containerfile` — Dockerfile anti-patterns, layer hygiene | Every build | Yes |
| **YAML syntax validation** | Workflow files and local composite actions parse correctly | Every build | Yes |
| **actionlint** | GitHub Actions schema, expressions, shell fragments, and workflow semantics | Every policy/build gate | Yes |
| **Dependency consistency** | README, manifest files, Containerfile, and scripts agree on prerequisites | Every build | Yes |
| **Release planner** | Published upstream release, exact source commit, published local assets, and approval class | Daily and on stable CI | Yes |
| **Release readiness gate** | Emergency tag-path preflight: upstream tag, release absence, clean synchronized git state | Manual recovery only | No (outside CI) |
| **Author attribution guard** | All commits authored by canonical human maintainer identity; no AI-agent trailers | Every push | Yes |
| **Build matrix** | x86_64 + aarch64 both must pass; release is blocked if either fails | Every build | Yes |
| **Repository label guard** | Required labels (`dependencies`, `github-actions`, `new-release`, `nightly`) exist on the repo | Every build | Yes |

## Distribution & Package Policy

- **No apt repository mixing** — this project does not instruct users to add third-party apt sources, PPAs, or Debian
  Sid repositories to their system. The `.deb` is downloaded over HTTPS and installed via `dpkg -i`.
- **Single self-contained package** — LuaJIT, libuv, tree-sitter and other bundled dependencies are statically linked
  at build time. No runtime dependency on external library packages beyond standard glibc/libgcc.
- **No distro interference** — the package uses the name `neovim` (matching Ubuntu's archive package) so `apt-mark`
  can hold/pin it cleanly. It does not overwrite or shadow system files outside Neovim's installation path.
- **Candidate-first releases** — scheduled or explicitly requested publication builds and verifies both architectures
  before creating a draft release and tag. Tag pushes remain an emergency compatibility path. Published tags and
  assets are protected by GitHub immutable-release enforcement.
- **HTTPS-only distribution** — all artifacts are served via TLS from GitHub Releases or Actions artifacts. There is
  no plain-HTTP mirror, no PPA, no custom repository endpoint.
- **Fork compatibility** — all CI expressions have hardcoded fallbacks so forks work without configuring repo-level
  variables. No secrets or privileged credentials are baked into the pipeline.

## Pull-request gate policy

The workflows are designed so that every code or workflow change has a directly applicable validation path:

- Build-affecting changes run the full lint, x86_64, and ARM64 matrix.
- Documentation, workflow, script, test, and dependency-manifest changes run the lightweight repository policy workflow.
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
- `Containerfile` — reproducible build environment
- `test.sh` — 8-check verification
- `.github/workflows/build.yml` — stable detection and release orchestration
- `.github/workflows/package.yml` — reusable native build and verification matrix

Build dependencies (CMake, Ninja, gettext, curl, jq, git, GCC) are installed from the configured Ubuntu LTS apt
repositories inside the pinned base image — not downloaded from ad-hoc sources. Neovim source is cloned from the
official GitHub repository at an exact release commit or the nightly `master` branch.
