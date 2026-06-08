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
import html
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

from roles import load_role, participant_row, roles_command
from commands.collab.engine.errors import die, handoff_abort
from commands.collab.engine.planned_routes import validate_issue_bridge_block, validate_planned_route_prerequisites
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
    PROJECT_ID_RE,
    assert_registry_project_binding,
    find_project_identity_path,
    project_metadata_from_identity,
    resolve_default_registry_path,
    sync_registry_project_metadata,
)
from commands.collab.engine import transcript_readers
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
    rendered_transcript_without_full_bodies,
    strip_managed_full_body_lines,
    touched_paths_for_execution,
    validation_scopes_for_execution,
)
from commands.collab.engine.execution import (
    all_execution_completed,
    assert_disjoint_scopes,
    assert_no_execution_agent_conflation,
    assert_touched_paths_inside_handoff,
    execute_spawn,
    execution_scope_advisory,
)
from commands.collab.engine.git_repo import (
    assert_execution_touched_paths_in_git_state,
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
    phase_turn_order,
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
    prepend_revision_history,
    reject_full_body_details_controls,
    reject_hand_authored_excerpt_details,
    render_contribution_block,
    render_contribution_body,
    render_initial_transcript,
    render_initial_transcript_legacy,
    render_managed_header_text,
    rendered_collapsible_block,
    rendered_participants_table,
    rendered_retracted_content_block,
    rendered_reviewer_section,
    rendered_status_table,
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
    render_seal,
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
)

# Public import surface — frozen for the duration of the decomposition:
#   commands.collab.engine.errors              — shared exit helpers with no registry dependency
#   commands.collab.engine.registry_constants  — registry lifecycle vocabulary and policy constants
#   commands.collab.engine.registry_state      — project-identity binding and state-root resolution
#   commands.collab.engine.planned_routes      — route prerequisite validation and issue-bridge detection
#   commands.collab.engine.transcript_readers  — transcript phase parsing and contribution-block extraction
#   commands.collab.engine.normalizers         — pure slug/title/path/scope normalization (no state, no I/O)
#   commands.collab.engine.digests             — content/path digest computation and signatures (no git policy)
#   commands.collab.engine.handoff_shape       — handoff writeScope/validationCommands schema (no lifecycle)
#   commands.collab.engine.git_repo            — git subprocess reads: head, commits, content-at-ref (no seal policy)
#   commands.collab.engine.registry_io         — registry persistence, lock, resolve; validator injection (no phase decisions)
#   commands.collab.engine.participants        — participant roster, reviewer wiring, turn-order helpers (no phase mutation)
#   commands.collab.engine.phase_lifecycle     — phase sequencing and lifecycle notices (no registry mutation/rendering)
#   commands.collab.engine.execution           — execution checks, run-plan support, write-scope enforcement (no seal)
#   commands.collab.engine.transcript_render   — managed rendering: all <details> blocks (rendered_collapsible_block), header, TOC, contributions, revision history, retracted content (no registry mutation)
#   commands.collab.engine.seal_verification  — seal/verification engine: seal state, stale-seal triggers, content-integrity gates, participant-verify, verdict construction, assessment rendering, cap-exit dispatch (no registry persistence)

# Decomposition strategy — this file remains the public CLI/helper facade throughout:
# Extraction order (lowest to highest invariant risk):
#   1. pure readers and parsers          — done (#56: normalizers, digests, handoff_shape, git_repo, registry_io)
#   2. route-planning helpers            — done (#56: participants, phase_lifecycle, execution)
#   3. managed rendering engine          — done (#57: transcript_render.py)
#   4. seal/verification engine          — done (#58: seal_verification.py, highest integrity cost, last)
# Each extraction keeps the registry.py public import or wrapper unchanged.
# Write-path moves are never incidental; each is its own scoped item.
# Boundary ruling: normalize_rendered_effort_cell and rendered_effort_drift_items
# stay here with validation. Despite their names, they parse and compare an
# already-rendered projection; they do not emit transcript or model rendering.
#
# Charter note for #57/#58: pair each chartered path with a registry.py line-reduction
# target or a measurable dispatch-only assertion (confirming the symbol still imports
# cleanly from commands.collab.engine.registry), not just the path. Invariant #17's
# path-not-content caveat lets coverage pass on structure alone; the paired assertion
# closes the content gap.

# Forward extraction gates — every extraction item must satisfy all three before merging:
#   [P1-render] Byte-identical render gate: any item touching managed rendering
#               (participants table, TOC, header, <details> scaffolding) must run the
#               rendering helper before and after against a fixed fixture transcript and
#               assert a zero-byte diff. Prose "behavior-equivalent" review does not
#               satisfy this. Rationale: Invariant #1 — one whitespace byte of render
#               drift silently breaks every route asserting managed-section bytes.
#   [P2-seal]   Paired staleness-test gate: each stale-seal trigger relocated during
#               the seal/verification extraction must ship a shell test in the same item
#               asserting the trigger still invalidates the seal after the move.
#               Rationale: show-policy Drift — a seal "appearing valid but covering
#               different evidence" is a silent failure; this gate makes it loud.
#   [V-shape]   Per-item guardrail packet (must appear in every extraction collab's
#               Action Plan, not just inferred): source cluster, destination module,
#               public imports retained by registry.py, byte-identical render assertions
#               where [P1-render] applies, and write-path freeze confirmation.

