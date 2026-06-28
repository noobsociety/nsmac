#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

SUMMARIZE_ROUTE="$ROOT/commands/collab/summarize/index.md"
REWRITE_EXECUTION_ROUTE="$ROOT/commands/collab/rewrite-execution/index.md"
RUN_PLAN_ROUTE="$ROOT/commands/collab/run-plan/index.md"
CLOSE_ROUTE="$ROOT/commands/collab/close/index.md"
SEAL_VERIFICATION_ROUTE="$ROOT/commands/collab/seal-verification/index.md"

for anchor in \
  '<!-- abort: summarize-active-phase-missing -->' \
  '<!-- abort: summarize-no-contributions -->' \
  '<!-- abort: summarize-record-unreadable -->' \
  '<!-- abort: summarize-registry-target-unavailable -->'
do
  if ! grep -Fq "$anchor" "$SUMMARIZE_ROUTE"; then
    printf 'FAIL: summarize abort anchor missing: %s\n' "$anchor" >&2
    exit 1
  fi
done

if ! grep -Fq '<!-- abort: rewrite-execution-registry-target -->' "$REWRITE_EXECUTION_ROUTE"; then
  printf 'FAIL: rewrite-execution registry-target abort anchor missing\n' >&2
  exit 1
fi
if ! grep -Fq '**ABORT**: registry target unavailable' "$REWRITE_EXECUTION_ROUTE"; then
  printf 'FAIL: rewrite-execution registry-target abort text missing\n' >&2
  exit 1
fi

if ! grep -Fq 'If Step 7 found no unchecked assigned items' "$RUN_PLAN_ROUTE"; then
  printf 'FAIL: run-plan Step 8 does not condition prior completed execution on Step 7 having no unchecked items\n' >&2
  exit 1
fi
if ! grep -Fq 'a later successful `execution` helper write replaces the role' "$RUN_PLAN_ROUTE"; then
  printf 'FAIL: run-plan Step 8 does not document replacement execution semantics\n' >&2
  exit 1
fi

assert_promotion_contract() {
  local route_name="$1"
  local route_path="$2"
  local close_word="$3"

  for promotion_contract in \
    'durable rationale' \
    'current transcript' \
    'Audit-block content' \
    'reviewer findings' \
    'seal-trust caveats' \
    'promote it now' \
    'committed source' \
    'relevant route doc, reference doc, or invariant file' \
    "file a concrete backlog row naming the slug, file, and exact location before $close_word" \
    'state that explicitly and continue'
  do
    if ! grep -Fq "$promotion_contract" "$route_path"; then
      printf 'FAIL: %s promotion contract missing: %s\n' "$route_name" "$promotion_contract" >&2
      exit 1
    fi
  done
}

assert_promotion_contract "close route pre-close" "$CLOSE_ROUTE" "closing"
assert_promotion_contract "seal route success-verdict" "$SEAL_VERIFICATION_ROUTE" "recording the success verdict"

for seal_contract in \
  '--outcome success' \
  'Promotion mechanism' \
  'not a per-collab `charteredDeliverables` requirement' \
  'success seal path'
do
  if ! grep -Fq -- "$seal_contract" "$SEAL_VERIFICATION_ROUTE"; then
    printf 'FAIL: seal route promotion design contract missing: %s\n' "$seal_contract" >&2
    exit 1
  fi
done

printf 'OK: collab route doc contracts remain anchored\n'
