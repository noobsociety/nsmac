#!/usr/bin/env python3
"""Issue-export model and command: normalizes external issue-export evidence files into validated issue dicts, detects the exported-issue handoff on an entry, and orchestrates the `export-issues` write-path command (record the exported issues, optionally close on close-eligibility, render the completion summary, and persist). The two dependencies it cannot import without a cycle — the core-owned `commit_registry_and_transcript` write and the `post_execution`-owned `close_eligible_after_execution` decision — are injected via `configure_issue_export`. Does not own the two-file commit implementation or the close-eligibility policy."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Callable

from commands.collab.engine.advisories import print_post_action_advisories
from commands.collab.engine.config_paths import DEFAULT_ROLES_DIR
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.errors import die
from commands.collab.engine.execution import all_execution_completed, issue_terminal
from commands.collab.engine.participants import (
    assert_caller_role,
    effective_turn_order,
    has_participant,
)
from commands.collab.engine.phase_lifecycle import lifecycle_status_notice, print_notice_diagnostic
from commands.collab.engine.registry_io import (
    load_registry,
    registry_lock,
    resolve_collab,
    save_registry,
)
from commands.collab.engine.seal_verification import (
    append_completion_summary,
    default_close_summary,
    summary_date_from_timestamp,
)
from commands.collab.engine.speak_state import next_line_for_state
from commands.collab.engine.transcript_readers import (
    completion_summary_empty,
    transcript_path_for_entry,
)
from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    render_managed_header_text,
)

_commit_registry_and_transcript: Callable[[Path, dict, Path, str], None] | None = None
_close_eligible_after_execution: Callable[[dict, list[str]], bool] | None = None


def configure_issue_export(
    *,
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None],
    close_eligible_after_execution: Callable[[dict, list[str]], bool],
) -> None:
    """Inject the cycle-blocked dependencies of the export-issues write path: the core-owned two-file commit and the post_execution-owned close-eligibility decision."""
    global _commit_registry_and_transcript, _close_eligible_after_execution
    _commit_registry_and_transcript = commit_registry_and_transcript
    _close_eligible_after_execution = close_eligible_after_execution


def exported_issue_handoff_present(entry: dict) -> bool:
    exported = entry.get('exportedIssues')
    return (
        isinstance(exported, dict)
        and isinstance(exported.get('issues'), list)
        and bool(exported.get('issues'))
    )


def normalize_issue_export_evidence(evidence_path: Path) -> list[dict]:
    try:
        raw = json.loads(evidence_path.read_text())
    except FileNotFoundError:
        die(f'issue export evidence file missing: {evidence_path}')
    except json.JSONDecodeError as exc:
        die(f'issue export evidence file invalid JSON: {evidence_path}: {exc}')
    if not isinstance(raw, dict):
        die('issue export evidence must be a JSON object')
    issues = raw.get('issues')
    if not isinstance(issues, list) or not issues:
        die('issue export evidence requires a non-empty issues list')
    normalized: list[dict] = []
    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            die(f'issue export evidence issue {index} must be an object')
        title = issue.get('title')
        if not isinstance(title, str) or not title.strip():
            die(f'issue export evidence issue {index} requires title')
        item = {'title': title.strip()}
        for optional in ('url', 'body', 'owner', 'delivery'):
            value = issue.get(optional)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                die(f'issue export evidence issue {index} {optional} must be a non-empty string')
            item[optional] = value.strip()
        requires = issue.get('requires')
        if requires is not None:
            if not isinstance(requires, list) or any(
                not isinstance(value, str) or not value.strip() for value in requires
            ):
                die(f'issue export evidence issue {index} requires must be a list of non-empty strings')
            item['requires'] = [value.strip() for value in requires]
        normalized.append(item)
    return normalized


def export_issues(
    path: Path,
    target: str,
    role: str,
    evidence_file: Path,
    timestamp: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    if _commit_registry_and_transcript is None or _close_eligible_after_execution is None:
        die('issue export engine is not configured: write callbacks missing')
    issues = normalize_issue_export_evidence(evidence_file)
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'export-issues', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("export-issues")} is valid only in Completion')
        if not issue_terminal(entry):
            die(f'{collab_dispatch("export-issues")} requires terminal issue')
        if role != 'pe':
            die('issue export must be authored by platform engineer role pe')
        if not has_participant(entry, role):
            die(f'issue export role must already be a participant: {role}')
        if not all_execution_completed(entry):
            die('issue export blocked: pending execution role(s) remain')
        entry['exportedIssues'] = {
            'exportedAt': timestamp or dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'exportedBy': role,
            'issues': issues,
        }
        closed = _close_eligible_after_execution(entry, effective_turn_order(entry))
        if closed:
            entry['status'] = 'closed'
            if data.get('activeCollabId') == entry['id']:
                data['activeCollabId'] = None
        notice = lifecycle_status_notice('closed') if closed else None
        transcript_path = transcript_path_for_entry(entry)
        if closed and transcript_path.exists():
            transcript = transcript_path.read_text()
            rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
            if completion_summary_empty(rendered):
                rendered = append_completion_summary(
                    rendered,
                    default_close_summary(entry),
                    summary_date_from_timestamp(entry['exportedIssues']['exportedAt']),
                )
            print_header_overwrite(header_changed)
            _commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line_for_state(entry))
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
    return 0
