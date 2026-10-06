from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

JsonObject = dict[str, Any]

FINDING_SEVERITIES = {"info", "warning", "error", "critical"}
REASONING_STATUSES = {"passed", "failed", "inconclusive", "error"}
EVIDENCE_NODE_KINDS = {
    "kir_element",
    "source_span",
    "fact",
    "rule",
    "analysis_run",
    "plugin",
    "artifact",
    "human_decision",
}
EVIDENCE_RELATIONS = {
    "supports",
    "derived_from",
    "produced_by",
    "consumed",
    "affects",
    "explains",
}


def require_object(data: Any, name: str) -> JsonObject:
    if not isinstance(data, dict):
        raise ValueError(f"{name} must be an object")
    return data


def require_string(data: JsonObject, key: str, name: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}.{key} must be a non-empty string")
    return value


def require_list(data: JsonObject, key: str, name: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{name}.{key} must be a list")
    return value


def validate_capability_descriptor(descriptor: JsonObject) -> None:
    require_object(descriptor, "capability descriptor")
    for key in ("id", "kind", "name", "version", "api_version"):
        require_string(descriptor, key, "capability")
    if not isinstance(descriptor.get("deterministic"), bool):
        raise ValueError("capability.deterministic must be a boolean")
    for key in ("input_artifact_kinds", "output_artifact_kinds"):
        values = require_list(descriptor, key, "capability")
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError(f"capability.{key} must contain only non-empty strings")


def validate_context(context: JsonObject) -> None:
    require_object(context, "context")
    require_string(context, "context_id", "context")
    if "kind" not in context:
        raise ValueError("context.kind is required")
    artifact = require_object(context.get("artifact"), "context.artifact")
    require_string(artifact, "artifact_key", "context.artifact")
    require_string(artifact, "kir_schema_version", "context.artifact")


@dataclass
class ElementRef:
    element_id: str
    qualified_name: str | None = None
    label: str | None = None

    def to_json(self) -> JsonObject:
        if not self.element_id:
            raise ValueError("element_ref.element_id must be a non-empty string")
        d: JsonObject = {"element_id": self.element_id}
        if self.qualified_name:
            d["qualified_name"] = self.qualified_name
        if self.label:
            d["label"] = self.label
        return d


@dataclass
class SourceSpanRef:
    file: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    def to_json(self) -> JsonObject:
        if not self.file:
            raise ValueError("source_span.file must be a non-empty string")
        return {
            "file": self.file,
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }


@dataclass
class Finding:
    id: str
    title: str
    severity: str  # "info" | "warning" | "error" | "critical"
    message: str
    elements: list[ElementRef] = field(default_factory=list)
    source_spans: list[SourceSpanRef] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def info(cls, id: str, title: str, message: str, **kwargs: Any) -> Finding:
        return cls(id=id, title=title, severity="info", message=message, **kwargs)

    @classmethod
    def warning(cls, id: str, title: str, message: str, **kwargs: Any) -> Finding:
        return cls(id=id, title=title, severity="warning", message=message, **kwargs)

    @classmethod
    def error(cls, id: str, title: str, message: str, **kwargs: Any) -> Finding:
        return cls(id=id, title=title, severity="error", message=message, **kwargs)

    @classmethod
    def critical(cls, id: str, title: str, message: str, **kwargs: Any) -> Finding:
        return cls(id=id, title=title, severity="critical", message=message, **kwargs)

    def to_json(self) -> JsonObject:
        if self.severity not in FINDING_SEVERITIES:
            raise ValueError(f"finding {self.id!r} has invalid severity {self.severity!r}")
        for key, value in (
            ("id", self.id),
            ("title", self.title),
            ("message", self.message),
        ):
            if not value:
                raise ValueError(f"finding.{key} must be a non-empty string")
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "message": self.message,
            "elements": [e.to_json() for e in self.elements],
            "source_spans": [s.to_json() for s in self.source_spans],
            "evidence_ids": self.evidence_ids,
            "properties": self.properties,
        }


