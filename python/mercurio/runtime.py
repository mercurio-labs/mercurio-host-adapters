from __future__ import annotations

from .backend import Mercurio
from .models import AnalysisCaseInfo, JsonObject, PartRef, SimulationTrace
from .project import MercurioProject


class RawWorkspace:
    """Escape hatch: direct access to the raw KIR-shaped HTTP responses."""

    def __init__(self, project: MercurioProject) -> None:
        self._project = project

    def graph(self, scope: str | None = None) -> JsonObject:
        return self._project.graph(scope=scope)

    def model(self) -> JsonObject:
        return self._project.model()

    def element(self, element_id: str) -> JsonObject:
        return self._project.element(element_id)


class NativeRawWorkspace:
    """Escape hatch for the in-process native workspace."""

    def __init__(self, workspace) -> None:
        self._workspace = workspace

    def model(self):
        return self._workspace.model()

    def element(self, element_id: str):
        return self._workspace.element(element_id)


class Model:
    """
    Single entry point for model inspection and simulation.

    Created by mercurio.open(path). Manages the backend process lifetime; use as
    a context manager or call close() explicitly.

        with mercurio.open(".") as model:
            trace = model.run_analysis("PrintSequence")
    """

    def __init__(self, backend: Mercurio, project: MercurioProject):
        self._backend = backend
        self._project = project
        self._workspace = None
        self.raw = RawWorkspace(project)

    @classmethod
    def from_native(cls, workspace) -> "Model":
        model = cls.__new__(cls)
        model._backend = None
        model._project = None
        model._workspace = workspace
        model.raw = NativeRawWorkspace(workspace)
        return model

    def parts(self) -> list[PartRef]:
        if self._workspace is not None:
            return self._workspace.parts()
        return self._project.parts()

    def part(self, name_or_id: str) -> PartRef:
        """Find a part by declared name or element id. Raises KeyError if not found."""
        for p in self.parts():
            if p.name == name_or_id or p.id == name_or_id:
                return p
        raise KeyError(f"No part with name or id {name_or_id!r}")

    def analysis_cases(self) -> list[AnalysisCaseInfo]:
        if self._workspace is not None:
            return self._workspace.list_analysis_cases()
        return self._project.list_analysis_cases()

    def run_analysis(self, case_id: str) -> SimulationTrace:
        if self._workspace is not None:
            return self._workspace.run_analysis(case_id)
        return self._project.run_analysis(case_id)

    def close(self) -> None:
        if self._workspace is not None:
            return
        self._project.close()
        self._backend.close()

    def __enter__(self) -> "Model":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


ModelRuntime = Model
