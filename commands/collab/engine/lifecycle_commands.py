#!/usr/bin/env python3
"""Record lifecycle status-change command handlers: archive a record and clear it as active (`archive`), reopen a closed record (`open`), close a record after enforcing the execution/issue/seal close gates (`close`), and permanently delete a record with its transcript and contribution store (`delete`). Each (except delete) re-renders the managed header and persists registry + transcript together. The one dependency these write-path commands cannot import without a cycle — the core-owned `commit_registry_and_transcript` two-file write — is injected via `configure_lifecycle_commands`. Does not own the two-file commit implementation, the close-gate predicates, header rendering, or the seal verdict companion writer."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from commands.collab.engine.advisories import print_post_action_advisories
from commands.collab.engine.config_paths import DEFAULT_ROLES_DIR
from commands.collab.engine.contribution_store import contribution_store_path_for_entry
from commands.collab.engine.errors import die
from commands.collab.engine.execution import (
    all_execution_completed,
    completed_execution_unchecked_items,
    issue_terminal,
    seal_terminal,
)
from commands.collab.engine.issue_export import exported_issue_handoff_present
from commands.collab.engine.participants import assert_caller_role, reviewer_backed
from commands.collab.engine.phase_lifecycle import (
    lifecycle_status_notice,
    print_notice_diagnostic,
)
from commands.collab.engine.registry_io import (
    load_registry,
    registry_lock,
    resolve_collab,
    save_registry,
)
from commands.collab.engine.seal_verification import (
    invalidate_seal_on_content_drift,
    successful_verdict,
    write_seal_verdict_companion,
)
from commands.collab.engine.speak_state import next_line_for_state
from commands.collab.engine.transcript_readers import transcript_path_for_entry
from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    render_managed_header_text,
)

_commit_registry_and_transcript: Callable[[Path, dict, Path, str], None] | None = None


def configure_lifecycle_commands(
    *,
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None],
) -> None:
    """Inject the cycle-blocked dependency of the archive/open/close write paths: the core-owned two-file commit."""
    global _commit_registry_and_transcript
    _commit_registry_and_transcript = commit_registry_and_transcript


def _require_commit() -> Callable[[Path, dict, Path, str], None]:
    if _commit_registry_and_transcript is None:
        die('lifecycle commands engine is not configured: commit callback missing')
    return _commit_registry_and_transcript


def archive_collab(
    path: Path,
    target: str,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'archive')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        entry['status'] = 'archived'
        entry['archived'] = True
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        _require_commit()(path, data, transcript_path, rendered)
    notice = lifecycle_status_notice('archived')
    print_post_action_advisories(entry, None, None, notice, next_line_for_state(entry))
    print(entry['id'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def open_collab(path: Path, target: str, caller_role: str | None = None) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'open')
        if entry['status'] == 'archived' or entry.get('archived'):
            die('archived records must be restored before reopening')
        if entry['status'] == 'open':
            print(f'record already open: {entry["id"]}')
            return 0
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        entry['status'] = 'open'
        entry['archived'] = False
        data['activeCollabId'] = entry['id']
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        _require_commit()(path, data, transcript_path, rendered)
    print(entry['id'])
    return 0


def close_collab(
    path: Path,
    target: str,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'close')
        if entry['status'] == 'archived':
            die('record is archived')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        violations = completed_execution_unchecked_items(entry, transcript)
        if violations:
            details = ', '.join(
                f"{item['role']}={item['uncheckedCount']}" for item in violations
            )
            die(
                'close blocked: completed execution has unchecked assigned Action Plan item(s): '
                f'{details}; loop target: Handoff for missing execution evidence'
            )
        if issue_terminal(entry) and entry['activePhase'] == 'Completion':
            if not all_execution_completed(entry):
                die('close blocked: issue terminal requires completed execution')
            if not exported_issue_handoff_present(entry):
                die('close blocked: issue terminal requires exported issue handoff evidence')
        elif seal_terminal(entry) and reviewer_backed(entry) and entry['activePhase'] == 'Completion':
            seal = entry.get('verificationSeal')
            if not isinstance(seal, dict):
                die('close blocked: reviewer-backed Completion requires verificationSeal')
            invalidate_seal_on_content_drift(entry)
            if seal.get('stale'):
                write_seal_verdict_companion(path, entry)
                save_registry(path, data)
                reason = seal.get('staleReason') or 'unknown'
                die(f'close blocked: verificationSeal is stale: {reason}')
            if not successful_verdict(entry):
                die('close blocked: reviewer-backed Completion requires verdict outcome success')
        entry['status'] = 'closed'
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        _require_commit()(path, data, transcript_path, rendered)
    notice = lifecycle_status_notice('closed')
    print_post_action_advisories(entry, None, None, notice, next_line_for_state(entry))
    print(entry['id'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def delete_collab(path: Path, target: str, confirmed: bool, caller_role: str | None = None) -> int:
    if not confirmed:
        die('delete requires --yes confirmation')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'delete')
        transcript_path = transcript_path_for_entry(entry)
        contribution_store_path = contribution_store_path_for_entry(path, entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        data['collabs'] = [candidate for candidate in data['collabs'] if candidate['id'] != entry['id']]
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        for owned_path in (transcript_path, contribution_store_path):
            if owned_path.exists():
                owned_path.unlink()
        save_registry(path, data)
    print(entry['id'])
    return 0
