#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

clean="$TMPDIR/clean"
mkdir -p "$clean/commands/demo/run" "$clean/commands/demo/show" "$clean/commands/demo/engine"
printf '[show](../show/index.md)\n' >"$clean/commands/demo/run/index.md"
printf '# /demo show\n' >"$clean/commands/demo/show/index.md"
printf 'from commands.demo.engine import helper\n' >"$clean/commands/demo/engine/local.py"
printf '# helper\n' >"$clean/commands/demo/engine/helper.py"
COMMAND_CONFIG_ROOT="$clean" "$ROOT/platform/tooling/audit-placement.sh" >/dev/null

legacy="$TMPDIR/legacy"
mkdir -p "$legacy/commands/demo/run" "$legacy/core/framework"
printf '# /demo run\n' >"$legacy/commands/demo/run/index.md"
set +e
COMMAND_CONFIG_ROOT="$legacy" "$ROOT/platform/tooling/audit-placement.sh" >"$TMPDIR/legacy.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected legacy layer directory to fail placement\n' >&2
  exit 1
fi
if ! grep -Fq 'ERROR: legacy root path remains after vertical-slice move: core' "$TMPDIR/legacy.out"; then
  printf 'FAIL: legacy layer placement error was not stable\n' >&2
  cat "$TMPDIR/legacy.out" >&2
  exit 1
fi

cross_import="$TMPDIR/cross-import"
mkdir -p "$cross_import/commands/demo/engine" "$cross_import/commands/other/engine"
printf 'import commands.other.engine.tool\n' >"$cross_import/commands/demo/engine/use_other.py"
printf '# tool\n' >"$cross_import/commands/other/engine/tool.py"
set +e
COMMAND_CONFIG_ROOT="$cross_import" "$ROOT/platform/tooling/audit-placement.sh" >"$TMPDIR/cross-import.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected cross-slice Python import to fail placement\n' >&2
  exit 1
fi
if ! grep -Fq 'ERROR: commands/demo/engine/use_other.py: cross-slice import `commands.other.engine.tool` targets commands/other/' "$TMPDIR/cross-import.out"; then
  printf 'FAIL: cross-slice import placement error was not stable\n' >&2
  cat "$TMPDIR/cross-import.out" >&2
  exit 1
fi

cross_link="$TMPDIR/cross-link"
mkdir -p "$cross_link/commands/demo/run" "$cross_link/commands/other/show"
printf '[other](../../other/show/index.md)\n' >"$cross_link/commands/demo/run/index.md"
printf '# /other show\n' >"$cross_link/commands/other/show/index.md"
set +e
COMMAND_CONFIG_ROOT="$cross_link" "$ROOT/platform/tooling/audit-placement.sh" >"$TMPDIR/cross-link.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected cross-slice Markdown link to fail placement\n' >&2
  exit 1
fi
if ! grep -Fq 'ERROR: commands/demo/run/index.md: cross-slice markdown link `../../other/show/index.md` targets commands/other/' "$TMPDIR/cross-link.out"; then
  printf 'FAIL: cross-slice link placement error was not stable\n' >&2
  cat "$TMPDIR/cross-link.out" >&2
  exit 1
fi

printf 'OK: placement audit rejects legacy layers and cross-slice references\n'
