from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StdlibRef:
    qualified_name: str

    @property
    def id(self) -> str:
        return self.qualified_name


class _Namespace:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def __getattr__(self, name: str) -> StdlibRef:
        return StdlibRef(f"{self._prefix}::{_pascal(name)}")


def _pascal(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


isq = _Namespace("ISQ")
si = _Namespace("SI")
scalar_values = _Namespace("ScalarValues")
