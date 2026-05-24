#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

routes="$TMPDIR/routes"
tests_dir="$TMPDIR/tests/tools/collab/registry.py"
allowlist="$TMPDIR/coverage-gate-allowlist.txt"
mkdir -p "$routes/commands/collab/sample" "$tests_dir"
touch "$allowlist"

run_gate() {
  "$ROOT/tools/command-system/coverage-gate.sh" \
    --routes-dir "$routes" \
    --tests-dir "$tests_dir" \
    --allowlist "$allowlist" \
    --route-file commands/collab/sample/index.md "$@"
}

cat >"$routes/commands/collab/sample/index.md" <<'MD'
# sample route

<!-- abort: sample-missing-input -->
1. If input is missing, **ABORT**: input required.
MD
touch "$tests_dir/sample-missing-input.test.sh"
run_gate >"$TMPDIR/pass.out"

if ! grep -Fq "P9-required-only check passed" "$TMPDIR/pass.out"; then
  printf 'FAIL: expected passing fixture output\n' >&2
  cat "$TMPDIR/pass.out" >&2
  exit 1
fi

rm "$tests_dir/sample-missing-input.test.sh"
set +e
run_gate >"$TMPDIR/missing.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: missing required P9 test passed\n' >&2
  exit 1
fi

if ! grep -Fq "expected $tests_dir/sample-missing-input.test.sh" "$TMPDIR/missing.out"; then
  printf 'FAIL: missing-test output did not name expected file\n' >&2
  cat "$TMPDIR/missing.out" >&2
  exit 1
fi

cat >"$routes/commands/collab/sample/index.md" <<'MD'
# sample route

<!-- abort: missing-input -->
1. If input is missing, **ABORT**: input required.
MD
touch "$tests_dir/missing-input.test.sh"
set +e
run_gate >"$TMPDIR/anchor-format.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: anchor without subcommand prefix passed\n' >&2
  exit 1
fi

if ! grep -Fq "abort anchor must start with \`sample-\`" "$TMPDIR/anchor-format.out"; then
  printf 'FAIL: anchor-format output mismatch\n' >&2
  cat "$TMPDIR/anchor-format.out" >&2
  exit 1
fi

rm "$tests_dir/missing-input.test.sh"

cat >"$routes/commands/collab/sample/index.md" <<'MD'
# sample route

<!-- abort: sample-human-judgment -->
1. If judgment is required, **ABORT** (agent-honor-system): human review required.
MD
run_gate >"$TMPDIR/honor.out"

cat >"$routes/commands/collab/sample/index.md" <<'MD'
# sample route

1. If input is missing, **ABORT**: input required.
MD

set +e
run_gate >"$TMPDIR/unanchored.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: unanchored ABORT passed without allowlist\n' >&2
  exit 1
fi

if ! grep -Fq "unanchored ABORT outside allowlist" "$TMPDIR/unanchored.out"; then
  printf 'FAIL: unanchored output did not name failure\n' >&2
  cat "$TMPDIR/unanchored.out" >&2
  exit 1
fi

run_gate --print-unanchored-allowlist >"$allowlist"
run_gate >"$TMPDIR/allowlisted.out"

if ! grep -Fq "migration debt remains; 1 allowlisted unanchored ABORT clause(s)" "$TMPDIR/allowlisted.out"; then
  printf 'FAIL: allowlisted pass output did not report migration debt\n' >&2
  cat "$TMPDIR/allowlisted.out" >&2
  exit 1
fi

cat >"$routes/commands/collab/sample/index.md" <<'MD'
# sample route

No abort clauses here.
MD

set +e
run_gate >"$TMPDIR/zero.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: zero ABORT parse result passed\n' >&2
  exit 1
fi

if ! grep -Fq "found 0 ABORT clauses" "$TMPDIR/zero.out"; then
  printf 'FAIL: zero-case output mismatch\n' >&2
  cat "$TMPDIR/zero.out" >&2
  exit 1
fi

if ! grep -Fq "tools/command-system/coverage-gate.sh" "$ROOT/tools/command-system/audit.sh"; then
  printf 'FAIL: audit.sh does not invoke coverage gate\n' >&2
  exit 1
fi
