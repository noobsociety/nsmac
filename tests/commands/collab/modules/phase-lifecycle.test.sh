#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import contextlib
import io
import json
import sys

root = sys.argv[1]
sys.path.insert(0, root)

from commands.collab.engine import phase_lifecycle as p


assert p.next_phase_name('Audit') == 'Discussion'
assert p.next_phase_name('Completion') is None

compact = p.transition_notice('Discussion', 'Conclusion')
assert compact == {
    'notice': 'compact',
    'transition': 'Discussion->Conclusion',
    'message': 'Run /compact before continuing to Conclusion.',
}
assert p.transition_notice('Audit', 'Discussion') is None
assert 'Action Plan entries' in p.transition_notice('Conclusion', 'Action Plan')['message']
assert p.transition_notice('Handoff', 'Completion')['notice'] == 'subagent'

entry = {'activePhase': 'Discussion', 'moderatorRole': 'mod'}
assert p.discussion_turn_notice(entry, ['pe'])['compactBeforeNextCommand'] is True
assert p.discussion_turn_notice(entry, ['mod']) is None
assert p.discussion_turn_notice({'activePhase': 'Audit', 'moderatorRole': 'mod'}, ['pe']) is None

lifecycle = p.lifecycle_status_notice('closed')
assert lifecycle['notice'] == 'clear'
assert p.notice_message({'message': ' custom '}) == 'custom'
assert p.notice_message({'notice': 'fallback'}) == 'fallback'
assert p.notice_message({}) == 'Lifecycle notice emitted.'

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    p.print_notice_diagnostic(lifecycle, emit_json=False)
assert buffer.getvalue().startswith('NOTICE: Run /clear')

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    p.print_notice_diagnostic(lifecycle, emit_json=True)
assert json.loads(buffer.getvalue())['status'] == 'closed'

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    p.print_lifecycle_diagnostic({'phaseState': 'Completion', 'notice': lifecycle}, emit_json=True)
lines = buffer.getvalue().splitlines()
assert lines[0] == 'PHASE: Completion'
assert json.loads(lines[-1])['phaseState'] == 'Completion'

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    p.print_phase_result('Completion', lifecycle, emit_json=False)
assert buffer.getvalue().splitlines()[0] == 'Completion'

print('OK: phase_lifecycle module is directly exercised')
PY
