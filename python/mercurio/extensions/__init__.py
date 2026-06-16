"""Mercurio Lab extension system.

Extensions are separately pip-installable packages that register analysis
bridges (``mercurio.bridges`` entry point group) and output renderers
(``mercurio.renderers`` entry point group).  No Mercurio core changes are
needed to add a new extension.

Usage::

    bridge = mercurio.extensions.get_bridge("pacti")
    results = bridge.run(model)
"""

from .base import AnalysisBridge, ExtensionNotInstalledError, OutputRenderer
from .registry import get_bridge, get_renderer, load_bridges, load_renderers

__all__ = [
    "AnalysisBridge",
    "ExtensionNotInstalledError",
    "OutputRenderer",
    "get_bridge",
    "get_renderer",
    "load_bridges",
    "load_renderers",
]
