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


def _cell_request(
    source: str,
    *,
    kind: str = "query",
    language: str | None = "mercurio_dsl",
    parameters: Mapping[str, Any] | None = None,
    cell_id: str | None = None,
    session_id: str | None = None,
) -> JsonObject:
    request: JsonObject = {
        "kind": kind,
        "source": source,
        "parameters": dict(parameters or {}),
    }
    if language is not None:
        request["language"] = language
    if cell_id is not None:
        request["cellId"] = cell_id
    if session_id is not None:
        request["sessionId"] = session_id
    return request


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


def _model_layer_label(value: Any) -> str:
    try:
        layer = int(value)
    except (TypeError, ValueError):
        return "" if value is None else str(value)
    return {
        0: "foundation",
        1: "library",
        2: "user",
        3: "derived",
    }.get(layer, "other")


def _metatype_tail(value: str) -> str:
    for separator in (":", ".", "/", "#"):
        value = value.rsplit(separator, 1)[-1]
    return value.strip().strip("\"'")


def _normalize_metatype_key(value: str) -> str:
    return "".join(ch.lower() for ch in value.strip() if ch.isalnum())


def _metatype_match_keys(value: str) -> set[str]:
    keys = {
        _normalize_metatype_key(value),
        _normalize_metatype_key(_metatype_tail(value)),
    }
    return {key for key in keys if key}


def _metatype_names_match(candidate: str, expected: str) -> bool:
    return bool(_metatype_match_keys(candidate) & _metatype_match_keys(expected))


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        for key in ("label", "name", "declared_name", "qualified_name", "id", "element_id"):
            if key in value:
                return _as_string_list(value[key])
        return []
    if isinstance(value, (list, tuple)):
        values: list[str] = []
        for item in value:
            values.extend(_as_string_list(item))
        return values
    text = str(value)
    return [text] if text else []


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

    @property
    def declared_name(self) -> str:
        values = _as_string_list(
            self.data.get("declared_name", self.data.get("declaredName"))
        )
        return values[0] if values else self.name

    @property
    def model_layer(self) -> str:
        for key in ("model_layer", "modelLayer", "layer_name", "layerName"):
            values = _as_string_list(self.data.get(key))
            if values:
                return values[0]
        return _model_layer_label(self.data.get("layer"))

    @property
    def metatype_name(self) -> str | None:
        for key in ("metatype_name", "metatypeName", "metatype"):
            values = _as_string_list(self.data.get(key))
            if values:
                return _metatype_tail(values[0])
        chain = self.metatype_chain
        return chain[0] if chain else None

    @property
    def metatype_chain(self) -> list[str]:
        for key in ("metatype_chain", "metatypeChain", "metatype_specialization_chain"):
            values = _as_string_list(self.data.get(key))
            if values:
                return [_metatype_tail(value) for value in values]
        for key in ("metatype_name", "metatypeName", "metatype"):
            values = _as_string_list(self.data.get(key))
            if values:
                return [_metatype_tail(values[0])]
        return []

    def attr(self, name: str, default: Any = None) -> Any:
        return self.data.get(name, default)

    def get(self, name: str, default: Any = None) -> Any:
        return self.attr(name, default)

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

    def is_metatype(self, expected: str, *, include_subtypes: bool = True) -> bool:
        candidates = self.metatype_chain if include_subtypes else []
        direct = self.metatype_name
        if direct is not None:
            candidates = [direct] + [item for item in candidates if item != direct]
        return any(_metatype_names_match(candidate, expected) for candidate in candidates)

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


