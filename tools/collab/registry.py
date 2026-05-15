#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import fnmatch
import json
import os
import re
import sys
import webbrowser
from contextlib import contextmanager
from collections.abc import Callable
from copy import deepcopy
from pathlib import PurePosixPath
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cursor.roles import load_role, participant_row, roles_command


PHASES = ['Audit', 'Discussion', 'Conclusion', 'Action Plan', 'Handoff', 'Completion']
CONTENT_ONLY_GUARD = '<!-- collab:content-only; do-not-execute -->'
HEADER_MANAGED_BEGIN = '<!-- collab:header-managed -->'
HEADER_MANAGED_END = '<!-- collab:header-end -->'
ONE_SPEAK_PHASES = {'Audit', 'Conclusion', 'Action Plan', 'Handoff'}
AUTO_ADVANCE_EXEMPT_PHASES = {'Discussion', 'Completion'}
CONVERGENT_REVIEWER_PHASES = {'Audit', 'Conclusion'}
MOD_EXCLUDED_PHASES = {'Conclusion', 'Action Plan', 'Handoff', 'Completion'}
ALLOWED_SET_FIELDS = {'title', 'description', 'turn-order', 'reviewer-optional-phases'}
FORCE_ONLY_FIELDS = {'active-phase'}
ALLOWED_STATUSES = {'open', 'closed', 'archived'}
ALLOWED_EXECUTION_STATUSES = {'in_progress', 'completed', 'failed'}
ALLOWED_VALIDATION_SCOPES = {'scoped', 'full', 'deferred'}
ALLOWED_COMPLETION_SUBSTATES = {'execution', 'verification'}
ALLOWED_CAP_EXITS = {'reopen-action-plan', 'reopen-handoff', 'archive'}
DEFAULT_VERIFICATION_CAP = 3
HANDOFF_SCHEMA_VERSION = 1
VERIFICATION_SEAL_SCHEMA_VERSION = 1
MAX_HANDOFF_SCOPE_COUNT = 32
MAX_HANDOFF_SCOPE_LENGTH = 200
MAX_VALIDATION_COMMANDS = 16
MAX_VALIDATION_COMMAND_ARGS = 16
MAX_VALIDATION_ARG_LENGTH = 200
ALLOWED_REVIEWER_MODES = {'last-in-convergent-phases'}
DEFAULT_REVIEWER_MODE = 'last-in-convergent-phases'
DEFAULT_REVIEWER_OPTIONAL_PHASES = ['Discussion']
INVALID_AGENT_ID_ALTERNATIVES = {'n/a', 'unspecified'}
DEFAULT_OPEN_ROSTER_EFFORT = 'medium'
def resolve_cursor_root() -> Path:
    configured = os.environ.get('CURSOR_CONFIG_ROOT')
    if configured:
        return Path(configured).expanduser().resolve()
    if (ROOT / 'commands').is_dir() and (ROOT / '_functions').is_dir():
        return ROOT
    source_cursor = ROOT / 'cursor'
    if (source_cursor / 'commands').is_dir() and (source_cursor / '_functions').is_dir():
        return source_cursor.resolve()
    return ROOT


DEFAULT_CURSOR_ROOT = resolve_cursor_root()
DEFAULT_ROLES_DIR = DEFAULT_CURSOR_ROOT / '_roles'
DEFAULT_EFFORT_PATH = DEFAULT_CURSOR_ROOT / '_functions/collab/_agent-effort.json'
DEFAULT_BUDGET_PATH = DEFAULT_CURSOR_ROOT / '_functions/collab/_contribution-budget.md'
DEFAULT_MODERATOR_POLISH_PATH = DEFAULT_CURSOR_ROOT / '_functions/collab/_moderator-polish.md'
DEFAULT_FLAG_TAXONOMY_PATH = DEFAULT_CURSOR_ROOT / '_functions/collab/_flag-taxonomy.md'
MODERATOR_ONLY_ACTIONS = {
    'advance',
    'archive',
    'close',
    'delete',
    'restore',
    'set',
    'unset',
}
ID_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$')
ROLE_KEY_RE = re.compile(r'^\w+$')
SUMMARY_RE = re.compile(r'^<summary>(?P<role>[A-Za-z0-9_-]+)(?:\s+—\s+.+)?</summary>$')
SUMMARY_HEADING_RE = re.compile(r'^### Summary \u2014 \d{4}-\d{2}-\d{2}$')
LEGACY_EXPANDED_RE = re.compile(r'^\*\*(?P<role>[A-Za-z0-9_-]+)\s+—')
LEGACY_HEADING_RE = re.compile(r'^###\s+(?P<role>[A-Za-z0-9_-]+)\s+—')
DETAILS_OPEN_RE = re.compile(r'^<details(?:\s+[^>]*)?>$')
DETAILS_CLOSE_RE = re.compile(r'^</details>$')
ANCHOR_RE = re.compile(r'^<a name="(?P<anchor>[A-Za-z0-9_-]+)"></a>$')
TIMESTAMP_RE = re.compile(r'^<p><em>(?P<timestamp>.+)</em></p>$')
ACTION_CHECKLIST_RE = re.compile(
    r'^\s*-\s+\[(?P<mark>[ xX])\]\s+\*\*(?P<role>[A-Za-z0-9_-]+):\*\*(?P<text>.*)$'
)
ACTION_PLAN_SHAPE_RE = re.compile(r'^- \[[ x]\] \*\*[a-z]+:\*\*')
ACTION_PLAN_EXEMPT_RE = re.compile(r'^\s*-\s+\[[ xX]\]\s+\*\*[A-Za-z0-9_-]+:\*\*')
UNLABELED_ACTION_CHECKBOX_RE = re.compile(r'^\s*-\s+\[ \]\s+(?!\*\*[A-Za-z0-9_-]+:\*\*)\S')
EFFORT_OVERRIDE_RE = re.compile(
    r'^EFFORT OVERRIDE: (?:(matrix)|'
    r'(low|medium|high|xhigh|max)\s+\u2014\s+'
    r'(coherence-risk|implementation-density|deadlock-or-disagreement|delivery-or-migration-risk|reviewer-concern-raised):\s+.+)$'
)
EFFORT_OVERRIDE_COMMENT_RE = re.compile(
    r'^<!-- collab:effort-override b64:(?P<payload>[A-Za-z0-9_-]+={0,2}) -->$'
)
STRUCTURED_HANDOFF_HEADING_RE = re.compile(r'^\s*\*\*(?P<field>writeScope|validationCommands):?\*\*:?\s*(?P<rest>.*)$')
CODE_SPAN_RE = re.compile(r'`([^`]+)`')
SHELL_PATTERN_RE = re.compile(r'[;&|<>`$\\\r\n]')
GLOB_PATTERN_RE = re.compile(r'[*?\[]')
MANDATORY_EFFORT_OVERRIDE_TURNS = {
    ('Audit', 'pa'),
    ('Conclusion', 'pa'),
    ('Completion', 'pa'),
    ('Handoff', 'tw'),
    ('Handoff', 'pe'),
}
TYPO_ROW_RE = re.compile(r'^\|\s*`(?P<typo>[^`]+)`\s*\|\s*`(?P<fix>[^`]+)`')
FLAG_ROW_RE = re.compile(r'^\|\s*`(?P<flag>[^`]+)`\s*\|\s*`(?P<class>[^`]+)`\s*\|\s*(?P<notes>.*?)\s*\|$')
OLD_ROOT_KEYS = {'schema_version', 'active_collab_id'}
OLD_ENTRY_KEYS = {
    'active_phase',
    'created_on',
    'moderator_role',
    'transcript_path',
    'turn_order',
}
ACTION_PLAN_SHAPE_EXAMPLE = '- [ ] **tw:** Update the route doc.'


def die(message: str) -> None:
    raise SystemExit(message)


def load_registry(path: Path) -> dict:
    if not path.exists():
        die(f'registry missing: {path}')
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f'registry invalid JSON: {path}: {exc}')
    validate_registry(data, path)
    return data


