#!/usr/bin/env python3
"""Default configuration-path resolution: resolve the command config root (honoring the COMMAND_CONFIG_ROOT environment override) and derive the default roles directory, effort-defaults, agent-model, and flag-taxonomy paths — a standalone leaf with no engine dependencies that self-resolves the repository root; does not own the executable sys.path bootstrap or any config-file reading."""
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
DEFAULT_ROLES_DIR = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/roles'
DEFAULT_EFFORT_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/agent-effort.json'
DEFAULT_AGENT_MODEL_PATH = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/agent-model.md'
DEFAULT_FLAG_TAXONOMY_PATH = DEFAULT_CONFIG_ROOT / 'platform/standards/flag-taxonomy.md'
