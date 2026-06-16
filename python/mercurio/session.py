from __future__ import annotations

import copy
import html
import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from .authoring import ModelBuilder
    from .semantic import SemanticSnapshotDifference


JsonObject = dict[str, Any]
FrozenJsonObject = Mapping[str, Any]


def _model_builder_class():
    from .authoring import ModelBuilder

    return ModelBuilder


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _source_fingerprint(files: Mapping[str, str]) -> str:
    return hashlib.sha256(_canonical_json(dict(files)).encode("utf-8")).hexdigest()


def _freeze_value(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _snapshot_rows(native_model: Any) -> list[JsonObject]:
    rows = json.loads(native_model.semantic_snapshot_json())
    if not isinstance(rows, list):
        raise TypeError("semantic snapshot must be a JSON array")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _row_name(row: JsonObject) -> str:
    qualified = row.get("qualified_name") or row.get("qualifiedName")
    if qualified is not None:
        return str(qualified)
    return str(row.get("name") or row.get("id") or "")


def _short_name(qualified_name: str) -> str:
    return qualified_name.rsplit(".", 1)[-1]


def _as_qualified_name(value: Any) -> str:
    if isinstance(value, SemanticRef):
        return value.qualified_name
    qualified_name = getattr(value, "qualified_name", None)
    if isinstance(qualified_name, str):
        return qualified_name
    return str(value)


def _row_values(row: JsonObject, *names: str) -> list[str]:
    values: list[str] = []
    for name in names:
        raw = row.get(name)
        if raw is None:
            continue
        if isinstance(raw, (list, tuple)):
            values.extend(str(item) for item in raw)
        else:
            values.append(str(raw))
    return values


@dataclass(frozen=True)
class SemanticRef:
    """Immutable handle to one element in one compiled model revision."""

    _model: "CompiledModel" = field(repr=False, compare=False)
    qualified_name: str
    kind: str
    data: FrozenJsonObject = field(repr=False)

    @property
    def revision(self) -> str:
        return self._model.revision

    @property
    def name(self) -> str:
        return _short_name(self.qualified_name)

    def attr(self, name: str, default: Any = None) -> Any:
        return self.data.get(name, default)

    def attrs(self) -> JsonObject:
        return dict(self.data)

    def owner(self) -> str | None:
        value = self.data.get("owner")
        return None if value is None else str(value)

    def type_name(self) -> str | None:
        values = _row_values(self.data, "type", "typed_by", "typedBy")
        return values[0] if values else None

    def specializes(self) -> list[str]:
        return _row_values(self.data, "specializes", "specialization")

    def children(self) -> list["SemanticRef"]:
        return self._model.children_of(self)

    def walk(self) -> Iterable["SemanticRef"]:
        yield self
        for child in self.children():
            yield from child.walk()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}({self.qualified_name!r}, "
            f"revision={self.revision[:12]!r})"
        )


@dataclass(frozen=True)
class PartDefRef(SemanticRef):
    def subtypes(self, *, transitive: bool = True) -> list["PartDefRef"]:
        return self._model.subtypes_of(self, transitive=transitive)


@dataclass(frozen=True)
class PartUsageRef(SemanticRef):
    pass


class VariantBaseChangedError(RuntimeError):
    """Raised when a variant is compiled after its base project has changed."""


class StaleSemanticRefError(RuntimeError):
    """Raised when editing through a ref from an older source state."""


