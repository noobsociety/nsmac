#!/usr/bin/env python3
"""Init-command input reader: parse the raw `init` argv token stream into a validated tuple (title, agent id, reviewer role, open-requested, participant-verification, terminal, work-repo), rejecting duplicate/unknown flags and missing flag values — the read-only token-parsing counterpart for the init command; does not own init-command orchestration, registry persistence, phase mutation, or any write path."""
from __future__ import annotations

import re

from commands.collab.engine.errors import die
from commands.collab.engine.normalizers import normalize_join_agent_id, normalize_title
from commands.collab.engine.registry_constants import (
    ALLOWED_TERMINALS,
    DEFAULT_TERMINAL,
    TERMINAL_CHOICES_MESSAGE,
)

ROLE_KEY_RE = re.compile(r'^\w+$')


def parse_init_tokens(tokens: list[str]) -> tuple[str, str, str | None, bool, bool, str, str | None]:
    name_tokens: list[str] = []
    agent_id: str | None = None
    reviewer: str | None = None
    work_repo: str | None = None
    terminal = DEFAULT_TERMINAL
    terminal_seen = False
    open_requested = False
    participant_verification = True
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == '--agent-id':
            if agent_id is not None:
                die('duplicate flag: --agent-id')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('agent-id is required')
            agent_id = tokens[index]
        elif token == '--reviewer':
            if reviewer is not None:
                die('duplicate flag: --reviewer')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('--reviewer requires a role key')
            reviewer = tokens[index]
            if not ROLE_KEY_RE.match(reviewer):
                die('--reviewer requires a role key')
        elif token == '--terminal':
            if terminal_seen:
                die('duplicate flag: --terminal')
            terminal_seen = True
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die(f'--terminal requires one of: {TERMINAL_CHOICES_MESSAGE}')
            terminal = tokens[index]
            if terminal not in ALLOWED_TERMINALS:
                die(f'--terminal requires one of: {TERMINAL_CHOICES_MESSAGE}')
        elif token == '--open':
            if open_requested:
                die('duplicate flag: --open')
            open_requested = True
        elif token == '--no-participant-verification':
            if not participant_verification:
                die('duplicate flag: --no-participant-verification')
            participant_verification = False
        elif token == '--work-repo':
            if work_repo is not None:
                die('duplicate flag: --work-repo')
            index += 1
            if index >= len(tokens) or tokens[index].startswith('--'):
                die('--work-repo requires a path')
            work_repo = tokens[index]
        elif token.startswith('--'):
            die(f'unknown flag: {token}')
        else:
            name_tokens.append(token)
        index += 1

    if len(name_tokens) > 1:
        die(f'unknown positional argument: {name_tokens[1]}')
    raw_title = ' '.join(name_tokens).strip()
    if not raw_title:
        die('<name> is required')
    title = normalize_title(raw_title)
    return title, normalize_join_agent_id(agent_id), reviewer, open_requested, participant_verification, terminal, work_repo
