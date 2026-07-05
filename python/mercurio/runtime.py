from __future__ import annotations

import json

from .backend import Mercurio
from .models import (
    AnalysisCaseInfo,
    AnalysisOpportunityReport,
    AnalysisRunReport,
    AnalysisSpec,
    JsonObject,
    PartRef,
    SimulationTrace,
)
from .project import MercurioProject
from .session import (
    CellRunReport,
    _canonical_json,
    _cell_report_from_dict,
    _cell_report_from_json,
    _cell_request,
    _explorer_request,
    _model_view_document,
)


class RawWorkspace:
    """Escape hatch: direct access to the raw KIR-shaped HTTP responses."""

    def __init__(self, project: MercurioProject) -> None:
        self._project = project

    def graph(self, scope: str | None = None) -> JsonObject:
        return self._project.graph(scope=scope)

    def model(self) -> JsonObject:
        return self._project.model()

    def element(self, element_id: str) -> JsonObject:
        return self._project.element(element_id)


class NativeRawWorkspace:
    """Escape hatch for the in-process native workspace."""

    def __init__(self, workspace) -> None:
        self._workspace = workspace

    def graph(self, scope: str | None = None) -> JsonObject:
        if scope not in (None, "model"):
            raise ValueError("native raw graph only supports the default compiled graph scope")
        return json.loads(self._workspace.graph())

    def model(self):
        return json.loads(self._workspace.model())

    def element(self, element_id: str):
        element = self._workspace.element(element_id)
        if element is None:
            return None
        return json.loads(element.json())


class AnalysisHandle:
    """Small facade for running a named analysis case."""

    def __init__(self, model: "Model", name_or_id: str) -> None:
        self._model = model
        self.name_or_id = name_or_id

    def spec(self) -> AnalysisSpec:
        return self._model.analysis_case_spec(self.name_or_id)

    def run(self, *, run_id: str | None = None) -> AnalysisRunReport:
        try:
            case_id = self.spec().case_ref.element_id
        except KeyError:
            case_id = self.name_or_id
        return self._model.run_analysis_report(case_id, run_id=run_id)

    def trace(self, *, run_id: str | None = None) -> SimulationTrace:
        return self.run(run_id=run_id).simulation_trace()


