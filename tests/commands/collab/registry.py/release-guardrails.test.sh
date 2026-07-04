#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

export COLLAB_STATE_HOME="$TMPDIR/state-home"
RUN_DATE="$(date +%Y-%m-%d)"

make_repo() {
  local repo="$1"
  mkdir -p "$repo"
  git -C "$repo" init >/dev/null
  git -C "$repo" config user.name "Test User"
  git -C "$repo" config user.email "test@example.com"
  printf 'base\n' >"$repo/file.txt"
  git -C "$repo" add file.txt
  git -C "$repo" commit -m "chore: initial" >/dev/null
}

cd "$TMPDIR"

DIRTY_WORK="$TMPDIR/dirty-work"
make_repo "$DIRTY_WORK"
DIRTY_TARGET="$RUN_DATE-release-guard-dirty"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --work-repo "$DIRTY_WORK" "Release Guard Dirty" >/dev/null
printf 'dirty\n' >>"$DIRTY_WORK/file.txt"
set +e
dirty_output="$("$ROOT/commands/collab/engine/registry.py" release "$DIRTY_TARGET" 2>&1)"
dirty_status=$?
set -e
if [[ "$dirty_status" -eq 0 || "$dirty_output" != *"RELEASE-GIT-STATE: work tree must be clean before tag/release"* ]]; then
  printf 'FAIL: dirty work tree was not rejected\n%s\n' "$dirty_output" >&2
  exit 1
fi

EXISTS_WORK="$TMPDIR/exists-work"
make_repo "$EXISTS_WORK"
EXISTS_TARGET="$RUN_DATE-release-guard-existing-tag"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --work-repo "$EXISTS_WORK" "Release Guard Existing Tag" >/dev/null
git -C "$EXISTS_WORK" tag -a collab/existing -m "existing tag"
set +e
exists_output="$("$ROOT/commands/collab/engine/registry.py" tag "$EXISTS_TARGET" --tag collab/existing --confirm 2>&1)"
exists_status=$?
set -e
if [[ "$exists_status" -eq 0 || "$exists_output" != *"RELEASE-TAG: tag already exists: collab/existing"* ]]; then
  printf 'FAIL: existing tag was not rejected\n%s\n' "$exists_output" >&2
  exit 1
fi

PUSH_WORK="$TMPDIR/push-work"
PUSH_REMOTE="$TMPDIR/push-remote.git"
make_repo "$PUSH_WORK"
git init --bare "$PUSH_REMOTE" >/dev/null
git -C "$PUSH_WORK" remote add origin "$PUSH_REMOTE"
PUSH_TARGET="$RUN_DATE-release-guard-push"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --work-repo "$PUSH_WORK" "Release Guard Push" >/dev/null
push_output="$("$ROOT/commands/collab/engine/registry.py" tag "$PUSH_TARGET" --tag collab/pushed --confirm --push)"
if [[ "$push_output" != *"CREATED: tag collab/pushed"* || "$push_output" != *"PUSHED: tag collab/pushed"* ]]; then
  printf 'FAIL: confirmed tag push did not report create+push\n%s\n' "$push_output" >&2
  exit 1
fi
if ! git -C "$PUSH_WORK" rev-parse --verify --quiet "refs/tags/collab/pushed" >/dev/null; then
  printf 'FAIL: confirmed push did not create local tag\n' >&2
  exit 1
fi
if ! git -C "$PUSH_REMOTE" rev-parse --verify --quiet "refs/tags/collab/pushed" >/dev/null; then
  printf 'FAIL: confirmed push did not push tag to origin\n' >&2
  exit 1
fi

ROLE_WORK="$TMPDIR/role-work"
make_repo "$ROLE_WORK"
ROLE_TARGET="$RUN_DATE-release-guard-role-agnostic"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --work-repo "$ROLE_WORK" "Release Guard Role Agnostic" >/dev/null
role_output="$("$ROOT/commands/collab/engine/registry.py" release "$ROLE_TARGET" --caller-role not-a-participant)"
if [[ "$role_output" != *"TARGET: $ROLE_TARGET"* || "$role_output" != *"MODE: dry-run"* ]]; then
  printf 'FAIL: role-agnostic release rejected or misrendered caller role\n%s\n' "$role_output" >&2
  exit 1
fi

printf 'OK: release guardrails reject dirty/duplicate states, push tags, and remain role-agnostic\n'
