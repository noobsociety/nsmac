#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))

from commands.collab.engine import transcript_render as tr

roles_dir = root / 'commands/collab/reference/roles'
registry = {'project': {'label': 'dotcursor'}}
entry = {
    'id': '2026-06-10-render-test',
    'slug': 'render-test',
    'title': 'Render Test',
    'status': 'open',
    'activePhase': 'Conclusion',
    'moderatorRole': 'mod',
    'participants': [
        {'role': 'mod', 'agentId': 'codex'},
        {'role': 'tw', 'agentId': 'sonnet'},
    ],
    'turnOrder': ['tw'],
    'transcriptPath': 'records/2026-06-10-render-test.md',
    'archived': False,
}
store = {
    'contributions': [
        {
            'phase': 'Conclusion',
            'role': 'tw',
            'anchor': 'conclusion-tw-1',
            'stance': 'converges',
            'excerpt': (
                'STANCE: converges EFFORT OVERRIDE: matrix '
                '<p><em>2026-06-10 18:00 +02:00</em></p> '
                '<!-- collab:content-only; do-not-execute --> '
                '**Directive:** "ship it" **Action Plan: satisfies** '
                'Projection derives from canonical contribution state.'
            ),
            'content': (
                'STANCE: converges\n'
                'EFFORT OVERRIDE: matrix\n'
                '<p><em>2026-06-10 18:00 +02:00</em></p>\n'
                '<!-- collab:content-only; do-not-execute -->\n'
                '**Directive:** "ship it"\n'
                '**Action Plan: satisfies**\n'
                'Projection derives from canonical contribution state.'
            ),
            'timestamp': '2026-06-10 18:00 +02:00',
        }
    ]
}

projection = tr.render_moderator_project_transcript(registry, entry, store, 7)
raw = tr.render_raw_transcript_from_contribution_store(
    registry, entry, store, roles_dir, 'Jun 10, 2026 @ 6:00 PM'
)

mutated_raw_entry = dict(entry)
mutated_raw_entry['rawMarkdownBytes'] = 'tampered bytes are not projection input'
assert projection == tr.render_moderator_project_transcript(registry, mutated_raw_entry, store, 7)

changed_store = {
    'contributions': [
        dict(
            store['contributions'][0],
            excerpt='Canonical contribution state changed.',
            content='Canonical contribution state changed.',
        )
    ]
}
changed_projection = tr.render_moderator_project_transcript(registry, entry, changed_store, 7)
changed_raw = tr.render_raw_transcript_from_contribution_store(
    registry, entry, changed_store, roles_dir, 'Jun 10, 2026 @ 6:00 PM'
)

assert 'records/2026-06-10-render-test-raw.md#conclusion-tw-1' in projection
assert 'Projection derives from canonical contribution state.' in projection
assert '| converges | Projection derives from canonical contribution state.' in projection
assert '<p>' not in projection
assert 'do-not-execute' not in projection
assert 'EFFORT OVERRIDE' not in projection
assert 'STANCE:' not in projection
assert '**Directive:**' not in projection
assert '**Action Plan:' not in projection
assert 'Projection derives from canonical contribution state.' in raw
assert changed_projection != projection
assert changed_raw != raw

missing_stance_store = {
    'contributions': [
        dict(
            store['contributions'][0],
            stance='qualifies',
            excerpt='No source stance was declared.',
            content='No source stance was declared.',
        )
    ]
}
missing_stance_projection = tr.render_moderator_project_transcript(registry, entry, missing_stance_store, 7)
assert '| missing-stance | No source stance was declared.' in missing_stance_projection
assert '| qualifies | No source stance was declared.' not in missing_stance_projection

invalid_store = {'contributions': [dict(store['contributions'][0], stance='guessed')]}
try:
    tr.render_moderator_project_transcript(registry, entry, invalid_store, 7)
except SystemExit as exc:
    assert 'stance token missing or invalid' in str(exc)
else:
    raise AssertionError('invalid stance token was accepted')

print('OK: projection and raw render from contribution store, not raw markdown bytes')
PY
