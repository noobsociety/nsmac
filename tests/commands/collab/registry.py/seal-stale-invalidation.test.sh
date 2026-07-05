#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Seal Stale Transcript Repair" "seal-stale-transcript-repair"
TARGET="$RUN_DATE-seal-stale-transcript-repair"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET"
"$ROOT/commands/collab/engine/registry.py" transcript-repair "$TARGET" --touch-execution-evidence --caller-role mod >/dev/null
assert_seal_stale "seal-stale-transcript-repair" "transcript repair touched execution evidence"

init_reviewer_target "Seal Stale Execution Rewrite" "seal-stale-execution-rewrite"
TARGET="$RUN_DATE-seal-stale-execution-rewrite"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET"
"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-15T22:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null
assert_seal_stale "seal-stale-execution-rewrite" "execution changed for pe"

init_reviewer_target "Seal Stale Out Of Scope Patch" "seal-stale-out-of-scope-patch"
TARGET="$RUN_DATE-seal-stale-out-of-scope-patch"
seed_handoff_scope "seal-stale-out-of-scope-patch"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET"
"$ROOT/commands/collab/engine/registry.py" out-of-scope-patch "$TARGET" pe \
  --path tests/run.sh \
  --caller-role pe >/dev/null
assert_seal_stale \
  "seal-stale-out-of-scope-patch" \
  "out-of-scope patch outside declared writeScope: tests/run.sh"

init_reviewer_target "Seal Stale Full Body" "seal-stale-full-body"
TARGET="$RUN_DATE-seal-stale-full-body"
REGISTRY="$(registry_path)"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Discussion --force --caller-role mod >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
revision="$(read_json_field registryRevision <<<"$state")"

printf 'Stable excerpt.\n' >excerpt.md
printf 'Original full body bytes.\n' >full-body.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe \
  --content-file excerpt.md \
  --full-body-file full-body.md \
  --observed-revision "$revision" \
  --caller-role pe >/dev/null

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET"

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'seal-stale-full-body')
transcript_path = registry.parent / Path(entry['transcriptPath'])
text = transcript_path.read_text()
assert 'Stable excerpt.' in text
transcript_path.write_text(text.replace('Original full body bytes.', 'Changed full body bytes.'))
PY

"$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa >/dev/null
assert_seal_stale "seal-stale-full-body" "full body content changed"

printf 'OK: seal stale invalidation scenarios remain covered\n'
