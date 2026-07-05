"""Render literal registry.py CLI invocation strings (RESUME / transcript-view) for users to run.

Distinct from dispatch_forms, which renders the routing-only ``(collab ...)`` hint
notation that must never be executed as a shell command. The builders here emit
runnable ``commands/collab/engine/registry.py <subcommand> ...`` command lines.
"""
from __future__ import annotations

import shlex


def resume_command_invocation(entry: dict, role: str) -> str:
    return f'commands/collab/engine/registry.py speak-state --resume {entry["id"]} {role}'


def resume_command(entry: dict, role: str) -> str:
    return f'RESUME: {resume_command_invocation(entry, role)}'


def transcript_view_command(entry: dict, phase: str | None = None, raw: bool = False) -> str:
    selected_phase = phase or entry['activePhase']
    command = f'commands/collab/engine/registry.py transcript-view {entry["id"]} {shlex.quote(selected_phase)}'
    if raw:
        command += ' --raw'
    return command


def transcript_view_command_for_role(entry: dict, role: str, phase: str | None = None) -> str:
    return transcript_view_command(entry, phase, raw=role != entry.get('moderatorRole'))