@dataclass
class Artifact:
    id: str
    kind: str
    schema: str
    digest: str
    payload: Any
    element_refs: list[ElementRef] = field(default_factory=list)

    @classmethod
    def table(
        cls,
        id: str,
        schema: str,
        columns: list[str],
        rows: list[list[Any]],
        *,
        digest: str | None = None,
        element_refs: list[ElementRef] | None = None,
    ) -> Artifact:
        return cls(
            id=id,
            kind="table",
            schema=schema,
            digest=digest or f"computed:{id}",
            payload={"columns": columns, "rows": rows},
            element_refs=element_refs or [],
        )

    @classmethod
    def markdown(
        cls,
        id: str,
        content: str,
        *,
        digest: str | None = None,
    ) -> Artifact:
        return cls(
            id=id,
            kind="markdown",
            schema="mercurio.markdown.v1",
            digest=digest or f"computed:{id}",
            payload={"content": content},
        )

    def to_json(self) -> JsonObject:
        for key, value in (
            ("id", self.id),
            ("kind", self.kind),
            ("schema", self.schema),
            ("digest", self.digest),
        ):
            if not value:
                raise ValueError(f"artifact.{key} must be a non-empty string")
        return {
            "id": self.id,
            "kind": self.kind,
            "schema": self.schema,
            "digest": self.digest,
            "element_refs": [e.to_json() for e in self.element_refs],
            "payload": self.payload,
        }


@dataclass
class EvidenceNode:
    id: str
    kind: str  # "kir_element" | "fact" | "rule" | "analysis_run" | "plugin" | "artifact"
    label: str
    element_refs: list[ElementRef] = field(default_factory=list)
    source_spans: list[SourceSpanRef] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> JsonObject:
        if self.kind not in EVIDENCE_NODE_KINDS:
            raise ValueError(f"evidence node {self.id!r} has invalid kind {self.kind!r}")
        if not self.id or not self.label:
            raise ValueError("evidence node id and label must be non-empty strings")
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "element_refs": [e.to_json() for e in self.element_refs],
            "source_spans": [s.to_json() for s in self.source_spans],
            "properties": self.properties,
        }


@dataclass
class EvidenceEdge:
    source_id: str
    target_id: str
    relation: str  # "supports" | "derived_from" | "produced_by" | "consumed" | "affects" | "explains"

    def to_json(self) -> JsonObject:
        if self.relation not in EVIDENCE_RELATIONS:
            raise ValueError(f"evidence edge has invalid relation {self.relation!r}")
        if not self.source_id or not self.target_id:
            raise ValueError("evidence edge source_id and target_id must be non-empty strings")
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
        }


@dataclass
class EvidenceGraph:
    nodes: list[EvidenceNode] = field(default_factory=list)
    edges: list[EvidenceEdge] = field(default_factory=list)

    def to_json(self) -> JsonObject:
        return {
            "nodes": [n.to_json() for n in self.nodes],
            "edges": [e.to_json() for e in self.edges],
        }


@dataclass
class ReasoningReport:
    request_id: str
    capability_descriptor: JsonObject
    context: JsonObject
    status: str  # "passed" | "failed" | "inconclusive" | "error"
    findings: list[Finding] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    evidence: EvidenceGraph = field(default_factory=EvidenceGraph)

    @classmethod
    def passed(
        cls,
        request_id: str,
        capability_descriptor: JsonObject,
        context: JsonObject,
        *,
        findings: list[Finding] | None = None,
        artifacts: list[Artifact] | None = None,
        evidence: EvidenceGraph | None = None,
    ) -> ReasoningReport:
        return cls(
            request_id=request_id,
            capability_descriptor=capability_descriptor,
            context=context,
            status="passed",
            findings=findings or [],
            artifacts=artifacts or [],
            evidence=evidence or EvidenceGraph(),
        )

    @classmethod
    def failed(
        cls,
        request_id: str,
        capability_descriptor: JsonObject,
        context: JsonObject,
        *,
        findings: list[Finding] | None = None,
        artifacts: list[Artifact] | None = None,
        evidence: EvidenceGraph | None = None,
    ) -> ReasoningReport:
        return cls(
            request_id=request_id,
            capability_descriptor=capability_descriptor,
            context=context,
            status="failed",
            findings=findings or [],
            artifacts=artifacts or [],
            evidence=evidence or EvidenceGraph(),
        )

    @classmethod
    def inconclusive(
        cls,
        request_id: str,
        capability_descriptor: JsonObject,
        context: JsonObject,
        *,
        findings: list[Finding] | None = None,
        artifacts: list[Artifact] | None = None,
        evidence: EvidenceGraph | None = None,
    ) -> ReasoningReport:
        return cls(
            request_id=request_id,
            capability_descriptor=capability_descriptor,
            context=context,
            status="inconclusive",
            findings=findings or [],
            artifacts=artifacts or [],
            evidence=evidence or EvidenceGraph(),
        )

    def to_json(self) -> JsonObject:
        if self.status not in REASONING_STATUSES:
            raise ValueError(f"reasoning report has invalid status {self.status!r}")
        if not self.request_id:
            raise ValueError("reasoning report request_id must be a non-empty string")
        validate_capability_descriptor(self.capability_descriptor)
        validate_context(self.context)
        return {
            "request_id": self.request_id,
            "capability": self.capability_descriptor,
            "context": self.context,
            "status": self.status,
            "findings": [f.to_json() for f in self.findings],
            "artifacts": [a.to_json() for a in self.artifacts],
            "evidence": self.evidence.to_json(),
        }


