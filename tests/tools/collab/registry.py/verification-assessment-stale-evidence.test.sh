#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Verification Assessment Stale Evidence" "verification-assessment-stale-evidence"
TARGET="$RUN_DATE-verification-assessment-stale-evidence"
REGISTRY="$(registry_path)"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$TARGET"

REVISION="$(assessment_revision "$TARGET")"
set +e
reseal_output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$REVISION" --caller-role pa 2>&1)"
reseal_status=$?
set -e
if [[ "$reseal_status" -eq 0 || "$reseal_output" != *"verification assessment is active; seal block is immutable; provide --outcome to record a verdict"* ]]; then
  printf 'FAIL: assessment allowed seal block mutation\n%s\n' "$reseal_output" >&2
  exit 1
fi

"$ROOT/tools/collab/registry.py" transcript-repair "$TARGET" --touch-execution-evidence --caller-role mod >/dev/null
REVISION="$(assessment_revision "$TARGET")"
set +e
success_output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$REVISION" \
  --outcome success \
  --caller-role pa 2>&1)"
success_status=$?
set -e
if [[ "$success_status" -eq 0 || "$success_output" != *"success verdict requires current non-stale verificationSeal; stale: transcript repair touched execution evidence"* ]]; then
  printf 'FAIL: stale seal accepted success verdict\n%s\n' "$success_output" >&2
  exit 1
fi

"$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$REVISION" \
  --outcome failed \
  --restore-target Handoff \
  --restore-reason "The sealed execution evidence became stale." \
  --evidence '{"registryRevision":3,"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"]}' \
  --caller-role pa >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-assessment-stale-evidence')
assert entry['status'] == 'open'
assert entry['verificationSeal']['stale'] is True
assert entry['verification']['subState'] == 'assessment'
assert entry['verdict']['outcome'] == 'failed'
assert entry['verdict']['restoreTarget'] == 'Handoff'
PY

printf 'OK: verification assessment rejects seal mutation and stale success verdicts\n'
