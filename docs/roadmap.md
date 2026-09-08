# Stable Release Automation Roadmap

**Document type:** Roadmap (temporary)

**Status:** Stage 1 implemented; later stages remain planned

## Purpose

Move stable publication from semver-based approval to exception-based approval. A human should decide genuine policy
exceptions, not repeat package checks that CI can enforce deterministically.

This file distinguishes delivered work from intended work. [`RELEASING.md`](../RELEASING.md) remains authoritative for
operator procedures. Update a stage's status only in the same change that delivers its acceptance criteria.

## Current baseline

The implemented pipeline already:

- Polls daily for GitHub's latest published, non-prerelease Neovim release.
- Resolves the upstream tag to an exact commit.
- Builds and tests native x86_64 and ARM64 packages.
- Validates package identity, runtime behavior, dependencies, alternatives registration, removal, and Lintian policy.
- Publishes checksums, build metadata, SPDX SBOMs, and build-provenance and SBOM attestations.
- Automatically publishes maintenance releases (`X.Y.Z` where `Z > 0`).
- Requires environment approval for feature releases (`X.Y.0`).
- Reports release failures through a self-healing issue.

The remaining manual approval is based only on the version shape. It does not distinguish a routine feature release
from an upstream change that materially affects packaging.

## Target state

Automatically publish every upstream stable release after all release gates pass, unless a deterministic risk
classifier identifies a review condition. The workflow must fail closed when it cannot establish the evidence needed to
classify a candidate.

Review remains mandatory for:

- Upstream changes to packaging-, dependency-, or build-critical inputs.
- Ubuntu target, base-image policy, or architecture-policy changes.
- Packaging-only revisions requested by a maintainer.
- Recovery from incomplete evidence or an unexpected release state.

## Delivery safeguards

Apply these rules to every roadmap stage:

1. **Keep stages independently revertible.** Implement and verify one stage before activating the next. Do not combine
   multiple policy transitions in one change.
2. **Preserve current publication behavior until replacement gates pass.** In particular, keep feature-release approval
   enabled until Stages 1 and 2 meet their acceptance criteria.
3. **Test policy before wiring publication.** Add fixtures and unit tests for success, failure, ambiguous state, API
   failure, and retry behavior before a new decision can affect a release.
4. **Do not experiment with production releases.** Use unit fixtures and artifact-only workflow runs for development.
   Never create a disposable tag or published release in this repository.
5. **Fail closed.** Missing metadata, unresolved commits, incomplete comparisons, unknown assets, unsupported versions,
   and exhausted retries must block publication rather than select a permissive default.
6. **Retain least privilege.** Give each job only the GitHub permissions it needs. Candidate construction remains
   read-only; publication, attestation, and issue reporting keep separate explicit permissions.
7. **Treat automated releases as immutable after publication.** A post-publication failure reports an incident and
   blocks workflow success; it never edits, deletes, replaces, or reuses the published release or tag.
8. **Keep sources of truth executable.** Store risk paths, retry bounds, asset contracts, and policy decisions in tested
   code or configuration. Documentation should explain the policy without duplicating change-prone values.
9. **Update documentation atomically.** Inspect every maintained Markdown file in the implementation change and update
   each affected document in that same commit. Do not postpone documentation cleanup to a later stage.
10. **Require complete evidence.** Local policy checks and every applicable GitHub Actions workflow must pass before the
    next stage begins. Record any deliberately skipped live check and its replacement evidence.
11. **Advance status only with delivery.** Change a stage from `Planned` only when its implementation, tests,
    documentation, and CI evidence satisfy all acceptance criteria.

### Documentation synchronization

Before completing a stage, inspect all repository Markdown files and apply this routing:

| Document                  | Update when the stage changes…                                                        |
| ------------------------- | ------------------------------------------------------------------------------------- |
| `README.md`               | User-visible installation, artifacts, verification, support, or release behavior      |
| `RELEASING.md`            | Maintainer operations, approvals, recovery, package revisions, or validation commands |
| `SECURITY.md`             | Permissions, trust boundaries, attestations, immutability, scanners, or guarantees    |
| `docs/architecture.md`    | Durable components, invariants, publication policy, or design rationale               |
| `docs/reproducibility.md` | Recorded inputs, metadata, replay procedure, build boundaries, or guarantees          |
| `docs/resources.md`       | An implemented decision introduces or replaces an authoritative external reference    |
| `docs/roadmap.md`         | Stage status, sequencing, acceptance criteria, or remaining scope                     |

