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

All `.deb` artifacts are built inside a **containerised, immutable build environment**:

- **Pinned base image** — `Containerfile` uses a specific Ubuntu LTS image pinned via SHA256 digest (stored as a
  repo-level variable `UBUNTU_SHA256`). Every build starts from the exact same filesystem.
- **Parameterised version** — `UBUNTU_VERSION`, `UBUNTU_CODENAME`, and `UBUNTU_SHA256` are governed by repo-level
  variables, not hardcoded or user-supplied at runtime.
- **Container isolation** — compilation and packaging run inside `docker build` then `docker run`. The host runner
  never executes untrusted code directly.
- **Verification inside the container** — `test.sh` runs inside the same container that built the `.deb`, ensuring
  runtime library versions match the build environment. The 7-check test suite covers install, version match, smoke
  test, runtime health, library dependencies, `update-alternatives` registration, and clean uninstall.
- **Integrity attestation** — every release publishes `SHA256SUMS` alongside the `.deb`. Build provenance is attested
  via `actions/attest` (Sigstore-backed OIDC).
- **Non-blocking lintian audit** — Debian package policy checks run on every build. Findings are logged but do not
  block the build (this is a CPack convenience package, not a Debian archive submission).

## Automated Scanners & Agents

| Guard | What it checks | Frequency | Blocks build? |
|---|---|---|---|
| **Dependabot** | Keeps GitHub Actions dependencies at latest patch | Weekly | No (creates PR) |
| **CodeQL** (security-extended) | Static analysis of workflow YAML for injection, token leaks, unsafe patterns | Every push + weekly | Yes |
| **Shellcheck** | `build.sh` and `test.sh` — POSIX shell correctness, quoting, error handling | Every build | Yes |
| **Hadolint** | `Containerfile` — Dockerfile anti-patterns, layer hygiene | Every build | Yes |
| **YAML syntax validation** | All `.github/workflows/*.yml` parse correctly | Every build | Yes |
| **Dependency consistency** | README, manifest files, Containerfile, and scripts agree on prerequisites | Every build | Yes |
| **Release readiness gate** | Upstream tag exists, tag not already released, git state clean, local validation passes | Before every tag push | Yes |
| **Author attribution guard** | All commits authored by canonical human maintainer identity; no AI-agent trailers | Every push | Yes |
| **Build matrix** | x86_64 + aarch64 both must pass; release is blocked if either fails | Every build | Yes |

## Distribution & Package Policy

- **No apt repository mixing** — this project does not instruct users to add third-party apt sources, PPAs, or Debian
  Sid repositories to their system. The `.deb` is downloaded over HTTPS and installed via `dpkg -i`.
- **Single self-contained package** — LuaJIT, libuv, tree-sitter and other bundled dependencies are statically linked
  at build time. No runtime dependency on external library packages beyond standard glibc/libgcc.
- **No distro interference** — the package uses the name `neovim` (matching Ubuntu's archive package) so `apt-mark`
  can hold/pin it cleanly. It does not overwrite or shadow system files outside Neovim's installation path.
- **Tagged releases only** — GitHub Releases are created exclusively from pushed tags matching `v*`. Branch pushes,
  schedule triggers, and manual dispatch produce workflow artifacts only (no Release page). Tags are immutable once
  published.
- **HTTPS-only distribution** — all artifacts are served via TLS from GitHub Releases or Actions artifacts. There is
  no plain-HTTP mirror, no PPA, no custom repository endpoint.
- **Fork compatibility** — all CI expressions have hardcoded fallbacks so forks work without configuring repo-level
  variables. No secrets or privileged credentials are baked into the pipeline.

## Supply Chain Visibility

The full build pipeline is defined in this repository and readable by anyone:

- `build.sh` — parameterised build script
- `Containerfile` — reproducible build environment
- `test.sh` — 7-check verification
- `.github/workflows/build.yml` — CI/CD orchestration

Every dependency (CMake, Ninja, gettext, curl, git, GCC) is installed from the pinned Ubuntu LTS base image — not
downloaded from ad-hoc sources. Neovim source is cloned from the official GitHub repository at a specific tag or
`master` branch.
