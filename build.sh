#!/usr/bin/env bash
# build.sh — Build Neovim from source and package as .deb
#
# Usage: ./build.sh [VERSION] [OUTPUT_DIR] [PACKAGE_REVISION]
#   VERSION          Neovim release tag, or latest/nightly (default: latest)
#   OUTPUT_DIR       Where to place the built .deb (default: .)
#   PACKAGE_REVISION Optional positive Debian package revision (for example: 1)
#
# Examples:
#   ./build.sh                          # Build default version into current dir
#   ./build.sh 0.13.0 ./out             # Build v0.13.0 into ./out
#   ./build.sh nightly ./dist           # Build latest nightly

set -euo pipefail

# --- Help ---
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '/^# build.sh/,/^$/ s/^# //p' "$0"
  exit 0
fi

# --- Parameters ---
VERSION="${1:-${VERSION:-latest}}"
OUTPUT_DIR="${2:-${OUTPUT_DIR:-.}}"
PACKAGE_REVISION="${3:-${PACKAGE_REVISION:-}}"

# --- Validation ---
if [[ -z "$VERSION" ]]; then
  echo "Error: VERSION must not be empty" >&2
  echo "Usage: $0 [VERSION] [OUTPUT_DIR] [PACKAGE_REVISION]" >&2
  exit 1
fi
if [[ -n "$PACKAGE_REVISION" && ! "$PACKAGE_REVISION" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: PACKAGE_REVISION must be a positive integer" >&2
  exit 1
fi

# --- Create temp build directory ---
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

echo "    Build dir: $BUILD_DIR"
echo "    Output dir: $OUTPUT_DIR"

# --- Resolve version aliases ---
if [[ "$VERSION" == "nightly" ]]; then
  echo "==> Building Neovim nightly (master branch)..."
elif [[ "$VERSION" == "latest" ]]; then
  echo "==> Detecting latest Neovim stable version..."
  if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required to resolve VERSION=latest" >&2
    exit 1
  fi
  github_headers=(-H 'Accept: application/vnd.github+json')
  if [[ -n "${GH_TOKEN:-}" ]]; then
    github_headers+=(-H "Authorization: Bearer ${GH_TOKEN}")
  fi
  response="$(curl --fail --silent --show-error --location \
    --retry 3 --retry-delay 2 --connect-timeout 10 --max-time 30 \
    "${github_headers[@]}" \
    https://api.github.com/repos/neovim/neovim/releases/latest)" || {
    echo "Error: Could not query the GitHub API while resolving VERSION=latest" >&2
    exit 1
  }
  VERSION="$(jq -r '.tag_name // empty' <<<"$response")"
  if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: GitHub API returned an invalid latest release tag: ${VERSION:-<empty>}" >&2
    exit 1
  fi
  VERSION="${VERSION#v}"
  echo "    Latest stable: v${VERSION}"
else
  echo "==> Building Neovim v${VERSION}..."
fi

SOURCE_VERSION="$VERSION"
PACKAGE_VERSION="$SOURCE_VERSION"
if [[ -n "$PACKAGE_REVISION" ]]; then
  PACKAGE_VERSION="${SOURCE_VERSION}-${PACKAGE_REVISION}"
fi

# --- Clone ---
if [[ "$VERSION" == "nightly" ]]; then
  echo "==> Cloning Neovim master branch..."
  git clone --depth 1 --branch master https://github.com/neovim/neovim "$BUILD_DIR" 2>&1
else
  echo "==> Cloning Neovim v${VERSION}..."
  git clone --depth 1 --branch "v${VERSION}" https://github.com/neovim/neovim "$BUILD_DIR" 2>&1
fi

# --- Build (via upstream Makefile which handles bundled deps first) ---
echo "==> Building (make CMAKE_BUILD_TYPE=RelWithDebInfo)..."
make -C "$BUILD_DIR" CMAKE_BUILD_TYPE=RelWithDebInfo

# --- Package ---
echo "==> Running cpack -G DEB..."
mkdir -p "$OUTPUT_DIR"
CPACK_ARGS=(-G DEB --config "$BUILD_DIR/build/CPackConfig.cmake" -B "$OUTPUT_DIR")
if [[ -n "$PACKAGE_REVISION" ]]; then
  CPACK_ARGS+=(-D "CPACK_DEBIAN_PACKAGE_RELEASE=${PACKAGE_REVISION}")
fi
cpack "${CPACK_ARGS[@]}"

# Record stable-release expectations independently from generated package
# metadata. Development and prerelease builds retain the historical metadata
# auto-detection behavior because their runtime/package version strings can be
# normalized by upstream Neovim.
if [[ "$SOURCE_VERSION" =~ ^[0-9]+[.][0-9]+[.][0-9]+$ ]]; then
  printf '%s\n' "$SOURCE_VERSION" > "$OUTPUT_DIR/EXPECTED_SOURCE_VERSION"
  printf '%s\n' "$PACKAGE_VERSION" > "$OUTPUT_DIR/EXPECTED_PACKAGE_VERSION"
else
  : > "$OUTPUT_DIR/EXPECTED_SOURCE_VERSION"
  : > "$OUTPUT_DIR/EXPECTED_PACKAGE_VERSION"
fi

# --- Verify output ---
if ! ls "$OUTPUT_DIR"/nvim-linux-*.deb >/dev/null 2>&1; then
  echo "Error: No .deb package found in $OUTPUT_DIR" >&2
  exit 1
fi

echo ""
echo "Done. Package created:"
ls -lh "$OUTPUT_DIR"/nvim-linux-*.deb
