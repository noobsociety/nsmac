#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

make_repo() {
  local dir="$1"
  mkdir -p "$dir/_data" "$dir/_functions/demo"
  cat >"$dir/_data/source-ledger.md" <<'MD'
# Migration ledger

| Source path | Normative essence | Destination owner | Load contract | Validation check | Delete condition |
|---|---|---|---|---|---|
| `rules/auto.mdc` | router | deleted | n/a | audit | no refs |
| `_mdc/auto/example.mdc` | policy | `_core/example.md` | read | audit | no refs |
| `_functions/demo/route.md` (embedded `route-arg`) | args | same file | read | audit | retained |
MD
  cat >"$dir/_functions/demo/route.md" <<'MD'
# route

```route-arg
dispatch: (demo route)
param: name=<arg>; required=optional; placeholder=<arg>; class=type; rule=text; default=literal:empty
```
MD
}

clean="$TMPDIR/clean"
make_repo "$clean"
"$ROOT/tools/command-system/check-source-ledger.py" --check --root "$clean" >"$TMPDIR/clean.out"

if ! grep -Fq "OK: source ledger" "$TMPDIR/clean.out"; then
  printf 'FAIL: expected clean fixture to pass\n' >&2
  cat "$TMPDIR/clean.out" >&2
  exit 1
fi

legacy="$TMPDIR/legacy"
make_repo "$legacy"
mkdir -p "$legacy/_mdc/auto"
printf 'extra\n' >"$legacy/_mdc/auto/missing.mdc"
set +e
"$ROOT/tools/command-system/check-source-ledger.py" --check --root "$legacy" >"$TMPDIR/legacy.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected retired carrier fixture to fail\n' >&2
  exit 1
fi
if ! grep -Fq "discovered carrier lacks ledger row: _mdc/auto/missing.mdc" "$TMPDIR/legacy.out"; then
  printf 'FAIL: retired carrier output mismatch\n' >&2
  cat "$TMPDIR/legacy.out" >&2
  exit 1
fi

blank="$TMPDIR/blank"
make_repo "$blank"
perl -0pi -e 's/\| `_mdc\/auto\/example\.mdc` \| policy \| `_core\/example\.md` \| read \| audit \| no refs \|/\| `_mdc\/auto\/example.mdc` \| policy \|  \| read \| audit \| no refs \|/' "$blank/_data/source-ledger.md"
set +e
"$ROOT/tools/command-system/check-source-ledger.py" --check --root "$blank" >"$TMPDIR/blank.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected blank field fixture to fail\n' >&2
  exit 1
fi
if ! grep -Fq "ledger row missing fields: destination owner" "$TMPDIR/blank.out"; then
  printf 'FAIL: blank field output mismatch\n' >&2
  cat "$TMPDIR/blank.out" >&2
  exit 1
fi

undeclared="$TMPDIR/undeclared"
make_repo "$undeclared"
printf 'See _mdc/auto/untracked.mdc\n' >"$undeclared/_functions/demo/use.md"
set +e
"$ROOT/tools/command-system/check-source-ledger.py" --check --root "$undeclared" >"$TMPDIR/undeclared.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected undeclared dependency fixture to fail\n' >&2
  exit 1
fi
if ! grep -Fq "retired substrate trace: _mdc/auto/untracked.mdc" "$TMPDIR/undeclared.out"; then
  printf 'FAIL: undeclared dependency output mismatch\n' >&2
  cat "$TMPDIR/undeclared.out" >&2
  exit 1
fi

printf 'OK: source ledger audit detects dependency drift\n'
