#!/usr/bin/env python3
"""Flag-taxonomy spec reader: parse the flag-taxonomy reference markdown (per-command `### ` headings and pipe-delimited flag rows) and project it into a class-grouped inventory (advisory / helper-enforced / generator-derived), rejecting unknown flag classes; owns the sole-use flag-row pattern and aggregates lower-tier leaves (config_paths, errors). Does not own registry persistence, phase mutation, or any write path."""
from __future__ import annotations

import re
from pathlib import Path

from commands.collab.engine.config_paths import DEFAULT_FLAG_TAXONOMY_PATH
from commands.collab.engine.errors import die

FLAG_ROW_RE = re.compile(r'^\|\s*`(?P<flag>[^`]+)`\s*\|\s*`(?P<class>[^`]+)`\s*\|\s*(?P<notes>.*?)\s*\|$')


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