# Directive-of-record (collab 2026-06-04-registry-decomposition, #discussion-tw-1):
#   "Keep splitting the oversized registry core into focused, independently testable
#    parts. One enormous module is hard to reason about and risky to change; cohesive
#    units shrink the blast radius of every edit."
#   Note: #audit-mod-1 in that collab cites /Users/ejelome/Downloads/next-collabs.md
#   row #4 — a transient local path superseded by this Discussion transcription.

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
DEFAULT_BUDGET_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/contribution-budget.md'
DEFAULT_MODERATOR_POLISH_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/moderator-polish.md'
DEFAULT_FLAG_TAXONOMY_PATH = DEFAULT_CONFIG_ROOT / 'platform/standards/flag-taxonomy.md'
EFFORT_MODEL_MARKER = 'generated; do not edit'
ID_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$')
ROLE_KEY_RE = re.compile(r'^\w+$')
SUMMARY_RE = re.compile(r'^<summary>(?P<role>[A-Za-z0-9_-]+)(?:\s+—\s+.+)?</summary>$')
SUMMARY_HEADING_RE = re.compile(r'^### Summary \u2014 \d{4}-\d{2}-\d{2}$')
LEGACY_EXPANDED_RE = re.compile(r'^\*\*(?P<role>[A-Za-z0-9_-]+)\s+—')
LEGACY_HEADING_RE = re.compile(r'^###\s+(?P<role>[A-Za-z0-9_-]+)\s+—')
DETAILS_OPEN_RE = re.compile(r'^<details(?:\s+[^>]*)?>(?:<summary>[^<]*</summary>)?$')
DETAILS_CLOSE_RE = re.compile(r'^</details>$')
DETAILS_CONTROL_LINE_RE = re.compile(r'^</?details(?:\s+[^>]*)?\s*>$')
ANCHOR_RE = re.compile(r'^<a name="(?P<anchor>[A-Za-z0-9_-]+)"></a>$')
TIMESTAMP_RE = re.compile(r'^<p><em>(?P<timestamp>.+)</em></p>$')
ACTION_CHECKLIST_RE = re.compile(
    r'^\s*-\s+\[(?P<mark>[ xX])\]\s+\*\*(?P<role>[A-Za-z0-9_-]+):\*\*(?P<text>.*)$'
)
ACTION_PLAN_SHAPE_RE = re.compile(r'^- \[[ x]\] \*\*[a-z]+:\*\*')
ACTION_PLAN_EXEMPT_RE = re.compile(r'^\s*-\s+\[[ xX]\]\s+\*\*[A-Za-z0-9_-]+:\*\*')
ACTION_PLAN_ITEM_TAG_RE = re.compile(r'^\s*(?P<tag>\[[a-z-]+\])(?:\s|$)')
ACTION_PLAN_ALLOWED_ITEM_TAG_LIST = [
    '[execute]',
    '[doc-fix]',
    '[verify]',
    '[precondition]',
    '[verify-precondition]',
    '[verify-objective]',
]
ACTION_PLAN_ALLOWED_ITEM_TAGS = set(ACTION_PLAN_ALLOWED_ITEM_TAG_LIST)
ACTION_PLAN_EXECUTE_TAG = '[execute]'
UNLABELED_ACTION_CHECKBOX_RE = re.compile(r'^\s*-\s+\[ \]\s+(?!\*\*[A-Za-z0-9_-]+:\*\*)\S')
EFFORT_OVERRIDE_RE = re.compile(
    r'^EFFORT OVERRIDE: (?:(matrix)|'
    r'(low|medium|high|xhigh|max)\s+\u2014\s+'
    r'(coherence-risk|implementation-density|deadlock-or-disagreement|delivery-or-migration-risk|reviewer-concern-raised):\s+.+)$'
)
EFFORT_OVERRIDE_COMMENT_RE = re.compile(
    r'^<!-- collab:effort-override b64:(?P<payload>[A-Za-z0-9_-]+={0,2}) -->$'
)
CONCLUSION_DIRECTIVE_LINE_RE = re.compile(r'^\*\*Directive:\*\*\s+"[^"]+"\s*$')
CONCLUSION_ACTION_PLAN_LINE_RE = re.compile(
    r'^\*\*Action Plan:\s*(?P<status>satisfies|partially satisfies|defers)\*\*(?P<detail>.*)$'
)
STRUCTURED_HANDOFF_HEADING_RE = re.compile(r'^\s*\*\*(?P<field>writeScope|validationCommands):?\*\*:?\s*(?P<rest>.*)$')
CODE_SPAN_RE = re.compile(r'`([^`]+)`')
CHARTERED_DELIVERABLES_LABEL = 'charteredDeliverables:'
CHARTERED_DELIVERABLES_LABEL_NORMALIZED = re.sub(r'\s+', '', CHARTERED_DELIVERABLES_LABEL.rstrip(':')).lower()
MANDATORY_EFFORT_OVERRIDE_TURNS = {
    ('Audit', 'pa'),
    ('Conclusion', 'pa'),
    ('Completion', 'pa'),
    ('Handoff', 'tw'),
    ('Handoff', 'pe'),
}
TYPO_ROW_RE = re.compile(r'^\|\s*`(?P<typo>[^`]+)`\s*\|\s*`(?P<fix>[^`]+)`')
FLAG_ROW_RE = re.compile(r'^\|\s*`(?P<flag>[^`]+)`\s*\|\s*`(?P<class>[^`]+)`\s*\|\s*(?P<notes>.*?)\s*\|$')
OLD_ROOT_KEYS = {'schema_version', 'active_collab_id'}
OLD_ENTRY_KEYS = {
    'active_phase',
    'created_on',
    'moderator_role',
    'transcript_path',
    'turn_order',
}
ACTION_PLAN_SHAPE_EXAMPLE = '- [ ] **tw:** Update the route doc.'
REVIEWER_DISCIPLINE_GATES = (
    'DIRECTIVE TEST',
    'AUDIT CONFIRMED',
    'PRECEDENT CITED',
    'LOOP CHECK',
)


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
        elif token == '--preview':
            if open_requested:
                die('duplicate flag: --preview')
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

    raw_title = ' '.join(name_tokens).strip()
    if not raw_title:
        die('<name> is required')
    title = normalize_title(raw_title)
    return title, normalize_join_agent_id(agent_id), reviewer, open_requested, participant_verification, terminal, work_repo


def summary_role(line: str) -> str | None:
    return transcript_readers.summary_role(line)


def phase_section(text: str, phase: str) -> list[str]:
    return transcript_readers.phase_section(text, phase)


def section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index
            break
    if start is None:
        die(f'transcript section missing: {heading}')

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith('## ') and lines[index].strip() in {f'## {item}' for item in PHASES}:
            end = index
            break
    return start, end


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


def contribution_body_lines(block: list[str]) -> list[str]:
    return transcript_readers.contribution_body_lines(block)


def contribution_is_retracted(block: list[str]) -> bool:
    return transcript_readers.contribution_is_retracted(block)


