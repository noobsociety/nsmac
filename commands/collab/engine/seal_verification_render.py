"""Seal/verification rendering and write entry points for collab records.

Owns: participant-verify rendering, assessment/seal rendering,
      reviewer-findings blocks, summary/history rendering, seal writing,
      and verdict recording.

Does not own: stale-seal trigger decisions, participant verification state,
              verdict validation, content-integrity gates, phase lifecycle
              sequencing, participant roster management, non-seal transcript
              rendering, or CLI dispatch. This module calls the logic module
              explicitly and is imported directly by registry_core.py for CLI
              dispatch; engine leaves import the concrete split modules directly.

Naming convention
  *_state(entry, ...)   -- pure registry-entry accessor; no I/O or side effects.
  *_state(path, ...)    -- CLI-callable reader; loads registry from path and persists normalized state.
  seal_write(...)       -- writes the immutable verification seal snapshot.
  record_verdict(...)   -- records the assessment verdict.
"""

from __future__ import annotations

import datetime as dt

import hashlib

import html

import json

import os

import re

from collections.abc import Callable

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def resolve_config_root() -> Path:
    configured = os.environ.get('COMMAND_CONFIG_ROOT')
    if configured:
        return Path(configured).expanduser().resolve()
    if (ROOT / 'commands').is_dir():
        return ROOT
    return ROOT

DEFAULT_CONFIG_ROOT = resolve_config_root()

DEFAULT_ROLES_DIR = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/roles'

SEAL_VERDICT_KIND = 'collab.seal-verdict'

from commands.collab.engine import transcript_readers

from commands.collab.engine.transcript_readers import (
    completion_summary_empty,
    phase_section,
    read_transcript_for_entry,
    section_bounds,
    transcript_path_for_entry,
)

from commands.collab.engine.transcript_readers import SUMMARY_HEADING_RE

from commands.collab.engine.transcript_readers import ANCHOR_RE

from commands.collab.engine.dispatch_forms import collab_dispatch

from commands.collab.engine.errors import die

from commands.collab.engine.registry_constants import (
    ACTIVE_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_COMPLETION_SUBSTATES,
    ALLOWED_VERDICT_OUTCOMES,
    CONTENT_ONLY_GUARD,
)

from commands.collab.engine.digests import (
    active_execution_entries,
    content_digest_for_touched_paths,
    execution_coverage_entries,
    execution_signature,
    full_body_signature_for_transcript,
    participant_execution_signature,
    participant_write_scope_signature,
    touched_paths_for_execution,
    validation_scopes_for_execution,
)

from commands.collab.engine.execution import (
    all_execution_completed,
    assert_execution_touched_paths_in_git_state,
    assert_no_execution_agent_conflation,
    assert_touched_paths_inside_handoff,
    execution_scope_advisory,
)

from commands.collab.engine.git_repo import work_repo_root

from commands.collab.engine.normalizers import (
    format_timestamp,
    normalize_touched_paths,
)

from commands.collab.engine.participants import (
    assert_caller_role,
    effective_turn_order,
    has_participant,
    participant_agent_id,
    reviewer_backed,
    reviewer_role,
    reviewer_state,
)

from commands.collab.engine.phase_lifecycle import lifecycle_status_notice, print_notice_diagnostic

from commands.collab.engine.registry_io import (
    commit_registry_and_transcript,
    load_registry,
    registry_lock,
    registry_revision,
    resolve_collab,
    save_registry,
)

from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    render_managed_header_text,
    rendered_collapsible_block,
)
from commands.collab.engine.seal_verification_logic import (
    all_participant_verification_completed,
    assert_chartered_deliverables_covered,
    assert_verification_execution_ready,
    build_verdict,
    clear_verdict,
    completion_state,
    die_content_drift_persisted,
    ensure_legacy_content_digest,
    first_pending_participant_verification_role,
    invalidate_seal_on_content_drift,
    invalidate_seal_on_full_body_drift,
    parse_verdict_evidence,
    participant_verification_enabled,
    participant_verification_inactive_message,
    participant_verification_incomplete,
    participant_verification_role_state,
    participant_verification_roles,
    record_verification_round_for_execution,
    seal_snapshot,
    sync_participant_verification_review_substate,
    verification_review_substate,
    verification_state,
    verification_substate,
    write_seal_verdict_companion,
)

_next_line_for_state: Callable[[dict], str] | None = None