class SemanticQuery:
    """Chainable read-only query over compiled semantic refs."""

    def __init__(self, refs: Iterable[SemanticRef]) -> None:
        self._refs = tuple(refs)

    def __iter__(self) -> Iterable[SemanticRef]:
        return iter(self._refs)

    def __len__(self) -> int:
        return len(self._refs)

    def refs(self) -> list[SemanticRef]:
        return list(self._refs)

    def count(self) -> int:
        return len(self._refs)

    def first(self) -> SemanticRef | None:
        return self._refs[0] if self._refs else None

    def where(self, predicate: Callable[[SemanticRef], bool]) -> "SemanticQuery":
        return type(self)(ref for ref in self._refs if predicate(ref))

    def where_kind_contains(self, text: str) -> "SemanticQuery":
        return self.where(lambda ref: text in ref.kind)

    def where_metatype(self, expected: str) -> "SemanticQuery":
        return self.where(lambda ref: ref.is_metatype(expected, include_subtypes=False))

    def where_metatype_is(self, expected: str) -> "SemanticQuery":
        return self.where(lambda ref: ref.is_metatype(expected, include_subtypes=True))

    def where_model_layer(self, expected: str) -> "SemanticQuery":
        expected_key = str(expected).lower()
        return self.where(lambda ref: ref.model_layer.lower() == expected_key)

    def order_by(self, field: str) -> "SemanticQuery":
        return type(self)(
            sorted(self._refs, key=lambda ref: str(_select_ref_field(ref, field) or ""))
        )

    def select(self, fields: Iterable[str]) -> list[JsonObject]:
        columns = [str(field) for field in fields]
        return [
            {field: _select_ref_field(ref, field) for field in columns}
            for ref in self._refs
        ]


def _select_ref_field(ref: SemanticRef, field: str) -> Any:
    if field == "qualified_name":
        return ref.qualified_name
    if field == "name":
        return ref.name
    if field == "declared_name":
        return ref.declared_name
    if field == "kind":
        return ref.kind
    if field == "owner":
        return ref.owner()
    if field == "type":
        return ref.type_name()
    if field == "revision":
        return ref.revision
    if field == "model_layer":
        return ref.model_layer
    if field == "metatype_name":
        return ref.metatype_name
    if field == "metatype_chain":
        return ref.metatype_chain
    return ref.attr(field)


class AnalysisQuery:
    """Read-only query and export helpers for one compiled model revision."""

    def __init__(self, model: "CompiledModel") -> None:
        self._model = model

    def elements(self) -> SemanticQuery:
        return SemanticQuery(self._model.refs())

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

    def where_metatype(self, expected: str) -> SemanticQuery:
        return self.elements().where_metatype(expected)

    def where_metatype_is(self, expected: str) -> SemanticQuery:
        return self.elements().where_metatype_is(expected)

    def where_model_layer(self, expected: str) -> SemanticQuery:
        return self.elements().where_model_layer(expected)

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


@dataclass(frozen=True)
class CellRunReport:
    """Result from the shared Mercurio session/cell execution path."""

    cell_id: str
    kind: str
    status: str
    outputs: tuple[JsonObject, ...] = ()
    artifacts: tuple[JsonObject, ...] = ()
    diagnostics: tuple[JsonObject, ...] = ()
    capability_report: JsonObject | None = None
    metadata: FrozenJsonObject = field(default_factory=lambda: MappingProxyType({}))
    session_id: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CellRunReport":
        outputs = tuple(dict(item) for item in data.get("outputs", []) if isinstance(item, Mapping))
        artifacts = tuple(dict(item) for item in data.get("artifacts", []) if isinstance(item, Mapping))
        diagnostics = tuple(dict(item) for item in data.get("diagnostics", []) if isinstance(item, Mapping))
        capability_report = data.get("capabilityReport")
        if capability_report is not None and not isinstance(capability_report, dict):
            capability_report = {"value": capability_report}
        metadata = data.get("metadata")
        if not isinstance(metadata, Mapping):
            metadata = {}
        return cls(
            session_id=None if data.get("sessionId") is None else str(data.get("sessionId")),
            cell_id=str(data.get("cellId") or ""),
            kind=str(data.get("kind") or ""),
            status=str(data.get("status") or ""),
            outputs=outputs,
            artifacts=artifacts,
            diagnostics=diagnostics,
            capability_report=capability_report,
            metadata=MappingProxyType(dict(metadata)),
        )

    def output(self, output_id: str) -> JsonObject:
        for output in self.outputs:
            if output.get("id") == output_id:
                return dict(output)
        raise KeyError(f"cell output {output_id!r} was not produced")

    @property
    def result(self) -> Any:
        return self.output("result").get("value")

    def to_dict(self) -> JsonObject:
        data: JsonObject = {
            "cellId": self.cell_id,
            "kind": self.kind,
            "status": self.status,
            "outputs": [dict(item) for item in self.outputs],
            "artifacts": [dict(item) for item in self.artifacts],
            "diagnostics": [dict(item) for item in self.diagnostics],
            "metadata": dict(self.metadata),
        }
        if self.session_id is not None:
            data["sessionId"] = self.session_id
        if self.capability_report is not None:
            data["capabilityReport"] = dict(self.capability_report)
        return data


