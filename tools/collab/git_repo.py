"""Git subprocess reads: head commit, execution commits, content-at-ref; does not own seal policy."""
# Tests: head-commit resolution, execution-commits-for-paths mapping, staged/unstaged path
#        detection, work-repo root enclosure check, deletion-path identification.
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tools.collab.errors import die
from tools.collab.normalizers import parse_execution_datetime
from tools.collab.registry_io import current_registry_project_id, root_project_id

ROOT = Path(__file__).resolve().parents[2]
RESOLVED_WORK_REPO_ROOT: Path | None = None


def set_resolved_work_repo_root(path: Path | None) -> None:
    global RESOLVED_WORK_REPO_ROOT
    RESOLVED_WORK_REPO_ROOT = path

def assert_work_repo_not_framework_for_external_project(repo_root: Path, label: str) -> None:
    # Refuse to bind the framework checkout as a collab's work tree when the
    # collab's own project root lives inside a *different* git work tree -- that
    # is the external-repo trap where sealing would silently certify ROOT instead
    # of the repo the work actually landed in. The discriminator is git-tree
    # containment, not the project marker id: a project root that is not inside
    # any git tree (a fresh dir or the test-harness temp dir) has no other tree to
    # seal, so ROOT is the legitimate fallback and must not abort here.
    if repo_root.resolve() != ROOT.resolve():
        return
    base = RESOLVED_WORK_REPO_ROOT if RESOLVED_WORK_REPO_ROOT is not None else ROOT
    enclosing = enclosing_git_tree(Path(base))
    if enclosing is not None and enclosing.resolve() != ROOT.resolve():
        die(
            f'{label} resolves to framework checkout {ROOT}; the collab project '
            f'root {base} is inside a different git work tree ({enclosing}); '
            "refusing to bind the framework checkout as this collab's work tree. "
            f'Bind the intended tree: pass --work-repo {enclosing} at init, or run '
            f'/collab set <target> work-repo {enclosing}'
        )

