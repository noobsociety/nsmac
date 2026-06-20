#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

GATE="$ROOT/platform/tooling/audit-vocabulary.sh"

_scaffold() {
  local dir="$1"
  mkdir -p "$dir/commands/collab/engine" "$dir/commands/collab/reference"
  cat >"$dir/commands/collab/engine/registry_constants.py" <<'PY'
PHASES = ['Audit', 'Discussion', 'Conclusion', 'Action Plan', 'Handoff', 'Completion']
ALLOWED_COMPLETION_SUBSTATES = {'execution', 'verification'}
ALLOWED_VERIFICATION_SUBSTATES = {'participant', 'seal', 'assessment'}
ALLOWED_PARTICIPANT_VERIFICATION_STAGES = {'audit', 'remediation', 'final-audit', 'completed', 'failed'}
ALLOWED_VERDICT_OUTCOMES = {'success', 'incomplete', 'failed'}
ALLOWED_VERDICT_RESTORE_TARGETS = {'Action Plan', 'Handoff'}
ALLOWED_CAP_EXITS = {'reopen-action-plan', 'reopen-handoff', 'follow-up-collab', 'archive'}
ALLOWED_TERMINALS = {'seal', 'issue'}
PY
  cat >"$dir/commands/collab/reference/phase-admissibility.md" <<'MD'
Audit Discussion Conclusion Action Plan Handoff Completion
MD
  cat >"$dir/commands/collab/reference/glossary.md" <<'MD'
terminal values: seal issue
MD
  cat >"$dir/commands/collab/reference/verification.md" <<'MD'
execution verification participant seal assessment audit remediation final-audit completed failed success incomplete failed Action Plan Handoff reopen-action-plan reopen-handoff follow-up-collab archive

## Operator guidance: participant verify inactive

guidance text
MD
  cat >"$dir/commands/collab/engine/seal_verification.py" <<'PY'
ref = 'commands/collab/reference/verification.md#operator-guidance-participant-verify-inactive'
PY
}

passing="$TMPDIR/passing"
_scaffold "$passing"
COMMAND_CONFIG_ROOT="$passing" "$GATE" >"$TMPDIR/passing.out"

if ! grep -Fxq 'OK: collab vocabulary mirrors registry constants' "$TMPDIR/passing.out"; then
  printf 'FAIL: passing fixture did not report stable OK output\n' >&2
  cat "$TMPDIR/passing.out" >&2
  exit 1
fi

drift="$TMPDIR/drift"
_scaffold "$drift"
perl -0pi -e 's/reopen-handoff //' "$drift/commands/collab/reference/verification.md"

if COMMAND_CONFIG_ROOT="$drift" "$GATE" >"$TMPDIR/drift.out" 2>&1; then
  printf 'FAIL: drift fixture should fail\n' >&2
  exit 1
fi

if ! grep -Fxq 'FAIL: commands/collab/reference/verification.md: missing `reopen-handoff` from ALLOWED_CAP_EXITS' "$TMPDIR/drift.out"; then
  printf 'FAIL: drift output did not name missing token\n' >&2
  cat "$TMPDIR/drift.out" >&2
  exit 1
fi

anchor_drift="$TMPDIR/anchor-drift"
_scaffold "$anchor_drift"
perl -0pi -e 's/## Operator guidance: participant verify inactive/## Renamed section/' "$anchor_drift/commands/collab/reference/verification.md"

if COMMAND_CONFIG_ROOT="$anchor_drift" "$GATE" >"$TMPDIR/anchor-drift.out" 2>&1; then
  printf 'FAIL: anchor-drift fixture should fail\n' >&2
  exit 1
fi

if ! grep -Fxq 'FAIL: commands/collab/engine/seal_verification.py: dangling ref `verification.md#operator-guidance-participant-verify-inactive` (no matching heading in verification.md)' "$TMPDIR/anchor-drift.out"; then
  printf 'FAIL: anchor-drift output did not name dangling ref\n' >&2
  cat "$TMPDIR/anchor-drift.out" >&2
  exit 1
fi

slug_parity="$TMPDIR/slug-parity"
_scaffold "$slug_parity"
cat >"$slug_parity/commands/collab/reference/verification.md" <<'MD'
execution verification participant seal assessment audit remediation final-audit completed failed success incomplete failed Action Plan Handoff reopen-action-plan reopen-handoff follow-up-collab archive

## Operator guidance: participant verify inactive

## Closing hashes heading ##

## Repeated heading

## Repeated heading

## Unicode Θ_Anchor heading ##
MD
cat >"$slug_parity/commands/collab/engine/seal_verification.py" <<'PY'
a = 'verification.md#operator-guidance-participant-verify-inactive'
b = 'verification.md#closing-hashes-heading'
c = 'verification.md#repeated-heading-1'
d = 'verification.md#unicode-θ_anchor-heading'
PY

if ! COMMAND_CONFIG_ROOT="$slug_parity" "$GATE" >"$TMPDIR/slug-parity.out" 2>&1; then
  printf 'FAIL: slug-parity fixture should pass (closing-hash + duplicate anchors must resolve)\n' >&2
  cat "$TMPDIR/slug-parity.out" >&2
  exit 1
fi

printf 'audit-vocabulary: all tests passed\n'
