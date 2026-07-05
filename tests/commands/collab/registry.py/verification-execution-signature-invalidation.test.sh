#!/usr/bin/env bash
set -euo pipefail

# A completed participant verification certifies a specific executed deliverable.
# It must be invalidated when that role's executed content changes -- a
# re-execution that keeps the same declared write scope, or a provenance repair
# that repoints the commit -- so a stale verification cannot be preserved across
# a reopen and ride through to a success seal. Declared-scope equality alone is
# insufficient; the per-role execution signature is the guard. This isolates that
# mechanism (lazy reset and scope-aware reset) plus inactive-guidance text.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys
sys.path.insert(0, f"{sys.argv[1]}/commands/collab/engine")
import registry as R


def entry():
    return {
        'id': '2026-06-02-exec-sig',
        'reviewerRole': 'pa',
        'moderatorRole': 'mod',
        'turnOrder': ['tw'],
        'participants': [{'role': 'tw', 'agentId': 'x'}, {'role': 'pa', 'agentId': 'y'}],
        'handoff': {'roles': {'tw': {'writeScope': ['a.txt']}}},
        'execution': {'tw': {
            'status': 'completed', 'validationResult': 'passed',
            'touchedPaths': ['a.txt'], 'commits': ['c1'],
        }},
        'verification': {
            'rounds': 1, 'subState': 'seal', 'participants': {},
        },
    }


def complete_tw(e):
    state = R.participant_verification_role_state(e, 'tw')
    state['stage'] = 'completed'
    state['executionSignature'] = R.participant_execution_signature(e, 'tw')


# Unchanged scope and unchanged execution -> verification preserved.
e = entry()
complete_tw(e)
assert R.participant_verification_role_state(e, 'tw').get('stage') == 'completed', \
    'unchanged scope+execution should preserve completed verification'

# Same declared scope, but a re-execution changed the touched content (PE2)
# -> the lazy reset invalidates the stale completion on the next access.
e = entry()
complete_tw(e)
e['execution']['tw']['touchedPaths'] = ['a.txt', 'b.txt']
assert R.participant_verification_role_state(e, 'tw').get('stage') != 'completed', \
    'changed execution content (touchedPaths) must reset a completed verification'

# Same scope and paths, but a provenance repoint changed the commit (PE1)
# -> also invalidated.
e = entry()
complete_tw(e)
e['execution']['tw']['commits'] = ['c2']
assert R.participant_verification_role_state(e, 'tw').get('stage') != 'completed', \
    'repointed execution commit must reset a completed verification'

# The scope-aware reset preserves only when BOTH scope and execution match.
e = entry()
complete_tw(e)
e['execution']['tw']['commits'] = ['c2']  # content changed, scope unchanged
R.reset_participant_verification_stages(e, scope_aware=True)
assert e['verification']['participants']['tw'].get('stage') != 'completed', \
    'scope-aware reset must clear a role whose execution content changed'

# Inactive participant-verify guidance names only published routes and the right
# actor per sub-state (no restart-verification or repair-execution-provenance route).
def msg(substate):
    e = entry()
    e['verification']['subState'] = substate
    return R.participant_verification_inactive_message(e)

seal_msg = msg('seal')
assert '(collab seal verification ' in seal_msg and 'restart-verification' not in seal_msg, seal_msg

assess_msg = msg('assessment')
assert '(collab seal verification ' in assess_msg, assess_msg
assert '(collab reopen <action-plan|handoff>' in assess_msg, assess_msg
assert 'restart-verification' not in assess_msg and 'repair-execution-provenance' not in assess_msg, assess_msg

print('OK: execution-content change invalidates completed verification (lazy and scope-aware); '
      'inactive guidance uses only published routes')
PY
