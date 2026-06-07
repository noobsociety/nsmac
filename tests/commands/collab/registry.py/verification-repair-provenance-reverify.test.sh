#!/usr/bin/env bash
set -euo pipefail

# repair-execution-provenance can repoint a completed execution to a different
# commit (and rewrite pairedExecutionSignature). It must NOT let a success seal
# certify content that was never participant-verified. The per-role execution
# signature pins what the verification certified; repointing to a commit with
# different content for the touched paths invalidates that completed verification
# on the next read, so the seal blocks and the role must re-verify.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
export COLLAB_STATE_HOME="$TMPDIR/state-home"

WORKREPO="$TMPDIR/work"
mkdir -p "$WORKREPO"
git -C "$WORKREPO" init -q
git -C "$WORKREPO" config user.email tester@example.com
git -C "$WORKREPO" config user.name tester
printf 'v1\n' >"$WORKREPO/foo.txt"
git -C "$WORKREPO" add foo.txt
git -C "$WORKREPO" -c commit.gpgsign=false commit -qm v1
V1_DATE="$(git -C "$WORKREPO" show -s --format=%cI HEAD)"

cd "$WORKREPO"
reg() { "$ROOT/commands/collab/engine/registry.py" "$@"; }

reg init --agent-id codex --reviewer pa "Repair Provenance Reverify" >/dev/null
TARGET="$RUN_DATE-repair-provenance-reverify"
reg join-participants "$TARGET" pe --agent-id gpt >/dev/null
reg join-participants "$TARGET" pa --agent-id opus >/dev/null
reg set "$TARGET" turn-order pe --caller-role mod >/dev/null
reg set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
REGISTRY="$(reg registry-path)"

python3 - "$TARGET" "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
target, registry = sys.argv[1:3]
data = json.loads(Path(registry).read_text())
entry = next(i for i in data['collabs'] if i['id'] == target)
entry['handoff'] = {'roles': {'pe': {'writeScope': ['foo.txt'], 'validationCommands': [['./check.sh']]}}}
Path(registry).write_text(json.dumps(data, indent=2) + '\n')
PY

reg execution "$TARGET" pe completed "$V1_DATE" \
  --assigned-role pe --validation-result passed --validation-scope scoped \
  --touched-path foo.txt --caller-role pe >/dev/null

AUDIT="$TMPDIR/a"; printf 'audit\n' >"$AUDIT"
REM="$TMPDIR/r"; printf 'remediation\n' >"$REM"
FIN="$TMPDIR/f"; printf 'final\n' >"$FIN"
state="$(reg participant-verify-state "$TARGET" pe)"
reg participant-verify-render "$TARGET" pe --observed-revision "$(read_json_field registryRevision <<<"$state")" \
  --audit-file "$AUDIT" --remediation-file "$REM" --final-audit-file "$FIN" \
  --status completed --touched-path foo.txt --caller-role pe >/dev/null

state="$(reg seal-state "$TARGET" pa)"
if [[ "$(read_json_field readyToSeal <<<"$state")" != "True" ]]; then
  printf 'FAIL: not sealable after a clean verification\n%s\n' "$state" >&2
  exit 1
fi

# Repoint to a commit whose foo.txt content differs from what pe verified.
printf 'v2-different-content\n' >"$WORKREPO/foo.txt"
git -C "$WORKREPO" add foo.txt
git -C "$WORKREPO" -c commit.gpgsign=false commit -qm v2
V2="$(git -C "$WORKREPO" rev-parse HEAD)"
reg repair-execution-provenance "$TARGET" pe --commit "$V2" --caller-role pe >/dev/null

# The prior verification certified v1's content; the repoint to v2 must invalidate
# it. The seal must no longer be ready, and pe must be flagged for re-verification.
state="$(reg seal-state "$TARGET" pa)"
if [[ "$(read_json_field readyToSeal <<<"$state")" == "True" ]]; then
  printf 'FAIL: success seal still ready after repointing provenance to different content\n%s\n' "$state" >&2
  exit 1
fi
if [[ "$(read_json_field nextParticipantVerificationRole <<<"$state")" != "pe" ]]; then
  printf 'FAIL: pe not flagged for re-verification after the repoint\n%s\n' "$state" >&2
  exit 1
fi

printf 'OK: repointing execution provenance to different content invalidates the prior verification; re-verify required before seal\n'
