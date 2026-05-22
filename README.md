# Neovim Latest — deb Package for Ubuntu

Build the latest stable [Neovim](https://neovim.io/) as a `.deb` package for Ubuntu, Linux Mint, and Debian — no snaps, no Flatpaks, no AppImages. Just `dpkg -i` and it's installed system-wide.

## Quick Start

Build and install in three commands:

```bash
sudo apt install ninja-build gettext cmake curl build-essential
git clone --depth 1 --branch v0.12.2 https://github.com/neovim/neovim && cd neovim
make CMAKE_BUILD_TYPE=RelWithDebInfo && cd build && cpack -G DEB && sudo dpkg -i nvim-linux-x86_64.deb
```

> Pre-built releases are also available — see [Download from Releases](#download-from-releases).

## Why This?

Neovim upstream stopped shipping `.deb` packages in v0.9. The alternatives all have trade-offs:

| Approach | Drawback |
| --- | --- |
| `apt install neovim` | Often lags behind latest release by months |
| Official AppImage | No system-wide `vi`/`editor` symlink integration |
| Snap (`snap install nvim`) | Sandboxing breaks file access, slow startup |
| Build from source manually | No package manager tracking, no clean uninstall |

This project gives you the latest Neovim as a proper system package — `update-alternatives` registration, clean uninstall, dependency tracking.

## Download from Releases

If a tag has been pushed to GitHub, the CI pipeline produces a `.deb` and attaches it to a release:

```bash
# Install the latest stable release
curl -LO https://github.com/neovim-latest-ubuntu/neovim-latest-ubuntu/releases/latest/download/nvim-linux-x86_64.deb
sudo dpkg -i nvim-linux-x86_64.deb
```

Replace the URL with your repository owner and name.

## Build from Source

### Prerequisites

```bash
sudo apt install ninja-build gettext cmake curl build-essential
```

| Tool                    | Minimum version |
| ----------------------- | --------------- |
| [ninja-build]           | 1.11            |
| [gettext]               | 0.21            |
| [cmake]                 | 3.25            |
| [unzip]                 | 6.00            |
| curl                    | 7.88            |

[ninja-build]: https://ninja-build.org/
[gettext]: https://www.gnu.org/software/gettext/
[cmake]: https://cmake.org/
[unzip]: https://infozip.sourceforge.net/UnZip.html#Release

### Containerized Build (Recommended for Reproducibility)

Build inside a Podman (or Docker) container matching the target OS — isolates from host
system state and ensures reproducibility:

```bash
# Build the container image (bakes build.sh into the image)
podman build -t neovim-builder .

# Build Neovim 0.12.2 (outputs .deb to ./output)
mkdir -p output
podman run --rm -v "$(pwd)/output:/output" neovim-builder

# Build a different version
podman run --rm -e VERSION=0.14.0 -v "$(pwd)/output:/output" neovim-builder

# Verify the .deb
./test.sh output/nvim-linux-x86_64.deb
```

The container image (`ubuntu:24.04`) includes all build prerequisites and runs
[`build.sh`](./build.sh) on startup. Set `VERSION` via `-e` to build a specific release;
defaults to `0.12.2`. The `-v "$(pwd)/output:/output"` mount ensures the `.deb` appears in
the `output/` directory on your host.

### Output

The build produces `nvim-linux-x86_64.deb` (or `nvim-linux-aarch64.deb` on ARM) in the
specified output directory. When building in the container, this maps to `./output/`.

Neovim's bundled dependencies (libuv, LuaJIT, tree-sitter, and others) are compiled and statically linked — no system library conflicts.

## Compilation Details

- Debian clang version 14.0.6
- Target: x86_64-pc-linux-gnu
- Thread model: posix
- Architecture: amd64
- Depends: libc6 (>= 2.34), libgcc-s1 (>= 3.3)

## Verification

Each build is verified against these checks:

| # | Check | Description |
| --- |------- | ------------- |
| 1 | Install | `dpkg -i` installs cleanly with `update-alternatives` registration |
| 2 | Version | `nvim --version` reports the expected release version |
| 3 | Dependencies | `ldd` shows no unresolved shared library dependencies |
| 4 | Alternatives | `update-alternatives --display vi` shows nvim registered |
| 5 | Uninstall | `dpkg -r` removes cleanly and unregisters alternatives |

These checks are automated in [`test.sh`](./test.sh).

## License

Copyright Neovim contributors. All rights reserved.

Licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
See [`LICENSE`](./LICENSE) for the full text.
