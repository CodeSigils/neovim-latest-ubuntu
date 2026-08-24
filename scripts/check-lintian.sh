#!/usr/bin/env bash
# Fail when lintian reports a tag not present in the reviewed allowlist.

set -euo pipefail

DEB="${1:?usage: check-lintian.sh DEB ALLOWLIST}"
ALLOWLIST="${2:?usage: check-lintian.sh DEB ALLOWLIST}"
REPORT="$(mktemp)"
trap 'rm -f "$REPORT"' EXIT

set +e
lintian --tag-display-limit 0 "$DEB" >"$REPORT" 2>&1
status=$?
set -e
cat "$REPORT"

if [[ "$status" -eq 0 ]]; then
  exit 0
fi

mapfile -t findings < <(
  sed -nE 's/^[EW]: [^:]+: ([^ ]+).*/\1/p' "$REPORT" | sort -u
)

if ((${#findings[@]} == 0)); then
  echo "Lintian failed without reporting a parseable error or warning tag." >&2
  exit "$status"
fi

unexpected=()
for tag in "${findings[@]}"; do
  if ! grep -Fxq "$tag" "$ALLOWLIST"; then
    unexpected+=("$tag")
  fi
done

if ((${#unexpected[@]} > 0)); then
  printf 'New lintian findings are not in %s:\n' "$ALLOWLIST" >&2
  printf '  - %s\n' "${unexpected[@]}" >&2
  exit 1
fi

echo "All lintian findings match the reviewed compatibility-package baseline."
