#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

MIGRATE="$ROOT/platform/tooling/migrate-collab-state-dirs.sh"
REGISTRY="$ROOT/commands/collab/engine/registry.py"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local label="$3"
  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'FAIL: %s\nexpected to find: %s\nin: %s\n' "$label" "$needle" "$haystack" >&2
    exit 1
  fi
}

make_legacy_project() {
  local project_root="$1"
  local state_home="$2"
  local old_id="$3"
  local label="$4"
  mkdir -p "$project_root" "$state_home/$old_id"
  python3 - "$project_root" "$state_home" "$old_id" "$label" <<'PY'
import json
import sys
from pathlib import Path

project_root = Path(sys.argv[1])
state_home = Path(sys.argv[2])
old_id = sys.argv[3]
label = sys.argv[4]
(project_root / '.collab.json').write_text(json.dumps({
    'projectId': old_id,
    'label': label,
    'state': {'mode': 'shared', 'isolation': 'opt-in'},
}, indent=2) + '\n')
(state_home / old_id / 'registry.json').write_text(json.dumps({
    'activeCollabId': None,
    'collabs': [],
    'project': {'projectId': old_id, 'label': label},
}, indent=2) + '\n')
PY
}

read_marker_id() {
  python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads((Path(sys.argv[1]) / '.collab.json').read_text())['projectId'])
PY
}

case_slug_format_and_noobsociety_sanitization() {
  local project="$TMPDIR/noobsociety.com"
  local state="$TMPDIR/state-slug"
  mkdir -p "$project"
  (
    cd "$project"
    COLLAB_STATE_HOME="$state" "$REGISTRY" init --agent-id codex "Slug Case" >/dev/null
  )
  python3 - "$project" "$state" <<'PY'
import json
import re
import sys
from pathlib import Path

project = Path(sys.argv[1])
state = Path(sys.argv[2])
identity = json.loads((project / '.collab.json').read_text())
assert identity['projectId'] == 'noobsociety-com'
assert re.match(r'^[a-z0-9][a-z0-9-]{7,127}$', identity['projectId'])
assert (state / identity['projectId'] / 'registry.json').exists()
PY
}

case_deterministic_collision_suffixing() {
  local state="$TMPDIR/state-collision"
  local project_a="$TMPDIR/a/noobsociety.com"
  local project_b="$TMPDIR/b/noobsociety.com"
  mkdir -p "$project_a" "$project_b"
  (
    cd "$project_a"
    COLLAB_STATE_HOME="$state" "$REGISTRY" init --agent-id codex "First" >/dev/null
  )
  (
    cd "$project_b"
    COLLAB_STATE_HOME="$state" "$REGISTRY" init --agent-id codex "Second" >/dev/null
  )
  python3 - "$ROOT" "$project_b" "$state" <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from commands.collab.engine.registry_state import project_id_for_project

project_b = Path(sys.argv[2])
state = Path(sys.argv[3])
identity = json.loads((project_b / '.collab.json').read_text())
expected = project_id_for_project(project_b, 'noobsociety.com', state, identity['projectId'])
assert identity['projectId'] == expected
assert identity['projectId'].startswith('noobsociety-com-')
assert identity['projectId'] != 'noobsociety-com'
assert (state / 'noobsociety-com' / 'registry.json').exists()
assert (state / identity['projectId'] / 'registry.json').exists()
PY
}

case_atomic_all_surface_rewrite_and_idempotent_rerun() {
  local project="$TMPDIR/legacy-project"
  local state="$TMPDIR/state-migrate"
  local old_id="0123456789abcdef0123456789abcdef"
  make_legacy_project "$project" "$state" "$old_id" "legacy-project"
  local output
  output="$("$MIGRATE" --project-root "$project" --state-home "$state")"
  assert_contains "$output" '"status": "migrated"' "migration status"
  python3 - "$project" "$state" "$old_id" <<'PY'
import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
state = Path(sys.argv[2])
old_id = sys.argv[3]
identity = json.loads((project / '.collab.json').read_text())
new_id = identity['projectId']
assert new_id == 'legacy-project'
assert not (state / old_id).exists()
registry_path = state / new_id / 'registry.json'
data = json.loads(registry_path.read_text())
assert data['project'] == {'projectId': new_id, 'label': 'legacy-project'}
record = data['projectIdMigrations'][-1]
assert record['oldProjectId'] == old_id
assert record['newProjectId'] == new_id
assert record['sourceMarker'] == str((project / '.collab.json').resolve())
assert record['sourceMarkers'] == [str((project / '.collab.json').resolve())]
assert record['registryPath'] == str(registry_path.resolve())
assert record['timestamp'].endswith('Z')
assert (state / new_id / 'label').read_text() == 'legacy-project\n'
PY
  output="$("$MIGRATE" --project-root "$project" --state-home "$state")"
  assert_contains "$output" '"status": "already-complete"' "idempotent rerun"
}

