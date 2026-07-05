#!/usr/bin/env python3
"""Git-tag helper for completed collabs.

The module owns tag-domain behavior. registry.py remains a facade that parses
arguments and forwards here.
"""
from __future__ import annotations

import subprocess
import datetime as dt
from pathlib import Path

from commands.collab.engine.errors import die
from commands.collab.engine.git_repo import current_head_commit, work_repo_root
from commands.collab.engine.registry_io import load_registry, registry_lock, require_active_collab, resolve_collab


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ['git', '-C', str(repo_root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result


def _require_clean_work_tree(repo_root: Path) -> None:
    result = _run_git(repo_root, ['status', '--porcelain'])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'TAG-GIT-STATE: git status failed: {detail}')
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        rendered = ', '.join(dirty)
        die(f'TAG-GIT-STATE: work tree must be clean before tagging: {rendered}')


def _head_commit(repo_root: Path) -> str:
    timestamp = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    commit = current_head_commit(timestamp, repo_root)
    if commit is None:
        die('TAG-GIT-STATE: cannot resolve HEAD at or before tag planning time')
    return commit


def _tag_exists(repo_root: Path, tag_name: str) -> bool:
    result = _run_git(repo_root, ['rev-parse', '--verify', '--quiet', f'refs/tags/{tag_name}'])
    return result.returncode == 0


def _default_tag_name(entry: dict) -> str:
    slug = entry.get('slug') or entry.get('id') or 'collab'
    return f'collab/{slug}'


def _target_entry(data: dict, target: str | None) -> dict:
    return resolve_collab(data, target) if target else require_active_collab(data)


def _create_annotated_tag(repo_root: Path, tag_name: str, message: str) -> None:
    result = _run_git(repo_root, ['tag', '-a', tag_name, '-m', message])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'TAG-CREATE: tag creation failed: {detail}')


def _push_tag(repo_root: Path, tag_name: str) -> None:
    result = _run_git(repo_root, ['push', 'origin', tag_name])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'TAG-PUSH: tag push failed: {detail}')


def _release_message(entry: dict, tag_name: str) -> str:
    return f'{entry.get("title", entry.get("id", "collab"))} ({tag_name})'


def _print_tag_plan(
    *,
    entry: dict,
    repo_root: Path,
    tag_name: str,
    confirm: bool,
    push: bool,
    head: str,
) -> None:
    mode = 'confirm' if confirm else 'dry-run'
    print(f'MODE: {mode}')
    print(f'TARGET: {entry["id"]}')
    print(f'WORK_REPO: {repo_root}')
    print(f'HEAD: {head}')
    print(f'TAG: {tag_name}')
    print('ACTION: create annotated local git tag')
    print(f'PUSH: {"enabled" if push else "disabled"}')


def tag_collab(
    path: Path,
    target: str | None,
    tag_name: str | None = None,
    confirm: bool = False,
    push: bool = False,
    caller_role: str | None = None,
) -> int:
    del caller_role
    with registry_lock(path):
        data = load_registry(path)
        entry = _target_entry(data, target)
        repo_root = work_repo_root(entry)
        _require_clean_work_tree(repo_root)
        resolved_tag = tag_name or _default_tag_name(entry)
        if _tag_exists(repo_root, resolved_tag):
            die(f'TAG-EXISTS: tag already exists: {resolved_tag}')
        head = _head_commit(repo_root)

    _print_tag_plan(
        entry=entry,
        repo_root=repo_root,
        tag_name=resolved_tag,
        confirm=confirm,
        push=push,
        head=head,
    )
    if not confirm:
        print('NEXT: Rerun with --confirm to create the local tag.')
        return 0

    _create_annotated_tag(repo_root, resolved_tag, _release_message(entry, resolved_tag))
    print(f'CREATED: tag {resolved_tag}')
    if push:
        _push_tag(repo_root, resolved_tag)
        print(f'PUSHED: tag {resolved_tag}')
    return 0
