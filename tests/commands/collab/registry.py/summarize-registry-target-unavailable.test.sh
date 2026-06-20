#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ROUTE="$ROOT/commands/collab/summarize/index.md"

if ! grep -Fq "<!-- abort: summarize-registry-target-unavailable -->" "$ROUTE"; then
  printf 'FAIL: summarize registry-target-unavailable abort anchor missing\n' >&2
  exit 1
fi

printf 'OK: summarize registry-target-unavailable abort remains anchored\n'
