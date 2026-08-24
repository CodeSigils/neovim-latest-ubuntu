# Reproducibility — Neovim Latest deb Package

**Document type:** Explanation (Diataxis)

**Status:** Implemented

## What "Reproducible" Means Here

This project produces a `.deb` package from Neovim source code. **Reproducibility** means:

> Given the same exact Neovim source commit, target architecture, base image, and resolved build dependencies, the
> pipeline is intended to produce a functionally equivalent `.deb` that passes the same verification checks.

This is a **functional-replayability goal**, not a claim of byte-for-byte reproducibility. The pipeline now derives
`SOURCE_DATE_EPOCH` from the exact upstream commit and CPack uses it for Debian archive timestamps, but Ubuntu apt
packages remain rolling unless a snapshot is selected. Independent rebuild comparisons are required before describing
the package as reproducible in the strict [Reproducible Builds](https://reproducible-builds.org/) sense.

## How the Pipeline Supports Functional Replay

### 1. Pinned Base Image

The [`Containerfile`](../Containerfile) pins the current Ubuntu LTS base image to a specific multi-architecture SHA256
digest. The `UBUNTU_VERSION`, `UBUNTU_CODENAME`, and `UBUNTU_SHA256` values come from repository variables in CI, with
public fallbacks in the reusable package workflow and `Containerfile`. Those executable files are the source of truth
for the current values.

`UBUNTU_APT_SNAPSHOT` is an optional build argument rather than a long-lived repository variable because snapshots are
an operator-selected replay input.

### 2. Parameterized Build Script

`build.sh` accepts positional or environment inputs for the package identity and output. CI also supplies an exact
source commit. The default `latest` version and Ubuntu apt indexes intentionally remain rolling:

| Parameter          | Source                                                     | Default                                       |
| ------------------ | ---------------------------------------------------------- | --------------------------------------------- |
| `VERSION`          | First arg or env var; `latest` auto-detects current stable | `latest`                                      |
| `OUTPUT_DIR`       | Second arg or env var                                      | `.` in `build.sh`; `/output` in the container |
| `PACKAGE_REVISION` | Third arg or env var                                       | Empty (upstream package version)              |
| `SOURCE_COMMIT`    | Environment only; stable CI resolves the release tag       | Empty (clone by tag/channel)                  |
| Build type         | Selected by release channel                                | Stable: `Release`; nightly: `RelWithDebInfo`  |
| CMake generator    | Upstream Makefile                                          | Auto-detects Ninja                            |
| CPack config       | Upstream `cmake.packaging/CMakeLists.txt`                  | Ships with Neovim                             |

Building inside the container reduces host-specific variation: all build prerequisites come from the selected Ubuntu
image's apt repositories. The digest fixes the base-image identity, but apt package indexes are rolling by default. Set
the optional `UBUNTU_APT_SNAPSHOT=YYYYMMDDTHHMMSSZ` build argument to use a dated Ubuntu snapshot and record that
timestamp when stronger replayability is required. A snapshot removes one rolling input; it does not by itself make the
output byte-for-byte reproducible.

Local builds using `VERSION=latest` query the upstream GitHub API and can set `GH_TOKEN` to avoid unauthenticated rate
limits. CI resolves stable versions and nightly commits in an authenticated orchestration step, then passes only the
resolved version and commit into the token-free build boundary.

Stable CI first resolves the published upstream tag to its final 40-character commit SHA. `build.sh` fetches and
verifies that exact commit through `SOURCE_COMMIT`; tag names are retained as human-facing version identifiers rather
than used as the final source-integrity boundary.

After checkout, `build.sh` exports the exact upstream commit timestamp as `SOURCE_DATE_EPOCH`. Stable packages use
CPack's standard strip option and explicitly strip generated parser-library copies that upstream installs as data.
Package documentation is installed through a CPack install script, so metadata fixes do not require unpacking and
repacking the finished archive.

### 3. Shared Quality Gate

Before any package build, the reusable workflow runs the repository's
[shared quality gate](../.github/actions/quality-gates/action.yml). It covers shell and container linting, Python quality
and tests, workflow syntax and security, dependency consistency, and release-policy regressions. The shared action is
the source of truth for the exact tools and commands, avoiding a duplicated checklist here.

### 4. Verification Checklist (test.sh)

Every stable `.deb` passes the same eight checks before it's considered valid:

1. **Install**: `dpkg -i` succeeds (auto-fixes dependencies if needed)
2. **Package version**: Debian metadata matches the independently resolved package version
3. **Runtime version**: `nvim --version` reports the independently resolved source version
4. **Smoke test**: `nvim --headless +q` starts and exits cleanly
5. **Runtime health**: `nvim --headless +checkhealth +q` runs without crash
6. **Library deps**: `ldd` shows no unresolved shared libraries
7. **Alternatives**: `update-alternatives` registers nvim for `vi`, `vim`, and `view`
8. **Cleanup**: `dpkg -r "$(dpkg-deb -f <deb-file> Package)"` removes the package cleanly

The same test suite runs on every build, regardless of architecture or trigger.

CI passes source and package expectations recorded by `build.sh` before inspecting the generated package. This prevents
a consistently mislabeled artifact from validating itself. For ad-hoc local use, `test.sh` can still infer the expected
version from package metadata when explicit expectations are omitted.

### 5. Explicit Artifact Handling

Package artifacts use explicit paths and identity checks:

- `cpack -B /output` writes the `.deb` to an explicit directory
- CI mounts `/output` from the container to `$PWD/output/` on the host
- CI requires exactly the expected architecture-specific package and verifies its Debian `Architecture` field before
  any downstream step
- Per-architecture artifacts include `SHA256SUMS-<arch>`; publication regenerates one combined `SHA256SUMS`
- `BUILD-METADATA-<arch>.json` binds each package hash to its upstream commit, packaging commit, architecture, package
  version, and Ubuntu image digest
- `SBOM-<arch>.spdx.json` inventories the package in SPDX 2.3 format; publication creates a separate SBOM attestation
  binding each SBOM to its package

## Replayability Guarantees and Limits

### What Is Guaranteed

- **Recorded inputs support functional replay**: Builds using the same exact source, target architecture, base image,
  and equivalent resolved dependencies should pass the same verification checks and behave equivalently at runtime.
- **Automated construction**: Every package follows the same lint → build → verify → inventory → checksum process.
  Feature-release publication still requires the documented environment approval.
- **Cross-architecture consistency**: The same build runs for x86_64 and ARM64. The verification checklist is identical.
  Both must pass their respective checks.

### What Is NOT Guaranteed

| Variation           | Cause                                               | Impact                                           |
| ------------------- | --------------------------------------------------- | ------------------------------------------------ |
| SHA256 hash differs | Unrecorded apt state or other upstream build inputs | Investigate before treating builds as equivalent |
| Binary size differs | Toolchain, dependency, or source variation          | Investigate rather than assuming it is benign    |

### Additional Variation Outside the Container

Building outside the container (running `build.sh` directly on a host system) has additional uncontrolled inputs even
if the host resembles the pinned container. Differences in `gcc`, `cmake`, `ninja`, or system libraries may change
dependency requirements or code generation.

This is why the **containerized build is the canonical build method**. Local builds outside the container are for
development and testing only.

## Replaying the build and verification contract

To replay the recorded source and packaging inputs and run the same functional checks, first use a worktree at the exact
packaging-repository commit in the release metadata. Then take the upstream version, source commit, and optional package
revision from that metadata. Do not use `VERSION=latest`, because it intentionally follows the moving upstream release:

```bash
# Replace these values with those recorded for the release being replayed.
VERSION=X.Y.Z
SOURCE_COMMIT=0123456789abcdef0123456789abcdef01234567
PACKAGE_REVISION=

# 1. Build inside the pinned container.
docker build -t neovim-builder -f Containerfile .
mkdir -p output
docker run --rm \
  -e "VERSION=$VERSION" \
  -e "SOURCE_COMMIT=$SOURCE_COMMIT" \
  -e "PACKAGE_REVISION=$PACKAGE_REVISION" \
  -v "$PWD/output:/output" \
  neovim-builder

# 2. Test inside the disposable target container with independent expectations.
docker run --rm \
  -v "$PWD/test.sh:/tmp/test.sh:ro" \
  -v "$PWD/output:/output:ro" \
  neovim-builder \
  bash /tmp/test.sh /output/nvim-linux-x86_64.deb \
    "$(cat output/EXPECTED_SOURCE_VERSION)" \
    "$(cat output/EXPECTED_PACKAGE_VERSION)"

# 3. Record the resulting checksum for comparison.
sha256sum output/*.deb
```

If `test.sh` passes, the package meets the functional verification contract. That result alone does not prove that two
builds used identical inputs or produced identical bytes. A different checksum can result from rolling apt state,
toolchain changes, or another unresolved build input even though package timestamps use `SOURCE_DATE_EPOCH`.

## Cross-Architecture Considerations

The CI runs on GitHub Actions runners with the build and test executed inside the digest-pinned target-Ubuntu container.
The runner OS does not need to match the target OS. `RUNNER_X86_64` and `RUNNER_AARCH64` select the native hosts; the
reusable package workflow contains the public fallback labels and the container provides the build and test environment.

The CI matrix builds on two architectures:

| Architecture    | Runner variable  | `.deb` filename         |
| --------------- | ---------------- | ----------------------- |
| x86_64          | `RUNNER_X86_64`  | `nvim-linux-x86_64.deb` |
| aarch64 / ARM64 | `RUNNER_AARCH64` | `nvim-linux-arm64.deb`  |

The ARM runner/build matrix uses the `aarch64` architecture label, while the generated CPack `.deb` filename and Debian
package metadata both use the Debian/Ubuntu architecture name `arm64`.

Both architectures use the same `Containerfile` (the multi-arch manifest digest resolves to the correct platform image),
the same `build.sh` parameters, and the same `test.sh` verification. The only difference is the binary itself — compiled
for the target ISA.

### Verification runs inside the build container

Test verification (`test.sh`) runs **inside the same container** that built the `.deb`, not on the host runner. This is
intentional: the container's runtime libraries match the build environment's. The generated `Depends` field is the
authority for the actual glibc and libgcc minima. Runner-side testing could otherwise fail when hosted-runner libraries
differ from the target container.

The test invocation and architecture matrix in
[`.github/workflows/package.yml`](../.github/workflows/package.yml) are authoritative for the current implementation.

Runner upgrades are operational configuration changes: verify the desired labels in
[actions/runner-images](https://github.com/actions/runner-images), update `RUNNER_X86_64` or `RUNNER_AARCH64`, and let
the native matrix validate them. Prose does not track anticipated future labels.

## References

- [`Containerfile`](../Containerfile) — Pinned base image and build environment
- [`build.sh`](../build.sh) — Parameterized build script
- [`test.sh`](../test.sh) — Verification checklist
- [`.github/workflows/build.yml`](../.github/workflows/build.yml) — CI pipeline
- [`docs/architecture.md`](architecture.md) — Architectural invariants and design rationale
- [Reproducible Builds project](https://reproducible-builds.org/) — Industry best practices
