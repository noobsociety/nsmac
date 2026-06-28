#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
GATE="$ROOT/platform/tooling/audit-collab-route-wiring.py"

make_fixture() {
  local dir="$1"
  mkdir -p "$dir/commands/collab/engine" "$dir/commands/collab/log" "$dir/generated"
  cat >"$dir/commands/collab/engine/registry.py" <<'PY'
#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='command', required=True)
subparsers.add_parser('log')
parser.parse_args()
PY
  chmod +x "$dir/commands/collab/engine/registry.py"
  cat >"$dir/commands/collab/index.md" <<'MD'
# (collab)

## Trigger

**Dispatch:** `(collab <log>)` -- routing-only command form; not a shell command.

## Notes

- **Route:** `log` -> [log](log/index.md).
MD
  cat >"$dir/commands/collab/log/index.md" <<'MD'
# (collab log)

## Trigger

**Dispatch:** `(collab log [<target>])` -- routing-only command form; not a shell command.

## Steps

1. Call `commands/collab/engine/registry.py log <target>`.
MD
  cat >"$dir/generated/command-reference.md" <<'MD'
# Command reference

<!-- BEGIN GENERATED:COMMAND_REFERENCE -->
## collab
### log
`(collab log [<target>])`
<!-- END GENERATED:COMMAND_REFERENCE -->
MD
}

clean="$TMPDIR/clean"
make_fixture "$clean"
python3 "$GATE" --root "$clean" >/dev/null

missing_backend="$TMPDIR/missing-backend"
make_fixture "$missing_backend"
perl -0pi -e 's/registry\.py log/registry.py status/' "$missing_backend/commands/collab/log/index.md"
set +e
python3 "$GATE" --root "$missing_backend" >"$TMPDIR/missing-backend.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected missing registry subcommand to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'registry subcommand missing: status' "$TMPDIR/missing-backend.out"; then
  printf 'FAIL: backend output mismatch\n' >&2
  cat "$TMPDIR/missing-backend.out" >&2
  exit 1
fi

router_omission="$TMPDIR/router-omission"
make_fixture "$router_omission"
python3 - "$router_omission/commands/collab/index.md" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.write_text(path.read_text().replace('`log` -> [log](log/index.md).', ''))
PY
set +e
python3 "$GATE" --root "$router_omission" >"$TMPDIR/router-omission.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected router omission to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'Route roster missing `log`' "$TMPDIR/router-omission.out"; then
  printf 'FAIL: router omission output mismatch\n' >&2
  cat "$TMPDIR/router-omission.out" >&2
  exit 1
fi

generated_omission="$TMPDIR/generated-omission"
make_fixture "$generated_omission"
python3 - "$generated_omission/generated/command-reference.md" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.write_text(path.read_text().replace('### log\n`(collab log [<target>])`\n', ''))
PY
set +e
python3 "$GATE" --root "$generated_omission" >"$TMPDIR/generated-omission.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected generated omission to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'generated/command-reference.md: missing collab route `log`' "$TMPDIR/generated-omission.out"; then
  printf 'FAIL: generated omission output mismatch\n' >&2
  cat "$TMPDIR/generated-omission.out" >&2
  exit 1
fi

printf 'OK: collab route wiring gate rejects backend and parity drift\n'