def resolve_git_work_tree(raw: str, label: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        die(f'{label} must be an absolute path: {raw}')
    probe = subprocess.run(
        ['git', '-C', str(path), 'rev-parse', '--show-toplevel'],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode != 0 or not probe.stdout.strip():
        die(f'{label} must be a git work tree: {raw}')
    return Path(probe.stdout.strip())

def enclosing_git_tree(path: Path) -> Path | None:
    """Return the git work tree toplevel containing *path*, or None when the path
    is not inside any git work tree. Unlike resolve_git_work_tree this never
    aborts: callers needing only a best-effort default (the init binding) can fall
    back, while gates that genuinely require git still go through
    resolve_git_work_tree."""
    probe = subprocess.run(
        ['git', '-C', str(path), 'rev-parse', '--show-toplevel'],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode != 0 or not probe.stdout.strip():
        return None
    return Path(probe.stdout.strip())

def default_init_work_repo_root() -> Path:
    # Bind the work repo to the git work tree enclosing the invocation's project
    # root, so a collab started inside an external repo auto-binds to that repo's
    # toplevel (the seal then gates against it, never the framework checkout).
    # When the project root is not inside any git work tree -- a fresh planning
    # directory or the test-harness temp dir -- fall back to the framework
    # checkout instead of aborting: git is still enforced later by work_repo_root
    # at execution-commit capture and seal time, so init must not hard-fail on a
    # not-yet-git directory (doing so makes /collab init unusable outside a repo).
    base = RESOLVED_WORK_REPO_ROOT if RESOLVED_WORK_REPO_ROOT is not None else ROOT
    enclosing = enclosing_git_tree(Path(base))
    return enclosing if enclosing is not None else ROOT

def work_repo_root(entry: dict) -> Path:
    """Resolve the git work tree that holds a collab's executed deliverables.

    Collabs whose execution targets a repository other than the framework
    checkout declare it via the registry ``workRepo`` field; the seal git-state
    and drift gates, and execution-commit capture, then operate on that tree.
    Missing bindings are allowed only for framework-project legacy records.
    External-project records must carry an explicit binding so execution,
    participant verification, and seal gates cannot silently certify ROOT.
    A declared-but-invalid ``workRepo`` is a hard error rather than a silent
    fall back to the wrong tree.
    """
    raw = entry.get('workRepo')
    if not isinstance(raw, str) or not raw.strip():
        current_project = current_registry_project_id()
        framework_project = root_project_id()
        if current_project is not None and framework_project is not None and current_project != framework_project:
            die(
                f'workRepo missing for external project {current_project}; '
                f'run /collab set {entry.get("id", "<target>")} work-repo <path>'
            )
        return ROOT
    repo_root = resolve_git_work_tree(raw, 'workRepo')
    assert_work_repo_not_framework_for_external_project(repo_root, 'workRepo')
    return repo_root

def git_commit_paths(ref: str, repo_root: Path = ROOT) -> set[str] | None:
    try:
        probe = subprocess.run(
            ['git', '-C', str(repo_root), 'cat-file', '-e', f'{ref}^{{commit}}'],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return None
    if probe.returncode != 0:
        return None
    result = subprocess.run(
        ['git', '-C', str(repo_root), 'show', '--name-only', '--format=', ref],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}

def git_latest_commit_for_path(path: str, repo_root: Path, execution_date: str) -> str | None:
    result = subprocess.run(
        ['git', '-C', str(repo_root), 'log', '-1', '--format=%H', '--', path],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'execution commit capture failed for touchedPath {path}: {detail}')
    commit = result.stdout.strip()
    if not commit:
        return None
    date_result = subprocess.run(
        ['git', '-C', str(repo_root), 'show', '-s', '--format=%cI', commit],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if date_result.returncode != 0:
        detail = date_result.stderr.strip() or date_result.stdout.strip() or 'unknown git error'
        die(f'execution commit date capture failed for touchedPath {path}: {detail}')
    execution_time = parse_execution_datetime(execution_date)
    commit_time = parse_execution_datetime(date_result.stdout.strip())
    if execution_time is not None and commit_time is not None and commit_time > execution_time:
        return None
    return commit

def execution_commits_for_touched_paths(date: str, repo_root: Path, touched_paths: list[str]) -> list[str]:
    if not touched_paths:
        head_commit = current_head_commit(date, repo_root)
        return [head_commit] if head_commit is not None else []
    commits: list[str] = []
    missing: list[str] = []
    for path in touched_paths:
        commit = git_latest_commit_for_path(path, repo_root, date)
        if commit is None:
            if not working_tree_path_exists(path, repo_root):
                missing.append(path)
            continue
        if commit not in commits:
            commits.append(commit)
    if missing:
        die(
            'execution commit capture failed: touchedPath(s) have no committed provenance in '
            f'{repo_root}: {json.dumps(missing, separators=(",", ":"))}'
        )
    return commits

def git_index_or_staged_paths(paths: list[str], repo_root: Path = ROOT) -> set[str]:
    if not paths:
        return set()
    commands = [
        ['git', '-C', str(repo_root), 'ls-files', '--', *paths],
        ['git', '-C', str(repo_root), 'diff', '--cached', '--name-only', '--', *paths],
    ]
    found: set[str] = set()
    for command in commands:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
            die(f'SEAL-GIT-STATE: git state check failed: {detail}')
        found.update(line.strip() for line in result.stdout.splitlines() if line.strip())
    return found

def git_staged_paths(paths: list[str], repo_root: Path = ROOT) -> set[str]:
    if not paths:
        return set()
    result = subprocess.run(
        ['git', '-C', str(repo_root), 'diff', '--cached', '--name-only', '--', *paths],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'SEAL-GIT-STATE: git staged check failed: {detail}')
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}

def git_committed_deletion_paths(paths: list[str], repo_root: Path = ROOT) -> set[str]:
    if not paths:
        return set()
    result = subprocess.run(
        ['git', '-C', str(repo_root), 'log', '--diff-filter=D', '--name-only', '--format=', '--', *paths],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'SEAL-GIT-STATE: git committed deletion check failed: {detail}')
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}

def git_unstaged_paths(paths: list[str], repo_root: Path = ROOT) -> set[str]:
    if not paths:
        return set()
    result = subprocess.run(
        ['git', '-C', str(repo_root), 'diff', '--name-only', '--', *paths],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'SEAL-GIT-STATE: git unstaged check failed: {detail}')
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}

def working_tree_path_exists(path: str, repo_root: Path = ROOT) -> bool:
    return os.path.lexists(repo_root / path)

def assert_execution_touched_paths_in_git_state(entry: dict) -> None:
    from tools.collab.digests import touched_paths_for_execution

    touched = touched_paths_for_execution(entry)
    if not touched:
        return
    repo_root = work_repo_root(entry)
    in_git = git_index_or_staged_paths(touched, repo_root)
    staged = git_staged_paths(touched, repo_root)
    unstaged = git_unstaged_paths(touched, repo_root)
    committed_deletions = git_committed_deletion_paths(touched, repo_root)
    invalid: list[str] = []
    for path in touched:
        if path in staged or path in unstaged:
            invalid.append(path)
            continue
        if path in in_git:
            continue
        if path in committed_deletions and not working_tree_path_exists(path, repo_root):
            continue
        invalid.append(path)
    invalid = sorted(invalid)
    if invalid:
        die(
            'SEAL-GIT-STATE: implementation not in git; '
            f'unstaged or uncommitted touchedPath(s) in {repo_root}: {json.dumps(invalid, separators=(",", ":"))}'
        )

def assert_touched_paths_recordable_in_work_repo(entry: dict, touched_paths: list[str]) -> None:
    if not touched_paths:
        return
    repo_root = work_repo_root(entry)
    in_git = git_index_or_staged_paths(touched_paths, repo_root)
    committed_deletions = git_committed_deletion_paths(touched_paths, repo_root)
    invalid = sorted(
        path for path in touched_paths
        if (
            path not in in_git
            and not working_tree_path_exists(path, repo_root)
            and not (path in committed_deletions and not working_tree_path_exists(path, repo_root))
        )
    )
    if invalid:
        die(
            'execution touchedPath(s) not found under workRepo '
            f'{repo_root}: {json.dumps(invalid, separators=(",", ":"))}'
        )

def current_head_commit(date: str, repo_root: Path = ROOT) -> str | None:
    result = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', 'HEAD'],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'execution commit capture failed: {detail}')
    commit = result.stdout.strip()
    if not commit:
        die('execution commit capture failed: git rev-parse HEAD returned empty output')
    date_result = subprocess.run(
        ['git', '-C', str(repo_root), 'show', '-s', '--format=%cI', commit],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if date_result.returncode != 0:
        detail = date_result.stderr.strip() or date_result.stdout.strip() or 'unknown git error'
        die(f'execution commit date capture failed: {detail}')
    execution_time = parse_execution_datetime(date)
    commit_time = parse_execution_datetime(date_result.stdout.strip())
    if execution_time is not None and commit_time is not None and commit_time > execution_time:
        return None
    return commit
