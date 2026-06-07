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

python3 platform/tooling/command-advisories.py --check >/dev/null
python3 platform/tooling/command-reference.py --check >/dev/null

if ! grep -Fq '> **Recommended:** execution capability; high effort' generated/command-reference.md; then
  printf 'FAIL: generated command reference does not render advisory lines\n' >&2
  exit 1
fi

cp -R platform/data "$TMPDIR/unknown-alias"
python3 - "$TMPDIR/unknown-alias/advisories/agent.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["advisories"][0]["capabilityTier"] = "missing"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
assert_fails_with "unknown capabilityTier: missing" \
  python3 platform/tooling/command-advisories.py --check --data-dir "$TMPDIR/unknown-alias"

cp -R platform/data "$TMPDIR/flat-override"
python3 - "$TMPDIR/flat-override/advisories/agent.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["advisories"].append({
    "route": "install",
    "role": "pe",
    "capabilityTier": "execution",
    "effortTier": "high",
    "rationale": "Fixture role override intentionally duplicates the route default.",
})
path.write_text(json.dumps(data, indent=2) + "\n")
PY
assert_fails_with "must differ from the route default capabilityTier or effortTier" \
  python3 platform/tooling/command-advisories.py --check --data-dir "$TMPDIR/flat-override"

cp -R platform/data "$TMPDIR/missing-coverage-decision"
python3 - "$TMPDIR/missing-coverage-decision/command-advisory-policy.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["namespaceCoverageExemptions"].pop("doc")
path.write_text(json.dumps(data, indent=2) + "\n")
PY
assert_fails_with "advisory coverage policy lacks namespace decision(s): doc" \
  python3 platform/tooling/command-advisories.py --check --data-dir "$TMPDIR/missing-coverage-decision"

cp -R platform/data "$TMPDIR/required-without-file"
python3 - "$TMPDIR/required-without-file/command-advisory-policy.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["namespaceCoverageExemptions"].pop("doc")
data["requiredNamespaces"].append("doc")
path.write_text(json.dumps(data, indent=2) + "\n")
PY
assert_fails_with "missing required advisory namespace file(s): doc" \
  python3 platform/tooling/command-advisories.py --check --data-dir "$TMPDIR/required-without-file"

python3 - "$ROOT/generated/command-reference.md" "$TMPDIR/leaky-command-reference.md" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text()
target.write_text(
    text.replace(
        "<!-- END GENERATED:COMMAND_REFERENCE -->",
        "> **Recommended:** execution capability; high effort - runtimePolicyRef opus\n<!-- END GENERATED:COMMAND_REFERENCE -->",
    )
)
PY
assert_fails_with "runtimePolicyRef" \
  python3 platform/tooling/command-advisories.py --check --artifact "$TMPDIR/leaky-command-reference.md"

cp -R platform/data "$TMPDIR/extra-model-token-data"
python3 - "$TMPDIR/extra-model-token-data/command-advisory-policy.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["modelOrHarnessLeakageTerms"].append("aurora")
path.write_text(json.dumps(data, indent=2) + "\n")
PY
python3 - "$ROOT/generated/command-reference.md" "$TMPDIR/aurora-command-reference.md" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text()
target.write_text(
    text.replace(
        "<!-- END GENERATED:COMMAND_REFERENCE -->",
        "> **Recommended:** execution capability; high effort - aurora family leak\n<!-- END GENERATED:COMMAND_REFERENCE -->",
    )
)
PY
assert_fails_with "model term 'aurora'" \
  python3 platform/tooling/command-advisories.py --check \
    --data-dir "$TMPDIR/extra-model-token-data" \
    --artifact "$TMPDIR/aurora-command-reference.md"

printf 'OK: command advisory validation enforces coverage, aliases, overrides, and render leakage\n'
