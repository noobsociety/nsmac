#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

fixture_dir="$ROOT/tests/fixtures/audit-role-prose"
clean_root="$TMPDIR/clean"
dirty_root="$TMPDIR/dirty"
mkdir -p "$clean_root/docs" "$dirty_root/docs"

cp "$fixture_dir/allowed.md.fixture" "$clean_root/docs/allowed.md"
cp "$fixture_dir/allowed.sh.fixture" "$clean_root/docs/allowed.sh"
cp "$fixture_dir/allowed.py.fixture" "$clean_root/docs/allowed.py"

"$ROOT/platform/tooling/audit-role-prose.sh" --root "$clean_root" >"$TMPDIR/clean.out"

if [[ -s "$TMPDIR/clean.out" ]]; then
  printf 'FAIL: expected clean fixture to produce empty output\n' >&2
  cat "$TMPDIR/clean.out" >&2
  exit 1
fi

cp "$fixture_dir/violation.md.fixture" "$dirty_root/docs/violation.md"

set +e
"$ROOT/platform/tooling/audit-role-prose.sh" --root "$dirty_root" >"$TMPDIR/dirty.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected violation fixture to fail\n' >&2
  exit 1
fi

if ! grep -Fxq 'docs/violation.md:3' "$TMPDIR/dirty.out"; then
  printf 'FAIL: violation output did not use stable path:line form\n' >&2
  cat "$TMPDIR/dirty.out" >&2
  exit 1
fi

printf 'OK: role prose audit detects in-scope drift and preserves carve-outs\n'
