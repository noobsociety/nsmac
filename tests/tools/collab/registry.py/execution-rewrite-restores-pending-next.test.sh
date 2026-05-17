#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export CURSOR_COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

run_case() {
  local title="$1"
  local slug="$2"
  local participant_verification="$3"
  local target="$RUN_DATE-$slug"
  local init_args=(--agent-id codex --reviewer pa)

  if [[ "$participant_verification" == "false" ]]; then
    init_args+=(--no-participant-verification)
  fi
  init_args+=("$title")

  "$ROOT/tools/collab/registry.py" init "${init_args[@]}" >/dev/null
  "$ROOT/tools/collab/registry.py" join-participants "$target" tw --agent-id claude-sonnet-4-6 >/dev/null
  "$ROOT/tools/collab/registry.py" join-participants "$target" pe --agent-id codex >/dev/null
  "$ROOT/tools/collab/registry.py" join-participants "$target" pa --agent-id opus >/dev/null
  "$ROOT/tools/collab/registry.py" set "$target" turn-order "tw pe" --caller-role mod >/dev/null
  "$ROOT/tools/collab/registry.py" set "$target" active-phase Completion --force --caller-role mod >/dev/null

  "$ROOT/tools/collab/registry.py" execution "$target" tw completed "2026-05-17T12:00:00+02:00" \
    --assigned-role tw \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path tools/collab/registry.py \
    --caller-role tw >/dev/null

  completed_output="$("$ROOT/tools/collab/registry.py" execution "$target" pe completed "2026-05-17T12:05:00+02:00" \
    --assigned-role tw \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path tools/collab/registry.py \
    --caller-role pe 2>&1)"

  if [[ "$participant_verification" == "true" ]]; then
    if [[ "$completed_output" != *"NEXT: Run /collab participant verify"* ]]; then
      printf 'FAIL: setup did not reach participant verification for %s\n%s\n' "$slug" "$completed_output" >&2
      exit 1
    fi
  elif [[ "$completed_output" != *"NEXT: Run /collab seal verification"* ]]; then
    printf 'FAIL: setup did not reach seal verification for %s\n%s\n' "$slug" "$completed_output" >&2
    exit 1
  fi

  output="$("$ROOT/tools/collab/registry.py" execution "$target" tw in_progress "2026-05-17T12:10:00+02:00" \
    --assigned-role tw \
    --assigned-role pe \
    --caller-role tw 2>&1)"

  if [[ "$output" != *"NEXT: Run /collab run plan for role tw."* ]]; then
    printf 'FAIL: execution rewrite NEXT did not restore the re-pending role for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi
  if [[ "$output" == *"NEXT: Run /collab seal verification"* ]]; then
    printf 'FAIL: execution rewrite NEXT kept a stale seal advisory for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi
  if [[ "$output" == *"NEXT: Run /collab participant verify"* ]]; then
    printf 'FAIL: execution rewrite NEXT kept a stale participant verification advisory for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi
}

run_case "Execution Rewrite Restores Pending Next" "execution-rewrite-restores-pending-next" false
run_case "Execution Rewrite Restores Pending Next Participant Verify" "execution-rewrite-restores-pending-next-participant-verify" true

printf 'OK: execution rewrites restore pending execution NEXT before verification advisories\n'
