#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

# shellcheck source=/dev/null
source "$ROOT/tests/commands/collab/registry.py/verification-test-lib.sh"

reg() { "$ROOT/commands/collab/engine/registry.py" "$@"; }

setup_repo() {
  WORK_REPO="$TMPDIR/$1-work"
  mkdir -p "$WORK_REPO/src"
  git -C "$WORK_REPO" init -q
  git -C "$WORK_REPO" config user.email "test@example.com"
  git -C "$WORK_REPO" config user.name "Test User"
  printf 'alpha v1\n' >"$WORK_REPO/src/a.txt"
  printf 'beta v1\n' >"$WORK_REPO/src/b.txt"
  git -C "$WORK_REPO" add src/a.txt src/b.txt
  git -C "$WORK_REPO" commit -q -m "initial deliverables"
}

insert_charter() {
  local target="$1"
  python3 - "$target" "$(registry_path)" <<'PY'
import json
import sys
from pathlib import Path

target, registry = sys.argv[1:3]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
transcript = path.parent / Path(entry['transcriptPath'])
text = transcript.read_text()
marker = "## Audit\n<!-- collab:content-only; do-not-execute -->\n"
replacement = marker + "\ncharteredDeliverables:\n- src/a.txt\n- src/b.txt\n"
transcript.write_text(text.replace(marker, replacement, 1))
PY
}