case_fresh_init_after_move_disambiguates_by_resolved_path() {
  local state="$TMPDIR/state-after-move"
  local project_a="$TMPDIR/original/fresh-move"
  local project_b="$TMPDIR/moved/fresh-move"
  mkdir -p "$project_a" "$project_b"
  (
    cd "$project_a"
    COLLAB_STATE_HOME="$state" "$REGISTRY" init --agent-id codex "Original" >/dev/null
  )
  (
    cd "$project_b"
    COLLAB_STATE_HOME="$state" "$REGISTRY" init --agent-id codex "Moved" >/dev/null
  )
  python3 - "$ROOT" "$project_b" "$state" <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from commands.collab.engine.registry_state import project_id_for_project

project_b = Path(sys.argv[2])
state = Path(sys.argv[3])
identity = json.loads((project_b / '.collab.json').read_text())
expected = project_id_for_project(project_b, 'fresh-move', state, identity['projectId'])
assert identity['projectId'] == expected
assert identity['projectId'].startswith('fresh-move-')
assert identity['projectId'] != 'fresh-move'
assert (state / 'fresh-move' / 'registry.json').exists()
assert (state / identity['projectId'] / 'registry.json').exists()
PY
}

case_multi_repo_marker_rewrite() {
  local project="$TMPDIR/multi-primary"
  local extra="$TMPDIR/multi-extra"
  local state="$TMPDIR/state-multi"
  local old_id="55555555555555555555555555555555"
  make_legacy_project "$project" "$state" "$old_id" "multi-repo"
  mkdir -p "$extra"
  cp "$project/.collab.json" "$extra/.collab.json"
  local output
  output="$("$MIGRATE" --project-root "$project" --extra-project-root "$extra" --state-home "$state")"
  assert_contains "$output" '"status": "migrated"' "multi-repo migration status"
  python3 - "$project" "$extra" "$state" "$old_id" <<'PY'
import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
extra = Path(sys.argv[2])
state = Path(sys.argv[3])
old_id = sys.argv[4]
primary_identity = json.loads((project / '.collab.json').read_text())
extra_identity = json.loads((extra / '.collab.json').read_text())
new_id = 'multi-repo'
assert primary_identity['projectId'] == new_id
assert extra_identity['projectId'] == new_id
assert primary_identity['state']['previousProjectId'] == old_id
assert extra_identity['state']['previousProjectId'] == old_id
assert not (state / old_id).exists()
registry_path = state / new_id / 'registry.json'
data = json.loads(registry_path.read_text())
record = data['projectIdMigrations'][-1]
assert record['oldProjectId'] == old_id
assert record['newProjectId'] == new_id
assert record['sourceMarkers'] == [
    str((project / '.collab.json').resolve()),
    str((extra / '.collab.json').resolve()),
]
assert (state / new_id / 'label').read_text() == 'multi-repo\n'
PY
}

case_held_flock_abort() {
  local project="$TMPDIR/held-lock"
  local state="$TMPDIR/state-held-lock"
  local old_id="11111111111111111111111111111111"
  make_legacy_project "$project" "$state" "$old_id" "held-lock"
  local lock="$state/$old_id/registry.json.lock"
  local ready="$TMPDIR/held-lock-ready"
  python3 - "$lock" "$ready" <<'PY' &
import fcntl
import sys
import time
from pathlib import Path

lock = Path(sys.argv[1])
ready = Path(sys.argv[2])
with lock.open('a+') as handle:
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    ready.write_text('ready')
    time.sleep(10)
PY
  local locker_pid=$!
  for _ in {1..100}; do
    [[ -e "$ready" ]] && break
    sleep 0.05
  done
  if [[ ! -e "$ready" ]]; then
    kill "$locker_pid" 2>/dev/null || true
    wait "$locker_pid" 2>/dev/null || true
    printf 'FAIL: lock holder did not become ready\n' >&2
    exit 1
  fi
  set +e
  local output
  output="$("$MIGRATE" --project-root "$project" --state-home "$state" 2>&1)"
  local rc=$?
  set -e
  kill "$locker_pid" 2>/dev/null || true
  wait "$locker_pid" 2>/dev/null || true
  if [[ "$rc" -eq 0 ]]; then
    printf 'FAIL: held flock migration unexpectedly succeeded\n' >&2
    exit 1
  fi
  assert_contains "$output" "registry lock held:" "held flock abort"
  [[ -d "$state/$old_id" ]]
  [[ ! -e "$state/held-lock" ]]
  [[ "$(read_marker_id "$project")" == "$old_id" ]]
}

