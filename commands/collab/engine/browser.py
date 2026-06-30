#!/usr/bin/env python3
"""Browser launch: open a URI in the system browser via an injectable opener, capturing any failure (raised exception or a falsey "no browser" return) as a human-readable string rather than propagating it — a standalone leaf with no engine dependencies. Does not own URI construction, registry persistence, or any write path."""
from __future__ import annotations

import webbrowser
from typing import Callable


def open_browser_uri(uri: str, opener: Callable[[str], bool] = webbrowser.open_new_tab) -> str | None:
    try:
        opened = opener(uri)
    except Exception as exc:
        return f'{type(exc).__name__}: {exc}'
    if not opened:
        return 'no browser available'
    return None
