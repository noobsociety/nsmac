"""Registry schema validation for collab records.

This module is intentionally independent from ``registry.py``. The CLI facade
passes route-owned defaults such as the roles directory into ``validate_registry``.
"""
from __future__ import annotations

import re
from pathlib import Path

from commands.collab.engine.errors import die
from commands.collab.engine.handoff_shape import validate_handoff_state
from commands.collab.engine.participants import reviewer_mode, validate_participant_role_files
from commands.collab.engine.registry_constants import (
    ALLOWED_CAP_EXITS,
    ALLOWED_COMPLETION_SUBSTATES,
    ALLOWED_EXECUTION_STATUSES,
    ALLOWED_PARTICIPANT_VERIFICATION_STAGES,
    ALLOWED_REVIEWER_MODES,
    ALLOWED_STATUSES,
    ALLOWED_TERMINALS,
    ALLOWED_VALIDATION_SCOPES,
    ALLOWED_VERIFICATION_SUBSTATES,
    CREATED_AT_REQUIRED_COLLAB_FIELDS,
    CREATED_AT_REQUIRED_REVIEWER_FIELDS,
    CREATED_AT_REQUIRED_VERIFICATION_FIELDS,
    DEFAULT_REVIEWER_OPTIONAL_PHASES,
    DEFAULT_VERIFICATION_CAP,
    DISALLOWED_VERSION_FIELD,
    PHASES,
)
from commands.collab.engine.registry_state import PROJECT_ID_RE
from commands.collab.engine.seal_verification import validate_verdict

ID_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$')
OLD_ROOT_KEYS = {'schema_version', 'active_collab_id'}
OLD_ENTRY_KEYS = {
    'active_phase',
    'created_on',
    'moderator_role',
    'transcript_path',
    'turn_order',
}

def require_created_at_fields(
    container: dict,
    fields: list[str],
    source: str,
    prefix: str,
    created_at: str | None,
) -> None:
    if created_at is None:
        return
    for field in fields:
        if field not in container:
            die(f'{source}: {prefix}.{field} is required when createdAt is present')

def validate_registry(data: dict, path: Path | None = None, roles_dir: Path | None = None) -> None:
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
            die(f'{source}: project.projectId must be a readable, collision-safe slug when present')
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
        require_created_at_fields(
            entry,
            CREATED_AT_REQUIRED_COLLAB_FIELDS,
            source,
            'collab',
            created_at,
        )

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
        validate_participant_role_files(participant_role_keys, roles_dir or Path("commands/collab/reference/roles"), source)
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

            require_created_at_fields(
                entry,
                CREATED_AT_REQUIRED_REVIEWER_FIELDS,
                source,
                'collab',
                created_at,
            )
            if 'reviewerOptionalPhases' in entry:
                optional_phases = entry['reviewerOptionalPhases']
            elif created_at is None:
                optional_phases = list(DEFAULT_REVIEWER_OPTIONAL_PHASES)
            else:
                die(f'{source}: collab.reviewerOptionalPhases is required when createdAt is present')
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
            require_created_at_fields(
                verification,
                CREATED_AT_REQUIRED_VERIFICATION_FIELDS,
                source,
                'verification',
                created_at,
            )
            if 'rounds' in verification:
                rounds = verification['rounds']
            elif created_at is None:
                rounds = 0
            else:
                die(f'{source}: verification.rounds is required when createdAt is present')
            if 'cap' in verification:
                cap = verification['cap']
            elif created_at is None:
                cap = DEFAULT_VERIFICATION_CAP
            else:
                die(f'{source}: verification.cap is required when createdAt is present')
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
