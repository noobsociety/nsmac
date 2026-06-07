"""Shared collab exit helpers; does not import registry or own write paths."""
from __future__ import annotations

import json


def die(message: str) -> None:
    raise SystemExit(message)


def handoff_abort(field: str, value: object) -> None:
    if isinstance(value, str):
        rendered = value
    else:
        rendered = json.dumps(value, sort_keys=True)
    die(f'ABORT: {field} contains disallowed pattern: {rendered}')
