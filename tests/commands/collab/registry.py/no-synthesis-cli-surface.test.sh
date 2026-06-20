#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
HELP_OUTPUT="$("$ROOT/commands/collab/engine/registry.py" --help)"

for command in synthesize-state synthesize render-raw-transcript render-projection-transcript; do
  if grep -Fq "$command" <<<"$HELP_OUTPUT"; then
    printf 'FAIL: registry.py help still exposes %s\n' "$command" >&2
    exit 1
  fi

  set +e
  output="$("$ROOT/commands/collab/engine/registry.py" "$command" 2>&1)"
  status=$?
  set -e
  if [[ "$status" -eq 0 || "$output" != *"invalid choice"* ]]; then
    printf 'FAIL: registry.py %s remains invocable\n%s\n' "$command" "$output" >&2
    exit 1
  fi

  if grep -Fq "### \`$command\`" "$ROOT/generated/registry-cli.md"; then
    printf 'FAIL: generated registry CLI docs still list %s\n' "$command" >&2
    exit 1
  fi
done

printf 'OK: synthesis/projection helper commands are absent from the registry CLI surface\n'
