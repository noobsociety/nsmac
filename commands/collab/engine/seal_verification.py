"""Compatibility exports for collab seal and verification helpers.

The implementation is split between seal_verification_logic.py and
seal_verification_render.py. Existing engine leaves import this facade while
registry_core.py imports the split modules directly for CLI dispatch and wrapper
configuration.
"""
from __future__ import annotations

from commands.collab.engine.seal_verification_logic import *  # noqa: F401,F403
from commands.collab.engine.seal_verification_render import *  # noqa: F401,F403