_print_post_action_advisories: Callable[[dict, str | None, str | None, dict | None, str], None] | None = None

def configure_registry_facade(
    *,
    next_line_for_state: Callable[[dict], str],
    print_post_action_advisories: Callable[[dict, str | None, str | None, dict | None, str], None],
) -> None:
    global _next_line_for_state, _print_post_action_advisories
    _next_line_for_state = next_line_for_state
    _print_post_action_advisories = print_post_action_advisories

def next_line_for_state(entry: dict) -> str:
    if _next_line_for_state is None:
        die('seal verification engine is not configured: next-line callback missing')
    return _next_line_for_state(entry)

def print_post_action_advisories(
    entry: dict,
    role: str | None,
    phase: str | None,
    notice: dict | None,
    next_line: str,
) -> None:
    if _print_post_action_advisories is None:
        die('seal verification engine is not configured: advisory callback missing')
    _print_post_action_advisories(entry, role, phase, notice, next_line)

def completion_summary_bounds(transcript: str) -> tuple[int, int]:
    lines = transcript.splitlines()
    completion_start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == '## Completion':
            completion_start = index + 1
            break
    if completion_start is None:
        die('transcript phase missing: Completion')

    heading_indexes = [
        index
        for index in range(completion_start, len(lines))
        if SUMMARY_HEADING_RE.match(lines[index].strip())
    ]
    if not heading_indexes:
        die(f'nothing yet summarized; run {collab_dispatch("write summary")} first')

    start = heading_indexes[-1]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith('## ') or SUMMARY_HEADING_RE.match(stripped):
            end = index
            break
    return start, end

def replace_latest_summary(transcript: str, summary_body: str, date: str) -> str:
    body = summary_body.strip()
    if not body:
        die('summary body must be non-empty')
    start, end = completion_summary_bounds(transcript)
    lines = transcript.splitlines()
    replacement = [f'### Summary \u2014 {date}', '', *body.splitlines(), '']
    return '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'

def append_completion_summary(transcript: str, summary_body: str, date: str) -> str:
    body = summary_body.strip()
    if not body:
        die('summary body must be non-empty')
    lines = transcript.splitlines()
    completion_start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == '## Completion':
            completion_start = index
            break
    if completion_start is None:
        die('transcript phase missing: Completion')
    insert_at = len(lines)
    replacement = ['', f'### Summary \u2014 {date}', '', *body.splitlines()]
    if insert_at > 0 and lines[insert_at - 1] == '':
        replacement = replacement[1:]
    return '\n'.join(lines[:insert_at] + replacement + lines[insert_at:]) + '\n'

def summary_date_from_timestamp(timestamp: str) -> str:
    match = re.match(r'^(\d{4}-\d{2}-\d{2})\b', timestamp)
    if match:
        return match.group(1)
    return dt.date.today().isoformat()

def default_close_summary(entry: dict) -> str:
    completed = [
        f'`{role}`'
        for role, state in sorted(entry.get('execution', {}).items())
        if state.get('status') == 'completed'
    ]
    completed_text = ', '.join(completed) if completed else 'no roles'
    touched: list[str] = []
    for state in entry.get('execution', {}).values():
        for path in state.get('touchedPaths', []):
            if isinstance(path, str) and path not in touched:
                touched.append(path)
    touched_text = ', '.join(f'`{path}`' for path in touched) if touched else 'no source paths recorded'
    return '\n'.join([
        f'Closed after completed execution for {completed_text}.',
        '',
        f'Validation result: passed for recorded role execution; touched paths: {touched_text}.',
    ])

def next_completion_history_number(transcript: str) -> int:
    try:
        lines = phase_section(transcript, 'Completion')
    except SystemExit as exc:
        if str(exc) == 'transcript phase missing: Completion':
            return 1
        raise
    highest = 0
    for line in lines:
        match = re.match(r'^\s*(\d+)\.\s+\*\*[^*]+:\*\*', line)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1

def append_completion_history_line(transcript: str, line: str) -> str:
    lines = transcript.splitlines()
    start, end = section_bounds(lines, '## Completion')
    insert_at = end
    if insert_at > start and lines[insert_at - 1] != '':
        line_block = ['', line]
    else:
        line_block = [line]
    return '\n'.join(lines[:insert_at] + line_block + lines[insert_at:]) + '\n'

