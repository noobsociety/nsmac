#!/usr/bin/env python3
"""Content-file readers: load a required speak content file (rejecting missing or blank files) and optionally load a full-body file, returning trailing-newline-trimmed text; does not own speak-command orchestration, registry persistence, or rendering."""
from __future__ import annotations

from pathlib import Path

from commands.collab.engine.errors import die


def read_content_file(path: Path) -> str:
    if not path.exists():
        die(f'content file missing: {path}')
    content = path.read_text()
    if not content.strip():
        die('content must be non-empty')
    return content.rstrip('\n')


def read_optional_content_file(path: Path | None) -> str | None:
    if path is None:
        return None
    return read_content_file(path)
