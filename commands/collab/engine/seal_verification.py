"""Compatibility facade for external seal/verification imports.

Engine modules import ``seal_verification_logic`` or ``seal_verification_render``
directly. This module remains for tests and out-of-tree callers that still
import stable helper names from ``commands.collab.engine.seal_verification``.
"""
from __future__ import annotations

from commands.collab.engine import seal_verification_logic as _logic
from commands.collab.engine import seal_verification_render as _render

_exported: set[str] = set()
for _module in (_logic, _render):
    for _name in getattr(_module, '__all__', ()):
        globals()[_name] = getattr(_module, _name)
        _exported.add(_name)

if not _exported:
    for _module in (_logic, _render):
        for _name in dir(_module):
            if _name.startswith('_'):
                continue
            _value = getattr(_module, _name)
            if getattr(_value, '__module__', None) != _module.__name__ and not _name.isupper():
                continue
            globals()[_name] = _value
            _exported.add(_name)

__all__ = sorted(_exported)
