"""Participant roster, reviewer wiring, and turn-order helpers; does not own phase mutations."""
# Tests: join validation (duplicate role, agent-id conflict, caller-declined), add/remove
#        participant round-trips, turn-order normalization per phase, reviewer wiring
#        (active/pending/optional), role-file presence checks.
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMMAND_SYSTEM_DIR = ROOT / 'platform' / 'tooling'
if str(COMMAND_SYSTEM_DIR) not in sys.path:
    sys.path.insert(0, str(COMMAND_SYSTEM_DIR))

from roles import load_role
from commands.collab.engine.errors import die
from commands.collab.engine.registry_constants import (
    CALLER_DECLINED_AGENT_ID,
    CONVERGENT_REVIEWER_PHASES,
    DEFAULT_REVIEWER_MODE,
    DEFAULT_REVIEWER_OPTIONAL_PHASES,
    MOD_EXCLUDED_PHASES,
    MODERATOR_ONLY_ACTIONS,
    PHASES,
)

def validate_participant_role_files(
    role_keys: list[str],
    roles_dir: Path,
    source: str,
) -> None:
    for role in role_keys:
        try:
            load_role(roles_dir, role)
        except SystemExit as exc:
            die(f'{source}: participants role file unreadable for {role}: {roles_dir / f"{role}.json"}: {exc}')

def reviewer_role(entry: dict) -> str | None:
    value = entry.get('reviewerRole')
    if isinstance(value, str) and value.strip():
        return value
    return None

def participant_roles(entry: dict) -> list[str]:
    return [p['role'] for p in entry.get('participants', [])]

def participant_agent_id(entry: dict, role: str) -> str | None:
    for participant in entry.get('participants', []):
        if participant.get('role') == role:
            value = participant.get('agentId')
            return value if isinstance(value, str) else None
    return None

def has_participant(entry: dict, role: str) -> bool:
    return role in participant_roles(entry)

def reviewer_state(entry: dict) -> dict:
    reviewer = reviewer_role(entry)
    if reviewer is None:
        return {'reviewerRole': None, 'state': 'absent'}
    state = 'active' if has_participant(entry, reviewer) else 'pending'
    return {'reviewerRole': reviewer, 'state': state}

def active_reviewer_role(entry: dict) -> str | None:
    reviewer = reviewer_role(entry)
    if reviewer and has_participant(entry, reviewer):
        return reviewer
    return None

def reviewer_backed(entry: dict) -> bool:
    return reviewer_role(entry) is not None

def pending_reviewer_role(entry: dict) -> str | None:
    reviewer = reviewer_role(entry)
    if reviewer and not has_participant(entry, reviewer):
        return reviewer
    return None

def reviewer_mode(entry: dict) -> str:
    if 'reviewerMode' in entry:
        value = entry['reviewerMode']
        if isinstance(value, str) and value.strip():
            return value
    if entry.get('createdAt') is None:
        return DEFAULT_REVIEWER_MODE
    die('registry: collab.reviewerMode is required when createdAt is present')

def reviewer_optional_phases(entry: dict) -> list[str]:
    if 'reviewerOptionalPhases' in entry:
        value = entry['reviewerOptionalPhases']
        if isinstance(value, list):
            return list(value)
        die('registry: collab.reviewerOptionalPhases must be a list when present')
    if entry.get('createdAt') is None:
        return list(DEFAULT_REVIEWER_OPTIONAL_PHASES)
    die('registry: collab.reviewerOptionalPhases is required when createdAt is present')

def parse_reviewer_optional_phases(value: str | None) -> list[str]:
    if value is None or not value.strip():
        die('reviewer-optional-phases requires at least one phase')
    raw = value.strip()
    if ',' in raw:
        phases = [phase.strip() for phase in raw.split(',') if phase.strip()]
    else:
        tokens = raw.split()
        phases = []
        index = 0
        while index < len(tokens):
            matched = None
            for phase in PHASES:
                phase_tokens = phase.split()
                if tokens[index:index + len(phase_tokens)] == phase_tokens:
                    matched = phase
                    break
            if matched is None:
                phases.append(tokens[index])
                index += 1
            else:
                phases.append(matched)
                index += len(matched.split())
    if not phases:
        die('reviewer-optional-phases requires at least one phase')
    invalid = [phase for phase in phases if phase not in PHASES]
    if invalid:
        die(f'reviewer-optional-phases must contain valid phase names: {", ".join(invalid)}')
    if len(set(phases)) != len(phases):
        die('reviewer-optional-phases must not contain duplicates')
    return phases

def reviewer_required_for_phase(entry: dict, phase: str) -> str | None:
    reviewer = active_reviewer_role(entry)
    if not reviewer:
        return None
    if reviewer_mode(entry) == 'last-in-convergent-phases' and phase in CONVERGENT_REVIEWER_PHASES:
        return reviewer
    return None

