"""Small public Python facade for Mercurio models."""

import os as _os
from pathlib import Path as _Path
from typing import Any as _Any

from .runtime import Model
from .session import ProjectSession as _ProjectSession
from .lab import LabModel as _LabModel

Project = _ProjectSession

__all__ = [
    "Model",
    "Project",
    "create",
    "open",
    "project",
]

__version__ = "0.1.0b4"

def open(
    path: str | None = None,
    *,
    executable: str | None = None,
    timeout: float = 60.0,
) -> "Model | _LabModel":
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


def _builder_facade(**kwargs: _Any):
    """Create an authoring builder using the simplified facade."""
    from .authoring import ModelBuilder

    return ModelBuilder(**kwargs)


def create(
    path: str | _Path | None = None,
    *,
    package: str | None = None,
    stdlib: bool = True,
    validate_each_mutation: bool = True,
) -> Project:
    """Create a new source-backed project.

    When *path* is omitted, the project stays fully in memory until ``save()``
    is called with a path. When *path* is provided, ``save()`` can be called
    without arguments.
    """
    project_builder = _builder_facade(validate_each_mutation=validate_each_mutation)
    if path is not None:
        project_builder._project_root = _Path(path)
    project_session = _ProjectSession(project_builder, path=path)
    if package is not None:
        project_session.in_package(package, stdlib_imports=stdlib)
    return project_session


def project(
    path: str,
    *,
    validate: bool = True,
) -> Project:
    """Open a mutable, source-backed project."""
    return _ProjectSession.open(path, validate=validate)
