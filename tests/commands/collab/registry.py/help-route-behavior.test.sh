#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

collab_init_output="$(commands/collab/engine/registry.py help collab init)"
collab_init_expected="$(cat commands/collab/init/index.md)"
if [[ "$collab_init_output" != "$collab_init_expected" ]]; then
  printf 'FAIL: help collab init did not render the route doc exactly
' >&2
  exit 1
fi

run_plan_output="$(commands/collab/engine/registry.py help collab run plan)"
run_plan_expected="$(cat commands/collab/run-plan/index.md)"
if [[ "$run_plan_output" != "$run_plan_expected" ]]; then
  printf 'FAIL: help collab run plan did not render the hyphenated route doc exactly
' >&2
  exit 1
fi

set +e
missing_output="$(commands/collab/engine/registry.py help collab missing 2>&1)"
missing_status=$?
empty_output="$(commands/collab/engine/registry.py help 2>&1)"
empty_status=$?
set -e

if [[ "$missing_status" -eq 0 || "$missing_output" != *'route not found: collab missing'* ]]; then
  printf 'FAIL: help accepted a missing route
%s
' "$missing_output" >&2
  exit 1
fi

if [[ "$empty_status" -eq 0 || "$empty_output" != *'<route> is required'* ]]; then
  printf 'FAIL: help accepted an empty route
%s
' "$empty_output" >&2
  exit 1
fi

printf 'OK: help renders existing route docs exactly and rejects missing route selectors
'