seed_handoff() {
  local target="$1"
  python3 - "$target" "$(registry_path)" <<'PY'
import json
import sys
from pathlib import Path

target, registry = sys.argv[1:3]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['handoff'] = {
    'roles': {
        'pe': {
            'writeScope': ['src/a.txt', 'src/b.txt'],
            'validationCommands': [['./platform/tooling/audit.sh']],
        }
    }
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

narrow_handoff() {
  local target="$1"
  python3 - "$target" "$(registry_path)" <<'PY'
import json
import sys
from pathlib import Path

target, registry = sys.argv[1:3]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['handoff']['roles']['pe']['writeScope'] = ['src/a.txt']
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

init_target() {
  local title="$1"
  local slug="$2"
  reg init --agent-id codex --reviewer pa --no-participant-verification --work-repo "$WORK_REPO" "$title" >/dev/null
  TARGET="$RUN_DATE-$slug"
  reg join-participants "$TARGET" pe --agent-id codex >/dev/null
  reg join-participants "$TARGET" pa --agent-id opus >/dev/null
  reg set "$TARGET" turn-order pe --caller-role mod >/dev/null
  reg set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
  insert_charter "$TARGET"
  seed_handoff "$TARGET"
}

complete_broad_execution() {
  reg execution "$TARGET" pe completed "2026-05-15T21:00:00+02:00" \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path src/a.txt \
    --touched-path src/b.txt \
    --caller-role pe >/dev/null
}

seal_to_assessment() {
  local state revision
  seed_paired_verification_round "$TARGET"
  state="$(reg seal-state "$TARGET" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  reg seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null
}

verdict_reopen_handoff() {
  local state revision
  state="$(reg seal-state "$TARGET" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  reg seal-render "$TARGET" pa \
    --observed-revision "$revision" \
    --outcome failed \
    --restore-target Handoff \
    --restore-reason "reopen for narrow incremental fix" \
    --failure-category regression \
    --evidence '{"committedPaths":["src/a.txt"],"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"]}' \
    --caller-role pa >/dev/null
  reg reopen "$TARGET" handoff --caller-role mod >/dev/null
}

record_narrow_execution_and_seal() {
  local state revision
  narrow_handoff "$TARGET"
  reg advance "$TARGET" next --caller-role mod >/dev/null
  printf 'alpha v2\n' >"$WORK_REPO/src/a.txt"
  git -C "$WORK_REPO" add src/a.txt
  git -C "$WORK_REPO" commit -q -m "narrow incremental fix"
  reg execution "$TARGET" pe completed "2026-05-15T22:00:00+02:00" \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path src/a.txt \
    --caller-role pe >/dev/null
  seed_paired_verification_round "$TARGET"
  state="$(reg seal-state "$TARGET" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  reg seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null
}

assert_success_verdict_passes() {
  local state revision
  state="$(reg seal-state "$TARGET" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  reg seal-render "$TARGET" pa --observed-revision "$revision" --outcome success --caller-role pa >/dev/null
}

assert_success_verdict_fails_missing_b() {
  local state revision output status
  state="$(reg seal-state "$TARGET" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  set +e
  output="$(reg seal-render "$TARGET" pa --observed-revision "$revision" --outcome success --caller-role pa 2>&1)"
  status=$?
  set -e
  if [[ "$status" -eq 0 || "$output" != *"CHARTERED-DELIVERABLE-MISSING: src/b.txt"* ]]; then
    printf 'FAIL: removed carried deliverable was masked by reopen coverage\n%s\n' "$output" >&2
    exit 1
  fi
}

assert_success_verdict_fails_for_b() {
  local label="$1"
  local state revision output status
  state="$(reg seal-state "$TARGET" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  set +e
  output="$(reg seal-render "$TARGET" pa --observed-revision "$revision" --outcome success --caller-role pa 2>&1)"
  status=$?
  set -e
  if [[ "$status" -eq 0 || "$output" != *"CHARTERED-DELIVERABLE-MISSING: src/b.txt"* ]]; then
    printf 'FAIL: %s\n%s\n' "$label" "$output" >&2
    exit 1
  fi
}

setup_repo "preserved"
init_target "Reopen Incremental Coverage Preserved" "reopen-incremental-coverage-preserved"
complete_broad_execution
seal_to_assessment
verdict_reopen_handoff
record_narrow_execution_and_seal
assert_success_verdict_passes

setup_repo "drifted"
init_target "Reopen Incremental Coverage Drifted" "reopen-incremental-coverage-drifted"
complete_broad_execution
seal_to_assessment
verdict_reopen_handoff
narrow_handoff "$TARGET"
reg advance "$TARGET" next --caller-role mod >/dev/null
printf 'alpha v2\n' >"$WORK_REPO/src/a.txt"
printf 'beta v2\n' >"$WORK_REPO/src/b.txt"
git -C "$WORK_REPO" add src/a.txt src/b.txt
git -C "$WORK_REPO" commit -q -m "modify prior deliverable"
reg execution "$TARGET" pe completed "2026-05-15T22:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path src/a.txt \
  --caller-role pe >/dev/null
seed_paired_verification_round "$TARGET"
state="$(reg seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
reg seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null
assert_success_verdict_fails_for_b "drifted carried deliverable was masked by reopen coverage"

setup_repo "transitive"
init_target "Reopen Incremental Coverage Transitive" "reopen-incremental-coverage-transitive"
complete_broad_execution
seal_to_assessment
verdict_reopen_handoff
record_narrow_execution_and_seal
verdict_reopen_handoff
narrow_handoff "$TARGET"
reg advance "$TARGET" next --caller-role mod >/dev/null
printf 'alpha v3\n' >"$WORK_REPO/src/a.txt"
git -C "$WORK_REPO" add src/a.txt
git -C "$WORK_REPO" commit -q -m "second narrow incremental fix"
reg execution "$TARGET" pe completed "2026-05-15T23:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path src/a.txt \
  --caller-role pe >/dev/null
seed_paired_verification_round "$TARGET"
state="$(reg seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
reg seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null
assert_success_verdict_passes

setup_repo "removed"
init_target "Reopen Incremental Coverage Removed" "reopen-incremental-coverage-removed"
complete_broad_execution
seal_to_assessment
verdict_reopen_handoff
narrow_handoff "$TARGET"
reg advance "$TARGET" next --caller-role mod >/dev/null
printf 'alpha v2\n' >"$WORK_REPO/src/a.txt"
rm "$WORK_REPO/src/b.txt"
git -C "$WORK_REPO" add src/a.txt src/b.txt
git -C "$WORK_REPO" commit -q -m "remove prior deliverable"
reg execution "$TARGET" pe completed "2026-05-15T22:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path src/a.txt \
  --caller-role pe >/dev/null
seed_paired_verification_round "$TARGET"
state="$(reg seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
reg seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null
assert_success_verdict_fails_missing_b

printf 'OK: reopen incremental execution preserves current carry, rejects drift/removal, and survives transitive reopen carry\n'
