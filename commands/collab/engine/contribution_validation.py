"""Speak-time contribution validation and moderator contribution normalization.

Owns content gates over a proposed contribution before it is rendered. Does not
own registry persistence, transcript rendering, phase lifecycle, or CLI dispatch.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from commands.collab.engine import transcript_readers
from commands.collab.engine.digests import strip_managed_full_body_lines
from commands.collab.engine.errors import die
from commands.collab.engine.participants import effective_turn_order, phase_turn_order, reviewer_role
from commands.collab.engine.transcript_readers import (
    ACTION_CHECKLIST_RE,
    ACTION_PLAN_ALLOWED_ITEM_TAG_LIST,
    STANCE_DECLARATION_RE,
)
from commands.collab.engine.transcript_render import is_hidden_metadata_line


ROOT = Path(__file__).resolve().parents[3]


def resolve_config_root() -> Path:
    configured_value = os.environ.get('COMMAND_CONFIG_ROOT')
    if configured_value:
        return Path(configured_value).expanduser().resolve()
    if (ROOT / 'commands').is_dir():
        return ROOT
    return ROOT


DEFAULT_CONFIG_ROOT = resolve_config_root()
DEFAULT_BUDGET_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/contribution-budget.md'
DEFAULT_MODERATOR_POLISH_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/moderator-polish.md'
ACTION_PLAN_SHAPE_RE = re.compile(r'^- \[[ x]\] \*\*[a-z]+:\*\*')
ACTION_PLAN_EXEMPT_RE = re.compile(r'^\s*-\s+\[[ xX]\]\s+\*\*[A-Za-z0-9_-]+:\*\*')
ACTION_PLAN_EXECUTE_TAG = '[execute]'
UNLABELED_ACTION_CHECKBOX_RE = re.compile(r'^\s*-\s+\[ \]\s+(?!\*\*[A-Za-z0-9_-]+:\*\*)\S')
EFFORT_OVERRIDE_RE = re.compile(
    r'^EFFORT OVERRIDE: (?:(matrix)|'
    r'(low|medium|high|xhigh|max)\s+\u2014\s+'
    r'(coherence-risk|implementation-density|deadlock-or-disagreement|delivery-or-migration-risk|reviewer-concern-raised):\s+.+)$'
)
CONCLUSION_DIRECTIVE_LINE_RE = re.compile(r'^\*\*Directive:\*\*\s+"[^"]+"\s*$')
CONCLUSION_ACTION_PLAN_LINE_RE = re.compile(
    r'^\*\*Action Plan:\s*(?P<status>satisfies|partially satisfies|defers)\*\*(?P<detail>.*)$'
)
MANDATORY_EFFORT_OVERRIDE_TURNS = {
    ('Audit', 'pa'),
    ('Conclusion', 'pa'),
    ('Completion', 'pa'),
    ('Handoff', 'tw'),
    ('Handoff', 'pe'),
}
TYPO_ROW_RE = re.compile(r'^\|\s*`(?P<typo>[^`]+)`\s*\|\s*`(?P<fix>[^`]+)`')
ACTION_PLAN_SHAPE_EXAMPLE = '- [ ] **tw:** Update the route doc.'
REVIEWER_DISCIPLINE_GATES = (
    'DIRECTIVE TEST',
    'AUDIT CONFIRMED',
    'PRECEDENT CITED',
    'LOOP CHECK',
)


def assert_turn_order_not_drifted(entry: dict, phase: str) -> list[str]:
    expected = phase_turn_order(entry, phase)
    actual = effective_turn_order(entry)
    if actual != expected:
        die(
            'TURN-ORDER-DRIFT: '
            f'phase={phase}; actual={" ".join(actual)}; expected={" ".join(expected)}'
        )
    return expected


def read_budget_spec(path: Path = DEFAULT_BUDGET_PATH) -> dict:
    if not path.exists():
        die(f'contribution budget spec missing: {path}')
    text = path.read_text()
    limit_match = re.search(r'capped at \*\*(\d+) words\*\*', text)
    if not limit_match:
        die(f'contribution budget spec missing word limit: {path}')
    classes = set(re.findall(r'\|\s*`([a-z0-9-]+)`\s*\|', text))
    required = {
        'action-plan-checklist',
        'conclusion-ratification',
        'moderator-verbatim',
        'effort-override-line',
        'stance-declaration-line',
        'contribution-full-body',
    }
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
    lines = strip_managed_full_body_lines(content.splitlines(), 'contribution body')
    for line in lines:
        stripped = line.strip()
        if is_hidden_metadata_line(stripped):
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
    if role == moderator_role:
        return
    countable_text = '\n'.join(budget_countable_lines(content, phase))
    count = len(countable_text.split())
    limit = spec['limit']
    if count > limit:
        die(
            f'contribution excerpt is {count} words; limit is {limit}; '
            'keep --content-file as a capped standalone excerpt and put complete detail in --full-body-file'
        )


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
        f"(Invariant #9, invariants.md). Offending line: '{line}'. "
        f"Example: '{ACTION_PLAN_SHAPE_EXAMPLE}'"
    )


def action_plan_tag_abort(line_number: int, line: str) -> None:
    tags = ', '.join(ACTION_PLAN_ALLOWED_ITEM_TAG_LIST)
    die(
        f'ABORT: line {line_number} missing recognized Action Plan item tag; '
        'loop target: Action Plan for missing executable scope. '
        f'Expected one of: {tags}. Offending line: {line!r}.'
    )


def action_plan_executable_scope_abort() -> None:
    die(
        'ABORT: action-plan advance blocked: missing [execute] item for execution directive; '
        'loop target: Action Plan for missing executable scope.'
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
        if is_hidden_metadata_line(stripped):
            continue
        if is_markdown_heading(line):
            continue
        if ACTION_PLAN_SHAPE_RE.match(line):
            match = ACTION_CHECKLIST_RE.match(line)
            if not match or transcript_readers.action_plan_item_tag(match.group('text').strip()) is None:
                action_plan_tag_abort(line_number, line)
            saw_assignment = True
            continue
        action_plan_shape_abort(line_number, line)
    if not saw_assignment:
        die(
            'ABORT: Action Plan body contains no assignment lines after exempt content is removed '
            f"(Invariant #9, invariants.md). Example: '{ACTION_PLAN_SHAPE_EXAMPLE}'"
        )


def validate_action_plan_executable_scope(transcript: str) -> None:
    items = transcript_readers.action_plan_checklist_items(transcript)
    if not items:
        action_plan_executable_scope_abort()
    if not any(item.get('tag') == ACTION_PLAN_EXECUTE_TAG for item in items):
        action_plan_executable_scope_abort()


def first_substantive_lines(content: str, limit: int) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
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
        if STANCE_DECLARATION_RE.match(stripped) or EFFORT_OVERRIDE_RE.match(stripped):
            continue
        lines.append((line_number, stripped))
        if len(lines) >= limit:
            break
    return lines


def conclusion_directive_gap_abort() -> None:
    die(
        'CONCLUSION-DIRECTIVE-GAP-MISSING: loop target: Completion/Conclusion '
        'for missing directive-gap evidence. Expected first lines: '
        '\'**Directive:** "<active directive>"\' and '
        '\'**Action Plan: satisfies | partially satisfies | defers**\'.'
    )


def validate_conclusion_directive_gap(content: str, phase: str) -> None:
    if phase != 'Conclusion':
        return
    lines = first_substantive_lines(content, 2)
    if len(lines) < 2:
        conclusion_directive_gap_abort()
    directive_line = lines[0][1]
    action_line = lines[1][1]
    if not CONCLUSION_DIRECTIVE_LINE_RE.match(directive_line):
        conclusion_directive_gap_abort()
    match = CONCLUSION_ACTION_PLAN_LINE_RE.match(action_line)
    if not match:
        conclusion_directive_gap_abort()
    if match.group('status') in {'partially satisfies', 'defers'} and not match.group('detail').strip():
        conclusion_directive_gap_abort()


def validate_reviewer_conclusion_gates(content: str, phase: str, role: str, entry: dict) -> None:
    if phase != 'Conclusion' or role != reviewer_role(entry):
        return
    missing = [gate for gate in REVIEWER_DISCIPLINE_GATES if gate not in content]
    if missing:
        die('REVIEWER-CONCLUSION-GATE-MISSING: ' + ', '.join(missing))


def validate_effort_override(content: str, phase: str, role: str, moderator_role: str) -> None:
    if role == moderator_role:
        return
    lines = content.splitlines()
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
    first_content_index: int | None = None
    in_html_comment = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if in_html_comment:
            if '-->' in stripped:
                in_html_comment = False
            continue
        if stripped.startswith('<!--'):
            if '-->' not in stripped[stripped.find('<!--') + 4:]:
                in_html_comment = True
            continue
        if not stripped or STANCE_DECLARATION_RE.match(stripped):
            continue
        first_content_index = index
        break
    if first_index != first_content_index:
        die('EFFORT OVERRIDE must be the first content line')
    if not EFFORT_OVERRIDE_RE.match(first_override):
        die('EFFORT OVERRIDE line has invalid format')
    if len(override_lines) > 1:
        die('EFFORT OVERRIDE must appear at most once')


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
                line = re.sub(
                    re.escape(typo),
                    lambda match, replacement=fix: preserve_case_replacement(match, replacement),
                    line,
                    flags=re.IGNORECASE,
                )
            list_match = re.match(r'^(\s*-\s+)([a-z])', line)
            if list_match:
                line = list_match.group(1) + list_match.group(2).upper() + line[list_match.end():]
            elif line and line[0].islower():
                line = line[0].upper() + line[1:]
            if (
                line
                and not EFFORT_OVERRIDE_RE.match(line.strip())
                and not line.endswith(('.', '?', '!', ':', '`'))
                and not line.lstrip().startswith(('- ', '#', '|'))
            ):
                line += '.'
        rendered.append(line)
    return '\n'.join(rendered).rstrip('\n')