def summary_date_from_iso(timestamp: str) -> str:
    match = re.match(r'^(\d{4}-\d{2}-\d{2})T', timestamp)
    if match:
        return match.group(1)
    return summary_date_from_timestamp(timestamp)

def append_participant_verify_block(
    transcript: str,
    role: str,
    turn_label: str,
    content: str,
    timestamp: str,
    agent_line: str | None = None,
) -> str:
    lines = transcript.splitlines()
    start, end = section_bounds(lines, '## Completion')
    existing = '\n'.join(lines[start:end])
    ordinal = len(re.findall(rf'<a name="participant-verify-{re.escape(role)}-\d+"></a>', existing)) + 1
    body_lines: list[str] = []
    if agent_line:
        body_lines.extend([agent_line, ''])
    body_lines.extend(content.rstrip('\n').splitlines() or ['(no findings)'])
    block = [
        '',
        *rendered_collapsible_block(
            f'participant-verify-{role}-{ordinal}',
            f'{role} · {turn_label}',
            body_lines,
            timestamp=timestamp,
            content_guard=True,
        ),
    ]
    return '\n'.join(lines[:end] + block + lines[end:]) + '\n'

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
    if status not in {'completed', 'failed'}:
        die('participant verification status must be one of: completed, failed')
    audit_content = Path(audit_file).read_text()
    remediation_content = Path(remediation_file).read_text()
    final_audit_content = Path(final_audit_file).read_text()
    normalized_touched_paths = normalize_touched_paths(touched_paths)
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'participant-verify-render', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("participant verify")} requires activePhase = Completion')
        live_revision = registry_revision(data)
        if observed_revision != live_revision:
            die(
                f'stale registry revision: observed {observed_revision}, live {live_revision}\n'
                f'RESUME: commands/collab/engine/registry.py participant-verify-state --resume {entry["id"]} {role}'
            )
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        assert_verification_execution_ready(entry, transcript, 'participant verification')
        if reviewer_backed(entry) and all_execution_completed(entry):
            completion = completion_state(entry)
            if completion['subState'] == 'execution':
                completion['subState'] = 'verification'
                verification = verification_state(entry)
                verification['rounds'] = 0
                verification['subState'] = 'participant' if participant_verification_enabled(entry) else 'seal'
            if completion['subState'] == 'verification':
                sync_participant_verification_review_substate(entry)
        verification = verification_state(entry)
        if not participant_verification_enabled(entry) or verification['subState'] != 'participant':
            die(participant_verification_inactive_message(entry))
        assigned_roles = participant_verification_roles(entry)
        if role not in assigned_roles:
            die(f'role is not assigned to participant verification: {role}')
        pending_role = first_pending_participant_verification_role(entry)
        if pending_role != role:
            die(f'participant verification turn lock is held by role {pending_role or "none"}')
        role_state = participant_verification_role_state(entry, role)
        if role_state.get('stage') == 'completed':
            print(f'participant verification for {role} already completed')
            return 0
        if role_state.get('stage') not in ACTIVE_PARTICIPANT_VERIFICATION_STAGES:
            die(
                'participant verification turn lock is not active; '
                f'run participant-verify-state first for role {role}'
            )
        attempts = role_state.get('attempts', 0)
        assert_touched_paths_inside_handoff(entry, role, normalized_touched_paths)
        rendered_timestamp = timestamp or format_timestamp()
        execution_state = entry.get('execution', {}).get(role, {})
        execution_id = (
            execution_agent_id
            or (execution_state.get('agentId') if isinstance(execution_state, dict) else None)
            or audit_agent_id
            or participant_agent_id(entry, role)
            or 'unknown'
        )
        remediation_id = remediation_agent_id or participant_agent_id(entry, role) or execution_id
        role_state['attempts'] = attempts + 1
        role_state['stage'] = 'audit'
        role_state['stage'] = 'remediation'
        role_state['stage'] = 'final-audit'
        role_state['stage'] = status
        if status == 'completed':
            # Pin the executed content this verification certifies so a later
            # change (re-execution or a provenance repoint) invalidates it.
            role_state['executionSignature'] = participant_execution_signature(entry, role)
        agent_line = None
        if remediation_id != execution_id:
            agent_line = f'AgentId: execution={execution_id}; remediation={remediation_id}'
        rendered = append_participant_verify_block(transcript, role, 'audit', audit_content, rendered_timestamp)
        rendered = append_participant_verify_block(rendered, role, 'remediation', remediation_content, rendered_timestamp, agent_line)
        rendered = append_participant_verify_block(rendered, role, 'final-audit', final_audit_content, rendered_timestamp)
        if status == 'completed' and all_participant_verification_completed(entry):
            record_verification_round_for_execution(entry, verification)
            verification['subState'] = 'seal'
        rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(f'participant verification {status} for {role}')
    next_role = first_pending_participant_verification_role(entry)
    print(
        f'NEXT: Run {collab_dispatch("participant verify")} for role {next_role}.'
        if next_role
        else f'NEXT: Run {collab_dispatch("seal verification")} for role {reviewer_role(entry)}.'
    )
    return 0

