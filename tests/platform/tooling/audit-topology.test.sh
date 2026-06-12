#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

make_catalog() {
  local root="$1"
  mkdir -p "$root/commands"
  cat >"$root/commands/commands.md" <<'CATALOG'
# (commands)

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
COMMAND_CONFIG_ROOT="$clean" "$ROOT/platform/tooling/audit-topology.sh" >/dev/null

missing="$TMPDIR/missing"
make_catalog "$missing"
mkdir -p "$missing/commands/demo"
printf '# /demo\n' >"$missing/commands/demo/index.md"
set +e
COMMAND_CONFIG_ROOT="$missing" "$ROOT/platform/tooling/audit-topology.sh" >"$TMPDIR/missing.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected missing route entry point to fail\n' >&2
  exit 1
fi
if ! grep -Fxq 'ERROR: generated catalog link target missing: commands/demo/run/index.md' "$TMPDIR/missing.out"; then
  printf 'FAIL: missing route output did not name broken generated link\n' >&2
  cat "$TMPDIR/missing.out" >&2
  exit 1
fi
if ! grep -Fxq 'ERROR: catalog names missing route entry point: commands/demo/run/index.md' "$TMPDIR/missing.out"; then
  printf 'FAIL: missing route output did not name catalog mismatch\n' >&2
  cat "$TMPDIR/missing.out" >&2
  exit 1
fi

orphan="$TMPDIR/orphan"
make_catalog "$orphan"
mkdir -p "$orphan/commands/demo/run" "$orphan/commands/demo/extra"
printf '# /demo\n' >"$orphan/commands/demo/index.md"
printf '# /demo run\n' >"$orphan/commands/demo/run/index.md"
printf '# /demo extra\n' >"$orphan/commands/demo/extra/index.md"
set +e
COMMAND_CONFIG_ROOT="$orphan" "$ROOT/platform/tooling/audit-topology.sh" >"$TMPDIR/orphan.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected uncataloged route entry point to fail\n' >&2
  exit 1
fi
if ! grep -Fxq 'ERROR: route missing from commands catalog: commands/demo/extra/index.md' "$TMPDIR/orphan.out"; then
  printf 'FAIL: uncataloged route output did not name stable path\n' >&2
  cat "$TMPDIR/orphan.out" >&2
  exit 1
fi

backing="$TMPDIR/backing"
make_catalog "$backing"
python3 - "$backing/commands/commands.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text().replace('[run](demo/run/index.md)', '[reference](demo/reference/doc.md)', 1)
path.write_text(text)
PY
mkdir -p "$backing/commands/demo/run" "$backing/commands/demo/reference"
printf '# /demo\n' >"$backing/commands/demo/index.md"
printf '# /demo run\n' >"$backing/commands/demo/run/index.md"
printf '# Backing doc\n' >"$backing/commands/demo/reference/doc.md"
set +e
COMMAND_CONFIG_ROOT="$backing" "$ROOT/platform/tooling/audit-topology.sh" >"$TMPDIR/backing.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected generated backing-file catalog link to fail\n' >&2
  exit 1
fi
if ! grep -Fxq 'ERROR: generated catalog links backing file instead of route entry: demo/reference/doc.md' "$TMPDIR/backing.out"; then
  printf 'FAIL: backing-link output did not name generated backing file\n' >&2
  cat "$TMPDIR/backing.out" >&2
  exit 1
fi

printf 'OK: topology audit enforces public index.md catalog entries\n'
