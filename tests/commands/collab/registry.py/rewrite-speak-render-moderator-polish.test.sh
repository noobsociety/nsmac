#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-rewrite-moderator-polish"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Rewrite Moderator Polish" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order "mod pe" --caller-role mod >/dev/null

revision="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" mod \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])')"

printf 'initial moderator text\n' >initial.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" mod \
  --content-file initial.md \
  --observed-revision "$revision" \
  --caller-role mod >/dev/null

transcript_path="$(python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / Path(entry['transcriptPath']))
PY
)"

printf '+ speek now\n' >rewrite-polished.md
"$ROOT/commands/collab/engine/registry.py" rewrite-speak-render "$TARGET" mod \
  --content-file rewrite-polished.md \
  --caller-role mod >/dev/null
grep -Fq -- '- Speak now' "$transcript_path"

printf '+ speek later\n' >rewrite-verbatim.md
"$ROOT/commands/collab/engine/registry.py" rewrite-speak-render "$TARGET" mod \
  --content-file rewrite-verbatim.md \
  --caller-role mod \
  --verbatim >/dev/null
grep -Fq -- '+ speek later' "$transcript_path"

python3 - "$ROOT" <<'PY'
import importlib.util
import sys
from pathlib import Path

root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("registry", root / "commands/collab/engine/registry.py")
registry = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(registry)

polished = registry.polish_moderator_content("EFFORT OVERRIDE: matrix")
assert polished == "EFFORT OVERRIDE: matrix", polished
assert polished != "EFFORT OVERRIDE: matrix.", polished
assert not polished.startswith("- "), polished
PY

printf 'OK: rewrite-speak-render applies moderator polish, preserves effort overrides, and honors --verbatim bypass\n'
