# Release and Operations Guide

This repository packages the latest **stable Neovim release** for the current Ubuntu LTS target. Neovim itself does
not define an LTS channel; `master`/nightly and stable releases are handled separately.

## Stable-release policy

The daily stable workflow is candidate-first:

1. Resolve GitHub's latest published upstream Neovim release.
2. Resolve its tag to an exact upstream commit SHA.
3. Compare it with this repository's published GitHub Releases and required assets.
4. Build and verify x86_64 and ARM64 packages from that exact commit.
5. Create a draft release, attach packages, checksums, and build metadata, attest both packages, then publish.

Maintenance releases (`X.Y.Z` where `Z > 0`) publish automatically after all gates pass. Feature releases (`X.Y.0`)
build automatically but the publish job uses the protected `release-reviewed` environment and waits for maintainer
approval. Routine detections do not open issues; failures create or update a `new-release` issue and a later successful
run closes it.

The published GitHub Release—not a Git tag—is the source of truth for whether a version shipped. Repository-level
immutable-release enforcement prevents published tags or assets from being moved, replaced, or deleted.

## Normal operation

No maintainer action is required for a maintenance release. Monitor the
[`Build and release stable Neovim`](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml)
workflow only when it reports a failure.

For a feature release:

1. Open the pending `release-reviewed` deployment in the workflow run.
2. Review upstream release notes and the successful package matrix.
3. Approve the environment deployment to publish.

The release job resumes an existing draft release safely, which makes asset-upload failures retryable without moving or
reusing a published tag.

## Manual builds and recovery

Run the stable workflow from the Actions tab with:

- `version`: an upstream stable version without `v`; empty means latest.
- `publish`: leave disabled for an artifact-only candidate build; enable it to publish after verification.

Manual publication follows the same feature-release approval policy as scheduled publication. Pre-releases and nightly
versions are intentionally rejected by the stable release planner.

Tag pushes matching `v*` remain supported as an emergency compatibility path. Before using that path, run:

```bash
scripts/check-release-readiness.sh X.Y.Z
git tag vX.Y.Z
git push origin vX.Y.Z
```

Candidate-first scheduled or manual publication is preferred because it creates the tag only after both packages pass.
For a packaging-only rebuild, use `X.Y.Z-N`, where `N` is a positive Debian package revision.

## Release verification

A complete release contains:

- `nvim-linux-x86_64.deb`
- `nvim-linux-arm64.deb`
- `SHA256SUMS`
- `BUILD-METADATA-amd64.json`
- `BUILD-METADATA-arm64.json`

Verify a downloaded package:

```bash
sha256sum -c SHA256SUMS
gh attestation verify nvim-linux-x86_64.deb \
  -R CodeSigils/neovim-latest-ubuntu
dpkg-deb -f nvim-linux-x86_64.deb Version Architecture
```

Each metadata document records the upstream tag and commit, packaging repository commit, target Ubuntu image digest,
Debian architecture, package version, and package SHA256.

## Package gates

The reusable package workflow applies the same architecture matrix and verification to stable and nightly builds:

- Shared ShellCheck, Hadolint, dependency, label, YAML, actionlint, and regression-test gates
- Native x86_64 and ARM64 builds
- Exact Debian architecture and filename checks
- Independent package/runtime version expectations
- Install, headless runtime, shared-library, alternatives, and removal tests
- Per-architecture checksums and build metadata

Stable packages use `CMAKE_BUILD_TYPE=Release`; nightlies use `RelWithDebInfo`. Stable builds also run Lintian. Known
upstream CPack findings are recorded in `scripts/lintian-allowlist.txt`; any new error or warning tag fails the build.

## Nightly builds

The nightly workflow builds Neovim `master` daily and uploads 30-day workflow artifacts. Nightlies never create GitHub
Releases. A single self-healing `nightly` issue is opened only while scheduled builds are failing.

## Troubleshooting

### Stable workflow says the release already exists

The planner found a published release containing both packages and `SHA256SUMS`, so it correctly skipped the expensive
build. Use a package-revision version for a packaging rebuild; do not mutate a published release.

### Release job is waiting

Feature releases wait on the `release-reviewed` environment. Review and approve the deployment in GitHub Actions.

### A draft release remains after failure

Fix the underlying failure and rerun the workflow. The release job uploads the verified assets with `--clobber`, updates
the notes, and publishes the existing draft. Do not delete or recreate a published release.

### Upstream resolution fails

The planner uses the workflow's authenticated GitHub token. Check GitHub API availability and token permissions, then
rerun the failed job. It never silently falls back to a hardcoded version.

### Local build

```bash
# Latest stable, Release build
VERSION=latest ./build.sh

# Specific stable version
./build.sh 0.12.5 ./output

# Nightly, RelWithDebInfo build
./build.sh nightly ./output
```
