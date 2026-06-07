#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys

root = sys.argv[1]
sys.path.insert(0, root)

from commands.collab.engine import handoff_shape as h


def aborts(fn, contains):
    try:
        fn()
    except SystemExit as exc:
        assert contains in str(exc), str(exc)
    else:
        raise AssertionError(f'expected abort containing {contains!r}')


assert h.validate_handoff_write_scope([' commands/collab/engine/ ', 'tools/*.py']) == ['commands/collab/engine', 'tools/*.py']
aborts(lambda: h.validate_handoff_write_scope(['/tmp/file']), 'writeScope')
aborts(lambda: h.validate_handoff_write_scope(['tools/a', 'tools/a/']), 'writeScope')
aborts(lambda: h.validate_handoff_write_scope(['../outside']), 'writeScope')

assert h.validate_handoff_validation_commands(['./tests/run.sh', '--fast']) == [['./tests/run.sh', '--fast']]
assert h.validate_handoff_validation_commands([
    {'argv': ['./tools/check.sh', 'arg']},
    ['./tests/run.sh'],
]) == [['./tools/check.sh', 'arg'], ['./tests/run.sh']]
aborts(lambda: h.validate_handoff_validation_commands(['tests/run.sh']), 'validationCommands')
aborts(lambda: h.normalize_validation_arg('bad;rm'), 'validationCommands')

effort = 'EFFORT OVERRIDE: medium \u2014 coherence-risk: direct test'
comment = h.effort_override_metadata_comment(effort)
assert comment.startswith('<!-- collab:effort-override b64:')
assert h.render_content_for_transcript(effort + '\nkeep') == [comment, 'keep']

content = """EFFORT OVERRIDE: medium \u2014 coherence-risk: direct test

**writeScope:**
- `commands/collab/engine`

**validationCommands:**
- `["./tests/run.sh"]`
"""
state = h.parse_handoff_content(content)
assert state['writeScope'] == ['commands/collab/engine']
assert state['validationCommands'] == [['./tests/run.sh']]
assert state['body'].splitlines()[0].startswith('<!-- collab:effort-override b64:')

valid = {
    'writeScope': ['commands/collab/engine'],
    'validationCommands': [['./tests/run.sh']],
    'body': 'body',
}
assert h.validate_handoff_state(valid, 'test') == valid
aborts(lambda: h.validate_handoff_state(dict(valid, schemaVersion=1), 'test'), 'disallowed version field')

entry = {'handoff': {'roles': {'pe': valid}}}
assert h.handoff_state_for_role(entry, 'pe')['writeScope'] == ['commands/collab/engine']
assert h.handoff_state_for_role(entry, 'tw') is None
h.set_handoff_state(entry, 'tw', valid)
assert h.handoff_state_for_role(entry, 'tw')['validationCommands'] == [['./tests/run.sh']]

print('OK: handoff_shape module is directly exercised')
PY
