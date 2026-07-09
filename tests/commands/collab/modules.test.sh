#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import ast
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

root = sys.argv[1]
sys.path.insert(0, root)


def run(argv: list[str], cwd: Path) -> str:
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def aborts(fn, contains: str) -> None:
    try:
        fn()
    except SystemExit as exc:
        assert contains in str(exc), str(exc)
    else:
        raise AssertionError(f'expected abort containing {contains!r}')


def test_engine_import_boundaries() -> None:
    for path in sorted((Path(root) / 'commands/collab/engine').glob('*.py')):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(alias.name == '*' for alias in node.names), (
                    f'wildcard import leaks module boundary: {path}:{node.lineno}'
                )


def test_digests() -> None:
    from commands.collab.engine import digests as d

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

        (repo / 'src').mkdir()
        (repo / 'src/a.txt').write_text('alpha v1\n')
        (repo / 'src/b.txt').write_text('beta v1\n')
        run(['git', 'add', 'src/a.txt', 'src/b.txt'], repo)
        run(['git', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'deliverables'], repo)

        carried_digest = d.content_digest_for_touched_paths(
            repo,
            'HEAD',
            ['src/a.txt', 'src/b.txt'],
        )
        carried = {
            'role': 'pe',
            'entryId': 'pe-old',
            'status': 'completed',
            'date': '2026-06-04',
            'validationResult': 'passed',
            'validationScope': 'full',
            'touchedPaths': ['src/a.txt', 'src/b.txt'],
            'pathDigests': carried_digest['pathDigests'],
            'contentDigest': carried_digest['contentDigest'],
        }
        carry_entry = {
            'workRepo': str(repo),
            'reopenCoverage': {'executionEntries': [carried]},
        }
        valid = d.valid_carried_execution_entries(carry_entry)
        assert valid[0]['touchedPaths'] == ['src/a.txt', 'src/b.txt']
        assert valid[0]['carriedFromReopen'] is True

        transitive_entry = {
            'workRepo': str(repo),
            'reopenCoverage': {'executionEntries': valid},
        }
        assert d.valid_carried_execution_entries(transitive_entry)[0]['touchedPaths'] == [
            'src/a.txt',
            'src/b.txt',
        ]

        (repo / 'src/a.txt').write_text('alpha v2\n')
        run(['git', 'add', 'src/a.txt'], repo)
        run(['git', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'drift a'], repo)
        drifted = d.valid_carried_execution_entries(carry_entry)
        assert drifted[0]['touchedPaths'] == ['src/b.txt']

        (repo / 'src/b.txt').unlink()
        run(['git', 'add', 'src/b.txt'], repo)
        run(['git', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'remove b'], repo)
        assert d.valid_carried_execution_entries(carry_entry) == []


def test_git_repo() -> None:
    from commands.collab.engine import git_repo as g

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp).resolve()
        run(['git', 'init', '-q'], repo)
        run(['git', 'config', 'user.email', 'tester@example.com'], repo)
        run(['git', 'config', 'user.name', 'tester'], repo)
        (repo / 'nested').mkdir()
        (repo / 'tracked.txt').write_text('tracked\n')
        (repo / 'deleted.txt').write_text('delete me\n')
        run(['git', 'add', 'tracked.txt', 'deleted.txt'], repo)
        run(['git', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'seed'], repo)
        seed = run(['git', 'rev-parse', 'HEAD'], repo)

        assert g.resolve_git_work_tree(str(repo), 'repo').resolve() == repo
        assert g.enclosing_git_tree(repo / 'nested').resolve() == repo
        assert 'tracked.txt' in g.git_commit_paths('HEAD', repo)
        assert g.git_latest_commit_for_path('tracked.txt', repo, '2999-01-01T00:00:00+00:00') == seed
        assert g.execution_commits_for_touched_paths('2999-01-01T00:00:00+00:00', repo, ['tracked.txt']) == [seed]
        assert g.current_head_commit('1970-01-01T00:00:00+00:00', repo) is None

        run(['git', 'rm', '-q', 'deleted.txt'], repo)
        run(['git', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'delete file'], repo)
        assert 'deleted.txt' in g.git_committed_deletion_paths(['deleted.txt'], repo)

        (repo / 'staged.txt').write_text('staged\n')
        run(['git', 'add', 'staged.txt'], repo)
        (repo / 'tracked.txt').write_text('modified\n')
        assert 'staged.txt' in g.git_index_or_staged_paths(['staged.txt'], repo)
        assert 'staged.txt' in g.git_staged_paths(['staged.txt'], repo)
        assert 'tracked.txt' in g.git_unstaged_paths(['tracked.txt'], repo)
        assert g.working_tree_path_exists('tracked.txt', repo)
        assert not g.working_tree_path_exists('missing.txt', repo)

        assert g.work_repo_root({'workRepo': str(repo)}).resolve() == repo
        g.assert_touched_paths_recordable_in_work_repo({'workRepo': str(repo)}, ['tracked.txt', 'staged.txt'])
        aborts(
            lambda: g.execution_commits_for_touched_paths(
                '2999-01-01T00:00:00+00:00',
                repo,
                ['missing.txt'],
            ),
            'no committed provenance',
        )


