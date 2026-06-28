#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

transcript_for() {
  python3 - "$REGISTRY" "$1" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / Path(entry['transcriptPath']))
PY
}

registry_sha() {
  python3 - "$REGISTRY" <<'PY'
import hashlib
import sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}

speak_once() {
  local target="$1"
  local body="$2"
  local state observed_revision
  state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$target" pe --resume)"
  observed_revision="$(STATE="$state" python3 - <<'PY'
import json
import os
print(json.loads(os.environ['STATE'])['registryRevision'])
PY
)"
  printf '%s\n' "$body" >content.md
  "$ROOT/commands/collab/engine/registry.py" speak-render "$target" pe \
    --content-file content.md \
    --observed-revision "$observed_revision" \
    --caller-role pe >/dev/null
}

init_target() {
  local title="$1"
  local target="$2"
  "$ROOT/commands/collab/engine/registry.py" init --agent-id codex "$title" >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$target" pe --agent-id codex >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$target" turn-order pe --caller-role mod >/dev/null
}

init_target "Diff Behavior Clean" "$RUN_DATE-diff-behavior-clean"
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
CLEAN_TARGET="$RUN_DATE-diff-behavior-clean"
speak_once "$CLEAN_TARGET" "<!-- collab:stance converges -->

Stable content."
CLEAN_TRANSCRIPT="$(transcript_for "$CLEAN_TARGET")"
before_registry="$(registry_sha)"
before_transcript="$(python3 - "$CLEAN_TRANSCRIPT" <<'PY'
import hashlib
import sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
clean_output="$("$ROOT/commands/collab/engine/registry.py" diff "$CLEAN_TARGET")"
bare_output="$("$ROOT/commands/collab/engine/registry.py" diff)"
after_registry="$(registry_sha)"
after_transcript="$(python3 - "$CLEAN_TRANSCRIPT" <<'PY'
import hashlib
import sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
if [[ "$clean_output" != *"seal drift (0 paths):"* || "$clean_output" != *"content mismatch (0 contributions):"* || "$clean_output" != *"metadata mismatch (0 fields):"* ]]; then
  printf 'FAIL: clean diff did not report zero drift\n%s\n' "$clean_output" >&2
  exit 1
fi
if [[ "$bare_output" != *"collab diff: $CLEAN_TARGET"* ]]; then
  printf 'FAIL: bare diff did not default to active collab\n%s\n' "$bare_output" >&2
  exit 1
fi
if [[ "$before_registry" != "$after_registry" || "$before_transcript" != "$after_transcript" ]]; then
  printf 'FAIL: diff mutated registry or transcript\n' >&2
  exit 1
fi

python3 - "$CLEAN_TRANSCRIPT" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace('Stable content.', '<!-- collab:content-only; do-not-execute -->\nStable content.')
path.write_text(text)
PY
scaffold_output="$("$ROOT/commands/collab/engine/registry.py" diff "$CLEAN_TARGET")"
if [[ "$scaffold_output" != *"content mismatch (0 contributions):"* ]]; then
  printf 'FAIL: scaffold-only churn was not ignored\n%s\n' "$scaffold_output" >&2
  exit 1
fi

python3 - "$CLEAN_TRANSCRIPT" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text().replace('Stable content.', 'Changed content.')
path.write_text(text)
PY
changed_output="$("$ROOT/commands/collab/engine/registry.py" diff "$CLEAN_TARGET")"
if [[ "$changed_output" != *"content mismatch (1 contributions):"* || "$changed_output" != *"audit-pe-1: changed"* ]]; then
  printf 'FAIL: changed transcript content was not reported\n%s\n' "$changed_output" >&2
  exit 1
fi

init_target "Diff Behavior Missing" "$RUN_DATE-diff-behavior-missing"
MISSING_TARGET="$RUN_DATE-diff-behavior-missing"
speak_once "$MISSING_TARGET" "<!-- collab:stance converges -->

