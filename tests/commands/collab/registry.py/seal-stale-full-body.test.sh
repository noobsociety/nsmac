#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

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
transcript_path = registry.parent / entry['transcriptPath']
text = transcript_path.read_text()
assert 'Stable excerpt.' in text
transcript_path.write_text(text.replace('Original full body bytes.', 'Changed full body bytes.'))
PY

"$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa >/dev/null

assert_seal_stale "seal-stale-full-body" "full body content changed"

printf 'OK: changed managed full-body bytes invalidate an existing verification seal\n'
