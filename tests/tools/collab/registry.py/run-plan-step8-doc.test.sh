#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

if ! grep -Fq 'If Step 7 found no unchecked assigned items' "$ROOT/_functions/collab/run-plan.md"; then
  printf 'FAIL: run-plan Step 8 does not condition prior completed execution on Step 7 having no unchecked items\n' >&2
  exit 1
fi

if ! grep -Fq 'a later successful `execution` helper write replaces the role' "$ROOT/_functions/collab/run-plan.md"; then
  printf 'FAIL: run-plan Step 8 does not document replacement execution semantics\n' >&2
  exit 1
fi

printf 'OK: run-plan Step 8 permits rerun when unchecked assigned items exist\n'
