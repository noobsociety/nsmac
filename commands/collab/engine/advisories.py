#!/usr/bin/env python3
"""Post-action and recovery advisory rendering: builds the post-speak/seal advisory line set and the forced active-phase recovery-advisory string; does not own registry persistence, phase mutation, or transcript reading."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def resolve_config_root() -> Path:
    configured = os.environ.get('COMMAND_CONFIG_ROOT')
    if configured:
        return Path(configured).expanduser().resolve()
    if (ROOT / 'commands').is_dir():
        return ROOT
    return ROOT


DEFAULT_CONFIG_ROOT = resolve_config_root()
DEFAULT_EFFORT_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/agent-effort.json'

from commands.collab.engine.command_lines import resume_command
from commands.collab.engine.transcript_readers import (
    action_plan_label_summary,
    contribution_roles,
    tombstone_count,
)
from commands.collab.engine.effort import effort_line, load_effort_defaults
from commands.collab.engine.phase_lifecycle import efficiency_line_from_notice


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
