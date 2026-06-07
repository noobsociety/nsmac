"""Pure slug, title, path, scope, and validation-arg normalization; does not own registry state or I/O."""
# Tests: slug/title/path normalization, scope-matching (glob and prefix), execution-datetime parsing,
#        restore-target normalization, touched-path deduplication, agent-id validation.
from __future__ import annotations

import datetime as dt
import fnmatch
import re
from pathlib import Path, PurePosixPath

from commands.collab.engine.errors import die
from commands.collab.engine.registry_constants import (
    ALLOWED_VERDICT_RESTORE_TARGETS,
    CALLER_DECLINED_AGENT_ID,
    GLOB_PATTERN_RE,
    INVALID_AGENT_ID_ALTERNATIVES,
    PHASES,
)

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

def phase_slug(phase: str) -> str:
    return phase.lower().replace(' ', '-')

def display_title(title: str, limit: int = 20) -> str:
    if len(title) <= limit:
        return title
    return title[:limit] + '…'

def collab_date(entry: dict) -> str:
    return entry['id'][:10]

def normalize_join_agent_id(agent_id: str | None) -> str:
    if agent_id is None:
        die('agent-id is required')
    normalized = agent_id.strip()
    if not normalized:
        die('agent-id is required')
    if normalized.lower() == 'unknown' and normalized != 'unknown':
        die('agent-id unknown token must be lowercase: unknown')
    if normalized.lower() == CALLER_DECLINED_AGENT_ID and normalized != CALLER_DECLINED_AGENT_ID:
        die(f'agent-id caller-declined token must be lowercase: {CALLER_DECLINED_AGENT_ID}')
    if normalized.lower() in INVALID_AGENT_ID_ALTERNATIVES:
        die('agent-id must use the literal unknown when identity is unavailable')
    return normalized

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

def normalize_touched_paths(touched_paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in touched_paths:
        path = normalize_scope_path(item, 'touched-path')
        if path not in normalized:
            normalized.append(path)
    return normalized

def parse_execution_datetime(raw: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return parsed

def normalize_restore_target(value: str | None, current_phase: str) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r'[\s_-]+', '-', value.strip().lower()).strip('-')
    by_token = {re.sub(r'[\s_-]+', '-', phase.lower()).strip('-'): phase for phase in PHASES}
    target = by_token.get(normalized)
    if target is None:
        die(f'verdict restoreTarget must be one of {PHASES}')
    if target not in ALLOWED_VERDICT_RESTORE_TARGETS:
        die('verdict restoreTarget must be one of: Action Plan, Handoff')
    if PHASES.index(target) > PHASES.index(current_phase):
        die(f'verdict restoreTarget must not be later than current phase {current_phase}')
    return target

def assert_one_line_nonempty(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        die(f'verdict {field} must be a non-empty string when present')
    if '\n' in stripped or '\r' in stripped:
        die(f'verdict {field} must be one line')
    return stripped
