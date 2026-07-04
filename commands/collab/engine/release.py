#!/usr/bin/env python3
"""Tag and release planning helpers for explicit collab release routes.

The module owns release-domain behavior. registry.py remains a facade that
parses arguments and forwards here.
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
        die(f'RELEASE-GIT-STATE: git status failed: {detail}')
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        rendered = ', '.join(dirty)
        die(f'RELEASE-GIT-STATE: work tree must be clean before tag/release: {rendered}')


def _head_commit(repo_root: Path) -> str:
    timestamp = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    commit = current_head_commit(timestamp, repo_root)
    if commit is None:
        die('RELEASE-GIT-STATE: cannot resolve HEAD at or before release planning time')
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
        die(f'RELEASE-TAG: tag creation failed: {detail}')


def _push_tag(repo_root: Path, tag_name: str) -> None:
    result = _run_git(repo_root, ['push', 'origin', tag_name])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'RELEASE-PUSH: tag push failed: {detail}')


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
            die(f'RELEASE-TAG: tag already exists: {resolved_tag}')
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


def _print_release_plan(
    *,
    entry: dict,
    repo_root: Path,
    tag_name: str,
    confirm: bool,
    push: bool,
    direct_merge: bool,
    github_release: bool,
    auto_fire: bool,
    head: str,
) -> None:
    mode = 'confirm' if confirm else 'dry-run'
    direct_merge_state = 'declared, not wired (v2)' if direct_merge else 'disabled'
    github_release_state = 'declared, not wired (v2)' if github_release else 'disabled'
    auto_fire_state = 'enabled for wired tag/push actions' if auto_fire else 'disabled'
    print(f'MODE: {mode}')
    print(f'TARGET: {entry["id"]}')
    print(f'WORK_REPO: {repo_root}')
    print(f'HEAD: {head}')
    print(f'TAG: {tag_name}')
    print('DEFAULT_FLOW: open release PR and stop declared, not wired (v2)')
    print(f'DIRECT_MERGE: {direct_merge_state}')
    print(f'GITHUB_RELEASE: {github_release_state}')
    print(f'AUTO_FIRE: {auto_fire_state}')
    print(f'PUSH: {"enabled" if push else "disabled"}')
    print('CHANGELOG: deferred; doc/write-changelog is not present in this repo')


def release_collab(
    path: Path,
    target: str | None,
    tag_name: str | None = None,
    confirm: bool = False,
    push: bool = False,
    direct_merge: bool = False,
    github_release: bool = False,
    auto_fire: bool = False,
    caller_role: str | None = None,
) -> int:
    del caller_role
    with registry_lock(path):
        data = load_registry(path)
        entry = _target_entry(data, target)
        repo_root = work_repo_root(entry)
        _require_clean_work_tree(repo_root)
        resolved_tag = tag_name or _default_tag_name(entry)
        tag_exists = _tag_exists(repo_root, resolved_tag)
        head = _head_commit(repo_root)

    _print_release_plan(
        entry=entry,
        repo_root=repo_root,
        tag_name=resolved_tag,
        confirm=confirm,
        push=push,
        direct_merge=direct_merge,
        github_release=github_release,
        auto_fire=auto_fire,
        head=head,
    )
    if not confirm:
        print('NEXT: Rerun with --confirm for release execution; --auto-fire is required for any outward release action.')
        return 0
    if not auto_fire:
        print('GATED: --confirm recorded, but no release action ran because --auto-fire is disabled.')
        return 0
    if not tag_exists:
        _create_annotated_tag(repo_root, resolved_tag, _release_message(entry, resolved_tag))
        print(f'CREATED: tag {resolved_tag}')
    else:
        print(f'EXISTS: tag {resolved_tag}')
    if push:
        _push_tag(repo_root, resolved_tag)
        print(f'PUSHED: tag {resolved_tag}')
    print('STOP: release PR, direct merge, and GitHub release are declared, not wired (v2); tag/push execution completed if requested.')
    return 0
