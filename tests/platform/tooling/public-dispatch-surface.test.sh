#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

make_fixture() {
  local fixture="$1"
  mkdir -p "$fixture/commands/collab/run"
  cat >"$fixture/commands/commands.md" <<'MD'
# (commands)

## Trigger

**Dispatch:** `(commands)` -- routing-only command form; not a shell command.
**Search phrases:** command commands list

## Steps

1. Read the catalog.

## Notes

- Catalog fixture.
MD
  cat >"$fixture/commands/collab/index.md" <<'MD'
# (collab)

## Trigger

**Dispatch:** `(collab <run>)` -- routing-only command form; not a shell command.
**Search phrases:** collab router

## Steps

1. Resolve the route after `collab`.

## Notes

- **Route:** `run` -> `run/index.md`.
MD
  cat >"$fixture/commands/collab/run/index.md" <<'MD'
# (collab run)

## Trigger

**Dispatch:** `(collab run)` -- routing-only command form; not a shell command.
**Search phrases:** collab run

## Steps

1. Run the fixture route.

## Notes

- **Parameters:** no arguments accepted.

```route-arg
dispatch: (collab run)
```
MD
}

clean="$TMPDIR/clean"
make_fixture "$clean"
python3 "$ROOT/platform/tooling/check-public-dispatch-surface.py" --root "$clean" >/dev/null

drift="$TMPDIR/drift"
make_fixture "$drift"
perl -0pi -e 's/dispatch: \(collab run\)/dispatch: (collab wrong)/' \
  "$drift/commands/collab/run/index.md"
set +e
python3 "$ROOT/platform/tooling/check-public-dispatch-surface.py" --root "$drift" >"$TMPDIR/drift.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected Dispatch vs route-arg dispatch drift to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'Dispatch `(collab run)` disagrees with route-arg dispatch `(collab wrong)`' "$TMPDIR/drift.out"; then
  printf 'FAIL: drift output did not name Dispatch mismatch\n' >&2
  cat "$TMPDIR/drift.out" >&2
  exit 1
fi

slash_title="$TMPDIR/slash-title"
make_fixture "$slash_title"
slash_char='/'
perl -0pi -e "s|# \\(collab run\\)|# ${slash_char}collab run|" \
  "$slash_title/commands/collab/run/index.md"
set +e
python3 "$ROOT/platform/tooling/check-public-dispatch-surface.py" --root "$slash_title" >"$TMPDIR/slash-title.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected slash H1 title to fail\n' >&2
  exit 1
fi
expected_h1="H1 must be \`# (collab run)\`, found \`# ${slash_char}collab run\`"
if ! grep -Fq "$expected_h1" "$TMPDIR/slash-title.out"; then
  printf 'FAIL: slash H1 output did not name title mismatch\n' >&2
  cat "$TMPDIR/slash-title.out" >&2
  exit 1
fi

slash="$TMPDIR/slash"
make_fixture "$slash"
printf '\n- **Regression:** Run `%scollab run` next.\n' "$slash_char" >>"$slash/commands/collab/run/index.md"
set +e
python3 "$ROOT/platform/tooling/check-public-dispatch-surface.py" --root "$slash" >"$TMPDIR/slash.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected public slash trigger prose to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'tracked slash command invocation is forbidden' "$TMPDIR/slash.out"; then
  printf 'FAIL: slash trigger output did not name forbidden slash command\n' >&2
  cat "$TMPDIR/slash.out" >&2
  exit 1
fi

runtime="$TMPDIR/runtime"
make_fixture "$runtime"
mkdir -p "$runtime/commands/collab/engine"
printf 'print("%scollab run plan")\n' "$slash_char" >"$runtime/commands/collab/engine/registry.py"
set +e
python3 "$ROOT/platform/tooling/check-public-dispatch-surface.py" --root "$runtime" >"$TMPDIR/runtime.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected runtime slash output string to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'commands/collab/engine/registry.py:1: tracked slash command invocation is forbidden' "$TMPDIR/runtime.out"; then
  printf 'FAIL: runtime output did not name forbidden slash command\n' >&2
  cat "$TMPDIR/runtime.out" >&2
  exit 1
fi

printf 'OK: public dispatch surface guard rejects drift and slash regressions\n'
