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

from commands.collab.engine import git_repo as g


def run(argv, cwd):
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def aborts(fn, contains):
    try:
        fn()
    except SystemExit as exc:
        assert contains in str(exc), str(exc)
    else:
        raise AssertionError(f'expected abort containing {contains!r}')


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

print('OK: git_repo module is directly exercised')
PY
