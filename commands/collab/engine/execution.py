"""Execution helper checks, run-plan dispatch support, and write-scope enforcement."""
# Tests: touched-path enforcement against declared writeScope, disjoint-scope assertion for
#        subagent spawns, completion check across all assigned roles, execution-scope advisory.
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from commands.collab.engine.digests import (
    active_execution_entries,
    content_digest_for_touched_paths,
    execution_identity,
    execution_signature,
    touched_paths_for_execution,
)
from commands.collab.engine.errors import die
from commands.collab.engine.git_repo import (
    assert_touched_paths_recordable_in_work_repo,
    execution_commits_for_touched_paths,
    git_commit_paths,
    git_committed_deletion_paths,
    git_index_or_staged_paths,
    git_staged_paths,
    git_unstaged_paths,
    work_repo_root,
    working_tree_path_exists,
)
from commands.collab.engine.handoff_shape import handoff_state_for_role
from commands.collab.engine.normalizers import normalize_scope_path, normalize_touched_paths, path_is_within, scope_matches_declared
from commands.collab.engine.participants import (
    assert_caller_role,
    effective_turn_order,
    has_participant,
    reviewer_backed,
    reviewer_role,
    reviewer_state,
)
from commands.collab.engine.phase_lifecycle import lifecycle_status_notice
from commands.collab.engine.registry_constants import (
    ALLOWED_EXECUTION_STATUSES,
    ALLOWED_VALIDATION_SCOPES,
    CALLER_DECLINED_AGENT_ID,
)
from commands.collab.engine.registry_io import load_registry, registry_lock, resolve_collab, save_registry
from commands.collab.engine.transcript_readers import (
    completion_summary_empty,
    read_transcript_for_entry,
    transcript_path_for_entry,
    unchecked_assigned_item_count,
)


@dataclass(frozen=True)
class ExecutionCallbacks:
    seal_terminal: Callable[[dict], bool]
    issue_terminal: Callable[[dict], bool]
    close_eligible_after_execution: Callable[[dict, list[str]], bool]
    initialize_completion_state: Callable[..., None]
    invalidate_verification_seal: Callable[[dict, str], None]
    write_seal_verdict_companion: Callable[[Path, dict], Path | None]
    next_line_after_execution: Callable[[dict, list[str]], str]
    render_managed_header_text: Callable[[str, dict, Path], tuple[str, bool]]
    append_completion_summary: Callable[[str, str, str], str]
    default_close_summary: Callable[[dict], str]
    summary_date_from_timestamp: Callable[[str], str]
    print_header_overwrite: Callable[[bool], None]
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None]
    print_post_action_advisories: Callable[[dict, str | None, str | None, dict | None, str], None]
    print_notice_diagnostic: Callable[[dict | None, bool], None]

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
    from commands.collab.engine.digests import active_execution_entries

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
    from commands.collab.engine.digests import active_execution_entries

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


def assert_execution_touched_paths_in_git_state(entry: dict) -> None:
    touched = touched_paths_for_execution(entry)
    if not touched:
        return
    repo_root = work_repo_root(entry)
    in_git = git_index_or_staged_paths(touched, repo_root)
    staged = git_staged_paths(touched, repo_root)
    unstaged = git_unstaged_paths(touched, repo_root)
    committed_deletions = git_committed_deletion_paths(touched, repo_root)
    invalid: list[str] = []
    for path in touched:
        if path in staged or path in unstaged:
            invalid.append(path)
            continue
        if path in in_git:
            continue
        if path in committed_deletions and not working_tree_path_exists(path, repo_root):
            continue
        invalid.append(path)
    invalid = sorted(invalid)
    if invalid:
        die(
            'SEAL-GIT-STATE: implementation not in git; '
            f'unstaged or uncommitted touchedPath(s) in {repo_root}: {json.dumps(invalid, separators=(",", ":"))}'
        )