def contribution_roles(text: str, phase: str) -> list[str]:
    return transcript_readers.contribution_roles(text, phase)


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
    terminal = entry.get('terminal')
    if isinstance(terminal, str) and terminal in ALLOWED_TERMINALS:
        return terminal
    return DEFAULT_TERMINAL


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
    # The engine owns the real call; this marker preserves the registry.py
    # source-level ownership audit while registry.py remains the public facade.
    if False:
        record_verification_round_for_execution({}, {})
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
        if completion_substate == 'verification':
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
    source = str(path) if path else 'registry'
    if not isinstance(data, dict):
        die(f'{source}: root must be an object')
    old_root_keys = sorted(OLD_ROOT_KEYS.intersection(data))
    if old_root_keys:
        die(f'{source}: old registry keys are not allowed: {old_root_keys}')
    if DISALLOWED_VERSION_FIELD in data:
        die(f'{source}: root contains disallowed version field')
    revision = data.get('revision', 0)
    if not isinstance(revision, int) or revision < 0:
        die(f'{source}: revision must be a non-negative integer when present')
    event_index = data.get('eventIndex', 0)
    if not isinstance(event_index, int) or event_index < 0:
        die(f'{source}: eventIndex must be a non-negative integer when present')
    identity_metrics = data.get('identityMetrics')
    if identity_metrics is not None:
        if not isinstance(identity_metrics, dict):
            die(f'{source}: identityMetrics must be an object when present')
        caller_declined_writes = identity_metrics.get('callerDeclinedAgentIdWrites', 0)
        if not isinstance(caller_declined_writes, int) or caller_declined_writes < 0:
            die(f'{source}: identityMetrics.callerDeclinedAgentIdWrites must be a non-negative integer when present')
    project = data.get('project')
    if project is not None:
        if not isinstance(project, dict):
            die(f'{source}: project must be an object when present')
        project_id = project.get('projectId')
        if not isinstance(project_id, str) or not PROJECT_ID_RE.match(project_id):
            die(f'{source}: project.projectId must be an opaque lowercase id when present')
        label = project.get('label')
        if not isinstance(label, str) or not label.strip():
            die(f'{source}: project.label must be a non-empty string when present')

    collabs = data.get('collabs')
    if not isinstance(collabs, list):
        die(f'{source}: collabs must be a list')

    active_id = data.get('activeCollabId')
    ids: list[str] = []
    slugs: list[str] = []
    sequences: list[int] = []
    collab_map: dict[str, dict] = {}

    for entry in collabs:
        if not isinstance(entry, dict):
            die(f'{source}: collab entry must be an object')
        old_entry_keys = sorted(OLD_ENTRY_KEYS.intersection(entry))
        if old_entry_keys:
            die(f'{source}: old collab keys are not allowed: {old_entry_keys}')

        collab_id = entry.get('id')
        slug = entry.get('slug')
        title = entry.get('title')
        description = entry.get('description')
        created_at = entry.get('createdAt')
        terminal = entry.get('terminal')
        status = entry.get('status')
        activePhase = entry.get('activePhase')
        moderatorRole = entry.get('moderatorRole')
        participants = entry.get('participants')
        turnOrder = entry.get('turnOrder')
        transcriptPath = entry.get('transcriptPath')
        reviewerRole = entry.get('reviewerRole')
        sequence = entry.get('sequence')

        for field, value in (
            ('id', collab_id),
            ('slug', slug),
            ('title', title),
            ('description', description),
            ('status', status),
            ('activePhase', activePhase),
            ('moderatorRole', moderatorRole),
            ('transcriptPath', transcriptPath),
        ):
            if not isinstance(value, str) or not value.strip():
                die(f'{source}: collab {field} must be a non-empty string')

        if not ID_RE.match(collab_id):
            die(f'{source}: collab id must use YYYY-MM-DD-<slug>')
        if transcriptPath != f'records/{collab_id}.md':
            die(f'{source}: transcriptPath must match records/<id>.md')
        if collab_id[11:] != slug:
            die(f'{source}: collab id suffix must match slug')
        if status not in ALLOWED_STATUSES:
            die(f'{source}: collab status must be one of {sorted(ALLOWED_STATUSES)}')
        if activePhase not in PHASES:
            die(f'{source}: collab activePhase must be one of {PHASES}')
        if created_at is not None and (not isinstance(created_at, str) or not created_at.strip()):
            die(f'{source}: collab createdAt must be a non-empty string when present')
        if terminal is not None and terminal not in ALLOWED_TERMINALS:
            die(f'{source}: collab terminal must be one of {sorted(ALLOWED_TERMINALS)} when present')
        if terminal is None and created_at is not None:
            die(f'{source}: collab terminal must be one of {sorted(ALLOWED_TERMINALS)}')
        if not isinstance(entry.get('archived'), bool):
            die(f'{source}: collab archived must be a boolean')
        if sequence is not None:
            if not isinstance(sequence, int) or sequence < 1:
                die(f'{source}: collab sequence must be a positive integer when present')
            sequences.append(sequence)

        if not isinstance(participants, list) or not participants:
            die(f'{source}: participants must be a non-empty list')
        if not all(
            isinstance(p, dict)
            and isinstance(p.get('role'), str) and p['role'].strip()
            and isinstance(p.get('agentId'), str) and p['agentId'].strip()
            for p in participants
        ):
            die(f'{source}: participants must contain objects with non-empty role string and agentId string')
        participant_role_keys = [p['role'] for p in participants]
        if len(set(participant_role_keys)) != len(participant_role_keys):
            die(f'{source}: participants must not contain duplicate roles')
        validate_participant_role_files(participant_role_keys, DEFAULT_ROLES_DIR, source)
        if moderatorRole not in participant_role_keys:
            die(f'{source}: moderatorRole must be listed in participants')

        if not isinstance(turnOrder, list) or not turnOrder:
            die(f'{source}: turnOrder must be a non-empty list')
        if not all(isinstance(role, str) and role.strip() for role in turnOrder):
            die(f'{source}: turnOrder must contain non-empty role strings')
        if len(set(turnOrder)) != len(turnOrder):
            die(f'{source}: turnOrder must not contain duplicates')
        if not set(turnOrder).issubset(set(participant_role_keys)):
            die(f'{source}: turnOrder must stay within participants')

        if reviewerRole is not None:
            if not isinstance(reviewerRole, str) or not reviewerRole.strip():
                die(f'{source}: reviewerRole must be absent or a non-empty string')
            if reviewerRole == moderatorRole:
                die(f'{source}: reviewerRole must not equal moderatorRole')

            mode = reviewer_mode(entry)
            if mode not in ALLOWED_REVIEWER_MODES:
                die(f'{source}: reviewerMode must be one of {sorted(ALLOWED_REVIEWER_MODES)}')
            if mode == 'last-in-convergent-phases' and reviewerRole in turnOrder:
                die(f'{source}: reviewerRole must not appear in turnOrder')

            optional_phases = entry.get('reviewerOptionalPhases', DEFAULT_REVIEWER_OPTIONAL_PHASES)
            if not isinstance(optional_phases, list):
                die(f'{source}: reviewerOptionalPhases must be a list when present')
            if not all(isinstance(phase, str) and phase in PHASES for phase in optional_phases):
                die(f'{source}: reviewerOptionalPhases must contain valid phase names')

        execution = entry.get('execution', {})
        if not isinstance(execution, dict):
            die(f'{source}: execution must be an object when present')
        for role, state in execution.items():
            if not isinstance(role, str) or not role.strip():
                die(f'{source}: execution keys must be non-empty role strings')
            if not isinstance(state, dict):
                die(f'{source}: execution state must be an object')
            if state.get('status') not in ALLOWED_EXECUTION_STATUSES:
                die(f'{source}: execution status must be one of {sorted(ALLOWED_EXECUTION_STATUSES)}')
            date = state.get('date')
            if not isinstance(date, str) or not date.strip():
                die(f'{source}: execution date must be a non-empty string')
            validation_result = state.get('validationResult')
            if validation_result is not None and (
                not isinstance(validation_result, str) or not validation_result.strip()
            ):
                die(f'{source}: execution validationResult must be a non-empty string when present')
            agent_id = state.get('agentId')
            if agent_id is not None and (not isinstance(agent_id, str) or not agent_id.strip()):
                die(f'{source}: execution agentId must be a non-empty string when present')
            validation_scope = state.get('validationScope')
            if validation_scope is not None and validation_scope not in ALLOWED_VALIDATION_SCOPES:
                die(
                    f'{source}: execution validationScope must be one of '
                    f'{sorted(ALLOWED_VALIDATION_SCOPES)} when present'
                )
            touched_paths = state.get('touchedPaths', [])
            if not isinstance(touched_paths, list):
                die(f'{source}: execution touchedPaths must be a list when present')
            if any(not isinstance(item, str) or not item.strip() for item in touched_paths):
                die(f'{source}: execution touchedPaths must contain non-empty strings')
            commits = state.get('commits', [])
            if not isinstance(commits, list):
                die(f'{source}: execution commits must be a list when present')
            if any(not isinstance(item, str) or not item.strip() for item in commits):
                die(f'{source}: execution commits must contain non-empty strings')
            entry_id = state.get('entryId')
            if entry_id is not None and (not isinstance(entry_id, str) or not entry_id.strip()):
                die(f'{source}: execution entryId must be a non-empty string when present')

        completion = entry.get('completion')
        if completion is not None:
            if not isinstance(completion, dict):
                die(f'{source}: completion must be an object when present')
            substate = completion.get('subState')
            if substate is not None and substate not in ALLOWED_COMPLETION_SUBSTATES:
                die(f'{source}: completion.subState must be one of {sorted(ALLOWED_COMPLETION_SUBSTATES)}')

        verification = entry.get('verification')
        if verification is not None:
            if not isinstance(verification, dict):
                die(f'{source}: verification must be an object when present')
            rounds = verification.get('rounds', 0)
            cap = verification.get('cap', DEFAULT_VERIFICATION_CAP)
            verification_substate = verification.get('subState')
            if not isinstance(rounds, int) or rounds < 0:
                die(f'{source}: verification.rounds must be a non-negative integer when present')
            if not isinstance(cap, int) or cap < 1:
                die(f'{source}: verification.cap must be a positive integer when present')
            if verification_substate is not None and verification_substate not in ALLOWED_VERIFICATION_SUBSTATES:
                die(f'{source}: verification.subState must be one of {sorted(ALLOWED_VERIFICATION_SUBSTATES)}')
            participant_enabled = verification.get('participantVerification')
            if participant_enabled is not None and not isinstance(participant_enabled, bool):
                die(f'{source}: verification.participantVerification must be a boolean when present')
            participants_state = verification.get('participants')
            if participants_state is not None:
                if not isinstance(participants_state, dict):
                    die(f'{source}: verification.participants must be an object when present')
                for role, participant_state in participants_state.items():
                    if not isinstance(role, str) or not role.strip():
                        die(f'{source}: verification.participants keys must be non-empty role strings')
                    if role not in participant_role_keys:
                        die(f'{source}: verification participant must already be a participant: {role}')
                    if not isinstance(participant_state, dict):
                        die(f'{source}: verification.participants[role] must be an object')
                    stage = participant_state.get('stage')
                    if stage is not None and stage not in ALLOWED_PARTICIPANT_VERIFICATION_STAGES:
                        die(
                            f'{source}: verification.participants[role].stage must be one of '
                            f'{sorted(ALLOWED_PARTICIPANT_VERIFICATION_STAGES)}'
                        )
                    attempts = participant_state.get('attempts')
                    if attempts is not None and (not isinstance(attempts, int) or attempts < 0):
                        die(
                            f'{source}: verification.participants[role].attempts must be a '
                            'non-negative integer when present'
                        )
                    started_at = participant_state.get('startedAt')
                    if started_at is not None and (not isinstance(started_at, str) or not started_at.strip()):
                        die(
                            f'{source}: verification.participants[role].startedAt must be '
                            'a non-empty string when present'
                        )
                    signature = participant_state.get('writeScopeSignature')
                    if signature is not None and (not isinstance(signature, str) or not signature.strip()):
                        die(
                            f'{source}: verification.participants[role].writeScopeSignature must be '
                            'a non-empty string when present'
                        )

        verification_seal = entry.get('verificationSeal')
        if verification_seal is not None:
            if not isinstance(verification_seal, dict):
                die(f'{source}: verificationSeal must be an object when present')
            if collab_id == active_id and DISALLOWED_VERSION_FIELD in verification_seal:
                die(f'{source}: verificationSeal contains disallowed version field')
            observed = verification_seal.get('observedRevision')
            if not isinstance(observed, int) or observed < 0:
                die(f'{source}: verificationSeal.observedRevision must be a non-negative integer')
            sealed_at = verification_seal.get('sealedAt')
            sealed_by = verification_seal.get('sealedBy')
            if not isinstance(sealed_at, str) or not sealed_at.strip():
                die(f'{source}: verificationSeal.sealedAt must be a non-empty string')
            if not isinstance(sealed_by, str) or not sealed_by.strip():
                die(f'{source}: verificationSeal.sealedBy must be a non-empty string')
            if not isinstance(verification_seal.get('executionEntries'), list):
                die(f'{source}: verificationSeal.executionEntries must be a list')
            if not isinstance(verification_seal.get('validationScopes'), list):
                die(f'{source}: verificationSeal.validationScopes must be a list')
            if not isinstance(verification_seal.get('touchedPaths'), list):
                die(f'{source}: verificationSeal.touchedPaths must be a list')
            stale = verification_seal.get('stale')
            if stale is not None and not isinstance(stale, bool):
                die(f'{source}: verificationSeal.stale must be a boolean when present')
            cap_exit = verification_seal.get('capExit')
            if cap_exit is not None and cap_exit not in ALLOWED_CAP_EXITS:
                die(f'{source}: verificationSeal.capExit must be one of {sorted(ALLOWED_CAP_EXITS)}')
            follow_up = verification_seal.get('followUp')
            if follow_up is not None:
                if not isinstance(follow_up, dict):
                    die(f'{source}: verificationSeal.followUp must be an object when present')
                restore_reason = follow_up.get('restoreReason')
                evidence = follow_up.get('evidence')
                failure_category = follow_up.get('failureCategory')
                if not isinstance(restore_reason, str) or not restore_reason.strip():
                    die(f'{source}: verificationSeal.followUp.restoreReason must be a non-empty string')
                if not isinstance(evidence, dict):
                    die(f'{source}: verificationSeal.followUp.evidence must be an object')
                if not isinstance(failure_category, str) or not failure_category.strip():
                    die(f'{source}: verificationSeal.followUp.failureCategory must be a non-empty string')

        exported_issues = entry.get('exportedIssues')
        if exported_issues is not None:
            if not isinstance(exported_issues, dict):
                die(f'{source}: exportedIssues must be an object when present')
            exported_at = exported_issues.get('exportedAt')
            exported_by = exported_issues.get('exportedBy')
            if not isinstance(exported_at, str) or not exported_at.strip():
                die(f'{source}: exportedIssues.exportedAt must be a non-empty string')
            if not isinstance(exported_by, str) or not exported_by.strip():
                die(f'{source}: exportedIssues.exportedBy must be a non-empty string')
            if exported_by not in participant_role_keys:
                die(f'{source}: exportedIssues.exportedBy must already be a participant')
            issues = exported_issues.get('issues')
            if not isinstance(issues, list) or not issues:
                die(f'{source}: exportedIssues.issues must be a non-empty list')
            for issue in issues:
                if not isinstance(issue, dict):
                    die(f'{source}: exportedIssues.issues entries must be objects')
                title = issue.get('title')
                if not isinstance(title, str) or not title.strip():
                    die(f'{source}: exportedIssues issue title must be a non-empty string')
                for optional in ('url', 'body', 'owner', 'delivery'):
                    value = issue.get(optional)
                    if value is not None and (not isinstance(value, str) or not value.strip()):
                        die(f'{source}: exportedIssues issue {optional} must be a non-empty string when present')
                requires = issue.get('requires')
                if requires is not None:
                    if not isinstance(requires, list) or any(
                        not isinstance(item, str) or not item.strip() for item in requires
                    ):
                        die(f'{source}: exportedIssues issue requires must be a list of non-empty strings')

        verdict = entry.get('verdict')
        if verdict is not None:
            validate_verdict(verdict, source, activePhase)

        handoff = entry.get('handoff')
        if handoff is not None:
            if not isinstance(handoff, dict):
                die(f'{source}: handoff must be an object when present')
            if collab_id == active_id and DISALLOWED_VERSION_FIELD in handoff:
                die(f'{source}: handoff contains disallowed version field')
            handoff_roles = handoff.get('roles')
            if not isinstance(handoff_roles, dict):
                die(f'{source}: handoff roles must be an object when present')
            for role, state in handoff_roles.items():
                if not isinstance(role, str) or not role.strip():
                    die(f'{source}: handoff role keys must be non-empty strings')
                if role not in participant_role_keys:
                    die(f'{source}: handoff role must already be a participant: {role}')
                validate_handoff_state(state, f'{source}: handoff.{role}', reject_version_field=collab_id == active_id)

        if collab_id in collab_map:
            die(f'{source}: duplicate collab id: {collab_id}')
        ids.append(collab_id)
        slugs.append(slug)
        collab_map[collab_id] = entry

    if len(ids) != len(set(ids)):
        die(f'{source}: duplicate collab ids are not allowed')
    if len(slugs) != len(set(slugs)):
        die(f'{source}: duplicate collab slugs are not allowed')
    if len(sequences) != len(set(sequences)):
        die(f'{source}: duplicate collab sequences are not allowed')

    if active_id is not None:
        if not isinstance(active_id, str) or not active_id.strip():
            die(f'{source}: activeCollabId must be null or a non-empty string')
        if active_id not in collab_map:
            die(f'{source}: activeCollabId must point at an existing collab id')
        if collab_map[active_id].get('archived'):
            die(f'{source}: activeCollabId must not point at an archived collab')


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


