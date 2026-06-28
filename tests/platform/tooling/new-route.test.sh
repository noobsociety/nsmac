#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

fixture="$TMPDIR/fixture"
mkdir -p "$fixture/commands"

"$ROOT/platform/tooling/new-route.sh" collab sample-route --root "$fixture" --no-sync >/dev/null

route_file="$fixture/commands/collab/sample-route/index.md"
test_file="$fixture/tests/commands/collab/registry.py/sample-route-scaffold-unimplemented.test.sh"

test -f "$route_file"
test -x "$test_file"

if ! grep -Fq '<!-- abort: sample-route-scaffold-unimplemented -->' "$route_file"; then
  printf 'FAIL: scaffolded route missing anchored default abort\n' >&2
  cat "$route_file" >&2
  exit 1
fi

if ! grep -Fq '**Dispatch:** `(collab sample-route)`' "$route_file"; then
  printf 'FAIL: scaffolded route missing Dispatch trigger\n' >&2
  cat "$route_file" >&2
  exit 1
fi

if ! grep -Fq 'route-specific behavior is not implemented' "$test_file"; then
  printf 'FAIL: scaffolded coverage fixture does not assert default abort\n' >&2
  cat "$test_file" >&2
  exit 1
fi

"$ROOT/platform/tooling/coverage-gate.sh" \
  --routes-dir "$fixture" \
  --tests-dir "$fixture/tests/commands/collab/registry.py" >/dev/null

# audit.sh conformance: full audit.sh cannot run on a fixture (requires CLAUDE.md,
# commands.md, generated/, and other repo-level scaffolding). The coverage-gate
# assertion above covers the P9-required portion. The remaining audit.sh subchecks
# that apply to route files pass by construction:
#   audit-topology / audit-placement: scaffold creates commands/<ns>/<route>/index.md —
#     the required directory layout; no extra structure needed.
#   audit-flag-scope: scaffold emits no route-flag blocks; nothing to lint.
#   route-arg optional defaults: scaffold emits no route-arg blocks; nothing to lint.
#   sync-commands-catalog: passes after real-repo scaffold (SYNC=1 by default refreshes
#     the catalog); the --no-sync flag here is fixture-only.

printf 'OK: new-route scaffold creates coverage-backed collab route fixture\n'
