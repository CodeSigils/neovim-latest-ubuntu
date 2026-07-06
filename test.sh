#!/usr/bin/env bash
# test.sh — Verify a built Neovim .deb package
#
# Usage: ./test.sh <deb-file> [EXPECTED_VERSION]
#   deb-file         Path to the .deb package to test
#   EXPECTED_VERSION Neovim version to verify (default: auto-detect from .deb)
#
# Runs all checks and reports results at the end.

set -euo pipefail

DEB="${1:-}"
EXPECTED_VERSION="${2:-}"
FAILED=0

if [[ -z "$DEB" || "$1" == "--help" || "$1" == "-h" ]]; then
  sed -n '/^# test.sh/,/^$/ s/^# //p' "$0"
  exit 1
fi

if [[ ! -f "$DEB" ]]; then
  echo "[FAIL] Package not found: $DEB"
  exit 1
fi

# Auto-detect version from .deb control file if not provided
if [[ -z "$EXPECTED_VERSION" ]]; then
  EXPECTED_VERSION="$(dpkg-deb -f "$DEB" Version 2>/dev/null || true)"
  if [[ -z "$EXPECTED_VERSION" ]]; then
    echo "[FAIL] Could not extract version from .deb and no version argument given"
    exit 1
  fi
  echo "    (version auto-detected from .deb: ${EXPECTED_VERSION})"
fi

check() {
  local label="$1"
  shift
  if "$@"; then
    echo "[PASS] $label"
  else
    echo "[FAIL] $label"
    FAILED=$((FAILED + 1))
  fi
}

echo "==> Testing Neovim .deb package"
echo "    Package: $DEB"
echo "    Expected version: v${EXPECTED_VERSION}"
echo ""

# Step 1: Install
echo "--- Install ---"
DEB_PATH="$(realpath "$DEB")"
if sudo dpkg -i "$DEB_PATH" 2>/dev/null; then
  echo "[PASS] dpkg install succeeded"
else
  echo "      dpkg reported dependency issues — attempting to fix..."
  sudo apt-get install -y -f 2>/dev/null
  check "dpkg install (after dep fix)" dpkg -i "$DEB_PATH" 2>/dev/null
fi

# Step 2: Verify version
echo ""
echo "--- Version Check ---"
check "nvim --version matches v${EXPECTED_VERSION}" \
  bash -c "nvim --version | grep -q 'NVIM v${EXPECTED_VERSION}'"

# Step 3: Runtime smoke test
echo ""
echo "--- Smoke Test ---"
check "nvim --headless starts and exits cleanly" timeout 10 nvim --headless +q
check "nvim --headless +checkhealth runs without crash" timeout 30 nvim --headless +"checkhealth" +q

# Step 4: Check shared library dependencies
echo ""
echo "--- Library Dependencies ---"
check "ldd reports no unresolved dependencies" \
  bash -c "! ldd \"\$(command -v nvim)\" 2>/dev/null | grep -qi 'not found'"

# Step 5: Verify update-alternatives
echo ""
echo "--- update-alternatives ---"
check "update-alternatives registers nvim for vi" \
  bash -c "update-alternatives --display vi 2>/dev/null | grep -q nvim"

# Step 6: Cleanup
echo ""
echo "--- Cleanup ---"
check "dpkg -r Neovim succeeds" sudo dpkg -r Neovim

# Summary
echo ""
echo "--- Summary ---"
if [[ $FAILED -eq 0 ]]; then
  echo "All checks passed."
  exit 0
else
  echo "${FAILED} check(s) failed."
  exit 1
fi
