"""Transcript phase parsing and contribution-block extraction; does not own registry state, route planning, or any write path."""
from __future__ import annotations

import re

from commands.collab.engine.errors import die


PHASES = ['Audit', 'Discussion', 'Conclusion', 'Action Plan', 'Handoff', 'Completion']
CONTENT_ONLY_GUARD = '<!-- collab:content-only; do-not-execute -->'
SUMMARY_RE = re.compile(r'^<summary>(?P<role>[A-Za-z0-9_-]+)(?:\s+—\s+.+)?</summary>$')
LEGACY_EXPANDED_RE = re.compile(r'^\*\*(?P<role>[A-Za-z0-9_-]+)\s+—')
LEGACY_HEADING_RE = re.compile(r'^###\s+(?P<role>[A-Za-z0-9_-]+)\s+—')
DETAILS_OPEN_RE = re.compile(r'^<details(?:\s+[^>]*)?>(?:<summary>[^<]*</summary>)?$')
DETAILS_CLOSE_RE = re.compile(r'^</details>$')
ACTION_CHECKLIST_RE = re.compile(
    r'^\s*-\s+\[(?P<mark>[ xX])\]\s+\*\*(?P<role>[A-Za-z0-9_-]+):\*\*(?P<text>.*)$'
)
ACTION_PLAN_ITEM_TAG_RE = re.compile(r'^\s*(?P<tag>\[[a-z-]+\])(?:\s|$)')
ACTION_PLAN_ALLOWED_ITEM_TAG_LIST = [
    '[execute]',
    '[doc-fix]',
    '[verify]',
    '[precondition]',
    '[verify-precondition]',
    '[verify-objective]',
]
ACTION_PLAN_ALLOWED_ITEM_TAGS = set(ACTION_PLAN_ALLOWED_ITEM_TAG_LIST)
ACTION_PLAN_EXECUTE_TAG = '[execute]'
CHARTERED_DELIVERABLES_LABEL = 'charteredDeliverables:'
CHARTERED_DELIVERABLES_LABEL_NORMALIZED = re.sub(
    r'\s+', '', CHARTERED_DELIVERABLES_LABEL.rstrip(':')
).lower()


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
            line_index = index + 1
            while line_index < len(lines):
                nested = lines[line_index].strip()
                if DETAILS_OPEN_RE.match(nested):
                    depth += 1
                elif DETAILS_CLOSE_RE.match(nested):
                    depth -= 1
                    if depth == 0:
                        end = line_index + 1
                        break
                line_index += 1
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


def action_plan_item_tag(text: str) -> str | None:
    match = ACTION_PLAN_ITEM_TAG_RE.match(text)
    if not match:
        return None
    tag = match.group('tag')
    if tag not in ACTION_PLAN_ALLOWED_ITEM_TAGS:
        return None
    return tag


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
        text = match.group('text').strip()
        items.append({
            'number': item_number,
            'role': match.group('role'),
            'checked': mark == 'x',
            'tag': action_plan_item_tag(text),
            'text': text,
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


def unchecked_assigned_item_count(transcript: str, role: str) -> int:
    return unchecked_assigned_items_by_role(transcript).get(role, 0)


def is_chartered_deliverables_label(stripped: str) -> bool:
    if not stripped:
        return False
    candidate = stripped
    for _ in range(4):
        changed = False
        match = re.match(r'^([*_`]{1,2})(.+?)\1$', candidate)
        if match:
            candidate = match.group(2).strip()
            changed = True
        if candidate.endswith(':'):
            candidate = candidate[:-1].strip()
            changed = True
        if not changed:
            break
    compact = re.sub(r'\s+', '', candidate).lower()
    return compact == CHARTERED_DELIVERABLES_LABEL_NORMALIZED


def chartered_deliverables(transcript: str) -> list[str]:
    try:
        audit_lines = phase_section(transcript, 'Audit')
    except SystemExit:
        return []
    deliverables: list[str] = []
    in_block = False
    in_code = False
    details_depth = 0
    for raw_line in audit_lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        if DETAILS_OPEN_RE.match(stripped):
            details_depth += 1
            continue
        if DETAILS_CLOSE_RE.match(stripped):
            details_depth = max(0, details_depth - 1)
            continue
        if details_depth > 1:
            continue
        if not in_block:
            if is_chartered_deliverables_label(stripped):
                in_block = True
            continue
        if not stripped:
            if not deliverables:
                continue
            break
        if not stripped.startswith('- '):
            break
        deliverable = stripped[2:].strip()
        if deliverable:
            deliverables.append(deliverable)
    return deliverables
