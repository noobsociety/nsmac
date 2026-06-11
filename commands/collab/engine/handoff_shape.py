"""Handoff writeScope and validationCommands schema validation and parsing; does not own handoff lifecycle or state."""
# Tests: writeScope validation (absolute, glob, duplicate, overlength paths), validationCommands
#        validation (argv shape, shell-pattern rejection), effort-override encode/decode round-trip,
#        handoff body section parsing (writeScope and validationCommands extraction).
from __future__ import annotations

import base64
import json
import re
from pathlib import Path, PurePosixPath

from commands.collab.engine.errors import die, handoff_abort
from commands.collab.engine.registry_constants import (
    DISALLOWED_VERSION_FIELD,
    MAX_HANDOFF_SCOPE_COUNT,
    MAX_HANDOFF_SCOPE_LENGTH,
    MAX_VALIDATION_ARG_LENGTH,
    MAX_VALIDATION_COMMAND_ARGS,
    MAX_VALIDATION_COMMANDS,
    SHELL_PATTERN_RE,
)

STRUCTURED_HANDOFF_HEADING_RE = re.compile(r'^\s*\*\*(?P<field>writeScope|validationCommands):?\*\*:?\s*(?P<rest>.*)$')
CODE_SPAN_RE = re.compile(r'`([^`]+)`')
EFFORT_OVERRIDE_RE = re.compile(
    r'^EFFORT OVERRIDE: (?:(matrix)|'
    r'(low|medium|high|xhigh|max)\s+—\s+'
    r'(coherence-risk|implementation-density|deadlock-or-disagreement|delivery-or-migration-risk|reviewer-concern-raised):\s+.+)$'
)
EFFORT_OVERRIDE_COMMENT_RE = re.compile(
    r'^<!-- collab:effort-override b64:(?P<payload>[A-Za-z0-9_-]+={0,2}) -->$'
)
STANCE_DECLARATION_RE = re.compile(r'^\s*STANCE:\s*(converges|dissents|qualifies)\s*$', re.IGNORECASE)


def effort_override_metadata_comment(line: str) -> str:
    payload = base64.urlsafe_b64encode(line.encode()).decode()
    return f'<!-- collab:effort-override b64:{payload} -->'


def render_content_for_transcript(content: str) -> list[str]:
    rendered: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        stance = STANCE_DECLARATION_RE.match(stripped)
        if stance:
            rendered.append(f'<!-- collab:stance {stance.group(1).lower()} -->')
            continue
        if EFFORT_OVERRIDE_RE.match(stripped):
            rendered.append(effort_override_metadata_comment(stripped))
        else:
            rendered.append(line)
    return rendered

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

def validate_handoff_state(value: object, source: str, reject_version_field: bool = True) -> dict:
    if not isinstance(value, dict):
        die(f'{source}: handoff state must be an object')
    if reject_version_field and DISALLOWED_VERSION_FIELD in value:
        die(f'{source}: handoff state contains disallowed version field')
    write_scope = validate_handoff_write_scope(value.get('writeScope'))
    validation_commands = validate_handoff_validation_commands(value.get('validationCommands'))
    body = value.get('body')
    if body is not None and not isinstance(body, str):
        die(f'{source}: handoff body must be a string when present')
    normalized = dict(value)
    normalized['writeScope'] = write_scope
    normalized['validationCommands'] = validation_commands
    return normalized

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
        'writeScope': parse_write_scope_section(sections['writeScope']),
        'validationCommands': parse_validation_commands_section(sections['validationCommands']),
        'body': '\n'.join(render_content_for_transcript(content)).rstrip('\n'),
    }
    return validate_handoff_state(state, 'handoff')

def set_handoff_state(entry: dict, role: str, state: dict) -> None:
    handoff = entry.setdefault('handoff', {'roles': {}})
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
