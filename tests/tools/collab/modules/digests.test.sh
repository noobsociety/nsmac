#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import subprocess
import sys
import tempfile
from pathlib import Path

root = sys.argv[1]
sys.path.insert(0, root)

from tools.collab import digests as d


def run(argv, cwd):
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


transcript = '\n'.join([
    'before',
    '<details>',
    '<summary>Full contribution</summary>',
    '',
    'large body',
    '</details>',
    'after',
]) + '\n'

blocks = d.managed_full_body_blocks(transcript)
assert len(blocks) == 1 and 'large body' in blocks[0]
assert d.rendered_transcript_without_full_bodies(transcript) == 'before\nafter\n'
assert d.full_body_signature_for_transcript(transcript) != d.full_body_signature_for_transcript(
    transcript.replace('large body', 'changed body')
)

entry = {
    'handoff': {'roles': {'pe': {'writeScope': ['b', 'a']}}},
    'execution': {
        'pe': {
            'status': 'completed',
            'date': '2026-06-04T12:00:00+00:00',
            'validationResult': 'passed',
            'validationScope': 'full',
            'touchedPaths': ['tools/b.py', 'tools/a.py'],
            'commits': ['c2', 'c1'],
            'contentDigest': 'digest',
            'pathDigests': {'tools/a.py': {'mode': '100644', 'blob': 'abc'}},
            'agentId': 'codex',
        }
    },
}
assert d.participant_write_scope_signature(entry, 'pe') == d.participant_write_scope_signature(
    {'handoff': {'roles': {'pe': {'writeScope': ['a', 'b']}}}},
    'pe',
)
signature = d.participant_execution_signature(entry, 'pe')
changed = {'execution': {'pe': dict(entry['execution']['pe'], status='failed')}}
assert signature != d.participant_execution_signature(changed, 'pe')
assert d.touched_paths_for_execution(entry) == ['tools/b.py', 'tools/a.py']
assert d.validation_scopes_for_execution(entry) == ['full']
rows = d.active_execution_entries(entry)
assert rows[0]['entryId'].startswith('pe-2026-06-04t12-00-00-00-00')
assert rows[0]['pathDigests'] == {'tools/a.py': {'mode': '100644', 'blob': 'abc'}}
assert d.execution_signature(entry)

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    run(['git', 'init', '-q'], repo)
    run(['git', 'config', 'user.email', 'tester@example.com'], repo)
    run(['git', 'config', 'user.name', 'tester'], repo)
    (repo / 'tracked.txt').write_text('tracked\n')
    run(['git', 'add', 'tracked.txt'], repo)
    run(['git', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'seed'], repo)

    worktree = d.content_digest_for_touched_paths(repo, 'WORKTREE', ['tracked.txt'])
    committed = d.content_digest_for_touched_paths(repo, 'HEAD', ['tracked.txt'])
    assert worktree == committed
    assert worktree['pathDigests']['tracked.txt']['mode'] == '100644'

print('OK: digests module is directly exercised')
PY
