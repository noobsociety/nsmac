#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

assert_not_ignored() {
  local path="$1"
  if git check-ignore -q --no-index "$path"; then
    printf 'FAIL: source path is ignored by .gitignore: %s\n' "$path" >&2
    exit 1
  fi
}

assert_ignored() {
  local path="$1"
  if ! git check-ignore -q --no-index "$path"; then
    printf 'FAIL: runtime path is not ignored by .gitignore: %s\n' "$path" >&2
    exit 1
  fi
}

assert_not_ignored commands/collab/reference/example-new-source.md
assert_not_ignored commands/collab/data/example.json
assert_not_ignored platform/standards/example-new-source.md
assert_not_ignored platform/tooling/example-new-source.sh
assert_ignored core/new-shared-surface/example.md
assert_ignored tools/new-helper/example.sh
assert_ignored data/example.json
assert_ignored templates/example.md
assert_ignored projects/example-runtime-state.json
assert_ignored "projects/example/m""cps/server.json"

lower_token="m""cp"
upper_token="M""CP"
managed_marker="$(printf '\x43\x55\x52\x53\x4f\x52 \x4d\x41\x4e\x41\x47\x45\x44')"
if grep -Fq "$managed_marker" .gitignore; then
  printf 'FAIL: .gitignore contains host-managed rewrite marker\n' >&2
  exit 1
fi
if grep -Eq '^!projects(/|$)' .gitignore; then
  printf 'FAIL: .gitignore un-ignores projects runtime state\n' >&2
  exit 1
fi
if grep -Eq "(${lower_token}|${upper_token})" .gitignore; then
  printf 'FAIL: .gitignore contains protocol-specific runtime token\n' >&2
  exit 1
fi

printf 'OK: .gitignore allowlist rejects retired roots and keeps slice/platform source trackable\n'