def assert_turn_order_not_drifted(entry: dict, phase: str) -> list[str]:
    expected = phase_turn_order(entry, phase)
    actual = effective_turn_order(entry)
    if actual != expected:
        die(
            'TURN-ORDER-DRIFT: '
            f'phase={phase}; actual={" ".join(actual)}; expected={" ".join(expected)}'
        )
    return expected


def resume_command(entry: dict, role: str) -> str:
    return f'RESUME: {resume_command_invocation(entry, role)}'


def resume_command_invocation(entry: dict, role: str) -> str:
    return f'commands/collab/engine/registry.py speak-state --resume {entry["id"]} {role}'


def transcript_view_command(entry: dict, phase: str | None = None) -> str:
    selected_phase = phase or entry['activePhase']
    return f'commands/collab/engine/registry.py transcript-view {entry["id"]} {shlex.quote(selected_phase)}'


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
                return f'/collab participant verify {entry["id"]} {pending_role}'
            return f'/collab participant verify {entry["id"]}'
        return f'/collab seal verification {entry["id"]}'
    return f'/collab run plan {entry["id"]}'


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
        return f'/collab speak {entry["id"]}'
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
    state['nextTranscriptCommand'] = transcript_view_command(entry)
    state['policyBlockers'] = policy_blockers_for_role(state, role, pending_reviewer)
    state['phaseSummary'] = phase_summary_for_state(entry, state)
    anchors = active_phase_anchors(transcript, entry['activePhase'])
    if anchors:
        state['excerptAnchors'] = anchors


def die_with_resume(message: str, entry: dict, role: str) -> None:
    die(f'{message}\n{resume_command(entry, role)}')


def completion_summary_empty(transcript: str) -> bool:
    try:
        lines = phase_section(transcript, 'Completion')
    except SystemExit as exc:
        if str(exc) == 'transcript phase missing: Completion':
            return True
        raise
    for line in lines:
        if SUMMARY_HEADING_RE.match(line.strip()):
            return False
    return True


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
        return f"NEXT: Run /collab run plan for role {effective_turn_order(entry)[0]}."
    if transcript is None:
        try:
            transcript = read_transcript_for_entry(entry)
        except SystemExit:
            order = effective_turn_order(entry)
            if order:
                return f'NEXT: Run /collab speak for role {order[0]}.'
            return f'NEXT: Active phase is {phase}.'
    try:
        state = speak_state_for_entry(entry, transcript)
    except SystemExit:
        order = effective_turn_order(entry)
        if order:
            return f'NEXT: Run /collab speak for role {order[0]}.'
        return f'NEXT: Active phase is {phase}.'
    expected = state.get('expectedRole')
    if expected:
        return f'NEXT: Run /collab speak for role {expected}.'
    return f'NEXT: Active phase is {phase}.'


