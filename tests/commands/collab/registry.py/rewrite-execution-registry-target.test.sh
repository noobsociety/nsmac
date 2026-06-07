#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ROUTE="$ROOT/commands/collab/rewrite-execution/index.md"

if ! grep -Fq '<!-- abort: rewrite-execution-registry-target -->' "$ROUTE"; then
  printf 'FAIL: rewrite-execution registry-target abort anchor missing\n' >&2
  exit 1
fi
if ! grep -Fq '**ABORT**: registry target unavailable' "$ROUTE"; then
  printf 'FAIL: rewrite-execution registry-target abort text missing\n' >&2
  exit 1
fi

printf 'OK: rewrite-execution registry target abort remains anchored\n'
