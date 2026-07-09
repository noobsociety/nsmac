#!/usr/bin/env python3
"""Shared collab registry helper.

Import model: intra-engine imports are fully qualified (``commands.collab.engine.X``); the
sole bare import is ``roles``, resolved from ``platform/tooling/`` via the ``COMMAND_SYSTEM_DIR``
sys.path insert below. External callers invoke via ``commands.collab.engine.*`` module imports
or the argv interface.
"""
from __future__ import annotations

import sys
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
    ALLOWED_COMPLETION_SUBSTATES,
    ALLOWED_EXECUTION_STATUSES,
    ALLOWED_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_REVIEWER_MODES,
    ALLOWED_SET_FIELDS,
    ALLOWED_STATUSES,
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
    record_execution_state,
    seal_terminal,
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
    commit_new_collab_artifacts,
    commit_registry_and_transcript,
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
from commands.collab.engine.registry_parser import build_parser, render_registry_cli_doc
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
from commands.collab.engine import seal_verification_render as _seal_verification_render
from commands.collab.engine.seal_verification_logic import (
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
    invalidate_verification_seal,
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
    default_close_summary,
    insert_reopen_pointer,
    latest_reviewer_findings_anchor,
    next_completion_history_number,
    next_reviewer_findings_counter,
    participant_verify_render,
    replace_latest_summary,
    summary_date_from_iso,
    summary_date_from_timestamp,
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
from commands.collab.engine.content_files import (
    read_content_file,
    read_optional_content_file,
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
    render_participants,
    render_status,
    summarize_collab,
    transcript_view,
)
from commands.collab.engine.field_commands import (
    clear_reviewer,
    remove_participant,
    set_field,
    unset_field,
)
from commands.collab.engine.lifecycle_commands import (
    archive_collab,
    close_collab,
    delete_collab,
    open_collab,
)
from commands.collab.engine.repair_commands import (
    out_of_scope_patch,
    repair_execution_provenance,
    transcript_repair,
)
from commands.collab.engine.reactivation_commands import (
    reopen_collab,
    restore_collab_content,
    save_registry_with_event_type,
)
from commands.collab.engine.onboarding_commands import (
    ensure_init_project_metadata,
    init_collab,
    join_participants,
)
from commands.collab.engine.speak_commands import (
    activate_collab,
    apply_speak_lifecycle_to_entry,
    apply_speak_lifecycle_with_notice,
    die_with_resume,
    render_re_speak,
    render_speak,
    retract_latest_contribution,
    speak_lifecycle,
    speak_lifecycle_live,
    speak_state,
)
from commands.collab.engine.route_write_guard import write_guard


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
    # Permanent facade-pair: registry.py owns CLI dispatch by design.
    # This wrapper delegates; the render implementation owns round recording.
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


_seal_verification_render.configure_registry_facade(
    next_line_for_state=next_line_for_state,
    print_post_action_advisories=print_post_action_advisories,
)


from commands.collab.engine.registry_dispatch import main


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