def next_line_after_speak(entry: dict, role: str, phase: str, transcript: str) -> str:
    if phase == 'Discussion':
        return f'NEXT: Run /compact before your next collab command for role {role}.'
    return next_line_for_state(entry, transcript)


def load_effort_defaults(path: Path) -> dict:
    if not path.exists():
        die(f'effort source missing: {path}')
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f'effort source invalid JSON: {path}: {exc}')
    matrix = data.get('matrix')
    if not isinstance(matrix, dict):
        die(f'effort source missing matrix: {path}')
    levels = data.get('levels')
    if levels is not None and not isinstance(levels, dict):
        die(f'effort source levels must be an object: {path}')
    return data


def effort_value(defaults: dict, phase: str, role: str) -> str | None:
    matrix = defaults['matrix']
    if phase not in matrix or not isinstance(matrix[phase], dict):
        die(f'effort source missing phase: {phase}')
    phase_defaults = matrix[phase]
    if role not in phase_defaults:
        return DEFAULT_OPEN_ROSTER_EFFORT
    effort = phase_defaults[role]
    if effort is not None and not isinstance(effort, str):
        die(f'effort source invalid value for role {role} in phase {phase}')
    return effort


def effort_phrase(defaults: dict, effort: str | None, phase: str, role: str) -> str:
    if effort is None:
        return f'{role} is not on the turn-order roster for {phase}'
    levels = defaults.get('levels', {})
    phrase = levels.get(effort) if isinstance(levels, dict) else None
    if not isinstance(phrase, str) or not phrase.strip():
        die(f'effort source missing level phrase: {effort}')
    return phrase.strip()


def effort_line(defaults: dict, phase: str, role: str) -> str:
    effort = effort_value(defaults, phase, role)
    phrase = effort_phrase(defaults, effort, phase, role)
    label = effort if effort is not None else 'not-on-roster'
    return f'EFFORT: {label} for {role} in {phase} \u2014 next-turn recommendation; {phrase}.'


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


def normalize_rendered_effort_cell(value: str) -> str | None:
    cleaned = re.sub(r'<[^>]+>', '', value).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if cleaned in {'', '-', '\u2014'} or cleaned.startswith('\u2014 '):
        return None
    match = re.match(r'`?([A-Za-z][A-Za-z0-9_-]*)`?', cleaned)
    if not match:
        return cleaned
    return match.group(1)


def parse_markdown_table(lines: list[str], start_index: int) -> tuple[list[str], list[dict[str, str]], int]:
    headers = [cell.strip() for cell in lines[start_index].strip().strip('|').split('|')]
    separator_index = start_index + 1
    if separator_index >= len(lines) or not re.match(
        r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$',
        lines[separator_index],
    ):
        die(f'effort matrix rendered table missing separator after line {start_index + 1}')
    rows: list[dict[str, str]] = []
    index = separator_index + 1
    while index < len(lines) and lines[index].lstrip().startswith('|'):
        cells = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
        if len(cells) != len(headers):
            die(f'effort matrix rendered table malformed at line {index + 1}')
        rows.append(dict(zip(headers, cells)))
        index += 1
    return headers, rows, index


def parse_agent_model_effort_table(model_path: Path) -> tuple[list[str], dict[str, dict[str, str]], bool]:
    if not model_path.exists():
        die(f'effort model projection missing: {model_path}')
    lines = model_path.read_text().splitlines()
    heading_index = None
    for index, line in enumerate(lines):
        if line.strip() == '## Per-speak-turn effort':
            heading_index = index
            break
    if heading_index is None:
        die('effort matrix rendered table missing heading: ## Per-speak-turn effort')

    table_index = None
    marker_found = False
    for index in range(heading_index + 1, len(lines)):
        stripped = lines[index].strip()
        if table_index is None and EFFORT_MODEL_MARKER in stripped.lower():
            marker_found = True
        if stripped.startswith('|'):
            table_index = index
            break
    if table_index is None:
        die('effort matrix rendered table missing after heading: ## Per-speak-turn effort')

    headers, rows, _ = parse_markdown_table(lines, table_index)
    if not headers or headers[0] != 'Phase':
        die('effort matrix rendered table first column must be Phase')
    roles = headers[1:]
    by_phase: dict[str, dict[str, str]] = {}
    for row in rows:
        phase = row.get('Phase', '').strip()
        if not phase:
            die('effort matrix rendered table contains row with blank Phase')
        if phase in by_phase:
            die(f'effort matrix rendered table duplicate phase/row: {phase}')
        by_phase[phase] = {role: row.get(role, '') for role in roles}
    return roles, by_phase, marker_found


def rendered_effort_drift_items(defaults: dict, model_path: Path) -> list[str]:
    roles, rendered_by_phase, marker_found = parse_agent_model_effort_table(model_path)
    matrix = defaults['matrix']
    failures: list[str] = []
    if not marker_found:
        failures.append(
            f'header-missing: expected "{EFFORT_MODEL_MARKER}" before rendered effort table in {model_path}'
        )

    expected_roles: list[str] = []
    for phase_defaults in matrix.values():
        for role in phase_defaults:
            if role not in expected_roles:
                expected_roles.append(role)
    for role in expected_roles:
        if role not in roles:
            failures.append(
                f'role {role}, phase/row <header>: JSON value present, rendered value missing-column'
            )

    for phase, phase_defaults in matrix.items():
        rendered_row = rendered_by_phase.get(phase)
        if rendered_row is None:
            failures.append(
                'role <all>, phase/row '
                f'{phase}: JSON value {json.dumps(phase_defaults, sort_keys=True)}, rendered value missing-row'
            )
            continue
        for role, json_value in phase_defaults.items():
            rendered_raw = rendered_row.get(role)
            if rendered_raw is None:
                failures.append(
                    f'role {role}, phase/row {phase}: JSON value {json_value}, rendered value missing-column'
                )
                continue
            rendered_value = normalize_rendered_effort_cell(rendered_raw)
            if rendered_value != json_value:
                failures.append(
                    f'role {role}, phase/row {phase}: JSON value {json_value}, '
                    f'rendered value {rendered_raw or "<blank>"}'
                )

    for phase in rendered_by_phase:
        if phase not in matrix:
            failures.append(
                f'role <all>, phase/row {phase}: JSON value missing-row, rendered value present'
            )
    return failures


def audit_effort_matrix(effort_defaults_path: Path, model_path: Path) -> int:
    defaults = load_effort_defaults(effort_defaults_path)
    failures = rendered_effort_drift_items(defaults, model_path)
    if failures:
        for failure in failures:
            print(f'effort matrix drift: {failure}', file=sys.stderr)
        return 1
    print('OK: agent-model.md effort projection matches agent-effort.json')
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
            return f'NEXT: Run /collab run plan for role {assigned_role}.'
    if issue_terminal(entry):
        if not exported_issue_handoff_present(entry):
            export_role = 'pe' if has_participant(entry, 'pe') else next(
                (
                    role for role in effective_turn_order(entry)
                    if role != entry['moderatorRole']
                ),
                'pe',
            )
            return f'NEXT: Run /collab export-issues for role {export_role}.'
        return next_line_for_state(entry)
    if reviewer_backed(entry):
        if participant_verification_enabled(entry):
            pending_role = first_pending_participant_verification_role(entry)
            if pending_role:
                return f'NEXT: Run /collab participant verify for role {pending_role}.'
        return f'NEXT: Run /collab seal verification for role {reviewer_role(entry)}.'
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
                if value == 'Completion':
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
                if value == entry['moderatorRole']:
                    die('reviewer must not be the moderator')
                if value in entry['turnOrder']:
                    die('reviewer must not appear in turnOrder')
                entry['reviewerRole'] = value
                entry['reviewerMode'] = DEFAULT_REVIEWER_MODE
                entry.setdefault('reviewerOptionalPhases', list(DEFAULT_REVIEWER_OPTIONAL_PHASES))
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
        transcript_path = Path(entry['transcriptPath'])
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, roles_dir)
            if forced_active_phase:
                force_advisory = forced_active_phase_advisory(entry, rendered)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
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

        transcript_path = Path(next_entry['transcriptPath'])
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
        transcript_path = Path(entry['transcriptPath'])
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


