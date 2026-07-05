#!/usr/bin/env python3
"""Help-route command: resolve a `(help <namespace> <route...>)` token list to its `commands/<namespace>/.../index.md` reference document under the repository root, reject malformed tokens and any path that escapes the commands tree, and print the document; aggregates lower-tier leaves (config_paths, errors). Does not own route dispatch, registry persistence, or any write path."""
from __future__ import annotations

import re

from commands.collab.engine.config_paths import ROOT
from commands.collab.engine.errors import die


def route_help_command(route_tokens: list[str]) -> int:
    if not route_tokens:
        die('<route> is required; e.g., (help collab init), (help collab run plan)')
    if any(not re.match(r'^[A-Za-z0-9_-]+$', token) for token in route_tokens):
        die(f'route not found: {" ".join(route_tokens)}; valid routes are listed in commands/commands.md')
    namespace = route_tokens[0]
    if len(route_tokens) == 1:
        route_path = ROOT / 'commands' / namespace / 'index.md'
    else:
        route_path = ROOT / 'commands' / namespace / '-'.join(route_tokens[1:]) / 'index.md'
    commands_root = (ROOT / 'commands').resolve()
    resolved = route_path.resolve()
    if commands_root not in resolved.parents:
        die(f'route not found: {" ".join(route_tokens)}; valid routes are listed in commands/commands.md')
    try:
        content = route_path.read_text()
    except OSError:
        die(f'route not found: {" ".join(route_tokens)}; valid routes are listed in commands/commands.md')
    print(content, end='')
    return 0
