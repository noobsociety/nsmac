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

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-release-confirmation-gates"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --work-repo "$WORK" "Release Confirmation Gates" >/dev/null

tag_output="$("$ROOT/commands/collab/engine/registry.py" tag "$TARGET" --tag collab/confirmed-tag --confirm)"
if [[ "$tag_output" != *"MODE: confirm"* || "$tag_output" != *"CREATED: tag collab/confirmed-tag"* ]]; then
  printf 'FAIL: confirmed tag did not report creation\n%s\n' "$tag_output" >&2
  exit 1
fi
if ! git -C "$WORK" rev-parse --verify --quiet "refs/tags/collab/confirmed-tag" >/dev/null; then
  printf 'FAIL: confirmed tag was not created\n' >&2
  exit 1
fi

release_output="$("$ROOT/commands/collab/engine/registry.py" release "$TARGET" \
  --tag collab/release-gated \
  --confirm \
  --direct-merge \
  --github-release)"
for expected in \
  "MODE: confirm" \
  "DIRECT_MERGE: declared, not wired (v2)" \
  "GITHUB_RELEASE: declared, not wired (v2)" \
  "AUTO_FIRE: disabled" \
  "GATED: --confirm recorded, but no release action ran because --auto-fire is disabled."
do
  if [[ "$release_output" != *"$expected"* ]]; then
    printf 'FAIL: release confirmation gate output missing %s\n%s\n' "$expected" "$release_output" >&2
    exit 1
  fi
done
if git -C "$WORK" rev-parse --verify --quiet "refs/tags/collab/release-gated" >/dev/null; then
  printf 'FAIL: release confirm without --auto-fire created a tag\n' >&2
  exit 1
fi

dry_opt_in_output="$("$ROOT/commands/collab/engine/registry.py" release "$TARGET" \
  --tag collab/release-opt-in-dry \
  --direct-merge \
  --github-release \
  --auto-fire)"
if [[ "$dry_opt_in_output" != *"MODE: dry-run"* || "$dry_opt_in_output" != *"AUTO_FIRE: enabled"* ]]; then
  printf 'FAIL: opt-in dry-run did not render enabled auto-fire without executing\n%s\n' "$dry_opt_in_output" >&2
  exit 1
fi
if [[ "$dry_opt_in_output" != *"DIRECT_MERGE: declared, not wired (v2)"* || "$dry_opt_in_output" != *"GITHUB_RELEASE: declared, not wired (v2)"* ]]; then
  printf 'FAIL: opt-in dry-run did not label unwired flags as v2\n%s\n' "$dry_opt_in_output" >&2
  exit 1
fi
if git -C "$WORK" rev-parse --verify --quiet "refs/tags/collab/release-opt-in-dry" >/dev/null; then
  printf 'FAIL: release opt-in dry-run created a tag\n' >&2
  exit 1
fi

printf 'OK: release confirmation and opt-in gates preserve dry-run/auto-fire boundaries\n'
