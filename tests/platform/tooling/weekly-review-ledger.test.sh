#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LEDGER="$ROOT/platform/data/weekly-review-ledger.md"
REGISTRY="$ROOT/commands/collab/engine/registry.py"

test -f "$LEDGER"

grep -Fq '| #6 | retired |' "$LEDGER"
grep -Fq 'dotfiles` at `234c10e` has no `core/framework` references' "$LEDGER"
grep -Fq '| #14 | retired |' "$LEDGER"
grep -Fq 'No `backup/*` branches exist in `~/.cursor`' "$LEDGER"
grep -Fq '| #25 | carried |' "$LEDGER"
grep -Fq '`(collab speak)` surfaces prior turns to speakers 2..N' "$LEDGER"
grep -Fq '| #26 | carried |' "$LEDGER"
grep -Fq '`seal-state` rejects closed/archived records' "$LEDGER"
grep -Fq '| #27 | retired |' "$LEDGER"
grep -Fq 'Commit `701001e` marks `dp` as `joinable: false`' "$LEDGER"

grep -Fq 'platform/data/weekly-review-ledger.md' "$REGISTRY"

TRANSIENT_WEEKLY_RE='(/Users/ejelome/[D]ownloads/(next-collabs|collab-audits)|~[/][D]ownloads/(next-collabs|collab-audits))'

if rg -n "$TRANSIENT_WEEKLY_RE" \
  "$ROOT/commands" "$ROOT/platform"; then
  printf 'ERROR: durable source still cites transient weekly-review audit files\n' >&2
  exit 1
fi

printf 'OK: weekly review row ledger is committed and durable references are clean\n'
