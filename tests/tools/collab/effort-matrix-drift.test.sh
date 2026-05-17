#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$ROOT"

"$ROOT/tools/collab/registry.py" audit-effort-matrix >/dev/null

sed '/generated; do not edit/d' \
  "$ROOT/_functions/collab/_agent-model.md" >"$TMPDIR/no-marker.md"

set +e
marker_output="$("$ROOT/tools/collab/registry.py" audit-effort-matrix \
  --agent-model "$TMPDIR/no-marker.md" 2>&1)"
marker_status=$?
set -e

if [[ "$marker_status" -eq 0 ]]; then
  printf 'FAIL: audit-effort-matrix accepted missing generated marker\n' >&2
  exit 1
fi

if [[ "$marker_output" != *"header-missing"* ]]; then
  printf 'FAIL: missing-marker output does not name header-missing case\n%s\n' "$marker_output" >&2
  exit 1
fi

sed 's/| Conclusion | low | medium | medium | xhigh |/| Conclusion | low | medium | high | xhigh |/' \
  "$ROOT/_functions/collab/_agent-model.md" >"$TMPDIR/drift.md"

set +e
drift_output="$("$ROOT/tools/collab/registry.py" audit-effort-matrix \
  --agent-model "$TMPDIR/drift.md" 2>&1)"
drift_status=$?
set -e

if [[ "$drift_status" -eq 0 ]]; then
  printf 'FAIL: audit-effort-matrix accepted rendered cell drift\n' >&2
  exit 1
fi

if [[ "$drift_output" != *"role pe, phase/row Conclusion: JSON value medium, rendered value high"* ]]; then
  printf 'FAIL: drift output does not name role, phase/row, JSON value, and rendered value\n%s\n' "$drift_output" >&2
  exit 1
fi

grep -v '^| Completion\.verification |' \
  "$ROOT/_functions/collab/_agent-model.md" >"$TMPDIR/missing-row.md"

set +e
row_output="$("$ROOT/tools/collab/registry.py" audit-effort-matrix \
  --agent-model "$TMPDIR/missing-row.md" 2>&1)"
row_status=$?
set -e

if [[ "$row_status" -eq 0 ]]; then
  printf 'FAIL: audit-effort-matrix accepted missing Completion.verification row\n' >&2
  exit 1
fi

if [[ "$row_output" != *"phase/row Completion.verification"* || "$row_output" != *"rendered value missing-row"* ]]; then
  printf 'FAIL: missing-row output does not name the missing phase row\n%s\n' "$row_output" >&2
  exit 1
fi

printf 'OK: effort matrix drift audit enforces marker and JSON projection\n'
