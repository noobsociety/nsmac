#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

ROLE=pe
RUN_DATE="$(date +%Y-%m-%d)"

run_gate() {
  local project="$1"
  local output="$2"
  (
    cd "$project"
    set +e
    "$ROOT/tools/narrative/state.py" gate --role "$ROLE" >"$output" 2>"$output.err"
    status=$?
    set -e
    printf '%s' "$status" >"$output.status"
  )
}

make_case() {
  local name="$1"
  local script="$2"
  local project="$TMPDIR/$name"
  mkdir -p "$project/.revamps"
  python3 - "$ROOT" "$project" "$RUN_DATE" "$script" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
project = Path(sys.argv[2])
run_date = sys.argv[3]
case = sys.argv[4]
role = json.loads((root / "_roles" / "pe.json").read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(rel: str, text: str) -> Path:
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


state = {
    "repoRoot": str(project),
    "activeStage": "align",
    "narrativeGlobs": ["**/*.md", "**/*.mdc"],
    "validationCommands": [["./tools/check.sh"]],
    "roleBindings": {"audit": "pe", "align": "pe"},
    "concernRequirements": {
        "audit": role["concerns"],
        "align": role["concerns"],
    },
    "phaseOutputs": {
        "audit": {
            "driftThemes": [{"theme": "fixture", "evidence": "fixture"}],
            "styleViolations": [],
            "recommendedScope": "path",
            "coveredConcerns": role["concerns"],
        },
        "align": {
            "aligned": [],
            "mismatched": [],
            "missingLocally": [],
            "missingGlobally": [],
            "coveredConcerns": role["concerns"],
        },
    },
}

if case == "unchanged":
    path = write("docs/topic.md", "unchanged\n")
    state["phaseOutputs"]["audit"]["auditScopeBaseline"] = [{"path": "docs/topic.md", "hash": digest(path)}]
elif case == "changed":
    path = write("docs/topic.md", "before\n")
    old_hash = digest(path)
    path.write_text("after\n")
    state["phaseOutputs"]["audit"]["auditScopeBaseline"] = [{"path": "docs/topic.md", "hash": old_hash}]
elif case == "missing_locally":
    state["phaseOutputs"]["audit"]["auditScopeBaseline"] = []
    state["phaseOutputs"]["align"]["missingLocally"] = [{"path": "rules/auto.mdc"}]
elif case == "acknowledged":
    path = write("docs/topic.md", "unchanged\n")
    state["phaseOutputs"]["audit"]["auditScopeBaseline"] = [{"path": "docs/topic.md", "hash": digest(path)}]
    state["acknowledgedScope"] = [{"path": "docs/topic.md", "reason": "accepted exception"}]
elif case == "out_of_repo":
    external = project.parent / "outside.md"
    external.write_text("outside\n")
    state["phaseOutputs"]["audit"]["auditScopeBaseline"] = [{"path": str(external), "hash": digest(external)}]
elif case == "legacy_files_to_edit":
    write("docs/topic.md", "legacy\n")
    state["phaseOutputs"]["audit"]["filesToEdit"] = [{"path": "docs/topic.md", "reason": "old state shape"}]
elif case == "mismatched":
    overlay_path = ".cur" "sor/rules/auto.mdc"
    path = write(overlay_path, "local\n")
    expected = hashlib.sha256(b"global\n").hexdigest()
    state["phaseOutputs"]["audit"]["auditScopeBaseline"] = []
    state["phaseOutputs"]["align"]["mismatched"] = [{"path": overlay_path, "expectedHash": expected}]
else:
    raise SystemExit(f"unknown case: {case}")

state_path = project / ".revamps" / f"{project.name}-{run_date}.json"
state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
PY
  printf '%s\n' "$project"
}

assert_result() {
  local output="$1"
  local expected_status="$2"
  local expected_result="$3"
  local expected_type="$4"
  local expected_disposition="$5"
  python3 - "$output" "$expected_status" "$expected_result" "$expected_type" "$expected_disposition" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
expected_status = int(sys.argv[2])
expected_result = sys.argv[3]
expected_type = sys.argv[4]
expected_disposition = sys.argv[5]
actual_status = int(output.with_suffix(output.suffix + ".status").read_text())
if actual_status != expected_status:
    raise SystemExit(f"status mismatch for {output}: {actual_status} != {expected_status}\n{output.read_text()}\n{output.with_suffix(output.suffix + '.err').read_text()}")
data = json.loads(output.read_text())
if data["result"] != expected_result:
    raise SystemExit(f"result mismatch for {output}: {data['result']} != {expected_result}")
types = {item.get("type") for item in data.get("failuresOrBlockers", [])}
if expected_type != "-" and expected_type not in types:
    raise SystemExit(f"missing failure type {expected_type}: {types}")
dispositions = {item.get("disposition") for item in data.get("scopeCheck", [])}
if expected_disposition != "-" and expected_disposition not in dispositions:
    raise SystemExit(f"missing disposition {expected_disposition}: {dispositions}")
if not data.get("sourceValidation") or data["sourceValidation"][0]["status"] != "not-run":
    raise SystemExit("gate helper should report validation commands without running them")
PY
}

assert_state_recorded() {
  local project="$1"
  python3 - "$project" "$RUN_DATE" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
run_date = sys.argv[2]
state = json.loads((project / ".revamps" / f"{project.name}-{run_date}.json").read_text())
assert state["activeStage"] == "gate"
assert state["roleBindings"]["gate"] == "pe"
assert "gate" in state["concernRequirements"]
assert "gate" in state["phaseOutputs"]
PY
}

unchanged="$(make_case unchanged unchanged)"
run_gate "$unchanged" "$TMPDIR/unchanged.json"
assert_result "$TMPDIR/unchanged.json" 1 fail unresolved-audit-scope blocking
assert_state_recorded "$unchanged"

changed="$(make_case changed changed)"
run_gate "$changed" "$TMPDIR/changed.json"
assert_result "$TMPDIR/changed.json" 0 pass - pass
assert_state_recorded "$changed"

missing="$(make_case missing missing_locally)"
run_gate "$missing" "$TMPDIR/missing.json"
assert_result "$TMPDIR/missing.json" 1 fail unresolved-align-missing-locally blocking
assert_state_recorded "$missing"

acknowledged="$(make_case acknowledged acknowledged)"
run_gate "$acknowledged" "$TMPDIR/acknowledged.json"
assert_result "$TMPDIR/acknowledged.json" 0 pass - skipped
assert_state_recorded "$acknowledged"

out_of_repo="$(make_case out-of-repo out_of_repo)"
run_gate "$out_of_repo" "$TMPDIR/out-of-repo.json"
assert_result "$TMPDIR/out-of-repo.json" 0 pass - advisory
assert_state_recorded "$out_of_repo"

legacy="$(make_case legacy legacy_files_to_edit)"
run_gate "$legacy" "$TMPDIR/legacy.json"
assert_result "$TMPDIR/legacy.json" 0 pass - advisory
assert_state_recorded "$legacy"

mismatched="$(make_case mismatched mismatched)"
run_gate "$mismatched" "$TMPDIR/mismatched.json"
assert_result "$TMPDIR/mismatched.json" 1 fail unresolved-align-mismatched blocking
assert_state_recorded "$mismatched"

printf 'OK: narrative gate enforces audit and align scope while preserving advisory compatibility cases\n'
