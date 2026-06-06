from __future__ import annotations

from .backend import Mercurio
from .models import AnalysisCaseInfo, JsonObject, PartRef, SimulationTrace
from .workspace import MercurioWorkspace


class ModelRuntime:
    """
    Single entry point for model inspection and simulation.

    Created by mercurio.open(path). Manages the backend process lifetime; use as
    a context manager or call close() explicitly.
    """

    def __init__(self, backend: Mercurio, workspace: MercurioWorkspace):
        self._backend = backend
        self._workspace = workspace

    @property
    def workspace(self) -> MercurioWorkspace:
        return self._workspace

    def parts(self) -> list[PartRef]:
        return self._workspace.parts()

    def element(self, element_id: str) -> JsonObject:
        return self._workspace.element(element_id)

    def graph(self) -> JsonObject:
        return self._workspace.graph()

    def analysis_cases(self) -> list[AnalysisCaseInfo]:
        return self._workspace.list_analysis_cases()

    def run_analysis(self, case_id: str) -> SimulationTrace:
        return self._workspace.run_analysis(case_id)

    def close(self) -> None:
        self._workspace.close()
        self._backend.close()

    def __enter__(self) -> "ModelRuntime":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
