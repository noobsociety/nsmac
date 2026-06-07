#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
STAGED_PATH="tests/commands/collab/registry.py/staged-touch-fixture.txt"
UNSTAGED_PATH="tests/commands/collab/registry.py/uncommitted-touch-fixture.txt"
DIRTY_STAGED_PATH="tests/commands/collab/registry.py/dirty-staged-touch-fixture.txt"
COMMITTED_DELETION_PATH="tools/narrative/state.py"
trap 'rm -rf "$TMPDIR"; rm -f "$ROOT/$STAGED_PATH" "$ROOT/$UNSTAGED_PATH" "$ROOT/$DIRTY_STAGED_PATH"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

source "$ROOT/tests/commands/collab/registry.py/verification-test-lib.sh"

complete_execution_with_path() {
  local target="$1"
  local path="$2"
  # Execution provenance capture rejects a commit dated after the execution
  # timestamp (a commit that did not exist at execution time is not provenance).
  # Most fixtures predate this default, but a committed-deletion fixture is only
  # provenance as of its deleting commit, so callers pass that commit's date.
  local exec_date="${3:-2026-05-15T21:00:00+02:00}"
  "$ROOT/commands/collab/engine/registry.py" execution "$target" pe completed "$exec_date" \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path "$path" \
    --caller-role pe >/dev/null
}

init_completion_target() {
  local title="$1"
  local slug="$2"
  init_reviewer_target "$title" "$slug"
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" active-phase Completion --force --caller-role mod >/dev/null
}

seal_without_execution() {
  local target="$1"
  shift || true
  local state revision
  seed_paired_verification_round "$target"
  state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$target" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  "$ROOT/commands/collab/engine/registry.py" seal-render "$target" pa --observed-revision "$revision" --caller-role pa "$@"
}

init_completion_target "Seal Render Committed Git State" "seal-render-committed-git-state"
COMMITTED_TARGET="$RUN_DATE-seal-render-committed-git-state"
complete_execution_with_path "$COMMITTED_TARGET" "platform/tooling/audit.sh"
seal_without_execution "$COMMITTED_TARGET" >/dev/null

if [[ -e "$ROOT/$COMMITTED_DELETION_PATH" ]]; then
  printf 'FAIL: committed deletion fixture unexpectedly exists: %s\n' "$COMMITTED_DELETION_PATH" >&2
  exit 1
fi
if ! git -C "$ROOT" log --diff-filter=D --format=%H -- "$COMMITTED_DELETION_PATH" | grep -q .; then
  printf 'FAIL: committed deletion fixture lacks a deleting commit: %s\n' "$COMMITTED_DELETION_PATH" >&2
  exit 1
fi
init_completion_target "Seal Render Committed Deletion Git State" "seal-render-committed-deletion-git-state"
COMMITTED_DELETION_TARGET="$RUN_DATE-seal-render-committed-deletion-git-state"
# The deletion is provenance only as of its deleting commit; derive that commit's
# date so capture stays valid regardless of when history was last rewritten.
COMMITTED_DELETION_DATE="$(git -C "$ROOT" log -1 --format=%cI -- "$COMMITTED_DELETION_PATH")"
complete_execution_with_path "$COMMITTED_DELETION_TARGET" "$COMMITTED_DELETION_PATH" "$COMMITTED_DELETION_DATE"
seal_without_execution "$COMMITTED_DELETION_TARGET" >/dev/null

init_completion_target "Seal Render Staged Git State" "seal-render-staged-git-state"
STAGED_TARGET="$RUN_DATE-seal-render-staged-git-state"
mkdir -p "$ROOT/$(dirname "$STAGED_PATH")"
printf 'staged fixture\n' >"$ROOT/$STAGED_PATH"
complete_execution_with_path "$STAGED_TARGET" "$STAGED_PATH"
STAGED_INDEX="$TMPDIR/staged.index"
GIT_INDEX_FILE="$STAGED_INDEX" git -C "$ROOT" read-tree HEAD
blob="$(printf 'staged fixture\n' | git -C "$ROOT" hash-object -w --stdin)"
GIT_INDEX_FILE="$STAGED_INDEX" git -C "$ROOT" update-index --add --cacheinfo 100644 "$blob" "$STAGED_PATH"
set +e
staged_output="$(GIT_INDEX_FILE="$STAGED_INDEX" seal_without_execution "$STAGED_TARGET" 2>&1)"
staged_status=$?
set -e
if [[ "$staged_status" -eq 0 || "$staged_output" != *"SEAL-GIT-STATE: implementation not in git; unstaged or uncommitted touchedPath(s) in "*"[\"$STAGED_PATH\"]"* ]]; then
  printf 'FAIL: seal-render did not reject a staged touchedPath\n%s\n' "$staged_output" >&2
  exit 1
fi

