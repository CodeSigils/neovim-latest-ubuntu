# notes.md — Agent Scratchpad / Task-Level Record

**Purpose:** Internal agent scratchpad — lightweight, task-level change log. Not user-facing.
User-facing release history lives in [`CHANGELOG.md`](./CHANGELOG.md). Full agent instructions in [`AGENTS.md`](./AGENTS.md).

## 2026-05-24

- Repo audit cleanup: fixed AGENTS.md workflow tree/link drift, narrowed unchecked-box warning regex, and synced ARM artifact naming to `aarch64` in AGENTS.md/RELEASING.md.

## 2026-05-23

- Drafted and withdrew Neovim Discussion post — not ready yet.
- .mailmap added to consolidate contributor attribution.
- SECURITY.md added with vulnerability reporting policy.
- Security audit completed — see strategy below.
- Remaining gaps: ARM64 CI, multi-release track record, provenance attestation.

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

---

## Discussion Draft — "Community-maintained .deb packages for latest stable Neovim"

```
**Title:** Community-maintained Ubuntu .deb packaging for latest stable Neovim

**Category:** Ideas

---

Hi all — I've been packaging the latest stable Neovim as a proper .deb for Ubuntu,
and wanted to share in case it's useful to others here.

**The repo:** [CodeSigils/neovim-latest-ubuntu](https://github.com/CodeSigils/neovim-latest-ubuntu)

### What it does

Takes the latest stable Neovim source, builds it in a reproducible
container (pinned `ubuntu:24.04`), and produces a system `.deb` package
with full `update-alternatives` registration — so `vi`, `vim`, `editor`
point to Neovim after install.

### Why this exists

Neovim upstream stopped shipping `.deb` packages in v0.9 (PR #22773).
The alternatives all have trade-offs:

- **`apt install neovim`** — often lags months behind latest release
- **Official AppImage** — no system-wide `vi`/`editor` symlink integration
- **Snap** — sandboxing breaks file access, slow startup
- **Manual `make install`** — no package manager tracking, no clean uninstall

This fills the gap: latest Neovim, native `.deb`, zero config.

### What's in the pipeline

- **Reproducible container build** — Podman/Docker, pinned base image digest
- **GitHub Actions CI** — builds on tag push, main push, and weekly schedule
- **Automated verification** — install, version match, ldd, alternatives, uninstall
- **SHA256 checksums** on every release
- **Dependabot** — automatic CI dependency updates

### Non-goals

- This is not a replacement for official Neovim release assets.
- This is not a distro-quality Debian package (no `debian/` directory, no lintian
  override, no system library linking — it uses upstream's CPack with bundled deps).
- ARM64 builds are planned but not yet in CI.
- Nightly builds are provided (workflow artifacts only — no Release page).

### Why I'm posting

Mostly to see if this is useful to others, and to get feedback on the approach.
If maintainers are open to it, I'd be happy to have this listed as a
community-maintained option somewhere in the docs — but no expectation there.

The repo is Apache 2.0 (Neovim's license).

Thoughts? Feedback? Contributions welcome.
```

### Where to post

1. **Neovim GitHub Discussions** (Ideas category) — this draft
2. Possibly r/neovim afterward if the discussion goes well
3. Only open a docs issue if a maintainer explicitly suggests it

### Key positioning

- Additive, not political
- Not asking Neovim to own or support it
- Just "here's a thing I built, maybe useful"
- Non-goals section upfront to set expectations

## Latest issues

How to prevent agent identities to appear as Contributors in my repo?

I’ll separate what GitHub can actually hide from what Git history will still expose. The clean answer depends on whether the agent already committed, or you’re preventing future commits.

To prevent agent identities showing as repo Contributors, control commit authorship.

### Best practice

```bash
git config user.name "your-actual-user-name"
git config user.email "your-github-noreply-or-public-email"
```

Then ensure agent tools do not add trailers like:

```text
Co-authored-by: Claude <...>
Co-authored-by: ChatGPT <...>
Co-authored-by: GitHub Copilot <...>
```

GitHub’s contributor graph is based on commit attribution;
.mailmap helps Git display names locally, but it generally won’t reliably remove identities from GitHub contributor views. GitHub docs also note contributor graphs are based on repository contributions, and commit emails must be associated with accounts to count on profile contribution graphs.

For existing commits:

```bash
git log --format='%h %an <%ae>%n%B' --all
```

If you see agent authors or Co-authored-by trailers, fix with interactive rebase:

```bash
git rebase -i --root
```

For each affected commit:

```bash
git commit --amend --author="user-name <your-email>" --no-edit
```

Remove agent Co-authored-by lines from the commit message too.

Then force-push:

```bash
git push --force-with-lease
```

Sharp recommendation: for your repos, agents should be treated as tools, not contributors.
You and the agents must guard against this.
Authorship should stay with the human maintainer unless you intentionally want public attribution.
