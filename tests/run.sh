#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if (($# > 0)); then
  printf 'Usage: ./tests/run.sh\n' >&2
  exit 2
fi

run_timed() {
  local label="$1"
  shift

  printf 'RUN: %s\n' "$label"
  TIMEFORMAT="TIME: ${label}: %3R seconds"
  time "$@"
}

script_count=0
suite_start="$(date +%s)"

run_test_script() {
  local test_script="$1"

  script_count=$((script_count + 1))
  run_timed "test $test_script" bash "$test_script"
}

# Every tests/**/*.test.sh runs; a new test file is picked up automatically.
run_all_test_scripts() {
  local test_script

  while IFS= read -r test_script; do
    run_test_script "$test_script"
  done < <(find tests -name '*.test.sh' | sort)
}

# audit.sh owns audit-role-prose.sh; keep the suite from duplicating it.
run_timed "audit ./platform/tooling/audit.sh" ./platform/tooling/audit.sh
run_all_test_scripts

suite_seconds=$(( $(date +%s) - suite_start ))
printf 'SUMMARY: ./tests/run.sh completed %d test script(s) in %d seconds.\n' "$script_count" "$suite_seconds"
