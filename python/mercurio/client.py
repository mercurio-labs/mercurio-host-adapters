from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import MercurioBackendError
from .models import JsonObject, ProjectInfo, SysmlReleaseInfo, VersionInfo


class MercurioClient:
    """Low-level HTTP client for a Mercurio backend."""

    def __init__(self, base_url: str, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> JsonObject:
        return self.get("/api/health")

    def version(self) -> VersionInfo:
        return VersionInfo.from_json(self.get("/api/version"))

    def list_sysml_releases(self) -> list[SysmlReleaseInfo]:
        payload = self.get("/api/releases/sysml")
        return [
            SysmlReleaseInfo.from_json(item)
            for item in payload.get("releases", [])
        ]

    def resolve_sysml_release(self, selector: str) -> SysmlReleaseInfo:
        for release in self.list_sysml_releases():
            if release.matches(selector):
                return release
        raise ValueError(f"unknown SysML release selector: {selector}")

    def open_project(self, path: str, *, mode: str = "lazy") -> ProjectInfo:
        return ProjectInfo.from_open_json(
            self.post("/api/workspaces", {"path": path, "mode": mode})
        )

    def open_workspace(self, path: str, *, mode: str = "lazy") -> ProjectInfo:
        return self.open_project(path, mode=mode)

    def list_projects(self) -> list[ProjectInfo]:
        return [
            ProjectInfo.from_summary_json(item)
            for item in self.get("/api/workspaces")
        ]

    def list_workspaces(self) -> list[ProjectInfo]:
        return self.list_projects()

    def delete_project(self, project_id: str) -> None:
        self.delete(f"/api/workspaces/{project_id}")

    def delete_workspace(self, workspace_id: str) -> None:
        self.delete_project(workspace_id)

    def check_semantic_legality(
        self,
        operation: JsonObject,
        *,
        facts: list[JsonObject] | None = None,
    ) -> JsonObject:
        return self.post(
            "/api/semantic/legality/check",
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
        return self.post("/api/semantic/next-actions", payload)

    def get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, query=query)

    def post(
        self,
        path: str,
        payload: JsonObject | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        return self._request("POST", path, payload=payload, query=query)

    def put(
        self,
        path: str,
        payload: JsonObject | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        return self._request("PUT", path, payload=payload, query=query)

    def delete(self, path: str, query: dict[str, Any] | None = None) -> Any:
        return self._request("DELETE", path, query=query)

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: JsonObject | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        body = None
        headers = {"accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["content-type"] = "application/json"

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            raise MercurioBackendError(error.code, message) from error
