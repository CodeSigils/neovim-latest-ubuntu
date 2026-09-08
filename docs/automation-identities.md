# Automation identities and permissions

This document records the repository's current automation identities and their security boundaries. Workflow
permissions are the source of truth; this page explains what those permissions mean and what remains manual.

## Identities

| Identity                               | How it is used here                               | Sensitive capability                                                                                          |
| -------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `github-actions[bot]` / `GITHUB_TOKEN` | Runs workflows and authenticates GitHub API calls | Release publication, asset upload, attestations, and failure-issue maintenance only in explicitly scoped jobs |
| `dependabot[bot]`                      | Opens grouped dependency-update pull requests     | Its workflow runs receive read-only repository access by default and do not receive ordinary Actions secrets  |
| Human maintainer                       | Reviews changes and policy exceptions             | Merges pull requests, approves feature releases, resolves incidents, and changes repository settings          |

`GITHUB_TOKEN` is a short-lived GitHub App installation token created for each job. Its effective permissions are set by
the workflow and job-level `permissions` blocks; unspecified permissions are not granted.

## Current workflow boundaries

| Workflow area                                                        | Token permissions                                               | Automation boundary                                                                                    |
| -------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Policy, author, package, Dependabot triage, and stale-branch reports | Primarily `contents: read`; triage also reads PRs/checks        | Validate or report only; no PR or branch mutation                                                      |
| CodeQL                                                               | `contents: read`, `security-events: write`, plus analysis reads | Publishes security-analysis results only                                                               |
| Stable release publication                                           | `contents: write`, `id-token: write`, `attestations: write`     | Creates/uploads and publishes a release after candidate gates; does not approve protected environments |
| Post-publication verification                                        | `contents: read`, `attestations: read`                          | Reads and verifies public release state; cannot mutate it                                              |
| Release/nightly failure reporting                                    | `issues: write`                                                 | Creates or updates the designated self-healing issue only                                              |

## Trigger and recursion rules

- Workflows triggered by Dependabot use read-only tokens and cannot access ordinary repository secrets by default.
- Commits or most events created with `GITHUB_TOKEN` do not start another workflow run. `workflow_dispatch` and
  `repository_dispatch` are exceptions.
- The repository has no workflow that creates, merges, rebases, closes, or deletes pull requests.
- Native Dependabot auto-merge is disabled. A maintainer reviews and merges dependency updates.
- Merged source branches are deleted by GitHub's repository setting, not by a privileged workflow.
- Protected `release-reviewed` approval remains a human decision.

## Security guidance

Use the least-privilege `permissions` block for every workflow and job. Do not introduce `pull_request_target`, a PAT,
or a GitHub App token merely to make automation more convenient. Those mechanisms can grant write access or trigger
additional workflows and require a separate threat-model review.

Official references:

- [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)
- [Workflow syntax and permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Triggering a workflow from a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [Dependabot on GitHub Actions](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-on-actions)
- [Managing GitHub Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
