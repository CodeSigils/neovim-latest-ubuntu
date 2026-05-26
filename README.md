# Neovim Latest — deb Package for Ubuntu

[![Build](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml/badge.svg)](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Releases](https://img.shields.io/github/v/release/CodeSigils/neovim-latest-ubuntu?display_name=tag&sort=semver)](https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-brightgreen.svg?logo=dependabot)](https://github.com/CodeSigils/neovim-latest-ubuntu/network/updates)
[![CodeQL](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/codeql.yml/badge.svg)](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/codeql.yml)
[![Nightly](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml/badge.svg)](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml)

Build the latest stable [Neovim](https://neovim.io/) as a `.deb` package for Ubuntu and Linux Mint — no snaps, no
Flatpaks, no AppImages. Just `dpkg -i` and it's installed system-wide.

A [weekly CI build](.github/workflows/build.yml) automatically fetches and packages the latest Neovim release. GitHub
Releases are created only when version tags are pushed. The Monday scheduled build keeps a fresh stable package
available as a workflow artifact on the Actions run page until the next tagged release is published, while
[nightly builds](.github/workflows/nightly.yml) from Neovim's `master` branch run daily and are **artifacts-only**
(download from the workflow run page, not from Releases).

## Quick Start

Install the latest pre-built Neovim as a system package:

```bash
curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/nvim-linux-x86_64.deb
sudo dpkg -i nvim-linux-x86_64.deb
```

On ARM64 systems, use `nvim-linux-arm64.deb` instead. Releases are created automatically when a tag is pushed to the
repository. A weekly scheduled build (Monday 06:00 UTC) also packages the latest stable Neovim as a workflow artifact,
so you can always download a fresh stable build from the Actions run page even between tagged releases.

> Need the freshest stable build rather than the last tagged release? Open the latest successful
> [`build.yml`](./.github/workflows/build.yml) run and download the workflow artifact for your architecture.

That's it! Neovim is now installed system-wide with `update-alternatives` registration for `vi`, `vim`, `view`, and
`editor` commands.

> For custom versions or reproducible builds, see [Compilation Instructions](#compilation-instructions).

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

| Approach                   | Drawback                                         |
| -------------------------- | ------------------------------------------------ |
| `apt install neovim`       | Often lags behind latest release by months       |
| Official AppImage          | No system-wide `vi`/`editor` symlink integration |
| Snap (`snap install nvim`) | Sandboxing breaks file access, slow startup      |
| Build from source manually | No package manager tracking, no clean uninstall  |

This project gives you the latest Neovim as a proper system package — `update-alternatives` registration, clean
uninstall, dependency tracking.

## Compilation Instructions

For custom builds, reproducible builds, or building newer/older versions of Neovim.

### Prerequisites

Manual build-host prerequisites (source of truth: [`deps/ubuntu-build-deps.txt`](./deps/ubuntu-build-deps.txt)):

```bash
sudo apt install ninja-build gettext cmake curl git build-essential
```

| Tool          | Minimum version |
| ------------- | --------------- |
| [ninja-build] | 1.11            |
| [gettext]     | 0.21            |
| [cmake]       | 3.25            |
| curl          | 7.88            |

> **Maintenance note**: These minimum versions were verified against the Neovim release used at the time of writing.
> When updating to a newer Neovim version, check upstream
> [BUILD.md](https://github.com/neovim/neovim/blob/master/BUILD.md) or release notes for any raised dependency
> requirements and update this table accordingly.

[ninja-build]: https://ninja-build.org/
[gettext]: https://www.gnu.org/software/gettext/
[cmake]: https://cmake.org/

> The CI/container image installs the same manual build list plus extra automation packages from
> [`deps/ubuntu-ci-extra-deps.txt`](./deps/ubuntu-ci-extra-deps.txt) (`ca-certificates`, `file`, `lua5.1`, `sudo`) for
> HTTPS fetches, packaging inspection, and `test.sh` execution. `scripts/check-dependencies.py` enforces that README,
> dependency manifests, Containerfile, and the build workflow stay aligned.

### Manual Build

Build and install Neovim in three commands:

```bash
sudo apt install ninja-build gettext cmake curl git build-essential
git clone --depth 1 --branch v<VERSION> https://github.com/neovim/neovim && cd neovim
make CMAKE_BUILD_TYPE=RelWithDebInfo && cd build && cpack -G DEB && sudo dpkg -i nvim-linux-x86_64.deb
```

### Containerized Build (Recommended for Reproducibility)

Build inside a Podman (or Docker) container matching the target OS — isolates from host system state and ensures
reproducibility:

```bash
# Build the container image (bakes build.sh into the image)
podman build -t neovim-builder .

# Build the default version (outputs .deb to ./output)
mkdir -p output
podman run --rm -v "$(pwd)/output:/output" neovim-builder

# Build a different version (e.g. v0.14.0)
podman run --rm -e VERSION=0.14.0 -v "$(pwd)/output:/output" neovim-builder

# Verify the .deb
# x86_64 builds produce nvim-linux-x86_64.deb; ARM64 builds produce nvim-linux-arm64.deb.
./test.sh output/nvim-linux-x86_64.deb
```

The container image (pinned to the current Ubuntu LTS in the Containerfile) includes all build prerequisites and runs
[`build.sh`](./build.sh) on startup. Set `VERSION` via `-e` to build a specific release; defaults to the version in
`build.sh`. Use `VERSION=latest` to build the latest stable release (the CI workflow uses this for its weekly scheduled
build). The `-v "$(pwd)/output:/output"` mount ensures the `.deb` appears in the `output/` directory on your host.

### Build Output

The build produces `nvim-linux-x86_64.deb` (or `nvim-linux-arm64.deb` on ARM64) in the specified output directory. When
building in the container, this maps to `./output/`.

Neovim's bundled dependencies (libuv, LuaJIT, tree-sitter, and others) are compiled and statically linked — no system
library conflicts.

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

| #   | Check          | Description                                                        |
| --- | -------------- | ------------------------------------------------------------------ |
| 1   | Install        | `dpkg -i` installs cleanly with `update-alternatives` registration |
| 2   | Version        | `nvim --version` reports the expected release version              |
| 3   | Smoke test     | `nvim --headless +q` starts and exits cleanly                      |
| 4   | Runtime health | `nvim --headless +checkhealth +q` runs without crash               |
| 5   | Dependencies   | `ldd` shows no unresolved shared library dependencies              |
| 6   | Alternatives   | `update-alternatives --display vi` shows nvim registered           |
| 7   | Uninstall      | `dpkg -r` removes cleanly and unregisters alternatives             |

These checks are automated in [`test.sh`](./test.sh).

## License

Copyright Neovim contributors. All rights reserved.

Licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0). See
[`LICENSE`](./LICENSE) for the full text.

---

## About This Project

| Item             | Detail                                                                                        |
| ---------------- | --------------------------------------------------------------------------------------------- |
| **Package**      | Neovim built with CPack (upstream-recommended)                                                |
| **Base OS**      | Ubuntu LTS (defined in Containerfile via `ARG UBUNTU_VERSION`)                                |
| **Build system** | Ninja (auto-detected by Neovim's Makefile)                                                    |
| **Dependencies** | Bundled and statically linked (libuv, LuaJIT, tree-sitter, utf8proc, unibilium)               |
| **CI/CD**        | GitHub Actions with container reproducibility                                                 |
| **Verification** | 7-point automated test suite (install, version, smoke, health, deps, alternatives, uninstall) |

## Documentation

- **[AGENTS.md](./AGENTS.md)** — Full agent instructions, research findings, design decisions, staleness guard
- **[docs/build-plan.md](./docs/build-plan.md)** — Build pipeline details, test strategy, versioning approach
- **[docs/resources.md](./docs/resources.md)** — Curated reference resources with evaluation scores
- **[docs/reproducibility.md](./docs/reproducibility.md)** — Build reproducibility approach, guarantees, and limitations
- **[CHANGELOG.md](./CHANGELOG.md)** — Release history (user-facing)
