from __future__ import annotations

from pathlib import Path
from typing import Any

from .builder import ModelBuilder as _NativeModelBuilder
from .stdlib import StdlibRef


def _ref(value: Any) -> str:
    if isinstance(value, StdlibRef):
        return value.qualified_name
    qualified_name = getattr(value, "qualified_name", None)
    if isinstance(qualified_name, str):
        return qualified_name
    return str(value)


class ModelBuilder:
    def __init__(self) -> None:
        self._inner = _NativeModelBuilder()
        self._default_package: str | None = None
        self._default_file = "model.sysml"

    @classmethod
    def for_metamodel(cls, _id: str) -> "ModelBuilder":
        return cls()

    def in_package(self, name: str) -> "ModelBuilder":
        self._inner.add_package(self._default_file, name)
        self._default_package = name
        return self

    def add(self, element: "_Declaration") -> "ModelBuilder":
        if self._default_package is None:
            raise ValueError("call in_package() before add()")
        element._emit(self._inner, self._default_package)
        return self

    def to_sysml(self) -> dict[str, str]:
        return self._inner.rendered_files()

    def compile(self):
        return self._inner.compile_model()

    def save(self, path: str | Path) -> None:
        root = Path(path)
        for rel, source in self.to_sysml().items():
            output = root / rel
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(source, encoding="utf-8")


class _Declaration:
    _kind = "definition"
    _keyword = ""

    def __init__(self, name: str) -> None:
        self.name = name
        self._type: str | None = None
        self._specializes: list[str] = []
        self._members: list[_Declaration] = []
        self._expression: str | None = None
        self._multiplicity: str | None = None
        self._direction: str | None = None
        self._abstract = False

    def specializes(self, target: Any):
        self._specializes.append(_ref(target))
        return self

    def typed(self, target: Any):
        self._type = _ref(target)
        return self

    def expression(self, text: str):
        self._expression = text
        return self

    def multiplicity(self, text: str):
        self._multiplicity = text
        return self

    def direction(self, text: str):
        self._direction = text
        return self

    def doc(self, _text: str):
        return self

    def abstract_(self):
        self._abstract = True
        return self

    def _emit(self, builder: _NativeModelBuilder, container: str) -> str:
        if self._kind == "definition":
            builder.add_definition(container, self._keyword, self.name, self._specializes or None)
        else:
            builder.add_usage(
                container,
                self._keyword,
                self.name,
                self._type,
                self._specializes or None,
            )
        qname = f"{container}.{self.name}"
        if self._expression is not None:
            builder.set_expression(qname, self._expression)
        if self._direction is not None:
            builder.set_attribute(qname, "direction", self._direction)
        if self._multiplicity is not None:
            builder.set_attribute(qname, "multiplicity", self._multiplicity)
        if self._abstract:
            builder.set_attribute(qname, "isAbstract", True)
        for member in self._members:
            member._emit(builder, qname)
        return qname


class _Definition(_Declaration):
    _kind = "definition"

    def _with(self, member: _Declaration):
        self._members.append(member)
        return self

    def with_part(self, member): return self._with(member)
    def with_item(self, member): return self._with(member)
    def with_attr(self, member): return self._with(member)
    def with_port(self, member): return self._with(member)
    def with_end(self, member): return self._with(member)
    def with_action(self, member): return self._with(member)
    def with_state(self, member): return self._with(member)


class _Usage(_Declaration):
    _kind = "usage"

    def end(self, _target: Any):
        return self


class PartDefinition(_Definition): _keyword = "part"
class ItemDefinition(_Definition): _keyword = "item"
class AttributeDefinition(_Definition): _keyword = "attribute"
class PortDefinition(_Definition): _keyword = "port"
class ConnectionDefinition(_Definition): _keyword = "connection"
class ActionDefinition(_Definition): _keyword = "action"
class StateDefinition(_Definition): _keyword = "state"
class RequirementDefinition(_Definition): _keyword = "requirement"
class InterfaceDefinition(_Definition): _keyword = "interface"


class PartUsage(_Usage): _keyword = "part"
class ItemUsage(_Usage): _keyword = "item"
class AttributeUsage(_Usage): _keyword = "attribute"
class PortUsage(_Usage): _keyword = "port"
class ConnectionUsage(_Usage): _keyword = "connection"


__all__ = [
    "ModelBuilder",
    "PartDefinition",
    "PartUsage",
    "ItemDefinition",
    "ItemUsage",
    "AttributeDefinition",
    "AttributeUsage",
    "PortDefinition",
    "PortUsage",
    "ConnectionDefinition",
    "ConnectionUsage",
    "ActionDefinition",
    "StateDefinition",
    "RequirementDefinition",
    "InterfaceDefinition",
]
