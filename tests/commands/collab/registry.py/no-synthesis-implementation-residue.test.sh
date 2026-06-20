#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

if [ -n "$(git ls-files commands/collab/engine/synthesis.py)" ]; then
  printf 'FAIL: commands/collab/engine/synthesis.py is still tracked\n' >&2
  exit 1
fi

if [ -n "$(ls tests/commands/collab/registry.py/synthesize-*.test.sh 2>/dev/null)" ]; then
  printf 'FAIL: synthesize registry tests are still present\n' >&2
  exit 1
fi

for path in \
  tests/commands/collab/aggregate-transcript.test.sh \
  tests/commands/collab/modules/transcript-render-projection-store.test.sh
do
  if [ -n "$(git ls-files "$path")" ] || [ -e "$path" ]; then
    printf 'FAIL: stale projection test remains: %s\n' "$path" >&2
    exit 1
  fi
done

if git grep -nE 'contribution_store_digest|projection_source_digest|projection_store_records' \
  -- commands/collab/engine '*.py' >/tmp/no-synthesis-residue-grep.out
then
  printf 'FAIL: dead synthesis digest/store symbol remains:\n' >&2
  cat /tmp/no-synthesis-residue-grep.out >&2
  exit 1
fi
rm -f /tmp/no-synthesis-residue-grep.out

python3 - <<'PY'
from commands.collab.engine import registry
from commands.collab.engine import seal_verification
from commands.collab.engine import transcript_render

assert registry
assert seal_verification
for name in (
    'excerpt_source',
    'stance_for_content',
    'is_hidden_metadata_line',
):
    assert hasattr(transcript_render, name), name
assert not hasattr(transcript_render, 'projection_excerpt_source')
assert not hasattr(transcript_render, 'projection_stance_for_content')
assert not hasattr(transcript_render, 'is_projection_hidden_metadata_line')
PY

printf 'OK: synthesis implementation residue is absent and live transcript helpers import cleanly\n'
