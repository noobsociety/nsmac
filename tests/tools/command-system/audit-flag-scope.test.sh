#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

write_flag_tree() {
  local root="$1" namespace_override="$2" command_override="$3"
  mkdir -p "$root/commands/demo/run"
  cat >"$root/commands/index.md" <<'MD'
# Commands

```route-flag
flag: force
eligibility: eligible
guard-class: global
```
MD
  cat >"$root/commands/demo/index.md" <<MD
# /demo

\`\`\`route-flag
flag: force
eligibility: eligible
guard-class: namespace
${namespace_override}
\`\`\`
MD
  cat >"$root/commands/demo/run/index.md" <<MD
# /demo run

\`\`\`route-flag
flag: force
eligibility: eligible
guard-class: command
${command_override}
\`\`\`
MD
}

missing="$TMPDIR/missing"
write_flag_tree "$missing" "" ""
set +e
COMMAND_CONFIG_ROOT="$missing" "$ROOT/tools/command-system/audit-flag-scope.sh" >"$TMPDIR/missing.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected silent shadowing to fail\n' >&2
  exit 1
fi
if ! grep -Fq "ERROR: flag '--force' at namespace scope shadows system scope without override declaration" "$TMPDIR/missing.out"; then
  printf 'FAIL: missing-override output did not name conflicting scopes\n' >&2
  cat "$TMPDIR/missing.out" >&2
  exit 1
fi

malformed="$TMPDIR/malformed"
write_flag_tree "$malformed" "override: system - bad delimiter" "override: namespace — command narrows behavior"
set +e
COMMAND_CONFIG_ROOT="$malformed" "$ROOT/tools/command-system/audit-flag-scope.sh" >"$TMPDIR/malformed.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected hyphen delimiter to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'required form: override: system — <reason>' "$TMPDIR/malformed.out"; then
  printf 'FAIL: malformed output did not require em-dash delimiter\n' >&2
  cat "$TMPDIR/malformed.out" >&2
  exit 1
fi

clean="$TMPDIR/clean"
write_flag_tree "$clean" "override: system — namespace narrows force" "override: namespace — command narrows force"
COMMAND_CONFIG_ROOT="$clean" "$ROOT/tools/command-system/audit-flag-scope.sh" >/dev/null

printf 'OK: flag-scope audit rejects silent shadowing and enforces em-dash overrides\n'
