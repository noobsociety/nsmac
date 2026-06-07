#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

fixture="$TMPDIR/fixture"
mkdir -p "$fixture/commands/demo/run"
cat >"$fixture/commands/commands.md" <<'MD'
# /commands

<!-- BEGIN GENERATED:COMMANDS_ROSTER -->
stale
<!-- END GENERATED:COMMANDS_ROSTER -->
MD
cat >"$fixture/commands/index.md" <<'MD'
# /commands

```route-flag
flag: force
eligibility: eligible
guard-class: system
```
MD
cat >"$fixture/commands/demo/index.md" <<'MD'
# /demo

**Signature:** `/demo <run>`

```route-flag
flag: force
eligibility: eligible
guard-class: namespace
override: system — namespace narrows force
```
MD
cat >"$fixture/commands/demo/run/index.md" <<'MD'
# /demo run

**Slash:** `/demo run`
**Signature:** `/demo run [--force]`

```route-flag
flag: force
eligibility: eligible
guard-class: command
override: namespace — command narrows force
```
MD

COMMAND_CONFIG_ROOT="$fixture" "$ROOT/platform/tooling/sync-commands-catalog.sh" >/dev/null
COMMAND_CONFIG_ROOT="$fixture" "$ROOT/platform/tooling/sync-commands-catalog.sh" --check >/dev/null
COMMAND_CONFIG_ROOT="$fixture" "$ROOT/platform/tooling/audit-flag-scope.sh" >/dev/null

if ! grep -Fq '| `/demo` | `/demo <run>` | [demo](demo/index.md) | [run](demo/run/index.md) |' "$fixture/commands/commands.md"; then
  printf 'FAIL: generated catalog did not discover namespace and command index.md entries\n' >&2
  cat "$fixture/commands/commands.md" >&2
  exit 1
fi
if grep -Fq '[commands](index.md)' "$fixture/commands/commands.md"; then
  printf 'FAIL: root commands/index.md was exposed as a public router\n' >&2
  cat "$fixture/commands/commands.md" >&2
  exit 1
fi
if grep -Fq '| `/commands` |' "$fixture/commands/commands.md"; then
  printf 'FAIL: root commands/index.md produced a slash roster row\n' >&2
  cat "$fixture/commands/commands.md" >&2
  exit 1
fi
if ! grep -Fq '| `/demo run` | [demo/run/index.md](demo/run/index.md) |' "$fixture/commands/commands.md"; then
  printf 'FAIL: generated route table did not link command index.md entry\n' >&2
  cat "$fixture/commands/commands.md" >&2
  exit 1
fi

printf 'OK: command catalog sync discovers index.md routes and preserves flag inheritance checks\n'
