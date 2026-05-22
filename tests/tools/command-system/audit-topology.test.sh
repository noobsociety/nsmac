#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

make_catalog() {
  local root="$1"
  mkdir -p "$root/commands"
  cat >"$root/commands/commands.md" <<'CATALOG'
# /commands

<!-- BEGIN GENERATED:COMMANDS_ROSTER -->
| Slash | Signature | Public router | Private functions |
| --- | --- | --- | --- |
| `/demo` | `/demo <run>` | [demo](demo/index.md) | [run](demo/run/index.md) |

| Route | Private function |
| --- | --- |
| `/demo run` | [demo/run/index.md](demo/run/index.md) |
<!-- END GENERATED:COMMANDS_ROSTER -->
CATALOG
}

clean="$TMPDIR/clean"
make_catalog "$clean"
mkdir -p "$clean/commands/demo/run"
printf '# /demo\n' >"$clean/commands/demo/index.md"
printf '# /demo run\n' >"$clean/commands/demo/run/index.md"
COMMAND_CONFIG_ROOT="$clean" "$ROOT/tools/command-system/audit-topology.sh" >/dev/null

missing="$TMPDIR/missing"
make_catalog "$missing"
mkdir -p "$missing/commands/demo"
printf '# /demo\n' >"$missing/commands/demo/index.md"
set +e
COMMAND_CONFIG_ROOT="$missing" "$ROOT/tools/command-system/audit-topology.sh" >"$TMPDIR/missing.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected missing command entry point to fail\n' >&2
  exit 1
fi
if ! grep -Fxq 'ERROR: missing command entry point: commands/demo/run/index.md' "$TMPDIR/missing.out"; then
  printf 'FAIL: missing output did not name required command path\n' >&2
  cat "$TMPDIR/missing.out" >&2
  exit 1
fi

orphan="$TMPDIR/orphan"
make_catalog "$orphan"
mkdir -p "$orphan/commands/demo/run" "$orphan/commands/demo/extra"
printf '# /demo\n' >"$orphan/commands/demo/index.md"
printf '# /demo run\n' >"$orphan/commands/demo/run/index.md"
printf '# /demo extra\n' >"$orphan/commands/demo/extra/index.md"
COMMAND_CONFIG_ROOT="$orphan" "$ROOT/tools/command-system/audit-topology.sh" >"$TMPDIR/orphan.out" 2>&1
if ! grep -Fxq 'WARN: orphaned entry point: commands/demo/extra/index.md (no catalog entry for command demo/extra)' "$TMPDIR/orphan.out"; then
  printf 'FAIL: orphan output did not warn with stable path\n' >&2
  cat "$TMPDIR/orphan.out" >&2
  exit 1
fi

printf 'OK: topology audit enforces registered index.md entries and orphan warnings\n'
