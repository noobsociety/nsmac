#!/usr/bin/env python3
"""Shared collab registry helper.

Import model: bare sibling imports inside ``commands/collab/engine/`` are intentional;
external callers invoke via ``commands.collab.engine.*`` module imports or the argv interface.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
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
    action_plan_checklist_items,
    action_plan_item_tag,
    action_plan_label_summary,
    active_phase_anchors,
    completion_summary_empty,
    contribution_block_bounds,
    contribution_body_lines,
    contribution_is_retracted,
    contribution_roles,
    phase_section,
    read_transcript_for_entry,
    section_bounds,
    summary_role,
    tombstone_count,
    transcript_path_for_entry,
    unchecked_assigned_item_count,
    unchecked_assigned_items_by_role,
)
from commands.collab.engine.planned_routes import validate_issue_bridge_block, validate_planned_route_prerequisites
from commands.collab.engine.registry_validation import validate_registry as validate_registry_data
from commands.collab.engine.effort import (
    audit_effort_matrix,
    effort_line,
    effort_override_audit_items,
    effort_override_from_metadata_comment,
    effort_phase_after_speak,
    effort_state,
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
    append_contribution_store_record,
    contribution_store_path_for_entry,
    empty_contribution_store,
    mark_contribution_store_record_retracted,
    mutable_contribution_store_for_entry,
    path_for_entry_target,
    replace_latest_contribution_store_record,
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
    TERMINAL_CHOICES_MESSAGE,
)
from commands.collab.engine.registry_state import (
    assert_registry_project_binding,
    find_project_identity_path,
    project_metadata_for_display,
    project_metadata_from_identity,
    resolve_default_registry_path,
    sync_registry_project_metadata,
)
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
from commands.collab.engine.command_lines import (
    resume_command,
    resume_command_invocation,
    transcript_view_command,
    transcript_view_command_for_role,
)
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.execution import (
    ExecutionCallbacks,
    all_execution_completed,
    assert_disjoint_scopes,
    assert_execution_touched_paths_in_git_state,
    assert_no_execution_agent_conflation,
    assert_touched_paths_inside_handoff,
    completed_execution_unchecked_items,
    execute_spawn,
    execution_scope_advisory,
    issue_terminal,
    record_execution_state,
    seal_terminal,
    terminal_value,
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
    role_is_joinable,
    validate_participant_role_files,
)
from commands.collab.engine.phase_lifecycle import (
    PhaseLifecycleCallbacks,
    add_completion_summary_notice,
    advance_phase_state,
    discussion_turn_notice,
    efficiency_line_from_notice,
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
    next_sequence,
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
    stale_registry_lock_message,
    write_json_if_absent,
    write_revision_event,
)
from commands.collab.engine.transcript_render import (
    TIMESTAMP_RE,
    append_phase_block,
    contribution_store_record,
    insert_toc_entry,
    latest_contribution_anchor,
    latest_contribution_timestamp,
    next_anchor_counter,
    print_header_overwrite,
    excerpt_source,
    replace_latest_contribution,
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
    replace_phase_summary,
    reviewer_notice_for_rewrite,
    revision_history_start,
)
from commands.collab.engine import seal_verification_logic as _seal_verification_logic
from commands.collab.engine import seal_verification_render as _seal_verification_render
from commands.collab.engine.seal_verification_logic import (
    apply_cap_exit,
    build_verdict,
    chartered_deliverable_path,
    chartered_deliverables,
    clear_verdict,
    completion_state,
    content_digest_for_execution,
    die_content_drift_persisted,
    ensure_legacy_content_digest,
    first_pending_participant_verification_role,
    initialize_completion_state,
    invalidate_seal_on_content_drift,
    invalidate_seal_on_full_body_drift,
    is_chartered_deliverables_label,
    parse_verdict_evidence,
    participant_verification_enabled,
    participant_verification_inactive_message,
    participant_verification_incomplete,
    participant_verification_role_state,
    participant_verification_roles,
    participant_verify_state,
    record_verification_round_for_execution,
    reset_participant_verification_stages,
    restart_verification,
    seal_snapshot,
    seal_state,
    set_verification_review_substate,
    show_verdict,
    successful_verdict,
    validate_verdict,
    validate_verdict_evidence,
    verification_review_substate,
    verification_state,
    verification_substate,
    write_seal_verdict_companion,
)
from commands.collab.engine.seal_verification_render import (
    append_completion_history_line,
    append_completion_summary,
    append_participant_verify_block,
    append_reviewer_findings_block,
    assessment_next_line,
    assessment_notice,
    completion_summary_bounds,
    configure_registry_facade as configure_seal_verification_facade,
    default_close_summary,
    insert_reopen_pointer,
    latest_reviewer_findings_anchor,
    next_completion_history_number,
    next_reviewer_findings_counter,
    participant_verify_render,
    replace_latest_summary,
    summary_date_from_iso,
    summary_date_from_timestamp,
    verdict_args_present,
    verdict_reopen_command,
)
from commands.collab.engine.speak_state import (
    add_participation_resume_fields,
    blocked_resume_state_for_entry,
    current_completion_command,
    next_command_for_state,
    next_line_after_speak,
    next_line_for_state,
    phase_summary_for_state,
    policy_blockers_for_role,
    speak_state_for_entry,
)
from commands.collab.engine.advisories import (
    forced_active_phase_advisory,
    post_action_advisory_lines,
    print_post_action_advisories,
)
from commands.collab.engine.issue_export import (
    configure_issue_export,
    export_issues,
    exported_issue_handoff_present,
    normalize_issue_export_evidence,
)
from commands.collab.engine.content_files import (
    read_content_file,
    read_optional_content_file,
)
from commands.collab.engine.parser_introspection import (
    action_display_name,
    action_value_shape,
    parser_subcommands,
)
from commands.collab.engine.restore_inputs import (
    collab_entry_from_registry_snapshot,
    parse_restore_event_index,
)
from commands.collab.engine.query_commands import (
    banner_timestamp_command,
    handoff_state_command,
    registry_path_command,
    reviewer_state_command,
    role_row_command,
    roles_command,
    summary_role_command,
    timestamp_command,
)
from commands.collab.engine.inspection_commands import (
    audit_closed,
    diff_command,
    list_collabs,
    log_command,
    print_status_view,
    status_view,
)
from commands.collab.engine.init_inputs import (
    ROLE_KEY_RE,
    parse_init_tokens,
)
from commands.collab.engine.post_execution import (
    close_eligible_after_execution,
    next_line_after_execution,
)

# Architecture: see commands/collab/reference/engine-architecture.md

from commands.collab.engine.config_paths import (
    DEFAULT_AGENT_MODEL_PATH,
    DEFAULT_CONFIG_ROOT,
    DEFAULT_EFFORT_PATH,
    DEFAULT_FLAG_TAXONOMY_PATH,
    DEFAULT_ROLES_DIR,
    resolve_config_root,
)
from commands.collab.engine.flag_taxonomy import FLAG_ROW_RE, flag_inventory
from commands.collab.engine.source_contracts import (
    require_source_text,
    validate_command,
    validate_source_contracts,
)
from commands.collab.engine.help_command import route_help_command
from commands.collab.engine.browser import open_browser_uri
from commands.collab.engine.render_commands import (
    configure_render_commands,
    render_participants,
    render_status,
    re_summarize_collab,
    summarize_collab,
    transcript_view,
)
from commands.collab.engine.field_commands import (
    clear_reviewer,
    configure_field_commands,
    remove_participant,
    set_field,
    unset_field,
)
from commands.collab.engine.lifecycle_commands import (
    archive_collab,
    close_collab,
    configure_lifecycle_commands,
    delete_collab,
    open_collab,
)
from commands.collab.engine.repair_commands import (
    configure_repair_commands,
    out_of_scope_patch,
    repair_execution_provenance,
    transcript_repair,
)
from commands.collab.engine.reactivation_commands import (
    configure_reactivation_commands,
    reopen_collab,
    restore_collab_content,
    save_registry_with_event_type,
)
from commands.collab.engine.onboarding_commands import (
    configure_onboarding_commands,
    ensure_init_project_metadata,
    init_collab,
    join_participants,
)
from commands.collab.engine.speak_commands import (
    activate_collab,
    apply_speak_lifecycle_to_entry,
    apply_speak_lifecycle_with_notice,
    configure_speak_commands,
    die_with_resume,
    render_re_speak,
    render_speak,
    retract_latest_contribution,
    speak_lifecycle,
    speak_lifecycle_live,
    speak_state,
)
from commands.collab.engine.route_write_guard import write_guard


def invalidate_verification_seal(entry: dict, reason: str) -> None:
    original_reviewer_backed = _seal_verification_logic.reviewer_backed
    original_incomplete = _seal_verification_logic.participant_verification_incomplete
    original_enabled = _seal_verification_logic.participant_verification_enabled
    try:
        _seal_verification_logic.reviewer_backed = reviewer_backed
        _seal_verification_logic.participant_verification_incomplete = participant_verification_incomplete
        _seal_verification_logic.participant_verification_enabled = participant_verification_enabled
        _seal_verification_logic.invalidate_verification_seal(entry, reason)
    finally:
        _seal_verification_logic.reviewer_backed = original_reviewer_backed
        _seal_verification_logic.participant_verification_incomplete = original_incomplete
        _seal_verification_logic.participant_verification_enabled = original_enabled


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
    return _seal_verification_render.participant_verify_render(
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
    return _seal_verification_render.render_seal(
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


def validate_registry(data: dict, path: Path | None = None) -> None:
    validate_registry_data(data, path, DEFAULT_ROLES_DIR)


configure_registry_io(validate_registry)


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
configure_issue_export(
    commit_registry_and_transcript=commit_registry_and_transcript,
    close_eligible_after_execution=close_eligible_after_execution,
)
configure_render_commands(
    commit_registry_and_transcript=commit_registry_and_transcript,
)
configure_field_commands(
    commit_registry_and_transcript=commit_registry_and_transcript,
)
configure_lifecycle_commands(
    commit_registry_and_transcript=commit_registry_and_transcript,
)
configure_repair_commands(
    invalidate_verification_seal=invalidate_verification_seal,
)
configure_reactivation_commands(
    invalidate_verification_seal=invalidate_verification_seal,
    commit_registry_and_transcript=commit_registry_and_transcript,
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


configure_onboarding_commands(
    commit_new_collab_artifacts=commit_new_collab_artifacts,
    commit_registry_and_transcript=commit_registry_and_transcript,
)
configure_speak_commands(
    commit_registry_and_transcript=commit_registry_and_transcript,
)


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

    restore_parser = subparsers.add_parser('restore')
    restore_parser.add_argument('target')
    restore_parser.add_argument('--to', required=True)
    restore_parser.add_argument('--caller-role')

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

    seal_write_parser = subparsers.add_parser('seal-write')
    seal_write_parser.add_argument('target')
    seal_write_parser.add_argument('role')
    seal_write_parser.add_argument('--observed-revision', type=int, required=True)
    seal_write_parser.add_argument('--cap-exit')
    seal_write_parser.add_argument('--restore-reason')
    seal_write_parser.add_argument('--evidence')
    seal_write_parser.add_argument('--failure-category')
    seal_write_parser.add_argument('--json', action='store_true')
    seal_write_parser.add_argument('--caller-role')

    record_verdict_parser = subparsers.add_parser('record-verdict')
    record_verdict_parser.add_argument('target')
    record_verdict_parser.add_argument('role')
    record_verdict_parser.add_argument('--observed-revision', type=int, required=True)
    record_verdict_parser.add_argument('--outcome', required=True)
    record_verdict_parser.add_argument('--restore-target')
    record_verdict_parser.add_argument('--restore-reason')
    record_verdict_parser.add_argument('--evidence')
    record_verdict_parser.add_argument('--failure-category')
    record_verdict_parser.add_argument('--null-result', action='store_true')
    record_verdict_parser.add_argument('--json', action='store_true')
    record_verdict_parser.add_argument('--caller-role')

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
    if args.command == 'restore':
        return restore_collab_content(path, args.target, args.to, args.caller_role)
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
    if args.command == 'seal-write':
        return _seal_verification_render.seal_write(
            path,
            args.target,
            args.role,
            args.observed_revision,
            args.cap_exit,
            args.restore_reason,
            args.evidence,
            args.failure_category,
            args.json,
            args.caller_role,
        )
    if args.command == 'record-verdict':
        return _seal_verification_render.record_verdict(
            path,
            args.target,
            args.role,
            args.observed_revision,
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