def _cell_report_from_dict(data: Mapping[str, Any]) -> CellRunReport:
    return CellRunReport.from_dict(data)


def _cell_report_from_json(raw: str) -> CellRunReport:
    data = json.loads(raw)
    if not isinstance(data, Mapping):
        raise TypeError("cell run report must be a JSON object")
    return _cell_report_from_dict(data)


def _native_json_data(native: Any, method_name: str, *args: Any) -> Any:
    method = getattr(native, method_name, None)
    if method is None:
        raise RuntimeError(
            f"{method_name}() requires the native Mercurio model; compile through "
            "the native Python package before calling this exploration API"
        )
    return json.loads(method(*args))


def _native_json_object(native: Any, method_name: str, *args: Any) -> JsonObject:
    data = _native_json_data(native, method_name, *args)
    if not isinstance(data, dict):
        raise TypeError(f"{method_name}() must return a JSON object")
    return data


def _native_json_list(native: Any, method_name: str, *args: Any) -> list[JsonObject]:
    data = _native_json_data(native, method_name, *args)
    if not isinstance(data, list):
        raise TypeError(f"{method_name}() must return a JSON array")
    return [dict(item) for item in data if isinstance(item, Mapping)]


def _explorer_request(
    seed_id: str,
    *,
    expanded_parents: Iterable[str] | None = None,
    expanded_children: Iterable[str] | None = None,
    include_reference_edges: bool | None = None,
) -> JsonObject:
    request: JsonObject = {
        "seed_id": seed_id,
        "expanded_parents": list(expanded_parents or ()),
        "expanded_children": list(expanded_children or ()),
    }
    if include_reference_edges is not None:
        request["include_reference_edges"] = include_reference_edges
    return request


