#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"

set +e
output="$("$ROOT/tools/collab/registry.py" seal-state missing pa 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"registry missing: .collabs/registry.json"* ]]; then
  printf 'FAIL: seal-state did not reject an unreadable registry\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: seal verification rejects unreadable records\n'
