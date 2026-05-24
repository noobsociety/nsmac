#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

make_fixture() {
  local dir="$1"
  mkdir -p "$dir/commands/collab/speak" "$dir/tools/collab"
  cp "$ROOT/commands/collab/speak/index.md" "$dir/commands/collab/speak/index.md"
  cp "$ROOT/tools/collab/registry.py" "$dir/tools/collab/registry.py"
}

clean="$TMPDIR/clean"
make_fixture "$clean"
"$ROOT/tools/collab/audit-reviewer-conclusion.sh" --root "$clean" >"$TMPDIR/clean.out"
if ! grep -Fq 'OK: reviewer Audit/Conclusion discipline gates are documented and wired' "$TMPDIR/clean.out"; then
  printf 'FAIL: clean reviewer audit fixture did not pass\n' >&2
  cat "$TMPDIR/clean.out" >&2
  exit 1
fi

missing_audit_gate="$TMPDIR/missing-audit-gate"
make_fixture "$missing_audit_gate"
perl -0pi -e 's/LOOP CHECK/LOOP MISSED/' "$missing_audit_gate/commands/collab/speak/index.md"
set +e
"$ROOT/tools/collab/audit-reviewer-conclusion.sh" --root "$missing_audit_gate" >"$TMPDIR/missing-audit-gate.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: reviewer audit accepted missing Audit gate label\n' >&2
  exit 1
fi
if ! grep -Fq 'missing Audit reviewer gate in speak docs: LOOP CHECK' "$TMPDIR/missing-audit-gate.out"; then
  printf 'FAIL: missing Audit gate output mismatch\n' >&2
  cat "$TMPDIR/missing-audit-gate.out" >&2
  exit 1
fi

missing_conclusion_call="$TMPDIR/missing-conclusion-call"
make_fixture "$missing_conclusion_call"
perl -0pi -e 's/validate_reviewer_conclusion_gates\(content, phase, role, current_entry\)/validate_reviewer_conclusion_gate_disabled(content, phase, role, current_entry)/' \
  "$missing_conclusion_call/tools/collab/registry.py"
set +e
"$ROOT/tools/collab/audit-reviewer-conclusion.sh" --root "$missing_conclusion_call" >"$TMPDIR/missing-conclusion-call.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: reviewer audit accepted missing Conclusion gate call\n' >&2
  exit 1
fi
if ! grep -Fq 'speak-render must call reviewer Conclusion gate before mutation' "$TMPDIR/missing-conclusion-call.out"; then
  printf 'FAIL: missing Conclusion gate output mismatch\n' >&2
  cat "$TMPDIR/missing-conclusion-call.out" >&2
  exit 1
fi

printf 'OK: reviewer conclusion audit detects gate documentation and wiring drift\n'
