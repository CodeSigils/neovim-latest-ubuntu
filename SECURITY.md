# Security Policy

## Scope

This policy covers the build pipeline scripts in this repository (`build.sh`, `test.sh`, `Containerfile`, CI workflows,
and related automation).

**Neovim itself** is an upstream project with its own security reporting process at
<https://github.com/neovim/neovim/security>.

## Reporting a Vulnerability

If you discover a security issue in the pipeline or generated artifacts, please report it via **GitHub's private
vulnerability reporting**:

1. Go to
   [https://github.com/CodeSigils/neovim-latest-ubuntu/security](https://github.com/CodeSigils/neovim-latest-ubuntu/security/advisories/new)
2. Click **"Report a vulnerability"**
3. Provide a description, steps to reproduce, and impact

Reports are acknowledged within 72 hours. You should receive a timeline for review within 5 business days.

## Supported Versions

The [latest release](https://github.com/CodeSigils/neovim-latest-ubuntu/releases/latest) is the only supported version.
Older releases are not backported — upgrade to the latest to receive fixes.
