#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

routes="$TMPDIR/routes"
tests_dir="$TMPDIR/tests/commands/collab/registry.py"
mkdir -p "$routes/commands/collab/sample" "$tests_dir"

run_gate() {
  "$ROOT/platform/tooling/coverage-gate.sh" \
    --routes-dir "$routes" \
    --tests-dir "$tests_dir" \
    --route-file commands/collab/sample/index.md "$@"
}

cat >"$routes/commands/collab/sample/index.md" <<'MD'
# sample route

<!-- abort: sample-missing-input -->
1. If input is missing, **ABORT**: input required.
MD
touch "$tests_dir/sample-missing-input.test.sh"
run_gate >"$TMPDIR/pass.out"

if ! grep -Fq "abort coverage check passed" "$TMPDIR/pass.out"; then
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
  printf 'FAIL: unanchored ABORT passed without anchor\n' >&2
  exit 1
fi

if ! grep -Fq "unanchored ABORT" "$TMPDIR/unanchored.out"; then
  printf 'FAIL: unanchored output did not name failure\n' >&2
  cat "$TMPDIR/unanchored.out" >&2
  exit 1
fi

cat >"$routes/commands/collab/sample/index.md" <<'MD'
# sample route

<!-- abort: sample-restored -->
1. If input is missing, **ABORT**: input required.
MD
touch "$tests_dir/sample-restored.test.sh"

set +e
run_gate --allowlist "$TMPDIR/retired-allowlist.txt" >"$TMPDIR/allowlist-arg.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: retired --allowlist argument passed\n' >&2
  exit 1
fi

if ! grep -Fq "unrecognized arguments: --allowlist" "$TMPDIR/allowlist-arg.out"; then
  printf 'FAIL: retired --allowlist argument was not rejected by argparse\n' >&2
  cat "$TMPDIR/allowlist-arg.out" >&2
  exit 1
fi

set +e
run_gate --print-unanchored-allowlist >"$TMPDIR/print-allowlist.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: retired --print-unanchored-allowlist argument passed\n' >&2
  exit 1
fi

if ! grep -Fq "unrecognized arguments: --print-unanchored-allowlist" "$TMPDIR/print-allowlist.out"; then
  printf 'FAIL: retired --print-unanchored-allowlist argument was not rejected\n' >&2
  cat "$TMPDIR/print-allowlist.out" >&2
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

if ! grep -Fq "platform/tooling/coverage-gate.sh" "$ROOT/platform/tooling/audit.sh"; then
  printf 'FAIL: audit.sh does not invoke coverage gate\n' >&2
  exit 1
fi
