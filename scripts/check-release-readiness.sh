#!/usr/bin/env bash
# check-release-readiness.sh — read-only preflight before publishing a release tag
#
# Usage: scripts/check-release-readiness.sh <version>
# Example: scripts/check-release-readiness.sh 0.13.0
#
# This script does not create commits, tags, releases, or pushes. It only checks
# whether the repository is in a safe state to publish v<version>.

set -euo pipefail

usage() {
  sed -n '/^# check-release-readiness.sh/,/^$/ s/^# //p' "$0"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 1 || -z "${1:-}" ]]; then
  usage >&2
  exit 2
fi

REQUESTED="${1#v}"
TAG="v${REQUESTED}"

# Package revision suffix support: if REQUESTED is "0.12.2-1", extract
# BASE_VERSION="0.12.2" for upstream Neovim comparisons.
if [[ "$REQUESTED" =~ ^([0-9]+\.[0-9]+\.[0-9]+)-([1-9][0-9]*)$ ]]; then
  BASE_VERSION="${BASH_REMATCH[1]}"
else
  BASE_VERSION="$REQUESTED"
fi
BASE_TAG="v${BASE_VERSION}"
CHECK_LOG="$(mktemp)"
trap 'rm -f "$CHECK_LOG"' EXIT

blockers=()

add_blocker() {
  blockers+=("$1")
}

run_check() {
  local label="$1"
  shift
  if "$@" >"$CHECK_LOG" 2>&1; then
    echo "PASS: $label"
  else
    echo "FAIL: $label"
    sed 's/^/  /' "$CHECK_LOG"
    add_blocker "$label failed"
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

echo "== Release readiness: ${TAG} =="

for cmd in git gh curl python3; do
  if ! command_exists "$cmd"; then
    add_blocker "Required command missing: $cmd"
  fi
done

if [[ ! "$REQUESTED" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[1-9][0-9]*)?$ ]]; then
  add_blocker "Unsupported release version format: ${REQUESTED} (expected X.Y.Z or X.Y.Z-N)"
fi

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  add_blocker "Not inside a git repository"
else
  branch="$(git branch --show-current)"
  if [[ "$branch" != "main" ]]; then
    add_blocker "Current branch is '$branch', expected 'main'"
  fi

  if [[ -n "$(git status --porcelain)" ]]; then
    add_blocker "Working tree is not clean"
  fi

  if ! git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    add_blocker "Current branch has no upstream tracking branch"
  else
    local_head="$(git rev-parse HEAD)"
    upstream_head="$(git rev-parse '@{u}')"
    if [[ "$local_head" != "$upstream_head" ]]; then
      add_blocker "Local main does not match upstream tracking branch"
    fi
  fi

  if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
    add_blocker "Local tag already exists: ${TAG}"
  fi

  set +e
  git ls-remote --exit-code --tags origin "${TAG}" >"$CHECK_LOG" 2>&1
  remote_tag_status=$?
  set -e
  case "$remote_tag_status" in
    0) add_blocker "Remote tag already exists: ${TAG}" ;;
    2) : ;; # No matching ref.
    *) add_blocker "Could not determine whether remote tag exists: ${TAG}" ;;
  esac
fi

if command_exists gh; then
  if ! gh auth status >/dev/null 2>&1; then
    add_blocker "GitHub CLI is not authenticated"
  fi

  repository="$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)"
  if [[ -z "$repository" ]]; then
    add_blocker "Could not determine the GitHub repository"
  else
    set +e
    release_error="$(gh api "repos/${repository}/releases/tags/${TAG}" --silent 2>&1)"
    release_status=$?
    set -e
    if [[ "$release_status" -eq 0 ]]; then
      add_blocker "GitHub Release already exists: ${TAG}"
    elif ! grep -q 'HTTP 404' <<<"$release_error"; then
      add_blocker "Could not determine whether GitHub Release exists: ${TAG}"
    fi
  fi

  if vars="$(gh variable list 2>/dev/null)"; then
    if ! grep -q '^UBUNTU_VERSION[[:space:]]' <<<"$vars"; then
      add_blocker "GitHub repo variable missing: UBUNTU_VERSION"
    fi
    if ! grep -q '^UBUNTU_CODENAME[[:space:]]' <<<"$vars"; then
      add_blocker "GitHub repo variable missing: UBUNTU_CODENAME"
    fi
    if ! grep -q '^UBUNTU_SHA256[[:space:]]' <<<"$vars"; then
      add_blocker "GitHub repo variable missing: UBUNTU_SHA256"
    fi
  else
    add_blocker "Could not list GitHub repository variables"
  fi
fi

if command_exists curl && command_exists python3; then
  upstream_tag=""
  # Prefer the authenticated GitHub CLI to avoid the low unauthenticated API
  # rate limit. Keep curl as a portable fallback for local fixtures and forks.
  if command_exists gh && gh auth status >/dev/null 2>&1; then
    upstream_tag="$(gh api repos/neovim/neovim/releases/latest --jq '.tag_name' 2>/dev/null || true)"
  fi
  if [[ -z "$upstream_tag" ]]; then
    curl_args=(-fsSL -H 'Accept: application/vnd.github+json')
    if [[ -n "${GH_TOKEN:-}" ]]; then
      curl_args+=(-H "Authorization: Bearer ${GH_TOKEN}")
    fi
    upstream_tag="$(curl "${curl_args[@]}" https://api.github.com/repos/neovim/neovim/releases/latest \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tag_name", ""))' 2>/dev/null || true)"
  fi
  if [[ -z "$upstream_tag" ]]; then
    add_blocker "Could not determine latest upstream Neovim release"
  elif [[ "$upstream_tag" != "$BASE_TAG" ]]; then
    add_blocker "Requested tag ${TAG} (base Neovim ${BASE_TAG}) does not match latest upstream Neovim release ${upstream_tag}"
  fi
fi

if [[ ! -f build.sh ]]; then
  add_blocker "build.sh missing"
fi

if [[ -f scripts/check-dependencies.py ]]; then
  run_check "dependency consistency" python3 scripts/check-dependencies.py
else
  add_blocker "scripts/check-dependencies.py missing"
fi

if [[ -f scripts/check-yaml-syntax.py ]]; then
  run_check "workflow YAML syntax" python3 scripts/check-yaml-syntax.py
else
  add_blocker "scripts/check-yaml-syntax.py missing"
fi

if [[ -f build.sh && -f test.sh ]]; then
  run_check "shell syntax" bash -n build.sh test.sh
else
  add_blocker "build.sh or test.sh missing"
fi

run_check "git diff whitespace" git diff --check

echo ""
if ((${#blockers[@]} > 0)); then
  echo "NOT READY"
  for blocker in "${blockers[@]}"; do
    echo "- $blocker"
  done
  exit 1
fi

echo "READY: safe to publish ${TAG}"
echo "git tag ${TAG}"
echo "git push origin ${TAG}"
