#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export CURSOR_COLLAB_STATE_HOME="$TMPDIR/state-home"

set +e
missing_name_output="$("$ROOT/tools/collab/registry.py" init --agent-id codex 2>&1)"
missing_name_status=$?
set -e
if [[ "$missing_name_status" -eq 0 || "$missing_name_output" != *'<name> is required'* ]]; then
  printf 'FAIL: init accepted a missing name\n%s\n' "$missing_name_output" >&2
  exit 1
fi

set +e
bad_reviewer_output="$("$ROOT/tools/collab/registry.py" init --agent-id codex --reviewer bad-role "Argument Validation" 2>&1)"
bad_reviewer_status=$?
set -e
if [[ "$bad_reviewer_status" -eq 0 || "$bad_reviewer_output" != *'--reviewer requires a role key'* ]]; then
  printf 'FAIL: init accepted an invalid reviewer value\n%s\n' "$bad_reviewer_output" >&2
  exit 1
fi

set +e
old_opt_in_output="$("$ROOT/tools/collab/registry.py" init --agent-id codex --participant-verification "Argument Validation" 2>&1)"
old_opt_in_status=$?
set -e
if [[ "$old_opt_in_status" -eq 0 || "$old_opt_in_output" != *'unknown flag: --participant-verification'* ]]; then
  printf 'FAIL: init accepted retired --participant-verification flag\n%s\n' "$old_opt_in_output" >&2
  exit 1
fi

set +e
retired_cap_output="$("$ROOT/tools/collab/registry.py" init --agent-id codex --verification-cap 2 "Argument Validation" 2>&1)"
retired_cap_status=$?
set -e
if [[ "$retired_cap_status" -eq 0 || "$retired_cap_output" != *'unknown flag: --verification-cap'* ]]; then
  printf 'FAIL: init accepted retired --verification-cap flag\n%s\n' "$retired_cap_output" >&2
  exit 1
fi

set +e
slug_empty_output="$("$ROOT/tools/collab/registry.py" init --agent-id codex "!!!" 2>&1)"
slug_empty_status=$?
set -e
if [[ "$slug_empty_status" -eq 0 || "$slug_empty_output" != *'slug is empty'* ]]; then
  printf 'FAIL: init accepted an empty slug\n%s\n' "$slug_empty_output" >&2
  exit 1
fi

printf 'OK: init argument validation rejects missing names, invalid reviewer values, retired verification flags, and empty slugs\n'