Run Markdown formatting and structure validation plus the relative-link checker after the inspection. Update only
documents affected by real behavior; do not add review dates, copied tool versions, or speculative claims merely to
show that a file was inspected.

## Stage 1 — Verify the published release (implemented)

**Status:** Planned

Add a post-publication job that consumes the release through its public interface rather than trusting only the local
release workspace.

The job should:

1. Download the published assets into a clean directory.
2. Require the exact release asset contract and reject unexpected assets.
3. Verify `SHA256SUMS` against both packages.
4. Verify build-provenance and SPDX SBOM attestations for both packages.
5. Revalidate package and build-metadata bindings.
6. Confirm the release and associated tag are immutable, using the supported GitHub CLI or API.
7. Retry only bounded, documented eventual-consistency failures.
8. Open or update the existing release-failure issue if verification fails; never mutate the published release.

Implemented acceptance criteria:

- Tests cover missing, extra, corrupted, unattested, and mismatched assets.
- A successful publication cannot report success until remote verification passes.
- A verification failure produces one actionable, self-healing maintainer issue.

The verifier uses read-only `contents` and `attestations` permissions; only the separate issue-reporting job has
`issues: write`.

## Stage 2 — Classify upstream packaging risk

**Status:** Planned

Compare the candidate's exact upstream commit with the source commit from the most recent published package. The first
comparison after the legacy `v0.12.5` release may resolve that upstream tag directly because its release lacks build
metadata.

The classifier should route a candidate to review when the comparison includes build-system, CMake/CPack packaging,
bundled-dependency, installation-layout, or release-automation changes. Keep the concrete path policy in tested
executable configuration rather than copying a path list into multiple documents.

The classifier should emit:

- A machine-readable `requires_review` result.
- A short human-readable summary containing the compared commits and risk reasons.
- A fail-closed result when the previous source, comparison, or policy cannot be resolved.

Acceptance criteria:

- Unit tests cover low-risk, high-risk, missing-baseline, API-failure, and annotated-tag cases.
- The workflow summary explains every review decision without requiring log inspection.
- A patch release with packaging-critical changes requires review even though its patch number is nonzero.

## Stage 3 — Enable exception-based publication

**Status:** Planned

Replace the current `patch == 0` approval rule only after Stages 1 and 2 are operational.

- Low-risk stable candidates use `release-auto` after the complete native matrix passes.
- Classified candidates use `release-reviewed` after the same matrix passes.
- Prereleases, drafts, nightlies, and unsupported version formats remain ineligible for stable publication.
- Approval changes only publication policy; it never bypasses build, verification, inventory, or attestation gates.

Acceptance criteria:

- A low-risk `X.Y.0` candidate can publish without human intervention.
- A high-risk `X.Y.Z` candidate waits for review.
- Failure and recovery behavior remains idempotent.
- `RELEASING.md`, `SECURITY.md`, and architecture invariants describe the implemented policy without referring back to
  this roadmap.

## Stage 4 — Simplify packaging-only revisions

**Status:** Planned

Add an explicit manual operation that computes the next unused positive Debian revision for the latest upstream stable
version. The maintainer should provide a reason, not calculate or enter `X.Y.Z-N` manually.

Packaging-only revisions should always require review because they publish repository-owned changes rather than a new
upstream stable release. Candidate construction, exact-source resolution, native verification, immutable publication,
and post-publication verification remain unchanged.

Acceptance criteria:

- Revision selection rejects gaps, reuse, and races with an existing draft or published release.
- The reason is included in the workflow summary and generated release notes.
- No tag or draft release is created before both architecture candidates pass.

## Deliberate non-goals

- Adding external webhook infrastructure solely to replace the daily upstream poll.
- Publishing upstream prereleases or nightlies as stable releases.
- Automatically changing the Ubuntu LTS target or architecture policy.
- Automatically satisfying or bypassing a required environment approval, or mutating an immutable published release.
- Treating generated release notes as a substitute for upstream release notes.

## Completion and removal

This roadmap is complete when all four stages meet their acceptance criteria and the normal stable-release path needs no
human action unless a documented exception is detected. At that point, move durable policy into
[`docs/architecture.md`](architecture.md), operational instructions into [`RELEASING.md`](../RELEASING.md), and security
claims into [`SECURITY.md`](../SECURITY.md), then delete this file rather than retaining a historical checklist.
