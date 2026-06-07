#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-registry-revision-events"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Registry Revision Events" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
STATE_ROOT="$(dirname "$REGISTRY")"

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
assert data['eventIndex'] == 1, data
assert 'registryRevision' not in data, data
event_dir = Path(sys.argv[1]).parent / 'revisions' / data['activeCollabId']
assert (event_dir / '000000000001.json').exists(), sorted(event_dir.iterdir())
assert not (event_dir / 'legacy-baseline.json').exists(), sorted(event_dir.iterdir())
PY

log="$("$ROOT/commands/collab/engine/registry.py" log "$TARGET")"
if [[ "$log" != *"#1  "*"registry-write"* ]]; then
  printf 'FAIL: log did not read the append-only event\n%s\n' "$log" >&2
  exit 1
fi

rm -rf "$STATE_ROOT/revisions"
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data['registryRevision'] = 1552
path.write_text(json.dumps(data, indent=2) + '\n')
PY

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" description "Updated description" --caller-role mod >/dev/null

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
assert data['eventIndex'] == 2, data
assert 'registryRevision' not in data, data
event_dir = Path(sys.argv[1]).parent / 'revisions' / sys.argv[2]
assert (event_dir / 'legacy-baseline.json').exists(), sorted(event_dir.iterdir())
assert (event_dir / '000000000002.json').exists(), sorted(event_dir.iterdir())
PY

log="$("$ROOT/commands/collab/engine/registry.py" log "$TARGET")"
if [[ "$log" != *"#2  "*"registry-write"* || "$log" != *"#legacy  -  legacy-baseline"* ]]; then
  printf 'FAIL: log did not include new and legacy events\n%s\n' "$log" >&2
  exit 1
fi

printf 'OK: registry revision events are append-only and retire top-level registryRevision\n'