@dataclass
class CapabilityRequest:
    request_id: str
    capability_id: str
    context: JsonObject
    focus: list[JsonObject]
    parameters: dict[str, Any]
    kir: JsonObject
    graph_facts: list[JsonObject]
    _descriptor: JsonObject = field(default_factory=dict, repr=False)
    kir_content_hash: str | None = field(default=None, repr=False)
    sub_reports: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_json(cls, data: JsonObject) -> CapabilityRequest:
        require_object(data, "capability request")
        request_id = data.get("request_id") or data.get("requestId")
        capability_id = data.get("capability_id") or data.get("capabilityId")
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("capability request request_id/requestId is required")
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise ValueError("capability request capability_id/capabilityId is required")
        context = require_object(data.get("context"), "capability request context")
        validate_context(context)
        focus = data.get("focus") or []
        if not isinstance(focus, list):
            raise ValueError("capability request focus must be a list")
        parameters = data.get("parameters") or data.get("request") or {}
        if not isinstance(parameters, dict):
            raise ValueError("capability request parameters/request must be an object")
        kir = data.get("kir") or {}
        if not isinstance(kir, dict):
            raise ValueError("capability request kir must be an object")
        graph_facts = data.get("graph_facts") or []
        if not isinstance(graph_facts, list):
            raise ValueError("capability request graph_facts must be a list")
        kir_content_hash = context.get("artifact", {}).get("kir_content_hash") if isinstance(context.get("artifact"), dict) else None
        if not isinstance(kir_content_hash, str):
            kir_content_hash = None
        sub_reports = data.get("sub_reports") or {}
        if not isinstance(sub_reports, dict):
            sub_reports = {}
        instance = cls(
            request_id=request_id,
            capability_id=capability_id,
            context=context,
            focus=focus,
            parameters=parameters,
            kir=kir,
            graph_facts=graph_facts,
        )
        instance.kir_content_hash = kir_content_hash
        instance.sub_reports = sub_reports
        return instance

    def param(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)

    def sub_report(self, capability_id: str) -> "JsonObject | None":
        """Return sub-report for a composed sub-capability, or None."""
        return self.sub_reports.get(capability_id)

    def report_passed(
        self,
        *,
        findings: list[Finding] | None = None,
        artifacts: list[Artifact] | None = None,
        evidence: EvidenceGraph | None = None,
    ) -> ReasoningReport:
        return ReasoningReport.passed(
            self.request_id,
            self._descriptor,
            self.context,
            findings=findings,
            artifacts=artifacts,
            evidence=evidence,
        )

    def report_failed(
        self,
        *,
        findings: list[Finding] | None = None,
        artifacts: list[Artifact] | None = None,
        evidence: EvidenceGraph | None = None,
    ) -> ReasoningReport:
        return ReasoningReport.failed(
            self.request_id,
            self._descriptor,
            self.context,
            findings=findings,
            artifacts=artifacts,
            evidence=evidence,
        )

    def report_inconclusive(
        self,
        *,
        findings: list[Finding] | None = None,
        artifacts: list[Artifact] | None = None,
        evidence: EvidenceGraph | None = None,
    ) -> ReasoningReport:
        return ReasoningReport.inconclusive(
            self.request_id,
            self._descriptor,
            self.context,
            findings=findings,
            artifacts=artifacts,
            evidence=evidence,
        )