def test_diff_scaffold_categories() -> None:
    from commands.collab.engine import diff as d

    route_doc = Path(root) / 'commands/collab/diff/index.md'
    route_titles: list[str] = []
    in_categories = False
    for line in route_doc.read_text().splitlines():
        if line.startswith('- **What diff ignores '):
            in_categories = True
            continue
        if in_categories and line.startswith('- **'):
            break
        if in_categories:
            match = re.match(r'^  - \*\*(?P<title>[^*]+)\*\*', line)
            if match:
                route_titles.append(match.group('title'))

    assert d.ignored_scaffold_category_names() == [
        'Contribution timestamp wrappers',
        'Content-only guards',
        'Effort-override banners',
        'Full-contribution collapsible blocks',
        'Managed header block',
        'Revision-history collapsible blocks',
        'Action Plan checkbox state',
    ]
    assert set(route_titles) == set(d.ignored_scaffold_category_names())
    predicate_map = d.scaffold_predicate_category_map()
    assert set().union(*[set(values) for values in predicate_map.values()]) == set(d.ignored_scaffold_category_names())
    assert all(predicate_map.values())
    assert all(d.scaffold_category_results().values())
    assert d.compact_excerpt('\n'.join([
        '<p><em>2026-06-25 12:00 +00:00</em></p>',
        '<!-- collab:content-only; do-not-execute -->',
        'Visible text.',
    ])) == 'Visible text.'
    assert d.compact_excerpt('- [x] **pe:** [execute] Stable item text.') == (
        '- [ ] **pe:** [execute] Stable item text.'
    )


