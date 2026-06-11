from dataclasses import dataclass

@dataclass(frozen=True)
class StdlibRef:
    qualified_name: str
    @property
    def id(self) -> str: ...

class _Namespace:
    def __getattr__(self, name: str) -> StdlibRef: ...

isq: _Namespace
si: _Namespace
scalar_values: _Namespace
