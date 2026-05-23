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

The pipeline does the following:

1. **Builds the container image** — installs build tools into `ubuntu:24.04`
2. **Runs build.sh** — clones the tagged Neovim version, compiles with CMake+Ninja,
   packages with CPack into a `.deb`
3. **Verifies the artifact** — checks the `.deb` exists in the output directory
4. **Uploads the artifact** — available as a workflow run artifact
5. **Creates a GitHub Release** — attaches the `.deb` as a downloadable asset

Monitor the run at: https://github.com/CodeSigils/neovim-latest-ubuntu/actions

### 4. Verify the release

Once CI completes:

- Check the [Releases page](https://github.com/CodeSigils/neovim-latest-ubuntu/releases)
  for the new release with the `.deb` attached.
- Download and test on a clean system:

  ```bash
  curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/nvim-linux-x86_64.deb
  sudo dpkg -i nvim-linux-x86_64.deb
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
create a GitHub Release (only tag pushes do that).

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

Releases are only created on tag pushes, not on branch pushes or manual dispatch. If you
need a release from a manual build, push a tag for that version.

### The version built is wrong

The CI determines the version with this priority:

1. **Manual dispatch input** — if triggered from the Actions tab
2. **Git tag** — extracted from the pushed tag (strips the leading `v`)
3. **Default** — `0.12.2` (falls back when neither of the above applies)

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
Docker builds the Containerfile → neovim-builder image
    ↓
docker run neovim-builder (with VERSION=0.13.0)
    ↓
Container executes build.sh:
  1. git clone --branch v0.13.0 neovim
  2. make CMAKE_BUILD_TYPE=RelWithDebInfo
  3. cpack -G DEB → nvim-linux-x86_64.deb
    ↓
Host verifies .deb exists in output/
    ↓
actions/upload-artifact uploads the .deb
    ↓
softprops/action-gh-release creates a GitHub Release
    ↓
Users download from Releases page
```

The build script (`build.sh`), container definition (`Containerfile`), and test script
(`test.sh`) are all in the repository — you can inspect or run them locally.

## Reference

- [`build.sh`](./build.sh) — Parameterised build script
- [`Containerfile`](./Containerfile) — Build environment definition
- [`test.sh`](./test.sh) — 5-check verification script
- [`docs/build-plan.md`](./docs/build-plan.md) — Technical build pipeline details
- [`AGENTS.md`](./AGENTS.md) — Project knowledge base and decision history