class AnalysisQuery:
    """Read-only query and export helpers for one compiled model revision."""

    def __init__(self, model: "CompiledModel") -> None:
        self._model = model

    def refs(
        self,
        *,
        kind: str | None = None,
        where: Callable[[SemanticRef], bool] | None = None,
    ) -> list[SemanticRef]:
        refs = self._model.refs()
        if kind is not None:
            refs = [ref for ref in refs if kind in ref.kind]
        if where is not None:
            refs = [ref for ref in refs if where(ref)]
        return refs

    def part_defs(
        self,
        where: Callable[[PartDefRef], bool] | None = None,
    ) -> list[PartDefRef]:
        refs = self._model.part_defs()
        if where is not None:
            refs = [ref for ref in refs if where(ref)]
        return refs

    def part_usages(
        self,
        where: Callable[[PartUsageRef], bool] | None = None,
    ) -> list[PartUsageRef]:
        refs = self._model.part_usages()
        if where is not None:
            refs = [ref for ref in refs if where(ref)]
        return refs

    def subtypes(self, base: str | SemanticRef, *, transitive: bool = True) -> list[PartDefRef]:
        base_ref = self._model.resolve(base) if isinstance(base, str) else base
        return self._model.subtypes_of(base_ref, transitive=transitive)

    def containment(self, root: str | SemanticRef | None = None) -> list[SemanticRef]:
        if root is None:
            return list(self._model.walk())
        root_ref = self._model.resolve(root) if isinstance(root, str) else root
        return list(root_ref.walk())


