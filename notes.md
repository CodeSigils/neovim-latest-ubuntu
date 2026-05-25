# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight, task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md). Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## 2026-05-25

- Implemented official-resource audit recommendations: added non-blocking `lintian` audit to `build.yml`, updated CodeQL workflow from v3 to v4, documented package replacement/apt hold behavior in README and RELEASING, and rechecked RELEASING for stale build/release details.
- Corrected ARM64 release-asset docs back to the actual CPack/GitHub Release filename, `nvim-linux-arm64.deb`; retained `aarch64` only for matrix/runner architecture labels.
- Investigated lintian's CI `exit code 2`: reproduced in an Ubuntu 24.04 container. It is lintian's normal non-zero findings exit when it reports package-policy errors/warnings (for example empty extended description, malformed maintainer contact, missing copyright/changelog, uncompressed manpage, unstripped binaries, national-encoding, parser shared-library prerequisites). Updated workflow to capture/report the exit code instead of using `continue-on-error`.
- Corrected README release badge to point to `/releases/latest` and fixed the remaining stale ARM filename explanation in docs/reproducibility.md.

## 2026-05-24

- Resources curation: filtered `docs/resources.md` toward official Neovim, Debian, Ubuntu, CMake, and Podman documentation. Removed general third-party packaging tutorials and GitHub example projects from the curated list; retained only the Debian wiki as a clearly marked supplement. Verified all remaining external URLs returned HTTP 200.
- Official-resource audit cleanup: aligned `docs/build-plan.md` with the actual `build.sh` Makefile-wrapper build path and fixed `docs/reproducibility.md` ARM filename/metadata wording.
- Dependency consistency enforcement added: created `deps/ubuntu-build-deps.txt` for manual host prerequisites, `deps/ubuntu-ci-extra-deps.txt` for CI/container-only extras, and `scripts/check-dependencies.py` wired into `build.yml`. README now includes the previously-missing `git` prerequisite and points to the manifest files as source of truth.
- Authorship enforcement tightened: `check-author.yml` now uses strict canonical identity enforcement (`CodeSigils <toolsoftrade.web@gmail.com>`) for both author and committer, while still rejecting known agent trailers/patterns. This intentionally rejects GitHub web-flow/bot committer identities on `main`.
- Release-channel evaluation: keep version-tag Releases as the canonical stable download surface. Scheduled/main/manual builds remain workflow-artifact only. No CI/workflow plan rewrite needed now; revisit only if we intentionally add a moving `latest-stable` release channel later.
- Staleness docs/CI alignment: documented warning-vs-error semantics in AGENTS.md, added `check-author.yml` to the pre-action gate, and clarified freshness checks in `staleness.yml` comments.
- Repo audit cleanup: fixed AGENTS.md workflow tree/link drift, narrowed unchecked-box warning regex, and synced ARM artifact naming in AGENTS.md/RELEASING.md.

## 2026-05-23

- Drafted and withdrew Neovim Discussion post — not ready yet.
- .mailmap added to consolidate contributor attribution.
- SECURITY.md added with vulnerability reporting policy.
- Security audit completed — see strategy below.
- Remaining gaps at the time: ARM64 CI, multi-release track record, provenance attestation. Superseded later by ARM64 CI and provenance attestation work; keep this as historical scratchpad context only.

---

## Security Audit Strategy (Future Work)

### Threat Model

| Vector                                          | Risk              | Impact                      |
| ----------------------------------------------- | ----------------- | --------------------------- |
| Compromised Neovim source (upstream tag hijack) | Low (signed tags) | Malicious binary shipped    |
| Compromised base image (pinned to digest)       | Very Low          | Backdoor in build env       |
| Compromised CI dependency (actions/\*)          | Low-Medium        | RCE in CI runner            |
| Compromised apt packages (ninja, cmake, etc.)   | Very Low          | Backdoor in build deps      |
| Compromised GitHub runner                       | Low (ephemeral)   | Token/artifact theft        |
| Artifact tampering (MITM on download)           | Low (SHA256SUMS)  | User installs modified .deb |

### Already Mitigated

- Base image pinned to SHA256 digest
- Dependabot for CI action updates
- SHA256SUMS for artifact integrity
- Containerized build (host isolation)
- test.sh verifies `ldd` (dependency integrity)

### Planned Improvements

| Priority | Action                           | Effort | Impact                               |
| -------- | -------------------------------- | ------ | ------------------------------------ |
| 1        | `attest-build-provenance` action | Low    | SLSA L1 provenance, no key mgmt      |
| 2        | GPG-sign SHA256SUMS in CI        | Low    | Additional verification layer        |
| 3        | SBOM generation                  | Medium | Transparency, vulnerability scanning |

**Recommendation**: Start with `attest-build-provenance` (Option B — keyless, zero ops burden). Adds SLSA L1 provenance with a single CI step and `gh attestation verify` for users. GPG signing would be nice-to-have on top but requires key management that isn't justified for this project's scale. See discussion in session transcript for full rationale.
