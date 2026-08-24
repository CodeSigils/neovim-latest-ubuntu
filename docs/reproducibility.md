# Reproducibility — Neovim Latest deb Package

**Document type:** Explanation (Diataxis) **Status:** Implemented and verified **Last updated:** 2026-08

## What "Reproducible" Means Here

This project produces a `.deb` package from Neovim source code. **Reproducibility** means:

> Given the same exact Neovim source commit, target architecture, pinned base image, and equivalent resolved build
> dependencies, the pipeline produces a functionally equivalent `.deb` that passes the same verification checks.

This is **functional reproducibility** — not byte-for-byte binary reproducibility. Two builds with the same inputs will
not produce identical SHA256 hashes, but they will produce packages that install, run, and behave identically.
(These correspond to the "reproducible behavior" rather than "reproducible build" variants discussed by the
[Reproducible Builds project](https://reproducible-builds.org/).)

**Why not byte-for-byte?** Neovim's upstream CPack configuration embeds build timestamps into the package metadata. The
compiler may also produce slightly different machine code based on host CPU features. These differences are benign —
they don't affect correctness or functionality.

## How the Pipeline Achieves Reproducibility

### 1. Pinned Base Image

The `Containerfile` pins the base image to a specific SHA256 digest of the current Ubuntu LTS, using a repo-level variable so the version and digest can be updated together:

```dockerfile
ARG UBUNTU_VERSION=26.04
ARG UBUNTU_SHA256=f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64
ARG UBUNTU_APT_SNAPSHOT=""
FROM ubuntu:${UBUNTU_VERSION}@sha256:${UBUNTU_SHA256}
```

The `UBUNTU_VERSION`, `UBUNTU_CODENAME`, and `UBUNTU_SHA256` values are sourced from repo-level variables (`vars.UBUNTU_VERSION`, `vars.UBUNTU_SHA256`, etc.) with fallbacks in the Containerfile. `UBUNTU_APT_SNAPSHOT` is an optional local/release-build argument and is intentionally not a repository variable.

### 2. Parameterized Build Script

`build.sh` accepts positional or environment inputs for the package identity and output. CI also supplies an exact
source commit. The default `latest` version and Ubuntu apt indexes intentionally remain rolling:

| Parameter       | Source                                    | Default                             |
| --------------- | ----------------------------------------- | ----------------------------------- |
| `VERSION`       | First arg or env var; `latest` auto-detects current stable | `latest` |
| `OUTPUT_DIR`    | Second arg or env var                     | `.` in `build.sh`; `/output` in the container |
| `PACKAGE_REVISION` | Third arg or env var                   | Empty (upstream package version)    |
| `SOURCE_COMMIT` | Environment only; stable CI resolves the release tag | Empty (clone by tag/channel) |
| Build type      | Selected by release channel               | Stable: `Release`; nightly: `RelWithDebInfo` |
| CMake generator | Upstream Makefile                         | Auto-detects Ninja                  |
| CPack config    | Upstream `cmake.packaging/CMakeLists.txt` | Ships with Neovim                   |

Building inside the container eliminates host-specific variation: all build prerequisites (ninja, cmake, gettext, curl,
gcc) come from the pinned Ubuntu image's apt repositories. The base image is reproducible by digest, but apt package
indexes are rolling by default. Set the optional `UBUNTU_APT_SNAPSHOT=YYYYMMDDTHHMMSSZ` build argument to use a dated
Ubuntu snapshot and record that timestamp when stronger replayability is required. A snapshot removes one rolling
input; it does not by itself make the output byte-for-byte reproducible.

Builds using `VERSION=latest` query the upstream GitHub API. CI supplies `GH_TOKEN` to avoid unauthenticated rate limits;
local builds can set the same variable when repeated API requests or network restrictions make anonymous access unreliable.

Stable CI first resolves the published upstream tag to its final 40-character commit SHA. `build.sh` fetches and
verifies that exact commit through `SOURCE_COMMIT`; tag names are retained as human-facing version identifiers rather
than used as the final source-integrity boundary.

### 3. CI Lint Layer

Before any build runs, the CI workflow validates:

- **shellcheck** on `build.sh`, `test.sh`, and `scripts/*.sh` — catches scripting errors
- **hadolint** on `Containerfile` — catches container anti-patterns

These lints ensure the build scripts are deterministic and well-formed. A ShellCheck-clean script is much less likely to
depend on accidental shell behavior.

### 4. Verification Checklist (test.sh)

Every stable `.deb` passes the same eight checks before it's considered valid:

1. **Install**: `dpkg -i` succeeds (auto-fixes dependencies if needed)
2. **Package version**: Debian metadata matches the independently resolved package version
3. **Runtime version**: `nvim --version` reports the independently resolved source version
4. **Smoke test**: `nvim --headless +q` starts and exits cleanly
5. **Runtime health**: `nvim --headless +checkhealth +q` runs without crash
6. **Library deps**: `ldd` shows no unresolved shared libraries
7. **Alternatives**: `update-alternatives` registers nvim for `vi`
8. **Cleanup**: `dpkg -r "$(dpkg-deb -f <deb-file> Package)"` removes the package cleanly

The same test suite runs on every build, regardless of architecture or trigger.

CI passes source and package expectations recorded by `build.sh` before inspecting the generated package. This prevents
a consistently mislabeled artifact from validating itself. For ad-hoc local use, `test.sh` can still infer the expected
version from package metadata when explicit expectations are omitted.

### 5. Explicit Artifact Handling

The pipeline never relies on implicit paths or auto-detected locations:

- `cpack -B /output` writes the `.deb` to an explicit directory
- CI mounts `/output` from the container to `$PWD/output/` on the host
- CI requires exactly the expected architecture-specific package and verifies its Debian `Architecture` field before
  any downstream step
- Per-architecture artifacts include `SHA256SUMS-<arch>`; publication regenerates one combined `SHA256SUMS`
- `BUILD-METADATA-<arch>.json` binds each package hash to its upstream commit, packaging commit, architecture, package
  version, and Ubuntu image digest

## Reproducibility Guarantees

### What Is Guaranteed

- **Recorded inputs support functional replay**: Two builds using the same exact source, target architecture, base image,
  and equivalent resolved dependencies should pass identical verification checks and behave equivalently at runtime.
- **No manual steps required**: The CI pipeline is fully automated. Every build follows the same process: lint → build →
  verify → checksum → (optionally) release.
- **Cross-architecture consistency**: The same build runs for x86_64 and ARM64. The verification checklist is identical.
  Both must pass their respective checks.

### What Is NOT Guaranteed

| Variation                                 | Cause                                                                          | Impact                                       |
| ----------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------- |
| SHA256 hash differs                       | CPack embedded timestamps, compiler timestamps                                 | None — functional equivalence unaffected     |
| Binary size varies slightly               | Compiler optimisations, linker alignment                                       | None — difference is typically bytes         |
| Bundled dep versions pinned at clone time | Dep version configs (Build*.cmake in `cmake.deps/`) are cloned with the source; actual downloads happen via CMake ExternalProject during build | Low — Neovim pins exact dep revisions        |
| Host CPU instruction set                  | Compiler auto-detects microarchitecture                                        | Low — Neovim targets baseline x86_64/ARM64v8 |

### Degraded Reproducibility Outside the Container

Building outside the container (running `build.sh` directly on a host system) is reproducible only if the host OS and
toolchain versions match the pinned container. Differences in `gcc`, `cmake`, `ninja`, or system library versions may
produce packages with different dependency requirements or slightly different code generation.

This is why the **containerized build is the canonical build method**. Local builds outside the container are for
development and testing only.

## Verifying Reproducibility

To verify that your build matches the canonical output:

```bash
# 1. Build inside the pinned container
docker build -t neovim-builder -f Containerfile .
docker run --rm -e VERSION=latest -v "$PWD/output:/output" neovim-builder

# 2. Run test.sh on the result (auto-detects version from the .deb)
./test.sh output/nvim-linux-x86_64.deb

# 3. Compare checksum style (not exact values — timestamps differ)
sha256sum output/*.deb
```

If `test.sh` passes all checks, the build is functionally reproducible according to the guarantees above.

## Cross-Architecture Considerations

The CI runs on GitHub Actions runners with the build and test executed inside a reproducible `ubuntu:26.04` container.
The runner OS does not need to match the target OS: x86_64 runners are sourced from the repo-level variable
`RUNNER_X86_64` (default: `ubuntu-latest`); ARM64 runners come from `RUNNER_AARCH64` (default:
`ubuntu-24.04-arm`, as no `ubuntu-26.04-arm` runner is available yet). The container provides the actual
build and test environment.

The CI matrix builds on two architectures:

| Architecture    | CI Runner (via repo variable)                          | `.deb` filename         |
| --------------- | ------------------------------------------------------- | ----------------------- |
| x86_64          | `${{ vars.RUNNER_X86_64 }}` (default `ubuntu-latest`)  | `nvim-linux-x86_64.deb` |
| aarch64 / ARM64 | `${{ vars.RUNNER_AARCH64 }}` (default `ubuntu-24.04-arm`) | `nvim-linux-arm64.deb`  |

The ARM runner/build matrix uses the `aarch64` architecture label, while the generated CPack `.deb` filename and Debian
package metadata both use the Debian/Ubuntu architecture name `arm64`.

Both architectures use the same `Containerfile` (the multi-arch manifest digest resolves to the correct platform image),
the same `build.sh` parameters, and the same `test.sh` verification. The only difference is the binary itself — compiled
for the target ISA.

### Verification runs inside the build container

Test verification (`test.sh`) runs **inside the same container** that built the `.deb`, not on the host runner. This is
intentional: the container's runtime libraries match the build environment's. If the `.deb` declares `libc6 >= 2.43`
(from Ubuntu 26.04), the test environment has exactly that version. Without this pattern, runner-side testing would fail
because the x86_64 runner (`vars.RUNNER_X86_64`, default `ubuntu-latest`) and ARM64 runner (`vars.RUNNER_AARCH64`, default `ubuntu-24.04-arm`) may have a different glibc than the container's target (2.43).

The CI workflow achieves this with:

```yaml
- name: Test .deb package
  run: |
    DEB_NAME="${{ matrix.deb_file }}"
    docker run --rm \
      -v "$PWD/test.sh:/tmp/test.sh:ro" \
      -v "$PWD/output:/output:ro" \
      neovim-builder \
      bash /tmp/test.sh "/output/$DEB_NAME" \
        "$(cat output/EXPECTED_SOURCE_VERSION)" \
        "$(cat output/EXPECTED_PACKAGE_VERSION)"
```

### Future: ubuntu-26.04 runner adoption

When GitHub releases `ubuntu-26.04-arm` runner images, update:

1. Set the repo-level variable `RUNNER_AARCH64` to `ubuntu-26.04-arm` (Settings → Secrets and Variables → Actions → Variables).
   All workflows pick it up immediately — no per-file changes needed.
2. `ubuntu-latest` will auto-roll to `ubuntu-26.04` once GitHub updates the alias; no action required unless
   you want to pin explicitly (set `RUNNER_X86_64` to `ubuntu-26.04`).
3. This file: update the runner table to remove the `(no ... runner is available yet)` notation.

Monitor: https://github.com/actions/runner-images

## References

- [`Containerfile`](../Containerfile) — Pinned base image and build environment
- [`build.sh`](../build.sh) — Parameterized build script
- [`test.sh`](../test.sh) — Verification checklist
- [`.github/workflows/build.yml`](../.github/workflows/build.yml) — CI pipeline
- [`docs/architecture.md`](architecture.md) — Architectural invariants and design rationale
- [Reproducible Builds project](https://reproducible-builds.org/) — Industry best practices
