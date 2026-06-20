#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
REGISTRY="$ROOT/commands/collab/engine/registry.py"
ROUTE="$ROOT/commands/collab/rewrite-speak/index.md"

python3 - "$REGISTRY" <<'PY'
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

if ! grep -Fq 'rewrite-speak-render' "$ROUTE"; then
  printf 'FAIL: rewrite-speak route does not name rewrite-speak-render\n' >&2
  exit 1
fi

if ! grep -Fq 'Do not use speak-state turn gating to decide whether a rewrite is allowed.' "$ROUTE"; then
  printf 'FAIL: rewrite-speak route missing explicit no-turn-gating rule\n' >&2
  exit 1
fi

printf 'OK: rewrite-speak remains contribution-scoped instead of turn-gated\n'
