# Reproducibility — Neovim Latest deb Package

**Document type:** Explanation (Diataxis) **Status:** Implemented and verified **Last updated:** 2026-05-25

## What "Reproducible" Means Here

This project produces a `.deb` package from Neovim source code. **Reproducibility** means:

> Given the same Neovim version and the same base container image, the build pipeline produces a functionally equivalent
> `.deb` that passes the same verification checks.

This is **functional reproducibility** — not byte-for-byte binary reproducibility. Two builds with the same inputs will
not produce identical SHA256 hashes, but they will produce packages that install, run, and behave identically.

**Why not byte-for-byte?** Neovim's upstream CPack configuration embeds build timestamps into the package metadata. The
compiler may also produce slightly different machine code based on host CPU features. These differences are benign —
they don't affect correctness or functionality.

## How the Pipeline Achieves Reproducibility

### 1. Pinned Base Image

The `Containerfile` pins the base image to a specific SHA256 digest of the current Ubuntu LTS:

```dockerfile
FROM ubuntu:${UBUNTU_VERSION}@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64
```

This means every build — whether on a developer's workstation, a CI runner, or a different day — starts from the exact
same operating system image with the exact same toolchain versions. The pinning digest is the multi-arch manifest list,
so the same `Containerfile` selects the correct platform-specific image on both x86_64 and ARM64.

**How to update**: When the base image needs a security refresh, run:

```bash
docker pull ubuntu:26.04
docker inspect --format='{{index .RepoDigests 0}}' ubuntu:26.04
```

Then update the `FROM` line and verify the build still passes.

### 2. Parameterized Build Script

`build.sh` accepts two variables: the Neovim version and output directory. Everything else is deterministic:

| Parameter       | Source                                        | Default            |
| --------------- | --------------------------------------------- | ------------------ |
| `VERSION`       | First arg, env var, or `latest` (auto-detect) | `0.12.2`           |
| `OUTPUT_DIR`    | Second arg or env var                         | `.` (current dir)  |
| Build type      | Hardcoded                                     | `RelWithDebInfo`   |
| CMake generator | Upstream Makefile                             | Auto-detects Ninja |
| CPack config    | Upstream `cmake.packaging/CMakeLists.txt`     | Ships with Neovim  |

Building inside the container eliminates host-specific variation: all build prerequisites (ninja, cmake, gettext, curl,
gcc) are the versions that ship with the pinned Ubuntu image.

### 3. CI Lint Layer

Before any build runs, the CI workflow validates:

- **shellcheck** on `build.sh` and `test.sh` — catches scripting errors
- **hadolint** on `Containerfile` — catches container anti-patterns

These lints ensure the build scripts are deterministic and well-formed. A ShellCheck-clean script is much less likely
to depend on accidental shell behavior.

### 4. Verification Checklist (test.sh)

Every built `.deb` passes the same seven checks before it's considered valid:

1. **Install**: `dpkg -i` succeeds (auto-fixes dependencies if needed)
2. **Version match**: `nvim --version` reports the expected Neovim version
3. **Smoke test**: `nvim --headless +q` starts and exits cleanly
4. **Runtime health**: `nvim --headless +checkhealth +q` runs without crash
5. **Library deps**: `ldd` shows no unresolved shared libraries
6. **Alternatives**: `update-alternatives` registers nvim for `vi`
7. **Cleanup**: `dpkg -r Neovim` removes the package cleanly

The same test suite runs on every build, regardless of architecture or trigger.

### 5. Explicit Artifact Handling

The pipeline never relies on implicit paths or auto-detected locations:

- `cpack -B /output` writes the `.deb` to an explicit directory
- CI mounts `/output` from the container to `$PWD/output/` on the host
- `ls output/*.deb` verifies the artifact exists before any downstream step
- `sha256sum *.deb > SHA256SUMS` generates checksums at two points: per-arch during build, and combined during release

## Reproducibility Guarantees

### What Is Guaranteed

- **Same version + same base image = same behavior**: Two builds of Neovim v0.12.2 inside the pinned base image
  image will produce packages that pass identical verification checks and behave identically at runtime.