def save_registry(path: Path, data: dict) -> None:
    bump_registry_revision(data)
    validate_registry(data, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f'{path.name}.tmp')
    try:
        tmp_path.write_text(json.dumps(data, indent=2) + '\n')
        tmp_path.replace(path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def bump_registry_revision(data: dict) -> int:
    revision = data.get('revision', 0)
    if not isinstance(revision, int) or revision < 0:
        die('registry revision must be a non-negative integer')
    revision += 1
    data['revision'] = revision
    return revision


def registry_revision(data: dict) -> int:
    revision = data.get('revision', 0)
    if not isinstance(revision, int) or revision < 0:
        die('registry revision must be a non-negative integer')
    return revision


@contextmanager
def registry_lock(path: Path):
    """Serialize registry/transcript mutations that derive state from live files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f'{path.name}.lock')
    with lock_path.open('a+') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def load_registry_or_bootstrap(path: Path) -> dict:
    if not path.exists():
        return {'schemaVersion': 1, 'activeCollabId': None, 'collabs': []}
    return load_registry(path)


def format_timestamp(now: dt.datetime | None = None) -> str:
    value = now or dt.datetime.now().astimezone()
    stamp = value.strftime('%Y-%m-%d %H:%M %z')
    return f'{stamp[:-2]}:{stamp[-2:]}'


def format_banner_timestamp(now: dt.datetime | None = None) -> str:
    value = now or dt.datetime.now().astimezone()
    day = str(value.day)
    return value.strftime(f'%b {day}, %Y @ %-I:%M %p')


def normalize_slug(title: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if not slug:
        die('slug is empty; ask the moderator for a clearer name')
    return slug


def normalize_title(title: str) -> str:
    words = re.sub(r'\s+', ' ', title.strip()).split(' ')
    if not words:
        die('<name> is required')
    acronyms = {'ai', 'api', 'cli', 'dx', 'qa', 'ui', 'ux'}
    small_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'vs', 'with'}
    normalized: list[str] = []
    for index, word in enumerate(words):
        if not word:
            continue
        parts = re.split(r'([/-])', word)
        rendered_parts: list[str] = []
        for part_index, part in enumerate(parts):
            lower = part.lower()
            if part in {'/', '-'}:
                rendered_parts.append(part)
            elif lower in acronyms:
                rendered_parts.append(lower.upper())
            elif index > 0 and part_index == 0 and lower in small_words:
                rendered_parts.append(lower)
            elif part.isupper() and len(part) > 1:
                rendered_parts.append(part)
            else:
                rendered_parts.append(part[:1].upper() + part[1:].lower())
        normalized.append(''.join(rendered_parts))
    return ' '.join(normalized)


def next_sequence(data: dict) -> int:
    sequences = [
        entry.get('sequence')
        for entry in data.get('collabs', [])
        if isinstance(entry.get('sequence'), int)
    ]
    return max(sequences, default=0) + 1


def parse_init_tokens(tokens: list[str]) -> tuple[str, str, str | None, bool]:
    name_tokens: list[str] = []
    agent_id: str | None = None
    reviewer: str | None = None
    open_requested = False
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == '--agent-id':
            if agent_id is not None:
                die('duplicate flag: --agent-id')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('agent-id is required')
            agent_id = tokens[index]
        elif token == '--reviewer':
            if reviewer is not None:
                die('duplicate flag: --reviewer')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('--reviewer requires a role key')
            reviewer = tokens[index]
            if not ROLE_KEY_RE.match(reviewer):
                die('--reviewer requires a role key')
        elif token == '--preview':
            if open_requested:
                die('duplicate flag: --preview')
            open_requested = True
        elif token.startswith('--'):
            die(f'unknown flag: {token}')
        else:
            name_tokens.append(token)
        index += 1

    raw_title = ' '.join(name_tokens).strip()
    if not raw_title:
        die('<name> is required')
    title = normalize_title(raw_title)
    return title, normalize_join_agent_id(agent_id), reviewer, open_requested


def summary_role(line: str) -> str | None:
    match = SUMMARY_RE.match(line.strip())
    if not match:
        return None
    return match.group('role')


def phase_section(text: str, phase: str) -> list[str]:
    lines = text.splitlines()
    heading = f'## {phase}'
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        die(f'transcript phase missing: {phase}')

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith('## ') and lines[index].strip() in {f'## {item}' for item in PHASES}:
            end = index
            break
    return lines[start:end]


def phase_slug(phase: str) -> str:
    return phase.lower().replace(' ', '-')


def section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index
            break
    if start is None:
        die(f'transcript section missing: {heading}')

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith('## ') and lines[index].strip() in {f'## {item}' for item in PHASES}:
            end = index
            break
    return start, end


def toc_bounds(lines: list[str]) -> tuple[int, int]:
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip().lower() == '**table of contents**':
            start = index
            break
    if start is None:
        die('transcript table of contents missing')

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == '---':
            end = index
            break
    return start, end


def next_anchor_counter(lines: list[str], phase: str, role: str) -> int:
    prefix = f'{phase_slug(phase)}-{role}-'
    highest = 0
    for line in lines:
        match = ANCHOR_RE.match(line.strip())
        if match and match.group('anchor').startswith(prefix):
            suffix = match.group('anchor')[len(prefix):]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
    return max(highest, contribution_roles('\n'.join(lines), phase).count(role)) + 1


def insert_toc_entry(lines: list[str], phase: str, role: str, anchor: str) -> list[str]:
    start, end = toc_bounds(lines)
    phase_line = f'- [{phase}](#{phase_slug(phase)})'
    phase_index: int | None = None
    for index in range(start + 1, end):
        if lines[index].strip() == phase_line:
            phase_index = index
            break
    if phase_index is None:
        die(f'transcript table of contents phase missing: {phase}')

    entry = f'  - [{role}](#{anchor})'
    insert_at = phase_index + 1
    while insert_at < end and lines[insert_at].startswith('  - '):
        if lines[insert_at].strip() == entry.strip():
            die(f'transcript table of contents entry already exists: {anchor}')
        insert_at += 1
    return lines[:insert_at] + [entry] + lines[insert_at:]


def append_phase_block(lines: list[str], phase: str, block: list[str]) -> list[str]:
    _start, end = section_bounds(lines, f'## {phase}')
    insert = list(block)
    before = lines[:end]
    after = lines[end:]
    if before and before[-1] != '':
        insert = [''] + insert
    if after and insert and insert[-1] != '':
        insert.append('')
    return before + insert + after


def contribution_body_lines(block: list[str]) -> list[str]:
    marker_index: int | None = None
    for index, line in enumerate(block):
        if line.strip() == CONTENT_ONLY_GUARD:
            marker_index = index
            break
    if marker_index is None:
        return []
    return block[marker_index + 1:len(block) - 1]


def contribution_is_retracted(block: list[str]) -> bool:
    for line in contribution_body_lines(block):
        stripped = line.strip()
        if not stripped:
            continue
        return stripped.startswith('RETRACTED:')
    return False


def contribution_roles(text: str, phase: str) -> list[str]:
    roles: list[str] = []
    lines = phase_section(text, phase)
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if DETAILS_OPEN_RE.match(stripped):
            start = index
            depth = 1
            end: int | None = None
            cursor = index + 1
            while cursor < len(lines):
                nested = lines[cursor].strip()
                if DETAILS_OPEN_RE.match(nested):
                    depth += 1
                elif DETAILS_CLOSE_RE.match(nested):
                    depth -= 1
                    if depth == 0:
                        end = cursor + 1
                        break
                cursor += 1
            if end is None:
                die(f'transcript details block not closed in phase: {phase}')
            role = summary_role(lines[start + 1]) if start + 1 < end else None
            if role is not None and not contribution_is_retracted(lines[start:end]):
                roles.append(role)
            index = end
            continue
        for pattern in (LEGACY_EXPANDED_RE, LEGACY_HEADING_RE):
            match = pattern.match(stripped)
            if match:
                roles.append(match.group('role'))
                break
        index += 1
    return roles


def action_plan_checklist_items(transcript: str) -> list[dict]:
    items: list[dict] = []
    details_depth = 0
    item_number = 0
    try:
        action_plan_lines = phase_section(transcript, 'Action Plan')
    except SystemExit as exc:
        if str(exc) == 'transcript phase missing: Action Plan':
            return []
        raise
    for line in action_plan_lines:
        stripped = line.strip()
        if DETAILS_OPEN_RE.match(stripped):
            details_depth += 1
            continue
        if DETAILS_CLOSE_RE.match(stripped):
            details_depth = max(0, details_depth - 1)
            continue
        if details_depth > 1:
            continue
        match = ACTION_CHECKLIST_RE.match(line)
        if not match:
            continue
        item_number += 1
        mark = match.group('mark').lower()
        items.append({
            'number': item_number,
            'role': match.group('role'),
            'checked': mark == 'x',
            'text': match.group('text').strip(),
        })
    return items


def unchecked_assigned_items_by_role(transcript: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in action_plan_checklist_items(transcript):
        role = item['role']
        counts.setdefault(role, 0)
        if not item['checked']:
            counts[role] += 1
    return counts


def tombstone_count(transcript: str) -> int:
    total = 0
    for phase in PHASES:
        try:
            lines = phase_section(transcript, phase)
        except SystemExit:
            continue
        index = 0
        while index < len(lines):
            if not DETAILS_OPEN_RE.match(lines[index].strip()):
                index += 1
                continue
            start = index
            depth = 1
            end: int | None = None
            cursor = index + 1
            while cursor < len(lines):
                stripped = lines[cursor].strip()
                if DETAILS_OPEN_RE.match(stripped):
                    depth += 1
                elif DETAILS_CLOSE_RE.match(stripped):
                    depth -= 1
                    if depth == 0:
                        end = cursor + 1
                        break
                cursor += 1
            if end is None:
                die(f'transcript details block not closed in phase: {phase}')
            if contribution_is_retracted(lines[start:end]):
                total += 1
            index = end
    return total


def action_plan_label_summary(transcript: str) -> str:
    counts = {
        role: count
        for role, count in unchecked_assigned_items_by_role(transcript).items()
        if count
    }
    if not counts:
        return 'none'
    return ', '.join(f'{role}={counts[role]}' for role in sorted(counts))


def unchecked_assigned_item_count(transcript: str, role: str) -> int:
    return unchecked_assigned_items_by_role(transcript).get(role, 0)


def completed_execution_unchecked_items(entry: dict, transcript: str) -> list[dict]:
    completed_roles = [
        role for role, state in sorted(entry.get('execution', {}).items())
        if state.get('status') == 'completed'
    ]
    if not completed_roles:
        return []
    unchecked = unchecked_assigned_items_by_role(transcript)
    violations: list[dict] = []
    for role in completed_roles:
        count = unchecked.get(role, 0)
        if count:
            violations.append({'role': role, 'uncheckedCount': count})
    return violations


def handoff_abort(field: str, value: object) -> None:
    if isinstance(value, str):
        rendered = value
    else:
        rendered = json.dumps(value, sort_keys=True)
    die(f'ABORT: {field} contains disallowed pattern: {rendered}')


def normalize_handoff_scope(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        handoff_abort('writeScope', raw)
    value = raw.strip().rstrip('/')
    if not value:
        handoff_abort('writeScope', raw)
    if len(value) > MAX_HANDOFF_SCOPE_LENGTH:
        handoff_abort('writeScope', value)
    if Path(value).is_absolute():
        handoff_abort('writeScope', raw)
    if value in {'*', '**'} or value.startswith('../') or '/../' in value or value.endswith('/..'):
        handoff_abort('writeScope', raw)
    normalized = PurePosixPath(Path(value).as_posix()).as_posix()
    if normalized in {'', '.', '..'}:
        handoff_abort('writeScope', raw)
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {'', '.', '..'} for part in parts):
        handoff_abort('writeScope', raw)
    if parts[0] in {'*', '**'}:
        handoff_abort('writeScope', raw)
    return normalized


def validate_handoff_write_scope(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        handoff_abort('writeScope', value)
    if len(value) > MAX_HANDOFF_SCOPE_COUNT:
        handoff_abort('writeScope', value)
    scopes = [normalize_handoff_scope(item) for item in value]
    if len(scopes) != len(set(scopes)):
        handoff_abort('writeScope', value)
    return scopes


def validation_command_abort(value: object) -> None:
    handoff_abort('validationCommands', value)


def normalize_validation_command_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        validation_command_abort(raw)
    value = raw.strip()
    if len(value) > MAX_VALIDATION_ARG_LENGTH:
        validation_command_abort(value)
    if SHELL_PATTERN_RE.search(value):
        validation_command_abort(value)
    if not value.startswith('./'):
        validation_command_abort(value)
    if Path(value).is_absolute():
        validation_command_abort(value)
    normalized = PurePosixPath(Path(value).as_posix()).as_posix()
    if normalized.startswith('../') or '/../' in normalized or normalized.endswith('/..'):
        validation_command_abort(value)
    if normalized in {'.', './'}:
        validation_command_abort(value)
    command_path = PurePosixPath(value[2:]).as_posix()
    if not command_path or command_path in {'.', '..'}:
        validation_command_abort(value)
    return f'./{command_path}'


def normalize_validation_arg(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        validation_command_abort(raw)
    value = raw.strip()
    if len(value) > MAX_VALIDATION_ARG_LENGTH:
        validation_command_abort(value)
    if SHELL_PATTERN_RE.search(value):
        validation_command_abort(value)
    if Path(value).is_absolute():
        validation_command_abort(value)
    if value.startswith('../') or '/../' in value or value.endswith('/..'):
        validation_command_abort(value)
    return value


def normalize_validation_argv(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        validation_command_abort(value)
    if len(value) > MAX_VALIDATION_COMMAND_ARGS:
        validation_command_abort(value)
    command = normalize_validation_command_path(value[0])
    return [command, *[normalize_validation_arg(item) for item in value[1:]]]


def normalize_validation_command_entry(value: object) -> list[str]:
    if isinstance(value, dict):
        extra_keys = set(value) - {'argv'}
        if extra_keys or 'argv' not in value:
            validation_command_abort(value)
        return normalize_validation_argv(value['argv'])
    return normalize_validation_argv(value)


def validate_handoff_validation_commands(value: object) -> list[list[str]]:
    if not isinstance(value, list) or not value:
        validation_command_abort(value)
    if len(value) > MAX_VALIDATION_COMMANDS:
        validation_command_abort(value)
    if all(isinstance(item, str) for item in value):
        return [normalize_validation_argv(value)]
    return [normalize_validation_command_entry(item) for item in value]


def validate_handoff_state(value: object, source: str) -> dict:
    if not isinstance(value, dict):
        die(f'{source}: handoff state must be an object')
    schema_version = value.get('schemaVersion')
    if schema_version != HANDOFF_SCHEMA_VERSION:
        die(f'{source}: handoff schemaVersion must be {HANDOFF_SCHEMA_VERSION}')
    write_scope = validate_handoff_write_scope(value.get('writeScope'))
    validation_commands = validate_handoff_validation_commands(value.get('validationCommands'))
    body = value.get('body')
    if body is not None and not isinstance(body, str):
        die(f'{source}: handoff body must be a string when present')
    normalized = dict(value)
    normalized['schemaVersion'] = HANDOFF_SCHEMA_VERSION
    normalized['writeScope'] = write_scope
    normalized['validationCommands'] = validation_commands
    return normalized


def reviewer_role(entry: dict) -> str | None:
    value = entry.get('reviewerRole')
    if isinstance(value, str) and value.strip():
        return value
    return None


def participant_roles(entry: dict) -> list[str]:
    return [p['role'] for p in entry.get('participants', [])]


def participant_agent_id(entry: dict, role: str) -> str | None:
    for participant in entry.get('participants', []):
        if participant.get('role') == role:
            value = participant.get('agentId')
            return value if isinstance(value, str) else None
    return None


def has_participant(entry: dict, role: str) -> bool:
    return role in participant_roles(entry)


def reviewer_state(entry: dict) -> dict:
    reviewer = reviewer_role(entry)
    if reviewer is None:
        return {'reviewerRole': None, 'state': 'absent'}
    state = 'active' if has_participant(entry, reviewer) else 'pending'
    return {'reviewerRole': reviewer, 'state': state}


def active_reviewer_role(entry: dict) -> str | None:
    reviewer = reviewer_role(entry)
    if reviewer and has_participant(entry, reviewer):
        return reviewer
    return None


def reviewer_backed(entry: dict) -> bool:
    return reviewer_role(entry) is not None


def completion_state(entry: dict) -> dict:
    completion = entry.setdefault('completion', {})
    if not isinstance(completion, dict):
        die('registry: completion must be an object when present')
    substate = completion.get('subState')
    if substate is None:
        substate = 'execution'
        completion['subState'] = substate
    if substate not in ALLOWED_COMPLETION_SUBSTATES:
        die(f'registry: completion.subState must be one of {sorted(ALLOWED_COMPLETION_SUBSTATES)}')
    return completion


def verification_state(entry: dict) -> dict:
    verification = entry.setdefault('verification', {})
    if not isinstance(verification, dict):
        die('registry: verification must be an object when present')
    rounds = verification.get('rounds', 0)
    cap = verification.get('cap', DEFAULT_VERIFICATION_CAP)
    if not isinstance(rounds, int) or rounds < 0:
        die('registry: verification.rounds must be a non-negative integer when present')
    if not isinstance(cap, int) or cap < 1:
        die('registry: verification.cap must be a positive integer when present')
    verification['rounds'] = rounds
    verification['cap'] = cap
    return verification


def initialize_completion_state(entry: dict, substate: str = 'execution', reset_rounds: bool = False) -> None:
    if not reviewer_backed(entry):
        return
    if substate not in ALLOWED_COMPLETION_SUBSTATES:
        die(f'completion subState must be one of {sorted(ALLOWED_COMPLETION_SUBSTATES)}')
    completion = completion_state(entry)
    completion['subState'] = substate
    verification = verification_state(entry)
    if reset_rounds:
        verification['rounds'] = 0
    verification.setdefault('cap', DEFAULT_VERIFICATION_CAP)


def execution_identity(role: str, date: str) -> str:
    suffix = re.sub(r'[^0-9A-Za-z]+', '-', date).strip('-').lower()
    return f'{role}-{suffix or "execution"}'


def active_execution_entries(entry: dict) -> list[dict]:
    rows: list[dict] = []
    for role, state in sorted(entry.get('execution', {}).items()):
        if not isinstance(state, dict):
            continue
        rows.append({
            'role': role,
            'entryId': state.get('entryId') or execution_identity(role, state.get('date', 'execution')),
            'status': state.get('status'),
            'date': state.get('date'),
            'validationResult': state.get('validationResult'),
            'validationScope': state.get('validationScope'),
            'touchedPaths': list(state.get('touchedPaths', [])),
        })
    return rows


def execution_signature(entry: dict) -> str:
    entries = active_execution_entries(entry)
    encoded = json.dumps(entries, sort_keys=True, separators=(',', ':'))
    return base64.urlsafe_b64encode(encoded.encode()).decode().rstrip('=')


def validation_scopes_for_execution(entry: dict) -> list[str]:
    scopes: list[str] = []
    for state in entry.get('execution', {}).values():
        scope = state.get('validationScope') if isinstance(state, dict) else None
        if isinstance(scope, str) and scope not in scopes:
            scopes.append(scope)
    return scopes


def touched_paths_for_execution(entry: dict) -> list[str]:
    touched: list[str] = []
    for state in entry.get('execution', {}).values():
        if not isinstance(state, dict):
            continue
        for item in state.get('touchedPaths', []):
            if isinstance(item, str) and item not in touched:
                touched.append(item)
    return touched


def invalidate_verification_seal(entry: dict, reason: str) -> None:
    seal = entry.get('verificationSeal')
    if isinstance(seal, dict):
        seal['stale'] = True
        seal['staleReason'] = reason


def pending_reviewer_role(entry: dict) -> str | None:
    reviewer = reviewer_role(entry)
    if reviewer and not has_participant(entry, reviewer):
        return reviewer
    return None


def reviewer_mode(entry: dict) -> str:
    return entry.get('reviewerMode') or DEFAULT_REVIEWER_MODE


def reviewer_optional_phases(entry: dict) -> list[str]:
    value = entry.get('reviewerOptionalPhases')
    if value is None:
        return list(DEFAULT_REVIEWER_OPTIONAL_PHASES)
    return list(value)


def parse_reviewer_optional_phases(value: str | None) -> list[str]:
    if value is None or not value.strip():
        die('reviewer-optional-phases requires at least one phase')
    raw = value.strip()
    if ',' in raw:
        phases = [phase.strip() for phase in raw.split(',') if phase.strip()]
    else:
        tokens = raw.split()
        phases = []
        index = 0
        while index < len(tokens):
            matched = None
            for phase in PHASES:
                phase_tokens = phase.split()
                if tokens[index:index + len(phase_tokens)] == phase_tokens:
                    matched = phase
                    break
            if matched is None:
                phases.append(tokens[index])
                index += 1
            else:
                phases.append(matched)
                index += len(matched.split())
    if not phases:
        die('reviewer-optional-phases requires at least one phase')
    invalid = [phase for phase in phases if phase not in PHASES]
    if invalid:
        die(f'reviewer-optional-phases must contain valid phase names: {", ".join(invalid)}')
    if len(set(phases)) != len(phases):
        die('reviewer-optional-phases must not contain duplicates')
    return phases


def reviewer_required_for_phase(entry: dict, phase: str) -> str | None:
    reviewer = active_reviewer_role(entry)
    if not reviewer:
        return None
    if reviewer_mode(entry) == 'last-in-convergent-phases' and phase in CONVERGENT_REVIEWER_PHASES:
        return reviewer
    return None


def reviewer_optional_for_phase(entry: dict, phase: str) -> str | None:
    reviewer = active_reviewer_role(entry)
    if reviewer and phase in reviewer_optional_phases(entry):
        return reviewer
    return None


def optional_reviewer_allowed_at_round_boundary(
    entry: dict,
    phase: str,
    contributors: list[str],
    order: list[str],
) -> str | None:
    reviewer = reviewer_optional_for_phase(entry, phase)
    if not reviewer or not order or not contributors:
        return None
    if contributors[-1] == reviewer:
        return None

    ordinary_contributors = [role for role in contributors if role in order]
    if len(ordinary_contributors) < len(order):
        return None
    if ordinary_contributors[-len(order):] != order:
        return None
    return reviewer


def expected_speaker(entry: dict, contributors: list[str]) -> str:
    phase = entry['activePhase']
    order = effective_turn_order(entry)
    reviewer = reviewer_required_for_phase(entry, phase)
    if reviewer and all(contributors.count(role) >= 1 for role in order):
        if contributors.count(reviewer) < 1:
            return reviewer
    ordered_contributors = [role for role in contributors if role in order]
    if not ordered_contributors:
        return order[0]
    last = ordered_contributors[-1]
    return order[(order.index(last) + 1) % len(order)]


def speak_state_for_entry(entry: dict, transcript: str) -> dict:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    order = effective_turn_order(entry)
    expected = expected_speaker(entry, contributors)
    optional_reviewer = optional_reviewer_allowed_at_round_boundary(entry, phase, contributors, order)
    allowed_roles = [expected]
    if optional_reviewer and optional_reviewer not in allowed_roles:
        allowed_roles.append(optional_reviewer)
    state = {
        'target': entry['id'],
        'activePhase': phase,
        'turnOrder': order,
        'contributors': contributors,
        'lastContributor': contributors[-1] if contributors else None,
        'expectedRole': expected,
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'reviewerMode': reviewer_mode(entry) if reviewer_role(entry) else None,
        'reviewerOptionalPhases': reviewer_optional_phases(entry) if reviewer_role(entry) else [],
        'allowedRoles': allowed_roles,
        'autoAdvanceExempt': phase in AUTO_ADVANCE_EXEMPT_PHASES,
        'freshRegistryRead': True,
        'freshTranscriptRead': True,
    }
    expected_agent_id = participant_agent_id(entry, expected)
    if expected_agent_id:
        state['expectedAgentId'] = expected_agent_id
    if reviewer_role(entry):
        state['uncheckedAssignedItemsByRole'] = unchecked_assigned_items_by_role(transcript)
    return state


def blocked_resume_state_for_entry(entry: dict, transcript: str) -> dict:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    state = {
        'target': entry['id'],
        'activePhase': phase,
        'turnOrder': effective_turn_order(entry),
        'contributors': contributors,
        'lastContributor': contributors[-1] if contributors else None,
        'expectedRole': None,
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'reviewerMode': reviewer_mode(entry) if reviewer_role(entry) else None,
        'reviewerOptionalPhases': reviewer_optional_phases(entry) if reviewer_role(entry) else [],
        'allowedRoles': [],
        'autoAdvanceExempt': phase in AUTO_ADVANCE_EXEMPT_PHASES,
        'freshRegistryRead': True,
        'freshTranscriptRead': True,
    }
    requested_agent_id = participant_agent_id(entry, entry.get('moderatorRole', ''))
    if requested_agent_id:
        state['moderatorAgentId'] = requested_agent_id
    if reviewer_role(entry):
        state['uncheckedAssignedItemsByRole'] = unchecked_assigned_items_by_role(transcript)
    return state


def validate_registry(data: dict, path: Path | None = None) -> None:
    source = str(path) if path else 'registry'
    if not isinstance(data, dict):
        die(f'{source}: root must be an object')
    old_root_keys = sorted(OLD_ROOT_KEYS.intersection(data))
    if old_root_keys:
        die(f'{source}: old registry keys are not allowed: {old_root_keys}')
    if data.get('schemaVersion') != 1:
        die(f'{source}: schemaVersion must be 1')
    revision = data.get('revision', 0)
    if not isinstance(revision, int) or revision < 0:
        die(f'{source}: revision must be a non-negative integer when present')

    collabs = data.get('collabs')
    if not isinstance(collabs, list):
        die(f'{source}: collabs must be a list')

    active_id = data.get('activeCollabId')
    ids: list[str] = []
    slugs: list[str] = []
    sequences: list[int] = []
    collab_map: dict[str, dict] = {}

    for entry in collabs:
        if not isinstance(entry, dict):
            die(f'{source}: collab entry must be an object')
        old_entry_keys = sorted(OLD_ENTRY_KEYS.intersection(entry))
        if old_entry_keys:
            die(f'{source}: old collab keys are not allowed: {old_entry_keys}')

        collab_id = entry.get('id')
        slug = entry.get('slug')
        title = entry.get('title')
        description = entry.get('description')
        status = entry.get('status')
        activePhase = entry.get('activePhase')
        moderatorRole = entry.get('moderatorRole')
        participants = entry.get('participants')
        turnOrder = entry.get('turnOrder')
        transcriptPath = entry.get('transcriptPath')
        reviewerRole = entry.get('reviewerRole')
        sequence = entry.get('sequence')

        for field, value in (
            ('id', collab_id),
            ('slug', slug),
            ('title', title),
            ('description', description),
            ('status', status),
            ('activePhase', activePhase),
            ('moderatorRole', moderatorRole),
            ('transcriptPath', transcriptPath),
        ):
            if not isinstance(value, str) or not value.strip():
                die(f'{source}: collab {field} must be a non-empty string')

        if not ID_RE.match(collab_id):
            die(f'{source}: collab id must use YYYY-MM-DD-<slug>')
        expected_path = f'.collabs/records/{collab_id}.md'
        if transcriptPath != expected_path:
            die(f'{source}: transcriptPath must match .collabs/records/<id>.md')
        if collab_id[11:] != slug:
            die(f'{source}: collab id suffix must match slug')
        if status not in ALLOWED_STATUSES:
            die(f'{source}: collab status must be one of {sorted(ALLOWED_STATUSES)}')
        if activePhase not in PHASES:
            die(f'{source}: collab activePhase must be one of {PHASES}')
        if not isinstance(entry.get('archived'), bool):
            die(f'{source}: collab archived must be a boolean')
        if sequence is not None:
            if not isinstance(sequence, int) or sequence < 1:
                die(f'{source}: collab sequence must be a positive integer when present')
            sequences.append(sequence)

        if not isinstance(participants, list) or not participants:
            die(f'{source}: participants must be a non-empty list')
        if not all(
            isinstance(p, dict)
            and isinstance(p.get('role'), str) and p['role'].strip()
            and isinstance(p.get('agentId'), str) and p['agentId'].strip()
            for p in participants
        ):
            die(f'{source}: participants must contain objects with non-empty role string and agentId string')
        participant_role_keys = [p['role'] for p in participants]
        if len(set(participant_role_keys)) != len(participant_role_keys):
            die(f'{source}: participants must not contain duplicate roles')
        if moderatorRole not in participant_role_keys:
            die(f'{source}: moderatorRole must be listed in participants')

        if not isinstance(turnOrder, list) or not turnOrder:
            die(f'{source}: turnOrder must be a non-empty list')
        if not all(isinstance(role, str) and role.strip() for role in turnOrder):
            die(f'{source}: turnOrder must contain non-empty role strings')
        if len(set(turnOrder)) != len(turnOrder):
            die(f'{source}: turnOrder must not contain duplicates')
        if not set(turnOrder).issubset(set(participant_role_keys)):
            die(f'{source}: turnOrder must stay within participants')

        if reviewerRole is not None:
            if not isinstance(reviewerRole, str) or not reviewerRole.strip():
                die(f'{source}: reviewerRole must be absent or a non-empty string')
            if reviewerRole == moderatorRole:
                die(f'{source}: reviewerRole must not equal moderatorRole')

            mode = reviewer_mode(entry)
            if mode not in ALLOWED_REVIEWER_MODES:
                die(f'{source}: reviewerMode must be one of {sorted(ALLOWED_REVIEWER_MODES)}')
            if mode == 'last-in-convergent-phases' and reviewerRole in turnOrder:
                die(f'{source}: reviewerRole must not appear in turnOrder')

            optional_phases = entry.get('reviewerOptionalPhases', DEFAULT_REVIEWER_OPTIONAL_PHASES)
            if not isinstance(optional_phases, list):
                die(f'{source}: reviewerOptionalPhases must be a list when present')
            if not all(isinstance(phase, str) and phase in PHASES for phase in optional_phases):
                die(f'{source}: reviewerOptionalPhases must contain valid phase names')

        execution = entry.get('execution', {})
        if not isinstance(execution, dict):
            die(f'{source}: execution must be an object when present')
        for role, state in execution.items():
            if not isinstance(role, str) or not role.strip():
                die(f'{source}: execution keys must be non-empty role strings')
            if not isinstance(state, dict):
                die(f'{source}: execution state must be an object')
            if state.get('status') not in ALLOWED_EXECUTION_STATUSES:
                die(f'{source}: execution status must be one of {sorted(ALLOWED_EXECUTION_STATUSES)}')
            date = state.get('date')
            if not isinstance(date, str) or not date.strip():
                die(f'{source}: execution date must be a non-empty string')
            validation_result = state.get('validationResult')
            if validation_result is not None and (
                not isinstance(validation_result, str) or not validation_result.strip()
            ):
                die(f'{source}: execution validationResult must be a non-empty string when present')
            validation_scope = state.get('validationScope')
            if validation_scope is not None and validation_scope not in ALLOWED_VALIDATION_SCOPES:
                die(
                    f'{source}: execution validationScope must be one of '
                    f'{sorted(ALLOWED_VALIDATION_SCOPES)} when present'
                )
            touched_paths = state.get('touchedPaths', [])
            if not isinstance(touched_paths, list):
                die(f'{source}: execution touchedPaths must be a list when present')
            if any(not isinstance(item, str) or not item.strip() for item in touched_paths):
                die(f'{source}: execution touchedPaths must contain non-empty strings')
            entry_id = state.get('entryId')
            if entry_id is not None and (not isinstance(entry_id, str) or not entry_id.strip()):
                die(f'{source}: execution entryId must be a non-empty string when present')

        completion = entry.get('completion')
        if completion is not None:
            if not isinstance(completion, dict):
                die(f'{source}: completion must be an object when present')
            substate = completion.get('subState')
            if substate is not None and substate not in ALLOWED_COMPLETION_SUBSTATES:
                die(f'{source}: completion.subState must be one of {sorted(ALLOWED_COMPLETION_SUBSTATES)}')

        verification = entry.get('verification')
        if verification is not None:
            if not isinstance(verification, dict):
                die(f'{source}: verification must be an object when present')
            rounds = verification.get('rounds', 0)
            cap = verification.get('cap', DEFAULT_VERIFICATION_CAP)
            if not isinstance(rounds, int) or rounds < 0:
                die(f'{source}: verification.rounds must be a non-negative integer when present')
            if not isinstance(cap, int) or cap < 1:
                die(f'{source}: verification.cap must be a positive integer when present')

        verification_seal = entry.get('verificationSeal')
        if verification_seal is not None:
            if not isinstance(verification_seal, dict):
                die(f'{source}: verificationSeal must be an object when present')
            if verification_seal.get('schemaVersion') != VERIFICATION_SEAL_SCHEMA_VERSION:
                die(f'{source}: verificationSeal.schemaVersion must be {VERIFICATION_SEAL_SCHEMA_VERSION}')
            observed = verification_seal.get('observedRevision')
            if not isinstance(observed, int) or observed < 0:
                die(f'{source}: verificationSeal.observedRevision must be a non-negative integer')
            sealed_at = verification_seal.get('sealedAt')
            sealed_by = verification_seal.get('sealedBy')
            if not isinstance(sealed_at, str) or not sealed_at.strip():
                die(f'{source}: verificationSeal.sealedAt must be a non-empty string')
            if not isinstance(sealed_by, str) or not sealed_by.strip():
                die(f'{source}: verificationSeal.sealedBy must be a non-empty string')
            if not isinstance(verification_seal.get('executionEntries'), list):
                die(f'{source}: verificationSeal.executionEntries must be a list')
            if not isinstance(verification_seal.get('validationScopes'), list):
                die(f'{source}: verificationSeal.validationScopes must be a list')
            if not isinstance(verification_seal.get('touchedPaths'), list):
                die(f'{source}: verificationSeal.touchedPaths must be a list')
            stale = verification_seal.get('stale')
            if stale is not None and not isinstance(stale, bool):
                die(f'{source}: verificationSeal.stale must be a boolean when present')
            cap_exit = verification_seal.get('capExit')
            if cap_exit is not None and cap_exit not in ALLOWED_CAP_EXITS:
                die(f'{source}: verificationSeal.capExit must be one of {sorted(ALLOWED_CAP_EXITS)}')

        handoff = entry.get('handoff')
        if handoff is not None:
            if not isinstance(handoff, dict):
                die(f'{source}: handoff must be an object when present')
            if handoff.get('schemaVersion') != HANDOFF_SCHEMA_VERSION:
                die(f'{source}: handoff schemaVersion must be {HANDOFF_SCHEMA_VERSION}')
            handoff_roles = handoff.get('roles')
            if not isinstance(handoff_roles, dict):
                die(f'{source}: handoff roles must be an object when present')
            for role, state in handoff_roles.items():
                if not isinstance(role, str) or not role.strip():
                    die(f'{source}: handoff role keys must be non-empty strings')
                if role not in participant_role_keys:
                    die(f'{source}: handoff role must already be a participant: {role}')
                validate_handoff_state(state, f'{source}: handoff.{role}')

        if collab_id in collab_map:
            die(f'{source}: duplicate collab id: {collab_id}')
        ids.append(collab_id)
        slugs.append(slug)
        collab_map[collab_id] = entry

    if len(ids) != len(set(ids)):
        die(f'{source}: duplicate collab ids are not allowed')
    if len(slugs) != len(set(slugs)):
        die(f'{source}: duplicate collab slugs are not allowed')
    if len(sequences) != len(set(sequences)):
        die(f'{source}: duplicate collab sequences are not allowed')

    if active_id is not None:
        if not isinstance(active_id, str) or not active_id.strip():
            die(f'{source}: activeCollabId must be null or a non-empty string')
        if active_id not in collab_map:
            die(f'{source}: activeCollabId must point at an existing collab id')
        if collab_map[active_id].get('archived'):
            die(f'{source}: activeCollabId must not point at an archived collab')


def resolve_collab(data: dict, target: str) -> dict:
    numeric_target = target[1:] if target.startswith('#') else target
    if numeric_target.isdigit():
        number = int(numeric_target)
        for index, entry in enumerate(data['collabs'], start=1):
            if entry.get('sequence', index) == number:
                return entry
        die(f'registry target not found: {target}')
    for entry in data['collabs']:
        if target in {entry['id'], entry['slug']}:
            return entry
    die(f'registry target not found: {target}')


def require_active_collab(data: dict) -> dict:
    active_id = data.get('activeCollabId')
    if not active_id:
        die('registry activeCollabId is empty')
    return resolve_collab(data, active_id)


def display_title(title: str, limit: int = 20) -> str:
    if len(title) <= limit:
        return title
    return title[:limit] + '…'


def collab_date(entry: dict) -> str:
    return entry['id'][:10]


def list_collabs(data: dict, status_filter: str | None = None) -> int:
    if status_filter is not None and status_filter not in ALLOWED_STATUSES:
        die(f'invalid status filter: {status_filter}')
    active_id = data.get('activeCollabId')
    indexed = [
        (index, entry)
        for index, entry in enumerate(data['collabs'], start=1)
        if status_filter is None or entry['status'] == status_filter
    ]
    indexed.sort(key=lambda item: (
        item[1]['id'] != active_id,
        -item[1].get('sequence', item[0]),
        item[1]['slug'],
    ))
    for output_index, (index, entry) in enumerate(indexed):
        marker = '[*]' if entry['id'] == active_id else '[ ]'
        number = entry.get('sequence', index)
        title = display_title(entry['title'])
        phase = entry['activePhase'] if entry['activePhase'] else '—'
        participant_label = 'participant' if len(entry['participants']) == 1 else 'participants'
        if output_index:
            print()
        print(f"{marker} #{number} - {entry['slug']}    {title}")
        print(
            f"         {entry['status']} · {phase} · "
            f"{len(entry['participants'])} {participant_label} · {collab_date(entry)}",
        )
    return 0


def add_participant_to_entry(entry: dict, role: str, agent_id: str = 'unknown') -> bool:
    if not role.strip():
        die('participant role must be non-empty')
    changed = False
    is_reviewer = role == reviewer_role(entry) and reviewer_mode(entry) == 'last-in-convergent-phases'
    if not has_participant(entry, role):
        entry['participants'].append({'role': role, 'agentId': agent_id})
        changed = True
    if not entry['turnOrder']:
        entry['turnOrder'] = [
            p['role'] for p in entry['participants']
            if not (
                p['role'] == reviewer_role(entry)
                and reviewer_mode(entry) == 'last-in-convergent-phases'
            )
        ]
        changed = True
    elif not is_reviewer and role not in entry['turnOrder']:
        entry['turnOrder'].append(role)
        changed = True
    return changed


def normalize_join_agent_id(agent_id: str | None) -> str:
    if agent_id is None:
        die('agent-id is required')
    normalized = agent_id.strip()
    if not normalized:
        die('agent-id is required')
    if normalized.lower() == 'unknown' and normalized != 'unknown':
        die('agent-id unknown token must be lowercase: unknown')
    if normalized.lower() in INVALID_AGENT_ID_ALTERNATIVES:
        die('agent-id must use the literal unknown when identity is unavailable')
    return normalized


def assert_caller_role(entry: dict, caller_role: str | None, action: str, subject_role: str | None = None) -> None:
    if caller_role is None:
        return
    if not has_participant(entry, caller_role):
        die(f'caller role must already be a participant: {caller_role}')
    if action in MODERATOR_ONLY_ACTIONS and caller_role != entry['moderatorRole']:
        die(f'{action} requires moderator role: {entry["moderatorRole"]}')
    if subject_role is not None and caller_role != subject_role:
        die(f'{action} caller role must match subject role: {subject_role}')


def effective_turn_order(entry: dict) -> list[str]:
    order = entry['turnOrder'] or participant_roles(entry)
    reviewer = reviewer_role(entry)
    if reviewer and reviewer_mode(entry) == 'last-in-convergent-phases':
        return [role for role in order if role != reviewer]
    return order


def next_phase_name(phase: str) -> str | None:
    index = PHASES.index(phase)
    if index == len(PHASES) - 1:
        return None
    return PHASES[index + 1]


def remove_moderator_from_turn_order(entry: dict, order: list[str] | None = None) -> None:
    moderator = entry['moderatorRole']
    source_order = order or effective_turn_order(entry)
    entry['turnOrder'] = [role for role in source_order if role != moderator]
    if not entry['turnOrder']:
        entry['turnOrder'] = [r for r in participant_roles(entry) if r != moderator]
    if not entry['turnOrder']:
        die('turnOrder cannot be empty after removing moderator')


def phase_turn_order(entry: dict, phase: str) -> list[str]:
    reviewer = reviewer_role(entry) if reviewer_mode(entry) == 'last-in-convergent-phases' else None
    roles = [role for role in participant_roles(entry) if role != reviewer]
    if phase in MOD_EXCLUDED_PHASES:
        roles = [role for role in roles if role != entry['moderatorRole']]
    elif entry['moderatorRole'] in roles:
        roles = [entry['moderatorRole']] + [role for role in roles if role != entry['moderatorRole']]
    if not roles:
        die(f'turnOrder cannot be empty for phase: {phase}')
    return roles


def normalize_turn_order_for_phase(entry: dict, phase: str) -> None:
    entry['turnOrder'] = phase_turn_order(entry, phase)


def transition_notice(from_phase: str, to_phase: str) -> dict | None:
    transition = f'{from_phase}->{to_phase}'
    if transition == 'Discussion->Conclusion':
        return {
            'notice': 'compact',
            'transition': transition,
            'message': 'Run /compact before continuing to Conclusion.',
        }
    if transition == 'Conclusion->Action Plan':
        return {
            'notice': 'action-plan-shape',
            'transition': transition,
            'message': (
                'Action Plan entries must follow _invariants.md Invariant #9: '
                r'^- \[[ x]\] \*\*[a-z]+:\*\*.'
            ),
        }
    if transition == 'Handoff->Completion':
        return {
            'notice': 'subagent',
            'transition': transition,
            'message': 'Use a subagent or compacted execution context before /collab run plan.',
        }
    return None


def discussion_turn_notice(entry: dict, contributors: list[str]) -> dict | None:
    if entry['activePhase'] != 'Discussion' or not contributors:
        return None
    if contributors[-1] == entry['moderatorRole']:
        return None
    # This is advisory visibility only. The helper cannot observe or orchestrate /compact.
    return {
        'compactBeforeNextCommand': True,
        'notice': 'compact',
        'transition': 'Discussion-turn',
        'message': 'Run /compact before issuing your next collab command.',
    }


def terminal_notice(status: str) -> dict:
    return {
        'notice': 'clear',
        'status': status,
        'message': 'Run /clear before starting another collab.',
    }


def notice_message(notice: dict) -> str:
    message = notice.get('message')
    if isinstance(message, str) and message.strip():
        return message.strip()
    notice_type = notice.get('notice')
    if isinstance(notice_type, str) and notice_type.strip():
        return notice_type.strip()
    return 'Lifecycle notice emitted.'


def print_notice_diagnostic(notice: dict | None, emit_json: bool) -> None:
    if not notice:
        return
    if not emit_json:
        print(f'NOTICE: {notice_message(notice)}')
    if emit_json:
        print(json.dumps(notice, sort_keys=True))


def print_lifecycle_diagnostic(lifecycle: dict, emit_json: bool) -> None:
    phase_state = lifecycle.get('phaseState')
    if phase_state:
        print(f'PHASE: {phase_state}')
    notice = lifecycle.get('notice')
    if isinstance(notice, dict):
        print_notice_diagnostic(notice, emit_json)
    if emit_json:
        print(json.dumps(lifecycle, sort_keys=True))


def print_phase_result(phase: str, notice: dict | None = None, emit_json: bool = True) -> None:
    print(phase)
    print_notice_diagnostic(notice, emit_json)


def resume_command(entry: dict, role: str) -> str:
    return f'RESUME: tools/collab/registry.py speak-state --resume {entry["id"]} {role}'


def die_with_resume(message: str, entry: dict, role: str) -> None:
    die(f'{message}\n{resume_command(entry, role)}')


def completion_summary_empty(transcript: str) -> bool:
    try:
        lines = phase_section(transcript, 'Completion')
    except SystemExit as exc:
        if str(exc) == 'transcript phase missing: Completion':
            return True
        raise
    saw_execution_history = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == CONTENT_ONLY_GUARD:
            continue
        if SUMMARY_HEADING_RE.match(stripped):
            return False
        if stripped == '**Execution history**':
            saw_execution_history = True
            continue
        if saw_execution_history and re.match(r'^\d+\.\s+\*\*[^*]+:\*\*\s+', stripped):
            continue
        if stripped.startswith('<') and stripped.endswith('>'):
            continue
        return False
    return True


def forced_active_phase_advisory(entry: dict, transcript: str) -> str:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    live = ', '.join(contributors) if contributors else 'none'
    return (
        f'RECOVERY-ADVISORY: active-phase --force post-check for {entry["id"]}; '
        f'live contributors in {phase}: {live}; '
        f'tombstones: {tombstone_count(transcript)}; '
        f'pending rewrites: manual-check; '
        f'active Action Plan labels: {action_plan_label_summary(transcript)}.'
    )


def add_completion_summary_notice(notice: dict | None, transcript: str) -> dict | None:
    if notice and notice.get('transition') == 'Handoff->Completion' and completion_summary_empty(transcript):
        notice = dict(notice)
        notice['summaryEmpty'] = True
    return notice


def next_line_for_state(entry: dict, transcript: str | None = None) -> str:
    if entry['status'] == 'closed':
        return 'NEXT: Collab closed; run /clear before starting another collab.'
    if entry['status'] == 'archived':
        return 'NEXT: Collab archived; run /clear before starting another collab.'
    phase = entry['activePhase']
    if phase == 'Completion':
        return f"NEXT: Run /collab run plan for role {effective_turn_order(entry)[0]}."
    if transcript is None:
        try:
            transcript = read_transcript_for_entry(entry)
        except SystemExit:
            order = effective_turn_order(entry)
            if order:
                return f'NEXT: Run /collab speak for role {order[0]}.'
            return f'NEXT: Active phase is {phase}.'
    try:
        state = speak_state_for_entry(entry, transcript)
    except SystemExit:
        order = effective_turn_order(entry)
        if order:
            return f'NEXT: Run /collab speak for role {order[0]}.'
        return f'NEXT: Active phase is {phase}.'
    expected = state.get('expectedRole')
    if expected:
        return f'NEXT: Run /collab speak for role {expected}.'
    return f'NEXT: Active phase is {phase}.'


def next_line_after_speak(entry: dict, role: str, phase: str, transcript: str) -> str:
    if phase == 'Discussion':
        return f'NEXT: Run /compact before your next collab command for role {role}.'
    return next_line_for_state(entry, transcript)


def load_effort_defaults(path: Path) -> dict:
    if not path.exists():
        die(f'effort source missing: {path}')
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f'effort source invalid JSON: {path}: {exc}')
    matrix = data.get('matrix')
    if not isinstance(matrix, dict):
        die(f'effort source missing matrix: {path}')
    levels = data.get('levels')
    if levels is not None and not isinstance(levels, dict):
        die(f'effort source levels must be an object: {path}')
    return data


def effort_value(defaults: dict, phase: str, role: str) -> str | None:
    matrix = defaults['matrix']
    if phase not in matrix or not isinstance(matrix[phase], dict):
        die(f'effort source missing phase: {phase}')
    phase_defaults = matrix[phase]
    if role not in phase_defaults:
        return DEFAULT_OPEN_ROSTER_EFFORT
    effort = phase_defaults[role]
    if effort is not None and not isinstance(effort, str):
        die(f'effort source invalid value for role {role} in phase {phase}')
    return effort


def effort_phrase(defaults: dict, effort: str | None, phase: str, role: str) -> str:
    if effort is None:
        return f'{role} is not on the turn-order roster for {phase}'
    levels = defaults.get('levels', {})
    phrase = levels.get(effort) if isinstance(levels, dict) else None
    if not isinstance(phrase, str) or not phrase.strip():
        die(f'effort source missing level phrase: {effort}')
    return phrase.strip()


def effort_line(defaults: dict, phase: str, role: str) -> str:
    effort = effort_value(defaults, phase, role)
    phrase = effort_phrase(defaults, effort, phase, role)
    label = effort if effort is not None else 'not-on-roster'
    return f'EFFORT: {label} for {role} in {phase} \u2014 next-turn recommendation; {phrase}.'


def effort_phase_after_speak(source_phase: str) -> str:
    if source_phase == 'Discussion':
        return 'Conclusion'
    if source_phase in ONE_SPEAK_PHASES:
        next_phase = next_phase_name(source_phase)
        if next_phase:
            return next_phase
    return source_phase


def efficiency_line_from_notice(notice: dict | None) -> str | None:
    if not notice:
        return None
    notice_type = notice.get('notice')
    transition = notice.get('transition')
    status = notice.get('status')
    if notice_type == 'compact' and transition in {'Discussion-turn', 'Discussion->Conclusion'}:
        return 'EFFICIENCY: Run /compact before next collab command.'
    if notice_type == 'subagent' and transition == 'Handoff->Completion':
        return 'EFFICIENCY: Run /compact, then prepare or use the assigned subagent work.'
    if notice_type == 'clear' or status in {'closed', 'archived'}:
        return 'EFFICIENCY: Run /clear before starting another collab.'
    return None


def post_action_advisory_lines(
    entry: dict,
    role: str | None,
    effort_phase: str | None,
    notice: dict | None,
    next_line: str,
    effort_path: Path = DEFAULT_EFFORT_PATH,
) -> list[str]:
    lines = [next_line]
    if role and entry['status'] not in {'closed', 'archived'}:
        lines.append(resume_command(entry, role))
    if role and effort_phase:
        defaults = load_effort_defaults(effort_path)
        lines.append(effort_line(defaults, effort_phase, role))
    efficiency = efficiency_line_from_notice(notice)
    if efficiency:
        lines.append(efficiency)
    if notice and notice.get('summaryEmpty'):
        lines.append('COMPLETION-ADVISORY: Completion section has no summary prose.')
    return lines


def print_post_action_advisories(
    entry: dict,
    role: str | None,
    effort_phase: str | None,
    notice: dict | None,
    next_line: str,
) -> None:
    for line in post_action_advisory_lines(entry, role, effort_phase, notice, next_line):
        print(line)


def effort_state(path: Path, target: str, role: str, effort_defaults_path: Path) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if not has_participant(entry, role):
        die(f'effort role must already be a participant: {role}')
    defaults = load_effort_defaults(effort_defaults_path)
    phase = entry['activePhase']
    effort = effort_value(defaults, phase, role)
    result = {
        'advisory': True,
        'effort': effort,
        'phase': phase,
        'role': role,
        'source': str(effort_defaults_path),
        'target': entry['id'],
    }
    if effort is None:
        result['notOnRoster'] = True
    print(json.dumps(result, sort_keys=True))
    return 0


def apply_speak_lifecycle_to_entry(entry: dict, contributors: list[str]) -> bool:
    phase = entry['activePhase']
    order = effective_turn_order(entry)
    reviewer = reviewer_required_for_phase(entry, phase)
    required_roles = list(order)
    if reviewer:
        required_roles.append(reviewer)
    counts = {role: contributors.count(role) for role in required_roles}

    if phase in ONE_SPEAK_PHASES:
        duplicates = [role for role, count in counts.items() if count > 1]
        if duplicates:
            die(f'duplicate contribution in one-speak phase {phase}: {duplicates[0]}')
        if optional_reviewer_allowed_at_round_boundary(entry, phase, contributors, order):
            return False

    if phase in AUTO_ADVANCE_EXEMPT_PHASES or not all(counts.get(role, 0) >= 1 for role in required_roles):
        return False

    next_phase = next_phase_name(phase)
    if next_phase is None:
        return False
    entry['activePhase'] = next_phase
    if next_phase in MOD_EXCLUDED_PHASES:
        remove_moderator_from_turn_order(entry, order)
    if next_phase == 'Completion':
        initialize_completion_state(entry, 'execution', reset_rounds=True)
    return True


def apply_speak_lifecycle_with_notice(entry: dict, contributors: list[str]) -> tuple[bool, dict | None]:
    from_phase = entry['activePhase']
    advanced = apply_speak_lifecycle_to_entry(entry, contributors)
    notice = transition_notice(from_phase, entry['activePhase']) if advanced else None
    if not notice and from_phase == 'Discussion':
        notice = discussion_turn_notice(entry, contributors)
    return advanced, notice


def close_eligible_after_execution(entry: dict, assigned_roles: list[str]) -> bool:
    roles = [role for role in assigned_roles if role != entry['moderatorRole']]
    if not roles:
        return False
    execution = entry.get('execution', {})
    completed = all(execution.get(role, {}).get('status') == 'completed' for role in roles)
    if not completed:
        return False
    if reviewer_backed(entry):
        seal = entry.get('verificationSeal')
        return isinstance(seal, dict) and not seal.get('stale')
    return True


def next_line_after_execution(entry: dict, assigned_roles: list[str]) -> str:
    if entry['status'] in {'closed', 'archived'}:
        return next_line_for_state(entry)
    execution = entry.get('execution', {})
    for assigned_role in assigned_roles:
        if assigned_role == entry['moderatorRole']:
            continue
        if execution.get(assigned_role, {}).get('status') != 'completed':
            return f'NEXT: Run /collab run plan for role {assigned_role}.'
    if reviewer_backed(entry):
        return f'NEXT: Run /collab seal verification for role {reviewer_role(entry)}.'
    return next_line_for_state(entry)


def activate_collab(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['archived']:
            die(f'registry target archived: {target}')
        data['activeCollabId'] = entry['id']
        save_registry(path, data)
    print(entry['id'])
    return 0


def set_field(
    path: Path,
    target: str,
    field: str,
    value: str | None,
    force: bool,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    force_advisory: str | None = None
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'set')
        forced_active_phase = False
        if field in FORCE_ONLY_FIELDS:
            if value is None:
                die(f'{field} requires a value')
            if not force:
                die(f'field requires --force: {field}')
            if field == 'active-phase':
                if value not in PHASES:
                    die(f'active-phase must be one of {PHASES}')
                entry['activePhase'] = value
                forced_active_phase = True
        elif field == 'reviewer':
            if value == '--clear':
                clear_reviewer(entry)
            else:
                if value is None:
                    die('reviewer requires a role or --clear')
                if not has_participant(entry, value):
                    die('reviewer must already be a participant')
                if value == entry['moderatorRole']:
                    die('reviewer must not be the moderator')
                if value in entry['turnOrder']:
                    die('reviewer must not appear in turnOrder')
                entry['reviewerRole'] = value
                entry['reviewerMode'] = DEFAULT_REVIEWER_MODE
                entry.setdefault('reviewerOptionalPhases', list(DEFAULT_REVIEWER_OPTIONAL_PHASES))
        elif field == 'reviewer-optional-phases':
            if not reviewer_role(entry):
                die('reviewer-optional-phases requires reviewerRole')
            entry['reviewerOptionalPhases'] = parse_reviewer_optional_phases(value)
        elif field not in ALLOWED_SET_FIELDS:
            die(f'field not settable: {field}')
        elif field == 'turn-order':
            if value is None:
                die('turn-order requires a value')
            turnOrder = value.split()
            if not turnOrder:
                die('turn-order requires at least one role')
            if len(set(turnOrder)) != len(turnOrder):
                die('turn-order roles must be unique')
            if not set(turnOrder).issubset(set(participant_roles(entry))):
                die('turn-order roles must already be participants')
            reviewer = reviewer_role(entry)
            if reviewer and reviewer in turnOrder:
                die('turn-order must not include reviewerRole')
            entry['turnOrder'] = turnOrder
        else:
            if value is None:
                die(f'{field} requires a value')
            if not value.strip():
                die(f'{field} requires a non-empty value')
            entry[field] = value
        transcript_path = Path(entry['transcriptPath'])
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, roles_dir)
            if forced_active_phase:
                force_advisory = forced_active_phase_advisory(entry, rendered)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print(entry['id'])
    if force_advisory:
        print(force_advisory)
    return 0


def clear_reviewer(entry: dict) -> bool:
    changed = False
    for key in ('reviewerRole', 'reviewerMode', 'reviewerOptionalPhases'):
        if key in entry:
            entry.pop(key)
            changed = True
    return changed


def unset_field(
    path: Path,
    target: str,
    field: str,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    if field != 'reviewer':
        die(f'field not unsettable: {field}')

    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'unset')
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')

        next_data = deepcopy(data)
        next_entry = resolve_collab(next_data, target)
        clear_reviewer(next_entry)
        validate_registry(next_data, path)

        transcript_path = Path(next_entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), next_entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, next_data, transcript_path, rendered)
    print(next_entry['id'])
    return 0


def speak_lifecycle(path: Path, target: str, contributors: list[str]) -> int:
    if not contributors:
        die('contributors requires at least one role')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        for role in contributors:
            if not has_participant(entry, role):
                die(f'contributor must already be a participant: {role}')
        advanced, notice = apply_speak_lifecycle_with_notice(entry, contributors)
        transcript_path = Path(entry['transcriptPath'])
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
            notice = add_completion_summary_notice(notice, rendered)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_phase_result(entry['activePhase'] if advanced else 'unchanged', notice)
    return 0


def read_transcript_for_entry(entry: dict) -> str:
    transcript_path = Path(entry['transcriptPath'])
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')
    return transcript_path.read_text()


def speak_state(path: Path, target: str, role: str, resume: bool = False) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if entry['status'] in {'closed', 'archived'}:
        die('record is closed')
    if not has_participant(entry, role):
        die(f'role must already be a participant: {role}')
    transcript = read_transcript_for_entry(entry)
    pending_reviewer = pending_reviewer_role(entry)
    if pending_reviewer:
        if resume:
            state = blocked_resume_state_for_entry(entry, transcript)
            state['roleAgentId'] = participant_agent_id(entry, role)
            state['readyToWrite'] = False
            state['registryRevision'] = registry_revision(data)
            print(json.dumps(state, sort_keys=True))
            return 0
        die_with_resume(f'pending reviewerRole: {pending_reviewer}', entry, role)
    state = speak_state_for_entry(entry, transcript)
    state['roleAgentId'] = participant_agent_id(entry, role)
    state['readyToWrite'] = role in state['allowedRoles']
    state['registryRevision'] = registry_revision(data)
    if resume:
        print(json.dumps(state, sort_keys=True))
        return 0
    if role not in state['allowedRoles']:
        if role == reviewer_optional_for_phase(entry, entry['activePhase']):
            die_with_resume('reviewer may speak after all turn-order participants have contributed in this round', entry, role)
        die_with_resume(f"expected role: {state['expectedRole']}", entry, role)
    print(json.dumps(state, sort_keys=True))
    return 0


def normalize_scope_path(raw: str, label: str) -> str:
    if not raw or not raw.strip():
        die(f'{label} must be non-empty')
    value = raw.strip()
    if Path(value).is_absolute():
        die(f'{label} must be repository-relative: {raw}')
    normalized = PurePosixPath(Path(value).as_posix())
    parts = normalized.parts
    if not parts or any(part in {'', '.', '..'} for part in parts):
        die(f'{label} must be a normalized repository-relative path: {raw}')
    return normalized.as_posix()


def path_is_within(path: str, scope: str) -> bool:
    return path == scope or path.startswith(f'{scope}/')


def scope_matches_declared(scope: str, declared: str) -> bool:
    if GLOB_PATTERN_RE.search(declared):
        return fnmatch.fnmatchcase(scope, declared)
    return path_is_within(scope, declared)


def assert_disjoint_scopes(scopes: list[str]) -> None:
    if not scopes:
        die('execute-spawn requires at least one --scope')
    if len(scopes) != len(set(scopes)):
        die('execute-spawn scopes must be unique')
    for index, left in enumerate(scopes):
        for right in scopes[index + 1:]:
            if path_is_within(left, right) or path_is_within(right, left):
                die(f'execute-spawn scopes must be disjoint: {left} {right}')


def execute_spawn(
    path: Path,
    target: str,
    role: str,
    scope: str | None,
    sibling_scopes: list[str],
    returned_paths: list[str],
) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if entry['status'] in {'closed', 'archived'}:
        die('record is closed')
    if entry['activePhase'] != 'Completion':
        die('execute-spawn is valid only in Completion')
    if not has_participant(entry, role):
        die(f'execution role must already be a participant: {role}')
    if scope is None:
        die('execute-spawn requires --scope')
    normalized_scope = normalize_scope_path(scope, 'scope')
    normalized_siblings = [normalize_scope_path(item, 'sibling-scope') for item in sibling_scopes]
    normalized_scopes = [normalized_scope, *normalized_siblings]
    handoff_state = handoff_state_for_role(entry, role)
    if handoff_state is not None:
        declared_scopes = handoff_state['writeScope']
        for declared_scope in normalized_scopes:
            if not any(scope_matches_declared(declared_scope, declared) for declared in declared_scopes):
                die(f'execute-spawn scope outside declared writeScope: {declared_scope}')
    assert_disjoint_scopes(normalized_scopes)
    normalized_returned = [normalize_scope_path(item, 'returned-path') for item in returned_paths]
    for returned_path in normalized_returned:
        if not path_is_within(returned_path, normalized_scope):
            die(f'returned path outside assigned scope: {returned_path}')
    print('ok')
    return 0


def transcript_repair(
    path: Path,
    target: str,
    touch_execution_evidence: bool,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'set')
        if touch_execution_evidence:
            invalidate_verification_seal(entry, 'transcript repair touched execution evidence')
        save_registry(path, data)
    print('ok')
    return 0


def out_of_scope_patch(
    path: Path,
    target: str,
    role: str,
    patch_path: str,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'execution', role)
        if not has_participant(entry, role):
            die(f'execution role must already be a participant: {role}')
        normalized_path = normalize_scope_path(patch_path, 'path')
        handoff_state = handoff_state_for_role(entry, role)
        if handoff_state is None:
            die(f'handoff writeScope missing for role: {role}')
        if any(scope_matches_declared(normalized_path, declared) for declared in handoff_state['writeScope']):
            die(f'out-of-scope patch path is inside declared writeScope: {normalized_path}')
        invalidate_verification_seal(entry, f'out-of-scope patch outside declared writeScope: {normalized_path}')
        save_registry(path, data)
    print('ok')
    return 0


def speak_lifecycle_live(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        state = speak_state_for_entry(entry, transcript)
        advanced, notice = apply_speak_lifecycle_with_notice(entry, state['contributors'])
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_phase_result(entry['activePhase'] if advanced else 'unchanged', notice)
    return 0


def read_content_file(path: Path) -> str:
    if not path.exists():
        die(f'content file missing: {path}')
    content = path.read_text()
    if not content.strip():
        die('content must be non-empty')
    return content.rstrip('\n')


def read_budget_spec(path: Path = DEFAULT_BUDGET_PATH) -> dict:
    if not path.exists():
        die(f'contribution budget spec missing: {path}')
    text = path.read_text()
    limit_match = re.search(r'capped at \*\*(\d+) words\*\*', text)
    if not limit_match:
        die(f'contribution budget spec missing word limit: {path}')
    classes = set(re.findall(r'\|\s*`([a-z0-9-]+)`\s*\|', text))
    required = {'action-plan-checklist', 'conclusion-ratification', 'moderator-verbatim', 'effort-override-line'}
    missing = required - classes
    if missing:
        die(f'contribution budget spec missing exempt class: {sorted(missing)[0]}')
    return {'limit': int(limit_match.group(1)), 'classes': classes}


def is_conclusion_ratification_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r'^\d+\.\s+\*\*[^*]+:\*\*\s+\S', stripped):
        return True
    return bool(re.match(r'^-\s+\*\*[^*]+:\*\*\s+\S', stripped))


def budget_countable_lines(content: str, phase: str) -> list[str]:
    countable: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == '<!-- collab:content-only; do-not-execute -->':
            continue
        if TIMESTAMP_RE.match(stripped):
            continue
        if EFFORT_OVERRIDE_RE.match(stripped):
            continue
        if EFFORT_OVERRIDE_COMMENT_RE.match(stripped):
            continue
        if phase == 'Action Plan' and ACTION_PLAN_EXEMPT_RE.match(line):
            continue
        if phase == 'Conclusion' and is_conclusion_ratification_line(line):
            continue
        countable.append(line)
    return countable


def enforce_contribution_budget(
    content: str,
    phase: str,
    role: str,
    moderator_role: str,
    verbatim: bool,
    spec_path: Path = DEFAULT_BUDGET_PATH,
) -> None:
    spec = read_budget_spec(spec_path)
    if verbatim or role == moderator_role:
        return
    countable_text = '\n'.join(budget_countable_lines(content, phase))
    count = len(countable_text.split())
    limit = spec['limit']
    if count > limit:
        die(f'contribution body is {count} words; limit is {limit}')


def action_plan_label_advisory(content: str, phase: str) -> str | None:
    if phase != 'Action Plan':
        return None
    count = sum(1 for line in content.splitlines() if UNLABELED_ACTION_CHECKBOX_RE.match(line))
    if not count:
        return None
    item = 'item' if count == 1 else 'items'
    return (
        f'LABEL-ADVISORY: {count} unlabeled Action Plan checklist {item}; '
        'use **<role>:** labels for executable work.'
    )


def is_markdown_heading(line: str) -> bool:
    return bool(re.match(r'^\s{0,3}#{1,6}(?:\s|$)', line))


def action_plan_shape_abort(line_number: int, line: str) -> None:
    die(
        f"ABORT: line {line_number} does not match Action Plan shape '- [ ] **<role>:** ...' "
        f"(Invariant #9, _invariants.md). Offending line: '{line}'. "
        f"Example: '{ACTION_PLAN_SHAPE_EXAMPLE}'"
    )


def validate_action_plan_shape(content: str, phase: str) -> None:
    if phase != 'Action Plan':
        return
    saw_assignment = False
    in_html_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if in_html_comment:
            if '-->' in stripped:
                in_html_comment = False
            continue
        if stripped.startswith('<!--'):
            if '-->' not in stripped[stripped.find('<!--') + 4:]:
                in_html_comment = True
            continue
        if not stripped:
            continue
        if line_number == 1 and EFFORT_OVERRIDE_RE.match(stripped):
            continue
        if is_markdown_heading(line):
            continue
        if ACTION_PLAN_SHAPE_RE.match(line):
            saw_assignment = True
            continue
        action_plan_shape_abort(line_number, line)
    if not saw_assignment:
        die(
            'ABORT: Action Plan body contains no assignment lines after exempt content is removed '
            f"(Invariant #9, _invariants.md). Example: '{ACTION_PLAN_SHAPE_EXAMPLE}'"
        )


def validate_effort_override(content: str, phase: str, role: str, moderator_role: str) -> None:
    if role == moderator_role:
        return
    lines = content.splitlines()
    first_line = lines[0].strip() if lines else ''
    override_lines = [
        (index, line.strip())
        for index, line in enumerate(lines)
        if line.strip().startswith('EFFORT OVERRIDE:')
    ]
    if (phase, role) in MANDATORY_EFFORT_OVERRIDE_TURNS and not override_lines:
        die(f'effort override required for {phase}-{role}')
    if not override_lines:
        return
    first_index, first_override = override_lines[0]
    if first_index != 0:
        die('EFFORT OVERRIDE must be the first content line')
    if not EFFORT_OVERRIDE_RE.match(first_override):
        die('EFFORT OVERRIDE line has invalid format')
    if len(override_lines) > 1:
        die('EFFORT OVERRIDE must appear at most once')


def effort_override_metadata_comment(line: str) -> str:
    payload = base64.urlsafe_b64encode(line.encode()).decode()
    return f'<!-- collab:effort-override b64:{payload} -->'


def effort_override_from_metadata_comment(line: str) -> str | None:
    match = EFFORT_OVERRIDE_COMMENT_RE.match(line.strip())
    if not match:
        return None
    try:
        return base64.urlsafe_b64decode(match.group('payload').encode()).decode()
    except (ValueError, UnicodeDecodeError):
        die('EFFORT OVERRIDE metadata is invalid')


def effort_override_audit_items(target: str, transcript: str) -> list[dict]:
    findings: list[dict] = []
    for phase in PHASES:
        try:
            lines = phase_section(transcript, phase)
        except SystemExit:
            continue
        details_depth = 0
        current_role: str | None = None
        current_override: str | None = None
        for line in lines:
            stripped = line.strip()
            if DETAILS_OPEN_RE.match(stripped):
                details_depth += 1
                if details_depth == 1:
                    current_role = None
                    current_override = None
                continue
            if DETAILS_CLOSE_RE.match(stripped):
                if details_depth == 1 and current_role:
                    mandatory = (phase, current_role) in MANDATORY_EFFORT_OVERRIDE_TURNS
                    if mandatory or current_override:
                        item = {
                            'target': target,
                            'phase': phase,
                            'role': current_role,
                            'mandatory': mandatory,
                            'hasOverride': current_override is not None,
                        }
                        if current_override:
                            item['effortOverride'] = current_override
                        findings.append(item)
                details_depth = max(0, details_depth - 1)
                continue
            if details_depth != 1:
                continue
            role = summary_role(line)
            if role is not None:
                current_role = role
                continue
            override = effort_override_from_metadata_comment(stripped)
            if override:
                current_override = override
    return findings


def render_content_for_transcript(content: str) -> list[str]:
    rendered: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if EFFORT_OVERRIDE_RE.match(stripped):
            rendered.append(effort_override_metadata_comment(stripped))
        else:
            rendered.append(line)
    return rendered


def handoff_field_sections(content: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if EFFORT_OVERRIDE_RE.match(stripped) or EFFORT_OVERRIDE_COMMENT_RE.match(stripped):
            continue
        match = STRUCTURED_HANDOFF_HEADING_RE.match(line)
        if match:
            current = match.group('field')
            sections.setdefault(current, [])
            rest = match.group('rest').strip()
            if rest:
                sections[current].append(rest)
            continue
        if current is not None:
            if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
                current = None
                continue
            sections[current].append(line)
    return sections


def parse_json_fragment(raw: str, field: str) -> object:
    value = raw.strip()
    if value.startswith('`') and value.endswith('`') and len(value) >= 2:
        value = value[1:-1].strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        handoff_abort(field, value)


def parse_write_scope_section(lines: list[str]) -> list[str]:
    if not lines:
        handoff_abort('writeScope', [])
    joined = '\n'.join(line.strip() for line in lines if line.strip()).strip()
    if joined.startswith('`[') or joined.startswith('['):
        parsed = parse_json_fragment(joined, 'writeScope')
        return validate_handoff_write_scope(parsed)
    scopes: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        spans = CODE_SPAN_RE.findall(line)
        if spans:
            scopes.append(spans[0])
            continue
        bullet = re.match(r'^[-*]\s+(\S+)', stripped)
        if bullet:
            scopes.append(bullet.group(1))
    return validate_handoff_write_scope(scopes)


def parse_validation_commands_section(lines: list[str]) -> list[list[str]]:
    if not lines:
        validation_command_abort([])
    fragments: list[object] = []
    inline = ' '.join(line.strip() for line in lines if line.strip()).strip()
    if inline.startswith('`') or inline.startswith('[') or inline.startswith('{') or (
        inline.startswith('"') and inline.endswith('"')
    ):
        parsed = parse_json_fragment(inline, 'validationCommands')
        return validate_handoff_validation_commands(parsed)
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        spans = CODE_SPAN_RE.findall(line)
        if spans:
            for span in spans:
                fragments.append(parse_json_fragment(span, 'validationCommands'))
            continue
        bullet = re.match(r'^[-*]\s+(.+)$', stripped)
        if bullet:
            fragments.append(parse_json_fragment(bullet.group(1), 'validationCommands'))
    if not fragments:
        validation_command_abort(inline)
    if len(fragments) == 1:
        return validate_handoff_validation_commands(fragments[0])
    return validate_handoff_validation_commands(fragments)


def parse_handoff_content(content: str) -> dict:
    sections = handoff_field_sections(content)
    if 'writeScope' not in sections:
        handoff_abort('writeScope', 'missing')
    if 'validationCommands' not in sections:
        handoff_abort('validationCommands', 'missing')
    state = {
        'schemaVersion': HANDOFF_SCHEMA_VERSION,
        'writeScope': parse_write_scope_section(sections['writeScope']),
        'validationCommands': parse_validation_commands_section(sections['validationCommands']),
        'body': '\n'.join(render_content_for_transcript(content)).rstrip('\n'),
    }
    return validate_handoff_state(state, 'handoff')


def set_handoff_state(entry: dict, role: str, state: dict) -> None:
    handoff = entry.setdefault('handoff', {'schemaVersion': HANDOFF_SCHEMA_VERSION, 'roles': {}})
    handoff['schemaVersion'] = HANDOFF_SCHEMA_VERSION
    roles = handoff.setdefault('roles', {})
    if not isinstance(roles, dict):
        die('handoff roles must be an object')
    roles[role] = validate_handoff_state(state, f'handoff.{role}')


def handoff_state_for_role(entry: dict, role: str) -> dict | None:
    handoff = entry.get('handoff')
    if not isinstance(handoff, dict):
        return None
    roles = handoff.get('roles')
    if not isinstance(roles, dict):
        return None
    state = roles.get(role)
    if not isinstance(state, dict):
        return None
    return validate_handoff_state(state, f'handoff.{role}')


def render_handoff_mirror_lines(body_lines: list[str], entry: dict) -> list[str]:
    handoff = entry.get('handoff')
    if not isinstance(handoff, dict):
        return body_lines
    roles = handoff.get('roles')
    if not isinstance(roles, dict) or not roles:
        return body_lines
    try:
        start, end = section_bounds(body_lines, '## Handoff')
    except SystemExit:
        return body_lines
    rendered = list(body_lines)
    index = start + 1
    while index < end:
        if not DETAILS_OPEN_RE.match(rendered[index].strip()):
            index += 1
            continue
        block_start = index
        depth = 1
        block_end: int | None = None
        cursor = index + 1
        while cursor < end:
            stripped = rendered[cursor].strip()
            if DETAILS_OPEN_RE.match(stripped):
                depth += 1
            elif DETAILS_CLOSE_RE.match(stripped):
                depth -= 1
                if depth == 0:
                    block_end = cursor + 1
                    break
            cursor += 1
        if block_end is None:
            die('transcript details block not closed in phase: Handoff')
        role = summary_role(rendered[block_start + 1]) if block_start + 1 < block_end else None
        state = roles.get(role) if role else None
        if isinstance(state, dict):
            validated = validate_handoff_state(state, f'handoff.{role}')
            body = validated.get('body')
            if isinstance(body, str) and body.strip():
                marker_index: int | None = None
                for offset in range(block_start, block_end):
                    if rendered[offset].strip() == CONTENT_ONLY_GUARD:
                        marker_index = offset
                        break
                if marker_index is None:
                    die('contribution content marker missing')
                replacement = (
                    rendered[:marker_index + 1]
                    + ['']
                    + body.splitlines()
                    + ['']
                    + rendered[block_end - 1:block_end]
                )
                delta = len(replacement) - block_end
                rendered = replacement + rendered[block_end:]
                end += delta
                block_end += delta
        index = block_end
    return rendered


def preserve_case_replacement(match: re.Match[str], replacement: str) -> str:
    text = match.group(0)
    if text.isupper():
        return replacement.upper()
    if text[:1].isupper() and text[1:].islower():
        return replacement[:1].upper() + replacement[1:].lower()
    return replacement


def read_moderator_polish_spec(path: Path = DEFAULT_MODERATOR_POLISH_PATH) -> dict:
    if not path.exists():
        die(f'moderator polish spec missing: {path}')
    typos: list[tuple[str, str]] = []
    for line in path.read_text().splitlines():
        match = TYPO_ROW_RE.match(line)
        if not match:
            continue
        typo = match.group('typo')
        fix = match.group('fix')
        if fix.startswith(f'{typo} '):
            fix = typo
        typos.append((typo, fix))
    if not typos:
        die(f'moderator polish spec missing typo dictionary: {path}')
    return {'typos': typos}


def polish_moderator_content(content: str, spec_path: Path = DEFAULT_MODERATOR_POLISH_PATH) -> str:
    spec = read_moderator_polish_spec(spec_path)
    lines = [line.rstrip() for line in content.splitlines()]
    rendered: list[str] = []
    in_code = False
    blank_pending = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code = not in_code
            rendered.append(raw_line)
            blank_pending = False
            continue
        if stripped == '':
            if not blank_pending:
                rendered.append('')
            blank_pending = True
            continue
        blank_pending = False
        line = raw_line
        if not in_code:
            line = re.sub(r'^(\s*)[*+]\s+', r'\1- ', line)
            for typo, fix in spec['typos']:
                line = re.sub(re.escape(typo), lambda match, replacement=fix: preserve_case_replacement(match, replacement), line, flags=re.IGNORECASE)
            list_match = re.match(r'^(\s*-\s+)([a-z])', line)
            if list_match:
                line = list_match.group(1) + list_match.group(2).upper() + line[list_match.end():]
            elif line and line[0].islower():
                line = line[0].upper() + line[1:]
            if (
                line
                and not line.endswith(('.', '?', '!', ':', '`'))
                and not line.lstrip().startswith(('- ', '#', '|'))
            ):
                line += '.'
        rendered.append(line)
    return '\n'.join(rendered).rstrip('\n')


def render_contribution_block(phase: str, role: str, counter: int, content: str, timestamp: str) -> tuple[str, list[str]]:
    anchor = f'{phase_slug(phase)}-{role}-{counter}'
    lines = [
        f'<a name="{anchor}"></a>',
        '<details>',
        f'<summary>{role}</summary>',
        f'<p><em>{timestamp}</em></p>',
        CONTENT_ONLY_GUARD,
        '',
        *render_content_for_transcript(content),
        '',
        '</details>',
    ]
    return anchor, lines


def render_speak(
    path: Path,
    target: str,
    role: str,
    content_file: Path,
    observed_revision: int | None = None,
    timestamp: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
    verbatim: bool = False,
) -> int:
    content = read_content_file(content_file)
    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'speak-render', role)
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if current_entry['activePhase'] == 'Completion':
            die('speak-render is not permitted in Completion')
        if not has_participant(current_entry, role):
            die(f'role must already be a participant: {role}')
        live_revision = registry_revision(data)
        resume = resume_command(current_entry, role)
        if observed_revision is None:
            die(f'speak-render requires --observed-revision\n{resume}')
        if observed_revision != live_revision:
            die(
                f'stale registry revision: observed {observed_revision}, live {live_revision}\n'
                f'{resume}'
            )

        transcript_path = Path(current_entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        pending_reviewer = pending_reviewer_role(current_entry)
        if pending_reviewer:
            die(f'pending reviewerRole: {pending_reviewer}\n{resume}')
        state = speak_state_for_entry(current_entry, transcript)
        if role not in state['allowedRoles']:
            if role == reviewer_optional_for_phase(current_entry, current_entry['activePhase']):
                die(
                    'reviewer may speak after all turn-order participants have contributed in this round\n'
                    f'{resume}'
                )
            die(f"expected role: {state['expectedRole']}\n{resume}")
        phase = current_entry['activePhase']
        if phase in ONE_SPEAK_PHASES and role in state['contributors']:
            die(f'duplicate phase contribution: {role} in {phase}\n{resume}')
        if role == current_entry['moderatorRole'] and not verbatim:
            content = polish_moderator_content(content)
        validate_effort_override(content, phase, role, current_entry['moderatorRole'])
        validate_action_plan_shape(content, phase)
        enforce_contribution_budget(content, phase, role, current_entry['moderatorRole'], verbatim)
        handoff_state = parse_handoff_content(content) if phase == 'Handoff' else None

        lines = transcript.splitlines()
        counter = next_anchor_counter(lines, phase, role)
        anchor, block = render_contribution_block(phase, role, counter, content, timestamp or format_timestamp())
        rendered_lines = append_phase_block(lines, phase, block)

        next_data = deepcopy(data)
        next_entry = resolve_collab(next_data, target)
        if handoff_state is not None:
            set_handoff_state(next_entry, role, handoff_state)
        rendered_text = '\n'.join(rendered_lines) + '\n'
        rendered_state = speak_state_for_entry(next_entry, rendered_text)
        advanced, notice = apply_speak_lifecycle_with_notice(next_entry, rendered_state['contributors'])
        rendered_text, header_changed = render_managed_header_text(rendered_text, next_entry, DEFAULT_ROLES_DIR)
        notice = add_completion_summary_notice(notice, rendered_text)
        print('BOUNDARY: transcript write only; no shell commands or file edits outside .collabs/')
        print('SUCCINCTLY: stay within role concerns; do not pad or summarize other roles')
        print('RETRACT: use /collab retract speak to tombstone the latest active-phase contribution')
        print_header_overwrite(header_changed)
        label_advisory = action_plan_label_advisory(content, phase)
        if label_advisory:
            print(label_advisory)
        commit_registry_and_transcript(path, next_data, transcript_path, rendered_text)
    print_post_action_advisories(
        next_entry,
        role,
        effort_phase_after_speak(phase),
        notice,
        next_line_after_speak(next_entry, role, phase, rendered_text),
    )
    lifecycle = {'phaseState': next_entry['activePhase'] if advanced else 'unchanged'}
    if notice:
        lifecycle['notice'] = notice
    print('appended')
    print_lifecycle_diagnostic(lifecycle, emit_json)
    return 0


def contribution_block_bounds(lines: list[str], phase: str, role: str) -> tuple[int, int] | None:
    _phase_start, phase_end = section_bounds(lines, f'## {phase}')
    latest: tuple[int, int] | None = None
    index = _phase_start + 1
    while index < phase_end:
        if DETAILS_OPEN_RE.match(lines[index].strip()):
            start = index
            depth = 1
            end: int | None = None
            cursor = index + 1
            while cursor < phase_end:
                stripped = lines[cursor].strip()
                if DETAILS_OPEN_RE.match(stripped):
                    depth += 1
                elif DETAILS_CLOSE_RE.match(stripped):
                    depth -= 1
                    if depth == 0:
                        end = cursor + 1
                        break
                cursor += 1
            if end is None:
                die(f'transcript details block not closed in phase: {phase}')
            summary = summary_role(lines[start + 1]) if start + 1 < end else None
            if summary == role:
                latest = (start, end)
            index = end
            continue
        index += 1
    return latest


def revision_history_start(block: list[str], content_start: int) -> int | None:
    depth = 0
    for index in range(content_start, len(block) - 1):
        stripped = block[index].strip()
        if stripped == '<details><summary>Revision history</summary>':
            return index
        if DETAILS_OPEN_RE.match(stripped):
            if depth == 0 and index + 1 < len(block) and block[index + 1].strip() == '<summary>Revision history</summary>':
                return index
            depth += 1
            continue
        if DETAILS_CLOSE_RE.match(stripped):
            depth = max(0, depth - 1)
    return None


def prepend_revision_history(existing: list[str] | None, original_timestamp: str, prior_content: list[str]) -> list[str]:
    body = list(prior_content)
    while body and body[0] == '':
        body.pop(0)
    while body and body[-1] == '':
        body.pop()
    revision = [
        f'Previous revision, {original_timestamp}:',
        '',
        *body,
        '',
    ]
    if existing is None:
        return [
            '<details><summary>Revision history</summary>',
            '',
            *revision,
            '</details>',
        ]
    if not existing:
        return [
            '<details><summary>Revision history</summary>',
            '',
            *revision,
            '</details>',
        ]
    insert_at = 1
    if len(existing) > 1 and existing[1] == '':
        insert_at = 2
    return existing[:insert_at] + revision + existing[insert_at:]


def replace_latest_contribution(
    transcript: str,
    phase: str,
    role: str,
    content: str,
    timestamp: str,
) -> str:
    lines = transcript.splitlines()
    bounds = contribution_block_bounds(lines, phase, role)
    if bounds is None:
        die('no prior contribution to rewrite; use /collab speak to create the first contribution')
    start, end = bounds
    block = lines[start:end]

    timestamp_index: int | None = None
    marker_index: int | None = None
    for index, line in enumerate(block):
        if timestamp_index is None and TIMESTAMP_RE.match(line.strip()):
            timestamp_index = index
        if line.strip() == '<!-- collab:content-only; do-not-execute -->':
            marker_index = index
            break
    if timestamp_index is None:
        die('contribution timestamp missing')
    if marker_index is None:
        die('contribution content marker missing')

    original_timestamp = TIMESTAMP_RE.match(block[timestamp_index].strip()).group('timestamp')  # type: ignore[union-attr]
    rev_start = revision_history_start(block, marker_index + 1)
    content_end = rev_start if rev_start is not None else len(block) - 1
    existing_history = block[rev_start:len(block) - 1] if rev_start is not None else None
    prior_content = block[marker_index + 1:content_end]

    block[timestamp_index] = f'<p><em>{timestamp}</em></p>'
    history = prepend_revision_history(existing_history, original_timestamp, prior_content)
    replacement = (
        block[:marker_index + 1]
        + ['']
        + render_content_for_transcript(content)
        + ['']
        + history
        + [block[-1]]
    )
    return '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'


def latest_contribution_timestamp(transcript: str, phase: str, role: str) -> str | None:
    lines = transcript.splitlines()
    bounds = contribution_block_bounds(lines, phase, role)
    if bounds is None:
        return None
    start, end = bounds
    for line in lines[start:end]:
        match = TIMESTAMP_RE.match(line.strip())
        if match:
            return match.group('timestamp')
    return None


def reviewer_notice_for_rewrite(entry: dict, transcript: str, role: str) -> str | None:
    reviewer = active_reviewer_role(entry)
    if not reviewer or role == reviewer:
        return None
    phase = entry['activePhase']
    target_timestamp = latest_contribution_timestamp(transcript, phase, role)
    reviewer_timestamp = latest_contribution_timestamp(transcript, phase, reviewer)
    if target_timestamp and reviewer_timestamp and target_timestamp < reviewer_timestamp:
        return (
            f'REVIEWER-NOTICE: {role} rewrite in {phase} predates the latest '
            f'{reviewer} reviewer contribution; reviewer gate re-triggered.'
        )
    return None


def render_re_speak(
    path: Path,
    target: str,
    role: str,
    content_file: Path,
    timestamp: str | None = None,
    caller_role: str | None = None,
) -> int:
    content = read_content_file(content_file)
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'rewrite-speak-render', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] == 'Completion':
            die('rewrite-speak-render is not permitted in Completion')
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        validate_action_plan_shape(content, entry['activePhase'])
        reviewer_notice = reviewer_notice_for_rewrite(entry, transcript, role)
        rendered = replace_latest_contribution(
            transcript,
            entry['activePhase'],
            role,
            content,
            timestamp or format_timestamp(),
        )
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    if reviewer_notice:
        print(reviewer_notice)
    print(entry['id'])
    return 0


def advance_phase(
    path: Path,
    target: str,
    direction: str,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'advance' if direction == 'next' else 'restore')
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        index = PHASES.index(entry['activePhase'])
        from_phase = entry['activePhase']
        if direction == 'next':
            if index == len(PHASES) - 1:
                die('no next phase')
            entry['activePhase'] = PHASES[index + 1]
            if entry['activePhase'] in MOD_EXCLUDED_PHASES:
                remove_moderator_from_turn_order(entry)
            if entry['activePhase'] == 'Completion':
                initialize_completion_state(entry, 'execution', reset_rounds=True)
        else:
            if index == 0:
                die('no previous phase')
            entry['activePhase'] = PHASES[index - 1]
            normalize_turn_order_for_phase(entry, entry['activePhase'])
            if entry['activePhase'] != 'Completion':
                invalidate_verification_seal(entry, f'restored to {entry["activePhase"]}')

        notice = transition_notice(from_phase, entry['activePhase'])
        transcript_path = Path(entry['transcriptPath'])
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
            notice = add_completion_summary_notice(notice, rendered)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_post_action_advisories(
        entry,
        None,
        None,
        notice,
        next_line_for_state(entry),
    )
    print_phase_result(entry['activePhase'], notice, emit_json)
    return 0


def record_execution(
    path: Path,
    target: str,
    role: str,
    status: str,
    date: str,
    assigned_roles: list[str],
    auto_close: bool,
    validation_result: str | None,
    validation_scope: str | None,
    touched_paths: list[str],
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    if status not in ALLOWED_EXECUTION_STATUSES:
        die(f'execution status must be one of {sorted(ALLOWED_EXECUTION_STATUSES)}')
    if validation_scope and validation_scope not in ALLOWED_VALIDATION_SCOPES:
        die(f'execution validation scope must be one of {sorted(ALLOWED_VALIDATION_SCOPES)}')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'execution', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if not has_participant(entry, role):
            die(f'execution role must already be a participant: {role}')
        if role == entry['moderatorRole']:
            die('execution role must not be the moderator')
        if reviewer_backed(entry) and reviewer_state(entry)['state'] != 'active':
            die(f'execution blocked: reviewer role is not active: {reviewer_role(entry)}')
        for assigned_role in assigned_roles:
            if not has_participant(entry, assigned_role):
                die(f'assigned role must already be a participant: {assigned_role}')
        transcript = read_transcript_for_entry(entry) if Path(entry['transcriptPath']).exists() else ''
        if status == 'completed' and entry['activePhase'] == 'Completion':
            unchecked_count = unchecked_assigned_item_count(transcript, role)
            if unchecked_count:
                die(
                    f'execution completed blocked for role {role}: '
                    f'{unchecked_count} unchecked assigned Action Plan item(s) remain'
                )

        execution_state = {'status': status, 'date': date}
        execution_state['entryId'] = execution_identity(role, date)
        if validation_result:
            execution_state['validationResult'] = validation_result
        if validation_scope:
            execution_state['validationScope'] = validation_scope
        if touched_paths:
            execution_state['touchedPaths'] = touched_paths
        previous_signature = execution_signature(entry)
        entry.setdefault('execution', {})[role] = execution_state
        if reviewer_backed(entry) and previous_signature != execution_signature(entry):
            invalidate_verification_seal(entry, f'execution changed for {role}')
        closed = False
        if reviewer_backed(entry) and entry['activePhase'] == 'Completion':
            if close_eligible_after_execution(entry, assigned_roles):
                if auto_close:
                    entry['status'] = 'closed'
                    closed = True
                    if data.get('activeCollabId') == entry['id']:
                        data['activeCollabId'] = None
            else:
                if all(
                    entry.get('execution', {}).get(assigned_role, {}).get('status') == 'completed'
                    for assigned_role in assigned_roles
                    if assigned_role != entry['moderatorRole']
                ):
                    initialize_completion_state(entry, 'verification', reset_rounds=True)
                else:
                    initialize_completion_state(entry, 'execution')
        elif auto_close and close_eligible_after_execution(entry, assigned_roles):
            entry['status'] = 'closed'
            closed = True
            if data.get('activeCollabId') == entry['id']:
                data['activeCollabId'] = None

        notice = terminal_notice('closed') if closed else None
        next_line = next_line_after_execution(entry, assigned_roles)
        transcript_path = Path(entry['transcriptPath'])
        if closed and transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
            if completion_summary_empty(rendered):
                rendered = append_completion_summary(
                    rendered,
                    default_close_summary(entry),
                    summary_date_from_timestamp(date),
                )
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line)
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def rendered_status_table(entry: dict) -> str:
    reviewer = reviewer_role(entry) or '\u2014'
    turn_order_values = effective_turn_order(entry)
    turn_order = ', '.join(turn_order_values) if turn_order_values else '\u2014'
    active_phase = entry['activePhase']
    if active_phase == 'Completion' and reviewer_backed(entry):
        completion = entry.get('completion')
        if isinstance(completion, dict) and completion.get('subState') in ALLOWED_COMPLETION_SUBSTATES:
            active_phase = f"Completion.{completion['subState']}"
    return '\n'.join([
        '| Status | Active phase | Turn order | Reviewer |',
        '|--------|--------------|------------|----------|',
        f"| {entry['status']} | {active_phase} | {turn_order} | {reviewer} |",
    ])


def rendered_participants_table(entry: dict, roles_dir: Path) -> str:
    rows = [
        '| # | Key | Role | Agent | Responsibilities |',
        '|---|-----|------|-------|------------------|',
    ]
    for index, p in enumerate(entry['participants'], start=1):
        rows.append(participant_row(load_role(roles_dir, p['role']), index, p['agentId']))
    return '\n'.join(rows)


def rendered_prohibitions_block(entry: dict, roles_dir: Path) -> str | None:
    rows = [
        '| Role | Constraints |',
        '|------|-------------|',
    ]
    for participant in entry['participants']:
        role_data = load_role(roles_dir, participant['role'])
        prohibitions = role_data.get('prohibitions') or []
        if not prohibitions:
            continue
        rows.append(f"| {role_data['key']} | {' · '.join(prohibitions)} |")
    if len(rows) == 2:
        return None
    return '\n'.join([
        '**Prohibitions**',
        '',
        '_principle-level behavioral constraints; not a runtime enforcement list_',
        '',
        *rows,
    ])


def replace_table_after_heading(
    transcript: str,
    heading: str,
    replacement: str,
    missing_section_message: str,
    missing_table_message: str,
) -> str:
    lines = transcript.splitlines()
    heading_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            heading_index = index
            break
    if heading_index is None:
        die(missing_section_message)

    table_start: int | None = None
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith('|'):
            table_start = index
            break
        if lines[index].startswith('**') or lines[index].startswith('## '):
            break
    if table_start is None:
        die(missing_table_message)

    table_end = table_start
    while table_end < len(lines) and lines[table_end].startswith('|'):
        table_end += 1

    return '\n'.join(lines[:table_start] + replacement.splitlines() + lines[table_end:]) + '\n'


def replace_status_table(transcript: str, entry: dict) -> str:
    return replace_table_after_heading(
        transcript,
        '**Status**',
        rendered_status_table(entry),
        'transcript status section missing',
        'transcript status table missing',
    )


def rendered_reviewer_section(entry: dict, roles_dir: Path) -> str | None:
    state = reviewer_state(entry)
    if state['state'] == 'absent':
        return '\u2014'
    reviewer = state['reviewerRole']
    mode = reviewer_mode(entry)
    optional = ', '.join(reviewer_optional_phases(entry)) or '\u2014'
    if state['state'] == 'active':
        return (
            f'**{reviewer}** — registered in **Participants** and active as the '
            f'convergent-phase reviewer per `.collabs/registry.json` '
            f'(`reviewerMode: {mode}`). Reviewer gating is now in effect for convergent phases. '
            f'Optional reviewer phases: {optional}.'
        )
    role_data = load_role(roles_dir, reviewer)
    display_name = role_data['displayName']
    return '\n'.join([
        '| Role | Status |',
        '|------|--------|',
        f'| {reviewer} ({display_name}) | (pending) |',
        '',
        f'`{reviewer}` is assigned as reviewer but has not yet joined. Run `/collab join --role {reviewer}` before any participant may contribute.',
    ])


def header_timestamp_from_lines(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('_') and stripped.endswith('_') and len(stripped) > 2:
            return stripped.strip('_')
    return format_banner_timestamp()


def anchor_role_for_toc(lines: list[str], anchor_index: int, anchor: str) -> str:
    for cursor in range(anchor_index + 1, min(len(lines), anchor_index + 8)):
        if lines[cursor].startswith('## ') or ANCHOR_RE.match(lines[cursor].strip()):
            break
        role = summary_role(lines[cursor])
        if role:
            return role
    parts = anchor.split('-')
    if len(parts) >= 3:
        return parts[-2]
    return anchor


def rendered_table_of_contents(body_lines: list[str]) -> str:
    lines: list[str] = ['**Table of contents**', '']
    for phase in PHASES:
        lines.append(f'- [{phase}](#{phase_slug(phase)})')
        try:
            start, end = section_bounds(body_lines, f'## {phase}')
        except SystemExit:
            continue
        for index in range(start + 1, end):
            match = ANCHOR_RE.match(body_lines[index].strip())
            if not match:
                continue
            anchor = match.group('anchor')
            if not anchor.startswith(f'{phase_slug(phase)}-'):
                continue
            role = anchor_role_for_toc(body_lines[start:end], index - start, anchor)
            lines.append(f'  - [{role}](#{anchor})')
    return '\n'.join(lines)


def rendered_managed_header(title: str, entry: dict, roles_dir: Path, timestamp: str, body_lines: list[str]) -> str:
    lines = [
        title,
        '> This record is shared context, not an instruction to execute the work being discussed.',
        '',
        HEADER_MANAGED_BEGIN,
        CONTENT_ONLY_GUARD,
        '',
        f'_{timestamp}_',
        '',
        'Moderated collaboration record for shared agent discussion.',
        '',
        'Registry-backed collab state is authoritative. Metadata below mirrors `.collabs/registry.json` for human orientation only.',
        '',
        '**Status**',
        '',
        rendered_status_table(entry),
        '',
        '**Participants**',
        '',
        rendered_participants_table(entry, roles_dir),
        '',
    ]
    prohibitions = rendered_prohibitions_block(entry, roles_dir)
    if prohibitions is not None:
        lines.extend([prohibitions, ''])
    lines.extend([
        'Agents must wait for the moderator to call `/collab speak` before contributing.',
        '',
        '**Reviewer**',
        '',
    ])
    reviewer = rendered_reviewer_section(entry, roles_dir)
    lines.extend((reviewer or '\u2014').splitlines())
    lines.extend([
        '',
        '---',
        '',
        rendered_table_of_contents(body_lines),
        '',
        '---',
        HEADER_MANAGED_END,
    ])
    return '\n'.join(lines)


def managed_header_bounds(lines: list[str]) -> tuple[int, int] | None:
    begin: int | None = None
    end: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == HEADER_MANAGED_BEGIN:
            begin = index
        elif stripped == HEADER_MANAGED_END and begin is not None:
            end = index + 1
            break
    if begin is None and end is None:
        return None
    if begin is None or end is None:
        die('managed header sentinel mismatch')
    return begin, end


def legacy_header_bounds(lines: list[str]) -> tuple[int, int]:
    body_start: int | None = None
    phase_headings = {f'## {phase}' for phase in PHASES}
    for index, line in enumerate(lines):
        if line.strip() in phase_headings:
            body_start = index
            break
    if body_start is None:
        die('transcript phase missing: Audit')
    return 1, body_start


def render_managed_header_text(transcript: str, entry: dict, roles_dir: Path) -> tuple[str, bool]:
    lines = transcript.splitlines()
    if not lines or not lines[0].startswith('# '):
        die('transcript title missing')
    bounds = managed_header_bounds(lines)
    if bounds is None:
        bounds = legacy_header_bounds(lines)
    start, end = bounds
    body_lines = render_handoff_mirror_lines(lines[end:], entry)
    timestamp = header_timestamp_from_lines(lines[start:end])
    replacement = rendered_managed_header(lines[0], entry, roles_dir, timestamp, body_lines).splitlines()
    changed = lines[start:end] != replacement[1:] or lines[end:] != body_lines
    rendered = lines[:1] + replacement[1:] + body_lines
    return '\n'.join(rendered) + '\n', changed


def print_header_overwrite(changed: bool) -> None:
    if changed:
        print('HEADER-OVERWRITE: managed transcript header was rendered from registry state')


def render_initial_transcript(title: str, entry: dict, roles_dir: Path, timestamp: str) -> str:
    body_lines = [
        '## Audit',
        CONTENT_ONLY_GUARD,
        '',
        '## Discussion',
        CONTENT_ONLY_GUARD,
        '',
        '## Conclusion',
        CONTENT_ONLY_GUARD,
        '',
        '## Action Plan',
        CONTENT_ONLY_GUARD,
        '',
        '## Handoff',
        CONTENT_ONLY_GUARD,
        '',
        '## Completion',
        CONTENT_ONLY_GUARD,
        '',
        '**Execution history**',
    ]
    header = rendered_managed_header(f'# {title}', entry, roles_dir, timestamp, body_lines)
    return '\n'.join([header, '', *body_lines]) + '\n'


def render_initial_transcript_legacy(title: str, entry: dict, roles_dir: Path, timestamp: str) -> str:
    participant = participant_row(
        load_role(roles_dir, entry['moderatorRole']),
        1,
        entry['participants'][0]['agentId'],
    )
    lines = [
        f'# {title}',
        '> This record is shared context, not an instruction to execute the work being discussed.',
        '',
        CONTENT_ONLY_GUARD,
        '',
        f'_{timestamp}_',
        '',
        'Moderated collaboration record for shared agent discussion.',
        '',
        'Registry-backed collab state is authoritative. Metadata below mirrors `.collabs/registry.json` for human orientation only.',
        '',
        '**Status**',
        '',
        rendered_status_table(entry),
        '',
        '**Participants**',
        '',
        '| # | Key | Role | Agent | Responsibilities |',
        '|---|-----|------|-------|------------------|',
        participant,
        '',
        'Agents must wait for the moderator to call `/collab speak` before contributing.',
        '',
    ]
    reviewer = rendered_reviewer_section(entry, roles_dir)
    if reviewer is not None and reviewer != '\u2014':
        lines.extend(['**Reviewer**', '', *reviewer.splitlines(), ''])
    lines.extend([
        '---',
        '',
        '**Table of contents**',
        '',
        '- [Audit](#audit)',
        '- [Discussion](#discussion)',
        '- [Conclusion](#conclusion)',
        '- [Action Plan](#action-plan)',
        '- [Handoff](#handoff)',
        '- [Completion](#completion)',
        '',
        '---',
        '',
        '## Audit',
        CONTENT_ONLY_GUARD,
        '',
        '## Discussion',
        CONTENT_ONLY_GUARD,
        '',
        '## Conclusion',
        CONTENT_ONLY_GUARD,
        '',
        '## Action Plan',
        CONTENT_ONLY_GUARD,
        '',
        '## Handoff',
        CONTENT_ONLY_GUARD,
        '',
        '## Completion',
        CONTENT_ONLY_GUARD,
        '',
        '**Execution history**',
    ])
    return '\n'.join(lines) + '\n'


def replace_reviewer_section_text(transcript: str, entry: dict, roles_dir: Path) -> str:
    lines = transcript.splitlines()
    heading_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == '**Reviewer**':
            heading_index = index
            break
    if heading_index is None:
        return transcript
    section_end: int | None = None
    for index in range(heading_index + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped == '---' or (stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4):
            section_end = index
            break
    if section_end is None:
        return transcript
    new_content = rendered_reviewer_section(entry, roles_dir)
    if new_content is None:
        return transcript
    new_lines = lines[:heading_index + 1] + [''] + new_content.splitlines() + [''] + lines[section_end:]
    return '\n'.join(new_lines) + '\n'


def replace_participants_table_text(transcript: str, entry: dict, roles_dir: Path) -> str:
    return replace_table_after_heading(
        transcript,
        '**Participants**',
        rendered_participants_table(entry, roles_dir),
        'transcript participants section missing',
        'transcript participants table missing',
    )


def replace_participants_table(transcript_path: Path, entry: dict, roles_dir: Path) -> None:
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')
    transcript = transcript_path.read_text()
    replacement = replace_participants_table_text(transcript, entry, roles_dir)
    transcript_path.write_text(replacement)


def completion_summary_bounds(transcript: str) -> tuple[int, int]:
    lines = transcript.splitlines()
    completion_start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == '## Completion':
            completion_start = index + 1
            break
    if completion_start is None:
        die('transcript phase missing: Completion')

    heading_indexes = [
        index
        for index in range(completion_start, len(lines))
        if SUMMARY_HEADING_RE.match(lines[index].strip())
    ]
    if not heading_indexes:
        die('nothing yet summarized; run /collab write summary first')

    start = heading_indexes[-1]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith('## ') or SUMMARY_HEADING_RE.match(stripped):
            end = index
            break
    return start, end


def replace_latest_summary(transcript: str, summary_body: str, date: str) -> str:
    body = summary_body.strip()
    if not body:
        die('summary body must be non-empty')
    start, end = completion_summary_bounds(transcript)
    lines = transcript.splitlines()
    replacement = [f'### Summary \u2014 {date}', '', *body.splitlines(), '']
    return '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'


def append_completion_summary(transcript: str, summary_body: str, date: str) -> str:
    body = summary_body.strip()
    if not body:
        die('summary body must be non-empty')
    lines = transcript.splitlines()
    completion_start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == '## Completion':
            completion_start = index
            break
    if completion_start is None:
        die('transcript phase missing: Completion')
    insert_at = len(lines)
    replacement = ['', f'### Summary \u2014 {date}', '', *body.splitlines()]
    if insert_at > 0 and lines[insert_at - 1] == '':
        replacement = replacement[1:]
    return '\n'.join(lines[:insert_at] + replacement + lines[insert_at:]) + '\n'


def summary_date_from_timestamp(timestamp: str) -> str:
    match = re.match(r'^(\d{4}-\d{2}-\d{2})\b', timestamp)
    if match:
        return match.group(1)
    return dt.date.today().isoformat()


def default_close_summary(entry: dict) -> str:
    completed = [
        f'`{role}`'
        for role, state in sorted(entry.get('execution', {}).items())
        if state.get('status') == 'completed'
    ]
    completed_text = ', '.join(completed) if completed else 'no roles'
    touched: list[str] = []
    for state in entry.get('execution', {}).values():
        for path in state.get('touchedPaths', []):
            if isinstance(path, str) and path not in touched:
                touched.append(path)
    touched_text = ', '.join(f'`{path}`' for path in touched) if touched else 'no source paths recorded'
    return '\n'.join([
        f'Closed after completed execution for {completed_text}.',
        '',
        f'Validation result: passed for recorded role execution; touched paths: {touched_text}.',
    ])


def next_completion_history_number(transcript: str) -> int:
    try:
        lines = phase_section(transcript, 'Completion')
    except SystemExit as exc:
        if str(exc) == 'transcript phase missing: Completion':
            return 1
        raise
    highest = 0
    for line in lines:
        match = re.match(r'^\s*(\d+)\.\s+\*\*[^*]+:\*\*', line)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def append_completion_history_line(transcript: str, line: str) -> str:
    lines = transcript.splitlines()
    start, end = section_bounds(lines, '## Completion')
    insert_at = end
    if insert_at > start and lines[insert_at - 1] != '':
        line_block = ['', line]
    else:
        line_block = [line]
    return '\n'.join(lines[:insert_at] + line_block + lines[insert_at:]) + '\n'


def summary_date_from_iso(timestamp: str) -> str:
    match = re.match(r'^(\d{4}-\d{2}-\d{2})T', timestamp)
    if match:
        return match.group(1)
    return summary_date_from_timestamp(timestamp)


def seal_snapshot(entry: dict, observed_revision: int, role: str, cap_exit: str | None = None) -> dict:
    seal = {
        'schemaVersion': VERIFICATION_SEAL_SCHEMA_VERSION,
        'observedRevision': observed_revision,
        'executionEntries': active_execution_entries(entry),
        'validationScopes': validation_scopes_for_execution(entry),
        'touchedPaths': touched_paths_for_execution(entry),
        'sealedAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'sealedBy': role,
        'executionSignature': execution_signature(entry),
        'stale': False,
    }
    if cap_exit:
        seal['capExit'] = cap_exit
    return seal


def verification_substate(entry: dict) -> str:
    if not reviewer_backed(entry):
        return 'none'
    completion = entry.get('completion')
    if isinstance(completion, dict) and completion.get('subState') in ALLOWED_COMPLETION_SUBSTATES:
        return completion['subState']
    return 'execution'


def all_execution_completed(entry: dict) -> bool:
    execution = entry.get('execution', {})
    roles = [role for role in effective_turn_order(entry) if role != entry['moderatorRole']]
    if not roles:
        return False
    return all(execution.get(role, {}).get('status') == 'completed' for role in roles)


def seal_state(path: Path, target: str, role: str | None = None, resume: bool = False) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die('/collab seal verification is valid only in the Completion phase')
        if reviewer_backed(entry):
            initialize_completion_state(entry, verification_substate(entry))
        if reviewer_backed(entry) and all_execution_completed(entry):
            completion = completion_state(entry)
            if completion['subState'] == 'execution':
                completion['subState'] = 'verification'
                verification_state(entry)['rounds'] = 0
        verification = verification_state(entry) if reviewer_backed(entry) else {'rounds': 0, 'cap': DEFAULT_VERIFICATION_CAP}
        if reviewer_backed(entry) and verification_substate(entry) == 'verification' and all_execution_completed(entry):
            signature = execution_signature(entry)
            if verification.get('pairedExecutionSignature') != signature:
                verification['rounds'] = verification.get('rounds', 0) + 1
                verification['pairedExecutionSignature'] = signature
        save_registry(path, data)
        data = load_registry(path)
        entry = resolve_collab(data, target)

    seal = entry.get('verificationSeal')
    result = {
        'target': entry['id'],
        'activePhase': entry['activePhase'],
        'registryRevision': registry_revision(data),
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'verificationSubState': verification_substate(entry),
        'verificationRounds': verification_state(entry).get('rounds', 0) if reviewer_backed(entry) else 0,
        'verificationCap': verification_state(entry).get('cap', DEFAULT_VERIFICATION_CAP) if reviewer_backed(entry) else DEFAULT_VERIFICATION_CAP,
        'executionEntries': active_execution_entries(entry),
        'validationScopes': validation_scopes_for_execution(entry),
        'touchedPaths': touched_paths_for_execution(entry),
        'sealStale': bool(isinstance(seal, dict) and seal.get('stale')),
        'freshRegistryRead': True,
    }
    if role:
        result['roleAgentId'] = participant_agent_id(entry, role)
        result['readyToSeal'] = role == reviewer_role(entry) and result['verificationSubState'] == 'verification'
    if resume:
        result['resume'] = f'tools/collab/registry.py seal-state --resume {entry["id"]} {role or reviewer_role(entry) or "<role>"}'
    print(json.dumps(result, sort_keys=True))
    return 0


def apply_cap_exit(entry: dict, data: dict, cap_exit: str | None) -> dict | None:
    if cap_exit is None:
        entry['status'] = 'closed'
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        return terminal_notice('closed')
    if cap_exit == 'archive':
        entry['status'] = 'archived'
        entry['archived'] = True
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        return terminal_notice('archived')
    if cap_exit == 'reopen-action-plan':
        entry['activePhase'] = 'Action Plan'
        normalize_turn_order_for_phase(entry, 'Action Plan')
        initialize_completion_state(entry, 'execution', reset_rounds=True)
        return {'notice': 'reopen', 'transition': 'Completion.verification->Action Plan', 'message': 'Verification cap exit reopened Action Plan.'}
    if cap_exit == 'reopen-handoff':
        entry['activePhase'] = 'Handoff'
        normalize_turn_order_for_phase(entry, 'Handoff')
        initialize_completion_state(entry, 'execution', reset_rounds=True)
        return {'notice': 'reopen', 'transition': 'Completion.verification->Handoff', 'message': 'Verification cap exit reopened Handoff.'}
    die(f'invalid cap-exit value {cap_exit}; must be one of: reopen-action-plan, reopen-handoff, archive')


def render_seal(
    path: Path,
    target: str,
    role: str,
    observed_revision: int,
    cap_exit: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    if cap_exit is not None and cap_exit not in ALLOWED_CAP_EXITS:
        die(f'invalid cap-exit value {cap_exit}; must be one of: reopen-action-plan, reopen-handoff, archive')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'seal-render', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] != 'Completion':
            die('/collab seal verification is valid only in the Completion phase')
        live_revision = registry_revision(data)
        if observed_revision != live_revision:
            die(
                f'stale registry revision: observed {observed_revision}, live {live_revision}\n'
                f'RESUME: tools/collab/registry.py seal-state --resume {entry["id"]} {role}'
            )
        reviewer = reviewer_role(entry)
        if reviewer is None:
            die('verification seal requires an active reviewer role')
        if reviewer_state(entry)['state'] != 'active':
            die(f'reviewer role is not a registered participant; run /collab join --role {reviewer} first')
        if role != reviewer:
            die(f'seal must be authored by the reviewer role; current role: {role}; expected: {reviewer}')
        if verification_substate(entry) != 'verification':
            die(f'Completion.verification sub-state is not active; current sub-state: {verification_substate(entry)}')
        verification = verification_state(entry)
        rounds = verification.get('rounds', 0)
        cap = verification.get('cap', DEFAULT_VERIFICATION_CAP)
        if rounds == 0:
            die('zero verification rounds; at least one reviewer-executor paired event is required before sealing')
        if cap_exit is None and rounds >= cap:
            die(
                'round cap reached; reissue with --cap-exit reopen-action-plan, '
                '--cap-exit reopen-handoff, or --cap-exit archive'
            )
        if not all_execution_completed(entry):
            die('verification seal requires all execution entries to be completed')
        seal = seal_snapshot(entry, observed_revision, role, cap_exit)
        entry['verificationSeal'] = seal
        notice = apply_cap_exit(entry, data, cap_exit)

        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        number = next_completion_history_number(transcript)
        scope_label = 'cap-exit' if cap_exit else 'seal'
        seal_line = (
            f"{number}. **{role}:** sealed {format_timestamp()} — verification passed; "
            f"{scope_label}; {len(seal['touchedPaths'])} paths."
        )
        rendered = append_completion_history_line(transcript, seal_line)
        rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
        if entry['status'] == 'closed' and completion_summary_empty(rendered):
            rendered = append_completion_summary(rendered, default_close_summary(entry), summary_date_from_iso(seal['sealedAt']))
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_post_action_advisories(entry, role, 'Completion', notice, next_line_for_state(entry))
    print(entry['status'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def reopen_collab(
    path: Path,
    target: str,
    phase_token: str,
    caller_role: str | None = None,
) -> int:
    if phase_token == 'action-plan':
        phase = 'Action Plan'
    elif phase_token == 'handoff':
        phase = 'Handoff'
    else:
        die('reopen phase must be one of: action-plan, handoff')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'set')
        if entry['status'] == 'archived':
            die('record is archived')
        entry['status'] = 'open'
        entry['archived'] = False
        entry['activePhase'] = phase
        data['activeCollabId'] = entry['id']
        normalize_turn_order_for_phase(entry, phase)
        initialize_completion_state(entry, 'execution', reset_rounds=True)
        invalidate_verification_seal(entry, f'reopened {phase}')
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_post_action_advisories(entry, None, None, None, next_line_for_state(entry))
    print(entry['id'])
    return 0


def render_status(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(transcript_path)
    return 0


def re_summarize_collab(path: Path, target: str, summary_file: Path, date: str | None = None) -> int:
    if not summary_file.exists():
        die(f'summary file missing: {summary_file}')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] == 'archived':
            die('record is archived')
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        summary_date = date or dt.date.today().isoformat()
        rendered = replace_latest_summary(transcript_path.read_text(), summary_file.read_text(), summary_date)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(entry['id'])
    return 0


def render_participants(path: Path, target: str, roles_dir: Path) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(transcript_path)
    return 0


def commit_registry_and_transcript(
    registry_path: Path,
    data: dict,
    transcript_path: Path,
    transcript_text: str,
) -> None:
    """Commit registry and transcript updates with rollback on known write failures.

    The registry file is replaced first, then the transcript file. If either
    replace fails, the helper restores the pre-operation contents it could read
    and reports which file may be inconsistent. This is a best-effort two-file
    transaction, not a filesystem-level atomic commit.
    """
    bump_registry_revision(data)
    validate_registry(data, registry_path)
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')

    registry_before = registry_path.read_text() if registry_path.exists() else None
    transcript_before = transcript_path.read_text()
    registry_after = json.dumps(data, indent=2) + '\n'
    registry_tmp = registry_path.with_name(f'{registry_path.name}.tmp')
    transcript_tmp = transcript_path.with_name(f'{transcript_path.name}.tmp')

    try:
        registry_tmp.write_text(registry_after)
        transcript_tmp.write_text(transcript_text)
        registry_tmp.replace(registry_path)
        transcript_tmp.replace(transcript_path)
    except OSError as exc:
        inconsistent: list[str] = []
        try:
            if registry_before is None:
                registry_path.unlink(missing_ok=True)
            else:
                registry_path.write_text(registry_before)
        except OSError:
            inconsistent.append(str(registry_path))
        try:
            transcript_path.write_text(transcript_before)
        except OSError:
            inconsistent.append(str(transcript_path))
        registry_tmp.unlink(missing_ok=True)
        transcript_tmp.unlink(missing_ok=True)
        if inconsistent:
            die(f'collab write failed; inconsistent state may remain: {", ".join(inconsistent)}: {exc}')
        die(f'collab write failed; restored pre-operation state: {exc}')


def commit_new_registry_and_transcript(
    registry_path: Path,
    data: dict,
    transcript_path: Path,
    transcript_text: str,
) -> None:
    bump_registry_revision(data)
    validate_registry(data, registry_path)
    if transcript_path.exists():
        die(f'record already exists: {transcript_path}')

    registry_before = registry_path.read_text() if registry_path.exists() else None
    registry_after = json.dumps(data, indent=2) + '\n'
    registry_tmp = registry_path.with_name(f'{registry_path.name}.tmp')
    transcript_tmp = transcript_path.with_name(f'{transcript_path.name}.tmp')

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        registry_tmp.write_text(registry_after)
        transcript_tmp.write_text(transcript_text)
        registry_tmp.replace(registry_path)
        transcript_tmp.replace(transcript_path)
    except OSError as exc:
        inconsistent: list[str] = []
        try:
            if registry_before is None:
                registry_path.unlink(missing_ok=True)
            else:
                registry_path.write_text(registry_before)
        except OSError:
            inconsistent.append(str(registry_path))
        try:
            transcript_path.unlink(missing_ok=True)
        except OSError:
            inconsistent.append(str(transcript_path))
        registry_tmp.unlink(missing_ok=True)
        transcript_tmp.unlink(missing_ok=True)
        if inconsistent:
            die(f'collab init failed; inconsistent state may remain: {", ".join(inconsistent)}: {exc}')
        die(f'collab init failed; restored pre-operation state: {exc}')


def open_browser_uri(uri: str, opener: Callable[[str], bool] = webbrowser.open_new_tab) -> str | None:
    try:
        opened = opener(uri)
    except Exception as exc:
        return f'{type(exc).__name__}: {exc}'
    if not opened:
        return 'no browser available'
    return None


def init_collab(
    path: Path,
    tokens: list[str],
    roles_dir: Path,
    opener: Callable[[str], bool] = webbrowser.open_new_tab,
) -> int:
    title, agent_id, reviewer, open_requested = parse_init_tokens(tokens)
    with registry_lock(path):
        data = load_registry_or_bootstrap(path)
        date = dt.date.today().isoformat()
        slug = normalize_slug(title)
        collab_id = f'{date}-{slug}'
        transcript_rel = f'.collabs/records/{collab_id}.md'
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
        if reviewer:
            entry['reviewerRole'] = reviewer
            entry['reviewerMode'] = DEFAULT_REVIEWER_MODE
            entry['reviewerOptionalPhases'] = list(DEFAULT_REVIEWER_OPTIONAL_PHASES)

        next_data = deepcopy(data)
        next_data['collabs'].append(entry)
        next_data['activeCollabId'] = collab_id
        rendered = render_initial_transcript(title, entry, roles_dir, format_banner_timestamp())
        commit_new_registry_and_transcript(path, next_data, transcript_path, rendered)
    print(transcript_path)
    if open_requested:
        file_uri = transcript_path.resolve().as_uri()
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

        next_data = deepcopy(data)
        next_entry = resolve_collab(next_data, target)
        add_participant_to_entry(next_entry, role, normalized_agent_id)
        validate_registry(next_data, path)

        transcript_path = Path(next_entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()

        rendered, header_changed = render_managed_header_text(transcript, next_entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, next_data, transcript_path, rendered)
    print_post_action_advisories(
        next_entry,
        role,
        next_entry['activePhase'],
        None,
        'NEXT: Run /collab show policy before first speak.',
    )
    print(f'IDENTITY: {role} {recorded_agent_id}')
    if identity_warning:
        print(identity_warning)
    print(' '.join(participant_roles(next_entry)))
    if emit_json:
        print(json.dumps({
            'agentId': recorded_agent_id,
            'freshRegistryRead': True,
            'identityWarning': identity_warning,
            'participants': participant_roles(next_entry),
            'target': next_entry['id'],
        }, sort_keys=True))
    return 0


def write_guard(route: str, paths: list[str]) -> int:
    if not paths:
        die('write-guard requires at least one path')
    if route == 'execute':
        print('ok')
        return 0
    for item in paths:
        normalized = Path(item).as_posix()
        if normalized.startswith('./'):
            normalized = normalized[2:]
        if Path(item).is_absolute() or not (normalized == '.collabs' or normalized.startswith('.collabs/')):
            die(f'route may only write under .collabs: {route}: {item}')
    print('ok')
    return 0


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
        entry['status'] = 'archived'
        entry['archived'] = True
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        transcript_path = Path(entry['transcriptPath'])
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
            print_header_overwrite(header_changed)
            commit_registry_and_transcript(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    notice = terminal_notice('archived')
    print_post_action_advisories(entry, None, None, notice, next_line_for_state(entry))
    print(entry['id'])
    print_notice_diagnostic(notice, emit_json)
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
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        violations = completed_execution_unchecked_items(entry, transcript)
        if violations:
            details = ', '.join(
                f"{item['role']}={item['uncheckedCount']}" for item in violations
            )
            die(f'close blocked: completed execution has unchecked assigned Action Plan item(s): {details}')
        if reviewer_backed(entry) and entry['activePhase'] == 'Completion':
            seal = entry.get('verificationSeal')
            if not isinstance(seal, dict):
                die('close blocked: reviewer-backed Completion requires verificationSeal')
            if seal.get('stale'):
                reason = seal.get('staleReason') or 'unknown'
                die(f'close blocked: verificationSeal is stale: {reason}')
        entry['status'] = 'closed'
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    notice = terminal_notice('closed')
    print_post_action_advisories(entry, None, None, notice, next_line_for_state(entry))
    print(entry['id'])
    print_notice_diagnostic(notice, emit_json)
    return 0


def audit_closed(path: Path) -> int:
    data = load_registry(path)
    findings: list[dict] = []
    for entry in data['collabs']:
        if entry['status'] != 'closed':
            continue
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        violations = completed_execution_unchecked_items(entry, transcript)
        for violation in violations:
            findings.append({
                'target': entry['id'],
                'role': violation['role'],
                'uncheckedCount': violation['uncheckedCount'],
            })
        findings.extend(effort_override_audit_items(entry['id'], transcript))
    print(json.dumps(findings, sort_keys=True))
    return 0


def delete_collab(path: Path, target: str, confirmed: bool, caller_role: str | None = None) -> int:
    if not confirmed:
        die('delete requires --yes confirmation')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'delete')
        transcript_path = Path(entry['transcriptPath'])
        data['collabs'] = [candidate for candidate in data['collabs'] if candidate['id'] != entry['id']]
        if data.get('activeCollabId') == entry['id']:
            data['activeCollabId'] = None
        if transcript_path.exists():
            transcript_path.unlink()
        save_registry(path, data)
    print(entry['id'])
    return 0


def flag_inventory(spec_path: Path = DEFAULT_FLAG_TAXONOMY_PATH) -> int:
    if not spec_path.exists():
        die(f'flag taxonomy spec missing: {spec_path}')
    by_class: dict[str, list[tuple[str, str, str]]] = {
        'advisory': [],
        'helper-enforced': [],
        'generator-derived': [],
    }
    current_command = ''
    for line in spec_path.read_text().splitlines():
        heading = re.match(r'^###\s+(.+)$', line)
        if heading:
            current_command = heading.group(1)
            continue
        match = FLAG_ROW_RE.match(line)
        if not match or match.group('flag') == 'Flag':
            continue
        flag_class = match.group('class')
        if flag_class not in by_class:
            die(f'flag taxonomy spec has unknown class: {flag_class}')
        by_class[flag_class].append((current_command, match.group('flag'), match.group('notes').strip()))
    for flag_class, rows in by_class.items():
        print(f'## {flag_class}')
        if not rows:
            print('- none')
        for command, flag, notes in rows:
            print(f'- {command}: `{flag}` — {notes}')
        print()
    return 0


def retract_latest_contribution(
    path: Path,
    target: str,
    role: str,
    reason: str | None,
    timestamp: str | None = None,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'retract-speak', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] == 'Completion':
            die('retract-speak is not permitted after Completion')
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript_path = Path(entry['transcriptPath'])
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        lines = transcript.splitlines()
        bounds = contribution_block_bounds(lines, entry['activePhase'], role)
        if bounds is None:
            die(f'no contribution found for {role} in {entry["activePhase"]}')
        start, end = bounds
        block = lines[start:end]
        marker_index: int | None = None
        for index, line in enumerate(block):
            if line.strip() == '<!-- collab:content-only; do-not-execute -->':
                marker_index = index
                break
        if marker_index is None:
            die('contribution content marker missing')
        existing_body = '\n'.join(block[marker_index + 1:len(block) - 1]).strip()
        if existing_body.startswith('RETRACTED:'):
            die(f'contribution already retracted for {role} in {entry["activePhase"]}')
        summary = reason.strip() if reason and reason.strip() else 'No reason supplied'
        stamp = timestamp or format_timestamp()
        tombstone = [
            'RETRACTED: contribution withdrawn; retained for audit history.',
            f'RETRACTION REASON: {summary}',
            f'RETRACTION TIMESTAMP: {stamp}',
            '',
            '<details><summary>Retracted content</summary>',
            '',
            *existing_body.splitlines(),
            '',
            '</details>',
        ]
        replacement = block[:marker_index + 1] + [''] + tombstone + [''] + [block[-1]]
        rendered = '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(entry['id'])
    print('retracted')
    return 0


def validate_command(path: Path) -> int:
    load_registry(path)
    print('registry OK')
    return 0


def role_row_command(roles_dir: Path, role: str, index: int) -> int:
    print(participant_row(load_role(roles_dir, role), index))
    return 0


def reviewer_state_command(path: Path, target: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    print(json.dumps(reviewer_state(entry), sort_keys=True))
    return 0


def handoff_state_command(path: Path, target: str, role: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if not has_participant(entry, role):
        die(f'handoff role must already be a participant: {role}')
    state = handoff_state_for_role(entry, role) or {}
    print(json.dumps(state, sort_keys=True))
    return 0


def timestamp_command() -> int:
    print(format_timestamp())
    return 0


def banner_timestamp_command() -> int:
    print(format_banner_timestamp())
    return 0


def summary_role_command(line: str) -> int:
    role = summary_role(line)
    if role is None:
        die('summary role unavailable')
    print(role)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Shared collab registry helper.')
    parser.add_argument(
        '--registry',
        default='.collabs/registry.json',
        help='Path to the collab registry JSON file.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('validate')
    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('--status', choices=sorted(ALLOWED_STATUSES))
    flag_inventory_parser = subparsers.add_parser('flag-inventory')
    flag_inventory_parser.add_argument('--spec', default=str(DEFAULT_FLAG_TAXONOMY_PATH))
    subparsers.add_parser('timestamp')
    subparsers.add_parser('banner-timestamp')

    role_row_parser = subparsers.add_parser('role-row')
    role_row_parser.add_argument('role')
    role_row_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    role_row_parser.add_argument('--index', type=int, default=1)

    roles_parser = subparsers.add_parser('roles')
    roles_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))

    summary_role_parser = subparsers.add_parser('summary-role')
    summary_role_parser.add_argument('line')

    reviewer_state_parser = subparsers.add_parser('reviewer-state')
    reviewer_state_parser.add_argument('target')

    handoff_state_parser = subparsers.add_parser('handoff-state')
    handoff_state_parser.add_argument('target')
    handoff_state_parser.add_argument('role')

    activate_parser = subparsers.add_parser('activate')
    activate_parser.add_argument('target')

    init_parser = subparsers.add_parser(
        'init',
        usage='%(prog)s --agent-id <agentId> [--reviewer <role>] [--preview] <name>',
        description='Create a registry-backed collab record.',
    )
    init_parser.add_argument('--agent-id', action='append')
    init_parser.add_argument('--reviewer', action='append')
    init_parser.add_argument('--preview', action='store_true')
    init_parser.add_argument('name', nargs='*')

    join_participants_parser = subparsers.add_parser('join-participants')
    join_participants_parser.add_argument('target')
    join_participants_parser.add_argument('role')
    join_participants_parser.add_argument('--agent-id', required=True)
    join_participants_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    join_participants_parser.add_argument('--json', action='store_true')

    set_parser = subparsers.add_parser('set')
    set_parser.add_argument('target')
    set_parser.add_argument('field')
    set_parser.add_argument('value', nargs='?')
    set_parser.add_argument('--force', action='store_true')
    set_parser.add_argument('--clear', action='store_true')
    set_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    set_parser.add_argument('--caller-role')

    unset_parser = subparsers.add_parser('unset')
    unset_parser.add_argument('target')
    unset_parser.add_argument('field')
    unset_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    unset_parser.add_argument('--caller-role')

    effort_state_parser = subparsers.add_parser('effort-state')
    effort_state_parser.add_argument('target')
    effort_state_parser.add_argument('role')
    effort_state_parser.add_argument('--effort-defaults', default=str(DEFAULT_EFFORT_PATH))

    advance_parser = subparsers.add_parser('advance')
    advance_parser.add_argument('target')
    advance_parser.add_argument('direction', choices=['next', 'prev'])
    advance_parser.add_argument('--json', action='store_true')
    advance_parser.add_argument('--caller-role')

    speak_parser = subparsers.add_parser('speak-lifecycle')
    speak_parser.add_argument('target')
    speak_parser.add_argument('contributors', nargs='+')

    speak_state_parser = subparsers.add_parser('speak-state')
    speak_state_parser.add_argument('target')
    speak_state_parser.add_argument('role')
    speak_state_parser.add_argument('--resume', action='store_true')

    speak_live_parser = subparsers.add_parser('speak-lifecycle-live')
    speak_live_parser.add_argument('target')

    speak_render_parser = subparsers.add_parser('speak-render')
    speak_render_parser.add_argument('target')
    speak_render_parser.add_argument('role')
    speak_render_parser.add_argument('--content-file', required=True)
    speak_render_parser.add_argument('--observed-revision', type=int, required=True)
    speak_render_parser.add_argument('--timestamp')
    speak_render_parser.add_argument('--json', action='store_true')
    speak_render_parser.add_argument('--caller-role')
    speak_render_parser.add_argument('--verbatim', action='store_true')

    re_speak_render_parser = subparsers.add_parser('rewrite-speak-render')
    re_speak_render_parser.add_argument('target')
    re_speak_render_parser.add_argument('role')
    re_speak_render_parser.add_argument('--content-file', required=True)
    re_speak_render_parser.add_argument('--timestamp')
    re_speak_render_parser.add_argument('--caller-role')

    retract_speak_parser = subparsers.add_parser('retract-speak')
    retract_speak_parser.add_argument('target')
    retract_speak_parser.add_argument('role')
    retract_speak_parser.add_argument('--reason')
    retract_speak_parser.add_argument('--timestamp')
    retract_speak_parser.add_argument('--caller-role')

    execution_parser = subparsers.add_parser('execution')
    execution_parser.add_argument('target')
    execution_parser.add_argument('role')
    execution_parser.add_argument('status', choices=sorted(ALLOWED_EXECUTION_STATUSES))
    execution_parser.add_argument('date')
    execution_parser.add_argument('--assigned-role', action='append', default=[])
    execution_parser.add_argument('--auto-close', action='store_true')
    execution_parser.add_argument('--validation-result')
    execution_parser.add_argument('--validation-scope', choices=sorted(ALLOWED_VALIDATION_SCOPES))
    execution_parser.add_argument('--touched-path', action='append', default=[])
    execution_parser.add_argument('--json', action='store_true')
    execution_parser.add_argument('--caller-role')

    execute_spawn_parser = subparsers.add_parser('execute-spawn')
    execute_spawn_parser.add_argument('target')
    execute_spawn_parser.add_argument('role')
    execute_spawn_parser.add_argument('--scope', required=True)
    execute_spawn_parser.add_argument('--sibling-scope', action='append', default=[])
    execute_spawn_parser.add_argument('--returned-path', action='append', default=[])

    transcript_repair_parser = subparsers.add_parser('transcript-repair')
    transcript_repair_parser.add_argument('target')
    transcript_repair_parser.add_argument('--touch-execution-evidence', action='store_true')
    transcript_repair_parser.add_argument('--caller-role')

    out_of_scope_patch_parser = subparsers.add_parser('out-of-scope-patch')
    out_of_scope_patch_parser.add_argument('target')
    out_of_scope_patch_parser.add_argument('role')
    out_of_scope_patch_parser.add_argument('--path', required=True)
    out_of_scope_patch_parser.add_argument('--caller-role')

    seal_state_parser = subparsers.add_parser('seal-state')
    seal_state_parser.add_argument('target')
    seal_state_parser.add_argument('role', nargs='?')
    seal_state_parser.add_argument('--resume', action='store_true')

    seal_render_parser = subparsers.add_parser('seal-render')
    seal_render_parser.add_argument('target')
    seal_render_parser.add_argument('role')
    seal_render_parser.add_argument('--observed-revision', type=int, required=True)
    seal_render_parser.add_argument('--cap-exit')
    seal_render_parser.add_argument('--json', action='store_true')
    seal_render_parser.add_argument('--caller-role')

    reopen_parser = subparsers.add_parser('reopen')
    reopen_parser.add_argument('target')
    reopen_parser.add_argument('phase', choices=['action-plan', 'handoff'])
    reopen_parser.add_argument('--caller-role')

    re_summarize_parser = subparsers.add_parser('rewrite-summary')
    re_summarize_parser.add_argument('target')
    re_summarize_parser.add_argument('--summary-file', required=True)
    re_summarize_parser.add_argument('--date')

    close_parser = subparsers.add_parser('close')
    close_parser.add_argument('target')
    close_parser.add_argument('--json', action='store_true')
    close_parser.add_argument('--caller-role')

    subparsers.add_parser('audit-closed')

    archive_parser = subparsers.add_parser('archive')
    archive_parser.add_argument('target')
    archive_parser.add_argument('--json', action='store_true')
    archive_parser.add_argument('--caller-role')

    delete_parser = subparsers.add_parser('delete')
    delete_parser.add_argument('target')
    delete_parser.add_argument('--yes', action='store_true')
    delete_parser.add_argument('--caller-role')

    render_status_parser = subparsers.add_parser('render-status')
    render_status_parser.add_argument('target')

    render_participants_parser = subparsers.add_parser('render-participants')
    render_participants_parser.add_argument('target')
    render_participants_parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))

    write_guard_parser = subparsers.add_parser('write-guard')
    write_guard_parser.add_argument('route')
    write_guard_parser.add_argument('paths', nargs='+')

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args, unknown_args = parser.parse_known_args(argv)
    if unknown_args:
        if args.command == 'init':
            for item in unknown_args:
                if item.startswith('--'):
                    die(f'unknown flag: {item}')
        parser.error(f'unrecognized arguments: {" ".join(unknown_args)}')
    path = Path(args.registry)

    if args.command == 'validate':
        return validate_command(path)
    if args.command == 'list':
        return list_collabs(load_registry(path), args.status)
    if args.command == 'flag-inventory':
        return flag_inventory(Path(args.spec))
    if args.command == 'timestamp':
        return timestamp_command()
    if args.command == 'banner-timestamp':
        return banner_timestamp_command()
    if args.command == 'role-row':
        return role_row_command(Path(args.roles_dir), args.role, args.index)
    if args.command == 'roles':
        return roles_command(Path(args.roles_dir))
    if args.command == 'summary-role':
        return summary_role_command(args.line)
    if args.command == 'reviewer-state':
        return reviewer_state_command(path, args.target)
    if args.command == 'handoff-state':
        return handoff_state_command(path, args.target, args.role)
    if args.command == 'activate':
        return activate_collab(path, args.target)
    if args.command == 'init':
        tokens: list[str] = []
        for agent_id in args.agent_id or []:
            tokens.extend(['--agent-id', agent_id])
        for reviewer in args.reviewer or []:
            tokens.extend(['--reviewer', reviewer])
        if args.preview:
            tokens.append('--preview')
        tokens.extend(args.name)
        return init_collab(path, tokens, DEFAULT_ROLES_DIR)
    if args.command == 'join-participants':
        return join_participants(path, args.target, args.role, args.agent_id, Path(args.roles_dir), args.json)
    if args.command == 'set':
        value = '--clear' if args.clear else args.value
        return set_field(path, args.target, args.field, value, args.force, Path(args.roles_dir), args.caller_role)
    if args.command == 'unset':
        return unset_field(path, args.target, args.field, Path(args.roles_dir), args.caller_role)
    if args.command == 'effort-state':
        return effort_state(path, args.target, args.role, Path(args.effort_defaults))
    if args.command == 'speak-lifecycle':
        return speak_lifecycle(path, args.target, args.contributors)
    if args.command == 'speak-state':
        return speak_state(path, args.target, args.role, args.resume)
    if args.command == 'speak-lifecycle-live':
        return speak_lifecycle_live(path, args.target)
    if args.command == 'speak-render':
        return render_speak(
            path,
            args.target,
            args.role,
            Path(args.content_file),
            args.observed_revision,
            args.timestamp,
            args.json,
            args.caller_role,
            args.verbatim,
        )
    if args.command == 'rewrite-speak-render':
        return render_re_speak(path, args.target, args.role, Path(args.content_file), args.timestamp, args.caller_role)
    if args.command == 'retract-speak':
        return retract_latest_contribution(path, args.target, args.role, args.reason, args.timestamp, args.caller_role)
    if args.command == 'advance':
        return advance_phase(path, args.target, args.direction, args.json, args.caller_role)
    if args.command == 'execution':
        return record_execution(
            path,
            args.target,
            args.role,
            args.status,
            args.date,
            args.assigned_role,
            args.auto_close,
            args.validation_result,
            args.validation_scope,
            args.touched_path,
            args.json,
            args.caller_role,
        )
    if args.command == 'execute-spawn':
        return execute_spawn(path, args.target, args.role, args.scope, args.sibling_scope, args.returned_path)
    if args.command == 'transcript-repair':
        return transcript_repair(path, args.target, args.touch_execution_evidence, args.caller_role)
    if args.command == 'out-of-scope-patch':
        return out_of_scope_patch(path, args.target, args.role, args.path, args.caller_role)
    if args.command == 'seal-state':
        return seal_state(path, args.target, args.role, args.resume)
    if args.command == 'seal-render':
        return render_seal(
            path,
            args.target,
            args.role,
            args.observed_revision,
            args.cap_exit,
            args.json,
            args.caller_role,
        )
    if args.command == 'reopen':
        return reopen_collab(path, args.target, args.phase, args.caller_role)
    if args.command == 'rewrite-summary':
        return re_summarize_collab(path, args.target, Path(args.summary_file), args.date)
    if args.command == 'close':
        return close_collab(path, args.target, args.json, args.caller_role)
    if args.command == 'audit-closed':
        return audit_closed(path)
    if args.command == 'archive':
        return archive_collab(path, args.target, args.json, args.caller_role)
    if args.command == 'delete':
        return delete_collab(path, args.target, args.yes, args.caller_role)
    if args.command == 'render-status':
        return render_status(path, args.target)
    if args.command == 'render-participants':
        return render_participants(path, args.target, Path(args.roles_dir))
    if args.command == 'write-guard':
        return write_guard(args.route, args.paths)
    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