init_completion_target "Seal Render Dirty Staged Git State" "seal-render-dirty-staged-git-state"
DIRTY_STAGED_TARGET="$RUN_DATE-seal-render-dirty-staged-git-state"
mkdir -p "$ROOT/$(dirname "$DIRTY_STAGED_PATH")"
printf 'dirty worktree fixture\n' >"$ROOT/$DIRTY_STAGED_PATH"
complete_execution_with_path "$DIRTY_STAGED_TARGET" "$DIRTY_STAGED_PATH"
DIRTY_STAGED_INDEX="$TMPDIR/dirty-staged.index"
GIT_INDEX_FILE="$DIRTY_STAGED_INDEX" git -C "$ROOT" read-tree HEAD
dirty_blob="$(printf 'staged fixture\n' | git -C "$ROOT" hash-object -w --stdin)"
GIT_INDEX_FILE="$DIRTY_STAGED_INDEX" git -C "$ROOT" update-index --add --cacheinfo 100644 "$dirty_blob" "$DIRTY_STAGED_PATH"
set +e
dirty_output="$(GIT_INDEX_FILE="$DIRTY_STAGED_INDEX" seal_without_execution "$DIRTY_STAGED_TARGET" 2>&1)"
dirty_status=$?
set -e
if [[ "$dirty_status" -eq 0 || "$dirty_output" != *"SEAL-GIT-STATE: implementation not in git; unstaged or uncommitted touchedPath(s) in "*"[\"$DIRTY_STAGED_PATH\"]"* ]]; then
  printf 'FAIL: seal-render did not reject a touchedPath with unstaged changes after staging\n%s\n' "$dirty_output" >&2
  exit 1
fi

init_completion_target "Seal Render Unstaged Git State" "seal-render-unstaged-git-state"
UNSTAGED_TARGET="$RUN_DATE-seal-render-unstaged-git-state"
mkdir -p "$ROOT/$(dirname "$UNSTAGED_PATH")"
printf 'unstaged fixture\n' >"$ROOT/$UNSTAGED_PATH"
complete_execution_with_path "$UNSTAGED_TARGET" "$UNSTAGED_PATH"
set +e
output="$(seal_without_execution "$UNSTAGED_TARGET" 2>&1)"
status=$?
set -e
if [[ "$status" -eq 0 || "$output" != *"SEAL-GIT-STATE: implementation not in git; unstaged or uncommitted touchedPath(s) in "*"[\"$UNSTAGED_PATH\"]"* ]]; then
  printf 'FAIL: seal-render did not reject a working-tree-only touchedPath\n%s\n' "$output" >&2
  exit 1
fi

# Work-repo resolution: a collab that declares `workRepo` is gated against THAT
# git tree, not the framework checkout — the cross-repo seal path.
WORK_REPO="$TMPDIR/work-repo"
mkdir -p "$WORK_REPO"
git -C "$WORK_REPO" init -q
git -C "$WORK_REPO" config user.email tester@example.com
git -C "$WORK_REPO" config user.name tester
printf 'projected config\n' >"$WORK_REPO/projected-file"
git -C "$WORK_REPO" add -A
git -C "$WORK_REPO" -c commit.gpgsign=false commit -qm 'seed work repo'

init_completion_target "Seal Render Work Repo Committed" "seal-render-work-repo-committed"
WORK_REPO_TARGET="$RUN_DATE-seal-render-work-repo-committed"
"$ROOT/commands/collab/engine/registry.py" set "$WORK_REPO_TARGET" work-repo "$WORK_REPO" >/dev/null
complete_execution_with_path "$WORK_REPO_TARGET" "projected-file"
seal_without_execution "$WORK_REPO_TARGET" >/dev/null

init_completion_target "Seal Render Work Repo Uncommitted" "seal-render-work-repo-uncommitted"
WORK_REPO_REJECT="$RUN_DATE-seal-render-work-repo-uncommitted"
"$ROOT/commands/collab/engine/registry.py" set "$WORK_REPO_REJECT" work-repo "$WORK_REPO" >/dev/null
printf 'loose\n' >"$WORK_REPO/loose-file"
complete_execution_with_path "$WORK_REPO_REJECT" "loose-file"
set +e
work_repo_output="$(seal_without_execution "$WORK_REPO_REJECT" 2>&1)"
work_repo_status=$?
set -e
if [[ "$work_repo_status" -eq 0 || "$work_repo_output" != *"SEAL-GIT-STATE: implementation not in git; unstaged or uncommitted touchedPath(s) in "*"[\"loose-file\"]"* ]]; then
  printf 'FAIL: seal-render did not gate against the declared workRepo\n%s\n' "$work_repo_output" >&2
  exit 1
fi

RELATIVE_WORK_REPO="relative-work-repo"
mkdir -p "$RELATIVE_WORK_REPO"
git -C "$RELATIVE_WORK_REPO" init -q
init_completion_target "Seal Render Work Repo Relative Rejected" "seal-render-work-repo-relative-rejected"
RELATIVE_WORK_REPO_TARGET="$RUN_DATE-seal-render-work-repo-relative-rejected"
set +e
relative_work_repo_output="$("$ROOT/commands/collab/engine/registry.py" set "$RELATIVE_WORK_REPO_TARGET" work-repo "$RELATIVE_WORK_REPO" 2>&1)"
relative_work_repo_status=$?
set -e
if [[ "$relative_work_repo_status" -eq 0 || "$relative_work_repo_output" != *"work-repo must be an absolute path: $RELATIVE_WORK_REPO"* ]]; then
  printf 'FAIL: work-repo accepted a relative path\n%s\n' "$relative_work_repo_output" >&2
  exit 1
fi

printf 'OK: seal-render git-state gate accepts committed/deleted paths and rejects staged, unstaged, or working-tree-only paths\n'
printf 'OK: seal-render git-state gate resolves declared workRepo for cross-repo collabs\n'
