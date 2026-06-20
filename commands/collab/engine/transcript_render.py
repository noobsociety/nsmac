"""Managed rendering engine for collab transcripts.

Owns: header scaffolding, Table of Contents management (including
      insert_toc_entry), participant table rendering, all <details> block
      construction via rendered_collapsible_block (single <details> owner;
      registry.py routes its participant-verify, reviewer-findings,
      revision-history, and retracted-content blocks here), contribution-block
      rendering (excerpt and full body handling), and effort-override banners.

Does not own: registry state, phase lifecycle decisions, participant roster
              management, write-path dispatch, or CLI entry-point logic.
              This module is imported by commands.collab.engine.registry only.

Naming convention
  rendered_*  -- pure function; produces a single self-contained rendered
                 artifact (string or line-list) representing one named thing;
                 no I/O or side effects.
  render_*    -- assembles, transforms, or drives a larger rendering operation;
                 may return complex types or a complete document; may be pure
                 but its scope is broader than a single named artifact.

Split boundary (if this module is later divided into header_render.py and
contribution_render.py):
  header_render.py       -- owns header scaffolding, TOC management, and
                            insert_toc_entry (single owner; the contribution
                            module imports it, never copy-owns it).
  contribution_render.py -- owns contribution/collapsible-block rendering,
                            excerpt/full-body handling, and effort-override
                            banners.
"""
from __future__ import annotations

import re
import sys
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMMAND_SYSTEM_DIR = ROOT / 'platform' / 'tooling'
if str(COMMAND_SYSTEM_DIR) not in sys.path:
    sys.path.insert(0, str(COMMAND_SYSTEM_DIR))

from roles import load_projector, load_role, participant_row, projectors_dir_for_roles  # noqa: E402

from commands.collab.engine.dispatch_forms import collab_dispatch  # noqa: E402
from commands.collab.engine.errors import die  # noqa: E402
from commands.collab.engine.handoff_shape import render_content_for_transcript, validate_handoff_state  # noqa: E402
from commands.collab.engine.normalizers import format_banner_timestamp, phase_slug  # noqa: E402
from commands.collab.engine.participants import (  # noqa: E402
    effective_turn_order,
    reviewer_backed,
    reviewer_mode,
    reviewer_optional_phases,
    reviewer_role,
    reviewer_state,
)
from commands.collab.engine.registry_constants import (  # noqa: E402
    ALLOWED_COMPLETION_SUBSTATES,
    ALLOWED_VERIFICATION_SUBSTATES,
    CONTENT_ONLY_GUARD,
    FULL_BODY_SUMMARY,
    HEADER_MANAGED_BEGIN,
    HEADER_MANAGED_END,
    PHASES,
)
from commands.collab.engine.transcript_readers import (  # noqa: E402
    DETAILS_CLOSE_RE,
    DETAILS_OPEN_RE,
    summary_role,
)

ANCHOR_RE = re.compile(r'^<a name="(?P<anchor>[A-Za-z0-9_-]+)"></a>$')
DETAILS_CONTROL_LINE_RE = re.compile(r'^</?details(?:\s+[^>]*)?\s*>$')
PROHIBITION_SEPARATOR = ' \u00b7 '
AUTHOR_DECLARED_STANCES = {'converges', 'dissents', 'qualifies'}
MISSING_STANCE = 'missing-stance'
DEFAULT_ROLES_DIR = ROOT / 'commands/collab/reference/roles'
STANCE_DECLARATION_RE = re.compile(r'^\s*STANCE:\s*(converges|dissents|qualifies)\s*$', re.IGNORECASE)
TIMESTAMP_WRAPPER_RE = re.compile(r'^\s*<p><em>.*</em></p>\s*$')
CONTENT_ONLY_GUARD_RE = re.compile(r'^\s*<!--\s*collab:content-only;\s*do-not-execute\s*-->\s*$')
EFFORT_OVERRIDE_LINE_RE = re.compile(r'^\s*EFFORT OVERRIDE:\s*.+$', re.IGNORECASE)
EFFORT_OVERRIDE_COMMENT_RE = re.compile(
    r'^\s*<!--\s*collab:effort-override b64:[A-Za-z0-9_-]+={0,2}\s*-->\s*$'
)
STANCE_COMMENT_RE = re.compile(r'^\s*<!--\s*collab:stance\s+(?:converges|dissents|qualifies)\s*-->\s*$', re.IGNORECASE)
DIRECTIVE_DECLARATION_RE = re.compile(r'^\s*\*\*Directive:\*\*\s+"[^"]+"\s*$', re.IGNORECASE)
DIRECTIVE_ACTION_PLAN_RE = re.compile(
    r'^\s*\*\*Action Plan:\s*(?:satisfies|partially satisfies|defers)\*\*.*$',
    re.IGNORECASE,
)
DIRECTIVE_GAP_COMMENT_RE = re.compile(r'^\s*<!--\s*collab:directive-gap\b.*-->\s*$', re.IGNORECASE)
INLINE_TIMESTAMP_WRAPPER_RE = re.compile(r'\s*(?:<p><em>.*?</em></p>|&lt;p&gt;&lt;em&gt;.*?&lt;/em&gt;&lt;/p&gt;)\s*')
INLINE_CONTENT_ONLY_GUARD_RE = re.compile(
    r'\s*(?:<!--\s*collab:content-only;\s*do-not-execute\s*-->|'
    r'&lt;!--\s*collab:content-only;\s*do-not-execute\s*--&gt;)\s*',
    re.IGNORECASE,
)


