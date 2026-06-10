"""Public Python API for opening and inspecting Mercurio models."""

from .runtime import Model

__all__ = [
    "Model",
    "open",
]

__version__ = "0.1.0"


def open(
    path: str,
    *,
    executable: str | None = None,
    timeout: float = 60.0,
) -> Model:
    """
    Launch a local Mercurio backend, open *path*, compile it, and return a
    typed model. Use as a context manager to close the backend process.
    """
    from .backend import Mercurio

    backend = Mercurio.launch(executable=executable, timeout=timeout)
    try:
        workspace = backend.open_workspace(path, mode="compiled")
    except Exception:
        backend.close()
        raise
    return Model(backend, workspace)