def read_transcript_for_entry(entry: dict) -> str:
    transcript_path = Path(entry['transcriptPath'])
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')
    return transcript_path.read_text()


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
    rendered = transcript if raw or phase == 'Audit' else rendered_transcript_without_full_bodies(transcript)
    lines = rendered.splitlines()
    start, end = section_bounds(lines, f'## {phase}')
    sys.stdout.write('\n'.join(lines[start:end]) + '\n')
    return 0


def speak_lifecycle_live(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        transcript_path = Path(entry['transcriptPath'])
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


def read_budget_spec(path: Path = DEFAULT_BUDGET_PATH) -> dict:
    if not path.exists():
        die(f'contribution budget spec missing: {path}')
    text = path.read_text()
    limit_match = re.search(r'capped at \*\*(\d+) words\*\*', text)
    if not limit_match:
        die(f'contribution budget spec missing word limit: {path}')
    classes = set(re.findall(r'\|\s*`([a-z0-9-]+)`\s*\|', text))
    required = {
        'action-plan-checklist',
        'conclusion-ratification',
        'moderator-verbatim',
        'effort-override-line',
        'contribution-full-body',
    }
    missing = required - classes
    if missing:
        die(f'contribution budget spec missing exempt class: {sorted(missing)[0]}')
    return {'limit': int(limit_match.group(1)), 'classes': classes}


def is_conclusion_ratification_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r'^\d+\.\s+\*\*[^*]+:\*\*\s+\S', stripped):
        return True
    return bool(re.match(r'^-\s+\*\*[^*]+:\*\*\s+\S', stripped))


def budget_countable_lines(content: str, phase: str) -> list[str]:
    countable: list[str] = []
    lines = strip_managed_full_body_lines(content.splitlines(), 'contribution body')
    for line in lines:
        stripped = line.strip()
        if stripped == '<!-- collab:content-only; do-not-execute -->':
            continue
        if TIMESTAMP_RE.match(stripped):
            continue
        if EFFORT_OVERRIDE_RE.match(stripped):
            continue
        if EFFORT_OVERRIDE_COMMENT_RE.match(stripped):
            continue
        if phase == 'Action Plan' and ACTION_PLAN_EXEMPT_RE.match(line):
            continue
        if phase == 'Conclusion' and is_conclusion_ratification_line(line):
            continue
        countable.append(line)
    return countable


def enforce_contribution_budget(
    content: str,
    phase: str,
    role: str,
    moderator_role: str,
    verbatim: bool,
    spec_path: Path = DEFAULT_BUDGET_PATH,
) -> None:
    spec = read_budget_spec(spec_path)
    if role == moderator_role:
        return
    countable_text = '\n'.join(budget_countable_lines(content, phase))
    count = len(countable_text.split())
    limit = spec['limit']
    if count > limit:
        die(
            f'contribution excerpt is {count} words; limit is {limit}; '
            'keep --content-file as a capped standalone excerpt and put complete detail in --full-body-file'
        )


def action_plan_label_advisory(content: str, phase: str) -> str | None:
    if phase != 'Action Plan':
        return None
    count = sum(1 for line in content.splitlines() if UNLABELED_ACTION_CHECKBOX_RE.match(line))
    if not count:
        return None
    item = 'item' if count == 1 else 'items'
    return (
        f'LABEL-ADVISORY: {count} unlabeled Action Plan checklist {item}; '
        'use **<role>:** labels for executable work.'
    )


def is_markdown_heading(line: str) -> bool:
    return bool(re.match(r'^\s{0,3}#{1,6}(?:\s|$)', line))


def action_plan_shape_abort(line_number: int, line: str) -> None:
    die(
        f"ABORT: line {line_number} does not match Action Plan shape '- [ ] **<role>:** ...' "
        f"(Invariant #9, invariants.md). Offending line: '{line}'. "
        f"Example: '{ACTION_PLAN_SHAPE_EXAMPLE}'"
    )


def action_plan_tag_abort(line_number: int, line: str) -> None:
    tags = ', '.join(ACTION_PLAN_ALLOWED_ITEM_TAG_LIST)
    die(
        f'ABORT: line {line_number} missing recognized Action Plan item tag; '
        'loop target: Action Plan for missing executable scope. '
        f'Expected one of: {tags}. Offending line: {line!r}.'
    )


def action_plan_executable_scope_abort() -> None:
    die(
        'ABORT: action-plan advance blocked: missing [execute] item for execution directive; '
        'loop target: Action Plan for missing executable scope.'
    )


def validate_action_plan_shape(content: str, phase: str) -> None:
    if phase != 'Action Plan':
        return
    saw_assignment = False
    in_html_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if in_html_comment:
            if '-->' in stripped:
                in_html_comment = False
            continue
        if stripped.startswith('<!--'):
            if '-->' not in stripped[stripped.find('<!--') + 4:]:
                in_html_comment = True
            continue
        if not stripped:
            continue
        if line_number == 1 and EFFORT_OVERRIDE_RE.match(stripped):
            continue
        if is_markdown_heading(line):
            continue
        if ACTION_PLAN_SHAPE_RE.match(line):
            match = ACTION_CHECKLIST_RE.match(line)
            if not match or action_plan_item_tag(match.group('text').strip()) is None:
                action_plan_tag_abort(line_number, line)
            saw_assignment = True
            continue
        action_plan_shape_abort(line_number, line)
    if not saw_assignment:
        die(
            'ABORT: Action Plan body contains no assignment lines after exempt content is removed '
            f"(Invariant #9, invariants.md). Example: '{ACTION_PLAN_SHAPE_EXAMPLE}'"
        )


def validate_action_plan_executable_scope(transcript: str) -> None:
    items = action_plan_checklist_items(transcript)
    if not items:
        action_plan_executable_scope_abort()
    if not any(item.get('tag') == ACTION_PLAN_EXECUTE_TAG for item in items):
        action_plan_executable_scope_abort()


def first_substantive_lines(content: str, limit: int) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    in_html_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if in_html_comment:
            if '-->' in stripped:
                in_html_comment = False
            continue
        if stripped.startswith('<!--'):
            if '-->' not in stripped[stripped.find('<!--') + 4:]:
                in_html_comment = True
            continue
        if not stripped:
            continue
        if line_number == 1 and EFFORT_OVERRIDE_RE.match(stripped):
            continue
        lines.append((line_number, stripped))
        if len(lines) >= limit:
            break
    return lines


def conclusion_directive_gap_abort() -> None:
    die(
        'CONCLUSION-DIRECTIVE-GAP-MISSING: loop target: Completion/Conclusion '
        'for missing directive-gap evidence. Expected first lines: '
        '\'**Directive:** "<active directive>"\' and '
        '\'**Action Plan: satisfies | partially satisfies | defers**\'.'
    )


def validate_conclusion_directive_gap(content: str, phase: str) -> None:
    if phase != 'Conclusion':
        return
    lines = first_substantive_lines(content, 2)
    if len(lines) < 2:
        conclusion_directive_gap_abort()
    directive_line = lines[0][1]
    action_line = lines[1][1]
    if not CONCLUSION_DIRECTIVE_LINE_RE.match(directive_line):
        conclusion_directive_gap_abort()
    match = CONCLUSION_ACTION_PLAN_LINE_RE.match(action_line)
    if not match:
        conclusion_directive_gap_abort()
    if match.group('status') in {'partially satisfies', 'defers'} and not match.group('detail').strip():
        conclusion_directive_gap_abort()


def validate_reviewer_conclusion_gates(content: str, phase: str, role: str, entry: dict) -> None:
    if phase != 'Conclusion' or role != reviewer_role(entry):
        return
    missing = [gate for gate in REVIEWER_DISCIPLINE_GATES if gate not in content]
    if missing:
        die('REVIEWER-CONCLUSION-GATE-MISSING: ' + ', '.join(missing))


