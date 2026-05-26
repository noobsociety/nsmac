#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

ROLE=pe
RUN_DATE="$(date +%Y-%m-%d)"

state_file() {
  local project="$1"
  printf '%s/.revamps/%s-%s.json' "$project" "$(basename "$project")" "$RUN_DATE"
}

run_helper() {
  local project="$1"
  shift
  (
    cd "$project"
    "$ROOT/tools/narrative/state.py" "$@"
  )
}

make_project() {
  local name="$1"
  local project="$TMPDIR/$name"
  mkdir -p "$project"
  printf './tests/run.sh\n' >"$project/REPOSITORY.md"
  run_helper "$project" audit --role "$ROLE" >/dev/null
  printf '%s\n' "$project"
}

write_artifacts() {
  local project="$1"
  python3 - "$ROOT" "$project" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
project = Path(sys.argv[2])
role = json.loads((root / "core/collab/roles" / "pe.json").read_text())

doc = project / "docs/topic.md"
doc.parent.mkdir(parents=True, exist_ok=True)
doc.write_text("before\n")
baseline = hashlib.sha256(doc.read_bytes()).hexdigest()

audit = {
    "driftThemes": [{"theme": "fixture", "evidence": "docs/topic.md"}],
    "styleViolations": [],
    "recommendedScope": "path",
    "filesToEdit": [{"path": "docs/topic.md", "reason": "fixture"}],
    "auditScopeBaseline": [{"path": "docs/topic.md", "hash": baseline}],
    "coveredConcerns": role["concerns"],
}
audit_missing = dict(audit)
audit_missing["coveredConcerns"] = role["concerns"][:-1]
align = {
    "aligned": [],
    "mismatched": [],
    "missingLocally": [],
    "missingGlobally": [],
    "coveredConcerns": role["concerns"],
}
for name, data in {
    "audit.json": audit,
    "audit-missing.json": audit_missing,
    "align.json": align,
}.items():
    (project / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
}

assert_json_field() {
  local path="$1"
  local expr="$2"
  python3 - "$path" "$expr" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
if not eval(sys.argv[2], {"data": data}):
    raise SystemExit(f"assertion failed: {sys.argv[2]}\n{json.dumps(data, indent=2, sort_keys=True)}")
PY
}

project="$(make_project ingestion)"
write_artifacts "$project"

set +e
run_helper "$project" record audit --role "$ROLE" --artifact "$project/audit-missing.json" >"$TMPDIR/audit-missing.out" 2>"$TMPDIR/audit-missing.err"
status=$?
set -e
if [[ "$status" -ne 1 ]]; then
  printf 'expected missing audit concern record to fail, got %s\n' "$status" >&2
  cat "$TMPDIR/audit-missing.out" >&2
  cat "$TMPDIR/audit-missing.err" >&2
  exit 1
fi
assert_json_field "$TMPDIR/audit-missing.out" 'data["coverage"]["status"] == "fail" and data["coverage"]["missing"]'
assert_json_field "$(state_file "$project")" 'data["phaseOutputs"]["audit"]["coveredConcerns"]'

run_helper "$project" record audit --role "$ROLE" --artifact "$project/audit.json" >"$TMPDIR/audit.out"
assert_json_field "$TMPDIR/audit.out" 'data["coverage"]["status"] == "pass"'

run_helper "$project" record align --role "$ROLE" --artifact "$project/align.json" >"$TMPDIR/align.out"
assert_json_field "$TMPDIR/align.out" 'data["coverage"]["status"] == "pass"'

set +e
run_helper "$project" gate --role "$ROLE" >"$TMPDIR/gate-fail.out" 2>"$TMPDIR/gate-fail.err"
status=$?
set -e
if [[ "$status" -ne 1 ]]; then
  printf 'expected unchanged ingested audit scope to fail gate, got %s\n' "$status" >&2
  cat "$TMPDIR/gate-fail.out" >&2
  cat "$TMPDIR/gate-fail.err" >&2
  exit 1
fi
assert_json_field "$TMPDIR/gate-fail.out" 'data["result"] == "fail" and any(item.get("type") == "unresolved-audit-scope" for item in data["failuresOrBlockers"])'

printf 'after\n' >"$project/docs/topic.md"
run_helper "$project" gate --role "$ROLE" >"$TMPDIR/gate-pass.out"
assert_json_field "$TMPDIR/gate-pass.out" 'data["result"] == "pass"'

missing_project="$(make_project missing-concern)"
write_artifacts "$missing_project"
run_helper "$missing_project" record audit --role "$ROLE" --artifact "$missing_project/audit-missing.json" >/dev/null || true
run_helper "$missing_project" record align --role "$ROLE" --artifact "$missing_project/align.json" >/dev/null

set +e
run_helper "$missing_project" gate --role "$ROLE" >"$TMPDIR/gate-coverage.out" 2>"$TMPDIR/gate-coverage.err"
status=$?
set -e
if [[ "$status" -ne 1 ]]; then
  printf 'expected missing coveredConcerns to block gate, got %s\n' "$status" >&2
  cat "$TMPDIR/gate-coverage.out" >&2
  cat "$TMPDIR/gate-coverage.err" >&2
  exit 1
fi
assert_json_field "$TMPDIR/gate-coverage.out" 'data["result"] == "blocked" and any(item.get("type") == "audit-concern-coverage" for item in data["failuresOrBlockers"])'

guard_home="$TMPDIR/home"
runtime_dir=".$(printf 'cur%s' 'sor')"
guard_root="$guard_home/$runtime_dir"
mkdir -p "$guard_root"
printf './tests/run.sh\n' >"$guard_root/REPOSITORY.md"
HOME="$guard_home" run_helper "$guard_root" audit --role "$ROLE" >/dev/null
set +e
HOME="$guard_home" run_helper "$guard_root" align --role "$ROLE" >"$TMPDIR/guard.out" 2>"$TMPDIR/guard.err"
status=$?
set -e
if [[ "$status" -ne 1 ]]; then
  printf 'expected align runtime/source guard to abort, got %s\n' "$status" >&2
  cat "$TMPDIR/guard.out" >&2
  cat "$TMPDIR/guard.err" >&2
  exit 1
fi
guard_expected="$(python3 - "$guard_root" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"
if ! grep -Fq "ABORT: runtime/source guard failed: $guard_expected" "$TMPDIR/guard.err"; then
  cat "$TMPDIR/guard.err" >&2
  exit 1
fi

printf 'OK: narrative artifacts ingest into state and gate fails before passing with real scope changes\n'
