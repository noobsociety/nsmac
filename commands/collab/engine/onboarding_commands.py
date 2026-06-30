#!/usr/bin/env python3
"""Record onboarding command handlers: create a new moderated record with its transcript and contribution store (`init`) and join a role into an existing record's roster (`join`). Owns the `ensure_init_project_metadata` helper that backfills project identity at init time. The two write paths cannot import their commit primitives without a cycle — the core-owned `commit_new_collab_artifacts` (three-artifact create) for init and `commit_registry_and_transcript` (two-file write) for join — so both are injected via `configure_onboarding_commands`. Does not own the commit primitives, registry validation, transcript rendering, or the init token parser."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import webbrowser
from copy import deepcopy
from pathlib import Path
from typing import Callable

from roles import load_role

from commands.collab.engine.advisories import print_post_action_advisories
from commands.collab.engine.browser import open_browser_uri
from commands.collab.engine.command_lines import (
    resume_command_invocation,
    transcript_view_command_for_role,
)
from commands.collab.engine.config_paths import DEFAULT_ROLES_DIR
from commands.collab.engine.contribution_store import (
    empty_contribution_store,
    path_for_entry_target,
)
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.errors import die
from commands.collab.engine.git_repo import (
    assert_work_repo_not_framework_for_external_project,
    default_init_work_repo_root,
    resolve_git_work_tree,
)
from commands.collab.engine.init_inputs import parse_init_tokens
from commands.collab.engine.normalizers import (
    format_banner_timestamp,
    normalize_join_agent_id,
    normalize_slug,
)
from commands.collab.engine.participants import (
    add_participant_to_entry,
    count_caller_declined_agent_id_write,
    participant_agent_id,
    participant_roles,
    role_is_joinable,
)
from commands.collab.engine.registry_constants import (
    DEFAULT_REVIEWER_MODE,
    DEFAULT_REVIEWER_OPTIONAL_PHASES,
    DEFAULT_VERIFICATION_CAP,
)
from commands.collab.engine.registry_io import (
    load_registry,
    load_registry_or_bootstrap,
    next_sequence,
    registry_lock,
    resolve_collab,
)
from commands.collab.engine.registry_state import project_metadata_from_identity
from commands.collab.engine.registry_validation import validate_registry as validate_registry_data
from commands.collab.engine.transcript_readers import transcript_path_for_entry
from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    render_initial_transcript,
    render_managed_header_text,
)

_commit_new_collab_artifacts: Callable[..., None] | None = None
_commit_registry_and_transcript: Callable[[Path, dict, Path, str], None] | None = None


def configure_onboarding_commands(
    *,
    commit_new_collab_artifacts: Callable[..., None],
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None],
) -> None:
    """Inject the cycle-blocked commit primitives of the init/join write paths: the core-owned three-artifact create and two-file write."""
    global _commit_new_collab_artifacts, _commit_registry_and_transcript
    _commit_new_collab_artifacts = commit_new_collab_artifacts
    _commit_registry_and_transcript = commit_registry_and_transcript


def _require_commit_new() -> Callable[..., None]:
    if _commit_new_collab_artifacts is None:
        die('onboarding commands engine is not configured: new-collab commit callback missing')
    return _commit_new_collab_artifacts


def _require_commit() -> Callable[[Path, dict, Path, str], None]:
    if _commit_registry_and_transcript is None:
        die('onboarding commands engine is not configured: commit callback missing')
    return _commit_registry_and_transcript


def ensure_init_project_metadata(data: dict, registry_path: Path) -> None:
    project = data.get('project')
    if isinstance(project, dict):
        return
    metadata = project_metadata_from_identity()
    if metadata is not None:
        data['project'] = metadata
        return
    project_root = registry_path.parent.resolve()
    data['project'] = {
        'projectId': hashlib.sha256(str(project_root).encode()).hexdigest()[:32],
        'label': project_root.name or 'command-project',
    }


def init_collab(
    path: Path,
    tokens: list[str],
    roles_dir: Path,
    opener: Callable[[str], bool] = webbrowser.open_new_tab,
) -> int:
    title, agent_id, reviewer, open_requested, participant_verification, terminal, work_repo_raw = parse_init_tokens(tokens)
    with registry_lock(path):
        data = load_registry_or_bootstrap(path)
        ensure_init_project_metadata(data, path)
        date = dt.date.today().isoformat()
        slug = normalize_slug(title)
        collab_id = f'{date}-{slug}'
        transcript_rel = f'records/{collab_id}.md'
        transcript_path = Path(transcript_rel)

        if transcript_path.exists():
            die(f'record already exists: {transcript_path}')
        if any(entry['id'] == collab_id for entry in data['collabs']):
            die(f'registry collision: {collab_id}')
        if any(entry['slug'] == slug for entry in data['collabs']):
            die(f'registry collision: {slug}')

        sequence = next_sequence(data)
        if any(entry.get('sequence') == sequence for entry in data['collabs']):
            die(f'registry collision: sequence {sequence}')

        load_role(roles_dir, 'mod')
        if reviewer:
            load_role(roles_dir, reviewer)

        entry = {
            'id': collab_id,
            'slug': slug,
            'title': title,
            'description': f'Moderated discussion of {title}.',
            'createdAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'terminal': terminal,
            'status': 'open',
            'activePhase': 'Audit',
            'moderatorRole': 'mod',
            'participants': [{'role': 'mod', 'agentId': agent_id}],
            'turnOrder': ['mod'],
            'transcriptPath': transcript_rel,
            'sequence': sequence,
            'archived': False,
            'execution': {},
        }
        if work_repo_raw is not None:
            work_repo = resolve_git_work_tree(work_repo_raw, 'workRepo')
        else:
            work_repo = default_init_work_repo_root()
        assert_work_repo_not_framework_for_external_project(work_repo, 'workRepo')
        entry['workRepo'] = str(work_repo)
        if reviewer:
            entry['reviewerRole'] = reviewer
            entry['reviewerMode'] = DEFAULT_REVIEWER_MODE
            entry['reviewerOptionalPhases'] = list(DEFAULT_REVIEWER_OPTIONAL_PHASES)
        if terminal == 'seal':
            entry['verification'] = {
                'rounds': 0,
                'cap': DEFAULT_VERIFICATION_CAP,
                'subState': 'participant' if participant_verification else 'seal',
                'participantVerification': participant_verification,
                'participants': {},
            }

        nextdata = deepcopy(data)
        count_caller_declined_agent_id_write(nextdata, agent_id)
        nextdata['collabs'].append(entry)
        nextdata['activeCollabId'] = collab_id
        rendered_timestamp = format_banner_timestamp()
        rendered = render_initial_transcript(title, entry, roles_dir, rendered_timestamp)
        transcript_path = path_for_entry_target(path, entry, entry['transcriptPath'])
        contribution_store = empty_contribution_store(rendered_timestamp)
        _require_commit_new()(path, nextdata, entry, transcript_path, rendered, contribution_store)
    print(entry['transcriptPath'])
    if open_requested:
        file_uri = path_for_entry_target(path, entry, entry['transcriptPath']).resolve().as_uri()
        open_failure = open_browser_uri(file_uri, opener)
        if open_failure is None:
            print(f'OPEN: {file_uri}')
        else:
            print(f'OPEN: failed: {open_failure}')
    return 0


def join_participants(
    path: Path,
    target: str,
    role: str,
    agent_id: str | None,
    roles_dir: Path,
    emit_json: bool = False,
) -> int:
    normalized_agent_id = normalize_join_agent_id(agent_id)
    role_data = load_role(roles_dir, role)
    if not role_is_joinable(role_data):
        die(f'role not joinable: {role}')
    recorded_agent_id = normalized_agent_id
    identity_warning: str | None = None
    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        existing_agent_id = participant_agent_id(current_entry, role)
        if existing_agent_id:
            recorded_agent_id = existing_agent_id
            if existing_agent_id != normalized_agent_id:
                identity_warning = (
                    f'IDENTITY-WARN: {role} already joined as {existing_agent_id}; '
                    f'supplied agentId {normalized_agent_id} ignored'
                )

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        if add_participant_to_entry(next_entry, role, normalized_agent_id):
            count_caller_declined_agent_id_write(nextdata, normalized_agent_id)
        validate_registry_data(nextdata, path, DEFAULT_ROLES_DIR)

        transcript_path = transcript_path_for_entry(next_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()

        rendered, header_changed = render_managed_header_text(transcript, next_entry, roles_dir)
        print_header_overwrite(header_changed)
        _require_commit()(path, nextdata, transcript_path, rendered)
    print_post_action_advisories(
        next_entry,
        role,
        next_entry['activePhase'],
        None,
        f'NEXT: Run {collab_dispatch("show policy")} before first speak.',
    )
    print(f'TRANSCRIPT: {transcript_view_command_for_role(next_entry, role)}')
    print(f'IDENTITY: {role} {recorded_agent_id}')
    if identity_warning:
        print(identity_warning)
    print(' '.join(participant_roles(next_entry)))
    if emit_json:
        print(json.dumps({
            'agentId': recorded_agent_id,
            'freshRegistryRead': True,
            'identityWarning': identity_warning,
            'nextTranscriptCommand': transcript_view_command_for_role(next_entry, role),
            'participants': participant_roles(next_entry),
            'resumeCommand': resume_command_invocation(next_entry, role),
            'target': next_entry['id'],
        }, sort_keys=True))
    return 0
