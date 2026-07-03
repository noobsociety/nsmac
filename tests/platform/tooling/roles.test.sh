#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

assert_fails_with() {
  local expected="$1"
  shift
  local output status
  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e
  if [[ "$status" -eq 0 ]]; then
    printf 'FAIL: command unexpectedly passed: %s\n' "$*" >&2
    exit 1
  fi
  if [[ "$output" != *"$expected"* ]]; then
    printf 'FAIL: output did not contain expected text: %s\n%s\n' "$expected" "$output" >&2
    exit 1
  fi
}

cd "$ROOT"

python3 platform/tooling/roles.py validate >/dev/null

cp -R commands/collab/reference/roles "$TMPDIR/roles"
python3 - "$TMPDIR/roles/pe.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["dimensions"] = ["missing"]
path.write_text(json.dumps(data, indent=2) + "\n")
PY
assert_fails_with "dimensions contain unknown value(s): missing" \
  python3 platform/tooling/roles.py --roles-dir "$TMPDIR/roles" validate

cp -R commands/collab/reference/roles "$TMPDIR/missing-dimensions"
python3 - "$TMPDIR/missing-dimensions/pe.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data.pop("dimensions")
path.write_text(json.dumps(data, indent=2) + "\n")
PY
assert_fails_with "dimensions must be a non-empty array" \
  python3 platform/tooling/roles.py --roles-dir "$TMPDIR/missing-dimensions" validate

printf 'OK: role validation enforces domain dimensions\n'
