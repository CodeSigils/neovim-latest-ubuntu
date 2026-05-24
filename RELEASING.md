# Releasing a New Neovim Version

This guide walks you through releasing a new Neovim version as a `.deb` package using this
repository's CI pipeline. It assumes you have write access to the repository.

## Overview

When Neovim releases a new stable version (e.g., v0.13.0), you need to:

1. Check the release exists and is stable
2. Push a matching tag to this repo
3. Let CI build it automatically
4. Confirm the release is published

That's the happy path. The sections below cover that flow and what to do when you need
something different (a custom version, a test build, or a local build).

Important distinction:

- The [GitHub Releases page](https://github.com/CodeSigils/neovim-latest-ubuntu/releases) is updated only by tag pushes.
- Scheduled builds, branch pushes, and manual dispatch builds upload workflow artifacts to the Actions run page instead.

## Prerequisites

- Write access to this GitHub repository
- `git` installed locally
- For local builds: Podman (or Docker), `ninja-build`, `cmake`, `curl`

## Release a new Neovim version via tag

The CI workflow is triggered by pushing a tag matching `v*`. This is the standard release
process.

### 1. Check the latest Neovim release

Before tagging, confirm the version you want to build actually exists:

```bash
# Check the latest stable release
curl -sL https://api.github.com/repos/neovim/neovim/releases/latest \
  | grep '"tag_name":' | head -1
```

Or visit https://github.com/neovim/neovim/releases and look for the latest stable tag
(e.g., `v0.13.0`).

### 2. Tag the new version

Create and push a tag matching the Neovim version:

```bash
# Replace 0.13.0 with the actual version
git tag v0.13.0
git push origin v0.13.0
```

That's it. Pushing the tag triggers the CI pipeline (`.github/workflows/build.yml`).

### 3. Wait for CI to finish

The pipeline does the following in parallel for both architectures (x86_64 and ARM64):

1. **Lints the scripts** — runs `shellcheck` on `build.sh`/`test.sh` and `hadolint` on
   `Containerfile`. If lint fails, the build is blocked — no point building a broken package.
2. **Builds the container image** — installs build tools into `ubuntu:24.04` (pinned to a
   multi-arch manifest digest so the same Containerfile works on both architectures)
3. **Runs build.sh** — clones the tagged Neovim version, compiles with CMake+Ninja,
   packages with CPack into a `.deb` (`nvim-linux-x86_64.deb` or `nvim-linux-aarch64.deb`)
4. **Verifies the artifact** — checks the `.deb` exists in the output directory
5. **Generates checksums** — produces `SHA256SUMS` alongside the `.deb`
6. **Uploads artifacts** — both the `.deb` and per-arch `SHA256SUMS` are stored as
   arch-specific workflow artifacts
7. **Aggregates and releases** — a separate `release` job downloads all arch artifacts,
   regenerates a combined `SHA256SUMS`, and creates the GitHub Release with both `.deb`
   files attached as downloadable assets (tag pushes only)

Monitor the run at: https://github.com/CodeSigils/neovim-latest-ubuntu/actions

### 4. Verify the release

Once CI completes:

- Check the [Releases page](https://github.com/CodeSigils/neovim-latest-ubuntu/releases)
  for the new release with both `.deb` files attached (one per architecture).
- Verify the checksum to confirm integrity:

  ```bash
  # Download both .deb files and the combined SHA256SUMS
  curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/nvim-linux-x86_64.deb
  curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/SHA256SUMS
  sha256sum -c SHA256SUMS
  ```
- Install and verify the package on your architecture:

  ```bash
  # x86_64 systems
  sudo dpkg -i nvim-linux-x86_64.deb

  # ARM64 systems — use the aarch64 build instead
  curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/nvim-linux-aarch64.deb
  sudo dpkg -i nvim-linux-aarch64.deb

  nvim --version
  ```

### 5. Update the changelog

Add an entry to [`CHANGELOG.md`](./CHANGELOG.md) documenting the new release:

```markdown
## [0.13.0] — 2026-XX-YY

### Added

- Built and packaged Neovim v0.13.0 as `.deb`.
```

Commit and push:

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG entry for v0.13.0"
git push origin main
```

## Build a different version (manual dispatch)

If you want to build a specific version (including release candidates like `v0.14.0-rc1`)
without creating a tag:

1. Go to https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml
2. Click **Run workflow**
3. Enter the version (e.g., `0.14.0-rc1`)
4. Click **Run workflow**

CI will build that version and upload the `.deb` as a workflow artifact. It will NOT
create or refresh a GitHub Release (only tag pushes do that).

## Build the latest stable version (local)

To build whatever the latest Neovim stable is, without checking what version that is:

```bash
VERSION=latest ./build.sh
```

This auto-detects the latest tag from the GitHub API and builds it.

## Build a custom version (local)

For testing unreleased versions or custom branches:

```bash
# Build a specific release
./build.sh 0.14.0 ./output

# Build inside a container
mkdir -p output
podman run --rm -e VERSION=0.14.0 -v "$PWD/output:/output" neovim-builder
```

## Nightly Builds

Nightly builds from Neovim's `master` branch run daily (Monday—Sunday) at 06:00 UTC
via [`nightly.yml`](.github/workflows/nightly.yml). They produce `.deb` packages for
both x86_64 and ARM64.

> **Nightly builds do NOT create Releases.** Artifacts are available from the workflow
> run page and expire after 30 days (workflow-configured retention).

### Trigger a manual nightly build

1. Go to https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml
2. Click **Run workflow**
3. Click **Run workflow** again (no input needed)

The workflow builds both architectures, runs the full test suite, and uploads the `.deb`
files as workflow artifacts.

### Download nightly artifacts

From the workflow run page:

1. Open the desired workflow run (https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml)
2. Scroll to the **Artifacts** section
3. Download `nvim-nightly-deb-x86_64` or `nvim-nightly-deb-aarch64`
4. Extract the `.deb` and install:

   ```bash
   # Extract and install (x86_64 example)
   unzip nvim-nightly-deb-x86_64.zip
   sudo dpkg -i output/nvim-linux-x86_64.deb
   nvim --version
   ```

### What gets built

- **Branch**: Neovim `master` (latest development code)
- **Build type**: `RelWithDebInfo` (optimised with debug info — same as upstream nightly)
- **Verification**: Same 7-check test suite as stable releases (install, version, smoke,
  health, dependencies, alternatives, uninstall)
- **Architectures**: x86_64 and ARM64 (both must pass)

## Troubleshooting

### CI says "No .deb package found"

The artifact verification step checks for `.deb` files in the `output/` directory. Possible
causes:

- The Neovim version doesn't exist — check `https://github.com/neovim/neovim/releases`
- A network issue prevented cloning — restart the workflow
- The CMake/CPack config changed upstream — check the build logs

Check the CI run logs for details: the build step output shows the full build log.

### Tag push didn't trigger CI

Ensure the tag matches the `v*` pattern: `git tag v0.13.0` not `git tag 0.13.0` or
`git tag neovim-0.13.0`.

### Build succeeded but no release created

Releases are only created on tag pushes, not on branch pushes, scheduled builds, or manual
dispatch. If you need a GitHub Release entry rather than a workflow artifact, push a tag for
that version.

### The version built is wrong

The CI determines the version with this priority:

1. **Manual dispatch input** — if triggered from the Actions tab
2. **Schedule** — builds `latest` (auto-fetches from GitHub API) on weekly cron (Monday 06:00 UTC)
3. **Git tag** — extracted from the pushed tag (strips the leading `v`)
4. **Default** — `0.12.2` (falls back when none of the above apply)

Both architectures receive the same version from the same priority chain.

Check which trigger you used and verify the version in the CI logs.

### "Permission denied" when pushing

You need write access to the repository. If you're using a personal access token, ensure it
has the `repo` scope.

## How it works (for the curious)

The pipeline works like this:

```
You push tag v0.13.0
    ↓
GitHub Actions triggers build.yml
    ↓
╔═══════════════════════════════════════╗
║  Lint job (runs first)                ║
║  ├─ shellcheck build.sh test.sh       ║
║  └─ hadolint Containerfile            ║
╚═══════════════════════════════════════╝
    ↓
╔═══════════════════════════════════════╗
║  Build job (matrix x86_64 + aarch64)  ║
║  ├─ ubuntu-24.04 → nvim-linux-        ║
║  │  x86_64.deb                        ║
║  └─ ubuntu-24.04-arm → nvim-linux-    ║
║     aarch64.deb                       ║
║  Each matrix entry:                   ║
║  ├─ Docker builds Containerfile       ║
║  │  → neovim-builder image            ║
║  ├─ docker run neovim-builder         ║
║  │  (with VERSION=0.13.0)             ║
║  │  Container executes build.sh:      ║
║  │    1. git clone --branch v0.13.0   ║
║  │    2. make CMAKE_BUILD_TYPE=Rel... ║
║  │    3. cpack -G DEB → .deb          ║
║  ├─ Host verifies .deb exists         ║
║  ├─ sha256sum *.deb > SHA256SUMS      ║
║  └─ Upload artifacts (arch-specific) ║
╚═══════════════════════════════════════╝
    ↓
╔═══════════════════════════════════════╗
║  Release job (tag pushes only)        ║
║  ├─ Download all arch artifacts       ║
║  ├─ Regenerate combined SHA256SUMS    ║
║  └─ softprops/gh-release              ║
║     (attaches both .deb + SHA256SUMS) ║
╚═══════════════════════════════════════╝
    ↓
Users download from Releases page
```

The build script (`build.sh`), container definition (`Containerfile`), and test script
(`test.sh`) are all in the repository — you can inspect or run them locally.

## Reference

- [`build.sh`](./build.sh) — Parameterised build script (arch-agnostic, produces `.deb` per `CMAKE_SYSTEM_PROCESSOR`)
- [`Containerfile`](./Containerfile) — Build environment definition
- [`test.sh`](./test.sh) — 7-check verification script
- [`docs/build-plan.md`](./docs/build-plan.md) — Technical build pipeline details
- [`nightly.yml`](.github/workflows/nightly.yml) — Daily nightly build workflow
- [`AGENTS.md`](./AGENTS.md) — Project knowledge base and decision history
