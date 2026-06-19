"""Native model-builder API.

This module intentionally hides the PyO3 extension module name from user scripts.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import site
import sys
from pathlib import Path


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
        spec = importlib.util.spec_from_file_location("mercurio._core", candidate)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules["mercurio._core"] = module
        spec.loader.exec_module(module)
        return module

    raise ImportError("No installed mercurio._core extension was found")


try:
    from mercurio._core import ModelBuilder, WriteBackResult
except ImportError:
    try:
        _core = _load_native_from_installed_wheel()
        ModelBuilder = _core.ModelBuilder
        WriteBackResult = _core.WriteBackResult
    except ImportError:
        try:
            from mercurio_core_native import ModelBuilder, WriteBackResult
        except ImportError as error:  # pragma: no cover - depends on native wheel install
            raise ImportError(
                "Mercurio native builder is not installed. Install the PyO3 wheel or run "
                "`maturin develop -m crates/mercurio-python/Cargo.toml` in this environment."
            ) from error


__all__ = ["ModelBuilder", "WriteBackResult"]
