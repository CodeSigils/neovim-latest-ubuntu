# Ubuntu Packaging Resources

**Purpose:** Curated, evaluated resources for building Neovim as a `.deb` package on Ubuntu.
**Last updated:** 2026-05-25 (filtered toward official Neovim, Debian, Ubuntu, CMake, and Podman documentation)

This file intentionally prefers official documentation. Third-party tutorials are omitted unless they are
project-specific evidence that cannot be replaced by Debian, Ubuntu, upstream Neovim, CMake, or Podman sources.

All resources below have been evaluated against five criteria:

- **Authoritative** — official docs > project-maintained docs > wiki pages > blogs
- **Current** — targets Neovim >= 0.10 / modern Ubuntu
- **Specific** — concrete commands, configs, versions
- **Reproducible** — approach reusable for future versions
- **Complete** — covers the full workflow, not a fragment

---

## Category 1: Neovim build system

### Primary official sources

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Neovim Install Docs](https://neovim.io/doc/install/) | Official | v0.10+ | Yes | Yes | Summary only |
| [Neovim BUILD.md](https://github.com/neovim/neovim/blob/master/BUILD.md) | Official | Latest | Yes | Yes | Yes |
| [Neovim v0.12.2 Release](https://github.com/neovim/neovim/releases/tag/v0.12.2/) | Official | Current project default | Yes | Yes | Yes |
| [Neovim cmake.packaging/CMakeLists.txt](https://github.com/neovim/neovim/blob/master/cmake.packaging/CMakeLists.txt) | Official | Latest | Yes | Yes | CPack fragment |
| [Neovim release.yml](https://github.com/neovim/neovim/blob/master/.github/workflows/release.yml) | Official | Latest | Full CI config | Yes | Yes |
| [PR #22773 — ci!: remove the .deb release](https://github.com/neovim/neovim/pull/22773) | Official merged PR | 2023 / v0.9 context | Yes | N/A | PR context |
| [neovim/neovim-releases](https://github.com/neovim/neovim-releases) | Official Neovim org | Latest | Yes | Yes | Yes |

### Notes

- Neovim upstream ships its own CPack `.deb` generator config in `cmake.packaging/CMakeLists.txt`.
- Neovim removed `.deb` files from the main official release workflow in PR #22773 (merged Apr 2023, v0.9). The CPack DEB config remains in source but is no longer published from the main release workflow.
- `neovim/neovim-releases` is a separate official Neovim-org repository with release automation that can still provide useful packaging context.
- No separate `debian/` directory exists in upstream Neovim; this project wraps upstream CPack output rather than maintaining Debian archive packaging.
- Upstream maintainer scripts register Neovim via `update-alternatives` in `postinst` and unregister it in `prerm`.
- Build prerequisites for this repository are declared in `deps/ubuntu-build-deps.txt` and enforced by `scripts/check-dependencies.py`.
- Bundled dependencies such as libuv, LuaJIT, tree-sitter, and utf8proc compile under `.deps/`, avoiding conflicts with system copies.
- Ninja is the recommended CMake generator: upstream CI uses it, Neovim's Makefile auto-detects it, and it gives faster/more reliable parallel builds than Unix Makefiles.

### Neovim release CI facts

- **Build on:** `ubuntu-22.04` and `ubuntu-22.04-arm` in upstream release automation
- **Build type:** nightly uses `RelWithDebInfo`; stable uses `Release`
- **Build command:** `cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release`, then `cmake --build build --target package`
- **CPack:** `cpack --config build/CPackConfig.cmake`
- **Release trigger:** tag push, scheduled nightly, or manual dispatch in upstream automation
- **History:** `.deb` files were removed from main upstream releases in PR #22773 to reduce maintenance burden

---

## Category 2: Debian and Ubuntu packaging guides

### Official / highly authoritative

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Debian Policy Manual](https://www.debian.org/doc/debian-policy/) | Debian official | Latest | Yes | Yes | Complete policy reference |
| [Debian Developer's Reference §6 — Best Packaging Practices](https://www.debian.org/doc/manuals/developers-reference/best-pkging-practices.html) | Debian official | Latest | Yes | Yes | Maintainer best practices |
| [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/) | Debian official | Current | Yes | Yes | Introductory packaging guide |
| [Debian Packaging Tutorial](https://www.debian.org/doc/manuals/packaging-tutorial/packaging-tutorial) | Debian official | Current | Yes | Yes | Tutorial format |
| [Guide for Debian Maintainers / debmake-doc](https://www.debian.org/doc/manuals/debmake-doc/) | Debian official | Current | Yes | Yes | Modern tooling-focused guide |
| [Ubuntu Packaging Guide](https://packaging.ubuntu.com/) | Ubuntu official redirect | Latest | Yes | Yes | Ubuntu contributor docs entry point |
| [Install built packages](https://documentation.ubuntu.com/project/contributors/bug-fix/install-built-packages/) | Ubuntu official | Latest | Yes | Yes | Install/test scope only |

### Useful Debian wiki supplement

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Debian Wiki: HowToPackageForDebian](https://wiki.debian.org/HowToPackageForDebian) | Debian project wiki | Latest | Yes | Yes | Wiki supplement |

### Key best practices from Debian/Ubuntu sources

1. **Maintainer scripts must be idempotent** — `postinst`, `prerm`, `postrm`, and `preinst` must tolerate repeated or partial runs.
2. **Avoid prompting during install** — package installation should be non-interactive unless debconf/preseeding is explicitly designed.
3. **Register alternatives consistently** — `update-alternatives` is appropriate for editor command integration (`vi`, `vim`, `view`, `editor`).
4. **Declare all runtime shared-library dependencies** — this project relies on `CPACK_DEBIAN_PACKAGE_SHLIBDEPS` / `dpkg-shlibdeps` for auto-detection.
5. **Do not conflict with Ubuntu archive packages accidentally** — this project is a local/distribution convenience package, not a Debian archive replacement.
6. **Test install, upgrade-adjacent behavior, and removal** — this repository's `test.sh` covers install, smoke, health, dependency, alternatives, and uninstall checks.

---

## Category 3: CPack DEB generator

### Official documentation

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [CMake CPack Documentation — DEB Generator](https://cmake.org/cmake/help/latest/cpack_gen/deb.html) | Kitware official | Latest | Yes | Yes | Complete DEB generator reference |
| [CPack module documentation](https://cmake.org/cmake/help/latest/module/CPack.html) | Kitware official | Latest | Yes | Yes | Core CPack behavior |
| [CMake install command](https://cmake.org/cmake/help/latest/command/install.html) | Kitware official | Latest | Yes | Yes | Install rule reference |

### Key CPack variables for DEB

```cmake
# Required
set(CPACK_GENERATOR "DEB")
set(CPACK_DEBIAN_PACKAGE_NAME "mypackage")
set(CPACK_DEBIAN_PACKAGE_MAINTAINER "Name <email>")

# Dependency auto-detection (recommended)
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS TRUE)

# Output naming
set(CPACK_PACKAGE_FILE_NAME "${CPACK_DEBIAN_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION}-${CMAKE_SYSTEM_PROCESSOR}")

# Maintainer scripts (postinst, prerm, etc.)
set(CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA
    "${CMAKE_SOURCE_DIR}/cmake/packaging/postinst"
    "${CMAKE_SOURCE_DIR}/cmake/packaging/prerm"
)

# Optional: triggers, shlibs, conffiles
set(CPACK_DEBIAN_PACKAGE_TRIGGERS "${CMAKE_SOURCE_DIR}/debian/triggers")
set(CPACK_DEBIAN_PACKAGE_SHLIBS "${CMAKE_SOURCE_DIR}/debian/shlibs")
set(CPACK_DEBIAN_PACKAGE_CONFFILES "${CMAKE_SOURCE_DIR}/debian/conffiles")

# Package description (single line summary + longer body)
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Short description")
set(CPACK_PACKAGE_DESCRIPTION "Longer\ndescription\nwith\nnewlines")

# Version
set(CPACK_PACKAGE_VERSION "1.0.0")

# Must be at the end
include(CPack)
```

---

## Category 4: Podman / container testing

### Official documentation

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Podman installation docs](https://podman.io/docs/installation) | Podman official | Latest | Yes | Yes | Yes |
| [podman-build manual](https://docs.podman.io/en/latest/markdown/podman-build.1.html) | Podman official | Latest | Yes | Yes | Yes |
| [Ubuntu Docker image tags](https://hub.docker.com/_/ubuntu) | Ubuntu image official | Latest | Yes | Yes | Image reference only |

---

## Evaluation summary

### Must-read first

1. **Neovim BUILD.md** — primary build workflow reference
2. **Neovim cmake.packaging/CMakeLists.txt** — upstream CPack config this project wraps
3. **Neovim release.yml** — official upstream CI workflow and build command reference
4. **PR #22773** — why `.deb` files were removed from the main Neovim release workflow
5. **CMake CPack DEB Generator documentation** — official reference for DEB generator variables
6. **Debian Policy Manual** — ultimate authority on Debian package structure and behavior
7. **Debian Developer's Reference §6** — best practices for maintainer scripts and package maintenance
8. **Ubuntu Packaging Guide** — target-distribution entry point for Ubuntu packaging conventions

### Reference for specific questions

1. **Guide for Debian Maintainers / debmake-doc** — modern Debian packaging workflow and tooling
2. **Debian New Maintainers' Guide** — beginner-friendly Debian packaging flow
3. **Ubuntu Install Built Packages** — target-side install/testing guidance
4. **Podman build manual** — reproducible container build behavior
