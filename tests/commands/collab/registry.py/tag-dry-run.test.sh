#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

WORK="$TMPDIR/work"
mkdir -p "$WORK"
git -C "$WORK" init >/dev/null
git -C "$WORK" config user.name "Test User"
git -C "$WORK" config user.email "test@example.com"
printf 'base\n' >"$WORK/file.txt"
git -C "$WORK" add file.txt
git -C "$WORK" commit -m "chore: initial" >/dev/null
WORK_REAL="$(cd "$WORK" && pwd -P)"

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-tag-dry-run"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --work-repo "$WORK" "Tag Dry Run" >/dev/null

output="$("$ROOT/commands/collab/engine/registry.py" tag "$TARGET" --tag collab/dry-run-tag)"
for expected in \
  "MODE: dry-run" \
  "TARGET: $TARGET" \
  "WORK_REPO: $WORK_REAL" \
  "TAG: collab/dry-run-tag" \
  "ACTION: create annotated local git tag" \
  "NEXT: Rerun with --confirm to create the local tag."
do
  if [[ "$output" != *"$expected"* ]]; then
    printf 'FAIL: tag dry-run output missing %s\n%s\n' "$expected" "$output" >&2
    exit 1
  fi
done

fallback_output="$("$ROOT/commands/collab/engine/registry.py" tag --tag collab/active-dry-run-tag)"
if [[ "$fallback_output" != *"TARGET: $TARGET"* || "$fallback_output" != *"MODE: dry-run"* ]]; then
  printf 'FAIL: tag without explicit target did not use active collab\n%s\n' "$fallback_output" >&2
  exit 1
fi

if [[ "$fallback_output" != *"TAG: collab/active-dry-run-tag"* ]]; then
  printf 'FAIL: tag fallback did not use supplied tag name\n%s\n' "$fallback_output" >&2
  exit 1
fi
if git -C "$WORK" rev-parse --verify --quiet "refs/tags/collab/dry-run-tag" >/dev/null; then
  printf 'FAIL: tag dry-run created a tag\n' >&2
  exit 1
fi

printf 'OK: tag defaults to dry-run plans with no tag side effects\n'
