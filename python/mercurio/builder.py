"""Native model-builder API.

This module intentionally hides the PyO3 extension module name from user scripts.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import site
import sys
from pathlib import Path


def _load_extension_module(candidate: Path):
    spec = importlib.util.spec_from_file_location(
        "mercurio._core",
        candidate,
        loader=importlib.machinery.ExtensionFileLoader("mercurio._core", str(candidate)),
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load native extension from {candidate}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mercurio._core"] = module
    spec.loader.exec_module(module)
    return module


def _load_native_from_workspace_target():
    """Load a locally built PyO3 extension when running from a source checkout."""

    package_dir = Path(__file__).resolve().parent
    workspace_dir = package_dir.parent.parent
    candidates = [
        workspace_dir / "target" / profile / name
        for profile in ("debug", "release")
        for name in ("_core.dll", "_core.pyd", "lib_core.so", "lib_core.dylib")
    ]
    for candidate in candidates:
        if candidate.is_file():
            return _load_extension_module(candidate)
    raise ImportError("No local mercurio._core target extension was found")


def _load_native_from_installed_wheel():
    """Load mercurio._core when source Python shadows the installed wheel."""

    package_dir = Path(__file__).resolve().parent
    candidates: list[Path] = []
    for base in site.getsitepackages() + [site.getusersitepackages()]:
        wheel_package_dir = Path(base) / "mercurio"
        if wheel_package_dir.resolve() == package_dir:
            continue
        for suffix in importlib.machinery.EXTENSION_SUFFIXES:
            candidates.extend(wheel_package_dir.glob(f"_core*{suffix}"))

    for candidate in candidates:
        return _load_extension_module(candidate)

    raise ImportError("No installed mercurio._core extension was found")


try:
    from mercurio._core import ModelBuilder, WriteBackResult
except ImportError:
    for load_native in (
        _load_native_from_workspace_target,
        _load_native_from_installed_wheel,
    ):
        try:
            _core = load_native()
            ModelBuilder = _core.ModelBuilder
            WriteBackResult = _core.WriteBackResult
            break
        except ImportError:
            continue
    else:
        try:
            from mercurio_core_native import ModelBuilder, WriteBackResult
        except ImportError as error:  # pragma: no cover - depends on native wheel install
            raise ImportError(
                "Mercurio native builder is not installed. Install the PyO3 wheel or run "
                "`maturin develop -m crates/mercurio-python/Cargo.toml` in this environment."
            ) from error


__all__ = ["ModelBuilder", "WriteBackResult"]
