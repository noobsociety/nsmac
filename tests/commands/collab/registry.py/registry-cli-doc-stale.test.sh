#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

"$ROOT/commands/collab/engine/registry.py" registry-cli-doc --check

printf 'OK: generated registry CLI reference is current\n'