def assessment_next_line(entry: dict, verdict: dict) -> str:
    if verdict.get('outcome') == 'success':
        return next_line_for_state(entry)
    target = verdict.get('restoreTarget', 'Action Plan')
    phase_token = 'handoff' if target == 'Handoff' else 'action-plan'
    return f'NEXT: Moderator should run {collab_dispatch("reopen", phase_token, entry["id"])}.'

def verdict_reopen_command(entry: dict, verdict: dict) -> str:
    target = verdict.get('restoreTarget', 'Action Plan')
    phase_token = 'handoff' if target == 'Handoff' else 'action-plan'
    return collab_dispatch('reopen', phase_token, entry["id"])

def evidence_list(evidence: dict, key: str) -> str:
    values = evidence.get(key)
    if not isinstance(values, list) or not values:
        return '[]'
    return json.dumps(values, ensure_ascii=True, separators=(',', ':'))

def affected_summary(evidence: dict) -> str:
    pieces: list[str] = []
    for key in ('committedPaths', 'executionEntryIds', 'transcriptIds'):
        values = evidence.get(key)
        if isinstance(values, list) and values:
            pieces.append(f'{key}={json.dumps(values, ensure_ascii=True, separators=(",", ":"))}')
    return '; '.join(pieces) if pieces else 'none'

def next_reviewer_findings_counter(transcript: str) -> int:
    highest = 0
    for line in transcript.splitlines():
        match = ANCHOR_RE.match(line.strip())
        if not match:
            continue
        anchor = match.group('anchor')
        if not anchor.startswith('reviewer-findings-'):
            continue
        suffix = anchor[len('reviewer-findings-'):]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return highest + 1

def latest_reviewer_findings_anchor(transcript: str) -> str | None:
    latest: tuple[int, str] | None = None
    for line in transcript.splitlines():
        match = ANCHOR_RE.match(line.strip())
        if not match:
            continue
        anchor = match.group('anchor')
        if not anchor.startswith('reviewer-findings-'):
            continue
        suffix = anchor[len('reviewer-findings-'):]
        if not suffix.isdigit():
            continue
        ordinal = int(suffix)
        if latest is None or ordinal > latest[0]:
            latest = (ordinal, anchor)
    return latest[1] if latest else None

def append_reviewer_findings_block(
    transcript: str,
    entry: dict,
    role: str,
    verdict: dict,
    timestamp: str,
    next_line: str,
) -> str:
    if verdict.get('outcome') == 'success':
        return transcript
    evidence = verdict.get('evidence') if isinstance(verdict.get('evidence'), dict) else {}
    failure_category = verdict.get('failureCategory') or 'uncategorized'
    restore_target = verdict.get('restoreTarget', 'Action Plan')
    restore_reason = verdict.get('restoreReason', '')
    anchor = f'reviewer-findings-{next_reviewer_findings_counter(transcript)}'
    command = verdict_reopen_command(entry, verdict)
    body_lines = [
        f'restoreReason: {restore_reason}',
        f'restoreTarget: {restore_target}',
        f'failureCategory: {failure_category}',
        'evidence:',
    ]
    evidence_revision = evidence.get('revision', evidence.get('registryRevision'))
    if evidence_revision is not None:
        body_lines.append(f'  revision: {evidence_revision}')
    body_lines.extend([
        f'  committedPaths: {evidence_list(evidence, "committedPaths")}',
        f'  executionEntryIds: {evidence_list(evidence, "executionEntryIds")}',
        f'  transcriptIds: {evidence_list(evidence, "transcriptIds")}',
        '',
        'commandPacket:',
        f'  NEXT: {command}',
        f'  REASON: {restore_reason}',
        f'  AFFECTED: {affected_summary(evidence)}',
        f'  RETURN: {restore_target}',
        '',
        f'helperNext: {next_line}',
    ])
    block = [
        '',
        *rendered_collapsible_block(
            anchor,
            (
                f'{html.escape(role)} · reopen brief '
                f'({html.escape(verdict["outcome"])}, {html.escape(failure_category)})'
            ),
            body_lines,
            timestamp=timestamp,
            content_guard=True,
        ),
    ]
    lines = transcript.splitlines()
    _start, end = section_bounds(lines, '## Completion')
    return '\n'.join(lines[:end] + block + lines[end:]) + '\n'

