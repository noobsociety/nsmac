#!/usr/bin/env python3
"""Thin CLI facade for the collab registry helper.

Domain implementation lives in ``registry_core``.  This file stays limited to
the executable entrypoint and lazy compatibility exports for tests/importers.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commands.collab.engine import registry_core as _registry_core
from commands.collab.engine.registry_core import main


def __getattr__(name: str) -> object:
    try:
        return getattr(_registry_core, name)
    except AttributeError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