def declared_stance_for_content(content: str) -> str | None:
    for line in content.splitlines():
        match = STANCE_DECLARATION_RE.match(line)
        if match:
            return match.group(1).lower()
    return None


def stance_for_content(content: str) -> str:
    return declared_stance_for_content(content) or MISSING_STANCE


def is_scaffold_line(line: str) -> bool:
    stripped = line.strip()
    normalized = html.unescape(stripped)
    return any(
        pattern.match(normalized)
        for pattern in (
            TIMESTAMP_WRAPPER_RE,
            CONTENT_ONLY_GUARD_RE,
            EFFORT_OVERRIDE_COMMENT_RE,
        )
    )


def is_hidden_metadata_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    normalized = html.unescape(stripped)
    return is_scaffold_line(stripped) or any(
        pattern.match(normalized)
        for pattern in (
            STANCE_DECLARATION_RE,
            STANCE_COMMENT_RE,
            EFFORT_OVERRIDE_LINE_RE,
            DIRECTIVE_DECLARATION_RE,
            DIRECTIVE_ACTION_PLAN_RE,
            DIRECTIVE_GAP_COMMENT_RE,
        )
    )


def excerpt_source(value: str) -> str:
    cleaned = INLINE_TIMESTAMP_WRAPPER_RE.sub('\n', value)
    cleaned = INLINE_CONTENT_ONLY_GUARD_RE.sub('\n', cleaned)
    lines = [
        line
        for line in cleaned.splitlines()
        if not is_scaffold_line(line)
    ]
    index = 0
    while index < len(lines) and is_hidden_metadata_line(lines[index]):
        index += 1
    return '\n'.join(lines[index:]).strip()


def load_participant_metadata(roles_dir: Path, role: str) -> dict:
    try:
        return load_role(roles_dir, role)
    except SystemExit as exc:
        try:
            return load_projector(projectors_dir_for_roles(roles_dir), role)
        except SystemExit:
            raise exc


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


def reject_hand_authored_excerpt_details(content: str) -> None:
    for line_number, line in enumerate(content.splitlines(), start=1):
        if DETAILS_CONTROL_LINE_RE.match(line.strip()):
            die(
                'excerpt must not contain hand-authored <details> blocks; '
                f'use --full-body-file for {FULL_BODY_SUMMARY}; line {line_number}'
            )


def reject_full_body_details_controls(content: str | None) -> None:
    if content is None:
        return
    for line_number, line in enumerate(content.splitlines(), start=1):
        if DETAILS_CONTROL_LINE_RE.match(line.strip()):
            die(
                'full body must not contain hand-authored <details> control lines; '
                f'the helper owns the {FULL_BODY_SUMMARY} envelope; line {line_number}'
            )


def render_full_body_block(full_body: str) -> list[str]:
    return rendered_collapsible_block(None, FULL_BODY_SUMMARY, full_body.rstrip('\n').splitlines())


def rendered_collapsible_block(
    anchor: str | None,
    summary: str,
    body_lines: list[str],
    timestamp: str | None = None,
    content_guard: bool = False,
    inline_summary: bool = False,
) -> list[str]:
    if inline_summary:
        lines = [f'<details><summary>{summary}</summary>']
    else:
        lines = ['<details>', f'<summary>{summary}</summary>']
    if anchor is not None:
        lines = [f'<a name="{anchor}"></a>', *lines]
    if timestamp is not None:
        lines.append(f'<p><em>{timestamp}</em></p>')
    if content_guard:
        lines.append(CONTENT_ONLY_GUARD)
    lines.extend(['', *body_lines, '', '</details>'])
    return lines


def render_contribution_body(content: str, full_body: str | None = None) -> list[str]:
    rendered = render_content_for_transcript(content)
    if full_body is not None:
        rendered.extend(['', *render_full_body_block(full_body)])
    return rendered


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
        line_index = index + 1
        while line_index < end:
            stripped = rendered[line_index].strip()
            if DETAILS_OPEN_RE.match(stripped):
                depth += 1
            elif DETAILS_CLOSE_RE.match(stripped):
                depth -= 1
                if depth == 0:
                    block_end = line_index + 1
                    break
            line_index += 1
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