def insert_reopen_pointer(transcript: str, phase: str, findings_anchor: str | None, expected_role: str | None) -> str:
    if findings_anchor is None:
        return transcript
    lines = transcript.splitlines()
    start, end = section_bounds(lines, f'## {phase}')
    link = f'[reviewer findings](#{findings_anchor})'
    role_label = expected_role or 'none'
    note = f'> Reopened from {link}; next expected role: `{role_label}`.'
    if any(line.strip() == note for line in lines[start:end]):
        return transcript
    insert_at = start + 1
    while insert_at < end and lines[insert_at].strip() in {'', CONTENT_ONLY_GUARD}:
        insert_at += 1
    block = [note, '']
    if insert_at > start + 1 and lines[insert_at - 1].strip() != '':
        block = ['', *block]
    if insert_at < len(lines) and lines[insert_at].strip() == '':
        block = block[:-1]
    return '\n'.join(lines[:insert_at] + block + lines[insert_at:]) + '\n'

def assessment_notice(verdict: dict) -> dict | None:
    outcome = verdict.get('outcome')
    if outcome == 'success':
        return lifecycle_status_notice('closed')
    target = verdict.get('restoreTarget', 'Action Plan')
    return {
        'notice': 'assessment',
        'outcome': outcome,
        'restoreTarget': target,
        'message': f'Assessment verdict recorded; restore target is {target}.',
    }

def seal_write(
    path: Path,
    target: str,
    role: str,
    observed_revision: int,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'seal-write', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("seal verification")} is valid only in the Completion phase')
        live_revision = registry_revision(data)
        if observed_revision != live_revision:
            die(
                f'stale registry revision: observed {observed_revision}, live {live_revision}\n'
                f'RESUME: commands/collab/engine/registry.py seal-state --resume {entry["id"]} {role}'
            )
        reviewer = reviewer_role(entry)
        if reviewer is None:
            die('verification seal requires an active reviewer role')
        if reviewer_state(entry)['state'] != 'active':
            die(f'reviewer role is not a registered participant; run {collab_dispatch("join", "--role", reviewer)} first')
        if role != reviewer:
            die(f'seal must be authored by the reviewer role; current role: {role}; expected: {reviewer}')
        if verification_substate(entry) != 'verification':
            die(f'Completion.verification sub-state is not active; current sub-state: {verification_substate(entry)}')
        verification = verification_state(entry)
        review_substate = verification_review_substate(entry)
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        invalidate_seal_on_full_body_drift(entry, transcript)
        invalidate_seal_on_content_drift(entry)
        review_substate = verification_review_substate(entry)

        assert_verification_execution_ready(entry, transcript, 'verification seal')
        if participant_verification_incomplete(entry):
            verification['subState'] = 'participant'
            pending_role = first_pending_participant_verification_role(entry)
            die(f'participant verification is active; next role: {pending_role or "none"}')
        if review_substate == 'participant':
            verification['subState'] = 'seal'
            review_substate = 'seal'
        if review_substate != 'seal':
            die('verification assessment is active; seal block is immutable; provide --outcome to record a verdict')
        if not all_execution_completed(entry):
            die('verification seal requires all execution entries to be completed')
        assert_execution_touched_paths_in_git_state(entry)
        assert_no_execution_agent_conflation(entry)
        advisory = execution_scope_advisory(entry)
        rounds = verification['rounds']
        if rounds == 0:
            die('zero verification rounds; at least one reviewer-executor paired event is required before sealing')
        clear_verdict(entry)
        seal = seal_snapshot(entry, observed_revision, role, transcript)
        entry['verificationSeal'] = seal
        verification['subState'] = 'assessment'
        notice = {
            'notice': 'assessment',
            'transition': 'Completion.verification.seal->Completion.verification.assessment',
            'message': 'Verification seal recorded; reviewer assessment required.',
        }
        number = next_completion_history_number(transcript)
        seal_line = (
            f"{number}. **{role}:** sealed {format_timestamp()} \u2014 verification passed; "
            f"seal; {len(seal['touchedPaths'])} paths."
        )
        rendered = append_completion_history_line(transcript, seal_line)
        rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
        if advisory:
            print(advisory)
        next_line = f'NEXT: Run {collab_dispatch("seal verification")} for role {role} with --outcome <success|incomplete|failed>.'
        write_seal_verdict_companion(path, entry)

        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line)
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
    return 0

