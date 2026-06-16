"""Extension discovery via importlib entry points."""
from __future__ import annotations

from importlib.metadata import entry_points

from .base import AnalysisBridge, ExtensionNotInstalledError, OutputRenderer

_bridges: dict[str, AnalysisBridge] | None = None
_renderers: dict[str, OutputRenderer] | None = None


def load_bridges() -> dict[str, AnalysisBridge]:
    """Discover and instantiate all registered analysis bridges."""
    global _bridges
    eps = entry_points(group="mercurio.bridges")
    _bridges = {}
    for ep in eps:
        try:
            _bridges[ep.name] = ep.load()()
        except Exception:
            pass
    return dict(_bridges)


def load_renderers() -> dict[str, OutputRenderer]:
    """Discover and instantiate all registered output renderers."""
    global _renderers
    eps = entry_points(group="mercurio.renderers")
    _renderers = {}
    for ep in eps:
        try:
            _renderers[ep.name] = ep.load()()
        except Exception:
            pass
    return dict(_renderers)


def get_bridge(name: str) -> AnalysisBridge:
    """Return the named bridge, discovering extensions on first call."""
    global _bridges
    if _bridges is None:
        load_bridges()
    bridge = (_bridges or {}).get(name)
    if bridge is None:
        raise ExtensionNotInstalledError(
            f"No analysis bridge named {name!r} is installed. "
            f"Try: pip install mercurio-{name}"
        )
    return bridge


def get_renderer(name: str) -> OutputRenderer:
    """Return the named renderer, discovering extensions on first call."""
    global _renderers
    if _renderers is None:
        load_renderers()
    renderer = (_renderers or {}).get(name)
    if renderer is None:
        raise ExtensionNotInstalledError(
            f"No renderer named {name!r} is installed."
        )
    return renderer
