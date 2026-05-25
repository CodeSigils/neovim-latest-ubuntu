# Releasing a New Neovim Version

This guide covers every way to build and distribute Neovim as a `.deb` package via
this repository's CI pipeline — from a one-command tag push (the happy path) to
local container builds for testing.

## Quick reference

| Method | Trigger | Creates Release? | Use when |
|--------|---------|-----------------|----------|
| Tag push | `git push origin v0.13.0` | Yes | Official stable release |
| Manual dispatch | Actions tab → Run workflow | No | RC, pre-release, or ad-hoc build |
| Schedule | Weekly cron (Mon 06:00 UTC) | No | Latest stable, automated |
| Nightly | Daily cron (06:00 UTC) | No | Track master branch |
| Local build | `./build.sh 0.13.0` | — | Testing, unreleased versions |

> **Tag pushes are the only trigger that creates a GitHub Release.** All other
> methods upload `.deb` artifacts to the workflow run page instead.

---

## Release a stable version (tag push)

The standard release flow. Push a tag and let CI do the rest.

### Release version policy

This project currently tracks upstream Neovim stable versions exactly. Use the
same tag as upstream, for example `v0.13.0`, and create a GitHub Release only
when that upstream release exists and this repository has not already released
the same tag.

Before tagging, check both upstream and this repository:

```bash
# Latest upstream Neovim release
curl -sL https://api.github.com/repos/neovim/neovim/releases/latest \
  | grep '"tag_name":' | head -1

# Existing local/remote tags and GitHub Releases
git tag --list 'v*' --sort=-version:refname | head
git ls-remote --tags origin 'v*'
gh release list --limit 20
```

Do not reuse an existing tag. Published tags and Releases are treated as
immutable. If upstream latest is already released here, wait for the next
upstream Neovim release.

Do not use packaging suffix tags such as `v0.12.2-1` unless the workflow has
explicit package-revision support. Today, the release workflow strips only the
leading `v` and passes the rest to `build.sh` as the upstream Neovim version, so
a suffix tag would make CI look for an upstream version that likely does not
exist.

### 1. Confirm the version exists

```bash
curl -sL https://api.github.com/repos/neovim/neovim/releases/latest \
  | grep '"tag_name":' | head -1
```

