"""Public Python API for opening and inspecting Mercurio models."""

import os as _os

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
from .lab import LabModel, parameter_sweep, batch_run
from . import extensions

__all__ = [
    "AnalysisQuery",
    "CompiledModel",
    "LabModel",
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
    "batch_run",
    "extensions",
    "fork",
    "open",
    "open_project",
    "parameter_sweep",
]

__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "ModelBuilder":
        from .authoring import ModelBuilder

        return ModelBuilder
    raise AttributeError(name)


def open(
    path: str | None = None,
    *,
    executable: str | None = None,
    timeout: float = 60.0,
) -> "Model | LabModel":
    """Open a model.

    In the Lab kernel context (``MERCURIO_LAB_KERNEL=1``), calling
    ``open()`` with no path returns a :class:`LabModel` backed by the
    active workspace.  Outside the Lab, *path* is required.
    """
    if _os.environ.get("MERCURIO_LAB_KERNEL") == "1" and path is None:
        from .lab import open_lab
        return open_lab()

    if path is None:
        raise TypeError("path is required outside the Lab kernel context")

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


def fork(model: LabModel, label: str, **params: object) -> LabModel:
    """Convenience wrapper for :meth:`LabModel.fork`."""
    return model.fork(label, **params)


def open_project(
    path: str,
    *,
    validate: bool = True,
) -> ProjectSession:
    """Open a mutable, source-backed project session."""
    return ProjectSession.open(path, validate=validate)
