from __future__ import annotations

from .backend import Mercurio
from .models import AnalysisCaseInfo, JsonObject, PartRef, SimulationTrace
from .workspace import MercurioWorkspace


class RawWorkspace:
    """Escape hatch: direct access to the raw KIR-shaped HTTP responses."""

    def __init__(self, workspace: MercurioWorkspace) -> None:
        self._workspace = workspace

    def graph(self, scope: str | None = None) -> JsonObject:
        return self._workspace.graph(scope=scope)

    def model(self) -> JsonObject:
        return self._workspace.model()

    def element(self, element_id: str) -> JsonObject:
        return self._workspace.element(element_id)


class Model:
    """
    Single entry point for model inspection and simulation.

    Created by mercurio.open(path). Manages the backend process lifetime; use as
    a context manager or call close() explicitly.

        with mercurio.open(".") as model:
            trace = model.run_analysis("PrintSequence")
    """

    def __init__(self, backend: Mercurio, workspace: MercurioWorkspace):
        self._backend = backend
        self._workspace = workspace
        self.raw = RawWorkspace(workspace)

    def parts(self) -> list[PartRef]:
        return self._workspace.parts()

    def part(self, name_or_id: str) -> PartRef:
        """Find a part by declared name or element id. Raises KeyError if not found."""
        for p in self.parts():
            if p.name == name_or_id or p.id == name_or_id:
                return p
        raise KeyError(f"No part with name or id {name_or_id!r}")

    def analysis_cases(self) -> list[AnalysisCaseInfo]:
        return self._workspace.list_analysis_cases()

    def run_analysis(self, case_id: str) -> SimulationTrace:
        return self._workspace.run_analysis(case_id)

    def close(self) -> None:
        self._workspace.close()
        self._backend.close()

    def __enter__(self) -> "Model":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


ModelRuntime = Model