def validate_effort_override(content: str, phase: str, role: str, moderator_role: str) -> None:
    if role == moderator_role:
        return
    lines = content.splitlines()
    first_line = lines[0].strip() if lines else ''
    override_lines = [
        (index, line.strip())
        for index, line in enumerate(lines)
        if line.strip().startswith('EFFORT OVERRIDE:')
    ]
    if (phase, role) in MANDATORY_EFFORT_OVERRIDE_TURNS and not override_lines:
        die(f'effort override required for {phase}-{role}')
    if not override_lines:
        return
    first_index, first_override = override_lines[0]
    if first_index != 0:
        die('EFFORT OVERRIDE must be the first content line')
    if not EFFORT_OVERRIDE_RE.match(first_override):
        die('EFFORT OVERRIDE line has invalid format')
    if len(override_lines) > 1:
        die('EFFORT OVERRIDE must appear at most once')


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


def preserve_case_replacement(match: re.Match[str], replacement: str) -> str:
    text = match.group(0)
    if text.isupper():
        return replacement.upper()
    if text[:1].isupper() and text[1:].islower():
        return replacement[:1].upper() + replacement[1:].lower()
    return replacement


def read_moderator_polish_spec(path: Path = DEFAULT_MODERATOR_POLISH_PATH) -> dict:
    if not path.exists():
        die(f'moderator polish spec missing: {path}')
    typos: list[tuple[str, str]] = []
    for line in path.read_text().splitlines():
        match = TYPO_ROW_RE.match(line)
        if not match:
            continue
        typo = match.group('typo')
        fix = match.group('fix')
        if fix.startswith(f'{typo} '):
            fix = typo
        typos.append((typo, fix))
    if not typos:
        die(f'moderator polish spec missing typo dictionary: {path}')
    return {'typos': typos}


def polish_moderator_content(content: str, spec_path: Path = DEFAULT_MODERATOR_POLISH_PATH) -> str:
    spec = read_moderator_polish_spec(spec_path)
    lines = [line.rstrip() for line in content.splitlines()]
    rendered: list[str] = []
    in_code = False
    blank_pending = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code = not in_code
            rendered.append(raw_line)
            blank_pending = False
            continue
        if stripped == '':
            if not blank_pending:
                rendered.append('')
            blank_pending = True
            continue
        blank_pending = False
        line = raw_line
        if not in_code:
            line = re.sub(r'^(\s*)[*+]\s+', r'\1- ', line)
            for typo, fix in spec['typos']:
                line = re.sub(re.escape(typo), lambda match, replacement=fix: preserve_case_replacement(match, replacement), line, flags=re.IGNORECASE)
            list_match = re.match(r'^(\s*-\s+)([a-z])', line)
            if list_match:
                line = list_match.group(1) + list_match.group(2).upper() + line[list_match.end():]
            elif line and line[0].islower():
                line = line[0].upper() + line[1:]
            if (
                line
                and not EFFORT_OVERRIDE_RE.match(line.strip())
                and not line.endswith(('.', '?', '!', ':', '`'))
                and not line.lstrip().startswith(('- ', '#', '|'))
            ):
                line += '.'
        rendered.append(line)
    return '\n'.join(rendered).rstrip('\n')


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

        transcript_path = Path(current_entry['transcriptPath'])
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
        anchor, block = render_contribution_block(
            phase,
            role,
            counter,
            content,
            timestamp or format_timestamp(),
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
        print('RETRACT: use /collab retract speak to tombstone the latest active-phase contribution')
        print_header_overwrite(header_changed)
        label_advisory = action_plan_label_advisory(content, phase)
        if label_advisory:
            print(label_advisory)
        commit_registry_and_transcript(path, nextdata, transcript_path, rendered_text)
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
        die('no prior contribution to rewrite; use /collab speak to create the first contribution')
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
        transcript_path = Path(entry['transcriptPath'])
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
        rendered = replace_latest_contribution(
            transcript,
            phase,
            role,
            content,
            timestamp or format_timestamp(),
            full_body,
        )
        if handoff_state is not None:
            rendered_lines = rendered.splitlines()
            bounds = contribution_block_bounds(rendered_lines, phase, role)
            if bounds is None:
                die('no prior contribution to rewrite; use /collab speak to create the first contribution')
            start, end = bounds
            handoff_state['body'] = '\n'.join(contribution_body_lines(rendered_lines[start:end])).rstrip('\n')
            set_handoff_state(entry, role, handoff_state)
            rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
            print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
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
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'advance' if direction == 'next' else 'restore')
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        index = PHASES.index(entry['activePhase'])
        from_phase = entry['activePhase']
        transcript_path = Path(entry['transcriptPath'])
        transcript = transcript_path.read_text() if transcript_path.exists() else None
        if direction == 'next':
            if index == len(PHASES) - 1:
                die('no next phase')
            if from_phase == 'Action Plan':
                if transcript is None:
                    die(f'transcript missing: {transcript_path}')
                validate_action_plan_executable_scope(transcript)
            entry['activePhase'] = PHASES[index + 1]
            if entry['activePhase'] in MOD_EXCLUDED_PHASES:
                remove_moderator_from_turn_order(entry)
            if entry['activePhase'] == 'Completion':
                # Scope-aware on (re)entry into Completion: a fresh round, and for
                # a reopen that preserved prior verification, keep the completed
                # verification of roles whose write scope is unchanged so only the
                # re-scoped roles re-verify. The all-preserved fallback in
                # reset_participant_verification_stages keeps a round earnable.
                initialize_completion_state(entry, 'execution', reset_rounds=True, scope_aware=True)
        else:
            if index == 0:
                die('no previous phase')
            entry['activePhase'] = PHASES[index - 1]
            normalize_turn_order_for_phase(entry, entry['activePhase'])
            if entry['activePhase'] != 'Completion':
                invalidate_verification_seal(entry, f'restored to {entry["activePhase"]}')

        notice = transition_notice(from_phase, entry['activePhase'])
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript or transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
            notice = add_completion_summary_notice(notice, rendered)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_post_action_advisories(
        entry,
        None,
        None,
        notice,
        next_line_for_state(entry),
    )
    print_phase_result(entry['activePhase'], notice, emit_json)
    return 0


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
        transcript = read_transcript_for_entry(entry) if Path(entry['transcriptPath']).exists() else ''
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
        if seal_terminal(entry) and reviewer_backed(entry) and previous_signature != execution_signature(entry):
            invalidate_verification_seal(entry, f'execution changed for {role}')
        closed = False
        if issue_terminal(entry) and entry['activePhase'] == 'Completion':
            if auto_close and close_eligible_after_execution(entry, assigned_roles):
                entry['status'] = 'closed'
                closed = True
                if data.get('activeCollabId') == entry['id']:
                    data['activeCollabId'] = None
        elif seal_terminal(entry) and reviewer_backed(entry) and entry['activePhase'] == 'Completion':
            if close_eligible_after_execution(entry, assigned_roles):
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
                    initialize_completion_state(entry, 'verification', reset_rounds=True)
                else:
                    initialize_completion_state(entry, 'execution')
        elif auto_close and close_eligible_after_execution(entry, assigned_roles):
            entry['status'] = 'closed'
            closed = True
            if data.get('activeCollabId') == entry['id']:
                data['activeCollabId'] = None

        notice = lifecycle_status_notice('closed') if closed else None
        next_line = next_line_after_execution(entry, assigned_roles)
        transcript_path = Path(entry['transcriptPath'])
        if closed and transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
            if completion_summary_empty(rendered):
                rendered = append_completion_summary(
                    rendered,
                    default_close_summary(entry),
                    summary_date_from_timestamp(date),
                )
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line)
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
    return 0


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
            die('/collab export-issues is valid only in Completion')
        if not issue_terminal(entry):
            die('/collab export-issues requires terminal issue')
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
        transcript_path = Path(entry['transcriptPath'])
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


def replace_table_after_heading(
    transcript: str,
    heading: str,
    replacement: str,
    missing_section_message: str,
    missing_table_message: str,
) -> str:
    lines = transcript.splitlines()
    heading_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            heading_index = index
            break
    if heading_index is None:
        die(missing_section_message)

    table_start: int | None = None
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith('|'):
            table_start = index
            break
        if lines[index].startswith('**') or lines[index].startswith('## '):
            break
    if table_start is None:
        die(missing_table_message)

    table_end = table_start
    while table_end < len(lines) and lines[table_end].startswith('|'):
        table_end += 1

    return '\n'.join(lines[:table_start] + replacement.splitlines() + lines[table_end:]) + '\n'


