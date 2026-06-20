#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

FAIL=0

# Verify retired synthesis/projector negation residue stays trimmed from live route prose
# (these phrases negated artifacts removed with the synthesis/projection stack; W24 weekly-review TW-4)
if grep -Fq 'synthesis artifacts' commands/collab/summarize/index.md 2>/dev/null; then
  printf 'FAIL: synthesis-artifact negation residue found in summarize route prose\n' >&2
  FAIL=1
fi

if grep -Fq 'Projector metadata is intentionally absent' commands/collab/show-policy/index.md 2>/dev/null; then
  printf 'FAIL: projector-metadata negation residue found in show-policy route prose\n' >&2
  FAIL=1
fi

# Verify the Deterministic Projector (dp) prohibition section is absent from role-prohibitions.md
if grep -Fq '## Deterministic Projector (dp)' commands/collab/reference/role-prohibitions.md 2>/dev/null; then
  printf 'FAIL: Deterministic Projector (dp) prohibition section still present in role-prohibitions.md\n' >&2
  FAIL=1
fi

# Verify stale (collab aggregate) reference is absent from live doc routes
if grep -Fq '(collab aggregate)' commands/collab/init/index.md commands/collab/open/index.md 2>/dev/null; then
  printf 'FAIL: retired (collab aggregate) dispatch reference found in init or open route docs\n' >&2
  FAIL=1
fi

# Verify raw transcript sibling references are absent from init and open docs
if grep -P 'records/[^`]*-raw\.md' commands/collab/init/index.md commands/collab/open/index.md 2>/dev/null; then
  printf 'FAIL: raw transcript sibling path reference found in init or open route docs\n' >&2
  FAIL=1
fi

# Verify no projection-mode synthesis flag in live doc surfaces (excluding engine code and records)
PROJECTION_MODE_HITS=$(git grep -nP '\bprojection-mode\b' \
  -- 'commands/' 'platform/standards/' \
  ':(exclude)commands/collab/engine/' \
  ':(exclude)records/' \
  2>/dev/null || true)

if [ -n "$PROJECTION_MODE_HITS" ]; then
  printf 'FAIL: synthesis projection-mode flag found in live doc surfaces:\n%s\n' "$PROJECTION_MODE_HITS" >&2
  FAIL=1
fi

# Verify no per-piece synthesis mode in live doc surfaces
PER_PIECE_HITS=$(git grep -nP '\bper-piece\b' \
  -- 'commands/' 'platform/standards/' \
  ':(exclude)commands/collab/engine/' \
  ':(exclude)records/' \
  2>/dev/null || true)

if [ -n "$PER_PIECE_HITS" ]; then
  printf 'FAIL: synthesis per-piece mode found in live doc surfaces:\n%s\n' "$PER_PIECE_HITS" >&2
  FAIL=1
fi

# Verify no projection_* / is_projection_* render symbol names in engine Python
# (symbols were retired with the synthesis/projection stack; transcript-neutral names replace them)
PROJECTION_SYMBOL_HITS=$(git grep -nP '\b(?:is_)?projection_[a-z_]+\s*[\(=]' \
  -- 'commands/collab/engine/*.py' \
  2>/dev/null || true)

if [ -n "$PROJECTION_SYMBOL_HITS" ]; then
  printf 'FAIL: legacy projection_* / is_projection_* render symbol found in engine Python:\n%s\n' "$PROJECTION_SYMBOL_HITS" >&2
  FAIL=1
fi

[ "$FAIL" -eq 0 ] && printf 'OK: synthesis CLI vocabulary absent from live doc surfaces\n'
exit "$FAIL"
