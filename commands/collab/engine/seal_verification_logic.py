"""Seal/verification state and gate logic for collab records.

Owns: seal state reads, completion-cycle state, stale-seal triggers,
      content-integrity and git-state gates, participant verification state,
      verdict construction and validation, chartered-deliverables coverage,
      and verification restart.

Does not own: participant-verify rendering, assessment rendering, seal rendering,
              verdict/seal write entry points, registry persistence, phase
              lifecycle sequencing, participant roster management, non-seal
              transcript rendering, or CLI dispatch. The compatibility facade
              in seal_verification.py re-exports this module for existing engine
              leaves; registry_core.py imports it directly for its seal facade.

Naming convention
  *_state(entry, ...)   -- pure registry-entry accessor; no I/O or side effects.
  *_state(path, ...)    -- CLI-callable reader; loads registry from path.
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
    ALLOWED_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_VERDICT_OUTCOMES,
    ALLOWED_VERIFICATION_SUBSTATES,
    CONTENT_ONLY_GUARD,
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
    assert_execution_touched_paths_in_git_state,
    assert_no_execution_agent_conflation,
    assert_touched_paths_inside_handoff,
    execution_scope_advisory,
)

from commands.collab.engine.git_repo import work_repo_root

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
    render_managed_header_text,
    rendered_collapsible_block,
)

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
    elif field == 'subState':
        verification[field] = 'participant'
    elif field == 'participants':
        verification[field] = {}
    else:
        die(f'registry: unknown legacy verification field: {field}')

def verification_state(entry: dict) -> dict:
    verification = entry.setdefault('verification', {})
    if not isinstance(verification, dict):
        die('registry: verification must be an object when present')
    for field in ('rounds', 'subState', 'participants'):
        set_missing_legacy_verification_field(entry, verification, field)
    rounds = verification['rounds']
    substate = verification['subState']
    if not isinstance(rounds, int) or rounds < 0:
        die('registry: verification.rounds must be a non-negative integer when present')
    if substate is None:
        substate = 'participant'
    if substate not in ALLOWED_VERIFICATION_SUBSTATES:
        die(f'registry: verification.subState must be one of {sorted(ALLOWED_VERIFICATION_SUBSTATES)}')
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
    return reviewer_backed(entry)

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
    # Operator guidance for each blocking state lives in
    # commands/collab/reference/verification.md#operator-guidance-participant-verify-inactive
    # (anchor resolution gate-enforced by platform/tooling/audit-vocabulary.sh).
    target = entry.get('id', '<target>')
    reviewer = reviewer_role(entry) or '<reviewer>'
    ref = 'commands/collab/reference/verification.md#operator-guidance-participant-verify-inactive'
    if not participant_verification_enabled(entry):
        return (
            f'participant verification is not enabled; '
            f'reviewer ({reviewer}) seals directly via {collab_dispatch("seal verification", target)} '
            f'— see {ref}'
        )
    substate = verification_state(entry)['subState']
    if substate == 'seal':
        return (
            f'participant verification already complete for this round; '
            f'reviewer ({reviewer}) seals via {collab_dispatch("seal verification", target)} '
            f'— see {ref}'
        )
    if substate == 'assessment':
        return (
            f'assessment pending: seal is recorded, awaiting reviewer ({reviewer}) verdict; '
            f'run {collab_dispatch("seal verification", target)} --outcome <success|incomplete|failed>; '
            f'for correction use {collab_dispatch("reopen", "<action-plan|handoff>", target)} '
            f'— see {ref}'
        )
    return f'participant verification is not the active sub-state; current sub-state: {substate} — see {ref}'

def reset_participant_verification_stages(entry: dict, scope_aware: bool = False) -> None:
    """Clear per-role participant-verification progress so a round reset can restart.
    Design rationale and the rounds==0/all-stages-completed invariant:
    commands/collab/reference/verification.md#participant-verification-stage-reset"""
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

def seal_snapshot(
    entry: dict,
    observed_revision: int,
    role: str,
    transcript: str,
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
        }
        output['sealVerdict'] = build_seal_verdict_companion(entry)
    print(json.dumps(output, sort_keys=True))
    return 0
