#!/usr/bin/env bash
# Contract: platform/tooling/migrate-collab-state-dirs.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/platform/tooling/migrate_collab_state_dirs.py" "$@"
