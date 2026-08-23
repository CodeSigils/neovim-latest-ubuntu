#!/usr/bin/env bash
# test.sh — Verify a built Neovim .deb package
#
# Usage: ./test.sh <deb-file> [EXPECTED_VERSION] [EXPECTED_PACKAGE_VERSION]
#   deb-file                 Path to the .deb package to test
#   EXPECTED_VERSION         Neovim runtime version to verify
#   EXPECTED_PACKAGE_VERSION Debian package version to verify
#
# Runs all checks and reports results at the end.

set -euo pipefail

DEB="${1:-}"
EXPECTED_VERSION="${2:-}"
EXPECTED_PACKAGE_VERSION="${3:-}"
FAILED=0
PACKAGE_INSTALLED=0
PACKAGE_NAME=""

# Invoked by the EXIT trap below; ShellCheck cannot resolve indirect trap calls.
# shellcheck disable=SC2329
cleanup() {
  # Invoked indirectly by the EXIT trap; ShellCheck cannot see that call site.
  # shellcheck disable=SC2317
  if [[ "$PACKAGE_INSTALLED" -eq 1 && -n "$PACKAGE_NAME" ]]; then
    sudo dpkg -r "$PACKAGE_NAME" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ -z "$DEB" || "$1" == "--help" || "$1" == "-h" ]]; then
  sed -n '/^# test.sh/,/^$/ s/^# //p' "$0"
  exit 1
fi

if [[ ! -f "$DEB" ]]; then
  echo "[FAIL] Package not found: $DEB"
  exit 1
fi

PACKAGE_NAME="$(dpkg-deb -f "$DEB" Package 2>/dev/null || true)"
if [[ -z "$PACKAGE_NAME" ]]; then
  echo "[FAIL] Could not extract package name from .deb"
  exit 1
fi

ACTUAL_PACKAGE_VERSION="$(dpkg-deb -f "$DEB" Version 2>/dev/null || true)"
if [[ -z "$ACTUAL_PACKAGE_VERSION" ]]; then
  echo "[FAIL] Could not extract Debian package version from .deb"
  exit 1
fi

# Auto-detect version from .deb control file if not provided
if [[ -z "$EXPECTED_VERSION" ]]; then
  EXPECTED_VERSION="${ACTUAL_PACKAGE_VERSION%%-*}"
  echo "    (version auto-detected from .deb: ${EXPECTED_VERSION})"
fi
if [[ -z "$EXPECTED_PACKAGE_VERSION" ]]; then
  EXPECTED_PACKAGE_VERSION="$ACTUAL_PACKAGE_VERSION"
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
echo "    Debian package name: ${PACKAGE_NAME}"
echo "    Expected version: v${EXPECTED_VERSION}"
echo "    Expected package version: ${EXPECTED_PACKAGE_VERSION}"
echo ""

# Step 1: Install
echo "--- Install ---"
DEB_PATH="$(realpath "$DEB")"
if sudo dpkg -i "$DEB_PATH" 2>/dev/null; then
  PACKAGE_INSTALLED=1
  echo "[PASS] dpkg install succeeded"
else
  echo "      dpkg reported dependency issues — attempting to fix..."
  sudo apt-get install -y -f 2>/dev/null
  if check "dpkg install (after dep fix)" dpkg -i "$DEB_PATH" 2>/dev/null; then
    PACKAGE_INSTALLED=1
  fi
fi

# Step 2: Verify version
echo ""
echo "--- Version Check ---"
check "Debian package version is ${EXPECTED_PACKAGE_VERSION}" \
  test "$ACTUAL_PACKAGE_VERSION" = "$EXPECTED_PACKAGE_VERSION"
check "nvim --version matches v${EXPECTED_VERSION}" \
  grep -Fq "NVIM v${EXPECTED_VERSION}" < <(nvim --version | head -1)

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
if check "dpkg -r ${PACKAGE_NAME} succeeds" sudo dpkg -r "$PACKAGE_NAME"; then
  PACKAGE_INSTALLED=0
fi

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
