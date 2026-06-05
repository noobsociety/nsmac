"""Execution helper checks, run-plan dispatch support, and write-scope enforcement."""
# Tests: touched-path enforcement against declared writeScope, disjoint-scope assertion for
#        subagent spawns, completion check across all assigned roles, execution-scope advisory.
from __future__ import annotations

from pathlib import Path

from tools.collab.digests import active_execution_entries
from tools.collab.errors import die
from tools.collab.git_repo import git_commit_paths, work_repo_root
from tools.collab.handoff_shape import handoff_state_for_role
from tools.collab.normalizers import normalize_scope_path, path_is_within, scope_matches_declared
from tools.collab.participants import effective_turn_order, has_participant
from tools.collab.registry_constants import CALLER_DECLINED_AGENT_ID
from tools.collab.registry_io import load_registry, resolve_collab

def assert_disjoint_scopes(scopes: list[str]) -> None:
    if not scopes:
        die('execute-spawn requires at least one --scope')
    if len(scopes) != len(set(scopes)):
        die('execute-spawn scopes must be unique')
    for index, left in enumerate(scopes):
        for right in scopes[index + 1:]:
            if path_is_within(left, right) or path_is_within(right, left):
                die(f'execute-spawn scopes must be disjoint: {left} {right}')

def assert_touched_paths_inside_handoff(entry: dict, role: str, touched_paths: list[str]) -> None:
    if not touched_paths:
        return
    handoff_state = handoff_state_for_role(entry, role)
    if handoff_state is None:
        return
    declared_scopes = handoff_state['writeScope']
    for touched_path in touched_paths:
        if not any(scope_matches_declared(touched_path, declared) for declared in declared_scopes):
            die(f'execution touched path outside declared writeScope: {touched_path}')

def execute_spawn(
    path: Path,
    target: str,
    role: str,
    scope: str | None,
    sibling_scopes: list[str],
    returned_paths: list[str],
) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if entry['status'] in {'closed', 'archived'}:
        die('record is closed')
    if entry['activePhase'] != 'Completion':
        die('execute-spawn is valid only in Completion')
    if not has_participant(entry, role):
        die(f'execution role must already be a participant: {role}')
    if scope is None:
        die('execute-spawn requires --scope')
    normalized_scope = normalize_scope_path(scope, 'scope')
    normalized_siblings = [normalize_scope_path(item, 'sibling-scope') for item in sibling_scopes]
    normalized_scopes = [normalized_scope, *normalized_siblings]
    handoff_state = handoff_state_for_role(entry, role)
    if handoff_state is not None:
        declared_scopes = handoff_state['writeScope']
        for declared_scope in normalized_scopes:
            if not any(scope_matches_declared(declared_scope, declared) for declared in declared_scopes):
                die(f'execute-spawn scope outside declared writeScope: {declared_scope}')
    assert_disjoint_scopes(normalized_scopes)
    normalized_returned = [normalize_scope_path(item, 'returned-path') for item in returned_paths]
    for returned_path in normalized_returned:
        if not path_is_within(returned_path, normalized_scope):
            die(f'returned path outside assigned scope: {returned_path}')
    print('ok')
    return 0

def execution_scope_advisory(entry: dict) -> str | None:
    from tools.collab.digests import active_execution_entries

    # Non-gating diagnostic only. Commit metadata is retained as informational
    # provenance, so failures to resolve it are ignored rather than reported as a
    # seal error.
    repo_root = work_repo_root(entry)
    declared_paths: set[str] = set()
    committed_paths: set[str] = set()
    for execution in active_execution_entries(entry):
        role = execution.get('role')
        if not isinstance(role, str) or handoff_state_for_role(entry, role) is None:
            continue
        commits = [
            commit
            for commit in execution.get('commits', [])
            if isinstance(commit, str) and commit.strip()
        ]
        if not commits:
            continue
        for commit in commits:
            commit_paths = git_commit_paths(commit, repo_root)
            if commit_paths is None:
                continue
            committed_paths.update(commit_paths)
        declared_paths.update(
            item
            for item in execution.get('touchedPaths', [])
            if isinstance(item, str) and item.strip()
        )
    if not committed_paths:
        return None
    undeclared = sorted(committed_paths - declared_paths)
    if not undeclared:
        return None
    return 'ADVISORY-SCOPE: undeclared ' + ', '.join(undeclared)

def assert_no_execution_agent_conflation(entry: dict) -> None:
    from tools.collab.digests import active_execution_entries

    seen: dict[str, str] = {}
    for execution in active_execution_entries(entry):
        agent_id = execution.get('agentId')
        role = execution.get('role')
        if not isinstance(agent_id, str) or not agent_id.strip():
            continue
        if agent_id == CALLER_DECLINED_AGENT_ID:
            continue
        if agent_id in seen and seen[agent_id] != role:
            die(
                'PARTICIPANT-VERIFY-AGENT-CONFLATION: '
                f'roles {seen[agent_id]} and {role} share agentId {agent_id}'
            )
        if isinstance(role, str):
            seen[agent_id] = role

def all_execution_completed(entry: dict) -> bool:
    execution = entry.get('execution', {})
    roles = [role for role in effective_turn_order(entry) if role != entry['moderatorRole']]
    if not roles:
        return False
    return all(execution.get(role, {}).get('status') == 'completed' for role in roles)
