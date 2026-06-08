"""Content and path digest computation and signatures; does not own git policy or registry state."""
# Tests: full-body block detection and strip, write-scope signature stability, execution-content
#        signature invalidation on path/status change, content digest for worktree and ref paths.
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from commands.collab.engine.errors import die
from commands.collab.engine.registry_constants import (
    DELETED_PATH_BLOB,
    DELETED_PATH_MODE,
    FULL_BODY_SUMMARY_LINE,
)

DETAILS_OPEN_RE = re.compile(r'^<details(?:\s+[^>]*)?>(?:<summary>[^<]*</summary>)?$')
DETAILS_CLOSE_RE = re.compile(r'^</details>$')

def details_block_end(lines: list[str], start: int, context: str) -> int:
    depth = 1
    line_index = start + 1
    while line_index < len(lines):
        stripped = lines[line_index].strip()
        if DETAILS_OPEN_RE.match(stripped):
            depth += 1
        elif DETAILS_CLOSE_RE.match(stripped):
            depth -= 1
            if depth == 0:
                return line_index + 1
        line_index += 1
    die(f'transcript details block not closed in {context}')

def is_full_body_block_start(lines: list[str], index: int) -> bool:
    return (
        DETAILS_OPEN_RE.match(lines[index].strip()) is not None
        and index + 1 < len(lines)
        and lines[index + 1].strip() == FULL_BODY_SUMMARY_LINE
    )

def strip_managed_full_body_lines(lines: list[str], context: str) -> list[str]:
    stripped_lines: list[str] = []
    index = 0
    while index < len(lines):
        if is_full_body_block_start(lines, index):
            index = details_block_end(lines, index, context)
            continue
        stripped_lines.append(lines[index])
        index += 1
    return stripped_lines

def managed_full_body_blocks(transcript: str) -> list[str]:
    lines = transcript.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if is_full_body_block_start(lines, index):
            end = details_block_end(lines, index, 'managed full-body block')
            blocks.append('\n'.join(lines[index:end]))
            index = end
            continue
        index += 1
    return blocks