def render_contribution_block(
    phase: str,
    role: str,
    counter: int,
    content: str,
    timestamp: str,
    full_body: str | None = None,
) -> tuple[str, list[str]]:
    anchor = f'{phase_slug(phase)}-{role}-{counter}'
    return anchor, rendered_collapsible_block(
        anchor,
        role,
        render_contribution_body(content, full_body),
        timestamp=timestamp,
        content_guard=True,
    )


def revision_history_start(block: list[str], content_start: int) -> int | None:
    depth = 0
    for index in range(content_start, len(block) - 1):
        stripped = block[index].strip()
        if stripped == '<details><summary>Revision history</summary>':
            return index
        if DETAILS_OPEN_RE.match(stripped):
            if (
                depth == 0
                and index + 1 < len(block)
                and block[index + 1].strip() == '<summary>Revision history</summary>'
            ):
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
    if not existing:
        return rendered_collapsible_block(None, 'Revision history', revision, inline_summary=True)
    insert_at = 1
    if len(existing) > 1 and existing[1] == '':
        insert_at = 2
    return existing[:insert_at] + revision + existing[insert_at:]


def rendered_retracted_content_block(existing_body: str) -> list[str]:
    return rendered_collapsible_block(
        None,
        'Retracted content',
        existing_body.splitlines(),
        inline_summary=True,
    )


def rendered_status_table(entry: dict) -> str:
    reviewer = reviewer_role(entry) or '\u2014'
    turn_order_values = effective_turn_order(entry)
    turn_order = ', '.join(turn_order_values) if turn_order_values else '\u2014'
    active_phase = entry['activePhase']
    if active_phase == 'Completion' and reviewer_backed(entry):
        completion = entry.get('completion')
        if isinstance(completion, dict) and completion.get('subState') in ALLOWED_COMPLETION_SUBSTATES:
            active_phase = f"Completion.{completion['subState']}"
            if completion['subState'] == 'verification':
                verification = entry.get('verification')
                if isinstance(verification, dict) and verification.get('subState') in ALLOWED_VERIFICATION_SUBSTATES:
                    active_phase = f"{active_phase}.{verification['subState']}"
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
        rows.append(participant_row(load_participant_metadata(roles_dir, p['role']), index, p['agentId']))
    return '\n'.join(rows)


def rendered_prohibitions_block(entry: dict, roles_dir: Path) -> str | None:
    rows = [
        '| Role | Constraints |',
        '|------|-------------|',
    ]
    for participant in entry['participants']:
        role_data = load_participant_metadata(roles_dir, participant['role'])
        prohibitions = role_data.get('prohibitions') or []
        if not prohibitions:
            continue
        rows.append(f"| {role_data['key']} | {PROHIBITION_SEPARATOR.join(prohibitions)} |")
    if len(rows) == 2:
        return None
    return '\n'.join([
        '**Prohibitions**',
        '',
        '_principle-level behavioral constraints; not a runtime enforcement list_',
        '',
        *rows,
    ])


def rendered_reviewer_section(entry: dict, roles_dir: Path) -> str | None:
    state = reviewer_state(entry)
    if state['state'] == 'absent':
        return '\u2014'
    reviewer = state['reviewerRole']
    mode = reviewer_mode(entry)
    optional = ', '.join(reviewer_optional_phases(entry)) or '\u2014'
    if state['state'] == 'active':
        return (
            f'**{reviewer}** \u2014 registered in **Participants** and active as the '
            f'convergent-phase reviewer per the user-scope collab state root `registry.json` '
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
        f'`{reviewer}` is assigned as reviewer but has not yet joined. Run `{collab_dispatch("join", "--role", reviewer)}` before any participant may contribute.',
    ])


def header_timestamp_from_lines(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('_') and stripped.endswith('_') and len(stripped) > 2:
            return stripped.strip('_')
    return format_banner_timestamp()


def anchor_role_for_toc(lines: list[str], anchor_index: int, anchor: str) -> str:
    for line_index in range(anchor_index + 1, min(len(lines), anchor_index + 8)):
        if lines[line_index].startswith('## ') or ANCHOR_RE.match(lines[line_index].strip()):
            break
        role = summary_role(lines[line_index])
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
        'Registry-backed collab state is authoritative. Metadata below mirrors `$HOME/.collabs/<projectId>/registry.json` for human orientation only.',
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
        f'Agents must wait for the moderator to call `{collab_dispatch("speak")}` before contributing.',
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
        'Registry-backed collab state is authoritative. Metadata below mirrors `$HOME/.collabs/<projectId>/registry.json` for human orientation only.',
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
        f'Agents must wait for the moderator to call `{collab_dispatch("speak")}` before contributing.',
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
