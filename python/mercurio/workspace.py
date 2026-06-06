from __future__ import annotations

from .client import MercurioClient
from .models import JsonObject, PartRef, SemanticProjectResult, WorkspaceInfo


class MercurioWorkspace:
    """Workspace-scoped convenience API."""

    def __init__(self, client: MercurioClient, info: WorkspaceInfo):
        self.client = client
        self.info = info

    @property
    def workspace_id(self) -> str:
        return self.info.workspace_id

    def model(self) -> JsonObject:
        return self.client.get(self._path("/model"))

    def graph(self, *, scope: str | None = None) -> JsonObject:
        query = {"scope": scope} if scope else None
        return self.client.get(self._path("/graph"), query=query)

    def element(self, element_id: str) -> JsonObject:
        return self.client.get(self._path(f"/elements/{element_id}"))

    def search(self, query_text: str) -> list[JsonObject]:
        return self.client.get(self._path("/search"), query={"q": query_text})

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

    def list_analysis_cases(self) -> list["AnalysisCaseInfo"]:
        from .models import AnalysisCaseInfo

        data = self.client.get(self._path("/simulation/analysis-cases"))
        return [AnalysisCaseInfo.from_json(item) for item in data]

    def run_analysis(self, case_id: str) -> "SimulationTrace":
        from .models import SimulationTrace

        data = self.client.post(
            self._path("/simulation/run-analysis"),
            {"id": case_id},
        )
        return SimulationTrace.from_json(data)

    def parts(self, *, scope: str = "l2") -> list[PartRef]:
        graph = self.graph(scope=scope)
        nodes = graph.get("nodes", [])
        part_kinds = ("PartUsage", "PartDefinition", "IndividualUsage")
        part_nodes = [
            node
            for node in nodes
            if any(kind in str(node.get("kind", "")) for kind in part_kinds)
        ]

        refs: dict[str, PartRef] = {}
        for node in part_nodes:
            node_id = str(node.get("id", node.get("elementId", "")))
            props = node.get("properties", {})
            name = str(
                props.get("declared_name")
                or props.get("name")
                or node_id.rsplit(".", 1)[-1]
            )
            kind = str(
                str(props.get("type", "")).rsplit(".", 1)[-1]
                or str(props.get("definition", "")).rsplit(".", 1)[-1]
                or node.get("kind", "")
            )
            refs[node_id] = PartRef(
                id=node_id,
                name=name,
                kind=kind,
                element_kind=str(node.get("kind", "")),
                parent=None,
                depth=0,
                _properties=props,
            )

        for node in part_nodes:
            node_id = str(node.get("id", node.get("elementId", "")))
            props = node.get("properties", {})
            owner_id = props.get("owner") or props.get("owning_type")
            if owner_id and owner_id in refs and node_id in refs:
                refs[node_id].parent = refs[str(owner_id)]

        def compute_depth(ref: PartRef) -> int:
            depth = 0
            current = ref
            seen: set[str] = set()
            while current.parent is not None and current.id not in seen:
                seen.add(current.id)
                depth += 1
                current = current.parent
            return depth

        for ref in refs.values():
            ref.depth = compute_depth(ref)

        result: list[PartRef] = []
        visited: set[str] = set()
        all_parts = list(refs.values())

        def visit(ref: PartRef) -> None:
            if ref.id in visited:
                return
            visited.add(ref.id)
            result.append(ref)
            for child in ref.children(all_parts):
                visit(child)

        for ref in all_parts:
            if ref.parent is None:
                visit(ref)

        return result

    def close(self) -> None:
        self.client.delete_workspace(self.workspace_id)

    def _path(self, suffix: str) -> str:
        return f"/api/workspaces/{self.workspace_id}{suffix}"

    @staticmethod
    def _staged_files(staged_files: dict[str, str] | None) -> list[JsonObject]:
        if not staged_files:
            return []
        return [
            {"path": path, "content": content}
            for path, content in staged_files.items()
        ]
