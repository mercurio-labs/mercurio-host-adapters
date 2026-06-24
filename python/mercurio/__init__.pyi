from pathlib import Path

from .lab import LabModel
from .runtime import Model
from .session import ProjectSession

__version__: str

Project = ProjectSession

def open(
    path: str | None = None,
    *,
    executable: str | None = None,
    timeout: float = 60.0,
) -> Model | LabModel: ...

def project(
    path: str,
    *,
    validate: bool = True,
) -> Project: ...

def create(
    path: str | Path | None = None,
    *,
    package: str | None = None,
    stdlib: bool = True,
    validate_each_mutation: bool = True,
) -> Project: ...

__all__: list[str]