def test_handoff_shape() -> None:
    from commands.collab.engine import handoff_shape as h

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

    effort = 'EFFORT OVERRIDE: medium — coherence-risk: direct test'
    comment = h.effort_override_metadata_comment(effort)
    assert comment.startswith('<!-- collab:effort-override b64:')
    assert h.render_content_for_transcript(effort + '\nkeep') == [comment, 'keep']

    content = """EFFORT OVERRIDE: medium — coherence-risk: direct test

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


def test_normalizers() -> None:
    from commands.collab.engine import normalizers as n

    assert n.normalize_slug('API UX rewrite') == 'api-ux-rewrite'
    assert n.normalize_title('api qa vs ui') == 'API QA vs UI'
    assert n.phase_slug('Action Plan') == 'action-plan'
    assert n.display_title('abcdefghij', limit=5) == 'abcde…'
    assert n.collab_date({'id': '2026-06-04-sample'}) == '2026-06-04'

    assert n.normalize_join_agent_id(' codex ') == 'codex'
    assert n.normalize_join_agent_id('unknown') == 'unknown'
    aborts(lambda: n.normalize_join_agent_id('Unknown'), 'unknown token must be lowercase')
    aborts(lambda: n.normalize_join_agent_id('n/a'), 'literal unknown')

    assert n.normalize_scope_path('commands/collab/engine/registry.py', 'scope') == 'commands/collab/engine/registry.py'
    aborts(lambda: n.normalize_scope_path('/tmp/file', 'scope'), 'repository-relative')
    aborts(lambda: n.normalize_scope_path('tools/../file', 'scope'), 'normalized')

    assert n.path_is_within('commands/collab/engine/registry.py', 'commands/collab/engine')
    assert not n.path_is_within('tools-other/file', 'tools')
    assert n.scope_matches_declared('commands/collab/engine/registry.py', 'commands/collab/engine/*.py')
    assert not n.scope_matches_declared('commands/collab/engine/registry.py', 'commands/agent/**')
    assert n.normalize_touched_paths(['platform/tooling/a.py', 'platform/tooling/a.py', 'platform/tooling/b.py']) == ['platform/tooling/a.py', 'platform/tooling/b.py']

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


def test_participants() -> None:
    from commands.collab.engine import participants as p
    from commands.collab.engine.registry_constants import CALLER_DECLINED_AGENT_ID

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

    data: dict = {}
    p.count_caller_declined_agent_id_write(data, CALLER_DECLINED_AGENT_ID)
    p.count_caller_declined_agent_id_write(data, CALLER_DECLINED_AGENT_ID)
    assert data['identityMetrics']['callerDeclinedAgentIdWrites'] == 2


def test_phase_lifecycle() -> None:
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


def test_registry_constants() -> None:
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
    assert c.ALLOWED_COMPLETION_SUBSTATES == {'execution', 'verification'}
    assert c.ALLOWED_VERIFICATION_SUBSTATES == {'participant', 'seal', 'assessment'}
    assert c.ALLOWED_VERDICT_RESTORE_TARGETS == {'Action Plan', 'Handoff'}
    assert c.DISALLOWED_VERSION_FIELD == 'schemaVersion'
    assert c.DELETED_PATH_MODE == '000000'
    assert c.DELETED_PATH_BLOB == '0' * 40


def test_registry_io() -> None:
    from commands.collab.engine import registry_io as r

    r.REGISTRY_VALIDATOR = None
    aborts(lambda: r._validate_registry({}, None), 'validator not configured')

    validator_calls: list[str | None] = []

    def validator(data, path):
        assert isinstance(data, dict)
        assert isinstance(data.get('collabs'), list)
        assert 'registryRevision' not in data
        validator_calls.append(None if path is None else Path(path).name)

    r.configure_registry_io(validator)

    with tempfile.TemporaryDirectory() as tmp:
        registry = Path(tmp) / 'registry.json'
        collab_id = '2026-06-04-unit-test'
        data = {
            'activeCollabId': collab_id,
            'registryRevision': 9,
            'collabs': [
                {
                    'id': collab_id,
                    'slug': 'unit-test',
                    'sequence': 1,
                }
            ],
        }

        r.save_registry(registry, data)
        saved = json.loads(registry.read_text())
        assert saved['revision'] == 1
        assert saved['eventIndex'] == 1
        assert 'registryRevision' not in saved
        assert validator_calls[-1] == 'registry.json'

        loaded = r.load_registry(registry)
        assert loaded['activeCollabId'] == collab_id
        assert r.resolve_collab(loaded, collab_id)['slug'] == 'unit-test'
        assert r.resolve_collab(loaded, 'unit-test')['id'] == collab_id
        assert r.resolve_collab(loaded, '#1')['id'] == collab_id
        assert r.require_active_collab(loaded)['id'] == collab_id

        events = r.read_revision_events(registry, collab_id)
        assert events[0]['eventType'] == 'registry-write'
        assert events[0]['eventIndex'] == 1
        assert r.read_revision_events(registry, 'missing')[0]['eventType'] == 'legacy-baseline'

        assert r.registry_revision(saved) == 1
        assert r.registry_event_index(saved) == 1
        before = dict(saved, revision=999, eventIndex=999)
        assert not r.registry_has_semantic_change(before, saved)
        after = dict(saved, activeCollabId=None)
        assert r.registry_has_semantic_change(saved, after)

        bootstrap = r.load_registry_or_bootstrap(Path(tmp) / 'missing.json')
        assert bootstrap['activeCollabId'] is None
        assert bootstrap['collabs'] == []

        with r.registry_lock(registry):
            assert registry.with_name('registry.json.lock').exists()

        invalid = Path(tmp) / 'invalid.json'
        invalid.write_text('{not-json')
        aborts(lambda: r.load_registry(invalid), 'registry invalid JSON')


def write_test_roles(roles: Path, *role_keys: str) -> None:
    roles.mkdir()
    for key in role_keys:
        data = {
            'key': key,
            'displayName': key.upper(),
            'concerns': ['test'],
        }
        if key != 'mod':
            data['dimensions'] = ['structure']
        roles.joinpath(f'{key}.json').write_text(json.dumps(data) + '\n')


@contextlib.contextmanager
def pushd(path: Path):
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def base_collab_entry(collab_id: str, transcript: str) -> dict:
    return {
        'id': collab_id,
        'slug': collab_id.split('-', 3)[-1],
        'title': 'Module Isolation',
        'description': 'Module isolation',
        'createdAt': '2026-06-30T00:00:00+00:00',
        'terminal': 'seal',
        'status': 'open',
        'activePhase': 'Audit',
        'moderatorRole': 'mod',
        'reviewerMode': 'last-in-convergent-phases',
        'reviewerOptionalPhases': ['Discussion'],
        'participants': [{'role': 'mod', 'agentId': 'codex'}],
        'turnOrder': ['mod'],
        'transcriptPath': transcript,
        'sequence': 1,
        'archived': False,
        'execution': {},
    }


def write_registry_fixture(registry: Path, entry: dict) -> None:
    registry.write_text(json.dumps({
        'revision': 1,
        'eventIndex': 1,
        'activeCollabId': entry['id'],
        'collabs': [entry],
    }, indent=2) + '\n')


def test_onboarding_commands_join_handler_isolated() -> None:
    from commands.collab.engine import onboarding_commands as o
    from commands.collab.engine.transcript_render import render_initial_transcript

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        roles = root_dir / 'roles'
        write_test_roles(roles, 'mod', 'zz')
        records = root_dir / 'records'
        records.mkdir()
        collab_id = '2026-06-30-onboarding-isolation'
        entry = base_collab_entry(collab_id, f'records/{collab_id}.md')
        transcript = render_initial_transcript(entry['title'], entry, roles, '2026-06-30 00:00 +00:00')
        records.joinpath(f'{collab_id}.md').write_text(transcript)
        registry = root_dir / 'registry.json'
        write_registry_fixture(registry, entry)

        commits: list[tuple[dict, str, Path | None]] = []

        def commit(
            _path: Path,
            data: dict,
            transcript_path: Path,
            rendered: str,
            roles_dir: Path | None = None,
        ) -> None:
            commits.append((json.loads(json.dumps(data)), rendered, roles_dir))
            _path.write_text(json.dumps(data, indent=2) + '\n')
            transcript_path.write_text(rendered)

        old_commit_new = o.commit_new_collab_artifacts
        old_commit = o.commit_registry_and_transcript
        o.commit_new_collab_artifacts = lambda *args, **kwargs: None
        o.commit_registry_and_transcript = commit
        try:
            with pushd(root_dir), contextlib.redirect_stdout(io.StringIO()):
                assert o.join_participants(registry, collab_id, 'zz', 'codex', roles) == 0
        finally:
            o.commit_new_collab_artifacts = old_commit_new
            o.commit_registry_and_transcript = old_commit

        assert commits, 'join handler did not call registry_io commit owner'
        joined = commits[-1][0]['collabs'][0]
        assert {'role': 'zz', 'agentId': 'codex'} in joined['participants']
        assert joined['turnOrder'] == ['mod', 'zz']
        assert commits[-1][2] == roles


def test_field_commands_unset_handler_uses_supplied_roles_dir() -> None:
    from commands.collab.engine import field_commands as f
    from commands.collab.engine.transcript_render import render_initial_transcript

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        roles = root_dir / 'roles'
        write_test_roles(roles, 'mod', 'zz')
        records = root_dir / 'records'
        records.mkdir()
        collab_id = '2026-06-30-field-isolation'
        entry = base_collab_entry(collab_id, f'records/{collab_id}.md')
        entry.update({
            'reviewerRole': 'zz',
            'reviewerMode': 'last-in-convergent-phases',
            'reviewerOptionalPhases': ['Discussion'],
        })
        entry['participants'].append({'role': 'zz', 'agentId': 'codex'})
        records.joinpath(f'{collab_id}.md').write_text(
            render_initial_transcript(entry['title'], entry, roles, '2026-06-30 00:00 +00:00')
        )
        registry = root_dir / 'registry.json'
        write_registry_fixture(registry, entry)
        commits: list[tuple[dict, Path | None]] = []

        def commit(
            _path: Path,
            data: dict,
            transcript_path: Path,
            rendered: str,
            roles_dir: Path | None = None,
        ) -> None:
            commits.append((json.loads(json.dumps(data)), roles_dir))
            _path.write_text(json.dumps(data, indent=2) + '\n')
            transcript_path.write_text(rendered)

        old_commit = f.commit_registry_and_transcript
        f.commit_registry_and_transcript = commit
        try:
            with pushd(root_dir), contextlib.redirect_stdout(io.StringIO()):
                assert f.unset_field(registry, collab_id, 'reviewer', roles) == 0
        finally:
            f.commit_registry_and_transcript = old_commit

        assert commits, 'unset handler did not call registry_io commit owner'
        updated = commits[-1][0]['collabs'][0]
        assert 'reviewerRole' not in updated
        assert {'role': 'zz', 'agentId': 'codex'} in updated['participants']
        assert commits[-1][1] == roles


def test_reactivation_commands_reopen_handler_isolated() -> None:
    from commands.collab.engine import reactivation_commands as r
    from commands.collab.engine.transcript_render import render_initial_transcript

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        roles = root_dir / 'roles'
        write_test_roles(roles, 'mod', 'pe')
        records = root_dir / 'records'
        records.mkdir()
        collab_id = '2026-06-30-reactivation-isolation'
        entry = base_collab_entry(collab_id, f'records/{collab_id}.md')
        entry.update({
            'activePhase': 'Completion',
            'participants': [
                {'role': 'mod', 'agentId': 'codex'},
                {'role': 'pe', 'agentId': 'codex'},
            ],
            'turnOrder': ['pe'],
            'verdict': {
                'outcome': 'failed',
                'restoreTarget': 'Handoff',
                'restoreReason': 'fixture',
            },
        })
        records.joinpath(f'{collab_id}.md').write_text(
            render_initial_transcript(entry['title'], entry, roles, '2026-06-30 00:00 +00:00')
        )
        registry = root_dir / 'registry.json'
        write_registry_fixture(registry, entry)
        invalidations: list[str] = []
        commits: list[dict] = []

        def commit(_path: Path, data: dict, transcript_path: Path, rendered: str) -> None:
            commits.append(json.loads(json.dumps(data)))
            _path.write_text(json.dumps(data, indent=2) + '\n')
            transcript_path.write_text(rendered)

        old_invalidate = r.invalidate_verification_seal
        old_commit = r.commit_registry_and_transcript
        r.invalidate_verification_seal = lambda item, reason: invalidations.append(reason)
        r.commit_registry_and_transcript = commit
        try:
            with pushd(root_dir), contextlib.redirect_stdout(io.StringIO()):
                assert r.reopen_collab(registry, collab_id, 'handoff') == 0
        finally:
            r.invalidate_verification_seal = old_invalidate
            r.commit_registry_and_transcript = old_commit

        reopened = commits[-1]['collabs'][0]
        assert reopened['activePhase'] == 'Handoff'
        assert reopened['status'] == 'open'
        assert 'verdict' not in reopened
        assert invalidations == ['reopened Handoff']


def test_speak_commands_lifecycle_handler_isolated() -> None:
    from commands.collab.engine import speak_commands as s
    from commands.collab.engine.transcript_render import render_initial_transcript

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        roles = root_dir / 'roles'
        write_test_roles(roles, 'mod', 'pe')
        records = root_dir / 'records'
        records.mkdir()
        collab_id = '2026-06-30-speak-isolation'
        entry = base_collab_entry(collab_id, f'records/{collab_id}.md')
        entry['participants'].append({'role': 'pe', 'agentId': 'codex'})
        entry['turnOrder'] = ['mod', 'pe']
        records.joinpath(f'{collab_id}.md').write_text(
            render_initial_transcript(entry['title'], entry, roles, '2026-06-30 00:00 +00:00')
        )
        registry = root_dir / 'registry.json'
        write_registry_fixture(registry, entry)
        commits: list[dict] = []

        def commit(_path: Path, data: dict, transcript_path: Path, rendered: str) -> None:
            commits.append(json.loads(json.dumps(data)))
            _path.write_text(json.dumps(data, indent=2) + '\n')
            transcript_path.write_text(rendered)

        old_commit = s.commit_registry_and_transcript
        s.commit_registry_and_transcript = commit
        try:
            with pushd(root_dir), contextlib.redirect_stdout(io.StringIO()):
                assert s.speak_lifecycle(registry, collab_id, ['mod', 'pe']) == 0
        finally:
            s.commit_registry_and_transcript = old_commit

        assert commits[-1]['collabs'][0]['activePhase'] == 'Discussion'


def test_seal_verdict_companion() -> None:
    from commands.collab.engine import seal_verification_logic as sv
    from commands.collab.engine.seal_verification_render import seal_write

    assert callable(sv.build_seal_verdict_companion)
    assert callable(seal_write)

    entry = {
        'id': '2026-06-10-verdict-test',
        'verificationSeal': {
            'observedRevision': 11,
            'executionSignature': 'execution-digest-1',
            'contentDigest': 'content-digest-1',
            'pathDigests': {'tools/a.py': {'mode': '100644', 'blob': 'a' * 40}},
            'sealedAt': '2026-06-10T18:00:00+02:00',
            'sealedBy': 'pa',
            'stale': False,
        },
        'verdict': {'outcome': 'success'},
    }

    companion = sv.build_seal_verdict_companion(entry)
    assert companion['authoritative'] is False
    assert companion['authority'] == 'verificationSeal'
    assert companion['closeGate'] == 'verificationSeal'
    assert companion['observedRevision'] == 11
    assert companion['executionDigest'] == 'execution-digest-1'
    assert companion['contentDigest'] == 'content-digest-1'
    assert sv.seal_verdict_companion_status(entry, companion)['current'] is True

    for key, value in (
        ('observedRevision', 10),
        ('executionDigest', 'execution-digest-2'),
        ('contentDigest', 'content-digest-2'),
        ('pathDigests', {'tools/a.py': {'mode': '100644', 'blob': 'b' * 40}}),
        ('verdict', {'outcome': 'failed'}),
    ):
        edited = dict(companion)
        edited[key] = value
        status = sv.seal_verdict_companion_status(entry, edited)
        assert status['current'] is False, (key, status)
        assert 'mismatch' in status['reason'], status

    assert sv.seal_verdict_companion_status(entry, None)['current'] is False
    aborts(lambda: sv.build_seal_verdict_companion({'id': 'missing-seal'}), 'requires verificationSeal')



def test_registry_validation_module() -> None:
    from commands.collab.engine import registry_validation as rv

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        roles = tmp_path / 'roles'
        roles.mkdir()
        for role in ('mod', 'pe'):
            data = {
                'key': role,
                'displayName': role.upper(),
                'concerns': ['test'],
            }
            if role != 'mod':
                data['dimensions'] = ['structure']
            (roles / f'{role}.json').write_text(json.dumps(data) + '\n')

        valid = {
            'revision': 1,
            'eventIndex': 1,
            'activeCollabId': '2026-06-26-validation-module',
            'collabs': [{
                'id': '2026-06-26-validation-module',
                'slug': 'validation-module',
                'title': 'Validation Module',
                'description': 'Validation module',
                'createdAt': '2026-06-26T00:00:00+02:00',
                'terminal': 'seal',
                'status': 'open',
                'activePhase': 'Audit',
                'moderatorRole': 'mod',
                'participants': [
                    {'role': 'mod', 'agentId': 'codex'},
                    {'role': 'pe', 'agentId': 'codex'},
                ],
                'turnOrder': ['mod', 'pe'],
                'transcriptPath': 'records/2026-06-26-validation-module.md',
                'sequence': 1,
                'archived': False,
            }],
        }
        rv.validate_registry(valid, tmp_path / 'registry.json', roles)

        duplicate = json.loads(json.dumps(valid))
        duplicate['collabs'][0]['turnOrder'] = ['pe', 'pe']
        aborts(lambda: rv.validate_registry(duplicate, tmp_path / 'registry.json', roles), 'turnOrder must not contain duplicates')

        missing_role = json.loads(json.dumps(valid))
        missing_role['collabs'][0]['participants'].append({'role': 'ghost', 'agentId': 'codex'})
        missing_role['collabs'][0]['turnOrder'].append('ghost')
        aborts(lambda: rv.validate_registry(missing_role, tmp_path / 'registry.json', roles), 'participants role file unreadable for ghost')


def test_effort_module() -> None:
    from commands.collab.engine import effort as e

    defaults = {
        'levels': {'low': 'simple pass', 'medium': 'needs judgment'},
        'matrix': {'Audit': {'pe': 'low', 'tw': None}},
    }
    assert e.effort_value(defaults, 'Audit', 'pe') == 'low'
    assert e.effort_value(defaults, 'Audit', 'pa') == 'medium'
    assert e.effort_phrase(defaults, 'medium', 'Audit', 'pe') == 'needs judgment'
    assert e.effort_line(defaults, 'Audit', 'pe') == 'EFFORT: low for pe in Audit — next-turn recommendation; simple pass.'
    assert e.normalize_rendered_effort_cell('`low`') == 'low'
    assert e.normalize_rendered_effort_cell('— not on roster') is None

    table = '\n'.join([
        '# Agent model',
        '',
        '## Per-speak-turn effort',
        '',
        '_generated; do not edit_',
        '',
        '| Phase | pe | tw |',
        '|---|---|---|',
        '| Audit | `low` | — not on roster |',
        '',
    ])
    with tempfile.TemporaryDirectory() as tmp:
        model = Path(tmp) / 'agent-model.md'
        model.write_text(table)
        assert e.rendered_effort_drift_items(defaults, model) == []

        drift = Path(tmp) / 'drift.md'
        drift.write_text(table.replace('`low`', '`medium`'))
        failures = e.rendered_effort_drift_items(defaults, drift)
        assert failures and 'role pe, phase/row Audit' in failures[0]

def test_role_file_readability() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        roles = tmp_path / 'roles'
        roles.mkdir()
        (roles / 'mod.json').write_text(json.dumps({
            'key': 'mod',
            'displayName': 'Moderator',
            'concerns': ['coordination'],
        }) + '\n')

        spec = importlib.util.spec_from_file_location(
            'registry_under_test',
            Path(root) / 'commands/collab/engine/registry.py',
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        module.DEFAULT_ROLES_DIR = roles

        registry = {
            'revision': 1,
            'activeCollabId': '2026-05-19-role-file-check',
            'collabs': [{
                'id': '2026-05-19-role-file-check',
                'slug': 'role-file-check',
                'title': 'Role File Check',
                'description': 'Role file check',
                'status': 'open',
                'activePhase': 'Audit',
                'moderatorRole': 'mod',
                'participants': [
                    {'role': 'mod', 'agentId': 'codex'},
                    {'role': 'ghost', 'agentId': 'codex'},
                ],
                'turnOrder': ['ghost'],
                'transcriptPath': 'records/2026-05-19-role-file-check.md',
                'archived': False,
            }],
        }

        try:
            module.validate_registry(registry, tmp_path / 'registry.json')
        except SystemExit as exc:
            message = str(exc)
            assert 'participants role file unreadable for ghost' in message, message
            assert 'roles/ghost.json' in message, message
        else:
            raise AssertionError('missing participant role file was accepted')


for test in (
    test_digests,
    test_git_repo,
    test_diff_scaffold_categories,
    test_handoff_shape,
    test_normalizers,
    test_participants,
    test_phase_lifecycle,
    test_registry_constants,
    test_registry_io,
    test_onboarding_commands_join_handler_isolated,
    test_field_commands_unset_handler_uses_supplied_roles_dir,
    test_reactivation_commands_reopen_handler_isolated,
    test_speak_commands_lifecycle_handler_isolated,
    test_seal_verdict_companion,
    test_registry_validation_module,
    test_effort_module,
    test_role_file_readability,
):
    test()

print('OK: collab engine modules are directly exercised')
PY
