#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
GATE="$ROOT/platform/tooling/audit-collab-readonly-contract.py"

make_fixture() {
  local dir="$1"
  mkdir -p "$dir/commands/collab/log"
  cat >"$dir/commands/collab/log/index.md" <<'MD'
# (collab log)

## Trigger

**Dispatch:** `(collab log [<target>])` -- routing-only command form; not a shell command.

## Steps

1. Call `commands/collab/engine/registry.py log <target>`.
2. Display the helper output.

## Notes

- **Read-only:** This route does not mutate registry state or transcript text.
- **Provenance:** `commands/collab/engine/registry.py render-participants` is mentioned here but is not a Step backend.
MD
}

clean="$TMPDIR/clean"
make_fixture "$clean"
python3 "$GATE" --root "$clean" >/dev/null

missing_backend="$TMPDIR/missing-backend"
make_fixture "$missing_backend"
python3 - "$missing_backend/commands/collab/log/index.md" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.write_text(path.read_text().replace("Call `commands/collab/engine/registry.py log <target>`.", "Read the registry."))
PY
set +e
python3 "$GATE" --root "$missing_backend" >"$TMPDIR/missing-backend.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected read-only route without Step backend to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'read-only route has no auditable Step registry.py backend' "$TMPDIR/missing-backend.out"; then
  printf 'FAIL: missing-backend output mismatch\n' >&2
  cat "$TMPDIR/missing-backend.out" >&2
  exit 1
fi

mutating_backend="$TMPDIR/mutating-backend"
make_fixture "$mutating_backend"
perl -0pi -e 's/registry\.py log/registry.py render-participants/' "$mutating_backend/commands/collab/log/index.md"
set +e
python3 "$GATE" --root "$mutating_backend" >"$TMPDIR/mutating-backend.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected read-only route with mutating backend to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'read-only route calls mutating or unknown registry subcommand: render-participants' "$TMPDIR/mutating-backend.out"; then
  printf 'FAIL: mutating-backend output mismatch\n' >&2
  cat "$TMPDIR/mutating-backend.out" >&2
  exit 1
fi

printf 'OK: collab read-only contract gate rejects unauditable and mutating backends\n'
