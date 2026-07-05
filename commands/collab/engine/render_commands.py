#!/usr/bin/env python3
"""Transcript render/view/summarize command handlers.

Owns the `render-status`, `render-participants`, `summarize`, and read-only
`transcript-view` command bodies. Registry/transcript commits stay owned by
`registry_io`.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

from commands.collab.engine.errors import die
from commands.collab.engine.inspection_commands import print_status_view
from commands.collab.engine.registry_constants import PHASES
from commands.collab.engine.registry_io import (
    commit_registry_and_transcript,
    load_registry,
    registry_lock,
    registry_revision,
    resolve_collab,
)
from commands.collab.engine.transcript_readers import (
    read_transcript_for_entry,
    section_bounds,
    transcript_path_for_entry,
)
from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    render_managed_header_text,
    replace_phase_summary,
)
from commands.collab.engine.config_paths import DEFAULT_ROLES_DIR


def summarize_collab(path: Path, target: str, date: str | None = None) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] == 'archived':
            die('record is archived')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, DEFAULT_ROLES_DIR)
        summary_date = date or dt.date.today().isoformat()
        rendered = replace_phase_summary(rendered, entry, summary_date)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print(transcript_path)
    return 0


def transcript_view(path: Path, target: str, phase: str, raw: bool = False) -> int:
    if phase not in PHASES:
        die(f'phase must be one of: {", ".join(PHASES)}')
    data = load_registry(path)
    entry = resolve_collab(data, target)
    transcript = read_transcript_for_entry(entry)
    lines = transcript.splitlines()
    start, end = section_bounds(lines, f'## {phase}')
    sys.stdout.write('\n'.join(lines[start:end]) + '\n')
    return 0


def render_status(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        rendered, _header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
        transcript = rendered
        revision = registry_revision(data)

    print_status_view(entry, transcript, revision)
    return 0


def render_participants(path: Path, target: str, roles_dir: Path) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, roles_dir)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered, roles_dir)
    print(transcript_path)
    return 0
