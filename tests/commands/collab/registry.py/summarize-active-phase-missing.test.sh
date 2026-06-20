#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ROUTE="$ROOT/commands/collab/summarize/index.md"

if ! grep -Fq "<!-- abort: summarize-active-phase-missing -->" "$ROUTE"; then
  printf 'FAIL: summarize active-phase-missing abort anchor missing\n' >&2
  exit 1
fi

printf 'OK: summarize active-phase-missing abort remains anchored\n'
