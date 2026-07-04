#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

step_calls="$(awk '
  /^## Steps$/ { in_steps = 1; next }
  /^## / && in_steps { in_steps = 0 }
  in_steps { print }
' commands/collab/close/index.md)"

if [[ "$step_calls" == *"commands/collab/engine/registry.py tag"* || "$step_calls" == *"commands/collab/engine/registry.py release"* || "$step_calls" == *"git push"* || "$step_calls" == *"gh release"* ]]; then
  printf 'FAIL: close route Steps contain release orchestration commands\n' >&2
  exit 1
fi

if rg -n "release_collab|tag_collab|commands\\.collab\\.engine\\.release|git push|gh release" commands/collab/engine/lifecycle_commands.py; then
  printf 'FAIL: lifecycle close implementation imports or calls release orchestration\n' >&2
  exit 1
fi

if ! rg -n "Release boundary" commands/collab/close/index.md >/dev/null; then
  printf 'FAIL: close route does not document the release boundary\n' >&2
  exit 1
fi

printf 'OK: close route and lifecycle implementation remain outside release orchestration\n'