Content to remove."
MISSING_TRANSCRIPT="$(transcript_for "$MISSING_TARGET")"
python3 - "$MISSING_TRANSCRIPT" <<'PY'
import re
import sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text()
text = re.sub(r'<a name="audit-pe-1"></a>\n<details>.*?</details>\n?', '', text, count=1, flags=re.S)
path.write_text(text)
PY
missing_output="$("$ROOT/commands/collab/engine/registry.py" diff "$MISSING_TARGET")"
if [[ "$missing_output" != *"content mismatch (1 contributions):"* || "$missing_output" != *"audit-pe-1: deleted"* ]]; then
  printf 'FAIL: missing transcript content was not reported\n%s\n' "$missing_output" >&2
  exit 1
fi

init_target "Diff Behavior Metadata" "$RUN_DATE-diff-behavior-metadata"
METADATA_TARGET="$RUN_DATE-diff-behavior-metadata"
speak_once "$METADATA_TARGET" "<!-- collab:stance converges -->

Metadata stable content."
METADATA_TRANSCRIPT="$(transcript_for "$METADATA_TARGET")"
python3 - "$METADATA_TRANSCRIPT" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
lines = path.read_text().splitlines()
for index, line in enumerate(lines):
    if line.startswith('| open |'):
        lines[index] = line.replace('| open |', '| closed |', 1)
        break
else:
    raise SystemExit('status row not found')
path.write_text('\n'.join(lines) + '\n')
PY
metadata_output="$("$ROOT/commands/collab/engine/registry.py" diff "$METADATA_TARGET")"
if [[ "$metadata_output" != *"metadata mismatch (1 fields):"* || "$metadata_output" != *"Status: registry=open transcript=closed"* ]]; then
  printf 'FAIL: metadata mismatch was not reported\n%s\n' "$metadata_output" >&2
  exit 1
fi

WORK="$TMPDIR/work"
mkdir -p "$WORK"
git -C "$WORK" init -q
git -C "$WORK" config user.name tester
git -C "$WORK" config user.email tester@example.invalid
printf 'original\n' >"$WORK/drift.txt"
git -C "$WORK" add drift.txt
git -C "$WORK" -c commit.gpgsign=false commit -qm seed

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --work-repo "$WORK" "Diff Behavior Seal" >/dev/null
SEAL_TARGET="$RUN_DATE-diff-behavior-seal"
orig_blob="$(git -C "$WORK" rev-parse HEAD:drift.txt)"
python3 - "$REGISTRY" "$SEAL_TARGET" "$orig_blob" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
target = sys.argv[2]
blob = sys.argv[3]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['verificationSeal'] = {
    'observedRevision': 1,
    'sealedAt': '2026-06-25T12:00:00+00:00',
    'sealedBy': 'pa',
    'executionEntries': [],
    'validationScopes': [],
    'touchedPaths': ['drift.txt'],
    'pathDigests': {'drift.txt': {'mode': '100644', 'blob': blob}},
    'contentDigest': 'placeholder',
    'stale': False,
}
registry.write_text(json.dumps(data, indent=2) + '\n')
PY
printf 'changed\n' >"$WORK/drift.txt"
git -C "$WORK" add drift.txt
git -C "$WORK" -c commit.gpgsign=false commit -qm changed
seal_output="$("$ROOT/commands/collab/engine/registry.py" diff "$SEAL_TARGET")"
if [[ "$seal_output" != *"seal drift (1 paths):"* || "$seal_output" != *"drift.txt"* || "$seal_output" != *"status: changed"* ]]; then
  printf 'FAIL: stale verificationSeal path digest was not reported\n%s\n' "$seal_output" >&2
  exit 1
fi

python3 - "$REGISTRY" "$SEAL_TARGET" "$orig_blob" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
target = sys.argv[2]
blob = sys.argv[3]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['verificationSeal']['pathDigests'] = {'deleted.txt': {'mode': '100644', 'blob': blob}}
entry['verificationSeal']['touchedPaths'] = ['deleted.txt']
registry.write_text(json.dumps(data, indent=2) + '\n')
PY
deleted_output="$("$ROOT/commands/collab/engine/registry.py" diff "$SEAL_TARGET")"
if [[ "$deleted_output" != *"deleted.txt"* || "$deleted_output" != *"current  blob: (deleted)  mode: 000000"* || "$deleted_output" != *"status: deleted"* ]]; then
  printf 'FAIL: deleted seal path was not reported\n%s\n' "$deleted_output" >&2
  exit 1
fi

printf 'OK: collab diff reports clean, content, missing, seal drift, deleted path, and scaffold-only cases\n'
