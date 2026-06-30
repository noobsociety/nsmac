#!/usr/bin/env python3
"""Argparse parser introspection: extracts the subcommand map from a parser and projects per-action display-name and value-shape descriptors used when rendering the registry CLI doc; does not own parser construction or CLI-doc orchestration."""
from __future__ import annotations

import argparse


def parser_subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def action_display_name(action: argparse.Action) -> str:
    if action.option_strings:
        return ', '.join(action.option_strings)
    return action.dest


def action_value_shape(action: argparse.Action) -> str:
    if action.option_strings:
        if action.nargs == 0:
            return 'flag'
        return 'value'
    if action.nargs in (None, 1):
        return 'required'
    return f'nargs={action.nargs}'