class CompiledModel:
    """Immutable semantic snapshot compiled from a project or variant."""

    def __init__(self, native_model: Any, *, source: Any = None) -> None:
        self._native_model = native_model
        self._source = source
        rows = _snapshot_rows(native_model)
        self.revision = hashlib.sha256(_canonical_json(rows).encode("utf-8")).hexdigest()
        self._rows = tuple(_freeze_value(row) for row in rows)
        self._refs = tuple(self._make_ref(row) for row in self._rows)
        self._by_qname = {ref.qualified_name: ref for ref in self._refs}
        self.query = AnalysisQuery(self)

    @property
    def raw(self) -> Any:
        return self._native_model

    @property
    def rows(self) -> tuple[FrozenJsonObject, ...]:
        return self._rows

    def semantic_snapshot_json(self) -> str:
        return self._native_model.semantic_snapshot_json()

    def refs(self) -> list[SemanticRef]:
        return list(self._refs)

    def diff(self, other: Any) -> list["SemanticSnapshotDifference"]:
        from .semantic import compare_semantic_snapshots

        return compare_semantic_snapshots(self, other)

    def to_records(self, refs: Iterable[SemanticRef] | None = None) -> list[JsonObject]:
        selected = self._refs if refs is None else tuple(refs)
        return [
            {
                "qualified_name": ref.qualified_name,
                "name": ref.name,
                "kind": ref.kind,
                "owner": ref.owner(),
                "type": ref.type_name(),
                "revision": ref.revision,
            }
            for ref in selected
        ]

    def to_frame(self, refs: Iterable[SemanticRef] | None = None) -> Any:
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("to_frame() requires pandas; use to_records() without pandas") from exc
        return pd.DataFrame(self.to_records(refs))

    def graph(self, relation: str = "containment") -> JsonObject:
        if relation == "containment":
            edges = [
                {"source": parent.qualified_name, "target": child.qualified_name, "relation": "owns"}
                for parent in self._refs
                for child in self.children_of(parent)
            ]
        elif relation == "specialization":
            edges = [
                {"source": subtype.qualified_name, "target": target, "relation": "specializes"}
                for subtype in self.part_defs()
                for target in subtype.specializes()
            ]
        else:
            raise ValueError("relation must be 'containment' or 'specialization'")
        return {
            "revision": self.revision,
            "relation": relation,
            "nodes": self.to_records(),
            "edges": edges,
        }

    def simulation(self, name: str) -> "SimulationConfiguration":
        return SimulationConfiguration(name, self)

    def _repr_html_(self) -> str:
        counts = {
            "part definitions": len(self.part_defs()),
            "part usages": len(self.part_usages()),
            "elements": len(self._refs),
        }
        rows = "".join(
            "<tr>"
            f"<th>{html.escape(label)}</th>"
            f"<td>{value}</td>"
            "</tr>"
            for label, value in counts.items()
        )
        return (
            "<table>"
            "<caption>Mercurio CompiledModel</caption>"
            f"<tr><th>revision</th><td><code>{html.escape(self.revision[:12])}</code></td></tr>"
            f"{rows}"
            "</table>"
        )

    def __repr__(self) -> str:
        return (
            f"CompiledModel(revision={self.revision[:12]!r}, "
            f"elements={len(self._refs)}, part_defs={len(self.part_defs())}, "
            f"part_usages={len(self.part_usages())})"
        )

    def resolve(self, value: Any) -> SemanticRef:
        qualified_name = _as_qualified_name(value)
        match = self._by_qname.get(qualified_name)
        if match is not None:
            return match
        suffix = f".{qualified_name}"
        matches = [ref for ref in self._refs if ref.qualified_name.endswith(suffix)]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise KeyError(f"no semantic element named {qualified_name!r} in model {self.revision}")
        raise KeyError(f"ambiguous semantic element name {qualified_name!r}")

    def part_def(self, name: str) -> PartDefRef:
        return self._one_typed(name, PartDefRef)

    def part_usage(self, name: str) -> PartUsageRef:
        return self._one_typed(name, PartUsageRef)

    def part_defs(self) -> list[PartDefRef]:
        return [ref for ref in self._refs if isinstance(ref, PartDefRef)]

    def part_usages(self) -> list[PartUsageRef]:
        return [ref for ref in self._refs if isinstance(ref, PartUsageRef)]

    def children_of(self, parent: SemanticRef) -> list[SemanticRef]:
        owner = parent.qualified_name
        owner_id = parent.data.get("id")
        children: list[SemanticRef] = []
        for ref in self._refs:
            if ref is parent:
                continue
            owners = _row_values(ref.data, "owner", "parent", "parentId")
            if owner in owners or (owner_id is not None and str(owner_id) in owners):
                children.append(ref)
        if children:
            return children
        prefix = f"{owner}."
        return [
            ref
            for ref in self._refs
            if ref.qualified_name.startswith(prefix)
            and "." not in ref.qualified_name[len(prefix) :]
        ]

    def walk(self) -> Iterable[SemanticRef]:
        owned = {child.qualified_name for ref in self._refs for child in self.children_of(ref)}
        for ref in self._refs:
            if ref.qualified_name not in owned:
                yield from ref.walk()

    def subtypes_of(self, base: SemanticRef, *, transitive: bool = True) -> list[PartDefRef]:
        found: list[PartDefRef] = []
        frontier = [base.qualified_name]
        while frontier:
            current = frontier.pop(0)
            direct = [
                ref
                for ref in self.part_defs()
                if ref not in found
                and any(value == current or value.endswith(f".{_short_name(current)}") for value in ref.specializes())
            ]
            found.extend(direct)
            if transitive:
                frontier.extend(ref.qualified_name for ref in direct)
        return found

    def _make_ref(self, row: FrozenJsonObject) -> SemanticRef:
        qualified_name = _row_name(row)
        kind = str(row.get("kind") or row.get("elementKind") or "")
        if "PartDefinition" in kind:
            return PartDefRef(self, qualified_name, kind, row)
        if "PartUsage" in kind:
            return PartUsageRef(self, qualified_name, kind, row)
        return SemanticRef(self, qualified_name, kind, row)

    def _one_typed(self, name: str, cls: type[SemanticRef]) -> Any:
        matches = [
            ref
            for ref in self._refs
            if isinstance(ref, cls)
            and (ref.qualified_name == name or ref.name == name or ref.qualified_name.endswith(f".{name}"))
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise KeyError(f"no {cls.__name__} named {name!r} in model {self.revision}")
        raise KeyError(f"ambiguous {cls.__name__} name {name!r}")


class SmallEdit:
    """Source-preserving mutation facade against a project or variant builder."""

    def __init__(self, builder: "ModelBuilder", target: Any) -> None:
        self._builder = builder
        self._target = _as_qualified_name(target)

    def rename(self, new_name: str) -> "SmallEdit":
        self._builder.rename(self._target, new_name)
        self._target = new_name if "." not in self._target else f"{self._target.rsplit('.', 1)[0]}.{new_name}"
        return self

    def set_type(self, target: Any | None) -> "SmallEdit":
        self._builder.set_type(self._target, target)
        return self

    def set_value(self, value: Any) -> "SmallEdit":
        self._builder.set_expression(self._target, str(value))
        return self

    def set_attribute(self, name: str, value: Any) -> "SmallEdit":
        self._builder.set_attribute(self._target, name, value)
        return self

    def add_specialization(self, target: Any) -> "SmallEdit":
        self._builder.add_specialization(self._target, target)
        return self

    def remove(self) -> None:
        self._builder.remove(self._target)


class ProjectSession:
    """Mutable, source-backed context for authoring, editing, and compiling."""

    def __init__(self, builder: "ModelBuilder", *, path: str | Path | None = None) -> None:
        self._builder = builder
        self.path = None if path is None else Path(path)
        self._compiled_source_fingerprints: dict[str, str] = {}

    @classmethod
    def open(cls, path: str | Path, *, validate: bool = True) -> "ProjectSession":
        return cls(_model_builder_class().from_project(path, validate=validate), path=path)

    @classmethod
    def from_files(
        cls,
        files: dict[str, str],
        *,
        validate: bool = True,
    ) -> "ProjectSession":
        return cls(_model_builder_class().from_files(files, validate=validate))

    def in_package(self, name: str, *, stdlib_imports: bool = True) -> "ProjectSession":
        self._builder.in_package(name, stdlib_imports=stdlib_imports)
        return self

    def add(self, declaration: Any) -> "ProjectSession":
        self._builder.add(declaration)
        return self

    def edit(self, target: Any) -> SmallEdit:
        self._assert_ref_current(target)
        return SmallEdit(self._builder, target)

    def compile(self) -> CompiledModel:
        model = CompiledModel(self._builder.compile(), source=self)
        self._compiled_source_fingerprints[model.revision] = self.source_fingerprint
        return model

    def to_sysml(self) -> dict[str, str]:
        return self._builder.to_sysml()

    @property
    def source_fingerprint(self) -> str:
        return _source_fingerprint(self.to_sysml())

    def save(self, path: str | Path | None = None) -> None:
        self._builder.save(path)

    def trade_study(self, name: str) -> "TradeStudy":
        return TradeStudy(name, self)

    def simulation(self, name: str) -> "SimulationConfiguration":
        return SimulationConfiguration(name, self)

    def __repr__(self) -> str:
        path = None if self.path is None else str(self.path)
        return (
            f"ProjectSession(path={path!r}, "
            f"source_fingerprint={self.source_fingerprint[:12]!r})"
        )

    def _assert_ref_current(self, target: Any) -> None:
        if not isinstance(target, SemanticRef):
            return
        source_fingerprint = self._compiled_source_fingerprints.get(target.revision)
        if source_fingerprint is None:
            return
        current_fingerprint = self.source_fingerprint
        if source_fingerprint != current_fingerprint:
            raise StaleSemanticRefError(
                f"semantic ref {target.qualified_name!r} belongs to model revision "
                f"{target.revision}, compiled from source fingerprint {source_fingerprint}; "
                f"current source fingerprint is {current_fingerprint}. Recompile and "
                "resolve a fresh ref before editing."
            )


class TradeStudy:
    """Named collection of low-cost source overlays over a base project session."""

    def __init__(self, name: str, base: ProjectSession) -> None:
        self.name = name
        self.base = base

    def variant(self, name: str) -> "Variant":
        files = copy.deepcopy(self.base.to_sysml())
        return Variant(
            name,
            self,
            _model_builder_class().from_files(files),
            base_fingerprint=_source_fingerprint(files),
        )


class Variant:
    """Mutable overlay for trade-study edits."""

    def __init__(
        self,
        name: str,
        study: TradeStudy,
        builder: "ModelBuilder",
        *,
        base_fingerprint: str | None = None,
    ) -> None:
        self.name = name
        self.study = study
        self._builder = builder
        self.base_fingerprint = base_fingerprint
        self._compiled_source_fingerprints: dict[str, str] = {}

    def edit(self, target: Any) -> SmallEdit:
        self._assert_ref_current(target)
        return SmallEdit(self._builder, target)

    def add(self, declaration: Any) -> "Variant":
        self._builder.add(declaration)
        return self

    def compile(self, *, allow_stale_base: bool = False) -> CompiledModel:
        if not allow_stale_base:
            self.assert_base_current()
        model = CompiledModel(self._builder.compile(), source=self)
        self._compiled_source_fingerprints[model.revision] = self.source_fingerprint
        return model

    def to_sysml(self) -> dict[str, str]:
        return self._builder.to_sysml()

    @property
    def source_fingerprint(self) -> str:
        return _source_fingerprint(self.to_sysml())

    @property
    def is_base_stale(self) -> bool:
        return (
            self.base_fingerprint is not None
            and self.base_fingerprint != self.study.base.source_fingerprint
        )

    def assert_base_current(self) -> None:
        if self.is_base_stale:
            raise VariantBaseChangedError(
                f"variant {self.name!r} was forked from base fingerprint "
                f"{self.base_fingerprint}, but the base project is now "
                f"{self.study.base.source_fingerprint}; create a new variant "
                "or compile with allow_stale_base=True"
            )

    def simulation(self, name: str) -> "SimulationConfiguration":
        return SimulationConfiguration(name, self)

    def __repr__(self) -> str:
        return (
            f"Variant(name={self.name!r}, base_stale={self.is_base_stale}, "
            f"source_fingerprint={self.source_fingerprint[:12]!r})"
        )

    def _assert_ref_current(self, target: Any) -> None:
        if not isinstance(target, SemanticRef):
            return
        source_fingerprint = self._compiled_source_fingerprints.get(target.revision)
        if source_fingerprint is None:
            return
        current_fingerprint = self.source_fingerprint
        if source_fingerprint != current_fingerprint:
            raise StaleSemanticRefError(
                f"semantic ref {target.qualified_name!r} belongs to model revision "
                f"{target.revision}, compiled from source fingerprint {source_fingerprint}; "
                f"current source fingerprint is {current_fingerprint}. Recompile and "
                "resolve a fresh ref before editing."
            )


class SimulationConfiguration:
    """Declarative simulation setup bound to a model, project, or variant."""

    def __init__(self, name: str, target: CompiledModel | ProjectSession | Variant) -> None:
        self.name = name
        self.target = target
        self.subject: str | None = None
        self.settings: JsonObject = {}

    @property
    def model_revision(self) -> str | None:
        if isinstance(self.target, CompiledModel):
            return self.target.revision
        return None

    @property
    def source_fingerprint(self) -> str | None:
        if isinstance(self.target, (ProjectSession, Variant)):
            return self.target.source_fingerprint
        return None

    def for_subject(self, subject: Any) -> "SimulationConfiguration":
        self.subject = _as_qualified_name(subject)
        return self

    def configure(self, **settings: Any) -> "SimulationConfiguration":
        self.settings.update(settings)
        return self

    def to_dict(self) -> JsonObject:
        return {
            "name": self.name,
            "subject": self.subject,
            "settings": dict(self.settings),
            "model_revision": self.model_revision,
            "source_fingerprint": self.source_fingerprint,
        }

    def _repr_html_(self) -> str:
        data = self.to_dict()
        rows = "".join(
            "<tr>"
            f"<th>{html.escape(str(key))}</th>"
            f"<td><code>{html.escape(str(value))}</code></td>"
            "</tr>"
            for key, value in data.items()
        )
        return f"<table><caption>Mercurio SimulationConfiguration</caption>{rows}</table>"

    def __repr__(self) -> str:
        return (
            f"SimulationConfiguration(name={self.name!r}, subject={self.subject!r}, "
            f"model_revision={None if self.model_revision is None else self.model_revision[:12]!r}, "
            f"source_fingerprint={None if self.source_fingerprint is None else self.source_fingerprint[:12]!r})"
        )

    def run(self) -> Any:
        raise NotImplementedError(
            "simulation execution is not wired to the layered Python API yet; "
            "use to_dict() to persist declarative simulation configuration"
        )