class Model:
    """
    Single entry point for model inspection and simulation.

    Created by mercurio.open(path). Manages the backend process lifetime; use as
    a context manager or call close() explicitly.

        with mercurio.open(".") as model:
            trace = model.run_analysis("PrintSequence")
    """

    def __init__(self, backend: Mercurio, project: MercurioProject):
        self._backend = backend
        self._project = project
        self._workspace = None
        self.raw = RawWorkspace(project)

    @classmethod
    def from_native(cls, workspace) -> "Model":
        model = cls.__new__(cls)
        model._backend = None
        model._project = None
        model._workspace = workspace
        model.raw = NativeRawWorkspace(workspace)
        return model

    def parts(self) -> list[PartRef]:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            lookup: dict[str, PartRef] = {}
            result: list[PartRef] = []
            for part in workspace.parts():
                data = json.loads(part.json())
                ref = PartRef.from_json(data, lookup)
                lookup[ref.id] = ref
                result.append(ref)
            return result
        return self._project.parts()

    def part(self, name_or_id: str) -> PartRef:
        """Find a part by declared name or element id. Raises KeyError if not found."""
        for p in self.parts():
            if p.name == name_or_id or p.id == name_or_id:
                return p
        raise KeyError(f"No part with name or id {name_or_id!r}")

    def analysis_cases(self) -> list[AnalysisCaseInfo]:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return workspace.list_analysis_cases()
        return self._project.list_analysis_cases()

    def analysis_opportunities(self) -> AnalysisOpportunityReport:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None and hasattr(workspace, "analysis_opportunities_json"):
            return AnalysisOpportunityReport.from_json(
                json.loads(workspace.analysis_opportunities_json())
            )
        return self._project.analysis_opportunities()

    def analysis_specs(self) -> list[AnalysisSpec]:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            if hasattr(workspace, "analysis_specs_json"):
                return [
                    AnalysisSpec.from_json(item)
                    for item in _json_object_list(
                        workspace.analysis_specs_json(), "analysis specs"
                    )
                ]
            raise RuntimeError(
                "analysis specs are not available in this native workspace; "
                "open with an HTTP sidecar executable"
            )
        return self._project.list_analysis_specs()

    def analysis_case_spec(self, name_or_id: str) -> AnalysisSpec:
        for spec in self.analysis_specs():
            if (
                spec.case_ref.element_id == name_or_id
                or spec.case_ref.label == name_or_id
            ):
                return spec
        raise KeyError(f"No analysis spec with name or id {name_or_id!r}")

    def analysis(self, name_or_id: str) -> AnalysisHandle:
        """Return a small handle for inspecting or running one analysis case."""
        return AnalysisHandle(self, name_or_id)

    def run_analysis_report(
        self, case_id: str, *, run_id: str | None = None
    ) -> AnalysisRunReport:
        workspace = getattr(self, "_workspace", None)
        effective_run_id = run_id or "python.analysis_case"
        if workspace is not None:
            if hasattr(workspace, "analysis_run_json"):
                return AnalysisRunReport.from_json(
                    _json_object(
                        workspace.analysis_run_json(case_id, effective_run_id),
                        "analysis run report",
                    )
                )
            raise RuntimeError(
                "analysis execution is not available in this native workspace; "
                "open with an HTTP sidecar executable"
            )
        return self._project.run_analysis_report(case_id, run_id=run_id)

    def run_analysis(self, case_id: str) -> SimulationTrace:
        return self.run_analysis_report(case_id).simulation_trace()

    def model_metadata(self) -> JsonObject:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return _json_object(workspace.model_metadata_json(), "model metadata")
        return self._project.model()

    def graph(self, scope: str = "model") -> JsonObject:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return _json_object(workspace.graph_view_json(scope), "graph view")
        return self._project.graph(scope=scope)

    def search(self, query: str) -> list[JsonObject]:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return _json_object_list(workspace.search_json(query), "search")
        return self._project.search(query)

    def element_details(self, element_id: str) -> JsonObject:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return _json_object(workspace.element_details_json(element_id), "element details")
        return self._project.element(element_id)

    def library_tree(self) -> list[JsonObject]:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return _json_object_list(workspace.library_tree_json(), "library tree")
        response = self._project.render_view(
            _model_view_document("model.library_tree", "Library Tree")
        )
        tree = response.get("libraryTree")
        if not isinstance(tree, list):
            raise RuntimeError("Library tree view did not return libraryTree")
        return [dict(item) for item in tree if isinstance(item, dict)]

    def check_semantic_legality(
        self,
        operation: JsonObject,
        *,
        facts: list[JsonObject] | None = None,
    ) -> JsonObject:
        request = {"operation": operation, "facts": list(facts or ())}
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            if hasattr(workspace, "semantic_legality_json"):
                return _json_object(
                    workspace.semantic_legality_json(_canonical_json(request)),
                    "semantic legality report",
                )
            raise RuntimeError(
                "semantic legality requires the native Mercurio legality bridge; "
                "upgrade the native Python package or open with an HTTP sidecar"
            )
        return self._project.check_semantic_legality(operation, facts=facts)

    def semantic_next_actions(
        self,
        element_kind: str,
        *,
        element: str | None = None,
        candidate_target_kinds: list[str] | None = None,
        candidate_attributes: list[str] | None = None,
        facts: list[JsonObject] | None = None,
        max_actions: int | None = None,
    ) -> JsonObject:
        request: JsonObject = {
            "elementKind": element_kind,
            "candidateTargetKinds": list(candidate_target_kinds or ()),
            "candidateAttributes": list(candidate_attributes or ()),
            "facts": list(facts or ()),
        }
        if element is not None:
            request["element"] = {"qualified_name": element}
        if max_actions is not None:
            request["maxActions"] = max_actions
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            if hasattr(workspace, "semantic_next_actions_json"):
                return _json_object(
                    workspace.semantic_next_actions_json(_canonical_json(request)),
                    "semantic next actions report",
                )
            raise RuntimeError(
                "semantic next actions require the native Mercurio next-actions bridge; "
                "upgrade the native Python package or open with an HTTP sidecar"
            )
        return self._project.semantic_next_actions(
            element_kind,
            element=element,
            candidate_target_kinds=candidate_target_kinds,
            candidate_attributes=candidate_attributes,
            facts=facts,
            max_actions=max_actions,
        )

    def can_contain(self, container_kind: str, child_kind: str) -> JsonObject:
        return self.check_semantic_legality(
            {
                "kind": "containment",
                "containerKind": container_kind,
                "childKind": child_kind,
            }
        )

    def can_specialize(self, source_kind: str, target_kind: str) -> JsonObject:
        return self.check_semantic_legality(
            {
                "kind": "specialization",
                "sourceKind": source_kind,
                "targetKind": target_kind,
            }
        )

    def can_type_usage(self, usage_kind: str, definition_kind: str) -> JsonObject:
        return self.check_semantic_legality(
            {
                "kind": "usageTyping",
                "usageKind": usage_kind,
                "definitionKind": definition_kind,
            }
        )

    def can_relate(
        self,
        relationship_kind: str,
        source_kind: str,
        target_kind: str,
    ) -> JsonObject:
        return self.check_semantic_legality(
            {
                "kind": "relationship",
                "relationshipKind": relationship_kind,
                "sourceKind": source_kind,
                "targetKind": target_kind,
            }
        )

    def can_write_attribute(self, kind: str, attribute: str) -> JsonObject:
        return self.check_semantic_legality(
            {
                "kind": "attributeWrite",
                "elementKind": kind,
                "attribute": attribute,
            }
        )

    def model_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: list[str] | None = None,
        expanded_children: list[str] | None = None,
        include_reference_edges: bool = True,
    ) -> JsonObject:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            request = _explorer_request(
                seed_id,
                expanded_parents=expanded_parents,
                expanded_children=expanded_children,
                include_reference_edges=include_reference_edges,
            )
            return _json_object(
                workspace.model_explorer_json(_canonical_json(request)),
                "Model explorer",
            )
        return self._project.model_explorer(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
            include_reference_edges=include_reference_edges,
        )

    def metatype_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: list[str] | None = None,
        expanded_children: list[str] | None = None,
    ) -> JsonObject:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            request = _explorer_request(
                seed_id,
                expanded_parents=expanded_parents,
                expanded_children=expanded_children,
            )
            return _json_object(
                workspace.metatype_explorer_json(_canonical_json(request)),
                "metatype explorer",
            )
        return self._project.metatype_explorer(
            seed_id,
            expanded_parents=expanded_parents,
            expanded_children=expanded_children,
        )

    def render_view(self, document: JsonObject) -> JsonObject:
        workspace = getattr(self, "_workspace", None)
        if workspace is None:
            return self._project.render_view(document)
        kind = str(document.get("kind") or "")
        model = document.get("model")
        if not isinstance(model, dict):
            raise RuntimeError("native render_view() requires a typed model view payload")
        model_kind = str(model.get("kind") or "")
        if kind == "model.metadata" and model_kind == "metadata":
            return {"kind": kind, "document": dict(document), "modelMetadata": self.model_metadata()}
        if kind == "model.graph" and model_kind == "graph":
            return {
                "kind": kind,
                "document": dict(document),
                "graph": self.graph_view(str(model.get("graph_scope") or model.get("graphScope") or "model")),
            }
        if kind == "model.search" and model_kind == "search":
            return {"kind": kind, "document": dict(document), "search": self.search(str(model.get("query") or ""))}
        if kind == "model.element_details" and model_kind == "element_details":
            return {
                "kind": kind,
                "document": dict(document),
                "elementDetails": self.element_details(str(model.get("root") or "")),
            }
        if kind == "model.library_tree" and model_kind == "library_tree":
            return {"kind": kind, "document": dict(document), "libraryTree": self.library_tree()}
        if kind == "explorer.model" and model_kind == "model_explorer":
            explorer = self.model_explorer(
                str(model.get("root") or ""),
                expanded_parents=model.get("expandedParents") or model.get("expanded_parents") or [],
                expanded_children=model.get("expandedChildren") or model.get("expanded_children") or [],
                include_reference_edges=bool(
                    model.get("includeReferenceEdges", model.get("include_reference_edges", True))
                ),
            )
            return {"kind": kind, "document": dict(document), "modelExplorer": explorer}
        if kind == "explorer.metatype" and model_kind == "metatype_explorer":
            explorer = self.metatype_explorer(
                str(model.get("root") or ""),
                expanded_parents=model.get("expandedParents") or model.get("expanded_parents") or [],
                expanded_children=model.get("expandedChildren") or model.get("expanded_children") or [],
            )
            return {"kind": kind, "document": dict(document), "metatypeExplorer": explorer}
        raise RuntimeError(f"native render_view() does not support model view kind {kind!r}")

    def model_explorer_view(
        self,
        seed_id: str,
        *,
        expanded_parents: list[str] | None = None,
        expanded_children: list[str] | None = None,
        include_reference_edges: bool = True,
    ) -> JsonObject:
        return self.render_view(
            _model_view_document(
                "explorer.model",
                "Model Explorer",
                root=seed_id,
                expanded_parents=list(expanded_parents or ()),
                expanded_children=list(expanded_children or ()),
                include_reference_edges=include_reference_edges,
            )
        )

    def metatype_explorer_view(
        self,
        seed_id: str,
        *,
        expanded_parents: list[str] | None = None,
        expanded_children: list[str] | None = None,
    ) -> JsonObject:
        return self.render_view(
            _model_view_document(
                "explorer.metatype",
                "Metatype Explorer",
                root=seed_id,
                expanded_parents=list(expanded_parents or ()),
                expanded_children=list(expanded_children or ()),
            )
        )

    def semantic_snapshot_json(self) -> str:
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return workspace.compile().semantic_snapshot_json()
        raise RuntimeError(
            "semantic snapshots require the native workspace; open without an HTTP sidecar executable"
        )

    def run_cell(
        self,
        source: str,
        *,
        kind: str = "query",
        language: str | None = "mercurio_dsl",
        parameters: dict[str, object] | None = None,
        cell_id: str | None = None,
        session_id: str | None = None,
    ) -> CellRunReport:
        request = _cell_request(
            source,
            kind=kind,
            language=language,
            parameters=parameters,
            cell_id=cell_id,
            session_id=session_id,
        )
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            return _cell_report_from_json(workspace.run_cell_json(_canonical_json(request)))
        return _cell_report_from_dict(self._project.run_cell(request))

    def dsl(self, source: str) -> object:
        """Run a Mercurio DSL query/action-preview expression against the model."""
        return self.run_cell(source, kind="query", language="mercurio_dsl").result

    def query(self, source: str) -> object:
        """Run a Mercurio DSL query and return the result value."""
        return self.dsl(source)

    def query_dsl(self, source: str) -> object:
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

    def action_dsl(self, source: str) -> object:
        return self.run_action_dsl(source).result

    def preview_dsl(self, source: str) -> object:
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
        parameters: dict[str, object] = {"capabilityId": capability_id}
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
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            data = json.loads(workspace.dsl_schema_json())
            if not isinstance(data, dict):
                raise TypeError("DSL schema must be a JSON object")
            return data
        return self._project.dsl_schema()

    def close(self) -> None:
        if getattr(self, "_workspace", None) is not None:
            return
        self._project.close()
        self._backend.close()

    def __enter__(self) -> "Model":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


ModelRuntime = Model


def _json_object(raw: str, label: str) -> JsonObject:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError(f"{label} response must be a JSON object")
    return data


def _json_object_list(raw: str, label: str) -> list[JsonObject]:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError(f"{label} response must be a JSON array")
    return [dict(item) for item in data if isinstance(item, dict)]

