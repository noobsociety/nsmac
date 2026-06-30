#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR_BASE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

GATE="$ROOT/platform/tooling/audit-reachability.sh"

_scaffold() {
  local dir="$1"
  mkdir -p "$dir/commands/ns" "$dir/docs" "$dir/platform/tooling"
  printf '# Router\n' >"$dir/commands/ns/index.md"
}

# --- Test 1: linked doc is reachable ----------------------------------------
linked="$TMPDIR_BASE/linked"
_scaffold "$linked"
printf '# Target\n' >"$linked/docs/target.md"
printf '[target](../../docs/target.md)\n' >"$linked/commands/ns/index.md"

if ! COMMAND_CONFIG_ROOT="$linked" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: linked doc should be reachable\n' >&2
  exit 1
fi

# --- Test 2: orphaned doc is rejected ----------------------------------------
orphan="$TMPDIR_BASE/orphan"
_scaffold "$orphan"
printf '# Orphan\n' >"$orphan/docs/orphan.md"

if COMMAND_CONFIG_ROOT="$orphan" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: orphaned doc should be rejected\n' >&2
  exit 1
fi

out="$(COMMAND_CONFIG_ROOT="$orphan" "$GATE" 2>&1 || true)"
if ! printf '%s\n' "$out" | grep -q 'FAIL: unreachable tracked doc'; then
  printf 'FAIL: orphan error message not stable: %s\n' "$out" >&2
  exit 1
fi

# --- Test 3: bare inline-code reference does not satisfy reachability --------
inline="$TMPDIR_BASE/inline"
_scaffold "$inline"
printf '# Code-only\n' >"$inline/docs/code-only.md"
printf 'Use `code-only.md` for details.\n' >"$inline/commands/ns/index.md"

if COMMAND_CONFIG_ROOT="$inline" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: inline-code-only reference should not satisfy reachability\n' >&2
  exit 1
fi

# --- Test 4: # Contract: reference in .sh file satisfies reachability --------
contract="$TMPDIR_BASE/contract"
_scaffold "$contract"
printf '# Contract spec\n' >"$contract/platform/tooling/contract.md"
printf '#!/usr/bin/env bash\n# Contract: platform/tooling/contract.md\n' \
  >"$contract/platform/tooling/validator.sh"
printf '# Contract: platform/tooling/contract.md\n' \
  >"$contract/platform/tooling/validator.py"

if ! COMMAND_CONFIG_ROOT="$contract" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: # Contract: references should satisfy reachability\n' >&2
  exit 1
fi

# --- Test 5: outbound root contract references must resolve ------------------
outbound="$TMPDIR_BASE/outbound"
_scaffold "$outbound"
printf 'Authority references `rules/{auto,shared}.mdc`.\n' >"$outbound/REPOSITORY.md"

if COMMAND_CONFIG_ROOT="$outbound" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: missing outbound root contract reference should be rejected\n' >&2
  exit 1
fi

out="$(COMMAND_CONFIG_ROOT="$outbound" "$GATE" 2>&1 || true)"
if ! printf '%s\n' "$out" | grep -q 'FAIL: unresolved outbound contract reference: REPOSITORY.md:1: rules/{auto,shared}.mdc'; then
  printf 'FAIL: outbound reference error message not stable: %s\n' "$out" >&2
  exit 1
fi

# --- Test 6: brace-expanded outbound root references may resolve -------------
outbound_ok="$TMPDIR_BASE/outbound-ok"
_scaffold "$outbound_ok"
mkdir -p "$outbound_ok/platform/templates"
printf '# A\n' >"$outbound_ok/platform/templates/CLAUDE.md"
printf '# B\n' >"$outbound_ok/platform/templates/AGENTS.md"
printf '# C\n' >"$outbound_ok/platform/templates/REPOSITORY.md"
printf 'Templates: `platform/templates/{CLAUDE,AGENTS,REPOSITORY}.md`.\n' >"$outbound_ok/REPOSITORY.md"

if ! COMMAND_CONFIG_ROOT="$outbound_ok" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: resolved brace-expanded contract references should pass\n' >&2
  exit 1
fi

printf 'audit-reachability: all tests passed\n'
