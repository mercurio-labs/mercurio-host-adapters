from __future__ import annotations

from .client import MercurioClient
from .models import (
    AnalysisOpportunityReport,
    AnalysisRunReport,
    JsonObject,
    PartRef,
    ProjectInfo,
    SemanticProjectResult,
)


class MercurioProject:
    """Project-scoped implementation API."""

    def __init__(self, client: MercurioClient, info: ProjectInfo):
        self.client = client
        self.info = info

    @property
    def project_id(self) -> str:
        return self.info.project_id

    @property
    def workspace_id(self) -> str:
        return self.project_id

    def model(self) -> JsonObject:
        return self.client.get(self._path("/model"))

    def graph(self, *, scope: str | None = None) -> JsonObject:
        query = {"scope": scope} if scope else None
        return self.client.get(self._path("/graph"), query=query)

    def element(self, element_id: str) -> JsonObject:
        return self.client.get(self._path(f"/elements/{element_id}"))

    def search(self, query_text: str) -> list[JsonObject]:
        return self.client.get(self._path("/search"), query={"q": query_text})

    def render_view(self, document: JsonObject) -> JsonObject:
        return self.client.post(self._path("/views/render"), document)

    def l2_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: list[str] | None = None,
        expanded_children: list[str] | None = None,
        include_reference_edges: bool = True,
    ) -> JsonObject:
        response = self.render_view(
            _view_document(
                "explorer.l2",
                {
                    "seedId": seed_id,
                    "expandedParents": list(expanded_parents or ()),
                    "expandedChildren": list(expanded_children or ()),
                    "includeReferenceEdges": include_reference_edges,
                },
            )
        )
        explorer = response.get("l2Explorer")
        if not isinstance(explorer, dict):
            raise RuntimeError("L2 explorer view did not return l2Explorer")
        return explorer

    def metatype_explorer(
        self,
        seed_id: str,
        *,
        expanded_parents: list[str] | None = None,
        expanded_children: list[str] | None = None,
    ) -> JsonObject:
        response = self.render_view(
            _view_document(
                "explorer.metatype",
                {
                    "seedId": seed_id,
                    "expandedParents": list(expanded_parents or ()),
                    "expandedChildren": list(expanded_children or ()),
                },
            )
        )
        explorer = response.get("metatypeExplorer")
        if not isinstance(explorer, dict):
            raise RuntimeError("metatype explorer view did not return metatypeExplorer")
        return explorer

    def mounted_library_trees(self) -> list[JsonObject]:
        data = self.client.get(self._path("/library/mounted-trees"))
        if not isinstance(data, list):
            raise TypeError("mounted library trees response must be a JSON array")
        return [dict(item) for item in data if isinstance(item, dict)]

    def files(self) -> JsonObject:
        return self.client.get(self._path("/editor/files"))

    def read_file(self, path: str) -> JsonObject:
        return self.client.get(self._path("/editor/file"), query={"path": path})

    def save_file(self, path: str, content: str) -> None:
        self.client.put(
            self._path("/editor/file"),
            {"content": content},
            query={"path": path},
        )

    def parse_preview(self, path: str, content: str) -> JsonObject:
        return self.client.post(
            self._path("/editor/parse"),
            {"path": path, "content": content},
        )

    def compile_file_preview(self, path: str, content: str) -> JsonObject:
        return self.client.post(
            self._path("/editor/semantic-compile"),
            {"path": path, "content": content},
        )

    def lint_preview(self, path: str, content: str) -> JsonObject:
        return self.client.post(
            self._path("/editor/lint"),
            {"path": path, "content": content},
        )

    def format_preview(self, path: str, content: str) -> JsonObject:
        return self.client.post(
            self._path("/editor/format"),
            {"path": path, "content": content},
        )

    def refresh(self, path: str) -> JsonObject:
        return self.client.post(self._path("/editor/refresh"), {"path": path})

    def workspace_session(self) -> JsonObject:
        return self.client.get(self._path("/semantic/workspace-session"))

    def check_semantic_legality(
        self,
        operation: JsonObject,
        *,
        facts: list[JsonObject] | None = None,
    ) -> JsonObject:
        return self.client.post(
            self._path("/semantic/legality/check"),
            {"operation": operation, "facts": list(facts or ())},
        )

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
        payload: JsonObject = {
            "elementKind": element_kind,
            "candidateTargetKinds": list(candidate_target_kinds or ()),
            "candidateAttributes": list(candidate_attributes or ()),
            "facts": list(facts or ()),
        }
        if element is not None:
            payload["element"] = {"qualified_name": element}
        if max_actions is not None:
            payload["maxActions"] = max_actions
        return self.client.post(self._path("/semantic/next-actions"), payload)

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

    def run_cell(self, request: JsonObject) -> JsonObject:
        return self.client.post(self._path("/session/cells/run"), request)

    def dsl_query(self, source: str) -> JsonObject:
        report = self.run_cell({
            "kind": "query",
            "language": "mercurio_dsl",
            "source": source,
            "parameters": {},
        })
        for output in report.get("outputs", []):
            if output.get("id") == "result":
                return output.get("value")
        raise RuntimeError("DSL query cell did not return a result output")

    def dsl_action(self, source: str) -> JsonObject:
        report = self.run_cell({
            "kind": "action",
            "language": "mercurio_dsl",
            "source": source,
            "parameters": {},
        })
        for output in report.get("outputs", []):
            if output.get("id") == "result":
                value = output.get("value")
                if isinstance(value, dict):
                    return value
                return {"value": value}
        raise RuntimeError("DSL action cell did not return a result output")

    def action_dsl(self, source: str) -> JsonObject:
        return self.dsl_action(source)

    def dsl_schema(self) -> JsonObject:
        return self.client.get(self._path("/dsl/schema"))

    def compile_project(
        self,
        project_path: str = ".",
        *,
        staged_files: dict[str, str] | None = None,
    ) -> SemanticProjectResult:
        return self.compile_project_preview(project_path, staged_files=staged_files)

    def compile_project_preview(
        self,
        project_path: str = ".",
        *,
        staged_files: dict[str, str] | None = None,
    ) -> SemanticProjectResult:
        payload = {
            "project_path": project_path,
            "staged_files": self._staged_files(staged_files),
        }
        return SemanticProjectResult(
            self.client.post(self._path("/semantic/project/compile"), payload)
        )

    def lint_project_preview(
        self,
        project_path: str = ".",
        *,
        staged_files: dict[str, str] | None = None,
    ) -> JsonObject:
        payload = {
            "project_path": project_path,
            "staged_files": self._staged_files(staged_files),
        }
        return self.client.post(self._path("/semantic/project/lint"), payload)

    def list_analysis_specs(self) -> list["AnalysisSpec"]:
        from .models import AnalysisSpec

        data = self.client.get(self._path("/analysis/specs"))
        return [AnalysisSpec.from_json(item) for item in data]

    def list_analysis_cases(self) -> list["AnalysisCaseInfo"]:
        from .models import AnalysisCaseInfo

        data = self.client.get(self._path("/analysis/cases"))
        return [AnalysisCaseInfo.from_json(item) for item in data]

    def analysis_opportunities(self) -> AnalysisOpportunityReport:
        data = self.client.get(self._path("/analysis/opportunities"))
        return AnalysisOpportunityReport.from_json(data)

    def run_analysis_report(
        self, case_id: str, *, run_id: str | None = None
    ) -> AnalysisRunReport:
        payload: JsonObject = {"id": case_id}
        if run_id is not None:
            payload["runId"] = run_id
        data = self.client.post(
            self._path("/analysis/cases/run"),
            payload,
        )
        return AnalysisRunReport.from_json(data)

    def run_analysis(self, case_id: str) -> "SimulationTrace":
        return self.run_analysis_report(case_id).simulation_trace()

    def parts(self) -> list[PartRef]:
        items = self.client.get(self._path("/parts"))
        items_sorted = sorted(items, key=lambda x: x.get("depth", 0))
        lookup: dict[str, PartRef] = {}
        for item in items_sorted:
            ref = PartRef.from_json(item, lookup)
            lookup[ref.id] = ref
        return list(lookup.values())

    def close(self) -> None:
        self.client.delete_project(self.project_id)

    def _path(self, suffix: str) -> str:
        return f"/api/workspaces/{self.project_id}{suffix}"

    @staticmethod
    def _staged_files(staged_files: dict[str, str] | None) -> list[JsonObject]:
        if not staged_files:
            return []
        return [
            {"path": path, "content": content}
            for path, content in staged_files.items()
        ]


def _view_document(kind: str, parameters: JsonObject) -> JsonObject:
    return {
        "schema": "mercurio.view.v1",
        "version": 1,
        "kind": kind,
        "mode": "visualization",
        "parameters": dict(parameters),
    }


MercurioWorkspace = MercurioProject
