#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

observed_revision() {
  "$ROOT/commands/collab/engine/registry.py" speak-state "$1" "$2" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])'
}

init_target() {
  local title="$1"
  "$ROOT/commands/collab/engine/registry.py" init --agent-id codex "$title" >/dev/null
  printf '%s-%s\n' "$RUN_DATE" "$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
}

assert_rewrite_output_order() {
  local output_file="$1"
  local target="$2"
  local expected_notice="$3"

  python3 - "$output_file" "$target" "$expected_notice" <<'PY'
import sys
from pathlib import Path

path, target, expected_notice = sys.argv[1:4]
lines = Path(path).read_text().splitlines()

def first(prefix: str) -> int:
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return index
    raise AssertionError(f"missing {prefix!r} in output: {lines!r}")

next_index = first("NEXT:")
effort_index = first("EFFORT:")
try:
    id_index = lines.index(target)
except ValueError as exc:
    raise AssertionError(f"missing rewritten entry id {target!r} in output: {lines!r}") from exc

if not next_index < effort_index < id_index:
    raise AssertionError(f"wrong advisory/id order: {lines!r}")

notice_indices = [index for index, line in enumerate(lines) if line.startswith("REVIEWER-NOTICE:")]
if expected_notice == "yes":
    if not notice_indices:
        raise AssertionError(f"missing reviewer notice: {lines!r}")
    if not notice_indices[0] < next_index:
        raise AssertionError(f"reviewer notice did not precede advisories: {lines!r}")
else:
    if notice_indices:
        raise AssertionError(f"unexpected reviewer notice: {lines!r}")
PY
}

PLAIN_TARGET="$(init_target "Rewrite Speak Render Advisories")"
"$ROOT/commands/collab/engine/registry.py" join-participants "$PLAIN_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$PLAIN_TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$PLAIN_TARGET" active-phase Discussion --force --caller-role mod >/dev/null
printf 'Initial pe contribution.\n' >plain-initial.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$PLAIN_TARGET" pe \
  --content-file plain-initial.md \
  --observed-revision "$(observed_revision "$PLAIN_TARGET" pe)" \
  --timestamp "2026-01-01 00:00:00" \
  --caller-role pe >/dev/null
printf 'Rewritten pe contribution.\n' >plain-rewrite.md
"$ROOT/commands/collab/engine/registry.py" rewrite-speak-render "$PLAIN_TARGET" pe \
  --content-file plain-rewrite.md \
  --timestamp "2026-01-01 00:01:00" \
  --caller-role pe >plain-rewrite-output.txt
assert_rewrite_output_order plain-rewrite-output.txt "$PLAIN_TARGET" no

NOTICE_TARGET="$(init_target "Rewrite Speak Render Reviewer Notice")"
"$ROOT/commands/collab/engine/registry.py" join-participants "$NOTICE_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$NOTICE_TARGET" pa --agent-id claude >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$NOTICE_TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$NOTICE_TARGET" reviewer pa --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$NOTICE_TARGET" active-phase Discussion --force --caller-role mod >/dev/null
printf 'Initial pe contribution before reviewer.\n' >notice-pe-initial.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$NOTICE_TARGET" pe \
  --content-file notice-pe-initial.md \
  --observed-revision "$(observed_revision "$NOTICE_TARGET" pe)" \
  --timestamp "2026-01-01 00:00:00" \
  --caller-role pe >/dev/null
printf 'Reviewer contribution after pe.\n' >notice-pa.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$NOTICE_TARGET" pa \
  --content-file notice-pa.md \
  --observed-revision "$(observed_revision "$NOTICE_TARGET" pa)" \
  --timestamp "2026-01-01 00:01:00" \
  --caller-role pa >/dev/null
printf 'Rewritten pe contribution after reviewer.\n' >notice-pe-rewrite.md
"$ROOT/commands/collab/engine/registry.py" rewrite-speak-render "$NOTICE_TARGET" pe \
  --content-file notice-pe-rewrite.md \
  --timestamp "2026-01-01 00:02:00" \
  --caller-role pe >notice-rewrite-output.txt
assert_rewrite_output_order notice-rewrite-output.txt "$NOTICE_TARGET" yes

printf 'OK: rewrite-speak-render emits reviewer notice, advisories, and entry id in order\n'