def reviewer_optional_for_phase(entry: dict, phase: str) -> str | None:
    reviewer = active_reviewer_role(entry)
    if reviewer and phase in reviewer_optional_phases(entry):
        return reviewer
    return None

def optional_reviewer_allowed_at_round_boundary(
    entry: dict,
    phase: str,
    contributors: list[str],
    order: list[str],
) -> str | None:
    reviewer = reviewer_optional_for_phase(entry, phase)
    if not reviewer or not order or not contributors:
        return None
    if contributors[-1] == reviewer:
        return None

    ordinary_contributors = [role for role in contributors if role in order]
    if len(ordinary_contributors) < len(order):
        return None
    if ordinary_contributors[-len(order):] != order:
        return None
    return reviewer

def expected_speaker(entry: dict, contributors: list[str]) -> str:
    phase = entry['activePhase']
    order = effective_turn_order(entry)
    reviewer = reviewer_required_for_phase(entry, phase)
    if reviewer and all(contributors.count(role) >= 1 for role in order):
        if contributors.count(reviewer) < 1:
            return reviewer
    ordered_contributors = [role for role in contributors if role in order]
    if not ordered_contributors:
        return order[0]
    last = ordered_contributors[-1]
    return order[(order.index(last) + 1) % len(order)]

def add_participant_to_entry(entry: dict, role: str, agent_id: str = 'unknown') -> bool:
    if not role.strip():
        die('participant role must be non-empty')
    changed = False
    is_reviewer = role == reviewer_role(entry) and reviewer_mode(entry) == 'last-in-convergent-phases'
    if not has_participant(entry, role):
        entry['participants'].append({'role': role, 'agentId': agent_id})
        changed = True
    if not entry['turnOrder']:
        entry['turnOrder'] = [
            p['role'] for p in entry['participants']
            if not (
                p['role'] == reviewer_role(entry)
                and reviewer_mode(entry) == 'last-in-convergent-phases'
            )
        ]
        changed = True
    elif not is_reviewer and role not in entry['turnOrder']:
        entry['turnOrder'].append(role)
        changed = True
    return changed

def count_caller_declined_agent_id_write(data: dict, agent_id: str) -> None:
    if agent_id != CALLER_DECLINED_AGENT_ID:
        return
    metrics = data.setdefault('identityMetrics', {})
    if not isinstance(metrics, dict):
        die('registry: identityMetrics must be an object when present')
    count = metrics.get('callerDeclinedAgentIdWrites', 0)
    if not isinstance(count, int) or count < 0:
        die('registry: identityMetrics.callerDeclinedAgentIdWrites must be a non-negative integer when present')
    metrics['callerDeclinedAgentIdWrites'] = count + 1

def assert_caller_role(entry: dict, caller_role: str | None, action: str, subject_role: str | None = None) -> None:
    if caller_role is None:
        return
    if not has_participant(entry, caller_role):
        die(f'caller role must already be a participant: {caller_role}')
    if action in MODERATOR_ONLY_ACTIONS and caller_role != entry['moderatorRole']:
        die(f'{action} requires moderator role: {entry["moderatorRole"]}')
    if subject_role is not None and caller_role != subject_role:
        die(f'{action} caller role must match subject role: {subject_role}')

def effective_turn_order(entry: dict) -> list[str]:
    order = entry['turnOrder'] or participant_roles(entry)
    reviewer = reviewer_role(entry)
    if reviewer and reviewer_mode(entry) == 'last-in-convergent-phases':
        return [role for role in order if role != reviewer]
    return order

def remove_moderator_from_turn_order(entry: dict, order: list[str] | None = None) -> None:
    moderator = entry['moderatorRole']
    source_order = order or effective_turn_order(entry)
    entry['turnOrder'] = [role for role in source_order if role != moderator]
    if not entry['turnOrder']:
        entry['turnOrder'] = [r for r in participant_roles(entry) if r != moderator]
    if not entry['turnOrder']:
        die('turnOrder cannot be empty after removing moderator')

def phase_turn_order(entry: dict, phase: str) -> list[str]:
    reviewer = reviewer_role(entry) if reviewer_mode(entry) == 'last-in-convergent-phases' else None
    roles = [role for role in participant_roles(entry) if role != reviewer]
    if phase in MOD_EXCLUDED_PHASES:
        roles = [role for role in roles if role != entry['moderatorRole']]
    elif entry['moderatorRole'] in roles:
        roles = [entry['moderatorRole']] + [role for role in roles if role != entry['moderatorRole']]
    if not roles:
        die(f'turnOrder cannot be empty for phase: {phase}')
    return roles

def normalize_turn_order_for_phase(entry: dict, phase: str) -> None:
    entry['turnOrder'] = phase_turn_order(entry, phase)