def replace_status_table(transcript: str, entry: dict) -> str:
    return replace_table_after_heading(
        transcript,
        '**Status**',
        rendered_status_table(entry),
        'transcript status section missing',
        'transcript status table missing',
    )


def replace_reviewer_section_text(transcript: str, entry: dict, roles_dir: Path) -> str:
    lines = transcript.splitlines()
    heading_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == '**Reviewer**':
            heading_index = index
            break
    if heading_index is None:
        return transcript
    section_end: int | None = None
    for index in range(heading_index + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped == '---' or (stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4):
            section_end = index
            break
    if section_end is None:
        return transcript
    new_content = rendered_reviewer_section(entry, roles_dir)
    if new_content is None:
        return transcript
    new_lines = lines[:heading_index + 1] + [''] + new_content.splitlines() + [''] + lines[section_end:]
    return '\n'.join(new_lines) + '\n'


def replace_participants_table_text(transcript: str, entry: dict, roles_dir: Path) -> str:
    return replace_table_after_heading(
        transcript,
        '**Participants**',
        rendered_participants_table(entry, roles_dir),
        'transcript participants section missing',
        'transcript participants table missing',
    )


def replace_participants_table(transcript_path: Path, entry: dict, roles_dir: Path) -> None:
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')
    transcript = transcript_path.read_text()
    replacement = replace_participants_table_text(transcript, entry, roles_dir)
    transcript_path.write_text(replacement)


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
            die('/collab reopen is valid only after a non-success Completion verdict')
        verdict = entry.get('verdict')
        if not isinstance(verdict, dict) or verdict.get('outcome') not in {'incomplete', 'failed'}:
            die('/collab reopen requires a non-success Completion verdict')
        restore_target = verdict.get('restoreTarget')
        if restore_target != phase:
            expected_token = 'handoff' if restore_target == 'Handoff' else 'action-plan'
            die(f'/collab reopen phase mismatch: verdict restoreTarget is {restore_target}; expected {expected_token}')
        transcript_path = Path(entry['transcriptPath'])
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


def render_status(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(transcript_path)
    return 0


def re_summarize_collab(path: Path, target: str, summary_file: Path, date: str | None = None) -> int:
    if not summary_file.exists():
        die(f'summary file missing: {summary_file}')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] == 'archived':
            die('record is archived')
        transcript_path = Path(entry['transcriptPath'])
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
        transcript_path = Path(entry['transcriptPath'])
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


def commit_new_registry_and_transcript(
    registry_path: Path,
    data: dict,
    transcript_path: Path,
    transcript_text: str,
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
    if transcript_path.exists():
        die(f'record already exists: {transcript_path}')

    registry_after = json.dumps(data, indent=2) + '\n'
    registry_tmp = registry_path.with_name(f'{registry_path.name}.tmp')
    transcript_tmp = transcript_path.with_name(f'{transcript_path.name}.tmp')

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
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
            transcript_path.unlink(missing_ok=True)
        except OSError:
            inconsistent.append(str(transcript_path))
        registry_tmp.unlink(missing_ok=True)
        transcript_tmp.unlink(missing_ok=True)
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
        if participant_verification and terminal == 'seal':
            entry['verification'] = {
                'rounds': 0,
                'cap': DEFAULT_VERIFICATION_CAP,
                'subState': 'participant',
                'participantVerification': True,
                'participants': {},
            }

        nextdata = deepcopy(data)
        count_caller_declined_agent_id_write(nextdata, agent_id)
        nextdata['collabs'].append(entry)
        nextdata['activeCollabId'] = collab_id
        rendered = render_initial_transcript(title, entry, roles_dir, format_banner_timestamp())
        commit_new_registry_and_transcript(path, nextdata, transcript_path, rendered)
    print(transcript_path)
    if open_requested:
        file_uri = transcript_path.resolve().as_uri()
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

        transcript_path = Path(next_entry['transcriptPath'])
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
        'NEXT: Run /collab show policy before first speak.',
    )
    print(f'TRANSCRIPT: {transcript_view_command(next_entry)}')
    print(f'IDENTITY: {role} {recorded_agent_id}')
    if identity_warning:
        print(identity_warning)
    print(' '.join(participant_roles(next_entry)))
    if emit_json:
        print(json.dumps({
            'agentId': recorded_agent_id,
            'freshRegistryRead': True,
            'identityWarning': identity_warning,
            'nextTranscriptCommand': transcript_view_command(next_entry),
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
        entry['status'] = 'archived'
        entry['archived'] = True
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        transcript_path = Path(entry['transcriptPath'])
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    notice = lifecycle_status_notice('archived')
    print_post_action_advisories(entry, None, None, notice, next_line_for_state(entry))
    print(entry['id'])
    print_notice_diagnostic(notice, emit_json)
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
        transcript_path = Path(entry['transcriptPath'])
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
        transcript_path = Path(entry['transcriptPath'])
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
        transcript_path = Path(entry['transcriptPath'])
        data['collabs'] = [candidate for candidate in data['collabs'] if candidate['id'] != entry['id']]
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        if transcript_path.exists():
            transcript_path.unlink()
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
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        lines = transcript.splitlines()
        bounds = contribution_block_bounds(lines, entry['activePhase'], role)
        if bounds is None:
            die(f'no contribution found for {role} in {entry["activePhase"]}')
        start, end = bounds
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


def source_text(path: Path) -> str:
    if not path.exists():
        return ''
    return path.read_text()


def validate_source_contracts() -> None:
    if not DEFAULT_FLAG_TAXONOMY_PATH.exists():
        die(f'source contract missing flag taxonomy: {DEFAULT_FLAG_TAXONOMY_PATH.relative_to(DEFAULT_CONFIG_ROOT)}')

    seal_verification = DEFAULT_CONFIG_ROOT / 'commands/collab/seal-verification/index.md'
    require_source_text(seal_verification, 'restore-route-recovery', 'restore-route recovery anchor')
    require_source_text(seal_verification, '/collab show verdict', 'restore-route verdict inspection')
    require_source_text(seal_verification, '/collab reopen action-plan', 'restore-route action-plan reopen')
    require_source_text(seal_verification, '/collab reopen handoff', 'restore-route handoff reopen')
    require_source_text(seal_verification, '/collab run plan', 'restore-route rerun step')
    require_source_text(seal_verification, '/collab seal verification', 'restore-route reseal step')

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

    init_parser = subparsers.add_parser(
        'init',
        usage=(
            '%(prog)s --agent-id <agentId> [--reviewer <role>] '
            '[--terminal <seal|issue>] [--no-participant-verification] [--work-repo <path>] [--preview] <name>'
        ),
        description='Create a registry-backed collab record.',
    )
    init_parser.add_argument('--agent-id', action='append')
    init_parser.add_argument('--reviewer', action='append')
    init_parser.add_argument('--terminal', action='append')
    init_parser.add_argument('--work-repo', action='append')
    init_parser.add_argument('--no-participant-verification', dest='participant_verification', action='store_false', default=True)
    init_parser.add_argument('--preview', action='store_true')
    init_parser.add_argument('name', nargs='*')

    join_participants_parser = subparsers.add_parser('join-participants')
    join_participants_parser.add_argument('target')
    join_participants_parser.add_argument('role')
    join_participants_parser.add_argument('--agent-id', required=True)
    join_participants_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    join_participants_parser.add_argument('--json', action='store_true')

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

    render_status_parser = subparsers.add_parser('render-status')
    render_status_parser.add_argument('target')

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
        if args.preview:
            tokens.append('--preview')
        tokens.extend(args.name)
        return init_collab(path, tokens, DEFAULT_ROLES_DIR)
    if args.command == 'join-participants':
        return join_participants(path, args.target, args.role, args.agent_id, Path(args.roles_dir), args.json)
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
    if args.command == 'render-status':
        return render_status(path, args.target)
    if args.command == 'render-participants':
        return render_participants(path, args.target, Path(args.roles_dir))
    if args.command == 'write-guard':
        return write_guard(args.route, args.paths)
    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