def full_body_signature_for_transcript(transcript: str) -> str:
    payload = json.dumps(managed_full_body_blocks(transcript), ensure_ascii=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()

def rendered_transcript_without_full_bodies(transcript: str) -> str:
    lines = strip_managed_full_body_lines(transcript.splitlines(), 'rendered transcript')
    return '\n'.join(lines) + ('\n' if transcript.endswith('\n') else '')

def participant_write_scope_signature(entry: dict, role: str) -> str:
    role_handoff = entry.get('handoff', {}).get('roles', {}).get(role, {})
    scope = role_handoff.get('writeScope', [])
    if not isinstance(scope, list):
        scope = []
    normalized = sorted(str(item) for item in scope if isinstance(item, str) and item.strip())
    payload = json.dumps(normalized, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()

def participant_execution_signature(entry: dict, role: str) -> str:
    """Signature of the executed content a participant's verification certifies:
    the role's execution status, validation result, touched paths, and commits.
    Used to invalidate a completed verification when that content later changes --
    a re-execution, or a provenance repair that repointed the commit -- so a stale
    verification cannot ride through to a success seal."""
    state = entry.get('execution', {}).get(role, {})
    if not isinstance(state, dict):
        state = {}
    payload = {
        'status': state.get('status'),
        'validationResult': state.get('validationResult'),
        'touchedPaths': sorted(
            str(item) for item in state.get('touchedPaths', []) if isinstance(item, str)
        ),
        'commits': sorted(
            str(item) for item in state.get('commits', []) if isinstance(item, str)
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()

def execution_identity(role: str, date: str) -> str:
    suffix = re.sub(r'[^0-9A-Za-z]+', '-', date).strip('-').lower()
    return f'{role}-{suffix or "execution"}'

def active_execution_entries(entry: dict) -> list[dict]:
    rows: list[dict] = []
    for role, state in sorted(entry.get('execution', {}).items()):
        if not isinstance(state, dict):
            continue
        row = {
            'role': role,
            'entryId': state.get('entryId') or execution_identity(role, state.get('date', 'execution')),
            'status': state.get('status'),
            'date': state.get('date'),
            'validationResult': state.get('validationResult'),
            'validationScope': state.get('validationScope'),
            'touchedPaths': list(state.get('touchedPaths', [])),
        }
        commits = state.get('commits', [])
        if commits:
            row['commits'] = list(commits)
        content_digest = state.get('contentDigest')
        if isinstance(content_digest, str) and content_digest:
            row['contentDigest'] = content_digest
        path_digests = state.get('pathDigests')
        if isinstance(path_digests, dict):
            row['pathDigests'] = path_digests
        if state.get('agentId'):
            row['agentId'] = state.get('agentId')
        rows.append(row)
    return rows

def carried_execution_entries(entry: dict) -> list[dict]:
    coverage = entry.get('reopenCoverage')
    if not isinstance(coverage, dict):
        return []
    entries = coverage.get('executionEntries', [])
    if not isinstance(entries, list):
        return []
    return [item for item in entries if isinstance(item, dict)]

def path_digest_at_ref(work_repo: Path, ref: str, path: str) -> dict[str, str] | None:
    result = subprocess.run(
        ['git', '-C', str(work_repo), 'ls-tree', ref, '--', path],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
        die(f'SEAL-CONTENT-INCOMPLETE: carried coverage digest failed for {path}: {detail}')
    line = result.stdout.strip()
    if not line:
        return None
    meta, _tab, _name = line.partition('\t')
    parts = meta.split()
    if len(parts) < 3 or parts[1] != 'blob':
        return None
    return {'mode': parts[0], 'blob': parts[2]}

def content_digest_from_path_digests(path_digests: dict[str, dict[str, str]]) -> str:
    canonical = json.dumps(path_digests, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

def valid_carried_execution_entries(entry: dict, ref: str = 'HEAD') -> list[dict]:
    from commands.collab.engine.git_repo import work_repo_root

    rows: list[dict] = []
    repo_root = work_repo_root(entry)
    active_paths = {
        item
        for row in active_execution_entries(entry)
        for item in row.get('touchedPaths', [])
        if isinstance(item, str)
    }
    for carried in carried_execution_entries(entry):
        path_digests = carried.get('pathDigests')
        if not isinstance(path_digests, dict):
            continue
        valid_paths: list[str] = []
        valid_digests: dict[str, dict[str, str]] = {}
        for item in carried.get('touchedPaths', []):
            if not isinstance(item, str) or item in active_paths:
                continue
            expected = path_digests.get(item)
            if not isinstance(expected, dict):
                continue
            current = path_digest_at_ref(repo_root, ref, item)
            if current is None:
                continue
            normalized_expected = {
                'mode': str(expected.get('mode', '')),
                'blob': str(expected.get('blob', '')),
            }
            if current != normalized_expected:
                continue
            valid_paths.append(item)
            valid_digests[item] = current
        if not valid_paths:
            continue
        row = {
            key: value
            for key, value in carried.items()
            if key not in {'touchedPaths', 'pathDigests', 'contentDigest'}
        }
        row['touchedPaths'] = valid_paths
        row['pathDigests'] = valid_digests
        row['contentDigest'] = content_digest_from_path_digests(valid_digests)
        row['carriedFromReopen'] = True
        rows.append(row)
    return rows

def execution_coverage_entries(entry: dict) -> list[dict]:
    return [*active_execution_entries(entry), *valid_carried_execution_entries(entry)]

def execution_signature(entry: dict) -> str:
    entries = execution_coverage_entries(entry)
    encoded = json.dumps(entries, sort_keys=True, separators=(',', ':'))
    return base64.urlsafe_b64encode(encoded.encode()).decode().rstrip('=')

def validation_scopes_for_execution(entry: dict) -> list[str]:
    scopes: list[str] = []
    for state in execution_coverage_entries(entry):
        scope = state.get('validationScope') if isinstance(state, dict) else None
        if isinstance(scope, str) and scope not in scopes:
            scopes.append(scope)
    return scopes

def touched_paths_for_execution(entry: dict) -> list[str]:
    touched: list[str] = []
    for state in execution_coverage_entries(entry):
        for item in state.get('touchedPaths', []):
            if isinstance(item, str) and item not in touched:
                touched.append(item)
    return touched

def content_digest_for_touched_paths(work_repo: Path, ref: str, touched_paths: list[str]) -> dict:
    from commands.collab.engine.git_repo import git_committed_deletion_paths, working_tree_path_exists

    path_digests: dict[str, dict[str, str]] = {}
    for path in sorted(dict.fromkeys(touched_paths)):
        if ref == 'WORKTREE':
            if not working_tree_path_exists(path, work_repo):
                if path in git_committed_deletion_paths([path], work_repo):
                    path_digests[path] = {'mode': DELETED_PATH_MODE, 'blob': DELETED_PATH_BLOB}
                    continue
                die(f'SEAL-CONTENT-INCOMPLETE: touchedPath missing in worktree {work_repo}: {path}')
            mode_result = subprocess.run(
                ['git', '-C', str(work_repo), 'ls-files', '-s', '--', path],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if mode_result.returncode != 0:
                detail = mode_result.stderr.strip() or mode_result.stdout.strip() or 'unknown git error'
                die(f'SEAL-CONTENT-INCOMPLETE: content digest mode failed for {path}: {detail}')
            mode_line = mode_result.stdout.strip()
            if mode_line:
                mode = mode_line.split()[0]
            else:
                mode = '100755' if os.access(work_repo / path, os.X_OK) else '100644'
            blob_result = subprocess.run(
                ['git', '-C', str(work_repo), 'hash-object', '--', path],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if blob_result.returncode != 0 or not blob_result.stdout.strip():
                detail = blob_result.stderr.strip() or blob_result.stdout.strip() or 'unknown git error'
                die(f'SEAL-CONTENT-INCOMPLETE: content digest blob failed for {path}: {detail}')
            path_digests[path] = {'mode': mode, 'blob': blob_result.stdout.strip()}
        else:
            result = subprocess.run(
                ['git', '-C', str(work_repo), 'ls-tree', ref, '--', path],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or 'unknown git error'
                die(f'SEAL-CONTENT-INCOMPLETE: content digest failed for {path}: {detail}')
            line = result.stdout.strip()
            if not line:
                if path in git_committed_deletion_paths([path], work_repo):
                    path_digests[path] = {'mode': DELETED_PATH_MODE, 'blob': DELETED_PATH_BLOB}
                    continue
                die(f'SEAL-CONTENT-INCOMPLETE: touchedPath missing at {ref} in {work_repo}: {path}')
            meta, _tab, _name = line.partition('\t')
            parts = meta.split()
            if len(parts) < 3 or parts[1] != 'blob':
                die(f'SEAL-CONTENT-INCOMPLETE: touchedPath is not a blob at {ref} in {work_repo}: {path}')
            path_digests[path] = {'mode': parts[0], 'blob': parts[2]}
    canonical = json.dumps(path_digests, sort_keys=True, separators=(',', ':'))
    return {
        'contentDigest': content_digest_from_path_digests(path_digests),
        'pathDigests': path_digests,
    }
