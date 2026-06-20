#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

if grep -R "RAW_PROVENANCE_BANNER" "$ROOT/commands/collab/engine" >/dev/null 2>&1; then
  printf 'FAIL: RAW_PROVENANCE_BANNER remains in collab engine\n' >&2
  exit 1
fi

if "$ROOT/commands/collab/engine/registry.py" --help | grep -Fq 'migrate-raw-transcript'; then
  printf 'FAIL: migrate-raw-transcript helper command remains in registry CLI\n' >&2
  exit 1
fi

if grep -R "migrate_raw_transcript\\|legacy_raw_transcript\\|raw_transcript_path_for_entry" "$ROOT/commands/collab/engine" >/dev/null 2>&1; then
  printf 'FAIL: raw transcript migration path remains in collab engine\n' >&2
  exit 1
fi

printf 'OK: raw-plane migration and provenance banner residue is absent\n'
