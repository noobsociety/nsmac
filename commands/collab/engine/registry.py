#!/usr/bin/env python3
"""Shared collab registry helper.

Import model: bare sibling imports inside ``commands/collab/engine/`` are intentional;
external callers invoke via ``commands.collab.engine.*`` module imports or the argv interface.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import webbrowser
from contextlib import contextmanager
from collections.abc import Callable
from copy import deepcopy
from pathlib import PurePosixPath
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
COMMAND_SYSTEM_DIR = ROOT / 'platform' / 'tooling'
if str(COMMAND_SYSTEM_DIR) not in sys.path:
    sys.path.insert(0, str(COMMAND_SYSTEM_DIR))

from roles import load_role, participant_row, role_catalog
from commands.collab.engine.errors import die, handoff_abort
from commands.collab.engine.transcript_readers import (
    ANCHOR_RE,
    CHARTERED_DELIVERABLES_LABEL,
    DETAILS_CLOSE_RE,
    DETAILS_OPEN_RE,
    completion_summary_empty,
    contribution_body_lines,
    contribution_is_retracted,
    contribution_roles,
    phase_section,
    read_transcript_for_entry,
    section_bounds,
    summary_role,
    transcript_path_for_entry,
)
from commands.collab.engine.planned_routes import validate_issue_bridge_block, validate_planned_route_prerequisites
from commands.collab.engine.registry_validation import validate_registry as validate_registry_data
from commands.collab.engine.effort import (
    audit_effort_matrix,
    effort_line,
    effort_value,
    load_effort_defaults,
)
from commands.collab.engine.contribution_validation import (
    MANDATORY_EFFORT_OVERRIDE_TURNS,
    action_plan_label_advisory,
    assert_turn_order_not_drifted,
    enforce_contribution_budget,
    polish_moderator_content,
    validate_action_plan_executable_scope,
    validate_action_plan_shape,
    validate_conclusion_directive_gap,
    validate_effort_override,
    validate_reviewer_conclusion_gates,
)
from commands.collab.engine.contribution_store import (
    contribution_store_path_for_entry,
    empty_contribution_store,
    mutable_contribution_store_for_entry,
    path_for_entry_target,
    write_contribution_store_for_entry,
)
from commands.collab.engine.registry_constants import (
    ACTIVE_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_CAP_EXITS,
    ALLOWED_COMPLETION_SUBSTATES,
    ALLOWED_EXECUTION_STATUSES,
    ALLOWED_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_REVIEWER_MODES,
    ALLOWED_SET_FIELDS,
    ALLOWED_STATUSES,
    ALLOWED_TERMINALS,
    ALLOWED_VALIDATION_SCOPES,
    ALLOWED_VERDICT_OUTCOMES,
    ALLOWED_VERDICT_RESTORE_TARGETS,
    ALLOWED_VERIFICATION_SUBSTATES,
    AUTO_ADVANCE_EXEMPT_PHASES,
    CALLER_DECLINED_AGENT_ID,
    CONTENT_ONLY_GUARD,
    CONVERGENT_REVIEWER_PHASES,
    CREATED_AT_REQUIRED_COLLAB_FIELDS,
    CREATED_AT_REQUIRED_REVIEWER_FIELDS,
    CREATED_AT_REQUIRED_VERIFICATION_FIELDS,
    DEFAULT_OPEN_ROSTER_EFFORT,
    DEFAULT_REVIEWER_MODE,
    DEFAULT_REVIEWER_OPTIONAL_PHASES,
    DEFAULT_TERMINAL,
    DEFAULT_VERIFICATION_CAP,
    DELETED_PATH_BLOB,
    DELETED_PATH_MODE,
    DISALLOWED_VERSION_FIELD,
    FORCE_ONLY_FIELDS,
    FULL_BODY_SUMMARY,
    GLOB_PATTERN_RE,
    HEADER_MANAGED_BEGIN,
    HEADER_MANAGED_END,
    INVALID_AGENT_ID_ALTERNATIVES,
    MAX_HANDOFF_SCOPE_COUNT,
    MAX_HANDOFF_SCOPE_LENGTH,
    MAX_VALIDATION_ARG_LENGTH,
    MAX_VALIDATION_COMMAND_ARGS,
    MAX_VALIDATION_COMMANDS,
    MOD_EXCLUDED_PHASES,
    MODERATOR_ONLY_ACTIONS,
    ONE_SPEAK_PHASES,
    PHASES,
    REGISTRY_EVENT_DIR,
    REGISTRY_EVENT_IGNORED_ROOT_KEYS,
    REGISTRY_EVENT_SCHEMA,
    RETIRED_ROOT_KEYS,
    SHELL_PATTERN_RE,
    STALE_LOCK_SECONDS,
    TERMINAL_CHOICES_MESSAGE,
)
from commands.collab.engine.registry_state import (
    assert_registry_project_binding,
    find_project_identity_path,
    project_metadata_from_identity,
    resolve_default_registry_path,
    sync_registry_project_metadata,
)
from commands.collab.engine import transcript_readers
from commands.collab.engine.diff import diff_result, render_diff
from commands.collab.engine.digests import (
    active_execution_entries,
    content_digest_for_touched_paths,
    details_block_end,
    execution_coverage_entries,
    execution_identity,
    execution_signature,
    full_body_signature_for_transcript,
    is_full_body_block_start,
    managed_full_body_blocks,
    participant_execution_signature,
    participant_write_scope_signature,
    touched_paths_for_execution,
    validation_scopes_for_execution,
)
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.execution import (
    ExecutionCallbacks,
    all_execution_completed,
    assert_disjoint_scopes,
    assert_execution_touched_paths_in_git_state,
    assert_no_execution_agent_conflation,
    assert_touched_paths_inside_handoff,
    execute_spawn,
    execution_scope_advisory,
    record_execution_state,
)
from commands.collab.engine.git_repo import (
    assert_touched_paths_recordable_in_work_repo,
    assert_work_repo_not_framework_for_external_project,
    current_head_commit,
    default_init_work_repo_root,
    enclosing_git_tree,
    execution_commits_for_touched_paths,
    git_commit_paths,
    git_committed_deletion_paths,
    git_index_or_staged_paths,
    git_latest_commit_for_path,
    git_staged_paths,
    git_unstaged_paths,
    resolve_git_work_tree,
    set_resolved_work_repo_root,
    work_repo_root,
    working_tree_path_exists,
)
from commands.collab.engine.handoff_shape import (
    effort_override_metadata_comment,
    handoff_field_sections,
    handoff_state_for_role,
    normalize_handoff_scope,
    normalize_validation_arg,
    normalize_validation_argv,
    normalize_validation_command_entry,
    normalize_validation_command_path,
    parse_handoff_content,
    parse_json_fragment,
    parse_validation_commands_section,
    parse_write_scope_section,
    render_content_for_transcript,
    set_handoff_state,
    validate_handoff_state,
    validate_handoff_validation_commands,
    validate_handoff_write_scope,
    validation_command_abort,
)
from commands.collab.engine.normalizers import (
    assert_one_line_nonempty,
    collab_date,
    display_title,
    format_banner_timestamp,
    format_timestamp,
    normalize_join_agent_id,
    normalize_restore_target,
    normalize_scope_path,
    normalize_slug,
    normalize_title,
    normalize_touched_paths,
    parse_execution_datetime,
    path_is_within,
    phase_slug,
    scope_matches_declared,
)
from commands.collab.engine.participants import (
    active_reviewer_role,
    add_participant_to_entry,
    assert_caller_role,
    count_caller_declined_agent_id_write,
    effective_turn_order,
    expected_speaker,
    has_participant,
    normalize_turn_order_for_phase,
    optional_reviewer_allowed_at_round_boundary,
    participant_agent_id,
    participant_roles,
    parse_reviewer_optional_phases,
    pending_reviewer_role,
    remove_moderator_from_turn_order,
    reviewer_backed,
    reviewer_mode,
    reviewer_optional_for_phase,
    reviewer_optional_phases,
    reviewer_required_for_phase,
    reviewer_role,
    reviewer_state,
    validate_participant_role_files,
)
from commands.collab.engine.phase_lifecycle import (
    PhaseLifecycleCallbacks,
    advance_phase_state,
    discussion_turn_notice,
    lifecycle_status_notice,
    next_phase_name,
    notice_message,
    print_lifecycle_diagnostic,
    print_notice_diagnostic,
    print_phase_result,
    transition_notice,
)
from commands.collab.engine.registry_io import (
    bump_registry_event_index,
    bump_registry_revision,
    capture_registry_project,
    collab_ids_by_id,
    configure_registry_io,
    current_registry_project_id,
    ensure_legacy_revision_baselines,
    finalize_registry_event,
    load_registry,
    load_registry_or_bootstrap,
    parse_registry_before,
    prepare_registry_event,
    read_revision_events,
    registry_event_collab_id,
    registry_event_index,
    registry_has_semantic_change,
    registry_lock,
    registry_revision,
    registry_semantic_snapshot,
    require_active_collab,
    retire_legacy_registry_fields,
    resolve_collab,
    revision_event_dir,
    revision_event_root,
    root_project_id,
    save_registry,
    write_json_if_absent,
    write_revision_event,
)
from commands.collab.engine.transcript_render import (
    append_phase_block,
    insert_toc_entry,
    print_header_overwrite,
    excerpt_source,
    stance_for_content,
    prepend_revision_history,
    reject_full_body_details_controls,
    reject_hand_authored_excerpt_details,
    render_contribution_block,
    render_contribution_body,
    render_initial_transcript,
    render_initial_transcript_legacy,
    render_managed_header_text,
    rendered_collapsible_block,
    rendered_retracted_content_block,
    revision_history_start,
)
from commands.collab.engine import seal_verification as _seal_verification
from commands.collab.engine.seal_verification import (
    append_completion_history_line,
    append_completion_summary,
    append_participant_verify_block,
    append_reviewer_findings_block,
    apply_cap_exit,
    assessment_next_line,
    assessment_notice,
    build_verdict,
    chartered_deliverable_path,
    chartered_deliverables,
    clear_verdict,
    completion_state,
    completion_summary_bounds,
    configure_registry_facade as configure_seal_verification_facade,
    content_digest_for_execution,
    default_close_summary,
    die_content_drift_persisted,
    ensure_legacy_content_digest,
    first_pending_participant_verification_role,
    initialize_completion_state,
    insert_reopen_pointer,
    invalidate_seal_on_content_drift,
    invalidate_seal_on_full_body_drift,
    is_chartered_deliverables_label,
    latest_reviewer_findings_anchor,
    next_completion_history_number,
    next_reviewer_findings_counter,
    parse_verdict_evidence,
    participant_verification_enabled,
    participant_verification_inactive_message,
    participant_verification_incomplete,
    participant_verification_role_state,
    participant_verification_roles,
    participant_verify_render,
    participant_verify_state,
    record_verification_round_for_execution,
    replace_latest_summary,
    reset_participant_verification_stages,
    restart_verification,
    seal_snapshot,
    seal_state,
    set_verification_review_substate,
    show_verdict,
    successful_verdict,
    summary_date_from_iso,
    summary_date_from_timestamp,
    sync_participant_verification_review_substate,
    validate_verdict,
    validate_verdict_evidence,
    verdict_args_present,
    verdict_reopen_command,
    verification_review_substate,
    verification_state,
    verification_substate,
    write_seal_verdict_companion,
)

# Architecture: see commands/collab/reference/engine-architecture.md

def resolve_config_root() -> Path:
    configured = os.environ.get('COMMAND_CONFIG_ROOT')
    if configured:
        return Path(configured).expanduser().resolve()
    if (ROOT / 'commands').is_dir():
        return ROOT
    return ROOT


DEFAULT_CONFIG_ROOT = resolve_config_root()
DEFAULT_ROLES_DIR = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/roles'
DEFAULT_EFFORT_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/agent-effort.json'
DEFAULT_AGENT_MODEL_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/agent-model.md'
DEFAULT_FLAG_TAXONOMY_PATH = DEFAULT_CONFIG_ROOT / 'platform/standards/flag-taxonomy.md'
ROLE_KEY_RE = re.compile(r'^\w+$')
PHASE_SUMMARY_BEGIN = '<!-- collab:phase-summary-managed -->'
PHASE_SUMMARY_END = '<!-- collab:phase-summary-end -->'
TIMESTAMP_RE = re.compile(r'^<p><em>(?P<timestamp>.+)</em></p>$')
EFFORT_OVERRIDE_COMMENT_RE = re.compile(
    r'^<!-- collab:effort-override b64:(?P<payload>[A-Za-z0-9_-]+={0,2}) -->$'
)
FLAG_ROW_RE = re.compile(r'^\|\s*`(?P<flag>[^`]+)`\s*\|\s*`(?P<class>[^`]+)`\s*\|\s*(?P<notes>.*?)\s*\|$')
def role_is_joinable(role_data: dict) -> bool:
    return role_data.get('joinable') is not False


def log_command(path: Path, target: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    for event in read_revision_events(path, entry['id']):
        index = event.get('eventIndex')
        index_label = '#legacy' if index is None else f'#{index}'
        timestamp = event.get('timestamp') or '-'
        event_type = event.get('eventType') or 'registry-write'
        summary = event.get('summary') or ''
        print(f'{index_label}  {timestamp}  {event_type}  {summary}')
    return 0


def next_sequence(data: dict) -> int:
    sequences = [
        entry.get('sequence')
        for entry in data.get('collabs', [])
        if isinstance(entry.get('sequence'), int)
    ]
    return max(sequences, default=0) + 1


def parse_init_tokens(tokens: list[str]) -> tuple[str, str, str | None, bool, bool, str, str | None]:
    name_tokens: list[str] = []
    agent_id: str | None = None
    reviewer: str | None = None
    work_repo: str | None = None
    terminal = DEFAULT_TERMINAL
    terminal_seen = False
    open_requested = False
    participant_verification = True
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == '--agent-id':
            if agent_id is not None:
                die('duplicate flag: --agent-id')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('agent-id is required')
            agent_id = tokens[index]
        elif token == '--reviewer':
            if reviewer is not None:
                die('duplicate flag: --reviewer')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('--reviewer requires a role key')
            reviewer = tokens[index]
            if not ROLE_KEY_RE.match(reviewer):
                die('--reviewer requires a role key')
        elif token == '--terminal':
            if terminal_seen:
                die('duplicate flag: --terminal')
            terminal_seen = True
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die(f'--terminal requires one of: {TERMINAL_CHOICES_MESSAGE}')
            terminal = tokens[index]
            if terminal not in ALLOWED_TERMINALS:
                die(f'--terminal requires one of: {TERMINAL_CHOICES_MESSAGE}')
        elif token == '--open':
            if open_requested:
                die('duplicate flag: --open')
            open_requested = True
        elif token == '--no-participant-verification':
            if not participant_verification:
                die('duplicate flag: --no-participant-verification')
            participant_verification = False
        elif token == '--work-repo':
            if work_repo is not None:
                die('duplicate flag: --work-repo')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('--work-repo requires a path')
            work_repo = tokens[index]
        elif token.startswith('--'):
            die(f'unknown flag: {token}')
        else:
            name_tokens.append(token)
        index += 1

    if len(name_tokens) > 1:
        die(f'unknown positional argument: {name_tokens[1]}')
    raw_title = ' '.join(name_tokens).strip()
    if not raw_title:
        die('<name> is required')
    title = normalize_title(raw_title)
    return title, normalize_join_agent_id(agent_id), reviewer, open_requested, participant_verification, terminal, work_repo


def next_anchor_counter(lines: list[str], phase: str, role: str) -> int:
    prefix = f'{phase_slug(phase)}-{role}-'
    highest = 0
    for line in lines:
        match = ANCHOR_RE.match(line.strip())
        if match and match.group('anchor').startswith(prefix):
            suffix = match.group('anchor')[len(prefix):]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
    return max(highest, contribution_roles('\n'.join(lines), phase).count(role)) + 1


def action_plan_item_tag(text: str) -> str | None:
    return transcript_readers.action_plan_item_tag(text)


def action_plan_checklist_items(transcript: str) -> list[dict]:
    return transcript_readers.action_plan_checklist_items(transcript)


def unchecked_assigned_items_by_role(transcript: str) -> dict[str, int]:
    return transcript_readers.unchecked_assigned_items_by_role(transcript)


def tombstone_count(transcript: str) -> int:
    total = 0
    for phase in PHASES:
        try:
            lines = phase_section(transcript, phase)
        except SystemExit:
            continue
        index = 0
        while index < len(lines):
            if not DETAILS_OPEN_RE.match(lines[index].strip()):
                index += 1
                continue
            start = index
            depth = 1
            end: int | None = None
            line_index = index + 1
            while line_index < len(lines):
                stripped = lines[line_index].strip()
                if DETAILS_OPEN_RE.match(stripped):
                    depth += 1
                elif DETAILS_CLOSE_RE.match(stripped):
                    depth -= 1
                    if depth == 0:
                        end = line_index + 1
                        break
                line_index += 1
            if end is None:
                die(f'transcript details block not closed in phase: {phase}')
            if contribution_is_retracted(lines[start:end]):
                total += 1
            index = end
    return total


def action_plan_label_summary(transcript: str) -> str:
    counts = {
        role: count
        for role, count in unchecked_assigned_items_by_role(transcript).items()
        if count
    }
    if not counts:
        return 'none'
    return ', '.join(f'{role}={counts[role]}' for role in sorted(counts))


def unchecked_assigned_item_count(transcript: str, role: str) -> int:
    return transcript_readers.unchecked_assigned_item_count(transcript, role)


def completed_execution_unchecked_items(entry: dict, transcript: str) -> list[dict]:
    completed_roles = [
        role for role, state in sorted(entry.get('execution', {}).items())
        if state.get('status') == 'completed'
    ]
    if not completed_roles:
        return []
    unchecked = unchecked_assigned_items_by_role(transcript)
    violations: list[dict] = []
    for role in completed_roles:
        count = unchecked.get(role, 0)
        if count:
            violations.append({'role': role, 'uncheckedCount': count})
    return violations




def terminal_value(entry: dict) -> str:
    if 'terminal' in entry:
        terminal = entry['terminal']
        if isinstance(terminal, str) and terminal in ALLOWED_TERMINALS:
            return terminal
    if entry.get('createdAt') is None:
        return DEFAULT_TERMINAL
    die(f'registry: collab terminal must be one of {sorted(ALLOWED_TERMINALS)}')


def seal_terminal(entry: dict) -> bool:
    return terminal_value(entry) == 'seal'


def issue_terminal(entry: dict) -> bool:
    return terminal_value(entry) == 'issue'


def exported_issue_handoff_present(entry: dict) -> bool:
    exported = entry.get('exportedIssues')
    return (
        isinstance(exported, dict)
        and isinstance(exported.get('issues'), list)
        and bool(exported.get('issues'))
    )


def invalidate_verification_seal(entry: dict, reason: str) -> None:
    original_reviewer_backed = _seal_verification.reviewer_backed
    original_incomplete = _seal_verification.participant_verification_incomplete
    original_enabled = _seal_verification.participant_verification_enabled
    try:
        _seal_verification.reviewer_backed = reviewer_backed
        _seal_verification.participant_verification_incomplete = participant_verification_incomplete
        _seal_verification.participant_verification_enabled = participant_verification_enabled
        _seal_verification.invalidate_verification_seal(entry, reason)
    finally:
        _seal_verification.reviewer_backed = original_reviewer_backed
        _seal_verification.participant_verification_incomplete = original_incomplete
        _seal_verification.participant_verification_enabled = original_enabled


def participant_verify_render(
    path: Path,
    target: str,
    role: str,
    observed_revision: int,
    audit_file: str,
    remediation_file: str,
    final_audit_file: str,
    status: str,
    touched_paths: list[str],
    execution_agent_id: str | None = None,
    audit_agent_id: str | None = None,
    remediation_agent_id: str | None = None,
    timestamp: str | None = None,
    caller_role: str | None = None,
) -> int:
    # Permanent facade-pair: registry.py owns CLI dispatch for both wrappers by design.
    # This wrapper delegates; seal_verification.py records the round and render_seal must not.
    return _seal_verification.participant_verify_render(
        path,
        target,
        role,
        observed_revision,
        audit_file,
        remediation_file,
        final_audit_file,
        status,
        touched_paths,
        execution_agent_id,
        audit_agent_id,
        remediation_agent_id,
        timestamp,
        caller_role,
    )


def render_seal(
    path: Path,
    target: str,
    role: str,
    observed_revision: int,
    cap_exit: str | None = None,
    outcome: str | None = None,
    restore_target: str | None = None,
    restore_reason: str | None = None,
    evidence: str | None = None,
    failure_category: str | None = None,
    null_result: bool = False,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    # Permanent facade-pair: registry.py owns CLI dispatch; seal_verification.py owns implementation.
    # This wrapper delegates and must not call record_verification_round_for_execution.
    return _seal_verification.render_seal(
        path,
        target,
        role,
        observed_revision,
        cap_exit,
        outcome,
        restore_target,
        restore_reason,
        evidence,
        failure_category,
        null_result,
        emit_json,
        caller_role,
    )


def speak_state_for_entry(entry: dict, transcript: str) -> dict:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    order = effective_turn_order(entry)
    expected = expected_speaker(entry, contributors)
    optional_reviewer = optional_reviewer_allowed_at_round_boundary(entry, phase, contributors, order)
    allowed_roles = [expected]
    if optional_reviewer and optional_reviewer not in allowed_roles:
        allowed_roles.append(optional_reviewer)
    state = {
        'target': entry['id'],
        'activePhase': phase,
        'turnOrder': order,
        'contributors': contributors,
        'lastContributor': contributors[-1] if contributors else None,
        'expectedRole': expected,
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'reviewerMode': reviewer_mode(entry) if reviewer_role(entry) else None,
        'reviewerOptionalPhases': reviewer_optional_phases(entry) if reviewer_role(entry) else [],
        'allowedRoles': allowed_roles,
        'autoAdvanceExempt': phase in AUTO_ADVANCE_EXEMPT_PHASES,
        'freshRegistryRead': True,
        'freshTranscriptRead': True,
    }
    if reviewer_backed(entry) and phase == 'Completion':
        completion_substate = verification_substate(entry)
        review_substate = verification_review_substate(entry)
        if (
            completion_substate == 'verification'
            and review_substate != 'assessment'
            and participant_verification_incomplete(entry)
        ):
            review_substate = 'participant'
        state['completionSubState'] = completion_substate
        state['verificationReviewSubState'] = review_substate
        state['participantVerification'] = participant_verification_enabled(entry)
        state['nextParticipantVerificationRole'] = first_pending_participant_verification_role(entry)
        if completion_substate == 'execution':
            execution_roles = [role for role in order if role != entry.get('moderatorRole')]
            execution = entry.get('execution') if isinstance(entry.get('execution'), dict) else {}
            expected = next(
                (
                    role
                    for role in execution_roles
                    if not (
                        isinstance(execution.get(role), dict)
                        and execution[role].get('status') == 'completed'
                    )
                ),
                None,
            )
            state['expectedRole'] = expected
            state['allowedRoles'] = execution_roles
        elif completion_substate == 'verification':
            if review_substate == 'participant':
                expected = state['nextParticipantVerificationRole']
                allowed_roles = [expected] if expected else []
            else:
                expected = reviewer_role(entry)
                allowed_roles = [expected] if expected else []
            state['expectedRole'] = expected
            state['allowedRoles'] = allowed_roles
    expected_agent_id = participant_agent_id(entry, expected)
    if expected_agent_id:
        state['expectedAgentId'] = expected_agent_id
    if reviewer_role(entry):
        state['uncheckedAssignedItemsByRole'] = unchecked_assigned_items_by_role(transcript)
    return state


def blocked_resume_state_for_entry(entry: dict, transcript: str) -> dict:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    state = {
        'target': entry['id'],
        'activePhase': phase,
        'turnOrder': effective_turn_order(entry),
        'contributors': contributors,
        'lastContributor': contributors[-1] if contributors else None,
        'expectedRole': None,
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'reviewerMode': reviewer_mode(entry) if reviewer_role(entry) else None,
        'reviewerOptionalPhases': reviewer_optional_phases(entry) if reviewer_role(entry) else [],
        'allowedRoles': [],
        'autoAdvanceExempt': phase in AUTO_ADVANCE_EXEMPT_PHASES,
        'freshRegistryRead': True,
        'freshTranscriptRead': True,
    }
    requested_agent_id = participant_agent_id(entry, entry.get('moderatorRole', ''))
    if requested_agent_id:
        state['moderatorAgentId'] = requested_agent_id
    if reviewer_role(entry):
        state['uncheckedAssignedItemsByRole'] = unchecked_assigned_items_by_role(transcript)
    return state




def validate_registry(data: dict, path: Path | None = None) -> None:
    validate_registry_data(data, path, DEFAULT_ROLES_DIR)


configure_registry_io(validate_registry)


def project_metadata_for_display(data: dict) -> dict | None:
    metadata = project_metadata_from_identity()
    if metadata is not None:
        return metadata
    project = data.get('project')
    if isinstance(project, dict):
        project_id = project.get('projectId')
        label = project.get('label')
        if isinstance(project_id, str) and project_id.strip() and isinstance(label, str) and label.strip():
            return {'projectId': project_id, 'label': label.strip()}
    return None


def list_collabs(data: dict, status_filter: str | None = None) -> int:
    if status_filter is not None and status_filter not in ALLOWED_STATUSES:
        die(f'invalid status filter: {status_filter}')
    active_id = data.get('activeCollabId')
    indexed = [
        (index, entry)
        for index, entry in enumerate(data['collabs'], start=1)
        if status_filter is None or entry['status'] == status_filter
    ]
    indexed.sort(key=lambda item: (
        item[1]['id'] != active_id,
        -item[1].get('sequence', item[0]),
        item[1]['slug'],
    ))
    project = project_metadata_for_display(data)
    if project is not None:
        print(f"Project: {project['label']} · {project['projectId']}")
    for output_index, (index, entry) in enumerate(indexed):
        marker = '[*]' if entry['id'] == active_id else '[ ]'
        number = entry.get('sequence', index)
        title = display_title(entry['title'])
        phase = entry['activePhase'] if entry['activePhase'] else '—'
        participant_label = 'participant' if len(entry['participants']) == 1 else 'participants'
        if output_index or project is not None:
            print()
        print(f"{marker} #{number} - {entry['slug']}    {title}")
        print(
            f"         {entry['status']} · {phase} · "
            f"{len(entry['participants'])} {participant_label} · {collab_date(entry)}",
        )
    return 0


def resume_command(entry: dict, role: str) -> str:
    return f'RESUME: {resume_command_invocation(entry, role)}'


def resume_command_invocation(entry: dict, role: str) -> str:
    return f'commands/collab/engine/registry.py speak-state --resume {entry["id"]} {role}'


def transcript_view_command(entry: dict, phase: str | None = None, raw: bool = False) -> str:
    selected_phase = phase or entry['activePhase']
    command = f'commands/collab/engine/registry.py transcript-view {entry["id"]} {shlex.quote(selected_phase)}'
    if raw:
        command += ' --raw'
    return command


def transcript_view_command_for_role(entry: dict, role: str, phase: str | None = None) -> str:
    return transcript_view_command(entry, phase, raw=role != entry.get('moderatorRole'))


def active_phase_anchors(transcript: str, phase: str) -> list[str]:
    anchors: list[str] = []
    for line in phase_section(transcript, phase):
        match = ANCHOR_RE.match(line.strip())
        if match:
            anchors.append(match.group('anchor'))
    return anchors


def current_completion_command(entry: dict) -> str | None:
    substate = verification_substate(entry)
    if substate == 'verification':
        review_substate = verification_review_substate(entry)
        if review_substate == 'assessment':
            return None
        if (
            review_substate == 'participant'
            or (
                review_substate != 'assessment'
                and participant_verification_incomplete(entry)
            )
        ):
            pending_role = first_pending_participant_verification_role(entry)
            if pending_role:
                return collab_dispatch('participant verify', entry["id"], pending_role)
            return collab_dispatch('participant verify', entry["id"])
        return collab_dispatch('seal verification', entry["id"])
    return collab_dispatch('run plan', entry["id"])


def next_command_for_state(entry: dict, transcript: str | None = None) -> str | None:
    if entry['status'] in {'closed', 'archived'}:
        return '/clear'
    phase = entry['activePhase']
    if phase == 'Completion':
        return current_completion_command(entry)
    if transcript is None:
        transcript = read_transcript_for_entry(entry)
    state = speak_state_for_entry(entry, transcript)
    if state.get('expectedRole') and state.get('expectedRole') != entry.get('moderatorRole'):
        return collab_dispatch('speak', entry["id"])
    return None


def phase_summary_for_state(entry: dict, state: dict) -> dict:
    summary = {
        'activePhase': entry['activePhase'],
        'status': entry['status'],
    }
    if state.get('completionSubState'):
        summary['completionSubState'] = state['completionSubState']
    if state.get('verificationReviewSubState'):
        summary['verificationReviewSubState'] = state['verificationReviewSubState']
    expected = state.get('expectedRole')
    if expected:
        summary['expectedRole'] = expected
    if state.get('lastContributor'):
        summary['lastContributor'] = state['lastContributor']
    unchecked = state.get('uncheckedAssignedItemsByRole')
    if unchecked:
        summary['uncheckedAssignedItemsByRole'] = unchecked
    return summary


def policy_blockers_for_role(state: dict, role: str, pending_reviewer: str | None = None) -> list[dict]:
    blockers: list[dict] = []
    if pending_reviewer:
        blockers.append({'code': 'pending-reviewer', 'reviewerRole': pending_reviewer})
    allowed = state.get('allowedRoles', [])
    if role not in allowed:
        expected = state.get('expectedRole')
        if expected:
            blockers.append({'code': 'expected-role', 'expectedRole': expected})
        elif not pending_reviewer:
            blockers.append({'code': 'no-eligible-role'})
    return blockers


def add_participation_resume_fields(
    state: dict,
    entry: dict,
    transcript: str,
    role: str,
    pending_reviewer: str | None = None,
) -> None:
    next_command = next_command_for_state(entry, transcript)
    if next_command:
        state['nextCommand'] = next_command
    state['nextTranscriptCommand'] = transcript_view_command_for_role(entry, role)
    state['policyBlockers'] = policy_blockers_for_role(state, role, pending_reviewer)
    state['phaseSummary'] = phase_summary_for_state(entry, state)
    anchors = active_phase_anchors(transcript, entry['activePhase'])
    if anchors:
        state['excerptAnchors'] = anchors


def die_with_resume(message: str, entry: dict, role: str) -> None:
    die(f'{message}\n{resume_command(entry, role)}')


def phase_summary_bounds(lines: list[str]) -> tuple[int, int] | None:
    start = None
    for index, line in enumerate(lines):
        if line.strip() == PHASE_SUMMARY_BEGIN:
            start = index
            break
    if start is None:
        return None
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == PHASE_SUMMARY_END:
            return start, index + 1
    die('phase summary sentinel mismatch')


def phase_summary_insert_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.strip() == HEADER_MANAGED_END:
            return index + 1
    if lines and lines[0].startswith('# '):
        return 1
    die('transcript title missing')


def phase_summary_line(transcript: str, entry: dict, phase: str) -> str:
    try:
        roles = contribution_roles(transcript, phase)
    except SystemExit as exc:
        if str(exc) == f'transcript phase missing: {phase}':
            return f'- **{phase}:** missing section'
        raise
    if not roles:
        summary = 'no contributions'
    else:
        unique_roles = ', '.join(dict.fromkeys(roles))
        summary = f'{len(roles)} contribution(s) from {unique_roles}'
    if phase == 'Completion':
        completed = [
            role
            for role, state in sorted(entry.get('execution', {}).items())
            if state.get('status') == 'completed'
        ]
        if completed:
            summary = f'{summary}; completed execution for {", ".join(completed)}'
        if entry.get('status') == 'closed':
            summary = f'{summary}; closed'
    return f'- **{phase}:** {summary}'


def rendered_phase_summary(transcript: str, entry: dict, date: str) -> list[str]:
    return [
        PHASE_SUMMARY_BEGIN,
        CONTENT_ONLY_GUARD,
        '',
        '## Phase Summary',
        '',
        f'_Last refreshed: {date}_',
        '',
        *[phase_summary_line(transcript, entry, phase) for phase in PHASES],
        '',
        PHASE_SUMMARY_END,
    ]


def replace_phase_summary(transcript: str, entry: dict, date: str) -> str:
    lines = transcript.splitlines()
    block = rendered_phase_summary(transcript, entry, date)
    bounds = phase_summary_bounds(lines)
    if bounds is not None:
        start, end = bounds
        replacement = block
        if end < len(lines) and lines[end].strip():
            replacement = [*replacement, '']
        return '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'
    insert_at = phase_summary_insert_index(lines)
    replacement = ['', *block, '']
    return '\n'.join(lines[:insert_at] + replacement + lines[insert_at:]) + '\n'


def summarize_collab(path: Path, target: str, date: str | None = None) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] == 'archived':
            die('record is archived')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
        summary_date = date or dt.date.today().isoformat()
        rendered = replace_phase_summary(rendered, entry, summary_date)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(transcript_path)
    return 0


def forced_active_phase_advisory(entry: dict, transcript: str) -> str:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    live = ', '.join(contributors) if contributors else 'none'
    return (
        f'RECOVERY-ADVISORY: active-phase --force post-check for {entry["id"]}; '
        f'live contributors in {phase}: {live}; '
        f'tombstones: {tombstone_count(transcript)}; '
        f'pending rewrites: manual-check; '
        f'active Action Plan labels: {action_plan_label_summary(transcript)}.'
    )


def add_completion_summary_notice(notice: dict | None, transcript: str) -> dict | None:
    if notice and notice.get('transition') == 'Handoff->Completion' and completion_summary_empty(transcript):
        notice = dict(notice)
        notice['summaryEmpty'] = True
    return notice


def next_line_for_state(entry: dict, transcript: str | None = None) -> str:
    if entry['status'] == 'closed':
        return 'NEXT: Collab closed; run /clear before starting another collab.'
    if entry['status'] == 'archived':
        return 'NEXT: Collab archived; run /clear before starting another collab.'
    phase = entry['activePhase']
    if phase == 'Completion':
        return f"NEXT: Run {collab_dispatch('run plan')} for role {effective_turn_order(entry)[0]}."
    if transcript is None:
        try:
            transcript = read_transcript_for_entry(entry)
        except SystemExit:
            order = effective_turn_order(entry)
            if order:
                return f'NEXT: Run {collab_dispatch("speak")} for role {order[0]}.'
            return f'NEXT: Active phase is {phase}.'
    try:
        state = speak_state_for_entry(entry, transcript)
    except SystemExit:
        order = effective_turn_order(entry)
        if order:
            return f'NEXT: Run {collab_dispatch("speak")} for role {order[0]}.'
        return f'NEXT: Active phase is {phase}.'
    expected = state.get('expectedRole')
    if expected:
        return f'NEXT: Run {collab_dispatch("speak")} for role {expected}.'
    return f'NEXT: Active phase is {phase}.'


def next_line_after_speak(entry: dict, role: str, phase: str, transcript: str) -> str:
    if phase == 'Discussion':
        return f'NEXT: Run /compact before your next collab command for role {role}.'
    return next_line_for_state(entry, transcript)










def effort_phase_after_speak(source_phase: str) -> str:
    if source_phase == 'Discussion':
        return 'Conclusion'
    if source_phase in ONE_SPEAK_PHASES:
        next_phase = next_phase_name(source_phase)
        if next_phase:
            return next_phase
    return source_phase


def efficiency_line_from_notice(notice: dict | None) -> str | None:
    if not notice:
        return None
    notice_type = notice.get('notice')
    transition = notice.get('transition')
    status = notice.get('status')
    if notice_type == 'compact' and transition in {'Discussion-turn', 'Discussion->Conclusion'}:
        return 'EFFICIENCY: Run /compact before next collab command.'
    if notice_type == 'subagent' and transition == 'Handoff->Completion':
        return 'EFFICIENCY: Run /compact, then prepare or use the assigned subagent work.'
    if notice_type == 'clear' or status in {'closed', 'archived'}:
        return 'EFFICIENCY: Run /clear before starting another collab.'
    return None


def post_action_advisory_lines(
    entry: dict,
    role: str | None,
    effort_phase: str | None,
    notice: dict | None,
    next_line: str,
    effort_path: Path = DEFAULT_EFFORT_PATH,
) -> list[str]:
    lines = [next_line]
    if role and entry['status'] not in {'closed', 'archived'}:
        lines.append(resume_command(entry, role))
    if role and effort_phase:
        defaults = load_effort_defaults(effort_path)
        lines.append(effort_line(defaults, effort_phase, role))
    efficiency = efficiency_line_from_notice(notice)
    if efficiency:
        lines.append(efficiency)
    if notice and notice.get('summaryEmpty'):
        lines.append('COMPLETION-ADVISORY: Completion section has no summary prose.')
    return lines


def print_post_action_advisories(
    entry: dict,
    role: str | None,
    effort_phase: str | None,
    notice: dict | None,
    next_line: str,
) -> None:
    for line in post_action_advisory_lines(entry, role, effort_phase, notice, next_line):
        print(line)


def effort_state(path: Path, target: str, role: str, effort_defaults_path: Path) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if not has_participant(entry, role):
        die(f'effort role must already be a participant: {role}')
    defaults = load_effort_defaults(effort_defaults_path)
    phase = entry['activePhase']
    effort = effort_value(defaults, phase, role)
    result = {
        'advisory': True,
        'effort': effort,
        'phase': phase,
        'role': role,
        'source': str(effort_defaults_path),
        'target': entry['id'],
    }
    if effort is None:
        result['notOnRoster'] = True
    print(json.dumps(result, sort_keys=True))
    return 0












def apply_speak_lifecycle_to_entry(
    entry: dict,
    contributors: list[str],
    transcript: str | None = None,
) -> bool:
    phase = entry['activePhase']
    order = effective_turn_order(entry)
    reviewer = reviewer_required_for_phase(entry, phase)
    required_roles = list(order)
    if reviewer:
        required_roles.append(reviewer)
    counts = {role: contributors.count(role) for role in required_roles}

    if phase in ONE_SPEAK_PHASES:
        duplicates = [role for role, count in counts.items() if count > 1]
        if duplicates:
            die(f'duplicate contribution in one-speak phase {phase}: {duplicates[0]}')
        if optional_reviewer_allowed_at_round_boundary(entry, phase, contributors, order):
            return False

    if phase in AUTO_ADVANCE_EXEMPT_PHASES or not all(counts.get(role, 0) >= 1 for role in required_roles):
        return False

    next_phase = next_phase_name(phase)
    if next_phase is None:
        return False
    if phase == 'Action Plan':
        validate_action_plan_executable_scope(transcript if transcript is not None else read_transcript_for_entry(entry))
    entry['activePhase'] = next_phase
    if next_phase in MOD_EXCLUDED_PHASES:
        remove_moderator_from_turn_order(entry, order)
    if next_phase == 'Completion' and seal_terminal(entry):
        initialize_completion_state(entry, 'execution', reset_rounds=True)
    return True


def apply_speak_lifecycle_with_notice(
    entry: dict,
    contributors: list[str],
    transcript: str | None = None,
) -> tuple[bool, dict | None]:
    from_phase = entry['activePhase']
    advanced = apply_speak_lifecycle_to_entry(entry, contributors, transcript)
    notice = transition_notice(from_phase, entry['activePhase']) if advanced else None
    if not notice and from_phase == 'Discussion':
        notice = discussion_turn_notice(entry, contributors)
    return advanced, notice


def close_eligible_after_execution(entry: dict, assigned_roles: list[str]) -> bool:
    roles = [role for role in assigned_roles if role != entry['moderatorRole']]
    if not roles:
        return False
    execution = entry.get('execution', {})
    completed = all(execution.get(role, {}).get('status') == 'completed' for role in roles)
    if not completed:
        return False
    if issue_terminal(entry):
        return exported_issue_handoff_present(entry)
    if reviewer_backed(entry):
        seal = entry.get('verificationSeal')
        return isinstance(seal, dict) and not seal.get('stale') and successful_verdict(entry)
    return True


def next_line_after_execution(entry: dict, assigned_roles: list[str]) -> str:
    if entry['status'] in {'closed', 'archived'}:
        return next_line_for_state(entry)
    execution = entry.get('execution', {})
    for assigned_role in effective_turn_order(entry):
        if assigned_role == entry['moderatorRole']:
            continue
        if execution.get(assigned_role, {}).get('status') != 'completed':
            return f'NEXT: Run {collab_dispatch("run plan")} for role {assigned_role}.'
    if issue_terminal(entry):
        if not exported_issue_handoff_present(entry):
            export_role = 'pe' if has_participant(entry, 'pe') else next(
                (
                    role for role in effective_turn_order(entry)
                    if role != entry['moderatorRole']
                ),
                'pe',
            )
            return f'NEXT: Run {collab_dispatch("export-issues")} for role {export_role}.'
        return next_line_for_state(entry)
    if reviewer_backed(entry):
        if participant_verification_enabled(entry):
            pending_role = first_pending_participant_verification_role(entry)
            if pending_role:
                return f'NEXT: Run {collab_dispatch("participant verify")} for role {pending_role}.'
        return f'NEXT: Run {collab_dispatch("seal verification")} for role {reviewer_role(entry)}.'
    return next_line_for_state(entry)


def activate_collab(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['archived']:
            die(f'registry target archived: {target}')
        data['activeCollabId'] = entry['id']
        save_registry(path, data)
    print(entry['id'])
    return 0


def set_field(
    path: Path,
    target: str,
    field: str,
    value: str | None,
    force: bool,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    force_advisory: str | None = None
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'set')
        forced_active_phase = False
        if field in FORCE_ONLY_FIELDS:
            if value is None:
                die(f'{field} requires a value')
            if not force:
                die(f'field requires --force: {field}')
            if field == 'active-phase':
                if value not in PHASES:
                    die(f'active-phase must be one of {PHASES}')
                entry['activePhase'] = value
                forced_active_phase = True
                if value == 'Completion' and seal_terminal(entry):
                    # Mirror advance_phase's Completion entry so a forced jump
                    # cannot bypass the scope-aware reset and strand a reopened
                    # cycle at rounds=0 with every stage preserved (the old
                    # deadlock). No-op on a fresh force (no completed stages yet).
                    initialize_completion_state(entry, 'execution', reset_rounds=True, scope_aware=True)
        elif field == 'reviewer':
            if value == '--clear':
                clear_reviewer(entry)
            else:
                if value is None:
                    die('reviewer requires a role or --clear')
                if not has_participant(entry, value):
                    die('reviewer must already be a participant')
                load_role(roles_dir, value)
                if value == entry['moderatorRole']:
                    die('reviewer must not be the moderator')
                if value in entry['turnOrder']:
                    die('reviewer must not appear in turnOrder')
                entry['reviewerRole'] = value
                entry['reviewerMode'] = DEFAULT_REVIEWER_MODE
                entry['reviewerOptionalPhases'] = list(DEFAULT_REVIEWER_OPTIONAL_PHASES)
        elif field == 'reviewer-optional-phases':
            if not reviewer_role(entry):
                die('reviewer-optional-phases requires reviewerRole')
            entry['reviewerOptionalPhases'] = parse_reviewer_optional_phases(value)
        elif field not in ALLOWED_SET_FIELDS:
            die(f'field not settable: {field}')
        elif field == 'turn-order':
            if value is None:
                die('turn-order requires a value')
            turnOrder = value.split()
            if not turnOrder:
                die('turn-order requires at least one role')
            if len(set(turnOrder)) != len(turnOrder):
                die('turn-order roles must be unique')
            if not set(turnOrder).issubset(set(participant_roles(entry))):
                die('turn-order roles must already be participants')
            reviewer = reviewer_role(entry)
            if reviewer and reviewer in turnOrder:
                die('turn-order must not include reviewerRole')
            entry['turnOrder'] = turnOrder
        elif field == 'work-repo':
            if value is None:
                die('work-repo requires a path')
            entry['workRepo'] = str(resolve_git_work_tree(value, 'work-repo'))
        else:
            if value is None:
                die(f'{field} requires a value')
            if not value.strip():
                die(f'{field} requires a non-empty value')
            entry[field] = value
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, roles_dir)
        if forced_active_phase:
            force_advisory = forced_active_phase_advisory(entry, rendered)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(entry['id'])
    if force_advisory:
        print(force_advisory)
    return 0


def clear_reviewer(entry: dict) -> bool:
    changed = False
    for key in ('reviewerRole', 'reviewerMode', 'reviewerOptionalPhases'):
        if key in entry:
            entry.pop(key)
            changed = True
    return changed


def unset_field(
    path: Path,
    target: str,
    field: str,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    if field != 'reviewer':
        die(f'field not unsettable: {field}')

    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'unset')
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        clear_reviewer(next_entry)
        validate_registry(nextdata, path)

        transcript_path = transcript_path_for_entry(next_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), next_entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, nextdata, transcript_path, rendered)
    print(next_entry['id'])
    return 0


def remove_participant(
    path: Path,
    target: str,
    role: str,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'remove-participant')
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if role == current_entry['moderatorRole']:
            die('moderator cannot be removed')
        if role == reviewer_role(current_entry):
            die('reviewer cannot be removed while assigned')
        if not has_participant(current_entry, role):
            print(f'participant already absent: {role}')
            return 0

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        next_entry['participants'] = [
            participant
            for participant in next_entry.get('participants', [])
            if participant.get('role') != role
        ]
        next_entry['turnOrder'] = [
            participant_role
            for participant_role in next_entry.get('turnOrder', [])
            if participant_role != role
        ]
        validate_registry(nextdata, path)

        transcript_path = transcript_path_for_entry(next_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), next_entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, nextdata, transcript_path, rendered)
    print(next_entry['id'])
    return 0


def speak_lifecycle(path: Path, target: str, contributors: list[str]) -> int:
    if not contributors:
        die('contributors requires at least one role')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        for role in contributors:
            if not has_participant(entry, role):
                die(f'contributor must already be a participant: {role}')
        transcript_path = transcript_path_for_entry(entry)
        transcript = transcript_path.read_text() if transcript_path.exists() else None
        advanced, notice = apply_speak_lifecycle_with_notice(entry, contributors, transcript)
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript or '', entry, DEFAULT_ROLES_DIR)
            notice = add_completion_summary_notice(notice, rendered)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_phase_result(entry['activePhase'] if advanced else 'unchanged', notice)
    return 0


def ensure_init_project_metadata(data: dict, registry_path: Path) -> None:
    project = data.get('project')
    if isinstance(project, dict):
        return
    metadata = project_metadata_from_identity()
    if metadata is not None:
        data['project'] = metadata
        return
    project_root = registry_path.parent.resolve()
    data['project'] = {
        'projectId': hashlib.sha256(str(project_root).encode()).hexdigest()[:32],
        'label': project_root.name or 'command-project',
    }


def contribution_store_record(
    phase: str,
    role: str,
    anchor: str,
    content: str,
    timestamp: str,
    full_body: str | None = None,
) -> dict:
    compact = re.sub(r'\s+', ' ', excerpt_source(content)).strip()
    record = {
        'phase': phase,
        'role': role,
        'anchor': anchor,
        'stance': stance_for_content(content),
        'excerpt': compact,
        'content': content,
        'timestamp': timestamp,
    }
    if full_body is not None:
        record['fullBody'] = full_body
    return record


def append_contribution_store_record(
    registry_path: Path,
    entry: dict,
    record: dict,
) -> None:
    store = mutable_contribution_store_for_entry(registry_path, entry)
    store.setdefault('contributions', []).append(record)
    write_contribution_store_for_entry(registry_path, entry, store)


def replace_latest_contribution_store_record(
    registry_path: Path,
    entry: dict,
    phase: str,
    role: str,
    record: dict,
) -> None:
    store = mutable_contribution_store_for_entry(registry_path, entry)
    contributions = store.setdefault('contributions', [])
    for index in range(len(contributions) - 1, -1, -1):
        existing = contributions[index]
        if isinstance(existing, dict) and existing.get('phase') == phase and existing.get('role') == role:
            contributions[index] = record
            write_contribution_store_for_entry(registry_path, entry, store)
            return
    contributions.append(record)
    write_contribution_store_for_entry(registry_path, entry, store)


def mark_contribution_store_record_retracted(
    registry_path: Path,
    entry: dict,
    anchor: str,
    reason: str,
    timestamp: str,
) -> None:
    store = mutable_contribution_store_for_entry(registry_path, entry)
    contributions = store.setdefault('contributions', [])
    for index in range(len(contributions) - 1, -1, -1):
        existing = contributions[index]
        if isinstance(existing, dict) and existing.get('anchor') == anchor:
            existing['retracted'] = True
            existing['retractionReason'] = reason
            existing['retractionTimestamp'] = timestamp
            write_contribution_store_for_entry(registry_path, entry, store)
            return


def speak_state(path: Path, target: str, role: str, resume: bool = False) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if entry['status'] in {'closed', 'archived'}:
        die('record is closed')
    if not has_participant(entry, role):
        die(f'role must already be a participant: {role}')
    transcript = read_transcript_for_entry(entry)
    pending_reviewer = pending_reviewer_role(entry)
    if pending_reviewer:
        if resume:
            state = blocked_resume_state_for_entry(entry, transcript)
            state['roleAgentId'] = participant_agent_id(entry, role)
            state['readyToWrite'] = False
            state['registryRevision'] = registry_revision(data)
            add_participation_resume_fields(state, entry, transcript, role, pending_reviewer)
            print(json.dumps(state, sort_keys=True))
            return 0
        die_with_resume(f'pending reviewerRole: {pending_reviewer}', entry, role)
    state = speak_state_for_entry(entry, transcript)
    state['roleAgentId'] = participant_agent_id(entry, role)
    state['readyToWrite'] = role in state['allowedRoles']
    state['registryRevision'] = registry_revision(data)
    if resume:
        add_participation_resume_fields(state, entry, transcript, role)
        print(json.dumps(state, sort_keys=True))
        return 0
    if role not in state['allowedRoles']:
        if role == reviewer_optional_for_phase(entry, entry['activePhase']):
            die_with_resume('reviewer may speak after all turn-order participants have contributed in this round', entry, role)
        die_with_resume(f"expected role: {state['expectedRole']}", entry, role)
    print(json.dumps(state, sort_keys=True))
    return 0


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


def transcript_view(path: Path, target: str, phase: str, raw: bool = False) -> int:
    if phase not in PHASES:
        die(f'phase must be one of: {", ".join(PHASES)}')
    data = load_registry(path)
    entry = resolve_collab(data, target)
    transcript = read_transcript_for_entry(entry)
    lines = transcript.splitlines()
    start, end = section_bounds(lines, f'## {phase}')
    sys.stdout.write('\n'.join(lines[start:end]) + '\n')
    return 0


def speak_lifecycle_live(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        state = speak_state_for_entry(entry, transcript)
        advanced, notice = apply_speak_lifecycle_with_notice(entry, state['contributors'], transcript)
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_phase_result(entry['activePhase'] if advanced else 'unchanged', notice)
    return 0


def read_content_file(path: Path) -> str:
    if not path.exists():
        die(f'content file missing: {path}')
    content = path.read_text()
    if not content.strip():
        die('content must be non-empty')
    return content.rstrip('\n')


def read_optional_content_file(path: Path | None) -> str | None:
    if path is None:
        return None
    return read_content_file(path)


def effort_override_from_metadata_comment(line: str) -> str | None:
    match = EFFORT_OVERRIDE_COMMENT_RE.match(line.strip())
    if not match:
        return None
    try:
        return base64.urlsafe_b64decode(match.group('payload').encode()).decode()
    except (ValueError, UnicodeDecodeError):
        die('EFFORT OVERRIDE metadata is invalid')


def effort_override_audit_items(target: str, transcript: str) -> list[dict]:
    findings: list[dict] = []
    for phase in PHASES:
        try:
            lines = phase_section(transcript, phase)
        except SystemExit:
            continue
        details_depth = 0
        current_role: str | None = None
        current_override: str | None = None
        for line in lines:
            stripped = line.strip()
            if DETAILS_OPEN_RE.match(stripped):
                details_depth += 1
                if details_depth == 1:
                    current_role = None
                    current_override = None
                continue
            if DETAILS_CLOSE_RE.match(stripped):
                if details_depth == 1 and current_role:
                    mandatory = (phase, current_role) in MANDATORY_EFFORT_OVERRIDE_TURNS
                    if mandatory or current_override:
                        item = {
                            'target': target,
                            'phase': phase,
                            'role': current_role,
                            'mandatory': mandatory,
                            'hasOverride': current_override is not None,
                        }
                        if current_override:
                            item['effortOverride'] = current_override
                        findings.append(item)
                details_depth = max(0, details_depth - 1)
                continue
            if details_depth != 1:
                continue
            role = summary_role(line)
            if role is not None:
                current_role = role
                continue
            override = effort_override_from_metadata_comment(stripped)
            if override:
                current_override = override
    return findings


def render_speak(
    path: Path,
    target: str,
    role: str,
    content_file: Path,
    full_body_file: Path | None = None,
    observed_revision: int | None = None,
    timestamp: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
    verbatim: bool = False,
) -> int:
    content = read_content_file(content_file)
    full_body = read_optional_content_file(full_body_file)
    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'speak-render', role)
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if current_entry['activePhase'] == 'Completion':
            die('speak-render is not permitted in Completion')
        if not has_participant(current_entry, role):
            die(f'role must already be a participant: {role}')
        live_revision = registry_revision(data)
        resume = resume_command(current_entry, role)
        if observed_revision is None:
            die(f'speak-render requires --observed-revision\n{resume}')
        if observed_revision != live_revision:
            die(
                f'stale registry revision: observed {observed_revision}, live {live_revision}\n'
                f'{resume}'
            )

        transcript_path = transcript_path_for_entry(current_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        pending_reviewer = pending_reviewer_role(current_entry)
        if pending_reviewer:
            die(f'pending reviewerRole: {pending_reviewer}\n{resume}')
        state = speak_state_for_entry(current_entry, transcript)
        if role not in state['allowedRoles']:
            if role == reviewer_optional_for_phase(current_entry, current_entry['activePhase']):
                die(
                    'reviewer may speak after all turn-order participants have contributed in this round\n'
                    f'{resume}'
                )
            die(f"expected role: {state['expectedRole']}\n{resume}")
        phase = current_entry['activePhase']
        if phase in ONE_SPEAK_PHASES and role in state['contributors']:
            die(f'duplicate phase contribution: {role} in {phase}\n{resume}')
        if role == current_entry['moderatorRole'] and not verbatim:
            content = polish_moderator_content(content)
        reject_hand_authored_excerpt_details(content)
        reject_full_body_details_controls(full_body)
        enforce_contribution_budget(content, phase, role, current_entry['moderatorRole'], verbatim)
        validate_effort_override(content, phase, role, current_entry['moderatorRole'])
        validate_conclusion_directive_gap(content, phase)
        validate_reviewer_conclusion_gates(content, phase, role, current_entry)
        validate_action_plan_shape(content, phase)
        handoff_state = parse_handoff_content(content) if phase == 'Handoff' else None

        lines = transcript.splitlines()
        counter = next_anchor_counter(lines, phase, role)
        render_timestamp = timestamp or format_timestamp()
        anchor, block = render_contribution_block(
            phase,
            role,
            counter,
            content,
            render_timestamp,
            full_body,
        )
        contribution_record = contribution_store_record(
            phase,
            role,
            anchor,
            content,
            render_timestamp,
            full_body,
        )
        rendered_lines = append_phase_block(lines, phase, block)

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        if handoff_state is not None:
            set_handoff_state(next_entry, role, handoff_state)
        rendered_text = '\n'.join(rendered_lines) + '\n'
        rendered_state = speak_state_for_entry(next_entry, rendered_text)
        advanced, notice = apply_speak_lifecycle_with_notice(next_entry, rendered_state['contributors'], rendered_text)
        rendered_text, header_changed = render_managed_header_text(rendered_text, next_entry, DEFAULT_ROLES_DIR)
        notice = add_completion_summary_notice(notice, rendered_text)
        print('BOUNDARY: transcript write only; no shell commands or source edits outside the user-scope collab state root')
        print('SUCCINCTLY: stay within role concerns; do not pad or summarize other roles')
        print(f'RETRACT: use {collab_dispatch("retract speak")} to tombstone the latest active-phase contribution')
        print_header_overwrite(header_changed)
        label_advisory = action_plan_label_advisory(content, phase)
        if label_advisory:
            print(label_advisory)
        commit_registry_and_transcript(path, nextdata, transcript_path, rendered_text)
        append_contribution_store_record(path, next_entry, contribution_record)
    print_post_action_advisories(
        next_entry,
        role,
        effort_phase_after_speak(phase),
        notice,
        next_line_after_speak(next_entry, role, phase, rendered_text),
    )
    lifecycle = {'phaseState': next_entry['activePhase'] if advanced else 'unchanged'}
    if notice:
        lifecycle['notice'] = notice
    print('appended')
    print_lifecycle_diagnostic(lifecycle, emit_json)
    return 0


def contribution_block_bounds(lines: list[str], phase: str, role: str) -> tuple[int, int] | None:
    _phase_start, phase_end = section_bounds(lines, f'## {phase}')
    latest: tuple[int, int] | None = None
    index = _phase_start + 1
    while index < phase_end:
        if DETAILS_OPEN_RE.match(lines[index].strip()):
            start = index
            depth = 1
            end: int | None = None
            line_index = index + 1
            while line_index < phase_end:
                stripped = lines[line_index].strip()
                if DETAILS_OPEN_RE.match(stripped):
                    depth += 1
                elif DETAILS_CLOSE_RE.match(stripped):
                    depth -= 1
                    if depth == 0:
                        end = line_index + 1
                        break
                line_index += 1
            if end is None:
                die(f'transcript details block not closed in phase: {phase}')
            summary = summary_role(lines[start + 1]) if start + 1 < end else None
            if summary == role:
                latest = (start, end)
            index = end
            continue
        index += 1
    return latest


def latest_contribution_anchor(transcript: str, phase: str, role: str) -> str:
    lines = transcript.splitlines()
    bounds = contribution_block_bounds(lines, phase, role)
    if bounds is None:
        die(f'no prior contribution to rewrite; use {collab_dispatch("speak")} to create the first contribution')
    start, _end = bounds
    if start > 0:
        match = ANCHOR_RE.match(lines[start - 1].strip())
        if match:
            return match.group('anchor')
    die('contribution anchor missing')


def replace_latest_contribution(
    transcript: str,
    phase: str,
    role: str,
    content: str,
    timestamp: str,
    full_body: str | None = None,
) -> str:
    lines = transcript.splitlines()
    bounds = contribution_block_bounds(lines, phase, role)
    if bounds is None:
        die(f'no prior contribution to rewrite; use {collab_dispatch("speak")} to create the first contribution')
    start, end = bounds
    block = lines[start:end]

    timestamp_index: int | None = None
    marker_index: int | None = None
    for index, line in enumerate(block):
        if timestamp_index is None and TIMESTAMP_RE.match(line.strip()):
            timestamp_index = index
        if line.strip() == '<!-- collab:content-only; do-not-execute -->':
            marker_index = index
            break
    if timestamp_index is None:
        die('contribution timestamp missing')
    if marker_index is None:
        die('contribution content marker missing')

    original_timestamp = TIMESTAMP_RE.match(block[timestamp_index].strip()).group('timestamp')  # type: ignore[union-attr]
    rev_start = revision_history_start(block, marker_index + 1)
    content_end = rev_start if rev_start is not None else len(block) - 1
    existing_history = block[rev_start:len(block) - 1] if rev_start is not None else None
    prior_content = block[marker_index + 1:content_end]

    block[timestamp_index] = f'<p><em>{timestamp}</em></p>'
    history = prepend_revision_history(existing_history, original_timestamp, prior_content)
    replacement = (
        block[:marker_index + 1]
        + ['']
        + render_contribution_body(content, full_body)
        + ['']
        + history
        + [block[-1]]
    )
    return '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'


def latest_contribution_timestamp(transcript: str, phase: str, role: str) -> str | None:
    lines = transcript.splitlines()
    bounds = contribution_block_bounds(lines, phase, role)
    if bounds is None:
        return None
    start, end = bounds
    for line in lines[start:end]:
        match = TIMESTAMP_RE.match(line.strip())
        if match:
            return match.group('timestamp')
    return None


def reviewer_notice_for_rewrite(entry: dict, transcript: str, role: str) -> str | None:
    reviewer = active_reviewer_role(entry)
    if not reviewer or role == reviewer:
        return None
    phase = entry['activePhase']
    target_timestamp = latest_contribution_timestamp(transcript, phase, role)
    reviewer_timestamp = latest_contribution_timestamp(transcript, phase, reviewer)
    if target_timestamp and reviewer_timestamp and target_timestamp < reviewer_timestamp:
        return (
            f'REVIEWER-NOTICE: {role} rewrite in {phase} predates the latest '
            f'{reviewer} reviewer contribution; reviewer gate re-triggered.'
        )
    return None


def render_re_speak(
    path: Path,
    target: str,
    role: str,
    content_file: Path,
    full_body_file: Path | None = None,
    timestamp: str | None = None,
    caller_role: str | None = None,
    verbatim: bool = False,
) -> int:
    content = read_content_file(content_file)
    full_body = read_optional_content_file(full_body_file)
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'rewrite-speak-render', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] == 'Completion':
            die('rewrite-speak-render is not permitted in Completion')
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        phase = entry['activePhase']
        if role == entry['moderatorRole'] and not verbatim:
            content = polish_moderator_content(content)
        reject_hand_authored_excerpt_details(content)
        reject_full_body_details_controls(full_body)
        enforce_contribution_budget(content, phase, role, entry['moderatorRole'], verbatim)
        validate_effort_override(content, phase, role, entry['moderatorRole'])
        validate_conclusion_directive_gap(content, phase)
        validate_reviewer_conclusion_gates(content, phase, role, entry)
        validate_action_plan_shape(content, phase)
        handoff_state = parse_handoff_content(content) if phase == 'Handoff' else None
        reviewer_notice = reviewer_notice_for_rewrite(entry, transcript, role)
        render_timestamp = timestamp or format_timestamp()
        rendered = replace_latest_contribution(
            transcript,
            phase,
            role,
            content,
            render_timestamp,
            full_body,
        )
        replacement_record = contribution_store_record(
            phase,
            role,
            latest_contribution_anchor(rendered, phase, role),
            content,
            render_timestamp,
            full_body,
        )
        if handoff_state is not None:
            rendered_lines = rendered.splitlines()
            bounds = contribution_block_bounds(rendered_lines, phase, role)
            if bounds is None:
                die(f'no prior contribution to rewrite; use {collab_dispatch("speak")} to create the first contribution')
            start, end = bounds
            handoff_state['body'] = '\n'.join(contribution_body_lines(rendered_lines[start:end])).rstrip('\n')
            set_handoff_state(entry, role, handoff_state)
            rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
            print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
        replace_latest_contribution_store_record(path, entry, phase, role, replacement_record)
    if reviewer_notice:
        print(reviewer_notice)
    print_post_action_advisories(
        entry,
        role,
        effort_phase_after_speak(phase),
        None,
        next_line_after_speak(entry, role, phase, rendered),
    )
    print(entry['id'])
    return 0


def advance_phase(
    path: Path,
    target: str,
    direction: str,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    callbacks = PhaseLifecycleCallbacks(
        seal_terminal=seal_terminal,
        initialize_completion_state=initialize_completion_state,
        invalidate_verification_seal=invalidate_verification_seal,
        render_managed_header_text=render_managed_header_text,
        add_completion_summary_notice=add_completion_summary_notice,
        print_header_overwrite=print_header_overwrite,
        commit_registry_and_transcript=commit_registry_and_transcript,
        print_post_action_advisories=print_post_action_advisories,
        next_line_for_state=next_line_for_state,
    )
    return advance_phase_state(
        path,
        target,
        direction,
        callbacks,
        DEFAULT_ROLES_DIR,
        emit_json=emit_json,
        caller_role=caller_role,
    )


def record_execution(
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
    agent_id: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    callbacks = ExecutionCallbacks(
        seal_terminal=seal_terminal,
        issue_terminal=issue_terminal,
        close_eligible_after_execution=close_eligible_after_execution,
        initialize_completion_state=initialize_completion_state,
        invalidate_verification_seal=invalidate_verification_seal,
        write_seal_verdict_companion=write_seal_verdict_companion,
        next_line_after_execution=next_line_after_execution,
        render_managed_header_text=render_managed_header_text,
        append_completion_summary=append_completion_summary,
        default_close_summary=default_close_summary,
        summary_date_from_timestamp=summary_date_from_timestamp,
        print_header_overwrite=print_header_overwrite,
        commit_registry_and_transcript=commit_registry_and_transcript,
        print_post_action_advisories=print_post_action_advisories,
        print_notice_diagnostic=print_notice_diagnostic,
    )
    return record_execution_state(
        path,
        target,
        role,
        status,
        date,
        assigned_roles,
        auto_close,
        validation_result,
        validation_scope,
        touched_paths,
        callbacks,
        DEFAULT_ROLES_DIR,
        agent_id=agent_id,
        emit_json=emit_json,
        caller_role=caller_role,
    )


def normalize_issue_export_evidence(evidence_path: Path) -> list[dict]:
    try:
        raw = json.loads(evidence_path.read_text())
    except FileNotFoundError:
        die(f'issue export evidence file missing: {evidence_path}')
    except json.JSONDecodeError as exc:
        die(f'issue export evidence file invalid JSON: {evidence_path}: {exc}')
    if not isinstance(raw, dict):
        die('issue export evidence must be a JSON object')
    issues = raw.get('issues')
    if not isinstance(issues, list) or not issues:
        die('issue export evidence requires a non-empty issues list')
    normalized: list[dict] = []
    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            die(f'issue export evidence issue {index} must be an object')
        title = issue.get('title')
        if not isinstance(title, str) or not title.strip():
            die(f'issue export evidence issue {index} requires title')
        item = {'title': title.strip()}
        for optional in ('url', 'body', 'owner', 'delivery'):
            value = issue.get(optional)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                die(f'issue export evidence issue {index} {optional} must be a non-empty string')
            item[optional] = value.strip()
        requires = issue.get('requires')
        if requires is not None:
            if not isinstance(requires, list) or any(
                not isinstance(value, str) or not value.strip() for value in requires
            ):
                die(f'issue export evidence issue {index} requires must be a list of non-empty strings')
            item['requires'] = [value.strip() for value in requires]
        normalized.append(item)
    return normalized


def export_issues(
    path: Path,
    target: str,
    role: str,
    evidence_file: Path,
    timestamp: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    issues = normalize_issue_export_evidence(evidence_file)
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'export-issues', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("export-issues")} is valid only in Completion')
        if not issue_terminal(entry):
            die(f'{collab_dispatch("export-issues")} requires terminal issue')
        if role != 'pe':
            die('issue export must be authored by platform engineer role pe')
        if not has_participant(entry, role):
            die(f'issue export role must already be a participant: {role}')
        if not all_execution_completed(entry):
            die('issue export blocked: pending execution role(s) remain')
        entry['exportedIssues'] = {
            'exportedAt': timestamp or dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'exportedBy': role,
            'issues': issues,
        }
        closed = close_eligible_after_execution(entry, effective_turn_order(entry))
        if closed:
            entry['status'] = 'closed'
            if data.get('activeCollabId') == entry['id']:
                data['activeCollabId'] = None
        notice = lifecycle_status_notice('closed') if closed else None
        transcript_path = transcript_path_for_entry(entry)
        if closed and transcript_path.exists():
            transcript = transcript_path.read_text()
            rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
            if completion_summary_empty(rendered):
                rendered = append_completion_summary(
                    rendered,
                    default_close_summary(entry),
                    summary_date_from_timestamp(entry['exportedIssues']['exportedAt']),
                )
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line_for_state(entry))
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
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


def reopen_collab(
    path: Path,
    target: str,
    phase_token: str,
    caller_role: str | None = None,
) -> int:
    if phase_token == 'action-plan':
        phase = 'Action Plan'
    elif phase_token == 'handoff':
        phase = 'Handoff'
    else:
        die('reopen phase must be one of: action-plan, handoff')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'reopen')
        if entry['status'] == 'archived':
            die('record is archived')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("reopen")} is valid only after a non-success Completion verdict')
        verdict = entry.get('verdict')
        if not isinstance(verdict, dict) or verdict.get('outcome') not in {'incomplete', 'failed'}:
            die(f'{collab_dispatch("reopen")} requires a non-success Completion verdict')
        restore_target = verdict.get('restoreTarget')
        if restore_target != phase:
            expected_token = 'handoff' if restore_target == 'Handoff' else 'action-plan'
            die(f'{collab_dispatch("reopen")} phase mismatch: verdict restoreTarget is {restore_target}; expected {expected_token}')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        findings_anchor = latest_reviewer_findings_anchor(transcript)
        derived_turn_order = assert_turn_order_not_drifted(entry, phase)
        coverage_entries = execution_coverage_entries(entry)
        if coverage_entries:
            entry['reopenCoverage'] = {
                'createdAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
                'executionEntries': coverage_entries,
            }
        entry['status'] = 'open'
        entry['archived'] = False
        entry['activePhase'] = phase
        data['activeCollabId'] = entry['id']
        entry['turnOrder'] = derived_turn_order
        # Preserve completed per-role verification across the reopen rather than
        # clearing it now: at reopen time no scope has been revised yet, so the
        # scope-aware decision is deferred to the advance back into Completion
        # (after the reopened phase revises scope and re-executes). This lets a
        # reopen that re-scopes only some roles re-verify just those roles.
        initialize_completion_state(entry, 'execution', reset_rounds=True, reset_stages=False)
        invalidate_verification_seal(entry, f'reopened {phase}')
        clear_verdict(entry)
        expected_role = next((item for item in effective_turn_order(entry) if item != entry['moderatorRole']), None)
        transcript = insert_reopen_pointer(transcript, phase, findings_anchor, expected_role)
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_post_action_advisories(entry, None, None, None, next_line_for_state(entry))
    print(entry['id'])
    return 0


def print_status_view(entry: dict, transcript: str, revision: int) -> None:
    active_phase = entry['activePhase']
    completion_substate = None
    if active_phase == 'Completion' and reviewer_backed(entry):
        completion_substate = verification_substate(entry)
        active_phase = f"Completion.{completion_substate}"
    turn_order = ', '.join(effective_turn_order(entry)) or '—'
    reviewer = reviewer_role(entry)
    participants = ', '.join(
        f"{participant['role']} ({participant.get('agentId') or 'unknown'})"
        for participant in entry.get('participants', [])
    ) or '—'
    lines = [
        f"id:           {entry['id']}",
        f"slug:         {entry['slug']}",
        f"title:        {entry['title']}",
        f"status:       {entry['status']}",
        f"activePhase:  {active_phase}",
    ]
    if completion_substate is not None:
        lines.append(f"completionSubState: {completion_substate}")
    lines.extend([
        f"turnOrder:    {turn_order}",
        f"reviewerRole: {reviewer or '—'}",
    ])
    if reviewer:
        lines.append(f"reviewerMode: {reviewer_mode(entry)}")
    lines.append(f"revision:     {revision}")
    if reviewer_backed(entry) and entry['activePhase'] == 'Completion':
        unchecked = unchecked_assigned_items_by_role(transcript)
        lines.append(f"uncheckedAssignedItemsByRole: {json.dumps(unchecked, sort_keys=True)}")
    lines.append(f"participants: {participants}")
    print('\n'.join(lines))


def status_view(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        revision = registry_revision(data)
    print_status_view(entry, transcript, revision)
    return 0


def diff_command(path: Path, target: str | None) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target) if target else require_active_collab(data)
    transcript_path = path_for_entry_target(path, entry, entry['transcriptPath'])
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')
    sys.stdout.write(render_diff(diff_result(path, entry, transcript_path.read_text())))
    return 0


def render_status(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        rendered, _header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
        transcript = rendered
        revision = registry_revision(data)

    print_status_view(entry, transcript, revision)
    return 0


def re_summarize_collab(path: Path, target: str, summary_file: Path, date: str | None = None) -> int:
    if not summary_file.exists():
        die(f'summary file missing: {summary_file}')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] == 'archived':
            die('record is archived')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        summary_date = date or dt.date.today().isoformat()
        rendered = replace_latest_summary(transcript_path.read_text(), summary_file.read_text(), summary_date)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(entry['id'])
    return 0


def render_participants(path: Path, target: str, roles_dir: Path) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(transcript_path)
    return 0


def commit_registry_and_transcript(
    registry_path: Path,
    data: dict,
    transcript_path: Path,
    transcript_text: str,
) -> None:
    """Commit registry and transcript updates with rollback on known write failures.

    The registry file is replaced first, then the transcript file. If either
    replace fails, the helper restores the pre-operation contents it could read
    and reports which file may be inconsistent. This is a best-effort two-file
    transaction, not a filesystem-level atomic commit.
    """
    registry_before = registry_path.read_text() if registry_path.exists() else None
    sync_registry_project_metadata(data)
    retire_legacy_registry_fields(data)
    registry_event = prepare_registry_event(registry_path, registry_before, data, 'registry-write')
    bump_registry_revision(data)
    if registry_event is not None:
        bump_registry_event_index(data)
        registry_event = finalize_registry_event(data, registry_event)
    validate_registry(data, registry_path)
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')

    transcript_before = transcript_path.read_text()
    registry_after = json.dumps(data, indent=2) + '\n'
    registry_tmp = registry_path.with_name(f'{registry_path.name}.tmp')
    transcript_tmp = transcript_path.with_name(f'{transcript_path.name}.tmp')

    try:
        registry_tmp.write_text(registry_after)
        transcript_tmp.write_text(transcript_text)
        registry_tmp.replace(registry_path)
        transcript_tmp.replace(transcript_path)
        if registry_event is not None:
            write_revision_event(registry_path, registry_event)
    except OSError as exc:
        inconsistent: list[str] = []
        try:
            if registry_before is None:
                registry_path.unlink(missing_ok=True)
            else:
                registry_path.write_text(registry_before)
        except OSError:
            inconsistent.append(str(registry_path))
        try:
            transcript_path.write_text(transcript_before)
        except OSError:
            inconsistent.append(str(transcript_path))
        registry_tmp.unlink(missing_ok=True)
        transcript_tmp.unlink(missing_ok=True)
        if inconsistent:
            die(f'collab write failed; inconsistent state may remain: {", ".join(inconsistent)}: {exc}')
        die(f'collab write failed; restored pre-operation state: {exc}')


configure_seal_verification_facade(
    commit_registry_and_transcript=commit_registry_and_transcript,
    next_line_for_state=next_line_for_state,
    print_post_action_advisories=print_post_action_advisories,
)


def commit_new_collab_artifacts(
    registry_path: Path,
    data: dict,
    entry: dict,
    transcript_path: Path,
    transcript_text: str,
    contribution_store: dict,
) -> None:
    registry_before = registry_path.read_text() if registry_path.exists() else None
    sync_registry_project_metadata(data)
    retire_legacy_registry_fields(data)
    registry_event = prepare_registry_event(registry_path, registry_before, data, 'registry-write')
    bump_registry_revision(data)
    if registry_event is not None:
        bump_registry_event_index(data)
        registry_event = finalize_registry_event(data, registry_event)
    validate_registry(data, registry_path)

    contribution_store_path = contribution_store_path_for_entry(registry_path, entry)
    artifacts = [
        transcript_path,
        contribution_store_path,
    ]
    for artifact_path in artifacts:
        if artifact_path.exists():
            die(f'record already exists: {artifact_path}')

    store_text = json.dumps(contribution_store, indent=2, ensure_ascii=True) + '\n'
    registry_after = json.dumps(data, indent=2) + '\n'
    registry_tmp = registry_path.with_name(f'{registry_path.name}.tmp')
    artifact_payloads = [
        (transcript_path, transcript_text),
        (contribution_store_path, store_text),
    ]
    artifact_tmps = [
        (artifact_path.with_name(f'{artifact_path.name}.tmp'), artifact_path)
        for artifact_path, _text in artifact_payloads
    ]

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    for artifact_path, _text in artifact_payloads:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        registry_tmp.write_text(registry_after)
        for (artifact_path, text), (tmp_path, _target_path) in zip(artifact_payloads, artifact_tmps):
            tmp_path.write_text(text)
        registry_tmp.replace(registry_path)
        for tmp_path, target_path in artifact_tmps:
            tmp_path.replace(target_path)
        if registry_event is not None:
            write_revision_event(registry_path, registry_event)
    except OSError as exc:
        inconsistent: list[str] = []
        try:
            if registry_before is None:
                registry_path.unlink(missing_ok=True)
            else:
                registry_path.write_text(registry_before)
        except OSError:
            inconsistent.append(str(registry_path))
        for artifact_path, _text in artifact_payloads:
            try:
                artifact_path.unlink(missing_ok=True)
            except OSError:
                inconsistent.append(str(artifact_path))
        registry_tmp.unlink(missing_ok=True)
        for tmp_path, _target_path in artifact_tmps:
            tmp_path.unlink(missing_ok=True)
        if inconsistent:
            die(f'collab init failed; inconsistent state may remain: {", ".join(inconsistent)}: {exc}')
        die(f'collab init failed; restored pre-operation state: {exc}')


def open_browser_uri(uri: str, opener: Callable[[str], bool] = webbrowser.open_new_tab) -> str | None:
    try:
        opened = opener(uri)
    except Exception as exc:
        return f'{type(exc).__name__}: {exc}'
    if not opened:
        return 'no browser available'
    return None


def parser_subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def action_display_name(action: argparse.Action) -> str:
    if action.option_strings:
        return ', '.join(action.option_strings)
    return action.dest


def action_value_shape(action: argparse.Action) -> str:
    if action.option_strings:
        if action.nargs == 0:
            return 'flag'
        return 'value'
    if action.nargs in (None, 1):
        return 'required'
    return f'nargs={action.nargs}'


def route_help_command(route_tokens: list[str]) -> int:
    if not route_tokens:
        die('<route> is required; e.g., (help collab init), (help collab run plan)')
    if any(not re.match(r'^[A-Za-z0-9_-]+$', token) for token in route_tokens):
        die(f'route not found: {" ".join(route_tokens)}; valid routes are listed in commands/commands.md')
    namespace = route_tokens[0]
    if len(route_tokens) == 1:
        route_path = ROOT / 'commands' / namespace / 'index.md'
    else:
        route_path = ROOT / 'commands' / namespace / '-'.join(route_tokens[1:]) / 'index.md'
    commands_root = (ROOT / 'commands').resolve()
    resolved = route_path.resolve()
    if commands_root not in resolved.parents:
        die(f'route not found: {" ".join(route_tokens)}; valid routes are listed in commands/commands.md')
    try:
        content = route_path.read_text()
    except OSError:
        die(f'route not found: {" ".join(route_tokens)}; valid routes are listed in commands/commands.md')
    print(content, end='')
    return 0


def render_registry_cli_doc() -> str:
    parser = build_parser()
    subcommands = parser_subcommands(parser)
    lines = [
        '# Registry CLI',
        '',
        '_Generated by `commands/collab/engine/registry.py registry-cli-doc`; do not edit by hand._',
        '',
        '## Global options',
        '',
        '- `--registry <path>` optional; bypasses the project-id state resolver.',
        '',
        '## Subcommands',
        '',
    ]
    for name in sorted(subcommands):
        subparser = subcommands[name]
        usage = subparser.format_usage().strip()
        if usage.startswith('usage: '):
            usage = usage[len('usage: '):]
        lines.extend([f'### `{name}`', '', f'Usage: `{usage}`', ''])
        actions = [
            action for action in subparser._actions
            if action.dest != 'help' and action.default is not argparse.SUPPRESS
        ]
        if actions:
            lines.append('Arguments and flags:')
            for action in actions:
                required = 'required' if getattr(action, 'required', False) or not action.option_strings else 'optional'
                lines.append(
                    f'- `{action_display_name(action)}` {required}; {action_value_shape(action)}'
                )
            lines.append('')
        else:
            lines.extend(['Arguments and flags: none', ''])
    return '\n'.join(lines).rstrip() + '\n'


def init_collab(
    path: Path,
    tokens: list[str],
    roles_dir: Path,
    opener: Callable[[str], bool] = webbrowser.open_new_tab,
) -> int:
    title, agent_id, reviewer, open_requested, participant_verification, terminal, work_repo_raw = parse_init_tokens(tokens)
    with registry_lock(path):
        data = load_registry_or_bootstrap(path)
        ensure_init_project_metadata(data, path)
        date = dt.date.today().isoformat()
        slug = normalize_slug(title)
        collab_id = f'{date}-{slug}'
        transcript_rel = f'records/{collab_id}.md'
        transcript_path = Path(transcript_rel)

        if transcript_path.exists():
            die(f'record already exists: {transcript_path}')
        if any(entry['id'] == collab_id for entry in data['collabs']):
            die(f'registry collision: {collab_id}')
        if any(entry['slug'] == slug for entry in data['collabs']):
            die(f'registry collision: {slug}')

        sequence = next_sequence(data)
        if any(entry.get('sequence') == sequence for entry in data['collabs']):
            die(f'registry collision: sequence {sequence}')

        load_role(roles_dir, 'mod')
        if reviewer:
            load_role(roles_dir, reviewer)

        entry = {
            'id': collab_id,
            'slug': slug,
            'title': title,
            'description': f'Moderated discussion of {title}.',
            'createdAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'terminal': terminal,
            'status': 'open',
            'activePhase': 'Audit',
            'moderatorRole': 'mod',
            'participants': [{'role': 'mod', 'agentId': agent_id}],
            'turnOrder': ['mod'],
            'transcriptPath': transcript_rel,
            'sequence': sequence,
            'archived': False,
            'execution': {},
        }
        if work_repo_raw is not None:
            work_repo = resolve_git_work_tree(work_repo_raw, 'workRepo')
        else:
            work_repo = default_init_work_repo_root()
        assert_work_repo_not_framework_for_external_project(work_repo, 'workRepo')
        entry['workRepo'] = str(work_repo)
        if reviewer:
            entry['reviewerRole'] = reviewer
            entry['reviewerMode'] = DEFAULT_REVIEWER_MODE
            entry['reviewerOptionalPhases'] = list(DEFAULT_REVIEWER_OPTIONAL_PHASES)
        if terminal == 'seal':
            entry['verification'] = {
                'rounds': 0,
                'cap': DEFAULT_VERIFICATION_CAP,
                'subState': 'participant' if participant_verification else 'seal',
                'participantVerification': participant_verification,
                'participants': {},
            }

        nextdata = deepcopy(data)
        count_caller_declined_agent_id_write(nextdata, agent_id)
        nextdata['collabs'].append(entry)
        nextdata['activeCollabId'] = collab_id
        rendered_timestamp = format_banner_timestamp()
        rendered = render_initial_transcript(title, entry, roles_dir, rendered_timestamp)
        transcript_path = path_for_entry_target(path, entry, entry['transcriptPath'])
        contribution_store = empty_contribution_store(rendered_timestamp)
        commit_new_collab_artifacts(path, nextdata, entry, transcript_path, rendered, contribution_store)
    print(entry['transcriptPath'])
    if open_requested:
        file_uri = path_for_entry_target(path, entry, entry['transcriptPath']).resolve().as_uri()
        open_failure = open_browser_uri(file_uri, opener)
        if open_failure is None:
            print(f'OPEN: {file_uri}')
        else:
            print(f'OPEN: failed: {open_failure}')
    return 0


def join_participants(
    path: Path,
    target: str,
    role: str,
    agent_id: str | None,
    roles_dir: Path,
    emit_json: bool = False,
) -> int:
    normalized_agent_id = normalize_join_agent_id(agent_id)
    role_data = load_role(roles_dir, role)
    if not role_is_joinable(role_data):
        die(f'role not joinable: {role}')
    recorded_agent_id = normalized_agent_id
    identity_warning: str | None = None
    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        existing_agent_id = participant_agent_id(current_entry, role)
        if existing_agent_id:
            recorded_agent_id = existing_agent_id
            if existing_agent_id != normalized_agent_id:
                identity_warning = (
                    f'IDENTITY-WARN: {role} already joined as {existing_agent_id}; '
                    f'supplied agentId {normalized_agent_id} ignored'
                )

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        if add_participant_to_entry(next_entry, role, normalized_agent_id):
            count_caller_declined_agent_id_write(nextdata, normalized_agent_id)
        validate_registry(nextdata, path)

        transcript_path = transcript_path_for_entry(next_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()

        rendered, header_changed = render_managed_header_text(transcript, next_entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, nextdata, transcript_path, rendered)
    print_post_action_advisories(
        next_entry,
        role,
        next_entry['activePhase'],
        None,
        f'NEXT: Run {collab_dispatch("show policy")} before first speak.',
    )
    print(f'TRANSCRIPT: {transcript_view_command_for_role(next_entry, role)}')
    print(f'IDENTITY: {role} {recorded_agent_id}')
    if identity_warning:
        print(identity_warning)
    print(' '.join(participant_roles(next_entry)))
    if emit_json:
        print(json.dumps({
            'agentId': recorded_agent_id,
            'freshRegistryRead': True,
            'identityWarning': identity_warning,
            'nextTranscriptCommand': transcript_view_command_for_role(next_entry, role),
            'participants': participant_roles(next_entry),
            'resumeCommand': resume_command_invocation(next_entry, role),
            'target': next_entry['id'],
        }, sort_keys=True))
    return 0


def write_guard(route: str, paths: list[str]) -> int:
    if not paths:
        die('write-guard requires at least one path')
    if route == 'execute':
        print('ok')
        return 0
    for item in paths:
        normalized = Path(item).as_posix()
        if normalized.startswith('./'):
            normalized = normalized[2:]
        if Path(item).is_absolute() or not (
            normalized in {'registry.json', 'registry.json.lock', 'records'}
            or normalized.startswith('records/')
        ):
            die(f'route may only write under the user-scope collab state root: {route}: {item}')
    print('ok')
    return 0


def archive_collab(
    path: Path,
    target: str,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'archive')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        entry['status'] = 'archived'
        entry['archived'] = True
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    notice = lifecycle_status_notice('archived')
    print_post_action_advisories(entry, None, None, notice, next_line_for_state(entry))
    print(entry['id'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def open_collab(path: Path, target: str, caller_role: str | None = None) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'open')
        if entry['status'] == 'archived' or entry.get('archived'):
            die('archived records must be restored before reopening')
        if entry['status'] == 'open':
            print(f'record already open: {entry["id"]}')
            return 0
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        entry['status'] = 'open'
        entry['archived'] = False
        data['activeCollabId'] = entry['id']
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(entry['id'])
    return 0


def close_collab(
    path: Path,
    target: str,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'close')
        if entry['status'] == 'archived':
            die('record is archived')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        violations = completed_execution_unchecked_items(entry, transcript)
        if violations:
            details = ', '.join(
                f"{item['role']}={item['uncheckedCount']}" for item in violations
            )
            die(
                'close blocked: completed execution has unchecked assigned Action Plan item(s): '
                f'{details}; loop target: Handoff for missing execution evidence'
            )
        if issue_terminal(entry) and entry['activePhase'] == 'Completion':
            if not all_execution_completed(entry):
                die('close blocked: issue terminal requires completed execution')
            if not exported_issue_handoff_present(entry):
                die('close blocked: issue terminal requires exported issue handoff evidence')
        elif seal_terminal(entry) and reviewer_backed(entry) and entry['activePhase'] == 'Completion':
            seal = entry.get('verificationSeal')
            if not isinstance(seal, dict):
                die('close blocked: reviewer-backed Completion requires verificationSeal')
            invalidate_seal_on_content_drift(entry)
            if seal.get('stale'):
                write_seal_verdict_companion(path, entry)
                save_registry(path, data)
                reason = seal.get('staleReason') or 'unknown'
                die(f'close blocked: verificationSeal is stale: {reason}')
            if not successful_verdict(entry):
                die('close blocked: reviewer-backed Completion requires verdict outcome success')
        entry['status'] = 'closed'
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    notice = lifecycle_status_notice('closed')
    print_post_action_advisories(entry, None, None, notice, next_line_for_state(entry))
    print(entry['id'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def audit_closed(path: Path) -> int:
    data = load_registry(path)
    findings: list[dict] = []
    for entry in data['collabs']:
        if entry['status'] != 'closed':
            continue
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        violations = completed_execution_unchecked_items(entry, transcript)
        for violation in violations:
            findings.append({
                'target': entry['id'],
                'role': violation['role'],
                'uncheckedCount': violation['uncheckedCount'],
            })
        findings.extend(effort_override_audit_items(entry['id'], transcript))
    print(json.dumps(findings, sort_keys=True))
    return 0


def delete_collab(path: Path, target: str, confirmed: bool, caller_role: str | None = None) -> int:
    if not confirmed:
        die('delete requires --yes confirmation')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'delete')
        transcript_path = transcript_path_for_entry(entry)
        contribution_store_path = contribution_store_path_for_entry(path, entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        data['collabs'] = [candidate for candidate in data['collabs'] if candidate['id'] != entry['id']]
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        for owned_path in (transcript_path, contribution_store_path):
            if owned_path.exists():
                owned_path.unlink()
        save_registry(path, data)
    print(entry['id'])
    return 0


def flag_inventory(spec_path: Path = DEFAULT_FLAG_TAXONOMY_PATH) -> int:
    if not spec_path.exists():
        die(f'flag taxonomy spec missing: {spec_path}')
    by_class: dict[str, list[tuple[str, str, str]]] = {
        'advisory': [],
        'helper-enforced': [],
        'generator-derived': [],
    }
    current_command = ''
    for line in spec_path.read_text().splitlines():
        heading = re.match(r'^###\s+(.+)$', line)
        if heading:
            current_command = heading.group(1)
            continue
        match = FLAG_ROW_RE.match(line)
        if not match or match.group('flag') == 'Flag':
            continue
        flag_class = match.group('class')
        if flag_class not in by_class:
            die(f'flag taxonomy spec has unknown class: {flag_class}')
        by_class[flag_class].append((current_command, match.group('flag'), match.group('notes').strip()))
    for flag_class, rows in by_class.items():
        print(f'## {flag_class}')
        if not rows:
            print('- none')
        for command, flag, notes in rows:
            print(f'- {command}: `{flag}` — {notes}')
        print()
    return 0


def retract_latest_contribution(
    path: Path,
    target: str,
    role: str,
    reason: str | None,
    timestamp: str | None = None,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'retract-speak', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] == 'Completion':
            die('retract-speak is not permitted after Completion')
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        lines = transcript.splitlines()
        bounds = contribution_block_bounds(lines, entry['activePhase'], role)
        if bounds is None:
            die(f'no contribution found for {role} in {entry["activePhase"]}')
        start, end = bounds
        anchor = latest_contribution_anchor(transcript, entry['activePhase'], role)
        block = lines[start:end]
        marker_index: int | None = None
        for index, line in enumerate(block):
            if line.strip() == '<!-- collab:content-only; do-not-execute -->':
                marker_index = index
                break
        if marker_index is None:
            die('contribution content marker missing')
        existing_body = '\n'.join(block[marker_index + 1:len(block) - 1]).strip()
        if existing_body.startswith('RETRACTED:'):
            die(f'contribution already retracted for {role} in {entry["activePhase"]}')
        summary = reason.strip() if reason and reason.strip() else 'No reason supplied'
        stamp = timestamp or format_timestamp()
        tombstone = [
            'RETRACTED: contribution withdrawn; retained for audit history.',
            f'RETRACTION REASON: {summary}',
            f'RETRACTION TIMESTAMP: {stamp}',
            '',
            *rendered_retracted_content_block(existing_body),
        ]
        replacement = block[:marker_index + 1] + [''] + tombstone + [''] + [block[-1]]
        rendered = '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'
        commit_registry_and_transcript(path, data, transcript_path, rendered)
        mark_contribution_store_record_retracted(path, entry, anchor, summary, stamp)
    print(entry['id'])
    print('retracted')
    return 0


def stale_registry_lock_message(path: Path, now: float | None = None) -> str | None:
    lock_path = path.with_name(f'{path.name}.lock')
    if not lock_path.exists():
        return None
    age = (now if now is not None else dt.datetime.now().timestamp()) - lock_path.stat().st_mtime
    if age < STALE_LOCK_SECONDS:
        return None
    try:
        with lock_path.open('a+') as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return (
                    f'stale registry lock: {lock_path}; a collab command has held it for '
                    f'at least {STALE_LOCK_SECONDS} seconds. Confirm whether a collab command '
                    'is stuck before terminating it.'
                )
            os.utime(lock_path, None)
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    except OSError as exc:
        return f'stale registry lock check failed: {lock_path}: {exc}'
    return None


def validate_command(path: Path) -> int:
    load_registry(path)
    stale_lock = stale_registry_lock_message(path)
    if stale_lock:
        die(stale_lock)
    validate_source_contracts()
    print('registry OK')
    return 0


def require_source_text(path: Path, needle: str, label: str) -> None:
    if not path.exists():
        die(f'source contract missing {label}: {path.relative_to(DEFAULT_CONFIG_ROOT)}')
    if needle not in path.read_text():
        die(f'source contract missing {label}: {path.relative_to(DEFAULT_CONFIG_ROOT)}')


def validate_source_contracts() -> None:
    if not DEFAULT_FLAG_TAXONOMY_PATH.exists():
        die(f'source contract missing flag taxonomy: {DEFAULT_FLAG_TAXONOMY_PATH.relative_to(DEFAULT_CONFIG_ROOT)}')

    seal_verification = DEFAULT_CONFIG_ROOT / 'commands/collab/seal-verification/index.md'
    require_source_text(seal_verification, 'restore-route-recovery', 'restore-route recovery anchor')
    require_source_text(seal_verification, '(collab show verdict)', 'restore-route verdict inspection')
    require_source_text(seal_verification, '(collab reopen action-plan)', 'restore-route action-plan reopen')
    require_source_text(seal_verification, '(collab reopen handoff)', 'restore-route handoff reopen')
    require_source_text(seal_verification, '(collab run plan)', 'restore-route rerun step')
    require_source_text(seal_verification, '(collab seal verification)', 'restore-route reseal step')

    invariants = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/invariants.md'
    require_source_text(invariants, 'Rollback triggers', 'rollback trigger section')
    require_source_text(invariants, 'Observation backlog', 'observation backlog section')
    validate_planned_route_prerequisites(DEFAULT_CONFIG_ROOT)


def registry_path_command(path: Path) -> int:
    print(path)
    return 0


def role_row_command(roles_dir: Path, role: str, index: int) -> int:
    print(participant_row(load_role(roles_dir, role), index))
    return 0


def roles_command(roles_dir: Path) -> int:
    index = 1
    for data in role_catalog(roles_dir):
        if not role_is_joinable(data):
            continue
        print(participant_row(data, index))
        index += 1
    return 0


def reviewer_state_command(path: Path, target: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    print(json.dumps(reviewer_state(entry), sort_keys=True))
    return 0


def handoff_state_command(path: Path, target: str, role: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if not has_participant(entry, role):
        die(f'handoff role must already be a participant: {role}')
    state = handoff_state_for_role(entry, role) or {}
    print(json.dumps(state, sort_keys=True))
    return 0


def timestamp_command() -> int:
    print(format_timestamp())
    return 0


def banner_timestamp_command() -> int:
    print(format_banner_timestamp())
    return 0


def summary_role_command(line: str) -> int:
    role = summary_role(line)
    if role is None:
        die('summary role unavailable')
    print(role)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Shared collab registry helper.')
    parser.add_argument(
        '--registry',
        default=None,
        help='Path to the collab registry JSON file; bypasses the project-id state resolver.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('validate')
    subparsers.add_parser('registry-path')
    registry_cli_doc_parser = subparsers.add_parser('registry-cli-doc')
    registry_cli_doc_parser.add_argument('--check', action='store_true')
    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('--status', choices=sorted(ALLOWED_STATUSES))
    log_parser = subparsers.add_parser('log')
    log_parser.add_argument('target')
    flag_inventory_parser = subparsers.add_parser('flag-inventory')
    flag_inventory_parser.add_argument('--spec', default=str(DEFAULT_FLAG_TAXONOMY_PATH))
    help_parser = subparsers.add_parser('help')
    help_parser.add_argument('route', nargs='*')
    subparsers.add_parser('timestamp')
    subparsers.add_parser('banner-timestamp')

    role_row_parser = subparsers.add_parser('role-row')
    role_row_parser.add_argument('role')
    role_row_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    role_row_parser.add_argument('--index', type=int, default=1)

    roles_parser = subparsers.add_parser('roles')
    roles_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))

    summary_role_parser = subparsers.add_parser('summary-role')
    summary_role_parser.add_argument('line')

    reviewer_state_parser = subparsers.add_parser('reviewer-state')
    reviewer_state_parser.add_argument('target')

    handoff_state_parser = subparsers.add_parser('handoff-state')
    handoff_state_parser.add_argument('target')
    handoff_state_parser.add_argument('role')

    activate_parser = subparsers.add_parser('activate')
    activate_parser.add_argument('target')

    open_parser = subparsers.add_parser('open')
    open_parser.add_argument('target')
    open_parser.add_argument('--caller-role')

    init_parser = subparsers.add_parser(
        'init',
        usage=(
            '%(prog)s --agent-id <agentId> [--reviewer <role>] '
            '[--terminal <seal|issue>] [--no-participant-verification] [--work-repo <path>] [--open] <name>'
        ),
        description='Create a registry-backed collab record.',
    )
    init_parser.add_argument('--agent-id', action='append')
    init_parser.add_argument('--reviewer', action='append')
    init_parser.add_argument('--terminal', action='append')
    init_parser.add_argument('--work-repo', action='append')
    init_parser.add_argument('--no-participant-verification', dest='participant_verification', action='store_false', default=True)
    init_parser.add_argument('--open', action='store_true')
    init_parser.add_argument('name', nargs='*')

    join_participants_parser = subparsers.add_parser('join-participants')
    join_participants_parser.add_argument('target')
    join_participants_parser.add_argument('role')
    join_participants_parser.add_argument('--agent-id', required=True)
    join_participants_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    join_participants_parser.add_argument('--json', action='store_true')

    remove_participant_parser = subparsers.add_parser('remove-participant')
    remove_participant_parser.add_argument('target')
    remove_participant_parser.add_argument('role')
    remove_participant_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    remove_participant_parser.add_argument('--caller-role')

    set_parser = subparsers.add_parser('set')
    set_parser.add_argument('target')
    set_parser.add_argument('field')
    set_parser.add_argument('value', nargs='?')
    set_parser.add_argument('--force', action='store_true')
    set_parser.add_argument('--clear', action='store_true')
    set_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    set_parser.add_argument('--caller-role')

    unset_parser = subparsers.add_parser('unset')
    unset_parser.add_argument('target')
    unset_parser.add_argument('field')
    unset_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    unset_parser.add_argument('--caller-role')

    effort_state_parser = subparsers.add_parser('effort-state')
    effort_state_parser.add_argument('target')
    effort_state_parser.add_argument('role')
    effort_state_parser.add_argument('--effort-defaults', default=str(DEFAULT_EFFORT_PATH))

    audit_effort_matrix_parser = subparsers.add_parser('audit-effort-matrix')
    audit_effort_matrix_parser.add_argument('--effort-defaults', default=str(DEFAULT_EFFORT_PATH))
    audit_effort_matrix_parser.add_argument('--agent-model', default=str(DEFAULT_AGENT_MODEL_PATH))

    advance_parser = subparsers.add_parser('advance')
    advance_parser.add_argument('target')
    advance_parser.add_argument('direction', choices=['next', 'prev'])
    advance_parser.add_argument('--json', action='store_true')
    advance_parser.add_argument('--caller-role')

    speak_parser = subparsers.add_parser('speak-lifecycle')
    speak_parser.add_argument('target')
    speak_parser.add_argument('contributors', nargs='+')

    speak_state_parser = subparsers.add_parser('speak-state')
    speak_state_parser.add_argument('target')
    speak_state_parser.add_argument('role')
    speak_state_parser.add_argument('--resume', action='store_true')

    speak_live_parser = subparsers.add_parser('speak-lifecycle-live')
    speak_live_parser.add_argument('target')

    speak_render_parser = subparsers.add_parser('speak-render')
    speak_render_parser.add_argument('target')
    speak_render_parser.add_argument('role')
    speak_render_parser.add_argument('--content-file', required=True)
    speak_render_parser.add_argument('--full-body-file')
    speak_render_parser.add_argument('--observed-revision', type=int, required=True)
    speak_render_parser.add_argument('--timestamp')
    speak_render_parser.add_argument('--json', action='store_true')
    speak_render_parser.add_argument('--caller-role')
    speak_render_parser.add_argument('--verbatim', action='store_true')

    re_speak_render_parser = subparsers.add_parser('rewrite-speak-render')
    re_speak_render_parser.add_argument('target')
    re_speak_render_parser.add_argument('role')
    re_speak_render_parser.add_argument('--content-file', required=True)
    re_speak_render_parser.add_argument('--full-body-file')
    re_speak_render_parser.add_argument('--timestamp')
    re_speak_render_parser.add_argument('--caller-role')
    re_speak_render_parser.add_argument('--verbatim', action='store_true')

    retract_speak_parser = subparsers.add_parser('retract-speak')
    retract_speak_parser.add_argument('target')
    retract_speak_parser.add_argument('role')
    retract_speak_parser.add_argument('--reason')
    retract_speak_parser.add_argument('--timestamp')
    retract_speak_parser.add_argument('--caller-role')

    execution_parser = subparsers.add_parser('execution')
    execution_parser.add_argument('target')
    execution_parser.add_argument('role')
    execution_parser.add_argument('status', choices=sorted(ALLOWED_EXECUTION_STATUSES))
    execution_parser.add_argument('date')
    execution_parser.add_argument('--assigned-role', action='append', default=[])
    execution_parser.add_argument('--auto-close', action='store_true')
    execution_parser.add_argument('--validation-result')
    execution_parser.add_argument('--validation-scope', choices=sorted(ALLOWED_VALIDATION_SCOPES))
    execution_parser.add_argument('--touched-path', action='append', default=[])
    execution_parser.add_argument('--agent-id')
    execution_parser.add_argument('--json', action='store_true')
    execution_parser.add_argument('--caller-role')

    export_issues_parser = subparsers.add_parser('export-issues')
    export_issues_parser.add_argument('target')
    export_issues_parser.add_argument('role')
    export_issues_parser.add_argument('--evidence-file', required=True)
    export_issues_parser.add_argument('--timestamp')
    export_issues_parser.add_argument('--json', action='store_true')
    export_issues_parser.add_argument('--caller-role')

    repair_execution_parser = subparsers.add_parser('repair-execution-provenance')
    repair_execution_parser.add_argument('target')
    repair_execution_parser.add_argument('role')
    repair_execution_parser.add_argument('--work-repo')
    repair_execution_parser.add_argument('--commit', action='append', default=[])
    repair_execution_parser.add_argument('--caller-role')

    execute_spawn_parser = subparsers.add_parser('execute-spawn')
    execute_spawn_parser.add_argument('target')
    execute_spawn_parser.add_argument('role')
    execute_spawn_parser.add_argument('--scope', required=True)
    execute_spawn_parser.add_argument('--sibling-scope', action='append', default=[])
    execute_spawn_parser.add_argument('--returned-path', action='append', default=[])

    transcript_repair_parser = subparsers.add_parser('transcript-repair')
    transcript_repair_parser.add_argument('target')
    transcript_repair_parser.add_argument('--touch-execution-evidence', action='store_true')
    transcript_repair_parser.add_argument('--caller-role')

    out_of_scope_patch_parser = subparsers.add_parser('out-of-scope-patch')
    out_of_scope_patch_parser.add_argument('target')
    out_of_scope_patch_parser.add_argument('role')
    out_of_scope_patch_parser.add_argument('--path', required=True)
    out_of_scope_patch_parser.add_argument('--caller-role')

    transcript_view_parser = subparsers.add_parser('transcript-view')
    transcript_view_parser.add_argument('target')
    transcript_view_parser.add_argument('phase', choices=PHASES)
    transcript_view_parser.add_argument('--raw', action='store_true')

    summarize_parser = subparsers.add_parser('summarize')
    summarize_parser.add_argument('target')
    summarize_parser.add_argument('--date')

    participant_verify_state_parser = subparsers.add_parser('participant-verify-state')
    participant_verify_state_parser.add_argument('target')
    participant_verify_state_parser.add_argument('role')
    participant_verify_state_parser.add_argument('--resume', action='store_true')

    participant_verify_render_parser = subparsers.add_parser('participant-verify-render')
    participant_verify_render_parser.add_argument('target')
    participant_verify_render_parser.add_argument('role')
    participant_verify_render_parser.add_argument('--observed-revision', type=int, required=True)
    participant_verify_render_parser.add_argument('--audit-file', required=True)
    participant_verify_render_parser.add_argument('--remediation-file', required=True)
    participant_verify_render_parser.add_argument('--final-audit-file', required=True)
    participant_verify_render_parser.add_argument('--status', choices=['completed', 'failed'], required=True)
    participant_verify_render_parser.add_argument('--touched-path', action='append', default=[])
    participant_verify_render_parser.add_argument('--execution-agent-id')
    participant_verify_render_parser.add_argument('--audit-agent-id')
    participant_verify_render_parser.add_argument('--remediation-agent-id')
    participant_verify_render_parser.add_argument('--timestamp')
    participant_verify_render_parser.add_argument('--caller-role')

    seal_state_parser = subparsers.add_parser('seal-state')
    seal_state_parser.add_argument('target')
    seal_state_parser.add_argument('role', nargs='?')
    seal_state_parser.add_argument('--resume', action='store_true')

    seal_render_parser = subparsers.add_parser('seal-render')
    seal_render_parser.add_argument('target')
    seal_render_parser.add_argument('role')
    seal_render_parser.add_argument('--observed-revision', type=int, required=True)
    seal_render_parser.add_argument('--cap-exit')
    seal_render_parser.add_argument('--outcome')
    seal_render_parser.add_argument('--restore-target')
    seal_render_parser.add_argument('--restore-reason')
    seal_render_parser.add_argument('--evidence')
    seal_render_parser.add_argument('--failure-category')
    seal_render_parser.add_argument('--null-result', action='store_true')
    seal_render_parser.add_argument('--json', action='store_true')
    seal_render_parser.add_argument('--caller-role')

    restart_verification_parser = subparsers.add_parser('restart-verification')
    restart_verification_parser.add_argument('target')
    restart_verification_parser.add_argument('--caller-role')

    reopen_parser = subparsers.add_parser('reopen')
    reopen_parser.add_argument('target')
    reopen_parser.add_argument('phase', choices=['action-plan', 'handoff'])
    reopen_parser.add_argument('--caller-role')

    show_verdict_parser = subparsers.add_parser('show-verdict')
    show_verdict_parser.add_argument('target')

    re_summarize_parser = subparsers.add_parser('rewrite-summary')
    re_summarize_parser.add_argument('target')
    re_summarize_parser.add_argument('--summary-file', required=True)
    re_summarize_parser.add_argument('--date')

    close_parser = subparsers.add_parser('close')
    close_parser.add_argument('target')
    close_parser.add_argument('--json', action='store_true')
    close_parser.add_argument('--caller-role')

    subparsers.add_parser('audit-closed')

    archive_parser = subparsers.add_parser('archive')
    archive_parser.add_argument('target')
    archive_parser.add_argument('--json', action='store_true')
    archive_parser.add_argument('--caller-role')

    delete_parser = subparsers.add_parser('delete')
    delete_parser.add_argument('target')
    delete_parser.add_argument('--yes', action='store_true')
    delete_parser.add_argument('--caller-role')

    diff_parser = subparsers.add_parser('diff')
    diff_parser.add_argument('target', nargs='?')

    render_status_parser = subparsers.add_parser('render-status')
    render_status_parser.add_argument('target')

    status_view_parser = subparsers.add_parser('status-view')
    status_view_parser.add_argument('target')

    render_participants_parser = subparsers.add_parser('render-participants')
    render_participants_parser.add_argument('target')
    render_participants_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))

    write_guard_parser = subparsers.add_parser('write-guard')
    write_guard_parser.add_argument('route')
    write_guard_parser.add_argument('paths', nargs='+')

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args, unknown_args = parser.parse_known_args(argv)
    if unknown_args:
        if args.command == 'init':
            for item in unknown_args:
                if item.startswith('--'):
                    die(f'unknown flag: {item}')
        parser.error(f'unrecognized arguments: {" ".join(unknown_args)}')
    for path_arg in ('content_file', 'full_body_file', 'summary_file', 'evidence_file'):
        if hasattr(args, path_arg) and getattr(args, path_arg):
            setattr(args, path_arg, str(Path(getattr(args, path_arg)).resolve()))

    if args.registry is None:
        path, use_state_root = resolve_default_registry_path(args.command)
        if use_state_root:
            identity_path = find_project_identity_path(Path.cwd())
            if identity_path is not None:
                set_resolved_work_repo_root(identity_path.parent)
            path = path.resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            os.chdir(path.parent)
    else:
        path = Path(args.registry)

    if args.command == 'validate':
        return validate_command(path)
    if args.command == 'registry-path':
        return registry_path_command(path)
    if args.command == 'registry-cli-doc':
        rendered = render_registry_cli_doc()
        generated_path = ROOT / 'generated/registry-cli.md'
        if args.check:
            if not generated_path.exists() or generated_path.read_text() != rendered:
                die('generated/registry-cli.md is stale; run commands/collab/engine/registry.py registry-cli-doc > generated/registry-cli.md')
            return 0
        print(rendered, end='')
        return 0
    if args.command == 'list':
        return list_collabs(load_registry(path), args.status)
    if args.command == 'log':
        return log_command(path, args.target)
    if args.command == 'flag-inventory':
        return flag_inventory(Path(args.spec))
    if args.command == 'help':
        return route_help_command(args.route)
    if args.command == 'timestamp':
        return timestamp_command()
    if args.command == 'banner-timestamp':
        return banner_timestamp_command()
    if args.command == 'role-row':
        return role_row_command(Path(args.roles_dir), args.role, args.index)
    if args.command == 'roles':
        return roles_command(Path(args.roles_dir))
    if args.command == 'summary-role':
        return summary_role_command(args.line)
    if args.command == 'reviewer-state':
        return reviewer_state_command(path, args.target)
    if args.command == 'handoff-state':
        return handoff_state_command(path, args.target, args.role)
    if args.command == 'activate':
        return activate_collab(path, args.target)
    if args.command == 'open':
        return open_collab(path, args.target, args.caller_role)
    if args.command == 'init':
        tokens: list[str] = []
        for agent_id in args.agent_id or []:
            tokens.extend(['--agent-id', agent_id])
        for reviewer in args.reviewer or []:
            tokens.extend(['--reviewer', reviewer])
        for terminal in args.terminal or []:
            tokens.extend(['--terminal', terminal])
        for work_repo in args.work_repo or []:
            tokens.extend(['--work-repo', work_repo])
        if not args.participant_verification:
            tokens.append('--no-participant-verification')
        if args.open:
            tokens.append('--open')
        tokens.extend(args.name)
        return init_collab(path, tokens, DEFAULT_ROLES_DIR)
    if args.command == 'join-participants':
        return join_participants(path, args.target, args.role, args.agent_id, Path(args.roles_dir), args.json)
    if args.command == 'remove-participant':
        return remove_participant(path, args.target, args.role, Path(args.roles_dir), args.caller_role)
    if args.command == 'set':
        value = '--clear' if args.clear else args.value
        return set_field(path, args.target, args.field, value, args.force, Path(args.roles_dir), args.caller_role)
    if args.command == 'unset':
        return unset_field(path, args.target, args.field, Path(args.roles_dir), args.caller_role)
    if args.command == 'effort-state':
        return effort_state(path, args.target, args.role, Path(args.effort_defaults))
    if args.command == 'audit-effort-matrix':
        return audit_effort_matrix(Path(args.effort_defaults), Path(args.agent_model))
    if args.command == 'speak-lifecycle':
        return speak_lifecycle(path, args.target, args.contributors)
    if args.command == 'speak-state':
        return speak_state(path, args.target, args.role, args.resume)
    if args.command == 'speak-lifecycle-live':
        return speak_lifecycle_live(path, args.target)
    if args.command == 'speak-render':
        return render_speak(
            path,
            args.target,
            args.role,
            Path(args.content_file),
            Path(args.full_body_file) if args.full_body_file else None,
            args.observed_revision,
            args.timestamp,
            args.json,
            args.caller_role,
            args.verbatim,
        )
    if args.command == 'rewrite-speak-render':
        return render_re_speak(
            path,
            args.target,
            args.role,
            Path(args.content_file),
            Path(args.full_body_file) if args.full_body_file else None,
            args.timestamp,
            args.caller_role,
            args.verbatim,
        )
    if args.command == 'retract-speak':
        return retract_latest_contribution(path, args.target, args.role, args.reason, args.timestamp, args.caller_role)
    if args.command == 'advance':
        return advance_phase(path, args.target, args.direction, args.json, args.caller_role)
    if args.command == 'execution':
        return record_execution(
            path,
            args.target,
            args.role,
            args.status,
            args.date,
            args.assigned_role,
            args.auto_close,
            args.validation_result,
            args.validation_scope,
            args.touched_path,
            args.agent_id,
            args.json,
            args.caller_role,
        )
    if args.command == 'export-issues':
        return export_issues(
            path,
            args.target,
            args.role,
            Path(args.evidence_file),
            args.timestamp,
            args.json,
            args.caller_role,
        )
    if args.command == 'repair-execution-provenance':
        return repair_execution_provenance(
            path,
            args.target,
            args.role,
            args.work_repo,
            args.commit,
            args.caller_role,
        )
    if args.command == 'execute-spawn':
        return execute_spawn(path, args.target, args.role, args.scope, args.sibling_scope, args.returned_path)
    if args.command == 'transcript-repair':
        return transcript_repair(path, args.target, args.touch_execution_evidence, args.caller_role)
    if args.command == 'out-of-scope-patch':
        return out_of_scope_patch(path, args.target, args.role, args.path, args.caller_role)
    if args.command == 'transcript-view':
        return transcript_view(path, args.target, args.phase, args.raw)
    if args.command == 'summarize':
        return summarize_collab(path, args.target, args.date)
    if args.command == 'participant-verify-state':
        return participant_verify_state(path, args.target, args.role, args.resume)
    if args.command == 'participant-verify-render':
        return participant_verify_render(
            path,
            args.target,
            args.role,
            args.observed_revision,
            args.audit_file,
            args.remediation_file,
            args.final_audit_file,
            args.status,
            args.touched_path,
            args.execution_agent_id,
            args.audit_agent_id,
            args.remediation_agent_id,
            args.timestamp,
            args.caller_role,
        )
    if args.command == 'seal-state':
        return seal_state(path, args.target, args.role, args.resume)
    if args.command == 'seal-render':
        return render_seal(
            path,
            args.target,
            args.role,
            args.observed_revision,
            args.cap_exit,
            args.outcome,
            args.restore_target,
            args.restore_reason,
            args.evidence,
            args.failure_category,
            args.null_result,
            args.json,
            args.caller_role,
        )
    if args.command == 'restart-verification':
        return restart_verification(path, args.target, args.caller_role)
    if args.command == 'reopen':
        return reopen_collab(path, args.target, args.phase, args.caller_role)
    if args.command == 'show-verdict':
        return show_verdict(path, args.target)
    if args.command == 'rewrite-summary':
        return re_summarize_collab(path, args.target, Path(args.summary_file), args.date)
    if args.command == 'close':
        return close_collab(path, args.target, args.json, args.caller_role)
    if args.command == 'audit-closed':
        return audit_closed(path)
    if args.command == 'archive':
        return archive_collab(path, args.target, args.json, args.caller_role)
    if args.command == 'delete':
        return delete_collab(path, args.target, args.yes, args.caller_role)
    if args.command == 'diff':
        return diff_command(path, args.target)
    if args.command == 'render-status':
        return render_status(path, args.target)
    if args.command == 'status-view':
        return status_view(path, args.target)
    if args.command == 'render-participants':
        return render_participants(path, args.target, Path(args.roles_dir))
    if args.command == 'write-guard':
        return write_guard(args.route, args.paths)
    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
