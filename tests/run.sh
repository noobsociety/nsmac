#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RETAINED_MANIFEST="tests/suites/full.txt"

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

  if [[ ! -f "$test_script" ]]; then
    printf 'FAIL: suite references missing test script: %s\n' "$test_script" >&2
    exit 1
  fi

  script_count=$((script_count + 1))
  run_timed "test $test_script" bash "$test_script"
}

run_retained_manifest() {
  local line

  [[ -f "$RETAINED_MANIFEST" ]] || {
    printf 'FAIL: missing retained test manifest: %s\n' "$RETAINED_MANIFEST" >&2
    exit 1
  }

  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      ""|\#*) continue ;;
      @*) printf 'FAIL: unsupported suite include in %s: %s\n' "$RETAINED_MANIFEST" "$line" >&2; exit 1 ;;
      *)
        run_test_script "$line"
        ;;
    esac
  done <"$RETAINED_MANIFEST"
}

# audit.sh owns audit-role-prose.sh; keep the retained suite from duplicating it.
run_timed "audit ./platform/tooling/audit.sh" ./platform/tooling/audit.sh
run_retained_manifest

suite_seconds=$(( $(date +%s) - suite_start ))
printf 'SUMMARY: ./tests/run.sh completed %d test script(s) in %d seconds.\n' "$script_count" "$suite_seconds"
