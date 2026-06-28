#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

run_timed() {
  local label="$1"
  shift

  printf 'RUN: %s\n' "$label"
  TIMEFORMAT="TIME: ${label}: %3R seconds"
  time "$@"
}

script_count=0
suite_start=$SECONDS

# audit.sh owns audit-role-prose.sh; keep the full-suite runner from duplicating it.
run_timed "audit ./platform/tooling/audit.sh" ./platform/tooling/audit.sh

while IFS= read -r test_script; do
  [[ -n "$test_script" ]] || continue
  script_count=$((script_count + 1))
  run_timed "test $test_script" bash "$test_script"
done < <(find tests -name "*.test.sh" -type f | sort)

suite_seconds=$((SECONDS - suite_start))
printf 'SUMMARY: tests/run.sh completed %d test script(s) in %d seconds.\n' "$script_count" "$suite_seconds"