def record_verdict(
    path: Path,
    target: str,
    role: str,
    observed_revision: int,
    outcome: str | None,
    restore_target: str | None = None,
    restore_reason: str | None = None,
    evidence: str | None = None,
    failure_category: str | None = None,
    null_result: bool = False,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'record-verdict', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("seal verification")} is valid only in the Completion phase')
        live_revision = registry_revision(data)
        if observed_revision != live_revision:
            die(
                f'stale registry revision: observed {observed_revision}, live {live_revision}\n'
                f'RESUME: commands/collab/engine/registry.py seal-state --resume {entry["id"]} {role}'
            )
        reviewer = reviewer_role(entry)
        if reviewer is None:
            die('verification seal requires an active reviewer role')
        if reviewer_state(entry)['state'] != 'active':
            die(f'reviewer role is not a registered participant; run {collab_dispatch("join", "--role", reviewer)} first')
        if role != reviewer:
            die(f'seal must be authored by the reviewer role; current role: {role}; expected: {reviewer}')
        if verification_substate(entry) != 'verification':
            die(f'Completion.verification sub-state is not active; current sub-state: {verification_substate(entry)}')
        if outcome is None:
            die('verdict outcome is required when writing assessment fields')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        invalidate_seal_on_full_body_drift(entry, transcript)
        invalidate_seal_on_content_drift(entry)
        review_substate = verification_review_substate(entry)
        if review_substate != 'assessment':
            die(f'verification assessment is not active; current verification.subState: {review_substate}')
        seal = entry.get('verificationSeal')
        if not isinstance(seal, dict):
            die('assessment verdict requires verificationSeal')
        if outcome == 'success' and seal.get('stale'):
            reason = seal.get('staleReason') or 'unknown'
            if reason == 'content-drift':
                die_content_drift_persisted(path, data)
            die(f'success verdict requires current non-stale verificationSeal; stale: {reason}')
        if outcome == 'success':
            assert_verification_execution_ready(entry, transcript, 'success verdict')
            ensure_legacy_content_digest(entry, seal)
            invalidate_seal_on_content_drift(entry)
            if seal.get('stale'):
                reason = seal.get('staleReason') or 'unknown'
                if reason == 'content-drift':
                    die_content_drift_persisted(path, data)
                die(f'success verdict requires current non-stale verificationSeal; stale: {reason}')
            assert_chartered_deliverables_covered(entry, transcript)
        verdict = build_verdict(
            outcome,
            restore_target,
            restore_reason,
            parse_verdict_evidence(evidence),
            failure_category,
            null_result,
            entry['activePhase'],
        )
        entry['verdict'] = verdict
        notice = assessment_notice(verdict)
        if outcome == 'success':
            entry['status'] = 'closed'
            if data.get('activeCollabId') == entry['id']:
                data['activeCollabId'] = None
        number = next_completion_history_number(transcript)
        if outcome == 'success':
            verdict_detail = 'verdict success'
        else:
            verdict_detail = f"verdict {outcome}; restore {verdict['restoreTarget']}"
        rendered_timestamp = format_timestamp()
        assessment_line = (
            f"{number}. **{role}:** assessed {rendered_timestamp} \u2014 "
            f"{verdict_detail}; assessment; {len(touched_paths_for_execution(entry))} paths."
        )
        next_line = assessment_next_line(entry, verdict)
        rendered = append_completion_history_line(transcript, assessment_line)
        rendered = append_reviewer_findings_block(rendered, entry, role, verdict, rendered_timestamp, next_line)
        rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
        if entry['status'] == 'closed' and completion_summary_empty(rendered):
            rendered = append_completion_summary(rendered, default_close_summary(entry), summary_date_from_timestamp(rendered_timestamp))
        write_seal_verdict_companion(path, entry)

        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line)
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
    return 0
