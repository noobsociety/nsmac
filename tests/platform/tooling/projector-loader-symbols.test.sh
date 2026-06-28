#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
GATE="$ROOT/platform/tooling/audit-projector-loader-symbols.py"

clean="$TMPDIR/clean"
mkdir -p "$clean/commands/collab/engine" "$clean/commands/collab/reference/roles" "$clean/platform/tooling"
printf '{"key":"dp","displayName":"Deterministic Projector","concerns":["historical rendering"],"joinable":false}\n' \
  >"$clean/commands/collab/reference/roles/dp.json"
printf 'def load_role(role):\n    return role\n' >"$clean/platform/tooling/roles.py"
printf 'role = "dp"\n' >"$clean/commands/collab/engine/render.py"
python3 "$GATE" --root "$clean" >/dev/null

bad="$TMPDIR/bad"
cp -R "$clean" "$bad"
printf 'from roles import load_projector\n' >"$bad/commands/collab/engine/render.py"
set +e
python3 "$GATE" --root "$bad" >"$TMPDIR/bad.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected projector loader symbol to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'projector loader symbol `load_projector`' "$TMPDIR/bad.out"; then
  printf 'FAIL: projector loader output mismatch\n' >&2
  cat "$TMPDIR/bad.out" >&2
  exit 1
fi

printf 'OK: projector loader symbol gate bans loader machinery without banning dp tombstone data\n'