case_stale_zero_byte_lock_tolerance() {
  local project="$TMPDIR/stale-lock"
  local state="$TMPDIR/state-stale-lock"
  local old_id="22222222222222222222222222222222"
  make_legacy_project "$project" "$state" "$old_id" "stale-lock"
  : >"$state/$old_id/registry.json.lock"
  touch -t 200001010000 "$state/$old_id/registry.json.lock"
  local output
  output="$("$MIGRATE" --project-root "$project" --state-home "$state")"
  assert_contains "$output" '"status": "migrated"' "stale lock tolerance"
  [[ -e "$state/stale-lock/registry.json.lock" ]]
}

case_partial_state_fail_loud() {
  local project="$TMPDIR/partial-state"
  local state="$TMPDIR/state-partial"
  local old_id="33333333333333333333333333333333"
  mkdir -p "$project" "$state/$old_id"
  python3 - "$project" "$old_id" <<'PY'
import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
old_id = sys.argv[2]
(project / '.collab.json').write_text(json.dumps({
    'projectId': old_id,
    'label': 'partial-state',
}, indent=2) + '\n')
PY
  set +e
  local output
  output="$("$MIGRATE" --project-root "$project" --state-home "$state" 2>&1)"
  local rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    printf 'FAIL: partial state migration unexpectedly succeeded\n' >&2
    exit 1
  fi
  assert_contains "$output" "partial migration state: registry missing" "partial state fail loud"

  local rollback_project="$TMPDIR/rollback-state"
  local rollback_state="$TMPDIR/state-rollback"
  local rollback_old_id="44444444444444444444444444444444"
  make_legacy_project "$rollback_project" "$rollback_state" "$rollback_old_id" "rollback-state"
  python3 - "$rollback_state" "$rollback_old_id" <<'PY'
import json
import sys
from pathlib import Path

state = Path(sys.argv[1])
old_id = sys.argv[2]
registry = state / old_id / 'registry.json'
data = json.loads(registry.read_text())
data['projectIdMigrations'] = {}
registry.write_text(json.dumps(data, indent=2) + '\n')
PY
  set +e
  output="$("$MIGRATE" --project-root "$rollback_project" --state-home "$rollback_state" 2>&1)"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    printf 'FAIL: rollback state migration unexpectedly succeeded\n' >&2
    exit 1
  fi
  assert_contains "$output" "registry projectIdMigrations must be a list" "post-rename rollback fail loud"
  [[ -d "$rollback_state/$rollback_old_id" ]]
  [[ ! -e "$rollback_state/rollback-state" ]]
  [[ "$(read_marker_id "$rollback_project")" == "$rollback_old_id" ]]
}

case_explicit_orphan_deletion() {
  local state="$TMPDIR/state-orphan"
  mkdir -p "$state/empty-orphan"
  local output
  output="$("$MIGRATE" --state-home "$state" --delete-empty-orphan empty-orphan)"
  assert_contains "$output" '"status": "deleted-empty-orphan"' "explicit orphan deletion"
  [[ ! -e "$state/empty-orphan" ]]

  mkdir -p "$state/registry-orphan/records" "$state/registry-orphan/revisions"
  python3 - "$state" <<'PY'
import json
import sys
from pathlib import Path

state = Path(sys.argv[1])
orphan = state / 'registry-orphan'
(orphan / 'label').write_text('registry-orphan\n')
(orphan / 'registry.json.lock').write_text('')
(orphan / 'registry.json').write_text(json.dumps({
    'activeCollabId': None,
    'collabs': [],
    'project': {'projectId': 'registry-orphan', 'label': 'registry-orphan'},
}, indent=2) + '\n')
PY
  output="$("$MIGRATE" --state-home "$state" --delete-empty-orphan registry-orphan)"
  assert_contains "$output" '"status": "deleted-empty-orphan"' "registry orphan deletion"
  [[ ! -e "$state/registry-orphan" ]]
}

case_slug_format_and_noobsociety_sanitization
case_deterministic_collision_suffixing
case_fresh_init_after_move_disambiguates_by_resolved_path
case_atomic_all_surface_rewrite_and_idempotent_rerun
case_multi_repo_marker_rewrite
case_held_flock_abort
case_stale_zero_byte_lock_tolerance
case_partial_state_fail_loud
case_explicit_orphan_deletion

printf 'OK: state-root naming, guarded migration, marker rewrite, lock handling, idempotency, partial-state rejection, and explicit orphan deletion\n'