def _view_document(kind: str, parameters: Mapping[str, Any]) -> JsonObject:
    return {
        "schema": "mercurio.view.v1",
        "version": 1,
        "kind": kind,
        "mode": "visualization",
        "parameters": dict(parameters),
    }


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
                "declared_name": ref.declared_name,
                "kind": ref.kind,
                "owner": ref.owner(),
                "type": ref.type_name(),
                "model_layer": ref.model_layer,
                "metatype_name": ref.metatype_name,
                "metatype_chain": ref.metatype_chain,
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

    def model_metadata(self) -> JsonObject:
        return _native_json_object(self._native_model, "model_metadata_json")

    def graph_view(self, scope: str = "l2") -> JsonObject:
        return _native_json_object(self._native_model, "graph_view_json", scope)

    def search(self, query: str) -> list[JsonObject]:
        return _native_json_list(self._native_model, "search_json", query)

    def element_details(self, element_id: str) -> JsonObject:
        return _native_json_object(self._native_model, "element_details_json", element_id)

    def l2_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: Iterable[str] | None = None,
        expanded_children: Iterable[str] | None = None,
        include_reference_edges: bool = True,
    ) -> JsonObject:
        request = _explorer_request(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
            include_reference_edges=include_reference_edges,
        )
        return _native_json_object(
            self._native_model,
            "l2_explorer_json",
            _canonical_json(request),
        )

    def metatype_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: Iterable[str] | None = None,
        expanded_children: Iterable[str] | None = None,
    ) -> JsonObject:
        request = _explorer_request(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
        )
        return _native_json_object(
            self._native_model,
            "metatype_explorer_json",
            _canonical_json(request),
        )

    def render_view(self, document: Mapping[str, Any]) -> JsonObject:
        kind = str(document.get("kind") or "")
        parameters = document.get("parameters")
        if not isinstance(parameters, Mapping):
            parameters = {}
        if kind == "explorer.l2":
            explorer = self.l2_explorer(
                str(parameters.get("seedId") or parameters.get("seed_id") or ""),
                expanded_parents=parameters.get("expandedParents") or parameters.get("expanded_parents") or (),
                expanded_children=parameters.get("expandedChildren") or parameters.get("expanded_children") or (),
                include_reference_edges=bool(
                    parameters.get("includeReferenceEdges", parameters.get("include_reference_edges", True))
                ),
            )
            return {"kind": kind, "document": dict(document), "l2Explorer": explorer}
        if kind == "explorer.metatype":
            explorer = self.metatype_explorer(
                str(parameters.get("seedId") or parameters.get("seed_id") or ""),
                expanded_parents=parameters.get("expandedParents") or parameters.get("expanded_parents") or (),
                expanded_children=parameters.get("expandedChildren") or parameters.get("expanded_children") or (),
            )
            return {"kind": kind, "document": dict(document), "metatypeExplorer": explorer}
        raise RuntimeError(
            "native render_view() currently supports parameterized explorer.l2 "
            "and explorer.metatype views; use a sidecar-backed model for full "
            "view rendering"
        )

    def run_cell(
        self,
        source: str,
        *,
        kind: str = "query",
        language: str | None = "mercurio_dsl",
        parameters: Mapping[str, Any] | None = None,
        cell_id: str | None = None,
        session_id: str | None = None,
    ) -> CellRunReport:
        if not hasattr(self._native_model, "run_cell_json"):
            raise RuntimeError(
                "cell execution requires the native Mercurio model; compile through "
                "the native Python package before calling run_cell()"
            )
        request = _cell_request(
            source,
            kind=kind,
            language=language,
            parameters=parameters,
            cell_id=cell_id,
            session_id=session_id,
        )
        return _cell_report_from_json(self._native_model.run_cell_json(_canonical_json(request)))

    def dsl(self, source: str) -> Any:
        """Run a Mercurio DSL query/action-preview expression against this revision."""
        return self.run_cell(source, kind="query", language="mercurio_dsl").result

    def query_dsl(self, source: str) -> Any:
        return self.dsl(source)

    def run_action_dsl(
        self,
        source: str,
        *,
        cell_id: str | None = None,
        session_id: str | None = None,
    ) -> CellRunReport:
        return self.run_cell(
            source,
            kind="action",
            language="mercurio_dsl",
            cell_id=cell_id,
            session_id=session_id,
        )

    def action_dsl(self, source: str) -> Any:
        return self.run_action_dsl(source).result

    def preview_dsl(self, source: str) -> Any:
        return self.action_dsl(source)

    def run_analysis_dsl(
        self,
        source: str,
        *,
        run_id: str | None = None,
        capability_id: str = "mercurio.dsl.analysis",
        subject_element_id: str | None = None,
        cell_id: str | None = None,
        session_id: str | None = None,
    ) -> CellRunReport:
        parameters: JsonObject = {"capabilityId": capability_id}
        if run_id is not None:
            parameters["runId"] = run_id
        if subject_element_id is not None:
            parameters["subjectElementId"] = subject_element_id
        return self.run_cell(
            source,
            kind="analysis",
            language="mercurio_dsl",
            parameters=parameters,
            cell_id=cell_id,
            session_id=session_id,
        )

    def analysis_dsl(
        self,
        source: str,
        *,
        run_id: str | None = None,
        capability_id: str = "mercurio.dsl.analysis",
        subject_element_id: str | None = None,
    ) -> JsonObject:
        report = self.run_analysis_dsl(
            source,
            run_id=run_id,
            capability_id=capability_id,
            subject_element_id=subject_element_id,
        )
        if report.capability_report is not None:
            return dict(report.capability_report)
        value = report.output("capability_report").get("value")
        if isinstance(value, dict):
            return value
        raise TypeError("analysis DSL cell did not return a capability report")

    def dsl_schema(self) -> JsonObject:
        if not hasattr(self._native_model, "dsl_schema_json"):
            raise RuntimeError(
                "DSL schema inspection requires the native Mercurio model"
            )
        data = json.loads(self._native_model.dsl_schema_json())
        if not isinstance(data, dict):
            raise TypeError("DSL schema must be a JSON object")
        return data

    def preview_transaction(self, request: Mapping[str, Any]) -> JsonObject:
        if not hasattr(self._native_model, "preview_transaction_json"):
            raise RuntimeError(
                "transaction preview requires the native Mercurio model"
            )
        return _native_json_object(
            self._native_model,
            "preview_transaction_json",
            _canonical_json(dict(request)),
        )

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


