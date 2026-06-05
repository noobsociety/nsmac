#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import datetime as dt
import sys

root = sys.argv[1]
sys.path.insert(0, root)

from tools.collab import normalizers as n


def aborts(fn, contains):
    try:
        fn()
    except SystemExit as exc:
        assert contains in str(exc), str(exc)
    else:
        raise AssertionError(f'expected abort containing {contains!r}')


assert n.normalize_slug('API UX rewrite') == 'api-ux-rewrite'
assert n.normalize_title('api qa vs ui') == 'API QA vs UI'
assert n.phase_slug('Action Plan') == 'action-plan'
assert n.display_title('abcdefghij', limit=5) == 'abcde\u2026'
assert n.collab_date({'id': '2026-06-04-sample'}) == '2026-06-04'

assert n.normalize_join_agent_id(' codex ') == 'codex'
assert n.normalize_join_agent_id('unknown') == 'unknown'
aborts(lambda: n.normalize_join_agent_id('Unknown'), 'unknown token must be lowercase')
aborts(lambda: n.normalize_join_agent_id('n/a'), 'literal unknown')

assert n.normalize_scope_path('tools/collab/registry.py', 'scope') == 'tools/collab/registry.py'
aborts(lambda: n.normalize_scope_path('/tmp/file', 'scope'), 'repository-relative')
aborts(lambda: n.normalize_scope_path('tools/../file', 'scope'), 'normalized')

assert n.path_is_within('tools/collab/registry.py', 'tools/collab')
assert not n.path_is_within('tools-other/file', 'tools')
assert n.scope_matches_declared('tools/collab/registry.py', 'tools/collab/*.py')
assert not n.scope_matches_declared('tools/collab/registry.py', 'commands')
assert n.normalize_touched_paths(['tools/a.py', 'tools/a.py', 'tools/b.py']) == ['tools/a.py', 'tools/b.py']

aware = n.parse_execution_datetime('2026-06-04T12:00:00+00:00')
assert aware is not None and aware.tzinfo is not None
naive = n.parse_execution_datetime('2026-06-04T12:00:00')
assert naive is not None and naive.tzinfo is not None
assert n.parse_execution_datetime('not-a-date') is None

assert n.normalize_restore_target('handoff', 'Completion') == 'Handoff'
assert n.normalize_restore_target(None, 'Completion') is None
aborts(lambda: n.normalize_restore_target('Audit', 'Completion'), 'Action Plan, Handoff')
aborts(lambda: n.normalize_restore_target('Handoff', 'Audit'), 'must not be later')

assert n.assert_one_line_nonempty(' reason ', 'restoreReason') == 'reason'
aborts(lambda: n.assert_one_line_nonempty('a\nb', 'restoreReason'), 'one line')

stamp = n.format_timestamp(dt.datetime(2026, 6, 4, 12, 30, tzinfo=dt.timezone.utc))
assert stamp == '2026-06-04 12:30 +00:00'

print('OK: normalizers module is directly exercised')
PY
