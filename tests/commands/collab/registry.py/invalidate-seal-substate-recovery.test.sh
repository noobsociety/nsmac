#!/usr/bin/env bash
set -euo pipefail

# Regression: invalidate_verification_seal must never strand a reviewer-backed
# collab in the 'assessment' review sub-state when the paired round is no longer
# intact. 'assessment' presumes a completed round awaiting a verdict; if the
# round was reset (e.g. a reopen clears rounds/participant stages before
# invalidating the seal) leaving the cycle in 'assessment' is a dead end: the
# seal block is immutable in assessment, a success verdict is blocked by the
# stale seal, and participant verify is gated to the 'participant' sub-state.
# The fix retains 'assessment' only when the round is intact and otherwise falls
# back to the live participant/seal entry point. This test isolates that branch
# decision from the participant role-state machinery (covered elsewhere).

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys
sys.path.insert(0, f"{sys.argv[1]}/commands/collab/engine")
import registry as R

def mk(rounds):
    return {
        'reviewerRole': 'pa',
        'verification': {'rounds': rounds, 'subState': 'assessment', 'cap': 3},
        'verificationSeal': {'sealedBy': 'pa'},
        'verdict': {'outcome': 'failed'},
    }

R.reviewer_backed = lambda e: True

# Round intact -> retain 'assessment' (legitimate stale-in-assessment recovery).
R.participant_verification_incomplete = lambda e: False
R.participant_verification_enabled = lambda e: True
e = mk(1)
R.invalidate_verification_seal(e, 'intact')
assert e['verificationSeal']['stale'] is True, 'seal not marked stale'
assert e.get('verdict') is None, 'verdict not cleared'
assert e['verification']['subState'] == 'assessment', \
    f"intact round should keep assessment, got {e['verification']['subState']}"

# Round reset (rounds=0), participant verification enabled -> 'participant'.
e = mk(0)
R.invalidate_verification_seal(e, 'reset')
assert e['verification']['subState'] == 'participant', \
    f"reset round stranded: {e['verification']['subState']}"

# Round present but participants incomplete -> 'participant'.
R.participant_verification_incomplete = lambda e: True
e = mk(1)
R.invalidate_verification_seal(e, 'incomplete')
assert e['verification']['subState'] == 'participant', \
    f"incomplete participants stranded: {e['verification']['subState']}"

# Round reset, participant verification disabled -> 'seal' (re-seal directly).
R.participant_verification_incomplete = lambda e: False
R.participant_verification_enabled = lambda e: False
e = mk(0)
R.invalidate_verification_seal(e, 'reset-nopv')
assert e['verification']['subState'] == 'seal', \
    f"reset/no-pv should re-seal, got {e['verification']['subState']}"
PY

printf 'OK: seal invalidation returns the cycle to a re-sealable sub-state, never strands assessment\n'
