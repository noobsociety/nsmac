"""Effort advisory calculation and projection-drift checks."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from commands.collab.engine.errors import die
from commands.collab.engine.registry_constants import DEFAULT_OPEN_ROSTER_EFFORT

EFFORT_MODEL_MARKER = 'generated; do not edit'

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
        # Explicit-values exemption: open-roster effort is matrix-resolved advisory state, not registry record state.
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

def normalize_rendered_effort_cell(value: str) -> str | None:
    cleaned = re.sub(r'<[^>]+>', '', value).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if cleaned in {'', '-', '\u2014'} or cleaned.startswith('\u2014 '):
        return None
    match = re.match(r'`?([A-Za-z][A-Za-z0-9_-]*)`?', cleaned)
    if not match:
        return cleaned
    return match.group(1)

def parse_markdown_table(lines: list[str], start_index: int) -> tuple[list[str], list[dict[str, str]], int]:
    headers = [cell.strip() for cell in lines[start_index].strip().strip('|').split('|')]
    separator_index = start_index + 1
    if separator_index >= len(lines) or not re.match(
        r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$',
        lines[separator_index],
    ):
        die(f'effort matrix rendered table missing separator after line {start_index + 1}')
    rows: list[dict[str, str]] = []
    index = separator_index + 1
    while index < len(lines) and lines[index].lstrip().startswith('|'):
        cells = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
        if len(cells) != len(headers):
            die(f'effort matrix rendered table malformed at line {index + 1}')
        rows.append(dict(zip(headers, cells)))
        index += 1
    return headers, rows, index

def parse_agent_model_effort_table(model_path: Path) -> tuple[list[str], dict[str, dict[str, str]], bool]:
    if not model_path.exists():
        die(f'effort model projection missing: {model_path}')
    lines = model_path.read_text().splitlines()
    heading_index = None
    for index, line in enumerate(lines):
        if line.strip() == '## Per-speak-turn effort':
            heading_index = index
            break
    if heading_index is None:
        die('effort matrix rendered table missing heading: ## Per-speak-turn effort')

    table_index = None
    marker_found = False
    for index in range(heading_index + 1, len(lines)):
        stripped = lines[index].strip()
        if table_index is None and EFFORT_MODEL_MARKER in stripped.lower():
            marker_found = True
        if stripped.startswith('|'):
            table_index = index
            break
    if table_index is None:
        die('effort matrix rendered table missing after heading: ## Per-speak-turn effort')

    headers, rows, _ = parse_markdown_table(lines, table_index)
    if not headers or headers[0] != 'Phase':
        die('effort matrix rendered table first column must be Phase')
    roles = headers[1:]
    by_phase: dict[str, dict[str, str]] = {}
    for row in rows:
        phase = row.get('Phase', '').strip()
        if not phase:
            die('effort matrix rendered table contains row with blank Phase')
        if phase in by_phase:
            die(f'effort matrix rendered table duplicate phase/row: {phase}')
        by_phase[phase] = {role: row.get(role, '') for role in roles}
    return roles, by_phase, marker_found

def rendered_effort_drift_items(defaults: dict, model_path: Path) -> list[str]:
    roles, rendered_by_phase, marker_found = parse_agent_model_effort_table(model_path)
    matrix = defaults['matrix']
    failures: list[str] = []
    if not marker_found:
        failures.append(
            f'header-missing: expected "{EFFORT_MODEL_MARKER}" before rendered effort table in {model_path}'
        )

    expected_roles: list[str] = []
    for phase_defaults in matrix.values():
        for role in phase_defaults:
            if role not in expected_roles:
                expected_roles.append(role)
    for role in expected_roles:
        if role not in roles:
            failures.append(
                f'role {role}, phase/row <header>: JSON value present, rendered value missing-column'
            )

    for phase, phase_defaults in matrix.items():
        rendered_row = rendered_by_phase.get(phase)
        if rendered_row is None:
            failures.append(
                'role <all>, phase/row '
                f'{phase}: JSON value {json.dumps(phase_defaults, sort_keys=True)}, rendered value missing-row'
            )
            continue
        for role, json_value in phase_defaults.items():
            rendered_raw = rendered_row.get(role)
            if rendered_raw is None:
                failures.append(
                    f'role {role}, phase/row {phase}: JSON value {json_value}, rendered value missing-column'
                )
                continue
            rendered_value = normalize_rendered_effort_cell(rendered_raw)
            if rendered_value != json_value:
                failures.append(
                    f'role {role}, phase/row {phase}: JSON value {json_value}, '
                    f'rendered value {rendered_raw or "<blank>"}'
                )

    for phase in rendered_by_phase:
        if phase not in matrix:
            failures.append(
                f'role <all>, phase/row {phase}: JSON value missing-row, rendered value present'
            )
    return failures

def audit_effort_matrix(effort_defaults_path: Path, model_path: Path) -> int:
    defaults = load_effort_defaults(effort_defaults_path)
    failures = rendered_effort_drift_items(defaults, model_path)
    if failures:
        for failure in failures:
            print(f'effort matrix drift: {failure}', file=sys.stderr)
        return 1
    print('OK: agent-model.md effort projection matches agent-effort.json')
    return 0
