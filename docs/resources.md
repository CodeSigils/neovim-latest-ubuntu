# Ubuntu Packaging Resources

**Purpose:** Curated, evaluated resources for building Neovim as a `.deb` package on Ubuntu.
**Last updated:** 2026-05-22

All resources below have been evaluated against five criteria:
- **Authoritative** — official docs > blog posts > forum answers
- **Current** — targets Neovim >= 0.10 / modern Ubuntu
- **Specific** — concrete commands, configs, versions
- **Reproducible** — approach reusable for future versions
- **Complete** — covers the full workflow, not a fragment

---

## Category 1: Neovim Build System

### Primary

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Neovim Install Docs](https://neovim.io/doc/install/) | ✅ Official | ✅ v0.10+ | ✅ | ✅ | ⚠️ Summary only |
| [Neovim BUILD.md](https://github.com/neovim/neovim/blob/master/BUILD.md) | ✅ Official | ✅ Latest | ✅ | ✅ | ✅ |
| [Neovim v0.12.2 Release](https://github.com/neovim/neovim/releases/tag/v0.12.2/) | ✅ Official | ✅ Current | ✅ | ✅ | ✅ |
| [Neovim cmake.packaging/CMakeLists.txt](https://github.com/neovim/neovim/blob/master/cmake.packaging/CMakeLists.txt) | ✅ Official | ✅ Latest | ✅ | ✅ | ⚠️ Fragment (CPack only) |
| [Neovim release.yml (release workflow)](https://github.com/neovim/neovim/blob/master/.github/workflows/release.yml) | ✅ Official | ✅ Latest | ✅✅ Full CI config | ✅ | ✅ |
| [PR #22773 — ci!: remove the .deb release](https://github.com/neovim/neovim/pull/22773) | ✅ Official (merged) | ✅ 2023 (v0.9) | ✅ | N/A | ⚠️ PR context |
| [neovim/neovim-releases](https://github.com/neovim/neovim-releases) | ✅ Official | ✅ Latest | ✅ | ✅ | ✅ |
| [code-of-hephaestus/neovim-builds](https://github.com/reaper8055/neovim-builds) | ⚠️ Third-party (transferred to @reaper8055) | ✅ 2026 | ✅✅ | ✅ | ✅ |

### Notes

- Neovim upstream ships its own CPack `.deb` generator config in `cmake.packaging/CMakeLists.txt`.
- **Neovim removed .deb from official releases** (PR #22773, merged Apr 2023, v0.9). Rationale: maintenance burden; users directed to AppImage or manual builds. The CPack DEB config remains in source but is no longer invoked by CI.
- **neovim/neovim-releases** is a separate repo with its own release.yml that still produces .deb artifacts.
- **code-of-hephaestus/neovim-builds** (now at @reaper8055) is a third-party GA workflow that builds Neovim .deb: clones stable branch, `make CMAKE_BUILD_TYPE=Release`, `cpack -G DEB`, tests install, names versioned files. Latest release: nvim-v0.12.0-stable-linux-amd64 (2026-03-30). Good reference for our pipeline.
- No separate `debian/` directory exists — Neovim generates DEB directly via `cpack -G DEB`.
- The upstream `postinst` registers Neovim via `update-alternatives` and `prerm` unregisters.
- Build prerequisites (Ubuntu 24.04): `ninja-build gettext cmake curl build-essential`.
- Bundled deps (libuv, LuaJIT, tree-sitter, etc.) compile to `.deps/` — no system conflicts.
- **Ninja** is the recommended CMake generator (used in CI, auto-detected by Neovim's Makefile, faster than Unix Makefiles).

### Neovim Release CI (from release.yml)

- **Build on**: `ubuntu-22.04` (oldest supported for broader glibc compatibility) and `ubuntu-22.04-arm`
- **Build type**: Nightly → `RelWithDebInfo` (retains asserts), Stable → `Release` (disables asserts)
- **Build command**: `cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release` then `cmake --build build --target package`
- **CPack**: `cpack --config build/CPackConfig.cmake` (produces both .tar.gz and .deb)
- **Release trigger**: push tag `v*`, scheduled nightly, or manual dispatch
- **Artifacts** (current): `.tar.gz`, AppImage (Linux); `.zip`, `.msi`, `.exe` (Windows); `.tar.gz` (macOS)
- **History**: `.deb` was part of releases until PR #22773 (v0.9, Apr 2023). Removed to reduce maintenance burden.

---

## Category 2: Debian/Ubuntu Packaging Guides

### Official / Highly Authoritative

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Debian Policy Manual](https://www.debian.org/doc/debian-policy/) | ✅✅ Debian official | ✅ Latest | ✅ | ✅ | ✅✅ |
| [Debian Developer's Reference §6 — Best Practices](https://www.debian.org/doc/manuals/developers-reference/best-pkging-practices.html) | ✅✅ Debian official | ✅ Latest | ✅ | ✅ | ✅ |
| [Debian New Maintainers' Guide (maint-guide)](https://www.debian.org/doc/manuals/maint-guide/) | ✅✅ Debian official | ✅ 2025 | ✅ | ✅ | ✅ |
| [Debian Packaging Tutorial](https://www.debian.org/doc/manuals/packaging-tutorial/packaging-tutorial) | ✅✅ Debian official | ✅ Current | ✅ | ✅ | ✅ |
| [Guide for Debian Maintainers (debmake-doc)](https://www.debian.org/doc/manuals/debmake-doc/) | ✅✅ Debian official | ✅ Current | ✅ | ✅ | ✅ |
| [Ubuntu Packaging Guide](https://packaging.ubuntu.com/) | ✅✅ Ubuntu official | ✅ Latest | ✅ | ✅ | ✅ |

### High-Quality Tutorials

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Creating Debian packages from upstream Git (2025)](https://www.debian.org/doc/manuals/packaging-tutorial/packaging-tutorial) | ✅ Debian | ✅ 2025 | ✅ | ✅ | ✅ |
| [Making a .deb package for CMake C/C++ project (2025)](https://www.baeldung.com/linux/package-deb-change-repack) | ⚠️ Tutorial | ✅ 2025 | ✅ | ✅ | ✅ |
| [Creating and Hosting Your Own Deb Packages (Earthly)](https://earthly.dev/blog/creating-and-hosting-your-own-deb-packages-and-apt-repo/) | ⚠️ Blog | ✅ 2024 | ✅ | ✅ | ✅ |
| [Ultimate Guide to Debian Packaging](https://dario.griffo.io/posts/ultimate-guide-debian-packaging/) | ⚠️ Blog | ✅ 2024 | ✅ | ✅ | ✅ |

### Supplementary

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [How to Create a Debian Package (UbuntuMint)](https://www.ubuntumint.com/create-debian-package/) | ⚠️ Blog | ✅ 2024 | ✅ | ⚠️ Partial | ⚠️ |
| [How to Install .deb in Ubuntu (LinuxVox)](https://linuxvox.com/blog/how-to-install-deb-in-ubuntu/) | ⚠️ Blog | ⚠️ 2023 | ✅ | ✅ | ⚠️ Install only |
| [Add Debian Repositories to Sources List](https://computingforgeeks.com/add-debian-official-repositories-to-sources-list/) | ⚠️ Blog | ✅ 2024 | ✅ | ✅ | ❌ Narrow scope |

### Key Best Practices (from Debian Developer's Reference §6)

1. **Maintainer scripts must be idempotent** — `postinst`, `prerm`, `postrm`, `preinst` should handle repeated runs gracefully.
2. **Avoid prompting during install** — use `debconf` preseed or accept defaults. Neovim's upstream scripts already follow this.
3. **Register alternatives with `update-alternatives`** — Neovim's `postinst` already does this for `vi`, `vim`, `view`, `editor`.
4. **Declare all dependencies** — `CPACK_DEBIAN_PACKAGE_SHLIBDEPS` handles shared libs automatically.
5. **Package naming** — use `neovim-{version}-{arch}.deb` for local builds; don't conflict with `neovim` in Ubuntu repos.

---

## Category 3: CPack DEB Generator

### Official Documentation

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [CMake CPack Documentation — DEB Generator](https://cmake.org/cmake/help/latest/module/CPackDeb.html) | ✅✅ Kitware | ✅ Latest | ✅✅ | ✅ | ✅✅ |
| [CMake CPack Component Install Guide](https://cmake.org/cmake/help/latest/guide/importing-exporting/index.html) | ✅✅ Kitware | ✅ Latest | ✅ | ✅ | ⚠️ Component focus |

### Real-World CPack DEB Examples (from GitHub)

| Project | Stars | CPack Config Highlights |
|---|---|---|
| [Kitware/CMake — CPackDeb.cmake](https://github.com/Kitware/CMake) | Core CMake module | Reference implementation for all CPack DEB variables |
| [Xilinx/XRT](https://github.com/Xilinx/XRT) | Xilinx Runtime | Uses `CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA` for postinst/prerm |
| [PX4/PX4-Autopilot](https://github.com/PX4/PX4-Autopilot) | 8k+ | Complex CPack with postinst/postrm for system services |
| [apache/singa](https://github.com/apache/singa) | 3k+ | Python-specific CPack setup for .deb generation |
| [LizardByte/Sunshine](https://github.com/LizardByte/Sunshine) | 20k+ | Cross-platform CPack with DEB/TGZ/NSIS generators |
| [roboception/cvkit](https://github.com/roboception/cvkit) | 500+ | Advanced: shlibs, triggers, conffiles, control extra |
| [mozilla-services/heka](https://github.com/mozilla-services/heka) | Archived | Uses `CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA` for postinst |
| [ttroy50/cmake-examples](https://github.com/ttroy50/cmake-examples) | 14k+ | Simple CPack DEB example in `03-package-deb` |

### Key CPack Variables for DEB

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

# Package description (single line section, longer description)
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Short description")
set(CPACK_PACKAGE_DESCRIPTION "Longer\ndescription\nwith\nnewlines")

# Version
set(CPACK_PACKAGE_VERSION "1.0.0")

# Must be at the end
include(CPack)
```

---

## Category 4: Podman / Container Testing

| Resource | Authoritative | Current | Specific | Reproducible | Complete |
|---|---|---|---|---|---|
| [Podman Getting Started](https://podman.io/docs/installation) | ✅✅ Official | ✅ Latest | ✅ | ✅ | ✅ |
| [Podman Build (Containerfile)](https://docs.podman.io/en/latest/markdown/podman-build.1.html) | ✅✅ Official | ✅ Latest | ✅ | ✅ | ✅ |
| [Ubuntu Docker Image Tags (for Podman)](https://hub.docker.com/_/ubuntu) | ✅✅ Official | ✅ Latest | ✅ | ✅ | ⚠️ Image only |

---

## Evaluation Summary

### Must-Read First

1. **Neovim BUILD.md** — Primary build workflow reference
2. **Neovim cmake.packaging/CMakeLists.txt** — The CPack config we're wrapping
3. **Neovim release.yml** — Official CI workflow (exact build commands, runner setup)
4. **PR #22773** — Context on why .deb was dropped from official releases
5. **CPack DEB Documentation** — Official reference for DEB generator variables
6. **Debian New Maintainers' Guide** — Best overall tutorial for Debian packaging
7. **Debian Developer's Reference §6** — Best practices for maintainer scripts
8. **Ubuntu Packaging Guide** — Target-distribution specific guidance

### Reference (Bookmark for Specific Questions)

7. **Debian Policy Manual** — Ultimate authority on package structure
8. **debmake-doc** — Modern tooling-focused guide
9. **ttroy50/cmake-examples** — Minimal CPack DEB example to learn the pattern
10. **PX4/PX4-Autopilot CPack config** — Complex real-world CPack pattern
