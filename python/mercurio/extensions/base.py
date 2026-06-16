"""Abstract base classes for Mercurio Lab extensions."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExtensionNotInstalledError(ImportError):
    """Raised when a bridge or renderer is requested but not installed."""


class AnalysisBridge(ABC):
    """Convert Mercurio model elements to/from an external analysis tool."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier used with mercurio.extensions.get_bridge(name)."""
        ...

    @abstractmethod
    def run(self, model: Any) -> dict[str, Any]:
        """Run the analysis on *model* and return a result dict."""
        ...


class OutputRenderer(ABC):
    """Describe how the Lab UI should render a custom output type."""

    @property
    @abstractmethod
    def output_type(self) -> str:
        """Namespaced output type string, e.g. 'mercurio/pacti-pareto'."""
        ...

    @abstractmethod
    def render_spec(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return a chart spec the OutputShelf can render.

        Supported spec *type* values: histogram, scatter, table,
        trace_overlay, html.
        """
        ...
