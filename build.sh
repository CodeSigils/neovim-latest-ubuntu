#!/usr/bin/env bash
# build.sh — Build Neovim from source and package as .deb
#
# Usage: ./build.sh [VERSION] [OUTPUT_DIR]
#   VERSION     Neovim release tag (default: 0.12.2)
#   OUTPUT_DIR  Where to place the built .deb (default: .)
#
# Examples:
#   ./build.sh                          # Build v0.12.2 into current dir
#   ./build.sh 0.13.0 ./out             # Build v0.13.0 into ./out
#   ./build.sh nightly ./dist           # Build latest nightly

set -euo pipefail

# --- Help ---
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '/^# build.sh/,/^$/ s/^# //p' "$0"
  exit 0
fi

# --- Parameters ---
VERSION="${1:-${VERSION:-0.12.2}}"
OUTPUT_DIR="${2:-${OUTPUT_DIR:-.}}"

# --- Validation ---
if [[ -z "$VERSION" ]]; then
  echo "Error: VERSION must not be empty" >&2
  echo "Usage: $0 [VERSION] [OUTPUT_DIR]" >&2
  exit 1
fi

# --- Create temp build directory ---
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

echo "==> Building Neovim v${VERSION}..."
echo "    Build dir: $BUILD_DIR"
echo "    Output dir: $OUTPUT_DIR"

# --- Handle "latest" alias ---
if [[ "$VERSION" == "latest" ]]; then
  echo "==> Detecting latest Neovim stable version..."
  VERSION="$(curl -sL https://api.github.com/repos/neovim/neovim/releases/latest \
    | grep -oP '"tag_name": "\K[^"]+' | sed 's/^v//')"
  if [[ -z "$VERSION" ]]; then
    echo "Error: Could not detect latest version from GitHub API" >&2
    exit 1
  fi
  echo "    Latest stable: v${VERSION}"
fi

# --- Clone ---
echo "==> Cloning Neovim v${VERSION}..."
git clone --depth 1 --branch "v${VERSION}" https://github.com/neovim/neovim "$BUILD_DIR" 2>&1

# --- Build (via upstream Makefile which handles bundled deps first) ---
echo "==> Building (make CMAKE_BUILD_TYPE=RelWithDebInfo)..."
make -C "$BUILD_DIR" CMAKE_BUILD_TYPE=RelWithDebInfo

# --- Package ---
echo "==> Running cpack -G DEB..."
cpack -G DEB --config "$BUILD_DIR/build/CPackConfig.cmake"

# --- Copy output ---
mkdir -p "$OUTPUT_DIR"
cp "$BUILD_DIR/build"/nvim-linux-*.deb "$OUTPUT_DIR" 2>/dev/null || {
  echo "Error: No .deb package found in build output" >&2
  exit 1
}

echo ""
echo "Done. Package created:"
ls -lh "$OUTPUT_DIR"/nvim-linux-*.deb
