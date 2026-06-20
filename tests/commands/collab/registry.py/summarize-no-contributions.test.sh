#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ROUTE="$ROOT/commands/collab/summarize/index.md"

if ! grep -Fq "<!-- abort: summarize-no-contributions -->" "$ROUTE"; then
  printf 'FAIL: summarize no-contributions abort anchor missing\n' >&2
  exit 1
fi

printf 'OK: summarize no-contributions abort remains anchored\n'
