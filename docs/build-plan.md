# Build Plan — Neovim Latest deb Package

**Document type:** Plan (design document — implemented and verified)
**Status:** Implemented — verified 2026-05-22
**Last updated:** 2026-05-24

## 1. Approach

Use **Neovim upstream CPack** (Approach A) — the CPack `.deb` generator configured in
`cmake.packaging/CMakeLists.txt`. This is what upstream BUILD.md recommends for local `.deb`
creation, and the config ships with every release.

Not using:
- A full `debian/` directory (Approach B) — overkill for local/personal `.deb` distribution;
  revisit only if PPA uploads are needed.
- Hybrid CPack+debhelper (Approach C) — unnecessary complexity at this scope.

## 2. Prerequisites

### 2.1 Build Dependencies

Install on the build host (Ubuntu 24.04 Noble or compatible):

```bash
sudo apt update
sudo apt install -y ninja-build gettext cmake curl build-essential
```

### 2.2 Runtime Dependencies (auto-detected by CPack)

`CPACK_DEBIAN_PACKAGE_SHLIBDEPS TRUE` in the upstream config uses `dpkg-shlibdeps` to
auto-detect shared library dependencies. The resulting `.deb` will declare depends on the
specific `libc6`, `libgcc-s1`, etc. versions found at build time.

## 3. Build Pipeline

### 3.1 Clone

```bash
VERSION="0.12.2"   # parameterised — change for future releases
git clone --depth 1 --branch "v${VERSION}" https://github.com/neovim/neovim
cd neovim
```

### 3.2 Configure

```bash
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo
```

`RelWithDebInfo` retains assertions (useful for manual testing). Switch to `Release` for
final packaging.

### 3.3 Build

```bash
cmake --build build --target package
```

This compiles bundled dependencies (libuv, LuaJIT, tree-sitter, etc.) into `.deps/` and
then builds the `nvim` binary.

### 3.4 Package

```bash
cpack -G DEB --config build/CPackConfig.cmake -B /output
```

The `-B /output` flag (binary output directory) is **critical** — it ensures CPack writes the
`.deb` to an explicit, deterministic location. Without it, CPack writes to the current working
directory, causing CI artifact-path ambiguity and pipeline failures.

Output: `nvim-linux-x86_64.deb` (or `nvim-linux-arm64.deb` on ARM) in the output directory.

### 3.5 Full Script (parameterised)

See [`build.sh`](../build.sh) for the actual implementation. Key features:

- **Version**: first positional arg, `VERSION` env var, or `latest` alias (auto-fetches from GitHub API)
- **Output**: second positional arg or `OUTPUT_DIR` env var; defaults to current directory
- **Build tool**: uses direct CMake+Ninja (`cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo` then `cmake --build build --target package`)
- **Temp dir**: `mktemp -d` with `trap` cleanup
- **Error handling**: checks for missing `.deb` in output, empty version

```bash
# Examples (matched to build.sh v0.12.2+)
./build.sh                          # Build default (0.12.2)
./build.sh 0.13.0 ./out             # Build specific version
VERSION=latest ./build.sh           # Auto-detect latest stable
```

## 4. Test Strategy

### 4.1 Container Testing

All verification occurs in a **Podman container** matching the target OS. This ensures
reproducibility and isolates from host system state.

Container image: `ubuntu:24.04`.

### 4.2 Verification Checklist

- [x] Package installs cleanly: `dpkg -i nvim-linux-$(uname -m).deb`
- [x] `nvim --version` reports the expected version
- [x] Smoke test: `nvim --headless +q` starts and exits cleanly
- [x] Runtime health: `nvim --headless +checkhealth +q` runs without crash
- [x] No missing shared library dependencies: `ldd $(which nvim)`
- [x] `update-alternatives` registers (check `vi --version` points to nvim)
- [x] Package uninstalls cleanly: `dpkg -r Neovim`

> All checks passed on 2026-05-22 inside a Podman `ubuntu:24.04` container.
> Build: Neovim v0.12.2, `CMAKE_BUILD_TYPE=RelWithDebInfo`, output `nvim-linux-x86_64.deb` (20MB, also verified on ARM64 via CI).

### 4.3 Test Script (for automation)

See [`test.sh`](../test.sh) for the actual implementation. Key features:

