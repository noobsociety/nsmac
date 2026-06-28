#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

assert_command_fails_containing() {
  local label="$1"
  local needle="$2"
  shift 2
  local output
  local status

  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e

  if [[ "$status" -eq 0 || "$output" != *"$needle"* ]]; then
    printf 'FAIL: %s\n%s\n' "$label" "$output" >&2
    exit 1
  fi
}

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa "Pending Reviewer Gate" >/dev/null
assert_command_fails_containing \
  "speak-state allowed contribution with pending reviewer" \
  "pending reviewerRole: pa" \
  "$ROOT/commands/collab/engine/registry.py" speak-state "${RUN_DATE}-pending-reviewer-gate" mod

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Stale Speak Render" >/dev/null
printf 'Moderator note.\n' >content.md
assert_command_fails_containing \
  "speak-render accepted stale observed revision" \
  "stale registry revision: observed 0, live 2" \
  "$ROOT/commands/collab/engine/registry.py" speak-render "${RUN_DATE}-stale-speak-render" mod --content-file content.md --observed-revision 0

python3 - "$ROOT/commands/collab/engine/registry.py" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text()
match = re.search(
    r"def\s+render_re_speak\b.*?(?=\ndef\s+|\nclass\s+|\Z)",
    source,
    re.S,
)
if not match:
    raise SystemExit("FAIL: render_re_speak implementation not found")

body = match.group(0)
blocked_tokens = [
    "expectedRole",
    "nextRole",
    "turn lock",
    "turn_lock",
    "speak_state",
    "speak-state",
]
for token in blocked_tokens:
    if token in body:
        raise SystemExit(
            f"FAIL: rewrite-speak-render must stay role-scoped, found turn-gating token: {token}"
        )

required_tokens = [
    "activePhase",
    "Completion",
    "contribution",
]
for token in required_tokens:
    if token not in body:
        raise SystemExit(
            f"FAIL: rewrite-speak-render missing expected contribution-scope guard: {token}"
        )
PY

REWRITE_SPEAK_ROUTE="$ROOT/commands/collab/rewrite-speak/index.md"
if ! grep -Fq 'rewrite-speak-render' "$REWRITE_SPEAK_ROUTE"; then
  printf 'FAIL: rewrite-speak route does not name rewrite-speak-render\n' >&2
  exit 1
fi

if ! grep -Fq 'Do not use speak-state turn gating to decide whether a rewrite is allowed.' "$REWRITE_SPEAK_ROUTE"; then
  printf 'FAIL: rewrite-speak route missing explicit no-turn-gating rule\n' >&2
  exit 1
fi

printf 'OK: speak state/render guard checks remain covered\n'
