"""Seal/verification engine for collab records.

Owns: seal state reads (seal_state, seal_snapshot, verification_state,
      verification_substate), completion-cycle state (completion_state,
      initialize_completion_state — governs Completion.execution and
      Completion.verification sub-states; named for the phase, not seal integrity),
      stale-seal triggers and invalidation (invalidate_seal_on_content_drift,
      invalidate_verification_seal, invalidate_seal_on_full_body_drift),
      content-integrity and git-state gates, participant verification state and
      rendering (participant_verify_state, participant_verify_render,
      append_participant_verify_block), verdict construction and validation
      (build_verdict, validate_verdict, parse_verdict_evidence, clear_verdict),
      assessment rendering (assessment_next_line, assessment_notice),
      cap-exit dispatch (apply_cap_exit), reviewer-findings blocks
      (append_reviewer_findings_block, insert_reopen_pointer), chartered-deliverables
      coverage (assert_chartered_deliverables_covered), and seal rendering
      (render_seal, restart_verification).

Does not own: registry persistence, phase lifecycle sequencing, participant
              roster management, non-seal transcript rendering, or CLI dispatch.
              This module is imported by commands.collab.engine.registry only.

Naming convention
  *_state(entry, ...)   -- pure registry-entry accessor; no I/O or side effects.
  *_state(path, ...)    -- CLI-callable reader; loads registry from path.
  render_seal(...)      -- assembles full seal-render; may emit transcript writes
                           and registry mutations.
  invalidate_*(entry)   -- mutates entry in-place; no registry write (caller
                           holds the write lock).
  assert_*(...)         -- guard; calls die() on violation; pure read path.
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
SUMMARY_HEADING_RE = re.compile(r'^### Summary \u2014 \d{4}-\d{2}-\d{2}$')
ANCHOR_RE = re.compile(r'^<a name="(?P<anchor>[A-Za-z0-9_-]+)"></a>$')
SEAL_VERDICT_KIND = 'collab.seal-verdict'

from commands.collab.engine import transcript_readers
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.errors import die
from commands.collab.engine.registry_constants import (
    ACTIVE_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_CAP_EXITS,
    ALLOWED_COMPLETION_SUBSTATES,
    ALLOWED_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_VERDICT_OUTCOMES,
    ALLOWED_VERIFICATION_SUBSTATES,
    CONTENT_ONLY_GUARD,
    DEFAULT_VERIFICATION_CAP,
    PHASES,
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
    assert_no_execution_agent_conflation,
    assert_touched_paths_inside_handoff,
    execution_scope_advisory,
)
from commands.collab.engine.git_repo import assert_execution_touched_paths_in_git_state, work_repo_root
from commands.collab.engine.normalizers import (
    assert_one_line_nonempty,
    format_timestamp,
    normalize_restore_target,
    normalize_touched_paths,
)
from commands.collab.engine.participants import (
    assert_caller_role,
    effective_turn_order,
    has_participant,
    normalize_turn_order_for_phase,
    participant_agent_id,
    reviewer_backed,
    reviewer_role,
    reviewer_state,
)
from commands.collab.engine.phase_lifecycle import lifecycle_status_notice, print_notice_diagnostic
from commands.collab.engine.registry_io import load_registry, registry_lock, registry_revision, resolve_collab, save_registry
from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    raw_transcript_path_for_entry,
    render_managed_header_text,
    rendered_collapsible_block,
)

_commit_registry_and_transcript: Callable[[Path, dict, Path, str], None] | None = None
_next_line_for_state: Callable[[dict], str] | None = None
_print_post_action_advisories: Callable[[dict, str | None, str | None, dict | None, str], None] | None = None


def configure_registry_facade(
    *,
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None],
    next_line_for_state: Callable[[dict], str],
    print_post_action_advisories: Callable[[dict, str | None, str | None, dict | None, str], None],
) -> None:
    global _commit_registry_and_transcript, _next_line_for_state, _print_post_action_advisories
    _commit_registry_and_transcript = commit_registry_and_transcript
    _next_line_for_state = next_line_for_state
    _print_post_action_advisories = print_post_action_advisories


def commit_registry_and_transcript(
    registry_path: Path,
    data: dict,
    transcript_path: Path,
    transcript_text: str,
) -> None:
    if _commit_registry_and_transcript is None:
        die('seal verification engine is not configured: commit callback missing')
    _commit_registry_and_transcript(registry_path, data, transcript_path, transcript_text)


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


def transcript_path_for_entry(entry: dict) -> Path:
    raw_path = Path(raw_transcript_path_for_entry(entry))
    if raw_path.exists():
        return raw_path
    projection_path = Path(entry['transcriptPath'])
    if projection_path.exists():
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(projection_path.read_text())
    return raw_path


def read_transcript_for_entry(entry: dict) -> str:
    transcript_path = transcript_path_for_entry(entry)
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')
    return transcript_path.read_text()


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


def chartered_deliverables(transcript: str) -> list[str]:
    return transcript_readers.chartered_deliverables(transcript)


def is_chartered_deliverables_label(stripped: str) -> bool:
    return transcript_readers.is_chartered_deliverables_label(stripped)


def chartered_deliverable_path(deliverable: str) -> str:
    head = deliverable.split(':', 1)[0].strip()
    return head.strip('`')


def assert_chartered_deliverables_covered(entry: dict, transcript: str) -> None:
    deliverables = chartered_deliverables(transcript)
    if not deliverables:
        return
    non_path = [item for item in deliverables if ' ' in chartered_deliverable_path(item)]
    if non_path:
        print(
            'CHARTER-NOTICE: charteredDeliverables label(s) are not file paths; '
            + 'coverage gate skipped per Invariant #19: '
            + ', '.join(chartered_deliverable_path(item) for item in non_path)
        )
        return
    touched = set(touched_paths_for_execution(entry))
    missing = [
        deliverable for deliverable in deliverables
        if chartered_deliverable_path(deliverable) not in touched
    ]
    if missing:
        die(
            'CHARTERED-DELIVERABLE-MISSING: '
            + ', '.join(chartered_deliverable_path(item) for item in missing)
            + '; loop target: Completion/Conclusion for missing objective evidence'
        )


def completion_state(entry: dict) -> dict:
    completion = entry.setdefault('completion', {})
    if not isinstance(completion, dict):
        die('registry: completion must be an object when present')
    substate = completion.get('subState')
    if substate is None:
        substate = 'execution'
        completion['subState'] = substate
    if substate not in ALLOWED_COMPLETION_SUBSTATES:
        die(f'registry: completion.subState must be one of {sorted(ALLOWED_COMPLETION_SUBSTATES)}')
    return completion


def set_missing_legacy_verification_field(entry: dict, verification: dict, field: str) -> None:
    if field in verification:
        return
    if entry.get('createdAt') is not None:
        die(f'registry: verification.{field} is required when createdAt is present')
    if field == 'rounds':
        verification[field] = 0
    elif field == 'cap':
        verification[field] = DEFAULT_VERIFICATION_CAP
    elif field == 'subState':
        verification[field] = 'seal'
    elif field == 'participantVerification':
        verification[field] = False
    elif field == 'participants':
        verification[field] = {}
    else:
        die(f'registry: unknown legacy verification field: {field}')


def verification_state(entry: dict) -> dict:
    verification = entry.setdefault('verification', {})
    if not isinstance(verification, dict):
        die('registry: verification must be an object when present')
    for field in ('rounds', 'cap', 'subState', 'participantVerification', 'participants'):
        set_missing_legacy_verification_field(entry, verification, field)
    rounds = verification['rounds']
    cap = verification['cap']
    substate = verification['subState']
    if not isinstance(rounds, int) or rounds < 0:
        die('registry: verification.rounds must be a non-negative integer when present')
    if not isinstance(cap, int) or cap < 1:
        die('registry: verification.cap must be a positive integer when present')
    if substate is None:
        substate = 'seal'
    if substate not in ALLOWED_VERIFICATION_SUBSTATES:
        die(f'registry: verification.subState must be one of {sorted(ALLOWED_VERIFICATION_SUBSTATES)}')
    participant_enabled = verification['participantVerification']
    if not isinstance(participant_enabled, bool):
        die('registry: verification.participantVerification must be a boolean when present')
    participants = verification['participants']
    if not isinstance(participants, dict):
        die('registry: verification.participants must be an object when present')
    for role, participant_state in participants.items():
        if not isinstance(role, str) or not role.strip():
            die('registry: verification.participants keys must be non-empty role strings')
        if not isinstance(participant_state, dict):
            die('registry: verification.participants[role] must be an object')
        stage = participant_state.get('stage')
        if stage is not None and stage not in ALLOWED_PARTICIPANT_VERIFICATION_STAGES:
            die(
                'registry: verification.participants[role].stage must be one of '
                f'{sorted(ALLOWED_PARTICIPANT_VERIFICATION_STAGES)}'
            )
        attempts = participant_state.get('attempts')
        if attempts is not None and (not isinstance(attempts, int) or attempts < 0):
            die('registry: verification.participants[role].attempts must be a non-negative integer when present')
        started_at = participant_state.get('startedAt')
        if started_at is not None and (not isinstance(started_at, str) or not started_at.strip()):
            die('registry: verification.participants[role].startedAt must be a non-empty string when present')
        signature = participant_state.get('writeScopeSignature')
        if signature is not None and (not isinstance(signature, str) or not signature.strip()):
            die('registry: verification.participants[role].writeScopeSignature must be a non-empty string when present')
        execution_signature = participant_state.get('executionSignature')
        if execution_signature is not None and (not isinstance(execution_signature, str) or not execution_signature.strip()):
            die('registry: verification.participants[role].executionSignature must be a non-empty string when present')
    return verification


def participant_verification_enabled(entry: dict) -> bool:
    verification = entry.get('verification')
    if not isinstance(verification, dict):
        return False
    if 'participantVerification' not in verification:
        return False
    return verification['participantVerification'] is True


def participant_verification_roles(entry: dict) -> list[str]:
    execution = entry.get('execution', {})
    roles: list[str] = []
    for role in effective_turn_order(entry):
        if role in {entry.get('moderatorRole'), reviewer_role(entry)}:
            continue
        if execution.get(role, {}).get('status') == 'completed':
            roles.append(role)
    return roles


def execution_roles(entry: dict) -> list[str]:
    return [
        role
        for role in effective_turn_order(entry)
        if role not in {entry.get('moderatorRole'), reviewer_role(entry)}
    ]


def pending_execution_roles(entry: dict) -> list[str]:
    execution = entry.get('execution', {})
    return [
        role
        for role in execution_roles(entry)
        if execution.get(role, {}).get('status') != 'completed'
    ]


def verification_execution_blocker(entry: dict, transcript: str) -> str | None:
    pending = pending_execution_roles(entry)
    unchecked = {
        role: count
        for role, count in transcript_readers.unchecked_assigned_items_by_role(transcript).items()
        if count
    }
    if not pending and not unchecked:
        return None

    details: list[str] = []
    if pending:
        details.append('pending execution role(s): ' + ', '.join(pending))
    if unchecked:
        details.append(
            'unchecked assigned Action Plan item(s): '
            + ', '.join(f'{role}={unchecked[role]}' for role in sorted(unchecked))
        )
    next_role = pending[0] if pending else sorted(unchecked)[0]
    return '; '.join(details) + f'; run {collab_dispatch("run plan")} for role {next_role}'


def assert_verification_execution_ready(entry: dict, transcript: str, action: str) -> None:
    blocker = verification_execution_blocker(entry, transcript)
    if blocker:
        die(f'{action} blocked: {blocker}')


def participant_verification_role_state(entry: dict, role: str) -> dict:
    verification = verification_state(entry)
    participants = verification.setdefault('participants', {})
    if not isinstance(participants, dict):
        die('registry: verification.participants must be an object when present')
    state = participants.setdefault(role, {})
    if not isinstance(state, dict):
        die('registry: verification.participants[role] must be an object')
    signature = participant_write_scope_signature(entry, role)
    # A completed verification certifies a specific executed deliverable. Invalidate
    # it when the role's declared scope changes, OR -- for a completed stage that
    # recorded its execution signature -- when the executed content it certified
    # changes (a re-execution, or a provenance repair that repointed the commit).
    # Every reader resolves role state through this helper, so the check closes the
    # stale-preservation hole regardless of which entry point mutated execution.
    execution_changed = (
        state.get('stage') == 'completed'
        and state.get('executionSignature') is not None
        and state.get('executionSignature') != participant_execution_signature(entry, role)
    )
    if state.get('writeScopeSignature') != signature or execution_changed:
        state.clear()
        state['writeScopeSignature'] = signature
        state['attempts'] = 0
    state.setdefault('attempts', 0)
    return state


def all_participant_verification_completed(entry: dict) -> bool:
    if not participant_verification_enabled(entry):
        return True
    roles = participant_verification_roles(entry)
    if not roles:
        return False
    return all(participant_verification_role_state(entry, role).get('stage') == 'completed' for role in roles)


def participant_verification_incomplete(entry: dict) -> bool:
    return participant_verification_enabled(entry) and all_execution_completed(entry) and not all_participant_verification_completed(entry)


def sync_participant_verification_review_substate(entry: dict) -> None:
    if not reviewer_backed(entry):
        return
    if verification_state(entry)['subState'] == 'assessment':
        return
    if participant_verification_incomplete(entry):
        verification_state(entry)['subState'] = 'participant'
    elif participant_verification_enabled(entry):
        verification_state(entry)['subState'] = 'seal'


def participant_verification_inactive_message(entry: dict) -> str:
    """Explain why participant verification cannot run and what to do next,
    instead of surfacing only the raw sub-state. The blocking states are:
    participant verification disabled, the round already complete (sub-state
    'seal'), or a seal recorded and awaiting the reviewer verdict ('assessment').
    The bare 'current value' form gave no exit and was a recurring dead-end when
    a contributor retried participant verify against a sealed/assessing round."""
    target = entry.get('id', '<target>')
    reviewer = reviewer_role(entry) or '<reviewer>'
    if not participant_verification_enabled(entry):
        return (
            'participant verification is not enabled for this collab; '
            f'the reviewer ({reviewer}) seals directly via {collab_dispatch("seal verification", target)}'
        )
    substate = verification_state(entry)['subState']
    if substate == 'seal':
        return (
            'participant verification for this round is already complete; the reviewer '
            f'({reviewer}) records the seal via {collab_dispatch("seal verification", target)}'
        )
    if substate == 'assessment':
        return (
            'participant verification cannot run while the cycle is in assessment: a '
            f'verification seal is recorded and awaiting the reviewer ({reviewer}) verdict. '
            f'Reviewer: record it via {collab_dispatch("seal verification", target)} '
            '--outcome <success|incomplete|failed>. To redo verification after a correction, '
            'record a non-success outcome; that routes the moderator to '
            f'{collab_dispatch("reopen", "<action-plan|handoff>", target)} to re-execute and re-verify'
        )
    return f'participant verification is not the active sub-state; current sub-state: {substate}'


def reset_participant_verification_stages(entry: dict, scope_aware: bool = False) -> None:
    """Clear per-role participant-verification progress so a round reset can
    restart the cycle. Without this, sync_participant_verification_review_substate
    sees stale "completed" stages and bounces subState back to "seal", leaving a
    record that is neither sealable (rounds 0) nor re-verifiable (stages done).

    With scope_aware=True (a reopen that may revise only some roles' scope) a role
    whose declared write scope is unchanged keeps its completed verification, so
    only the roles the reviewer actually re-scoped have to re-run -- a reopen no
    longer forces every participant through a fresh audit round. A verification
    round is earned only when a participant completes a fresh run (see
    record_verification_round_for_execution), and rounds=0 + all-stages-completed
    is intentionally not sealable; so if scope-aware preservation would retain
    every completed role, no participant would re-run and the round could never be
    re-earned. Guard that by falling back to a full reset whenever no role would
    otherwise be cleared, guaranteeing at least one re-run earns the new round."""
    if not participant_verification_enabled(entry):
        return
    participants = verification_state(entry).get('participants')
    if not isinstance(participants, dict):
        return
    roles = participant_verification_roles(entry)
    if scope_aware:
        to_clear = [
            role for role in roles
            if not (
                isinstance(participants.get(role), dict)
                and participants[role].get('stage') == 'completed'
                and participants[role].get('writeScopeSignature')
                == participant_write_scope_signature(entry, role)
                and participants[role].get('executionSignature')
                == participant_execution_signature(entry, role)
            )
        ]
        if to_clear:
            for role in to_clear:
                state = participants.get(role)
                if isinstance(state, dict):
                    state.pop('stage', None)
                    state['attempts'] = 0
            return
        # Every completed role is unchanged: fall through to a full reset so a
        # re-run can earn the round (a preserved-only reset would deadlock).
    for role in roles:
        state = participants.get(role)
        if isinstance(state, dict):
            state.pop('stage', None)
            state['attempts'] = 0


def initialize_completion_state(
    entry: dict,
    substate: str = 'execution',
    reset_rounds: bool = False,
    scope_aware: bool = False,
    reset_stages: bool = True,
) -> None:
    if not reviewer_backed(entry):
        return
    if substate not in ALLOWED_COMPLETION_SUBSTATES:
        die(f'completion subState must be one of {sorted(ALLOWED_COMPLETION_SUBSTATES)}')
    completion = completion_state(entry)
    completion['subState'] = substate
    verification = verification_state(entry)
    if reset_rounds:
        verification['rounds'] = 0
        verification.pop('pairedExecutionSignature', None)
        # reset_stages=False preserves completed per-role verification across a
        # reopen so the eventual re-entry into Completion can decide, scope-aware,
        # which roles must re-verify. scope_aware preserves unchanged-scope roles.
        if reset_stages:
            reset_participant_verification_stages(entry, scope_aware=scope_aware)
        verification['subState'] = 'participant' if participant_verification_enabled(entry) else 'seal'
    elif substate == 'verification' and verification['subState'] not in ALLOWED_VERIFICATION_SUBSTATES:
        verification['subState'] = 'seal'
    if substate == 'verification':
        sync_participant_verification_review_substate(entry)


def verification_review_substate(entry: dict) -> str:
    if not reviewer_backed(entry):
        return 'none'
    return verification_state(entry).get('subState', 'seal')


def set_verification_review_substate(entry: dict, substate: str) -> None:
    if substate not in ALLOWED_VERIFICATION_SUBSTATES:
        die(f'verification.subState must be one of {sorted(ALLOWED_VERIFICATION_SUBSTATES)}')
    verification_state(entry)['subState'] = substate


def parse_verdict_evidence(raw: str | None) -> dict | None:
    if raw is None:
        return None
    try:
        evidence = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f'verdict evidence must be a JSON object: {exc}')
    validate_verdict_evidence(evidence, 'verdict evidence')
    return evidence


def validate_verdict_evidence(evidence: object, source: str) -> None:
    if not isinstance(evidence, dict):
        die(f'{source} must be an object')
    allowed_keys = {'transcriptIds', 'revision', 'registryRevision', 'committedPaths', 'executionEntryIds'}
    unknown = sorted(set(evidence) - allowed_keys)
    if unknown:
        die(f'{source} contains non-anchor fields: {unknown}')
    if 'revision' in evidence and 'registryRevision' in evidence:
        die(f'{source} must not contain both revision and legacy registryRevision')
    if 'revision' in evidence and (not isinstance(evidence['revision'], int) or evidence['revision'] < 0):
        die(f'{source}.revision must be a non-negative integer')
    if 'registryRevision' in evidence and (
        not isinstance(evidence['registryRevision'], int) or evidence['registryRevision'] < 0
    ):
        die(f'{source}.registryRevision must be a non-negative integer')
    for key in ('transcriptIds', 'committedPaths', 'executionEntryIds'):
        if key not in evidence:
            continue
        values = evidence[key]
        if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
            die(f'{source}.{key} must be a list of non-empty strings')


def validate_verdict(verdict: object, source: str, current_phase: str = 'Completion') -> None:
    if not isinstance(verdict, dict):
        die(f'{source}: verdict must be an object when present')
    outcome = verdict.get('outcome')
    if outcome not in ALLOWED_VERDICT_OUTCOMES:
        die(f'{source}: verdict.outcome must be one of {sorted(ALLOWED_VERDICT_OUTCOMES)}')
    restore_target = verdict.get('restoreTarget')
    restore_reason = verdict.get('restoreReason')
    if outcome == 'success':
        if restore_target is not None:
            die(f'{source}: verdict.restoreTarget must be absent when outcome is success')
        if restore_reason is not None:
            die(f'{source}: verdict.restoreReason must be absent when outcome is success')
    else:
        if not isinstance(restore_target, str) or not restore_target.strip():
            die(f'{source}: verdict.restoreTarget is required when outcome is not success')
        normalize_restore_target(restore_target, current_phase)
        if not isinstance(restore_reason, str) or not restore_reason.strip():
            die(f'{source}: verdict.restoreReason is required when outcome is not success')
        assert_one_line_nonempty(restore_reason, 'restoreReason')
    evidence = verdict.get('evidence')
    if evidence is not None:
        validate_verdict_evidence(evidence, f'{source}: verdict.evidence')
    failure_category = verdict.get('failureCategory')
    if failure_category is not None:
        if not isinstance(failure_category, str):
            die(f'{source}: verdict.failureCategory must be a string when present')
        assert_one_line_nonempty(failure_category, 'failureCategory')
    null_result = verdict.get('nullResult')
    if null_result is not None and not isinstance(null_result, bool):
        die(f'{source}: verdict.nullResult must be a boolean when present')
    if null_result is True and not isinstance(restore_reason, str):
        die(f'{source}: verdict.nullResult requires restoreReason as the one-line justification')


def build_verdict(
    outcome: str,
    restore_target: str | None,
    restore_reason: str | None,
    evidence: dict | None,
    failure_category: str | None,
    null_result: bool,
    current_phase: str,
) -> dict:
    if outcome not in ALLOWED_VERDICT_OUTCOMES:
        die('verdict outcome must be one of: success, incomplete, failed')
    verdict: dict = {'outcome': outcome}
    target = normalize_restore_target(restore_target, current_phase)
    reason = assert_one_line_nonempty(restore_reason, 'restoreReason')
    category = assert_one_line_nonempty(failure_category, 'failureCategory')
    if target is not None:
        verdict['restoreTarget'] = target
    if reason is not None:
        verdict['restoreReason'] = reason
    if evidence is not None:
        verdict['evidence'] = evidence
    if category is not None:
        verdict['failureCategory'] = category
    if null_result:
        verdict['nullResult'] = True
    validate_verdict(verdict, 'registry', current_phase)
    return verdict


def successful_verdict(entry: dict) -> bool:
    verdict = entry.get('verdict')
    return isinstance(verdict, dict) and verdict.get('outcome') == 'success'


def clear_verdict(entry: dict) -> None:
    entry.pop('verdict', None)


def record_verification_round_for_execution(entry: dict, verification: dict) -> None:
    signature = execution_signature(entry)
    if verification.get('pairedExecutionSignature') != signature:
        verification['rounds'] += 1
        verification['pairedExecutionSignature'] = signature


def content_digest_for_execution(entry: dict, ref: str = 'HEAD') -> dict:
    return content_digest_for_touched_paths(work_repo_root(entry), ref, touched_paths_for_execution(entry))


def ensure_legacy_content_digest(entry: dict, seal: dict) -> None:
    if isinstance(seal.get('contentDigest'), str) and isinstance(seal.get('pathDigests'), dict):
        return
    digest = content_digest_for_execution(entry)
    seal['contentDigest'] = digest['contentDigest']
    seal['pathDigests'] = digest['pathDigests']
    seal['legacyContentDigestRecomputedAt'] = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    seal['legacyContentDigestNote'] = (
        'legacy verificationSeal lacked contentDigest; recomputed on next touch '
        f'for touchedPaths={json.dumps(touched_paths_for_execution(entry), separators=(",", ":"))} '
        f'contentDigest={digest["contentDigest"]}'
    )


def invalidate_seal_on_content_drift(entry: dict) -> None:
    seal = entry.get('verificationSeal')
    if not isinstance(seal, dict) or seal.get('stale'):
        return
    if not isinstance(seal.get('contentDigest'), str) or not isinstance(seal.get('pathDigests'), dict):
        ensure_legacy_content_digest(entry, seal)
    digest = content_digest_for_execution(entry)
    if seal.get('contentDigest') != digest['contentDigest'] or seal.get('pathDigests') != digest['pathDigests']:
        invalidate_verification_seal(entry, 'content-drift')


def die_content_drift_persisted(path: Path, data: dict) -> None:
    save_registry(path, data)
    die('SEAL-CONTENT-DRIFT: post-seal content change detected in a touched path; re-issue the seal with current branch content')


def invalidate_verification_seal(entry: dict, reason: str) -> None:
    seal = entry.get('verificationSeal')
    if isinstance(seal, dict):
        seal['stale'] = True
        seal['staleReason'] = reason
        if reviewer_backed(entry):
            # 'assessment' presumes a completed paired round awaiting a verdict, so
            # only retain it when that round is still intact. When the round has been
            # reset -- e.g. a reopen clears rounds and participant stages before
            # invalidating the seal -- forcing 'assessment' strands the cycle: the
            # seal block is immutable in assessment, a success verdict is blocked by
            # the stale seal, and participant verify is gated to the 'participant'
            # sub-state, so nothing can advance. Fall back to the live participant or
            # seal entry point so the cycle always has a forward path.
            verification = verification_state(entry)
            rounds = verification['rounds']
            if rounds > 0 and not participant_verification_incomplete(entry):
                set_verification_review_substate(entry, 'assessment')
            else:
                set_verification_review_substate(
                    entry, 'participant' if participant_verification_enabled(entry) else 'seal'
                )
        clear_verdict(entry)


def invalidate_seal_on_full_body_drift(entry: dict, transcript: str) -> None:
    seal = entry.get('verificationSeal')
    if not isinstance(seal, dict) or seal.get('stale'):
        return
    sealed_signature = seal.get('fullBodySignature')
    if not isinstance(sealed_signature, str):
        return
    if full_body_signature_for_transcript(transcript) != sealed_signature:
        invalidate_verification_seal(entry, 'full body content changed')


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


def seal_snapshot(
    entry: dict,
    observed_revision: int,
    role: str,
    transcript: str,
    cap_exit: str | None = None,
    follow_up: dict | None = None,
) -> dict:
    digest = content_digest_for_execution(entry)
    seal = {
        'observedRevision': observed_revision,
        'executionEntries': execution_coverage_entries(entry),
        'validationScopes': validation_scopes_for_execution(entry),
        'touchedPaths': touched_paths_for_execution(entry),
        'contentDigest': digest['contentDigest'],
        'pathDigests': digest['pathDigests'],
        'sealedAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'sealedBy': role,
        'executionSignature': execution_signature(entry),
        'fullBodySignature': full_body_signature_for_transcript(transcript),
        'stale': False,
    }
    if cap_exit:
        seal['capExit'] = cap_exit
    if follow_up is not None:
        seal['followUp'] = follow_up
    return seal


def _digest_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def seal_verdict_inputs(entry: dict) -> dict:
    seal = entry.get('verificationSeal')
    if not isinstance(seal, dict):
        die('seal-verdict companion requires verificationSeal')
    return {
        'observedRevision': seal.get('observedRevision'),
        'executionDigest': seal.get('executionSignature'),
        'contentDigest': seal.get('contentDigest'),
        'pathDigests': seal.get('pathDigests'),
    }


def seal_verdict_input_digest(entry: dict) -> str:
    return _digest_json(seal_verdict_inputs(entry))


def build_seal_verdict_companion(entry: dict) -> dict:
    seal = entry.get('verificationSeal')
    if not isinstance(seal, dict):
        die('seal-verdict companion requires verificationSeal')
    verdict = entry.get('verdict') if isinstance(entry.get('verdict'), dict) else None
    inputs = seal_verdict_inputs(entry)
    return {
        'kind': SEAL_VERDICT_KIND,
        'target': entry.get('id'),
        'authoritative': False,
        'authority': 'verificationSeal',
        'closeGate': 'verificationSeal',
        'observedRevision': inputs['observedRevision'],
        'executionDigest': inputs['executionDigest'],
        'contentDigest': inputs['contentDigest'],
        'pathDigests': inputs['pathDigests'],
        'inputDigest': seal_verdict_input_digest(entry),
        'verificationSealDigest': _digest_json(seal),
        'verdict': verdict,
        'stale': bool(seal.get('stale')),
        'staleReason': seal.get('staleReason'),
    }


def seal_verdict_companion_status(entry: dict, companion: object | None) -> dict:
    if companion is None:
        return {'current': False, 'reason': 'missing seal-verdict companion'}
    if not isinstance(companion, dict):
        return {'current': False, 'reason': 'invalid seal-verdict companion'}
    if companion.get('authoritative') is not False or companion.get('closeGate') != 'verificationSeal':
        return {'current': False, 'reason': 'seal-verdict companion authority drift'}
    expected = build_seal_verdict_companion(entry)
    for key in ('observedRevision', 'executionDigest', 'contentDigest', 'pathDigests', 'inputDigest', 'verdict'):
        if companion.get(key) != expected.get(key):
            return {'current': False, 'reason': f'seal-verdict companion {key} mismatch'}
    return {'current': True, 'reason': None}


def seal_verdict_companion_path(registry_path: Path, entry: dict) -> Path:
    transcript_path = Path(entry['transcriptPath'])
    companion_name = f'{transcript_path.stem}-seal-verdict.json'
    return registry_path.parent / transcript_path.with_name(companion_name)


def write_seal_verdict_companion(registry_path: Path, entry: dict) -> Path | None:
    if not isinstance(entry.get('verificationSeal'), dict):
        return None
    path = seal_verdict_companion_path(registry_path, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_seal_verdict_companion(entry), indent=2, sort_keys=True) + '\n')
    return path


def verification_substate(entry: dict) -> str:
    if not reviewer_backed(entry):
        return 'none'
    completion = entry.get('completion')
    if isinstance(completion, dict) and completion.get('subState') in ALLOWED_COMPLETION_SUBSTATES:
        return completion['subState']
    return 'execution'


def first_pending_participant_verification_role(entry: dict) -> str | None:
    if not participant_verification_enabled(entry) or not all_execution_completed(entry):
        return None
    for role in participant_verification_roles(entry):
        if participant_verification_role_state(entry, role).get('stage') != 'completed':
            return role
    return None


def seal_state(path: Path, target: str, role: str | None = None, resume: bool = False) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("seal verification")} is valid only in the Completion phase')
        if entry.get('terminal') == 'issue':
            die(f'seal verification is not used for issue-terminal collabs; close with {collab_dispatch("export-issues")}')
        if reviewer_backed(entry):
            initialize_completion_state(entry, verification_substate(entry))
        if reviewer_backed(entry) and all_execution_completed(entry):
            completion = completion_state(entry)
            if completion['subState'] == 'execution':
                completion['subState'] = 'verification'
                verification = verification_state(entry)
                verification['rounds'] = 0
                verification['subState'] = 'participant' if participant_verification_enabled(entry) else 'seal'
            verification = verification_state(entry)
            sync_participant_verification_review_substate(entry)
        if reviewer_backed(entry):
            verification_state(entry)
        if isinstance(entry.get('verificationSeal'), dict):
            invalidate_seal_on_full_body_drift(entry, read_transcript_for_entry(entry))
        save_registry(path, data)
        data = load_registry(path)
        entry = resolve_collab(data, target)

    seal = entry.get('verificationSeal')
    transcript = read_transcript_for_entry(entry)
    execution_blocker = verification_execution_blocker(entry, transcript) if reviewer_backed(entry) else None
    result = {
        'target': entry['id'],
        'activePhase': entry['activePhase'],
        'registryRevision': registry_revision(data),
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'verificationSubState': verification_substate(entry),
        'completionSubState': verification_substate(entry),
        'verificationReviewSubState': verification_review_substate(entry),
        'verificationRounds': verification_state(entry)['rounds'] if reviewer_backed(entry) else 0,
        'verificationCap': verification_state(entry)['cap'] if reviewer_backed(entry) else DEFAULT_VERIFICATION_CAP,
        'executionEntries': active_execution_entries(entry),
        'validationScopes': validation_scopes_for_execution(entry),
        'touchedPaths': touched_paths_for_execution(entry),
        'participantVerification': participant_verification_enabled(entry),
        'participantVerificationRoles': participant_verification_roles(entry),
        'participantVerificationParticipants': verification_state(entry)['participants'] if reviewer_backed(entry) else {},
        'nextParticipantVerificationRole': first_pending_participant_verification_role(entry),
        'sealStale': bool(isinstance(seal, dict) and seal.get('stale')),
        'verdict': entry.get('verdict') if isinstance(entry.get('verdict'), dict) else None,
        'freshRegistryRead': True,
    }
    if execution_blocker:
        result['executionBlocker'] = execution_blocker
    if role:
        result['roleAgentId'] = participant_agent_id(entry, role)
        result['readyToSeal'] = (
            role == reviewer_role(entry)
            and result['verificationSubState'] == 'verification'
            and result['verificationReviewSubState'] == 'seal'
            and result['verificationRounds'] > 0
            and execution_blocker is None
        )
        result['readyToAssess'] = (
            role == reviewer_role(entry)
            and result['verificationSubState'] == 'verification'
            and result['verificationReviewSubState'] == 'assessment'
        )
    if resume:
        result['resume'] = f'commands/collab/engine/registry.py seal-state --resume {entry["id"]} {role or reviewer_role(entry) or "<role>"}'
    print(json.dumps(result, sort_keys=True))
    return 0


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


def participant_verify_state(path: Path, target: str, role: str, resume: bool = False) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("participant verify")} requires activePhase = Completion')
        if reviewer_backed(entry) and all_execution_completed(entry):
            completion = completion_state(entry)
            if completion['subState'] == 'execution':
                completion['subState'] = 'verification'
                verification = verification_state(entry)
                verification['rounds'] = 0
                verification['subState'] = 'participant' if participant_verification_enabled(entry) else 'seal'
            if completion['subState'] == 'verification':
                sync_participant_verification_review_substate(entry)
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript = read_transcript_for_entry(entry)
        assert_verification_execution_ready(entry, transcript, 'participant verification')
        verification = verification_state(entry)
        assigned_roles = participant_verification_roles(entry)
        if not participant_verification_enabled(entry) or verification['subState'] != 'participant':
            die(participant_verification_inactive_message(entry))
        if role not in assigned_roles:
            die(f'role is not assigned to participant verification: {role}')
        pending_role = first_pending_participant_verification_role(entry)
        if pending_role != role:
            die(f'participant verification turn lock is held by role {pending_role or "none"}')
        role_state = participant_verification_role_state(entry, role)
        if role_state.get('stage') == 'completed':
            save_registry(path, data)
            data = load_registry(path)
            entry = resolve_collab(data, target)
            verification = verification_state(entry)
            role_state = participant_verification_role_state(entry, role)
        else:
            cap = verification['cap']
            attempts = role_state.get('attempts', 0)
            if attempts >= cap:
                die(f'participant verification attempt cap reached for {role}: {attempts}/{cap}')
            if role_state.get('stage') not in ACTIVE_PARTICIPANT_VERIFICATION_STAGES:
                role_state['stage'] = 'audit'
                role_state['startedAt'] = dt.datetime.now().astimezone().isoformat(timespec='seconds')
        save_registry(path, data)
        data = load_registry(path)
        entry = resolve_collab(data, target)
        verification = verification_state(entry)
        role_state = participant_verification_role_state(entry, role)
    result = {
        'target': entry['id'],
        'activePhase': entry['activePhase'],
        'registryRevision': registry_revision(data),
        'completionSubState': verification_substate(entry),
        'verificationReviewSubState': verification['subState'],
        'assignedRoles': assigned_roles,
        'nextRole': first_pending_participant_verification_role(entry),
        'role': role,
        'roleAgentId': participant_agent_id(entry, role),
        'roleState': role_state,
        'readyToVerify': first_pending_participant_verification_role(entry) == role,
        'freshRegistryRead': True,
    }
    if resume:
        result['resume'] = f'commands/collab/engine/registry.py participant-verify-state --resume {entry["id"]} {role}'
    print(json.dumps(result, sort_keys=True))
    return 0


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
        cap = verification['cap']
        attempts = role_state.get('attempts', 0)
        if attempts >= cap:
            die(f'participant verification attempt cap reached for {role}: {attempts}/{cap}')
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


def apply_cap_exit(entry: dict, data: dict, cap_exit: str | None) -> dict | None:
    if cap_exit is None:
        set_verification_review_substate(entry, 'assessment')
        return {
            'notice': 'assessment',
            'transition': 'Completion.verification.seal->Completion.verification.assessment',
            'message': 'Verification seal recorded; reviewer assessment required.',
        }
    if cap_exit == 'archive':
        # Route prose reserves archive for unresolved findings. Participant
        # verification findings are transcript prose, not structured registry
        # fields, so clean-vs-remediated distinction remains caller-asserted.
        entry['status'] = 'archived'
        entry['archived'] = True
        set_verification_review_substate(entry, 'assessment')
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        return lifecycle_status_notice('archived')
    if cap_exit == 'reopen-action-plan':
        entry['activePhase'] = 'Action Plan'
        normalize_turn_order_for_phase(entry, 'Action Plan')
        initialize_completion_state(entry, 'execution', reset_rounds=True, reset_stages=False)
        set_verification_review_substate(entry, 'assessment')
        return {'notice': 'reopen', 'transition': 'Completion.verification->Action Plan', 'message': 'Verification cap exit reopened Action Plan.'}
    if cap_exit == 'reopen-handoff':
        entry['activePhase'] = 'Handoff'
        normalize_turn_order_for_phase(entry, 'Handoff')
        initialize_completion_state(entry, 'execution', reset_rounds=True, reset_stages=False)
        set_verification_review_substate(entry, 'assessment')
        return {'notice': 'reopen', 'transition': 'Completion.verification->Handoff', 'message': 'Verification cap exit reopened Handoff.'}
    if cap_exit == 'follow-up-collab':
        set_verification_review_substate(entry, 'assessment')
        return {
            'notice': 'follow-up-collab',
            'transition': 'Completion.verification.seal->Completion.verification.assessment',
            'message': 'Verification cap exit requires a follow-up collab with restoreReason, evidence, and failureCategory.',
        }
    die(f'invalid cap-exit value {cap_exit}; must be one of: reopen-action-plan, reopen-handoff, follow-up-collab, archive')


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


def verdict_args_present(
    outcome: str | None,
    restore_target: str | None,
    restore_reason: str | None,
    evidence: str | None,
    failure_category: str | None,
    null_result: bool,
) -> bool:
    return any([
        outcome is not None,
        restore_target is not None,
        restore_reason is not None,
        evidence is not None,
        failure_category is not None,
        null_result,
    ])


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
    if cap_exit is not None and cap_exit not in ALLOWED_CAP_EXITS:
        die(f'invalid cap-exit value {cap_exit}; must be one of: reopen-action-plan, reopen-handoff, follow-up-collab, archive')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'seal-render', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("seal verification")} is valid only in the Completion phase')
        if entry.get('terminal') == 'issue':
            die(f'seal verification is not used for issue-terminal collabs; close with {collab_dispatch("export-issues")}')
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
        has_verdict_args = verdict_args_present(
            outcome,
            restore_target,
            restore_reason,
            evidence,
            failure_category,
            null_result,
        )
        follow_up_args_present = any([restore_reason is not None, evidence is not None, failure_category is not None])
        follow_up: dict | None = None
        if cap_exit == 'follow-up-collab':
            if outcome is not None or restore_target is not None or null_result:
                die('follow-up-collab cap-exit cannot include assessment outcome fields')
            if not restore_reason or evidence is None or not failure_category:
                die('follow-up-collab cap-exit requires --restore-reason, --evidence, and --failure-category')
            follow_up = {
                'restoreReason': restore_reason,
                'evidence': parse_verdict_evidence(evidence),
                'failureCategory': failure_category,
            }
            has_verdict_args = False
        elif cap_exit is not None and follow_up_args_present:
            die('cap-exit metadata is only valid with --cap-exit follow-up-collab')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        invalidate_seal_on_full_body_drift(entry, transcript)
        invalidate_seal_on_content_drift(entry)
        review_substate = verification_review_substate(entry)

        if has_verdict_args:
            if cap_exit is not None:
                die('verification assessment cannot mutate seal cap-exit; omit --cap-exit when writing a verdict')
            if review_substate != 'assessment':
                die(f'verification assessment is not active; current verification.subState: {review_substate}')
            if outcome is None:
                die('verdict outcome is required when writing assessment fields')
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
        else:
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
            cap = verification['cap']
            if rounds == 0:
                die('zero verification rounds; at least one reviewer-executor paired event is required before sealing')
            if cap_exit is None and rounds >= cap:
                die(
                    'round cap reached; reissue with --cap-exit reopen-action-plan, '
                    '--cap-exit reopen-handoff, --cap-exit follow-up-collab, or --cap-exit archive'
                )
            clear_verdict(entry)
            seal = seal_snapshot(entry, observed_revision, role, transcript, cap_exit, follow_up)
            entry['verificationSeal'] = seal
            notice = apply_cap_exit(entry, data, cap_exit)
            number = next_completion_history_number(transcript)
            scope_label = 'cap-exit' if cap_exit else 'seal'
            seal_line = (
                f"{number}. **{role}:** sealed {format_timestamp()} \u2014 verification passed; "
                f"{scope_label}; {len(seal['touchedPaths'])} paths."
            )
            rendered = append_completion_history_line(transcript, seal_line)
            rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
            if advisory:
                print(advisory)
            next_line = (
                f'NEXT: Run {collab_dispatch("seal verification")} for role {role} with --outcome <success|incomplete|failed>.'
                if cap_exit is None
                else (
                    'NEXT: Open a follow-up collab '
                    f'{json.dumps(follow_up, sort_keys=True, separators=(",", ":"))}.'
                    if cap_exit == 'follow-up-collab'
                    else next_line_for_state(entry)
                )
            )
            write_seal_verdict_companion(path, entry)

        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line)
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def restart_verification(
    path: Path,
    target: str,
    caller_role: str | None = None,
) -> int:
    """Reviewer recovery primitive: restart Completion.verification after the
    execution record was corrected (e.g. via rewrite execution). Resets
    rounds to 0, clears participant-verification stages, and returns the cycle to
    the 'participant' sub-state WITHOUT re-recording execution, so the corrected
    commit reference is preserved. Participants then re-run participant
    verify to record a fresh paired round before the reviewer seals."""
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'restart-verification', reviewer_role(entry))
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if not reviewer_backed(entry):
            die('restart-verification requires a reviewer-backed collab')
        if entry['activePhase'] != 'Completion':
            die('restart-verification requires activePhase = Completion')
        if not all_execution_completed(entry):
            die('restart-verification requires all execution entries completed')
        transcript = read_transcript_for_entry(entry)
        assert_verification_execution_ready(entry, transcript, 'restart-verification')
        initialize_completion_state(entry, 'verification', reset_rounds=True)
        save_registry(path, data)
    verification = verification_state(entry)
    print(
        'verification cycle restarted: rounds=0, participant stages cleared, '
        f'subState={verification.get("subState")}'
    )
    next_role = first_pending_participant_verification_role(entry)
    if next_role:
        print(f'NEXT: Run {collab_dispatch("participant verify")} for role {next_role}.')
    else:
        print(f'NEXT: Run {collab_dispatch("seal verification")} for role {reviewer_role(entry)}.')
    return 0


def show_verdict(path: Path, target: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    verdict = entry.get('verdict')
    if not isinstance(verdict, dict):
        die('verdict unavailable for target')
    seal = entry.get('verificationSeal')
    output = {
        'target': entry['id'],
        'status': entry['status'],
        'activePhase': entry['activePhase'],
        'completionSubState': verification_substate(entry),
        'verificationReviewSubState': verification_review_substate(entry),
        'verdict': verdict,
    }
    if isinstance(seal, dict):
        output['verificationSeal'] = {
            'observedRevision': seal.get('observedRevision'),
            'sealedAt': seal.get('sealedAt'),
            'sealedBy': seal.get('sealedBy'),
            'stale': seal.get('stale'),
            'staleReason': seal.get('staleReason'),
            'capExit': seal.get('capExit'),
        }
        output['sealVerdict'] = build_seal_verdict_companion(entry)
    print(json.dumps(output, sort_keys=True))
    return 0
