# Neovim Latest — deb Package for Ubuntu

[![Build](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml/badge.svg)](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Releases](https://img.shields.io/github/v/release/CodeSigils/neovim-latest-ubuntu?display_name=tag&sort=semver)](https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-brightgreen.svg?logo=dependabot)](./.github/dependabot.yml)
[![CodeQL](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/codeql.yml/badge.svg)](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/codeql.yml)
[![Nightly](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml/badge.svg)](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml)

Build the latest stable [Neovim](https://neovim.io/) as a `.deb` package for Ubuntu 26.04-based systems — no snaps, no
Flatpaks, no AppImages. Just `dpkg -i` and it's installed system-wide.

A [daily stable-release workflow](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml)
detects new upstream releases, resolves each release tag to an exact commit, builds and verifies both architectures,
then publishes maintenance releases automatically. Feature releases build automatically and wait for approval at the
publication step. Issues are created only when release automation fails. Neovim
[`master` nightlies](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml) remain
artifacts-only and never replace the stable GitHub Release.

## Quick Start

Install the latest pre-built Neovim as a system package:

```bash
curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/nvim-linux-x86_64.deb
sudo dpkg -i nvim-linux-x86_64.deb
```

On ARM64 systems, use `nvim-linux-arm64.deb` instead. New releases created by the current pipeline pass the native
x86_64 and ARM64 matrix and include checksums, build metadata, SPDX SBOMs, and GitHub build-provenance and SBOM
attestations. The legacy `v0.12.5` release predates that expanded asset contract.

That's it! Neovim is now installed system-wide with `update-alternatives` registration for `vi`, `vim`, and
`view` commands.

> For custom versions or replay-oriented builds, see [Compilation Instructions](#compilation-instructions).

### Package replacement and apt behavior

This `.deb` installs the Debian package name `neovim`, the same package name used by Ubuntu's archive package. That is
intentional: package managers can track it as the system Neovim package and remove it cleanly.

After installation, `apt` may still compare this package with versions available from your configured repositories. If
`apt` later proposes replacing or downgrading Neovim, inspect the candidate versions before upgrading:

```bash
apt policy neovim
```

If you intentionally want to keep this package installed, you can hold it:

```bash
sudo apt-mark hold neovim
# Later, to resume normal apt upgrades:
sudo apt-mark unhold neovim
```

## Why This Project?

Neovim upstream stopped shipping `.deb` packages in v0.9. The alternatives all have trade-offs:

| Approach                   | Drawback                                                                 |
| -------------------------- | ------------------------------------------------------------------------ |
| `apt install neovim`       | Tracks Ubuntu's selected version rather than necessarily latest upstream |
| Official AppImage          | No package-manager ownership or system-wide alternatives integration     |
| Snap (`snap install nvim`) | Snap-managed installation and refreshes; uses classic confinement        |
| Build from source manually | No package manager tracking or automatic clean uninstall                 |

This project gives you the latest Neovim as a proper system package — `update-alternatives` registration, clean
uninstall, dependency tracking.

## Wallpapers

The [`wallpapers/`](./wallpapers/) directory contains optional AI-generated Neovim and Ubuntu artwork. It is not part
of the package or build context and can be omitted from a sparse clone.

If you don't want them taking up space after cloning, simply remove the directory:

```bash
rm -rf wallpapers/
```

To exclude them when cloning:

```bash
git clone --depth 1 --sparse https://github.com/CodeSigils/neovim-latest-ubuntu.git
cd neovim-latest-ubuntu
git sparse-checkout set --no-cone '/*' '!wallpapers/'
```

## Compilation Instructions

For custom builds, replay-oriented builds, or building newer/older versions of Neovim.

### Prerequisites

Manual build-host prerequisites (source of truth: [`deps/ubuntu-build-deps.txt`](./deps/ubuntu-build-deps.txt)):

```bash
sudo apt install ninja-build gettext cmake curl jq git build-essential
```

The manifest is deliberately package-name based instead of duplicating version minima that can drift from Ubuntu and
upstream Neovim. For non-Ubuntu hosts, follow upstream
[BUILD.md](https://github.com/neovim/neovim/blob/master/BUILD.md).

> The CI/container image installs the same manual build list plus extra automation packages from
> [`deps/ubuntu-ci-extra-deps.txt`](./deps/ubuntu-ci-extra-deps.txt) (`ca-certificates`, `file`, `lintian`, `lua5.1`,
> `sudo`) for HTTPS fetches, packaging inspection, package-policy audit, and `test.sh` execution.
> `scripts/check-dependencies.py` enforces that the README, dependency manifests, `Containerfile`, and `.dockerignore`
> stay aligned.

### Manual Build

Build and install Neovim in three commands:

```bash
sudo apt install ninja-build gettext cmake curl git build-essential
git clone --depth 1 --branch v<VERSION> https://github.com/neovim/neovim && cd neovim
make CMAKE_BUILD_TYPE=Release && cd build && cpack -G DEB && sudo dpkg -i nvim-linux-x86_64.deb
```

### Containerized Build (Recommended for Repeatability)

Build inside a Podman (or Docker) container matching the target OS. This isolates the build from most host state and is
the canonical way to replay the project environment:

```bash
# Build the container image (bakes build.sh into the image)
podman build -t neovim-builder .

# Build the default version (outputs .deb to ./output)
mkdir -p output
podman run --rm -v "$(pwd)/output:/output" neovim-builder

# Build a different version (e.g. v0.14.0)
podman run --rm -e VERSION=0.14.0 -v "$(pwd)/output:/output" neovim-builder

# Verify the .deb inside the disposable build container
# x86_64 builds produce nvim-linux-x86_64.deb; ARM64 builds produce nvim-linux-arm64.deb.
podman run --rm \
  -v "$PWD/test.sh:/tmp/test.sh:ro" \
  -v "$PWD/output:/output:ro" \
  neovim-builder \
  bash /tmp/test.sh /output/nvim-linux-x86_64.deb
```

The container image (pinned to the current Ubuntu LTS in the Containerfile) includes all build prerequisites and runs
[`build.sh`](./build.sh) on startup. Set `VERSION` via `-e` to build a specific release; it defaults to `latest`, which
resolves the current stable release from the upstream GitHub API. The `-v "$(pwd)/output:/output"` mount ensures the
`.deb` appears in the `output/` directory on your host.

Stable versions use CMake's `Release` build type. `VERSION=nightly` uses `RelWithDebInfo` for diagnostic value.

The base image is digest-pinned, but Ubuntu apt repositories remain rolling. A dated Ubuntu package snapshot removes
that rolling input for a replay-oriented build; it does not by itself guarantee byte-identical output:

```bash
podman build --build-arg UBUNTU_APT_SNAPSHOT=YYYYMMDDTHHMMSSZ -t neovim-builder .
```

> CI passes the Ubuntu base image version, codename, and digest from repo-level GitHub Actions variables
> (`UBUNTU_VERSION`, `UBUNTU_CODENAME`, `UBUNTU_SHA256`) into the Containerfile. When upgrading to a new Ubuntu LTS,
> update those three variables and the public Containerfile fallbacks together.
> Fork? Don't worry — every expression has a hardcoded fallback, so CI works without creating any variables.
> Configure them in the repo under Settings → Secrets and variables → Actions → Variables; see
> [GitHub Actions variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables).

### Build Output

The build produces `nvim-linux-x86_64.deb` (or `nvim-linux-arm64.deb` on ARM64) in the specified output directory. When
building in the container, this maps to `./output/`.

Neovim's bundled third-party dependencies are built from revisions selected by the exact upstream source commit. CPack
derives the remaining runtime shared-library dependencies from the target Ubuntu environment and records them in the
package metadata.

## Compilation Details

Build verification and technical information:

### Build environment

The container build runs inside the Ubuntu LTS base image (pinned via digest in Containerfile) and currently produces
packages for both supported CI architectures:

- x86_64
- aarch64

Compiler, target triple, and resolved runtime dependency details come from the specific build environment and package
metadata at build time, so they may change as the base image is refreshed. For repo-stable facts, treat the workflow
matrix and the generated package itself as the source of truth rather than a hard-coded snapshot.

### Verification Checklist

Each build is verified against these checks:

| #   | Check           | Description                                                                                     |
| --- | --------------- | ----------------------------------------------------------------------------------------------- |
| 1   | Install         | `dpkg -i` installs cleanly; `test.sh` attempts `apt-get install -f` if dependencies are missing |
| 2   | Package version | Debian metadata reports the expected package version                                            |
| 3   | Runtime version | `nvim --version` reports the expected release version                                           |
| 4   | Smoke test      | `nvim --headless +q` starts and exits cleanly                                                   |
| 5   | Runtime health  | `nvim --headless +checkhealth +q` runs without crash                                            |
| 6   | Dependencies    | `ldd` shows no unresolved shared library dependencies                                           |
| 7   | Alternatives    | `update-alternatives` shows nvim registered for `vi`, `vim`, and `view`                         |
| 8   | Uninstall       | `dpkg -r` removes cleanly and unregisters alternatives                                          |

These checks are automated in [`test.sh`](./test.sh).
Because the test installs and removes the system `neovim` package, it refuses to run directly on a host unless
`ALLOW_HOST_PACKAGE_TEST=1` is explicitly set. The disposable container invocation above is the supported default.

For stable CI builds, the upstream release tag is resolved to an exact commit before compilation. Requested source and
Debian package versions are passed to `test.sh` independently of generated package metadata. Package revisions such as
`vX.Y.Z-1` therefore verify Neovim `X.Y.Z` while requiring Debian package version `X.Y.Z-1`.

To verify provenance after downloading a release:

```bash
gh attestation verify nvim-linux-x86_64.deb \
  -R CodeSigils/neovim-latest-ubuntu

# Verify the SPDX SBOM attestation
gh attestation verify nvim-linux-x86_64.deb \
  -R CodeSigils/neovim-latest-ubuntu \
  --predicate-type https://spdx.dev/Document/v2.3
```

## License

The packaging automation in this repository is licensed under the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0); see [`LICENSE`](./LICENSE). Generated
packages contain Neovim, which retains its upstream copyright notices and Apache 2.0 license.

---

## About This Project

| Item             | Detail                                                                                                         |
| ---------------- | -------------------------------------------------------------------------------------------------------------- |
| **Package**      | Neovim built with CPack (upstream-recommended)                                                                 |
| **Base OS**      | Ubuntu LTS (defined in Containerfile via `ARG UBUNTU_VERSION`)                                                 |
| **Build system** | Ninja (auto-detected by Neovim's Makefile)                                                                     |
| **Dependencies** | Upstream-pinned bundled dependencies plus CPack-derived Ubuntu runtime dependencies                            |
| **CI/CD**        | GitHub Actions with a pinned, containerized build environment                                                  |
| **Verification** | 8-point automated test suite (install, package/runtime versions, smoke, health, deps, alternatives, uninstall) |

## Documentation

- **[docs/architecture.md](./docs/architecture.md)** — Architectural invariants and code map (read this first)
- **[docs/reproducibility.md](./docs/reproducibility.md)** — Functional replayability approach, guarantees, and limits
- **[docs/resources.md](./docs/resources.md)** — Authoritative upstream, packaging, and automation references
- **[RELEASING.md](./RELEASING.md)** — Release process guide for maintainers
- **[SECURITY.md](./SECURITY.md)** — Security policy, scanners, distribution boundaries
