#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys

root = sys.argv[1]
sys.path.insert(0, root)

from commands.collab.engine import participants as p
from commands.collab.engine.registry_constants import CALLER_DECLINED_AGENT_ID


def aborts(fn, contains):
    try:
        fn()
    except SystemExit as exc:
        assert contains in str(exc), str(exc)
    else:
        raise AssertionError(f'expected abort containing {contains!r}')


entry = {
    'activePhase': 'Audit',
    'moderatorRole': 'mod',
    'reviewerRole': 'pa',
    'reviewerMode': 'last-in-convergent-phases',
    'reviewerOptionalPhases': ['Discussion'],
    'participants': [{'role': 'mod', 'agentId': 'mod-agent'}],
    'turnOrder': [],
}

assert p.reviewer_state(entry) == {'reviewerRole': 'pa', 'state': 'pending'}
assert p.pending_reviewer_role(entry) == 'pa'
assert p.add_participant_to_entry(entry, 'pe', 'agent-pe')
assert p.add_participant_to_entry(entry, 'tw', 'agent-tw')
assert p.add_participant_to_entry(entry, 'pa', 'agent-pa')
assert p.participant_roles(entry) == ['mod', 'pe', 'tw', 'pa']
assert p.participant_agent_id(entry, 'pe') == 'agent-pe'
assert p.reviewer_state(entry) == {'reviewerRole': 'pa', 'state': 'active'}
assert p.active_reviewer_role(entry) == 'pa'
assert p.effective_turn_order(entry) == ['mod', 'pe', 'tw']
assert p.phase_turn_order(entry, 'Audit') == ['mod', 'pe', 'tw']
assert p.phase_turn_order(entry, 'Conclusion') == ['pe', 'tw']
assert p.expected_speaker(entry, ['mod', 'pe', 'tw']) == 'pa'
assert p.optional_reviewer_allowed_at_round_boundary(
    entry,
    'Discussion',
    ['mod', 'pe', 'tw'],
    ['mod', 'pe', 'tw'],
) == 'pa'

p.remove_moderator_from_turn_order(entry, ['mod', 'pe', 'tw'])
assert entry['turnOrder'] == ['pe', 'tw']
p.normalize_turn_order_for_phase(entry, 'Audit')
assert entry['turnOrder'] == ['mod', 'pe', 'tw']

assert p.parse_reviewer_optional_phases('Discussion Handoff') == ['Discussion', 'Handoff']
assert p.parse_reviewer_optional_phases('Action Plan,Discussion') == ['Action Plan', 'Discussion']
aborts(lambda: p.parse_reviewer_optional_phases('Discussion Discussion'), 'duplicates')

p.assert_caller_role(entry, 'mod', 'advance')
aborts(lambda: p.assert_caller_role(entry, 'pe', 'advance'), 'requires moderator role')
aborts(lambda: p.assert_caller_role(entry, 'pe', 'execution', subject_role='tw'), 'must match subject role')

data = {}
p.count_caller_declined_agent_id_write(data, CALLER_DECLINED_AGENT_ID)
p.count_caller_declined_agent_id_write(data, CALLER_DECLINED_AGENT_ID)
assert data['identityMetrics']['callerDeclinedAgentIdWrites'] == 2

print('OK: participants module is directly exercised')
PY
