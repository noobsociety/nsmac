#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR_BASE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

GATE="$ROOT/tools/command-system/audit-reachability.sh"

_scaffold() {
  local dir="$1"
  mkdir -p "$dir/commands/ns" "$dir/core/collab" "$dir/tools/command-system"
  printf '# Router\n' >"$dir/commands/ns/index.md"
}

# --- Test 1: linked doc is reachable ----------------------------------------
linked="$TMPDIR_BASE/linked"
_scaffold "$linked"
printf '# Target\n' >"$linked/core/collab/target.md"
printf '[target](../../core/collab/target.md)\n' >"$linked/commands/ns/index.md"

if ! COMMAND_CONFIG_ROOT="$linked" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: linked doc should be reachable\n' >&2
  exit 1
fi

# --- Test 2: orphaned doc is rejected ----------------------------------------
orphan="$TMPDIR_BASE/orphan"
_scaffold "$orphan"
printf '# Orphan\n' >"$orphan/core/collab/orphan.md"

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
printf '# Code-only\n' >"$inline/core/collab/code-only.md"
printf 'Use `code-only.md` for details.\n' >"$inline/commands/ns/index.md"

if COMMAND_CONFIG_ROOT="$inline" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: inline-code-only reference should not satisfy reachability\n' >&2
  exit 1
fi

# --- Test 4: # Contract: reference in .sh file satisfies reachability --------
contract="$TMPDIR_BASE/contract"
_scaffold "$contract"
printf '# Contract spec\n' >"$contract/tools/command-system/contract.md"
printf '#!/usr/bin/env bash\n# Contract: tools/command-system/contract.md\n' \
  >"$contract/tools/command-system/validator.sh"

if ! COMMAND_CONFIG_ROOT="$contract" "$GATE" >/dev/null 2>&1; then
  printf 'FAIL: # Contract: reference should satisfy reachability\n' >&2
  exit 1
fi

printf 'audit-reachability: all tests passed\n'