class TransactionBuilder:
    """Fluent Python facade for semantic transaction preview and source edits."""

    def __init__(self, owner: Any, label: str) -> None:
        self._owner = owner
        self.label = label
        self._operations: list[tuple[str, tuple[Any, ...]]] = []

    def rename(self, element: Any, new_name: str) -> "TransactionBuilder":
        self._operations.append(("rename", (_as_qualified_name(element), new_name)))
        return self

    def set_attribute(self, element: Any, attribute: str, value: Any) -> "TransactionBuilder":
        self._operations.append(
            ("set_attribute", (_as_qualified_name(element), attribute, value))
        )
        return self

    def to_dict(self) -> JsonObject:
        actions: list[JsonObject] = []
        for kind, args in self._operations:
            if kind == "rename":
                element, new_name = args
                actions.append({
                    "kind": "rename_declaration",
                    "element": element,
                    "new_name": new_name,
                })
            elif kind == "set_attribute":
                element, attribute, value = args
                actions.append({
                    "kind": "set_attribute",
                    "element": element,
                    "attribute": attribute,
                    "value": value,
                })
        return {"label": self.label, "actions": actions}

    def preview(self) -> JsonObject:
        return self._owner.compile().preview_transaction(self.to_dict())

    def apply(self) -> Any:
        for kind, args in self._operations:
            if kind == "rename":
                element, new_name = args
                self._owner.edit(element).rename(new_name)
            elif kind == "set_attribute":
                element, attribute, value = args
                self._owner.edit(element).set_attribute(attribute, value)
        return getattr(self._owner, "_variant", self._owner)


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

    def transaction(self, label: str) -> TransactionBuilder:
        return TransactionBuilder(self, label)

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

    def run_cell(
        self,
        source: str,
        *,
        kind: str = "query",
        language: str | None = "mercurio_dsl",
        parameters: Mapping[str, Any] | None = None,
        cell_id: str | None = None,
        session_id: str | None = None,
    ) -> CellRunReport:
        return self.compile().run_cell(
            source,
            kind=kind,
            language=language,
            parameters=parameters,
            cell_id=cell_id,
            session_id=session_id,
        )

    def dsl(self, source: str) -> Any:
        return self.run_cell(source, kind="query", language="mercurio_dsl").result

    def query(self, source: str) -> Any:
        return self.dsl(source)

    def query_dsl(self, source: str) -> Any:
        return self.dsl(source)

    def run_action_dsl(
        self,
        source: str,
        *,
        cell_id: str | None = None,
        session_id: str | None = None,
    ) -> CellRunReport:
        return self.compile().run_action_dsl(
            source,
            cell_id=cell_id,
            session_id=session_id,
        )

    def action_dsl(self, source: str) -> Any:
        return self.run_action_dsl(source).result

    def preview_dsl(self, source: str) -> Any:
        return self.action_dsl(source)

    def run_analysis_dsl(
        self,
        source: str,
        *,
        run_id: str | None = None,
        capability_id: str = "mercurio.dsl.analysis",
        subject_element_id: str | None = None,
        cell_id: str | None = None,
        session_id: str | None = None,
    ) -> CellRunReport:
        return self.compile().run_analysis_dsl(
            source,
            run_id=run_id,
            capability_id=capability_id,
            subject_element_id=subject_element_id,
            cell_id=cell_id,
            session_id=session_id,
        )

    def analysis_dsl(
        self,
        source: str,
        *,
        run_id: str | None = None,
        capability_id: str = "mercurio.dsl.analysis",
        subject_element_id: str | None = None,
    ) -> JsonObject:
        return self.compile().analysis_dsl(
            source,
            run_id=run_id,
            capability_id=capability_id,
            subject_element_id=subject_element_id,
        )

    def dsl_schema(self) -> JsonObject:
        return self.compile().dsl_schema()

    def model_metadata(self) -> JsonObject:
        return self.compile().model_metadata()

    def graph_view(self, scope: str = "l2") -> JsonObject:
        return self.compile().graph_view(scope)

    def search(self, query: str) -> list[JsonObject]:
        return self.compile().search(query)

    def element_details(self, element_id: str) -> JsonObject:
        return self.compile().element_details(element_id)

    def l2_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: Iterable[str] | None = None,
        expanded_children: Iterable[str] | None = None,
        include_reference_edges: bool = True,
    ) -> JsonObject:
        return self.compile().l2_explorer(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
            include_reference_edges=include_reference_edges,
        )

    def metatype_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: Iterable[str] | None = None,
        expanded_children: Iterable[str] | None = None,
    ) -> JsonObject:
        return self.compile().metatype_explorer(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
        )

    def render_view(self, document: Mapping[str, Any]) -> JsonObject:
        return self.compile().render_view(document)

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