def record_execution_state(
    path: Path,
    target: str,
    role: str,
    status: str,
    date: str,
    assigned_roles: list[str],
    auto_close: bool,
    validation_result: str | None,
    validation_scope: str | None,
    touched_paths: list[str],
    callbacks: ExecutionCallbacks,
    roles_dir: Path,
    agent_id: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    if status not in ALLOWED_EXECUTION_STATUSES:
        die(f'execution status must be one of {sorted(ALLOWED_EXECUTION_STATUSES)}')
    if validation_scope and validation_scope not in ALLOWED_VALIDATION_SCOPES:
        die(f'execution validation scope must be one of {sorted(ALLOWED_VALIDATION_SCOPES)}')
    normalized_touched_paths = normalize_touched_paths(touched_paths)
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'execution', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if not has_participant(entry, role):
            die(f'execution role must already be a participant: {role}')
        if role == entry['moderatorRole']:
            die('execution role must not be the moderator')
        if reviewer_backed(entry) and reviewer_state(entry)['state'] != 'active':
            die(f'execution blocked: reviewer role is not active: {reviewer_role(entry)}')
        for assigned_role in assigned_roles:
            if not has_participant(entry, assigned_role):
                die(f'assigned role must already be a participant: {assigned_role}')
        transcript = read_transcript_for_entry(entry) if transcript_path_for_entry(entry).exists() else ''
        if status == 'completed' and entry['activePhase'] == 'Completion':
            unchecked_count = unchecked_assigned_item_count(transcript, role)
            if unchecked_count:
                die(
                    f'execution completed blocked for role {role}: '
                    f'{unchecked_count} unchecked assigned Action Plan item(s) remain; '
                    'loop target: Handoff for missing execution evidence'
                )
        assert_touched_paths_inside_handoff(entry, role, normalized_touched_paths)
        assert_touched_paths_recordable_in_work_repo(entry, normalized_touched_paths)

        execution_state = {'status': status, 'date': date}
        execution_state['entryId'] = execution_identity(role, date)
        commits = execution_commits_for_touched_paths(date, work_repo_root(entry), normalized_touched_paths)
        if commits:
            execution_state['commits'] = commits
        digest = content_digest_for_touched_paths(work_repo_root(entry), 'WORKTREE', normalized_touched_paths)
        execution_state['contentDigest'] = digest['contentDigest']
        execution_state['pathDigests'] = digest['pathDigests']
        if agent_id:
            execution_state['agentId'] = agent_id
        if validation_result:
            execution_state['validationResult'] = validation_result
        if validation_scope:
            execution_state['validationScope'] = validation_scope
        if normalized_touched_paths:
            execution_state['touchedPaths'] = normalized_touched_paths
        previous_signature = execution_signature(entry)
        entry.setdefault('execution', {})[role] = execution_state
        if callbacks.seal_terminal(entry) and reviewer_backed(entry) and previous_signature != execution_signature(entry):
            callbacks.invalidate_verification_seal(entry, f'execution changed for {role}')
            callbacks.write_seal_verdict_companion(path, entry)
        closed = False
        if callbacks.issue_terminal(entry) and entry['activePhase'] == 'Completion':
            if auto_close and callbacks.close_eligible_after_execution(entry, assigned_roles):
                entry['status'] = 'closed'
                closed = True
                if data.get('activeCollabId') == entry['id']:
                    data['activeCollabId'] = None
        elif callbacks.seal_terminal(entry) and reviewer_backed(entry) and entry['activePhase'] == 'Completion':
            if callbacks.close_eligible_after_execution(entry, assigned_roles):
                if auto_close:
                    entry['status'] = 'closed'
                    closed = True
                    if data.get('activeCollabId') == entry['id']:
                        data['activeCollabId'] = None
            else:
                effective_assigned = assigned_roles if assigned_roles else [
                    r for r in effective_turn_order(entry)
                    if r != entry['moderatorRole']
                ]
                if effective_assigned and all(
                    entry.get('execution', {}).get(r, {}).get('status') == 'completed'
                    for r in effective_assigned
                ):
                    callbacks.initialize_completion_state(entry, 'verification', reset_rounds=True)
                else:
                    callbacks.initialize_completion_state(entry, 'execution')
        elif auto_close and callbacks.close_eligible_after_execution(entry, assigned_roles):
            entry['status'] = 'closed'
            closed = True
            if data.get('activeCollabId') == entry['id']:
                data['activeCollabId'] = None

        notice = lifecycle_status_notice('closed') if closed else None
        next_line = callbacks.next_line_after_execution(entry, assigned_roles)
        transcript_path = transcript_path_for_entry(entry)
        if closed and transcript_path.exists():
            rendered, header_changed = callbacks.render_managed_header_text(transcript, entry, roles_dir)
            if completion_summary_empty(rendered):
                rendered = callbacks.append_completion_summary(
                    rendered,
                    callbacks.default_close_summary(entry),
                    callbacks.summary_date_from_timestamp(date),
                )
            callbacks.print_header_overwrite(header_changed)
            callbacks.commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    callbacks.print_post_action_advisories(entry, role, 'Completion', notice, next_line)
    print(entry['status'])
    callbacks.print_notice_diagnostic(notice, emit_json)
    return 0
