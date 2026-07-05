#!/usr/bin/env python3
"""Integrity repair command handlers.

Owns `transcript-repair`, `out-of-scope-patch`, and
`repair-execution-provenance` command bodies. Seal invalidation stays owned by
`seal_verification_logic`; registry persistence stays owned by `registry_io`.
"""
from __future__ import annotations

from pathlib import Path

from commands.collab.engine.digests import execution_signature
from commands.collab.engine.errors import die
from commands.collab.engine.git_repo import (
    assert_touched_paths_recordable_in_work_repo,
    assert_work_repo_not_framework_for_external_project,
    git_commit_paths,
    resolve_git_work_tree,
    work_repo_root,
)
from commands.collab.engine.handoff_shape import handoff_state_for_role
from commands.collab.engine.normalizers import normalize_scope_path, scope_matches_declared
from commands.collab.engine.participants import (
    assert_caller_role,
    effective_turn_order,
    has_participant,
)
from commands.collab.engine.post_execution import next_line_after_execution
from commands.collab.engine.registry_io import (
    load_registry,
    registry_lock,
    resolve_collab,
    save_registry,
)
from commands.collab.engine.seal_verification_logic import (
    content_digest_for_execution,
    invalidate_verification_seal,
)


def transcript_repair(
    path: Path,
    target: str,
    touch_execution_evidence: bool,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'set')
        if touch_execution_evidence:
            invalidate_verification_seal(entry, 'transcript repair touched execution evidence')
        save_registry(path, data)
    print('ok')
    return 0


def out_of_scope_patch(
    path: Path,
    target: str,
    role: str,
    patch_path: str,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'execution', role)
        if not has_participant(entry, role):
            die(f'execution role must already be a participant: {role}')
        normalized_path = normalize_scope_path(patch_path, 'path')
        handoff_state = handoff_state_for_role(entry, role)
        if handoff_state is None:
            die(f'handoff writeScope missing for role: {role}')
        if any(scope_matches_declared(normalized_path, declared) for declared in handoff_state['writeScope']):
            die(f'out-of-scope patch path is inside declared writeScope: {normalized_path}')
        invalidate_verification_seal(entry, f'out-of-scope patch outside declared writeScope: {normalized_path}')
        save_registry(path, data)
    print('ok')
    return 0


def repair_execution_provenance(
    path: Path,
    target: str,
    role: str,
    work_repo: str | None,
    commits: list[str],
    caller_role: str | None = None,
) -> int:
    if work_repo is None and not commits:
        die('repair-execution-provenance requires --work-repo or --commit')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'rewrite-execution', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        execution = entry.get('execution', {}).get(role)
        if not isinstance(execution, dict):
            die(f'no execution record for role: {role}')
        if execution.get('status') != 'completed':
            die(f'execution provenance repair requires completed execution for role: {role}')
        if work_repo is not None:
            repo_root = resolve_git_work_tree(work_repo, 'workRepo')
            assert_work_repo_not_framework_for_external_project(repo_root, 'workRepo')
            entry['workRepo'] = str(repo_root)
        repo_root = work_repo_root(entry)
        provenance_changed = work_repo is not None or bool(commits)
        if commits:
            normalized_commits: list[str] = []
            for commit in commits:
                if not isinstance(commit, str) or not commit.strip():
                    die('repair-execution-provenance --commit requires non-empty commit ids')
                if git_commit_paths(commit, repo_root) is None:
                    die(f'repair-execution-provenance commit not found in workRepo {repo_root}: {commit}')
                if commit not in normalized_commits:
                    normalized_commits.append(commit)
            execution['commits'] = normalized_commits
        touched = [
            item
            for item in execution.get('touchedPaths', [])
            if isinstance(item, str) and item.strip()
        ]
        assert_touched_paths_recordable_in_work_repo(entry, touched)
        if provenance_changed:
            digest = content_digest_for_execution(entry)
            execution['contentDigest'] = digest['contentDigest']
            execution['pathDigests'] = digest['pathDigests']
        verification = entry.get('verification')
        if isinstance(verification, dict) and verification.get('pairedExecutionSignature') is not None:
            verification['pairedExecutionSignature'] = execution_signature(entry)
        invalidate_verification_seal(entry, f'execution provenance repaired for {role}')
        save_registry(path, data)
    print(next_line_after_execution(entry, effective_turn_order(entry)))
    print(entry['status'])
    return 0
