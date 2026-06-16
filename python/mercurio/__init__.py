"""Public Python API for opening and inspecting Mercurio models."""

from .runtime import Model
from .session import (
    AnalysisQuery,
    CompiledModel,
    PartDefRef,
    PartUsageRef,
    ProjectSession,
    SemanticRef,
    SimulationConfiguration,
    SmallEdit,
    StaleSemanticRefError,
    TradeStudy,
    Variant,
    VariantBaseChangedError,
)

__all__ = [
    "AnalysisQuery",
    "CompiledModel",
    "Model",
    "PartDefRef",
    "PartUsageRef",
    "ProjectSession",
    "SemanticRef",
    "SimulationConfiguration",
    "SmallEdit",
    "StaleSemanticRefError",
    "TradeStudy",
    "Variant",
    "VariantBaseChangedError",
    "open",
    "open_project",
]

__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "ModelBuilder":
        from .authoring import ModelBuilder

        return ModelBuilder
    raise AttributeError(name)


def open(
    path: str,
    *,
    executable: str | None = None,
    timeout: float = 60.0,
) -> Model:
    """
    Open *path*, compile it, and return a typed model. Native in-process
    bindings are used when available; the HTTP sidecar remains as fallback.
    """
    try:
        from mercurio._core import PyWorkspace as _Workspace
    except ImportError:
        _Workspace = None
    except AttributeError:
        _Workspace = None

    if _Workspace is not None and executable is None:
        return Model.from_native(_Workspace.open(path))

    from .backend import Mercurio

    backend = Mercurio.launch(executable=executable, timeout=timeout)
    try:
        project = backend.open_project(path, mode="compiled")
    except Exception:
        backend.close()
        raise
    return Model(backend, project)


def open_project(
    path: str,
    *,
    validate: bool = True,
) -> ProjectSession:
    """Open a mutable, source-backed project session."""
    return ProjectSession.open(path, validate=validate)