class _StaleTolerantVariant:
    def __init__(self, variant: "Variant") -> None:
        self._variant = variant

    def edit(self, target: Any) -> SmallEdit:
        return self._variant.edit(target)

    def compile(self) -> CompiledModel:
        return self._variant.compile(allow_stale_base=True)


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

    def transaction(self, label: str, *, allow_stale_base: bool = False) -> TransactionBuilder:
        if allow_stale_base:
            return TransactionBuilder(_StaleTolerantVariant(self), label)
        return TransactionBuilder(self, label)

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

    def run_cell(
        self,
        source: str,
        *,
        kind: str = "query",
        language: str | None = "mercurio_dsl",
        parameters: Mapping[str, Any] | None = None,
        cell_id: str | None = None,
        session_id: str | None = None,
        allow_stale_base: bool = False,
    ) -> CellRunReport:
        return self.compile(allow_stale_base=allow_stale_base).run_cell(
            source,
            kind=kind,
            language=language,
            parameters=parameters,
            cell_id=cell_id,
            session_id=session_id,
        )

    def dsl(self, source: str, *, allow_stale_base: bool = False) -> Any:
        return self.run_cell(
            source,
            kind="query",
            language="mercurio_dsl",
            allow_stale_base=allow_stale_base,
        ).result

    def query(self, source: str, *, allow_stale_base: bool = False) -> Any:
        return self.dsl(source, allow_stale_base=allow_stale_base)

    def query_dsl(self, source: str, *, allow_stale_base: bool = False) -> Any:
        return self.dsl(source, allow_stale_base=allow_stale_base)

    def run_action_dsl(
        self,
        source: str,
        *,
        cell_id: str | None = None,
        session_id: str | None = None,
        allow_stale_base: bool = False,
    ) -> CellRunReport:
        return self.compile(allow_stale_base=allow_stale_base).run_action_dsl(
            source,
            cell_id=cell_id,
            session_id=session_id,
        )

    def action_dsl(self, source: str, *, allow_stale_base: bool = False) -> Any:
        return self.run_action_dsl(source, allow_stale_base=allow_stale_base).result

    def preview_dsl(self, source: str, *, allow_stale_base: bool = False) -> Any:
        return self.action_dsl(source, allow_stale_base=allow_stale_base)

    def run_analysis_dsl(
        self,
        source: str,
        *,
        run_id: str | None = None,
        capability_id: str = "mercurio.dsl.analysis",
        subject_element_id: str | None = None,
        cell_id: str | None = None,
        session_id: str | None = None,
        allow_stale_base: bool = False,
    ) -> CellRunReport:
        return self.compile(allow_stale_base=allow_stale_base).run_analysis_dsl(
            source,
            run_id=run_id,
            capability_id=capability_id,
            subject_element_id=subject_element_id,
            cell_id=cell_id,
            session_id=session_id,
        )

    def analysis_dsl(
        self,
        source: str,
        *,
        run_id: str | None = None,
        capability_id: str = "mercurio.dsl.analysis",
        subject_element_id: str | None = None,
        allow_stale_base: bool = False,
    ) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).analysis_dsl(
            source,
            run_id=run_id,
            capability_id=capability_id,
            subject_element_id=subject_element_id,
        )

    def dsl_schema(self, *, allow_stale_base: bool = False) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).dsl_schema()

    def model_metadata(self, *, allow_stale_base: bool = False) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).model_metadata()

    def graph_view(self, scope: str = "l2", *, allow_stale_base: bool = False) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).graph_view(scope)

    def search(self, query: str, *, allow_stale_base: bool = False) -> list[JsonObject]:
        return self.compile(allow_stale_base=allow_stale_base).search(query)

    def element_details(self, element_id: str, *, allow_stale_base: bool = False) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).element_details(element_id)

    def l2_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: Iterable[str] | None = None,
        expanded_children: Iterable[str] | None = None,
        include_reference_edges: bool = True,
        allow_stale_base: bool = False,
    ) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).l2_explorer(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
            include_reference_edges=include_reference_edges,
        )

    def metatype_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: Iterable[str] | None = None,
        expanded_children: Iterable[str] | None = None,
        allow_stale_base: bool = False,
    ) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).metatype_explorer(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
        )

    def render_view(
        self,
        document: Mapping[str, Any],
        *,
        allow_stale_base: bool = False,
    ) -> JsonObject:
        return self.compile(allow_stale_base=allow_stale_base).render_view(document)

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
