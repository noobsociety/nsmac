#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

FAIL=0

# Verify synthesizers/ directory and sy.json artifact are absent
if [ -d "commands/collab/reference/synthesizers" ]; then
  printf 'FAIL: commands/collab/reference/synthesizers/ directory still exists\n' >&2
  FAIL=1
fi

if [ -f "commands/collab/reference/synthesizers/sy.json" ]; then
  printf 'FAIL: synthesizers/sy.json still exists\n' >&2
  FAIL=1
fi

# Verify projectors/ directory is absent (dp.json in roles/ is intentionally retained as non-joinable)
if [ -d "commands/collab/reference/projectors" ]; then
  printf 'FAIL: commands/collab/reference/projectors/ directory still exists\n' >&2
  FAIL=1
fi

if [ -f "commands/collab/reference/projectors/dp.json" ]; then
  printf 'FAIL: projectors/dp.json still exists\n' >&2
  FAIL=1
fi

# Verify no Synthesizer role identity prose in live doc surfaces
# Excludes: engine code (implementation), records/ (audit ledger, Inv #2)
# Note: dp.json in roles/ is an intentional non-joinable stub and is exempt
SYNTHESIZER_HITS=$(git grep -nP '\bSynthesizer\b' \
  -- 'commands/' 'platform/standards/' \
  ':(exclude)commands/collab/engine/' \
  ':(exclude)records/' \
  ':(exclude)commands/collab/reference/roles/' \
  2>/dev/null || true)

if [ -n "$SYNTHESIZER_HITS" ]; then
  printf 'FAIL: Synthesizer role identity prose found in live surfaces:\n%s\n' "$SYNTHESIZER_HITS" >&2
  FAIL=1
fi

[ "$FAIL" -eq 0 ] && printf 'OK: sy/dp role artifacts absent and identity prose clean on live surfaces\n'
exit "$FAIL"
