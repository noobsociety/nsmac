#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ROUTE="$ROOT/commands/collab/summarize/index.md"

if ! grep -Fq "<!-- abort: summarize-record-unreadable -->" "$ROUTE"; then
  printf 'FAIL: summarize record-unreadable abort anchor missing\n' >&2
  exit 1
fi

printf 'OK: summarize record-unreadable abort remains anchored\n'