- **No manual steps required**: The CI pipeline is fully automated. Every build follows the same process: lint → build →
  verify → checksum → (optionally) release.
- **Cross-architecture consistency**: The same build runs for x86_64 and ARM64. The verification checklist is identical.
  Both must pass their respective checks.

### What Is NOT Guaranteed

| Variation                                 | Cause                                                                          | Impact                                       |
| ----------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------- |
| SHA256 hash differs                       | CPack embedded timestamps, compiler timestamps                                 | None — functional equivalence unaffected     |
| Binary size varies slightly               | Compiler optimisations, linker alignment                                       | None — difference is typically bytes         |
| Bundled dep versions pinned at clone time | `git clone --depth 1` fetches current dep tree from Neovim's pinned submodules | Low — Neovim pins exact dep revisions        |
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
docker run --rm -e VERSION=0.12.2 -v "$PWD/output:/output" neovim-builder

# 2. Run test.sh on the result
./test.sh output/nvim-linux-x86_64.deb 0.12.2

# 3. Compare checksum style (not exact values — timestamps differ)
sha256sum output/*.deb
```

If `test.sh` passes all checks, the build is reproducible.

## Cross-Architecture Considerations

The CI runs on GitHub Actions runners with the build and test executed inside a
reproducible `ubuntu:26.04` container. The runner OS does not need to match the target OS:
x86_64 builds use `ubuntu-latest` runners; ARM64 uses `ubuntu-24.04-arm` (no `ubuntu-26.04-arm`
runner is available yet). The container provides the actual build and test environment.

The CI matrix builds on two architectures:

| Architecture    | CI Runner          | `.deb` filename         |
| --------------- | ------------------ | ----------------------- |
| x86_64          | `ubuntu-latest`     | `nvim-linux-x86_64.deb`  |
| aarch64 / ARM64 | `ubuntu-24.04-arm` (target OS: Ubuntu 26.04 via container) | `nvim-linux-arm64.deb`  |

The ARM runner/build matrix uses the `aarch64` architecture label, while the generated CPack `.deb` filename and Debian
package metadata both use the Debian/Ubuntu architecture name `arm64`.

Both architectures use the same `Containerfile` (the multi-arch manifest digest resolves to the correct platform image),
the same `build.sh` parameters, and the same `test.sh` verification. The only difference is the binary itself — compiled
for the target ISA.

### Verification runs inside the build container

Test verification (`test.sh`) runs **inside the same container** that built the `.deb`, not on the host runner. This
is intentional: the container's runtime libraries match the build environment's. If the `.deb` declares `libc6 >= 2.43`
(from Ubuntu 26.04), the test environment has exactly that version. Without this pattern, runner-side testing would
fail because the runner (ubuntu-24.04) has an older glibc (2.39) that can't satisfy the package's dependencies.

The CI workflow achieves this with:

```yaml
- name: Test .deb package
  run: |
    DEB_NAME=$(basename "$(ls output/*.deb | head -1)")
    docker run --rm \
      -v "$PWD/test.sh:/tmp/test.sh:ro" \
      -v "$PWD/output:/output:ro" \
      neovim-builder \
      bash /tmp/test.sh "/output/$DEB_NAME"
```

### Future: ubuntu-26.04 runner adoption

When GitHub releases `ubuntu-26.04` and `ubuntu-26.04-arm` runner images, update:

- `build.yml` / `nightly.yml`: change ARM64 runner from `ubuntu-24.04-arm` to `ubuntu-26.04-arm`
- `build.yml`: `ubuntu-latest` will auto-roll to `ubuntu-26.04` once GitHub updates the alias
- This file: update the runner table to remove the `(no ... runner is available yet)` notation

Monitor: https://github.com/actions/runner-images

## References

- [`Containerfile`](../Containerfile) — Pinned base image and build environment
- [`build.sh`](../build.sh) — Parameterized build script
- [`test.sh`](../test.sh) — Verification checklist
- [`.github/workflows/build.yml`](../.github/workflows/build.yml) — CI pipeline
- [`docs/build-plan.md`](build-plan.md) — Build pipeline architecture and design decisions
- [Reproducible Builds project](https://reproducible-builds.org/) — Industry best practices
