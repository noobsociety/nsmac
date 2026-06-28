#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

upper_token="M""C""P"
lower_token="m""c""p"
pattern="(${upper_token}s?|${lower_token}s?)"

expected_paths=(
  "platform/reference.md"
  "platform/standards/doctrine.md"
  "platform/standards/framework-boundaries.md"
  "platform/tooling/sync-framework-boundaries.sh"
)

actual="$(
  git grep -Il -E "$pattern" -- . | sort
)"
expected="$(printf '%s\n' "${expected_paths[@]}")"

if [[ "$actual" != "$expected" ]]; then
  printf 'FAIL: boundary token mention set changed\n' >&2
  printf 'Expected:\n%s\n' "$expected" >&2
  printf 'Actual:\n%s\n' "$actual" >&2
  exit 1
fi

if ! grep -Fq "$upper_token" platform/standards/framework-boundaries.md \
  || ! grep -Fq "out of scope" platform/standards/framework-boundaries.md; then
  printf 'FAIL: framework boundary no longer states the loose out-of-scope claim\n' >&2
  exit 1
fi

printf 'OK: protocol boundary mention set stays pinned to the declared source files\n'
