#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
printf '{"projectId":"test-seal-content-digest-fixture","label":"test"}\n' > .collab.json

RUN_DATE="$(date +%Y-%m-%d)"

read_json_field() {
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["'"$1"'"])'
}

seed_round() {
  local slug="$1"
  python3 - "$ROOT" "$REGISTRY" "$slug" <<'PY'
import json
import sys
from pathlib import Path

root = sys.argv[1]
path = Path(sys.argv[2])
target = sys.argv[3]
sys.path.insert(0, root)
from commands.collab.engine import registry as R

data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
verification = entry.setdefault('verification', {})
verification['rounds'] = 1
verification['subState'] = 'seal'
verification['pairedExecutionSignature'] = R.execution_signature(entry)
for role in R.participant_verification_roles(entry):
    state = R.participant_verification_role_state(entry, role)
    state['stage'] = 'completed'
    state['executionSignature'] = R.participant_execution_signature(entry, role)
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"

init_target() {
  local title="$1"
  local slug="$2"
  local work_repo="$3"
  "$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa --work-repo "$work_repo" "$title" >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$RUN_DATE-$slug" pa --agent-id opus >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$RUN_DATE-$slug" pe --agent-id codex >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" turn-order pe --caller-role mod >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" active-phase Completion --force --caller-role mod >/dev/null
}

make_repo() {
  local repo="$1"
  mkdir -p "$repo"
  git -C "$repo" init >/dev/null
  git -C "$repo" config user.name test
  git -C "$repo" config user.email test@example.invalid
}

EMPTY_WORK="$TMPDIR/empty-work"
make_repo "$EMPTY_WORK"
touch "$EMPTY_WORK/.keep"
git -C "$EMPTY_WORK" add .keep
git -C "$EMPTY_WORK" commit -m "initial empty fixture" >/dev/null

init_target "Seal Content Digest Empty Paths" "seal-content-digest-empty-paths" "$EMPTY_WORK"
TARGET="$RUN_DATE-seal-content-digest-empty-paths"
"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-23T18:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --caller-role pe >/dev/null

seed_round "$TARGET"
state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
"$ROOT/commands/collab/engine/registry.py" seal-write "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
entry = next(item for item in data['collabs'] if item['id'] == sys.argv[2])
seal = entry.get('verificationSeal', {})
execution = entry.get('execution', {}).get('pe', {})
if not seal.get('contentDigest') or seal.get('pathDigests') != {}:
    raise SystemExit(f"seal content digest not stable for empty touchedPaths: {seal!r}")
if not execution.get('contentDigest') or execution.get('pathDigests') != {}:
    raise SystemExit(f"execution content digest not stable for empty touchedPaths: {execution!r}")
PY

AMEND_WORK="$TMPDIR/amend-work"
make_repo "$AMEND_WORK"
printf 'stable content\n' > "$AMEND_WORK/deliverable.txt"
git -C "$AMEND_WORK" add deliverable.txt
GIT_AUTHOR_DATE="2026-05-23T17:00:00+02:00" \
GIT_COMMITTER_DATE="2026-05-23T17:00:00+02:00" \
  git -C "$AMEND_WORK" commit -m "initial content" >/dev/null
old_head="$(git -C "$AMEND_WORK" rev-parse HEAD)"

init_target "Seal Content Digest Amend Stable" "seal-content-digest-amend-stable" "$AMEND_WORK"
AMEND_TARGET="$RUN_DATE-seal-content-digest-amend-stable"
"$ROOT/commands/collab/engine/registry.py" execution "$AMEND_TARGET" pe completed "2026-05-23T18:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --touched-path deliverable.txt \
  --caller-role pe >/dev/null
seed_round "$AMEND_TARGET"
amend_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$AMEND_TARGET" pa)"
amend_revision="$(read_json_field registryRevision <<<"$amend_state")"
"$ROOT/commands/collab/engine/registry.py" seal-write "$AMEND_TARGET" pa --observed-revision "$amend_revision" --caller-role pa >/dev/null
GIT_AUTHOR_DATE="2026-05-23T17:30:00+02:00" \
GIT_COMMITTER_DATE="2026-05-23T17:30:00+02:00" \
  git -C "$AMEND_WORK" commit --amend --no-edit --date "2026-05-23T17:30:00+02:00" >/dev/null
new_head="$(git -C "$AMEND_WORK" rev-parse HEAD)"
if [[ "$old_head" == "$new_head" ]]; then
  printf 'FAIL: amend fixture did not change commit identity\n' >&2
  exit 1
fi
assessment_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$AMEND_TARGET" pa)"
assessment_revision="$(read_json_field registryRevision <<<"$assessment_state")"
"$ROOT/commands/collab/engine/registry.py" record-verdict "$AMEND_TARGET" pa --observed-revision "$assessment_revision" --caller-role pa --outcome success >/dev/null

DELETE_WORK="$TMPDIR/delete-work"
make_repo "$DELETE_WORK"
printf 'removed content\n' > "$DELETE_WORK/deleted.txt"
git -C "$DELETE_WORK" add deleted.txt
GIT_AUTHOR_DATE="2026-05-23T17:00:00+02:00" \
GIT_COMMITTER_DATE="2026-05-23T17:00:00+02:00" \
  git -C "$DELETE_WORK" commit -m "add deleted fixture" >/dev/null
rm "$DELETE_WORK/deleted.txt"
git -C "$DELETE_WORK" add deleted.txt
GIT_AUTHOR_DATE="2026-05-23T17:30:00+02:00" \
GIT_COMMITTER_DATE="2026-05-23T17:30:00+02:00" \
  git -C "$DELETE_WORK" commit -m "delete fixture path" >/dev/null

init_target "Seal Content Digest Committed Deletion" "seal-content-digest-committed-deletion" "$DELETE_WORK"
DELETE_TARGET="$RUN_DATE-seal-content-digest-committed-deletion"
"$ROOT/commands/collab/engine/registry.py" execution "$DELETE_TARGET" pe completed "2026-05-23T18:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --touched-path deleted.txt \
  --caller-role pe >/dev/null
seed_round "$DELETE_TARGET"
delete_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$DELETE_TARGET" pa)"
delete_revision="$(read_json_field registryRevision <<<"$delete_state")"
"$ROOT/commands/collab/engine/registry.py" seal-write "$DELETE_TARGET" pa --observed-revision "$delete_revision" --caller-role pa >/dev/null

python3 - "$REGISTRY" "$DELETE_TARGET" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
entry = next(item for item in data['collabs'] if item['id'] == sys.argv[2])
digest = entry.get('verificationSeal', {}).get('pathDigests', {}).get('deleted.txt')
expected = {'mode': '000000', 'blob': '0000000000000000000000000000000000000000'}
if digest != expected:
    raise SystemExit(f"committed deletion digest mismatch: {digest!r}")
PY

printf 'OK: content digest is stable across amend and committed deletion\n'