- **Auto-detection**: version extracted from `.deb` via `dpkg-deb -f` when not provided
- **Check framework**: `check()` function wraps each test with PASS/FAIL tracking
- **Dependency handling**: auto-runs `apt-get install -f` if `dpkg` reports missing deps
- **Realpath**: resolves absolute path before install
- **Summary**: reports total failures at end, exits non-zero on any failure

## 5. CI Artifact Handling

The GitHub Actions workflow uses **explicit artifact paths** to ensure deterministic pipeline behavior:

| Component | Implementation |
|---|---|
| **Container build** | `docker build -t neovim-builder -f Containerfile .` (multi-arch manifest digest) |
| **Build execution** | `docker run --rm -e VERSION=x.y.z -v "$PWD/output:/output" neovim-builder` |
| **Artifact path** | `/output` mounted to `output/` on host |
| **Architecture matrix** | `x86_64` on `ubuntu-24.04` + `aarch64` on `ubuntu-24.04-arm` (both must pass) |
| **Lint** | `shellcheck build.sh test.sh` + `hadolint Containerfile` via `hadolint/hadolint-action@v3.3.0` |
| **Verification** | `ls output/*.deb` before upload (fail-fast) per arch |
| **Checksums** | `sha256sum *.deb > SHA256SUMS` after verification (per arch) |
| **Artifact upload** | `actions/upload-artifact@v7` with arch-specific name (`nvim-linux-deb-${{ matrix.arch }}`) |
| **Release aggregation** | Separate `release` job downloads all arch artifacts, generates combined `SHA256SUMS`, creates Release with `softprops/action-gh-release@v3` |

**Key principle**: Explicit paths eliminate ambiguity. Every tool knows exactly where to write and read artifacts.

## 6. Versioning Strategy

| Parameter | Value | Notes |
|---|---|---|
| `VERSION` | `0.12.2` (default) | Git tag — `v${VERSION}` |
| Output name | `nvim-linux-{arch}.deb` | From upstream CPack config |
| Script parameter | `VERSION` as first arg or env var (`OUTPUT_DIR` is container-managed in CI/local container runs) | Future-proof for version bumps |

For new releases: change `VERSION` and re-run. No structural changes expected between
Neovim minor versions unless CMake/CPack config changes upstream.

## 6. Files to Create

| File | Purpose | Status |
|---|---|---|
| `build.sh` | Parameterised build script (§3.5) | Done |
| `Containerfile` | Podman image for reproducible builds | Done — updated for explicit arg passing & cpack output dir |
| `test.sh` | Verification script (§4.3) | Done |
| `.github/workflows/build.yml` | CI automation (tag/main/dispatch triggers) | Done — refactored for explicit paths & fail-fast checks |

> **Build run**: All files tested successfully inside Podman on 2026-05-22.
> **CI verification**: Workflow tested — container builds, build.sh executes, artifacts generated and uploaded, Release creation succeeds.
> **Containerfile updates**: Added `COPY --chmod=755` for build-neovim (eliminates separate RUN layer); CMD now passes VERSION and OUTPUT_DIR args.
> **CI workflow updates**: Explicit `-v "$PWD/output:/output"` mount; artifact verification step added; unified version input handling.

## 7. Release Process

### 7.1 CI Release

The project has a GitHub Actions workflow (`.github/workflows/build.yml`) that automates
building and releasing the `.deb`:

1. **Tag push** (`git tag v0.13.0 && git push origin v0.13.0`) → CI builds matrix (x86_64 + aarch64) → release job aggregates artifacts
2. **Artifacts** → both `.deb` files (`nvim-linux-x86_64.deb` + `nvim-linux-arm64.deb`) uploaded as release assets with combined SHA256SUMS
3. **Users** → download the correct `.deb` for their architecture from Releases page and install via `dpkg -i`

> See [`RELEASING.md`](../RELEASING.md) for the full human-readable release process guide.

### 7.2 Manual Build

For testing or offline distribution:

```bash
./build.sh                 # builds default version (0.12.2)
./build.sh 0.14.0          # builds specific version
VERSION=latest ./build.sh  # auto-fetches latest stable tag
```

Output is written to the current directory or `$OUTPUT_DIR`.

## 8. Reference

- AGENTS.md §3.5 — Full research findings
- docs/resources.md — Curated resource evaluations
- README.md — How-to guide (Build from Source section)
