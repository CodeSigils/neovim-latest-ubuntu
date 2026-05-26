# Ubuntu Packaging Resources

**Purpose:** Curated, evaluated resources for building Neovim as a `.deb` package on Ubuntu. **Last updated:**
2026-05-26 (added Category 6: CodeQL best practices) (filtered toward official Neovim, Debian, Ubuntu, CMake, and Podman documentation) **Base distribution:**
Ubuntu 26.04 LTS (Resolute Raccoon)

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

| Resource                                                                                                             | Authoritative       | Current                 | Specific       | Reproducible | Complete       |
| -------------------------------------------------------------------------------------------------------------------- | ------------------- | ----------------------- | -------------- | ------------ | -------------- |
| [Neovim Install Docs](https://neovim.io/doc/install/)                                                                | Official            | v0.10+                  | Yes            | Yes          | Summary only   |
| [Neovim BUILD.md](https://github.com/neovim/neovim/blob/master/BUILD.md)                                             | Official            | Latest                  | Yes            | Yes          | Yes            |
| [Neovim v0.12.2 Release](https://github.com/neovim/neovim/releases/tag/v0.12.2/)                                     | Official            | Current project default | Yes            | Yes          | Yes            |
| [Neovim cmake.packaging/CMakeLists.txt](https://github.com/neovim/neovim/blob/master/cmake.packaging/CMakeLists.txt) | Official            | Latest                  | Yes            | Yes          | CPack fragment |
| [Neovim release.yml](https://github.com/neovim/neovim/blob/master/.github/workflows/release.yml)                     | Official            | Latest                  | Full CI config | Yes          | Yes            |
| [PR #22773 — ci!: remove the .deb release](https://github.com/neovim/neovim/pull/22773)                              | Official merged PR  | 2023 / v0.9 context     | Yes            | N/A          | PR context     |
| [neovim/neovim-releases](https://github.com/neovim/neovim-releases)                                                  | Official Neovim org | Latest                  | Yes            | Yes          | Yes            |

### Notes

- Neovim upstream ships its own CPack `.deb` generator config in `cmake.packaging/CMakeLists.txt`.
- Neovim removed `.deb` files from the main official release workflow in PR #22773 (merged Apr 2023, v0.9). The CPack
  DEB config remains in source but is no longer published from the main release workflow.
- `neovim/neovim-releases` is a separate official Neovim-org repository with release automation that can still provide
  useful packaging context.
- No separate `debian/` directory exists in upstream Neovim; this project wraps upstream CPack output rather than
  maintaining Debian archive packaging.
- Upstream maintainer scripts register Neovim via `update-alternatives` in `postinst` and unregister it in `prerm`.
- Build prerequisites for this repository are declared in `deps/ubuntu-build-deps.txt` and enforced by
  `scripts/check-dependencies.py`.
- Bundled dependencies such as libuv, LuaJIT, tree-sitter, and utf8proc compile under `.deps/`, avoiding conflicts with
  system copies.
- Ninja is the recommended CMake generator: upstream CI uses it, Neovim's Makefile auto-detects it, and it gives
  faster/more reliable parallel builds than Unix Makefiles.

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

| Resource                                                                                                                                         | Authoritative            | Current | Specific | Reproducible | Complete                            |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ | ------- | -------- | ------------ | ----------------------------------- |
| [Debian Policy Manual](https://www.debian.org/doc/debian-policy/)                                                                                | Debian official          | Latest  | Yes      | Yes          | Complete policy reference           |
| [Debian Developer's Reference §6 — Best Packaging Practices](https://www.debian.org/doc/manuals/developers-reference/best-pkging-practices.html) | Debian official          | Latest  | Yes      | Yes          | Maintainer best practices           |
| [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/)                                                                 | Debian official          | Current | Yes      | Yes          | Introductory packaging guide        |
| [Debian Packaging Tutorial](https://www.debian.org/doc/manuals/packaging-tutorial/packaging-tutorial)                                            | Debian official          | Current | Yes      | Yes          | Tutorial format                     |
| [Guide for Debian Maintainers / debmake-doc](https://www.debian.org/doc/manuals/debmake-doc/)                                                    | Debian official          | Current | Yes      | Yes          | Modern tooling-focused guide        |
| [Ubuntu Packaging Guide](https://packaging.ubuntu.com/)                                                                                          | Ubuntu official redirect | Latest  | Yes      | Yes          | Ubuntu contributor docs entry point |
| [Install built packages](https://documentation.ubuntu.com/project/contributors/bug-fix/install-built-packages/)                                  | Ubuntu official          | Latest  | Yes      | Yes          | Install/test scope only             |
| [Ubuntu 26.04 LTS Release Notes](https://discourse.ubuntu.com/t/resolute-raccoon-release-notes/)                                                 | Ubuntu official          | 26.04   | Yes      | Yes          | Release notes / changes             |
| [GitHub Actions runner images](https://github.com/actions/runner-images)                                                                         | GitHub official          | 26.04   | Yes      | N/A          | Runner image reference              |

### Useful Debian wiki supplement

| Resource                                                                            | Authoritative       | Current | Specific | Reproducible | Complete        |
| ----------------------------------------------------------------------------------- | ------------------- | ------- | -------- | ------------ | --------------- |
| [Debian Wiki: HowToPackageForDebian](https://wiki.debian.org/HowToPackageForDebian) | Debian project wiki | Latest  | Yes      | Yes          | Wiki supplement |

### Key best practices from Debian/Ubuntu sources

1. **Maintainer scripts must be idempotent** — `postinst`, `prerm`, `postrm`, and `preinst` must tolerate repeated or
   partial runs.
2. **Avoid prompting during install** — package installation should be non-interactive unless debconf/preseeding is
   explicitly designed.
3. **Register alternatives consistently** — `update-alternatives` is appropriate for editor command integration (`vi`,
   `vim`, `view`, `editor`).
4. **Declare all runtime shared-library dependencies** — this project relies on `CPACK_DEBIAN_PACKAGE_SHLIBDEPS` /
   `dpkg-shlibdeps` for auto-detection.
5. **Do not conflict with Ubuntu archive packages accidentally** — this project is a local/distribution convenience
   package, not a Debian archive replacement.
6. **Test install, upgrade-adjacent behavior, and removal** — this repository's `test.sh` covers install, smoke, health,
   dependency, alternatives, and uninstall checks.

### Ubuntu 26.04 (Resolute Raccoon) packaging notes

Target distribution is Ubuntu 26.04 LTS (Resolute Raccoon), with build and test running inside a pinned `ubuntu:26.04`
container. Key characteristics relevant to .deb packaging:

| Component     | Ubuntu 26.04 | Note                                                                  |
| ------------- | ------------ | --------------------------------------------------------------------- |
| glibc (libc6) | 2.43         | Up from 2.39 in 24.04 — packages built on 26.04 require libc6 >= 2.43 |
| GCC           | 15           | libgcc-s1 from GCC 15; C23 language features available                |
| dpkg          | 1.22.x       | usrmerge-aware; improved dpkg-shlibdeps                               |
| apt           | 2.9.x        | UI improvements, performance                                          |
| lintian       | 2.117–2.118  | Updated usrmerge policy checks                                        |
| Python        | 3.13         | Default interpreter; may affect build-time scripts                    |
| OpenSSL       | 3.x          | System TLS library                                                    |

**Packaging toolchain notes:**

- `dpkg-shlibdeps` emits versioned deps like `libc6 (>= 2.43)` — packages built on 26.04 will NOT install on 24.04
  (glibc 2.39) or older. This is expected and correct for a native LTS package.
- usrmerge (merged `/usr`) is complete in 26.04 — `/lib` and `/usr/lib` are the same filesystem. CPack and dpkg handle
  this transparently.
- GCC 15 ABI is backward-compatible; `libgcc-s1 (>= 3.3)` still covers all modern GCC versions.
- Lintian runs on the GitHub Actions runner (currently ubuntu-24.04), not inside the build container. This is acceptable
  for advisory/audit purposes. To get 26.04-accurate lintian results, run lintian inside the container.
- The container digest is pinned via SHA256 for reproducibility; refresh per docs/reproducibility.md.

---

## Category 3: CPack DEB generator

### Official documentation

| Resource                                                                                            | Authoritative    | Current | Specific | Reproducible | Complete                         |
| --------------------------------------------------------------------------------------------------- | ---------------- | ------- | -------- | ------------ | -------------------------------- |
| [CMake CPack Documentation — DEB Generator](https://cmake.org/cmake/help/latest/cpack_gen/deb.html) | Kitware official | Latest  | Yes      | Yes          | Complete DEB generator reference |
| [CPack module documentation](https://cmake.org/cmake/help/latest/module/CPack.html)                 | Kitware official | Latest  | Yes      | Yes          | Core CPack behavior              |
| [CMake install command](https://cmake.org/cmake/help/latest/command/install.html)                   | Kitware official | Latest  | Yes      | Yes          | Install rule reference           |

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

| Resource                                                                             | Authoritative         | Current | Specific | Reproducible | Complete             |
| ------------------------------------------------------------------------------------ | --------------------- | ------- | -------- | ------------ | -------------------- |
| [Podman installation docs](https://podman.io/docs/installation)                      | Podman official       | Latest  | Yes      | Yes          | Yes                  |
| [podman-build manual](https://docs.podman.io/en/latest/markdown/podman-build.1.html) | Podman official       | Latest  | Yes      | Yes          | Yes                  |
| [Ubuntu Docker image tags](https://hub.docker.com/_/ubuntu)                          | Ubuntu image official | Latest  | Yes      | Yes          | Image reference only |

---

## Category 5: GitHub Actions workflow automation

### Official documentation

| Resource                                                                                                                                                                     | Authoritative   | Current | Specific | Reproducible | Complete           |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ------- | -------- | ------------ | ------------------ |
| [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)                                                | GitHub official | Latest  | Yes      | Yes          | Complete reference |
| [Events that trigger workflows](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows)                         | GitHub official | Latest  | Yes      | Yes          | Complete reference |
| [Using conditions to control job execution](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/using-conditions-to-control-job-execution) | GitHub official | Latest  | Yes      | Yes          | How-to guide       |

### Key rules for GitHub Actions YAML parser

1. **Use flat structure under `on.push:`** — The `branches`, `tags`, and `paths-ignore` keywords must be siblings under
   a single `push:` key. The YAML array/list syntax (`- branches:\n  - main`) is not supported under `push` by GitHub's
   YAML parser.
2. **Path filters are NOT evaluated for tag pushes** — Tag pushes always trigger the workflow regardless of
   `paths-ignore`. Only branch pushes evaluate path filters.
3. **`paths` and `paths-ignore` are mutually exclusive** — You cannot use both for the same event in a workflow. Use
   `paths` with `!` prefix for exclusion if you need both include and exclude.
4. **Branch and path filters compound** — If you define both `branches`/`branches-ignore` and `paths`/`paths-ignore`,
   the workflow runs only when BOTH filters are satisfied.

### CI cycle efficiency analysis

**Before paths-ignore**: Every push to `main` triggered full lint + build matrix (x86_64 + aarch64), consuming ~10
minutes of runner time per run.

**After paths-ignore**: Doc-only pushes (`*.md`, `LICENSE`, `docs/**`) skip the build pipeline. In the project's first
~48 hours of active development:

- **13 of 18 main-branch pushes (72%) were doc-only** and would now be skipped
- **~130 minutes of runner time saved** in this window alone
- **All other workflows** (staleness guard, author check, CodeQL) still run on doc-only pushes — they have no
  paths-ignore — to maintain CI integrity
- **Doc-only PRs skip the build workflow** (PR trigger uses the same paths-ignore as branch pushes); code/workflow PRs
  still build
- **Tag pushes always build** (path filters not evaluated for tags) — releases never skip

**Verdict**: paths-ignore is highly effective for this project. The high doc-to-code ratio (~3:1) means ~3 of every 4
main-branch pushes skip the 10-min build. The lightweight validation workflows (staleness, author, CodeQL) still
validate doc-only changes in ~2 minutes total.

---

## Category 6: CodeQL / code scanning

### Official documentation

| Resource                                                                                                                                                           | Authoritative          | Current | Specific             | Reproducible | Complete                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------- | ------- | -------------------- | ------------ | ------------------------- |
| [github/codeql-action](https://github.com/github/codeql-action)                                                                                                    | GitHub official        | Latest  | Yes                  | Yes          | Action reference + README |
| [About code scanning with CodeQL](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/about-code-scanning-with-codeql)                          | GitHub Docs (concept)  | Latest  | Yes                  | Yes          | Conceptual overview       |
| [CodeQL code scanning for compiled languages](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/about-codeql-code-scanning-for-compiled-languages) | GitHub Docs (concept)  | Latest  | Yes (C/C++ specific) | Yes          | Build modes + caching     |
| [CodeQL query suites](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-query-suites)                                                 | GitHub Docs (concept)  | Latest  | Yes                  | Yes          | Default / security-extended / security-and-quality |
| [Configuring advanced setup](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning) | GitHub Docs (how-to)   | Latest  | Yes                  | Yes          | Step-by-step guide        |
| [CodeQL CLI](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/about-the-codeql-cli)                                                          | GitHub Docs (concept)  | Latest  | Yes                  | Yes          | CLI reference             |
| [CodeQL documentation](https://codeql.github.com/docs/)                                                                                                           | CodeQL official        | Latest  | Yes                  | Yes          | Full reference            |
| [CodeQL init action.yml](https://github.com/github/codeql-action/blob/main/init/action.yml)                                                                        | GitHub official (code) | Latest  | All input parameters | Yes          | Action YAML spec          |

### Key best practices for this project

1. **Use `security-extended` over `security-and-quality` for the `actions` language** — The `actions` language (GitHub Actions YAML workflows) is a relatively small analysis surface (~1000 lines across 6 workflow files). `security-and-quality` adds code-quality queries that generate noise on workflow files without meaningful security signal. `security-extended` catches all relevant security vulnerabilities with fewer false positives.

2. **paths-ignore must NOT exclude workflow files** — CodeQL's purpose is to analyze workflow file changes for security issues. Excluding `.github/workflows/*.yml` from CodeQL's paths-ignore defeats its purpose. Build.yml's paths-ignore excludes workflow files to save build minutes; CodeQL's should only exclude doc/metadata files. Independent trigger lists serve different purposes.

3. **Pin to major version, not SHA** — Reference `github/codeql-action/init@v4` and `github/codeql-action/analyze@v4` (not a commit SHA). Dependabot will keep the major-version tag updated. This ensures bug fixes and new query definitions are picked up automatically.

4. **Use `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`** — GitHub Actions is migrating from Node 20 to Node 24. Setting this env var opt-in to the Node 24 runtime now, avoiding breakage when the default switches.

5. **Schedule analysis weekly, not daily** — CodeQL runs on every push to main anyway. The schedule trigger exists to catch dormant code (no push activity). Weekly (Monday 06:45 UTC) is sufficient; daily burns minutes on idle repos.

6. **Use `permissions:` explicitly** — CodeQL needs `security-events: write` to upload results and `contents: read` to checkout code. Setting these explicitly follows least-privilege and avoids issues with GITHUB_TOKEN defaults changing.

7. **Single-language job for `actions`** — The `actions` language is analyzed alone (not in a matrix with C/C++ or other languages). This keeps the job fast (~54s) and avoids unnecessary build steps. The `actions` query pack doesn't require compilation.

8. **No CLI caching for the `actions` language** — For the `actions` language (~1000 lines across 6 YAML files), the CodeQL CLI download is fast enough (a few seconds) that a caching step adds complexity with negligible benefit. The real savings come from paths-ignore skipping doc-only pushes entirely.

9. **Dependency caching is for compiled languages** — CodeQL dependency caching (https://docs.github.com/en/code-security/concepts/code-scanning/codeql/about-codeql-code-scanning-for-compiled-languages#about-dependency-caching-for-codeql) applies to compiled languages like C/C++, Java, Go, Rust, and Swift — not to the `actions` language. If this project adds C/C++ CodeQL analysis in the future, consider caching Go module dependencies or other build artifacts.

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
