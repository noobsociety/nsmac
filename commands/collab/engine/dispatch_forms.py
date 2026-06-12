"""Render user-facing command dispatch notation."""
from __future__ import annotations


def command_dispatch(namespace: str, route: str = "", *args: object) -> str:
    tokens: list[str] = [namespace]
    if route:
        tokens.extend(route.split())
    tokens.extend(str(arg) for arg in args if arg is not None and str(arg) != "")
    return f'({" ".join(tokens)})'


def collab_dispatch(route: str = "", *args: object) -> str:
    return command_dispatch("collab", route, *args)
