#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


class StateError(Exception):
    pass


def state_path(repo_root: Path) -> Path:
    return repo_root / ".revamps" / f"{repo_root.name}-{date.today().isoformat()}.json"


def load_role(role_key: str) -> dict[str, Any]:
    path = ROOT / "core/collab/roles" / f"{role_key}.json"
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise StateError(f"role file unreadable: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"invalid role JSON: {path}: {exc}") from exc

    if data.get("key") != role_key:
        raise StateError(f"invalid role JSON: {path}: key")
    if not isinstance(data.get("displayName"), str) or not data["displayName"]:
        raise StateError(f"invalid role JSON: {path}: displayName")
    if not isinstance(data.get("concerns"), list) or not data["concerns"]:
        raise StateError(f"invalid role JSON: {path}: concerns")
    if not all(isinstance(item, str) and item for item in data["concerns"]):
        raise StateError(f"invalid role JSON: {path}: concerns")
    return data


def read_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise StateError(f"state file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"state file malformed: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StateError(f"state file malformed: {path}: root object")
    return data


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def role_update(state: dict[str, Any], stage: str, role: dict[str, Any]) -> None:
    state.setdefault("roleBindings", {})[stage] = role["key"]
    state.setdefault("concernRequirements", {})[stage] = list(role["concerns"])
    state["activeStage"] = stage


def repo_root_from_state(state: dict[str, Any], cwd: Path) -> Path:
    value = state.get("repoRoot")
    if isinstance(value, str) and value:
        return Path(value).expanduser().resolve()
    return cwd.resolve()


def discover_validation_commands(repo_root: Path) -> list[list[str]]:
    repository = repo_root / "REPOSITORY.md"
    if repository.exists():
        text = repository.read_text(errors="replace")
        commands: list[list[str]] = []
        for candidate in (
            "./tools/command-system/audit.sh",
            "./tools/command-system/sync-commands-catalog.sh --check",
            "./tools/command-system/sync-framework-boundaries.sh",
            "./tools/command-system/sync-roles-roster.sh",
            "./tests/run.sh",
        ):
            if candidate in text:
                commands.append(candidate.split())
        if commands:
            return commands

    package_json = repo_root / "package.json"
    if package_json.exists():
        try:
            package = json.loads(package_json.read_text())
        except json.JSONDecodeError:
            package = {}
        scripts = package.get("scripts")
        if isinstance(scripts, dict) and "test" in scripts:
            return [["npm", "test"]]

    tools_dir = repo_root / "tools"
    if tools_dir.is_dir():
        for script in sorted(tools_dir.rglob("*.sh")):
            if os.access(script, os.X_OK):
                return [[f"./{script.relative_to(repo_root).as_posix()}"]]
    return []


def ensure_state_base(state: dict[str, Any], repo_root: Path) -> None:
    state.setdefault("repoRoot", str(repo_root))
    state.setdefault("narrativeGlobs", ["**/*.md", "**/*.mdc"])
    state.setdefault("roleBindings", {})
    state.setdefault("concernRequirements", {})
    state.setdefault("phaseOutputs", {})


def parse_path_entries(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                paths.append(item)
            elif isinstance(item, dict):
                raw = item.get("path") or item.get("file") or item.get("target")
                if isinstance(raw, str):
                    paths.append(raw)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict):
                raw = item.get("path") or item.get("file") or key
                if isinstance(raw, str):
                    paths.append(raw)
            elif isinstance(key, str):
                paths.append(key)
    return paths


def parse_baseline_entries(value: Any) -> list[dict[str, str | None]]:
    entries: list[dict[str, str | None]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str):
                entries.append({"path": key, "hash": item})
            elif isinstance(item, dict):
                raw_path = item.get("path") or item.get("file") or key
                raw_hash = first_string(
                    item,
                    "hash",
                    "sha256",
                    "digest",
                    "blobHash",
                    "contentHash",
                    "baseline",
                    "baselineHash",
                )
                if isinstance(raw_path, str):
                    entries.append({"path": raw_path, "hash": raw_hash})
            elif isinstance(key, str):
                entries.append({"path": key, "hash": None})
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                entries.append({"path": item, "hash": None})
            elif isinstance(item, dict):
                raw_path = item.get("path") or item.get("file") or item.get("target")
                raw_hash = first_string(
                    item,
                    "hash",
                    "sha256",
                    "digest",
                    "blobHash",
                    "contentHash",
                    "baseline",
                    "baselineHash",
                )
                if isinstance(raw_path, str):
                    entries.append({"path": raw_path, "hash": raw_hash})
    return entries


def first_string(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str):
            return value
    return None


def normalize_hash(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower()
    for prefix in ("sha256:", "sha1:", "git:", "blob:"):
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :]
            break
    return lowered


def file_hashes(path: Path) -> set[str]:
    data = path.read_bytes()
    git_blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return {hashlib.sha256(data).hexdigest(), hashlib.sha1(git_blob).hexdigest()}


def resolve_scope_path(repo_root: Path, raw: str) -> tuple[Path, str, bool]:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        rel = resolved.relative_to(repo_root)
    except ValueError:
        return resolved, resolved.as_posix(), False
    return resolved, rel.as_posix(), True


def acknowledged_paths(state: dict[str, Any], repo_root: Path) -> set[str]:
    raw = state.get("acknowledgedScope")
    paths: set[str] = set()
    if isinstance(raw, dict):
        iterable: list[Any] = list(raw.keys())
    elif isinstance(raw, list):
        iterable = raw
    else:
        iterable = []
    for item in iterable:
        if isinstance(item, str):
            _, normalized, _ = resolve_scope_path(repo_root, item)
            paths.add(item)
            paths.add(normalized)
        elif isinstance(item, dict):
            path = item.get("path") or item.get("file") or item.get("target")
            if isinstance(path, str):
                _, normalized, _ = resolve_scope_path(repo_root, path)
                paths.add(path)
                paths.add(normalized)
    return paths


def is_acknowledged(raw: str, normalized: str, acknowledged: set[str]) -> bool:
    return raw in acknowledged or normalized in acknowledged


def covered_values(phase_output: dict[str, Any]) -> set[str]:
    value = (
        phase_output.get("coveredConcerns")
        or phase_output.get("covered_concerns")
        or phase_output.get("Covered concerns")
    )
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def coverage_status(state: dict[str, Any], phase: str, output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"status": "malformed", "missing": []}
    required = state.get("concernRequirements", {}).get(phase, [])
    if not isinstance(required, list):
        return {"status": "malformed", "missing": []}
    missing = sorted({item for item in required if isinstance(item, str)} - covered_values(output))
    return {"status": "fail" if missing else "pass", "missing": missing}


def audit_phase_output(state: dict[str, Any]) -> Any:
    return state.get("phaseOutputs", {}).get("audit")


def align_phase_output(state: dict[str, Any]) -> Any:
    return state.get("phaseOutputs", {}).get("align")


def audit_baselines(audit_output: dict[str, Any]) -> list[dict[str, str | None]]:
    return parse_baseline_entries(
        audit_output.get("auditScopeBaseline")
        or audit_output.get("audit_scope_baseline")
        or audit_output.get("Audit scope baseline")
    )


def audit_legacy_paths(audit_output: dict[str, Any]) -> list[str]:
    return parse_path_entries(
        audit_output.get("filesToEdit")
        or audit_output.get("files_to_edit")
        or audit_output.get("Files to edit")
    )


def align_entries(align_output: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = align_output.get(key)
        if value is not None:
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                return [{"path": path, **(item if isinstance(item, dict) else {})} for path, item in value.items()]
            if isinstance(value, str):
                return [value]
    return []


def entry_path(entry: Any) -> str | None:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        value = entry.get("path") or entry.get("file") or entry.get("target")
        if isinstance(value, str):
            return value
    return None


def expected_hash(entry: Any) -> str | None:
    if isinstance(entry, dict):
        return first_string(entry, "expectedHash", "globalHash", "hash", "sha256", "digest", "contentHash")
    return None


def scope_item(path: str, classification: str, disposition: str, reason: str, failure: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": path,
        "classification": classification,
        "disposition": disposition,
        "reason": reason,
    }
    if failure:
        item["failure"] = failure
    return item


def evaluate_scope(state: dict[str, Any], repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    audit_output = audit_phase_output(state)
    align_output = align_phase_output(state)
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    acknowledged = acknowledged_paths(state, repo_root)

    if isinstance(audit_output, dict):
        baselined_paths: set[str] = set()
        for entry in audit_baselines(audit_output):
            raw_path = entry["path"]
            if not raw_path:
                continue
            path, normalized, in_repo = resolve_scope_path(repo_root, raw_path)
            baselined_paths.add(normalized)
            if is_acknowledged(raw_path, normalized, acknowledged):
                checks.append(scope_item(normalized, "acknowledged", "skipped", "explicit acknowledgement"))
                continue
            if not in_repo:
                checks.append(scope_item(normalized, "out-of-repo", "advisory", "path is outside repo root"))
                continue
            baseline = normalize_hash(entry.get("hash"))
            if baseline is None:
                checks.append(scope_item(normalized, "legacy-no-baseline", "advisory", "no baseline hash recorded"))
                continue
            if not path.exists():
                failures.append({"type": "unresolved-audit-scope", "path": normalized})
                checks.append(scope_item(normalized, "missing", "blocking", "audit-scoped path is missing", "unresolved-audit-scope"))
                continue
            if baseline in file_hashes(path):
                failures.append({"type": "unresolved-audit-scope", "path": normalized})
                checks.append(scope_item(normalized, "unchanged", "blocking", "content matches audit baseline", "unresolved-audit-scope"))
            else:
                checks.append(scope_item(normalized, "changed", "pass", "content differs from audit baseline"))

        for raw_path in audit_legacy_paths(audit_output):
            _, normalized, in_repo = resolve_scope_path(repo_root, raw_path)
            if normalized in baselined_paths or is_acknowledged(raw_path, normalized, acknowledged):
                continue
            classification = "legacy-no-baseline" if in_repo else "out-of-repo"
            reason = "filesToEdit path has no auditScopeBaseline entry" if in_repo else "path is outside repo root"
            checks.append(scope_item(normalized, classification, "advisory", reason))

    if isinstance(align_output, dict):
        for entry in align_entries(align_output, "mismatched", "Mismatched", "mismatch"):
            raw_path = entry_path(entry)
            if not raw_path:
                continue
            path, normalized, in_repo = resolve_scope_path(repo_root, raw_path)
            if is_acknowledged(raw_path, normalized, acknowledged):
                checks.append(scope_item(normalized, "acknowledged", "skipped", "explicit acknowledgement"))
                continue
            if not in_repo:
                checks.append(scope_item(normalized, "out-of-repo", "advisory", "path is outside repo root"))
                continue
            expected = normalize_hash(expected_hash(entry))
            if expected is not None and path.exists() and expected in file_hashes(path):
                checks.append(scope_item(normalized, "aligned", "pass", "content matches recorded expected hash"))
                continue
            failures.append({"type": "unresolved-align-mismatched", "path": normalized})
            checks.append(scope_item(normalized, "mismatched", "blocking", "align mismatch remains unresolved", "unresolved-align-mismatched"))

        for entry in align_entries(align_output, "missingLocally", "missing_locally", "Missing locally"):
            raw_path = entry_path(entry)
            if not raw_path:
                continue
            path, normalized, in_repo = resolve_scope_path(repo_root, raw_path)
            if is_acknowledged(raw_path, normalized, acknowledged):
                checks.append(scope_item(normalized, "acknowledged", "skipped", "explicit acknowledgement"))
                continue
            if not in_repo:
                checks.append(scope_item(normalized, "out-of-repo", "advisory", "path is outside repo root"))
                continue
            if path.exists():
                checks.append(scope_item(normalized, "changed", "pass", "missing local path now exists"))
            else:
                failures.append({"type": "unresolved-align-missing-locally", "path": normalized})
                checks.append(scope_item(normalized, "missing-locally", "blocking", "align missingLocally path was not created", "unresolved-align-missing-locally"))

    return checks, failures


def gate_artifact(state: dict[str, Any], repo_root: Path, role: dict[str, Any]) -> dict[str, Any]:
    audit_output = audit_phase_output(state)
    align_output = align_phase_output(state)
    audit_present = isinstance(audit_output, dict)
    align_present = isinstance(align_output, dict)
    audit_coverage = coverage_status(state, "audit", audit_output)
    align_coverage = coverage_status(state, "align", align_output)
    checks, failures = evaluate_scope(state, repo_root)
    blockers: list[dict[str, str]] = []
    if not audit_present:
        blockers.append({"type": "phaseOutputs.audit", "path": "phaseOutputs.audit"})
    if not align_present:
        blockers.append({"type": "phaseOutputs.align", "path": "phaseOutputs.align"})
    for phase, coverage in (("audit", audit_coverage), ("align", align_coverage)):
        for concern in coverage.get("missing", []):
            blockers.append({"type": f"{phase}-concern-coverage", "path": concern})

    validation_commands = state.get("validationCommands")
    if not isinstance(validation_commands, list) or not validation_commands:
        blockers.append({"type": "validationCommands", "path": "validationCommands"})
        validation_commands = []

    result = "pass"
    if blockers:
        result = "blocked"
    elif failures:
        result = "fail"

    return {
        "repoRoot": str(repo_root),
        "handoffVerification": {
            "auditPhaseOutputs": "present" if audit_present else "malformed",
            "alignPhaseOutputs": "present" if align_present else "malformed",
            "auditConcernCoverage": audit_coverage,
            "alignConcernCoverage": align_coverage,
        },
        "scopeCheck": checks,
        "sourceValidation": [
            {"command": command, "status": "not-run"}
            for command in validation_commands
            if isinstance(command, list) and all(isinstance(part, str) for part in command)
        ],
        "result": result,
        "failuresOrBlockers": blockers + failures,
        "coveredConcerns": list(role["concerns"]),
        "nextAction": "rerun gate after edits" if result == "fail" else "archive state" if result == "pass" else "act on recommended scope",
    }


def command_audit(args: argparse.Namespace) -> int:
    role = load_role(args.role)
    repo_root = Path.cwd().resolve()
    path = state_path(repo_root)
    state: dict[str, Any] = {}
    if path.exists() and args.rerun == "abort":
        raise StateError(f"state file exists: {path}; choose --rerun resume or --rerun replace")
    if path.exists() and args.rerun == "resume":
        state = read_state(path)
    ensure_state_base(state, repo_root)
    role_update(state, "audit", role)
    state["validationCommands"] = discover_validation_commands(repo_root)
    state.setdefault("phaseOutputs", {})["audit"] = {
        "driftThemes": [],
        "styleViolations": [],
        "recommendedScope": "path",
        "filesToEdit": [],
        "auditScopeBaseline": [],
        "coveredConcerns": list(role["concerns"]),
    }
    write_state(path, state)
    print(json.dumps({"statePath": str(path), "validationCommands": state["validationCommands"]}, indent=2, sort_keys=True))
    return 0


def command_align(args: argparse.Namespace) -> int:
    role = load_role(args.role)
    path = state_path(Path.cwd().resolve())
    state = read_state(path)
    repo_root = repo_root_from_state(state, Path.cwd())
    ensure_state_base(state, repo_root)
    if not isinstance(audit_phase_output(state), dict):
        raise StateError("phaseOutputs.audit missing or malformed")
    role_update(state, "align", role)
    state.setdefault("phaseOutputs", {})["align"] = {
        "aligned": [],
        "mismatched": [],
        "missingLocally": [],
        "missingGlobally": [],
        "coveredConcerns": list(role["concerns"]),
    }
    write_state(path, state)
    print(json.dumps({"statePath": str(path), "phaseOutputs.audit": "present"}, indent=2, sort_keys=True))
    return 0


def command_gate(args: argparse.Namespace) -> int:
    role = load_role(args.role)
    path = state_path(Path.cwd().resolve())
    state = read_state(path)
    repo_root = repo_root_from_state(state, Path.cwd())
    ensure_state_base(state, repo_root)
    role_update(state, "gate", role)
    artifact = gate_artifact(state, repo_root, role)
    state.setdefault("phaseOutputs", {})["gate"] = artifact
    write_state(path, state)
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if artifact["result"] == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Narrative rewrite state helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit")
    audit.add_argument("--role", required=True)
    audit.add_argument("--rerun", choices=("abort", "resume", "replace"), default="abort")
    audit.set_defaults(func=command_audit)

    align = subparsers.add_parser("align")
    align.add_argument("--role", required=True)
    align.set_defaults(func=command_align)

    gate = subparsers.add_parser("gate")
    gate.add_argument("--role", required=True)
    gate.set_defaults(func=command_gate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except StateError as exc:
        print(f"ABORT: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"ABORT: {exc}", file=sys.stderr)
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
