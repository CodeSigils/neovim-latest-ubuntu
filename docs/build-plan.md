# Build Plan — Neovim Latest deb Package

**Document type:** Plan (design document — implemented and verified) **Status:** Implemented — verified 2026-05-22
**Last updated:** 2026-07

## 1. Approach

Use **Neovim upstream CPack** (Approach A) — the CPack `.deb` generator configured in `cmake.packaging/CMakeLists.txt`.
This is what upstream BUILD.md recommends for local `.deb` creation, and the config ships with every release.

Not using:

- A full `debian/` directory (Approach B) — overkill for local/personal `.deb` distribution; revisit only if PPA uploads
  are needed.
- Hybrid CPack+debhelper (Approach C) — unnecessary complexity at this scope.

This pipeline adapts Neovim's upstream CPack and CMake infrastructure: clone the tag, build via the upstream Makefile wrapper (`make CMAKE_BUILD_TYPE=RelWithDebInfo`), then package as `.deb` using the CPack config that ships with every Neovim release. Upstream's own [release.yml](https://github.com/neovim/neovim/blob/master/.github/workflows/release.yml) uses the same CMake toolchain and CPack machinery, though it switched from DEB to TGZ in PR #22773.

## 2. Prerequisites

### 2.1 Build Dependencies

Install on the build host (Ubuntu LTS or compatible). Source of truth:
[`deps/ubuntu-build-deps.txt`](../deps/ubuntu-build-deps.txt).

```bash
sudo apt update
sudo apt install -y ninja-build gettext cmake curl git build-essential
```

### 2.2 CI / Container Automation Dependencies

The CI/container image installs the same build-host list plus these extras from
[`deps/ubuntu-ci-extra-deps.txt`](../deps/ubuntu-ci-extra-deps.txt):

- `ca-certificates` — HTTPS certificate roots for downloads/API calls
- `file` — package/binary inspection helper inside the build image
- `lintian` — Debian package-policy auditing inside the target container
- `lua5.1` — build/runtime helper package kept in the reproducible image
- `sudo` — required because [`test.sh`](../test.sh) exercises install/remove flows with `dpkg`

`scripts/check-dependencies.py` is the enforcement layer: it fails CI if README prerequisites, dependency manifest
files, Containerfile wiring, and build/test script expectations drift apart.

### 2.3 Runtime Dependencies (auto-detected by CPack)

`CPACK_DEBIAN_PACKAGE_SHLIBDEPS TRUE` in the upstream config uses `dpkg-shlibdeps` to auto-detect shared library
dependencies. The resulting `.deb` will declare depends on the specific `libc6`, `libgcc-s1`, etc. versions found at
build time.

> **LTS targeting:** Runtime deps (e.g., `libc6 (>= 2.43)`) reflect the Ubuntu 26.04 toolchain; packages are
> intentionally not compatible with older Ubuntu releases. This is expected and correct for a native LTS package.

## 3. Build Pipeline

### 3.1 Clone

```bash
VERSION="0.12.3"   # parameterised — change for future releases
git clone --depth 1 --branch "v${VERSION}" https://github.com/neovim/neovim
cd neovim
```

### 3.2 Configure / build via upstream wrapper

```bash
make CMAKE_BUILD_TYPE=RelWithDebInfo
```

The upstream Makefile wraps the CMake configure/build flow and auto-detects Ninja when available. `RelWithDebInfo`
matches the project's current build script and retains debug information useful for testing.

### 3.3 Build output

```bash
ls build/CPackConfig.cmake
```

This compiles bundled dependencies (libuv, LuaJIT, tree-sitter, etc.) into `.deps/` and then builds the `nvim` binary
and CPack configuration.

### 3.4 Package

```bash
cpack -G DEB --config build/CPackConfig.cmake -B /output
```

The `-B /output` flag (binary output directory) is **critical** — it ensures CPack writes the `.deb` to an explicit,
deterministic location. Without it, CPack writes to the current working directory, causing CI artifact-path ambiguity
and pipeline failures.

Output: `nvim-linux-x86_64.deb` (or `nvim-linux-arm64.deb` on ARM) in the output directory.

### 3.5 Full Script (parameterised)

See [`build.sh`](../build.sh) for the actual implementation. Key features:

- **Version**: first positional arg, `VERSION` env var, or `latest` alias (auto-fetches from GitHub API)
- **Output**: second positional arg or `OUTPUT_DIR` env var; defaults to current directory
- **Build tool**: uses Neovim's upstream Makefile wrapper (`make CMAKE_BUILD_TYPE=RelWithDebInfo`), which auto-detects
  Ninja when available
- **Temp dir**: `mktemp -d` with `trap` cleanup
- **Error handling**: checks for missing `.deb` in output, empty version

```bash
# Examples (matched to build.sh v0.12.3+)
./build.sh                          # Build default (0.12.3)
./build.sh 0.13.0 ./out             # Build specific version
VERSION=latest ./build.sh           # Auto-detect latest stable
```

## 4. Test Strategy

### 4.1 Container Testing

All verification occurs in a **Podman container** matching the target OS. This ensures reproducibility and isolates from
host system state.

Podman provides rootless, daemonless containerization on Linux, which reduces host attack surface compared to running
builds directly on the host or using a rootful daemon.

Container image: currently `ubuntu:26.04` (see Containerfile for current version).

### 4.2 Verification Checklist

- [x] Package installs cleanly: `dpkg -i nvim-linux-x86_64.deb` or `dpkg -i nvim-linux-arm64.deb`
- [x] `nvim --version` reports the expected version
- [x] Smoke test: `nvim --headless +q` starts and exits cleanly
- [x] Runtime health: `nvim --headless +checkhealth +q` runs without crash
- [x] No missing shared library dependencies: `ldd $(which nvim)`
- [x] `update-alternatives` registers (check `vi --version` points to nvim)
- [x] Package uninstalls cleanly: `dpkg -r Neovim`

> All checks passed on 2026-05-22 inside a Podman `ubuntu:26.04` container (Containerfile defines the current version).
> Build: Neovim v0.12.3, `CMAKE_BUILD_TYPE=RelWithDebInfo`, output `nvim-linux-x86_64.deb` (20MB, also verified on ARM64
> via CI).

**Alignment with Debian/Ubuntu best practices:** Dependency declarations via `CPACK_DEBIAN_PACKAGE_SHLIBDEPS` and
`update-alternatives` registration (via upstream Neovim's `postinst`/`prerm` scripts inherited from `cmake.packaging/`)
follow the principles outlined in the [Debian Developer's Reference §6](https://www.debian.org/doc/manuals/developers-reference/best-pkging-practices.html)
and [Debian Policy Manual](https://www.debian.org/doc/debian-policy/) for local convenience packages.

### 4.3 Test Script (for automation)

See [`test.sh`](../test.sh) for the actual implementation. Key features:

- **Auto-detection**: version extracted from `.deb` via `dpkg-deb -f` when not provided
- **Check framework**: `check()` function wraps each test with PASS/FAIL tracking
- **Dependency handling**: auto-runs `apt-get install -f` if `dpkg` reports missing deps
- **Realpath**: resolves absolute path before install
- **Summary**: reports total failures at end, exits non-zero on any failure

## 5. CI Artifact Handling

The GitHub Actions workflow uses **explicit artifact paths** to ensure deterministic pipeline behavior:

| Component                       | Implementation                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Container build**             | `docker build -t neovim-builder --build-arg UBUNTU_VERSION=... --build-arg UBUNTU_CODENAME=... --build-arg UBUNTU_SHA256=... -f Containerfile .` (multi-arch manifest digest; version/codename/digest sourced from repo-level variables) |
| **Build execution**             | `docker run --rm -e VERSION=x.y.z -v "$PWD/output:/output" neovim-builder`                                                                                                                                                                                                                                                                                                                        |
| **Artifact path**               | `/output` mounted to `output/` on host                                                                                                                                                                                                                                                                                                                                                            |
| **Architecture matrix**         | `x86_64` on `${{ vars.RUNNER_X86_64 || 'ubuntu-latest' }}` + `aarch64` on `${{ vars.RUNNER_AARCH64 || 'ubuntu-24.04-arm' }}` (both must pass; target OS Ubuntu 26.04 via container; test runs inside the container to match runtime deps) |
| **Lint**                        | 6 checks: `check-dependencies.py` (dep consistency), `check-labels.py` (required repo labels), `shellcheck build.sh test.sh scripts/*.sh`, `check-yaml-syntax.py` (YAML validation), `python3 -m unittest discover` (release readiness gate), `hadolint/hadolint-action@v3.3.0` (Containerfile lint — enforces Dockerfile/Containerfile best practices and catches security and efficiency issues in the build image definition) |
| **Verification**                | `ls output/*.deb` before upload (fail-fast) per arch                                                                                                                                                                                                                                                                                                                                              |
| **Checksums**                   | `sha256sum *.deb > SHA256SUMS` after verification (per arch)                                                                                                                                                                                                                                                                                                                                      |
| **Package-policy audit**        | Non-blocking `lintian` run inside the pinned Ubuntu target container per built `.deb` so Debian/Ubuntu policy findings match the package's target environment without blocking CPack convenience packages                                                                                                                                                                                         |
| **Artifact upload**             | `actions/upload-artifact@v7` with arch-specific name (`nvim-linux-deb-${{ matrix.arch }}`)                                                                                                                                                                                                                                                                                                        |
| **Release aggregation**         | Separate `release` job downloads all arch artifacts, generates combined `SHA256SUMS`, creates Release with `softprops/action-gh-release@v3`                                                                                                                                                                                                                                                       |
| **Trigger (branch push)**       | `branches: [main]` with `paths-ignore: ['*.md', LICENSE, docs/**, .gitignore, .gitattributes, .mailmap, .githooks/**, .github/dependabot.yml, .github/workflows/nightly.yml, .github/workflows/check-author.yml, .github/workflows/codeql.yml]` — doc/metadata/workflow-edit pushes skip the build pipeline, but excluded workflows (author guard, codeql) still run via their own triggers |
| **Trigger (tag push)**          | `tags: ['v*']` — path filters NOT evaluated for tags (GitHub Actions behavior); tag pushes always build                                                                                                                                                                                                                                                                                           |
| **Trigger (PR)**                | `pull_request: [main]` with doc/metadata paths ignored; workflow changes, including CodeQL workflow edits, still run lint + build                                                                                                                                                                                                                                                                 |
| **Trigger (workflow_dispatch)** | Manual trigger with optional `version` input — accepts stable version string (e.g. `0.14.0`), `latest`, or empty (defaults to `latest` — auto-detects current stable via GitHub API)                                                                                                                                                                                                              |
| **Trigger (schedule)**          | Weekly Monday 06:00 UTC — builds `latest` stable                                                                                                                                                                                                                                                                                                                                                  |

**Key principle**: Keep artifact paths explicit at every boundary — container, host workspace, artifact upload, and
release aggregation.

## 6. Versioning Strategy

| Parameter        | Value                                                                                            | Notes                          |
| ---------------- | ------------------------------------------------------------------------------------------------ | ------------------------------ |
| `VERSION`        | `0.12.3` (default)                                                                               | Git tag — `v${VERSION}`        |
| Output name      | `nvim-linux-{arch}.deb`                                                                          | From upstream CPack config     |
| Script parameter | `VERSION` as first arg or env var (`OUTPUT_DIR` is container-managed in CI/local container runs) | Future-proof for version bumps |

For new releases: change `VERSION` and re-run. No structural changes expected between Neovim minor versions unless
CMake/CPack config changes upstream.

## 7. Files Created

| File                          | Purpose                                                                | Status                                                              |
| ----------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `build.sh`                    | Parameterised build script (§3.5)                                      | Done                                                                |
| `Containerfile`               | Podman image for reproducible builds                                   | Done — updated for explicit arg passing & cpack output dir          |
| `test.sh`                     | Verification script (§4.3)                                             | Done                                                                |
| `.github/workflows/build.yml` | CI automation (tag/main/dispatch triggers, doc-only pushes skip build) | Done — explicit paths, fail-fast checks, paths-ignore for doc files |

> **Build run**: All files tested successfully inside Podman on 2026-05-22. **CI verification**: Workflow tested —
> container builds, build.sh executes, artifacts generated and uploaded, Release creation succeeds. **Containerfile
> updates**: Added `COPY --chmod=755` for build-neovim (eliminates separate RUN layer); CMD now passes VERSION and
> OUTPUT_DIR args. **CI workflow updates**: Explicit `-v "$PWD/output:/output"` mount; artifact verification step added;
> unified version input handling.

## 8. Release Process

### 8.1 CI Release

The project has a GitHub Actions workflow (`.github/workflows/build.yml`) that automates building and releasing the
`.deb`:

1. **Tag push** (`git tag v0.13.0 && git push origin v0.13.0`) → CI builds matrix (x86_64 + aarch64) → release job
   aggregates artifacts
2. **Main push** (non-doc changes) → CI builds matrix; doc/metadata/workflow-only pushes (`*.md`, `LICENSE`, `docs/**`,
   `.mailmap`, `.gitignore`, `.gitattributes`, `.githooks/**`, `.github/dependabot.yml`, `nightly.yml`,
   `check-author.yml`, `codeql.yml`) skip the pipeline (each skipped workflow runs independently)
3. **Artifacts** → both `.deb` files (`nvim-linux-x86_64.deb` + `nvim-linux-arm64.deb`) uploaded as release assets with
   combined SHA256SUMS
4. **Users** → download the correct `.deb` for their architecture from Releases page and install via `dpkg -i`

> See [`RELEASING.md`](../RELEASING.md) for the full human-readable release process guide.

### 8.2 Manual Build

For testing or offline distribution:

```bash
./build.sh                 # builds default version (0.12.3)
./build.sh 0.14.0          # builds specific version
VERSION=latest ./build.sh  # auto-fetches latest stable tag
```

Output is written to the current directory or `$OUTPUT_DIR`.

## 8. Reference

- **[docs/resources.md](./resources.md)** — Curated resource evaluations
- **[README.md](../README.md)** — How-to guide (Build from Source section)
