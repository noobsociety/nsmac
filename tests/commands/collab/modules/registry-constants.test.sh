#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys

root = sys.argv[1]
sys.path.insert(0, root)

from commands.collab.engine import registry_constants as c

assert c.PHASES == ['Audit', 'Discussion', 'Conclusion', 'Action Plan', 'Handoff', 'Completion']
assert c.FULL_BODY_SUMMARY_LINE == '<summary>Full contribution</summary>'
assert c.SHELL_PATTERN_RE.search('echo one && echo two')
assert c.SHELL_PATTERN_RE.search('$(unsafe)')
assert not c.SHELL_PATTERN_RE.search('./tests/run.sh')
assert c.GLOB_PATTERN_RE.search('tools/*.py')
assert not c.GLOB_PATTERN_RE.search('commands/collab/engine/registry.py')

assert c.MODERATOR_ONLY_ACTIONS >= {'advance', 'archive', 'close', 'delete', 'reopen', 'restore', 'set', 'unset'}
assert c.ALLOWED_STATUSES == {'open', 'closed', 'archived'}
assert c.ALLOWED_TERMINALS == {'seal', 'issue'}
assert c.TERMINAL_CHOICES_MESSAGE == 'seal, issue'
assert c.ALLOWED_COMPLETION_SUBSTATES == {'execution', 'verification'}
assert c.ALLOWED_VERIFICATION_SUBSTATES == {'participant', 'seal', 'assessment'}
assert c.ALLOWED_VERDICT_RESTORE_TARGETS == {'Action Plan', 'Handoff'}
assert c.DISALLOWED_VERSION_FIELD == 'schemaVersion'
assert c.DELETED_PATH_MODE == '000000'
assert c.DELETED_PATH_BLOB == '0' * 40

print('OK: registry_constants module is directly exercised')
PY