Or visit [neovim/neovim/releases](https://github.com/neovim/neovim/releases)
and look for the latest stable tag (e.g. `v0.13.0`).

### 2. Tag and push

```bash
git tag v0.13.0
git push origin v0.13.0
```

That's it. Pushing the tag triggers the CI pipeline.

### 3. Monitor CI

Watch the run at https://github.com/CodeSigils/neovim-latest-ubuntu/actions

The pipeline runs in parallel for **x86_64** and **ARM64**:

1. **Lint** — `shellcheck` on `build.sh`/`test.sh`, `hadolint` on `Containerfile`, YAML syntax validation.
   If lint fails, the build is blocked.
2. **Build** — Container image builds from the Ubuntu LTS base image, then `build.sh` clones
   Neovim at the tagged version, builds through its upstream Makefile wrapper
   (CMake + Ninja), and packages with CPack into a `.deb`.
3. **Verify** — Checks the `.deb` exists, generates `SHA256SUMS`, runs the full
   7-check test suite, and performs a non-blocking `lintian` package-policy audit.
4. **Release** — Aggregates both architecture artifacts, regenerates a combined
   `SHA256SUMS`, attests provenance, and creates a GitHub Release with all assets attached.

### 4. Verify the release

Once CI finishes:

- Check the [Releases page](https://github.com/CodeSigils/neovim-latest-ubuntu/releases)
  for the new entry with both `.deb` files attached.
- Verify integrity:

  ```bash
  curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/nvim-linux-x86_64.deb
  curl -LO https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest/download/SHA256SUMS
  sha256sum -c SHA256SUMS
  ```

- Install and test:

  ```bash
  sudo dpkg -i nvim-linux-x86_64.deb
  nvim --version
  ```

### 5. Update the changelog

Add an entry to [`CHANGELOG.md`](./CHANGELOG.md):

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

---

## Build a specific version (manual dispatch)

Use the Actions tab to build any version — including release candidates like
`v0.14.0-rc1` — without creating a tag.

1. Go to https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/build.yml
2. Click **Run workflow**
3. Enter the version (e.g. `0.14.0-rc1`)
4. Click **Run workflow**

CI builds that version and uploads the `.deb` as a workflow artifact. No Release
will be created — use this for testing.

---

## Build locally

### Latest stable (auto-detect)

```bash
VERSION=latest ./build.sh
```

This fetches the latest Neovim tag from the GitHub API and builds it.

### Custom version

```bash
# Direct build
./build.sh 0.14.0 ./output

# Containerised build
mkdir -p output
podman run --rm -e VERSION=0.14.0 -v "$PWD/output:/output" neovim-builder
```

---

## Nightly builds

Neovim's `master` branch is built daily at **06:00 UTC** (every day) via
[`nightly.yml`](.github/workflows/nightly.yml). Both architectures are built.

> **Nightlies do not create Releases.** Artifacts are available from the workflow
> run page and expire after 30 days.

### Trigger a manual nightly

Go to https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml
and click **Run workflow** (no input needed).

### Download nightly artifacts

1. Open the [workflow run page](https://github.com/CodeSigils/neovim-latest-ubuntu/actions/workflows/nightly.yml)
2. Scroll to **Artifacts**
3. Download `nvim-nightly-deb-x86_64` or `nvim-nightly-deb-aarch64`
4. Extract and install:

   ```bash
   unzip nvim-nightly-deb-x86_64.zip
   sudo dpkg -i output/nvim-linux-x86_64.deb
   nvim --version
   ```

### What gets built

| | |
|---|---|
| **Branch** | Neovim `master` |
| **Build type** | `RelWithDebInfo` (optimised with debug info) |
| **Verification** | Same 7-check suite as stable releases |
| **Architectures** | x86_64 + ARM64 (both must pass) |

---

## Troubleshooting

### "No .deb package found"

The verify step checks `output/*.deb`. Possible causes:

- The Neovim version doesn't exist — verify on the [releases page](https://github.com/neovim/neovim/releases)
- A network issue prevented cloning — re-run the workflow
- The CMake/CPack config changed upstream — check build logs

### Tag push didn't trigger CI

Tags must match the `v*` pattern. Use `git tag v0.13.0`, not `0.13.0` or `neovim-0.13.0`.

### Build succeeded but no release created

Releases are only created on tag pushes. If you used manual dispatch, scheduled
build, or a branch push, the `.deb` is stored as a workflow artifact only.
Push a tag to create a Release.

### apt wants to replace or downgrade Neovim

This project intentionally uses the Debian package name `neovim` so Ubuntu's
package manager treats it as the system package. To pin it:

```bash
sudo apt-mark hold neovim
# Later, to resume normal apt upgrades:
sudo apt-mark unhold neovim
```

### Wrong version was built

The CI determines the version with this priority chain:

1. **Manual dispatch input** — from the Actions tab
2. **Schedule** — builds `latest` (auto-fetched from GitHub API)
3. **Git tag** — extracted from the pushed tag (`v` prefix stripped)
4. **Default** — `0.12.2` (fallback)

Check which trigger you used and verify the version in the CI logs.

### "Permission denied" when pushing

You need write access to the repository. If using a personal access token,
ensure it has the `repo` scope.

---

## Pipeline overview

```text
You push tag v0.13.0
    ↓
GitHub Actions triggers build.yml
    ↓
╔═══════════════════════════════════════════╗
║  Lint job                                 ║
║  ├─ shellcheck build.sh test.sh           ║
║  ├─ hadolint Containerfile                ║
║  └─ Python YAML validation                ║
╚═══════════════════════════════════════════╝
    ↓
╔═══════════════════════════════════════════╗
║  Build job (matrix: x86_64 + aarch64)     ║
║                                           ║
║  Each matrix entry:                       ║
║  ├─ docker build → neovim-builder         ║
║  ├─ docker run (VERSION=0.13.0):          ║
║  │    1. git clone --branch v0.13.0       ║
║  │    2. make (CMake + Ninja)             ║
║  │    3. cpack -G DEB → .deb              ║
║  ├─ Verify artifact exists                ║
║  ├─ sha256sum > SHA256SUMS                ║
║  ├─ test.sh (7 checks)                    ║
║  ├─ lintian audit (non-blocking)          ║
║  └─ Upload arch-specific artifacts        ║
╚═══════════════════════════════════════════╝
    ↓
╔═══════════════════════════════════════════╗
║  Release job (tag pushes only)            ║
║  ├─ Download all arch artifacts            ║
║  ├─ Regenerate combined SHA256SUMS         ║
║  ├─ Attest build provenance               ║
║  └─ softprops/action-gh-release            ║
╚═══════════════════════════════════════════╝
    ↓
Users download from Releases page
```

All pipeline files are in the repository:

- [`build.sh`](./build.sh) — parameterised build script
- [`Containerfile`](./Containerfile) — build environment definition
- [`test.sh`](./test.sh) — 7-check verification script
- [`docs/build-plan.md`](./docs/build-plan.md) — technical pipeline details
- [`.github/workflows/nightly.yml`](.github/workflows/nightly.yml) — daily nightly build
- [`AGENTS.md`](./AGENTS.md) — project knowledge base and decision history
