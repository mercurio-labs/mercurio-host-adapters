"""Python client for the Mercurio local HTTP backend."""

from .backend import Mercurio
from .client import MercurioClient
from .errors import MercurioBackendError, MercurioError, MercurioLaunchError
from .models import (
    AnalysisCaseInfo,
    ChannelData,
    PartRef,
    SimulationTrace,
    StateData,
    TraceChannel,
)
from .runtime import ModelRuntime
from .workspace import MercurioWorkspace

__all__ = [
    "AnalysisCaseInfo",
    "ChannelData",
    "Mercurio",
    "MercurioBackendError",
    "MercurioClient",
    "MercurioError",
    "MercurioLaunchError",
    "MercurioWorkspace",
    "ModelRuntime",
    "PartRef",
    "SimulationTrace",
    "StateData",
    "TraceChannel",
    "open",
]

__version__ = "0.1.0"


def open(
    path: str,
    *,
    executable: str | None = None,
    timeout: float = 60.0,
) -> ModelRuntime:
    """
    Launch a local Mercurio backend, open *path*, compile it, and return a
    model runtime. Use as a context manager to close the backend process.
    """
    backend = Mercurio.launch(executable=executable, timeout=timeout)
    try:
        workspace = backend.open_workspace(path)
        workspace.compile_project(".")
    except Exception:
        backend.close()
        raise
    return ModelRuntime(backend, workspace)
