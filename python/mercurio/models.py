from __future__ import annotations

from dataclasses import dataclass
from typing import Any


JsonObject = dict[str, Any]


def _field(data: JsonObject, snake_name: str, camel_name: str, default: Any = None) -> Any:
    return data.get(snake_name, data.get(camel_name, default))


def _object_field(data: JsonObject, snake_name: str, camel_name: str) -> JsonObject:
    value = _field(data, snake_name, camel_name, {})
    return dict(value) if isinstance(value, dict) else {}


def _list_field(data: JsonObject, snake_name: str, camel_name: str) -> list[Any]:
    value = _field(data, snake_name, camel_name, [])
    return list(value) if isinstance(value, list) else []


@dataclass(frozen=True)
class VersionInfo:
    service: str
    version: str
    api_version: int

    @classmethod
    def from_json(cls, data: JsonObject) -> "VersionInfo":
        return cls(
            service=str(data["service"]),
            version=str(data["version"]),
            api_version=int(data["apiVersion"]),
        )


@dataclass(frozen=True)
class SysmlReleaseInfo:
    release: str | None
    selector: str
    profile_id: str
    status: str
    sysml_version: str
    pilot_release_tag: str | None
    pilot_implementation_version: str | None
    stdlib_locator: str
    python_wrapper_module: str | None
    aliases: list[str]

    @classmethod
    def from_json(cls, data: JsonObject) -> "SysmlReleaseInfo":
        return cls(
            release=data.get("release"),
            selector=str(data["selector"]),
            profile_id=str(data["profileId"]),
            status=str(data["status"]),
            sysml_version=str(data["sysmlVersion"]),
            pilot_release_tag=data.get("pilotReleaseTag"),
            pilot_implementation_version=data.get("pilotImplementationVersion"),
            stdlib_locator=str(data["stdlibLocator"]),
            python_wrapper_module=data.get("pythonWrapperModule"),
            aliases=[str(alias) for alias in data.get("aliases", [])],
        )

    def matches(self, selector: str) -> bool:
        return selector in {
            self.selector,
            self.profile_id,
            *(value for value in [self.release, self.pilot_release_tag] if value),
            *self.aliases,
        }


@dataclass(frozen=True)
class BackendStartupInfo:
    url: str
    pid: int
    version: str
    api_version: int

    @classmethod
    def from_json(cls, data: JsonObject) -> "BackendStartupInfo":
        return cls(
            url=str(data["url"]),
            pid=int(data["pid"]),
            version=str(data["version"]),
            api_version=int(data["apiVersion"]),
        )


@dataclass(frozen=True)
class ProjectInfo:
    project_id: str
    project_root: str | None
    active_path: str | None
    project: JsonObject | None

    @classmethod
    def from_open_json(cls, data: JsonObject) -> "ProjectInfo":
        return cls(
            project_id=str(data["workspaceId"]),
            project_root=data.get("workspaceRoot"),
            active_path=data.get("activePath"),
            project=data.get("project"),
        )

    @classmethod
    def from_summary_json(cls, data: JsonObject) -> "ProjectInfo":
        return cls(
            project_id=str(data["workspaceId"]),
            project_root=data.get("workspaceRoot"),
            active_path=data.get("activePath"),
            project=data.get("project"),
        )

    @property
    def workspace_id(self) -> str:
        return self.project_id

    @property
    def workspace_root(self) -> str | None:
        return self.project_root


WorkspaceInfo = ProjectInfo


@dataclass(frozen=True)
class SemanticProjectResult:
    data: JsonObject

    @property
    def ok(self) -> bool:
        return bool(self.data.get("ok"))

    @property
    def file_count(self) -> int:
        return int(self.data.get("file_count", self.data.get("fileCount", 0)))

    @property
    def success_count(self) -> int:
        return int(self.data.get("success_count", self.data.get("successCount", 0)))

    @property
    def failure_count(self) -> int:
        return int(self.data.get("failure_count", self.data.get("failureCount", 0)))

    @property
    def results(self) -> list[JsonObject]:
        value = self.data.get("results", [])
        return value if isinstance(value, list) else []

    def __repr__(self) -> str:
        return (
            "SemanticProjectResult("
            f"ok={self.ok}, files={self.file_count}, "
            f"success={self.success_count}, failure={self.failure_count})"
        )


@dataclass(frozen=True)
class AnalysisCaseInfo:
    id: str
    label: str
    subject_count: int

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisCaseInfo":
        return cls(
            id=str(data["id"]),
            label=str(data["label"]),
            subject_count=int(data.get("subject_count", data.get("subjectCount", 0))),
        )


@dataclass(frozen=True)
class SemanticElementRef:
    element_id: str
    qualified_name: str | None
    label: str | None
    kind: str | None

    @classmethod
    def from_json(cls, data: JsonObject) -> "SemanticElementRef":
        return cls(
            element_id=str(_field(data, "element_id", "elementId", "")),
            qualified_name=_field(data, "qualified_name", "qualifiedName"),
            label=data.get("label"),
            kind=data.get("kind"),
        )


AnalysisElementRef = SemanticElementRef


@dataclass(frozen=True)
class AnalysisOpportunity:
    id: str
    kind: str
    label: str
    description: str
    runnable: bool
    elements: list[AnalysisElementRef]
    techniques: list[str]
    capability_id: str | None
    action_id: str | None
    route_hint: str | None
    metadata: JsonObject

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisOpportunity":
        return cls(
            id=str(data.get("id", "")),
            kind=str(data.get("kind", "")),
            label=str(data.get("label", "")),
            description=str(data.get("description", "")),
            runnable=bool(data.get("runnable", False)),
            elements=[
                AnalysisElementRef.from_json(item)
                for item in _list_field(data, "elements", "elements")
                if isinstance(item, dict)
            ],
            techniques=[
                str(item) for item in _list_field(data, "techniques", "techniques")
            ],
            capability_id=_field(data, "capability_id", "capabilityId"),
            action_id=_field(data, "action_id", "actionId"),
            route_hint=_field(data, "route_hint", "routeHint"),
            metadata=_object_field(data, "metadata", "metadata"),
        )


@dataclass(frozen=True)
class AnalysisOpportunityReport:
    schema: str
    opportunities: list[AnalysisOpportunity]

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisOpportunityReport":
        return cls(
            schema=str(data.get("schema", "")),
            opportunities=[
                AnalysisOpportunity.from_json(item)
                for item in _list_field(data, "opportunities", "opportunities")
                if isinstance(item, dict)
            ],
        )

    def runnable(self) -> list[AnalysisOpportunity]:
        return [
            opportunity
            for opportunity in self.opportunities
            if opportunity.runnable
        ]


@dataclass(frozen=True)
class AnalysisExpectedArtifact:
    kind: str
    schema: str

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisExpectedArtifact":
        return cls(kind=str(data.get("kind", "")), schema=str(data.get("schema", "")))


@dataclass(frozen=True)
class AnalysisReadinessDiagnostic:
    severity: str
    code: str
    message: str
    element_id: str | None

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisReadinessDiagnostic":
        return cls(
            severity=str(data.get("severity", "")),
            code=str(data.get("code", "")),
            message=str(data.get("message", "")),
            element_id=_field(data, "element_id", "elementId"),
        )


@dataclass(frozen=True)
class AnalysisClockConfig:
    max_steps: int | None = None
    step_duration_s: float | None = None
    max_time_s: float | None = None
    fixed_step_s: float | None = None
    sample_interval_s: float | None = None
    change_loop_limit: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisClockConfig":
        max_steps = _field(data, "max_steps", "maxSteps")
        step_duration_s = _field(data, "step_duration_s", "stepDurationS")
        max_time_s = _field(data, "max_time_s", "maxTimeS")
        fixed_step_s = _field(data, "fixed_step_s", "fixedStepS")
        sample_interval_s = _field(data, "sample_interval_s", "sampleIntervalS")
        change_loop_limit = _field(data, "change_loop_limit", "changeLoopLimit")
        return cls(
            max_steps=int(max_steps) if max_steps is not None else None,
            step_duration_s=float(step_duration_s)
            if step_duration_s is not None
            else None,
            max_time_s=float(max_time_s) if max_time_s is not None else None,
            fixed_step_s=float(fixed_step_s) if fixed_step_s is not None else None,
            sample_interval_s=float(sample_interval_s)
            if sample_interval_s is not None
            else None,
            change_loop_limit=int(change_loop_limit)
            if change_loop_limit is not None
            else None,
        )


@dataclass(frozen=True)
class AnalysisExecutionContext:
    initial_values: dict[str, dict[str, Any]]
    clock: AnalysisClockConfig | None
    provider_bindings: JsonObject

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisExecutionContext":
        raw_initial_values = _object_field(data, "initial_values", "initialValues")
        initial_values = {
            str(subject_id): dict(values)
            for subject_id, values in raw_initial_values.items()
            if isinstance(values, dict)
        }
        raw_clock = _field(data, "clock", "clock")
        return cls(
            initial_values=initial_values,
            clock=AnalysisClockConfig.from_json(raw_clock)
            if isinstance(raw_clock, dict)
            else None,
            provider_bindings=_object_field(data, "provider_bindings", "providerBindings"),
        )


@dataclass(frozen=True)
class AnalysisExecutionStep:
    kind: str
    label: str
    techniques: list[str]
    elements: list[AnalysisElementRef]

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisExecutionStep":
        return cls(
            kind=str(data.get("kind", "")),
            label=str(data.get("label", "")),
            techniques=[str(value) for value in data.get("techniques", [])],
            elements=[
                AnalysisElementRef.from_json(item)
                for item in _list_field(data, "elements", "elements")
                if isinstance(item, dict)
            ],
        )


@dataclass(frozen=True)
class AnalysisExecutionPlan:
    steps: list[AnalysisExecutionStep]

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisExecutionPlan":
        return cls(
            steps=[
                AnalysisExecutionStep.from_json(item)
                for item in _list_field(data, "steps", "steps")
                if isinstance(item, dict)
            ]
        )


@dataclass(frozen=True)
class AnalysisDynamicBehaviorBinding:
    subject: AnalysisElementRef
    behavior: AnalysisElementRef
    kind: str

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisDynamicBehaviorBinding":
        return cls(
            subject=AnalysisElementRef.from_json(_object_field(data, "subject", "subject")),
            behavior=AnalysisElementRef.from_json(
                _object_field(data, "behavior", "behavior")
            ),
            kind=str(data.get("kind", "")),
        )


@dataclass(frozen=True)
class AnalysisSpec:
    case_ref: AnalysisElementRef
    model_revision: str
    subjects: list[AnalysisElementRef]
    inputs: list[AnalysisElementRef]
    assumptions: list[AnalysisElementRef]
    objectives: list[AnalysisElementRef]
    calculations: list[AnalysisElementRef]
    constraints: list[AnalysisElementRef]
    requirements: list[AnalysisElementRef]
    verification_cases: list[AnalysisElementRef]
    views: list[AnalysisElementRef]
    concerns: list[AnalysisElementRef]
    techniques: list[str]
    dynamic_behavior_bindings: list[AnalysisDynamicBehaviorBinding]
    execution_context: AnalysisExecutionContext
    execution_plan: AnalysisExecutionPlan
    expected_artifacts: list[AnalysisExpectedArtifact]
    readiness: str
    readiness_diagnostics: list[AnalysisReadinessDiagnostic]

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisSpec":
        return cls(
            case_ref=AnalysisElementRef.from_json(
                _object_field(data, "case_ref", "caseRef")
            ),
            model_revision=str(_field(data, "model_revision", "modelRevision", "")),
            subjects=_analysis_element_refs(data, "subjects", "subjects"),
            inputs=_analysis_element_refs(data, "inputs", "inputs"),
            assumptions=_analysis_element_refs(data, "assumptions", "assumptions"),
            objectives=_analysis_element_refs(data, "objectives", "objectives"),
            calculations=_analysis_element_refs(data, "calculations", "calculations"),
            constraints=_analysis_element_refs(data, "constraints", "constraints"),
            requirements=_analysis_element_refs(data, "requirements", "requirements"),
            verification_cases=_analysis_element_refs(
                data, "verification_cases", "verificationCases"
            ),
            views=_analysis_element_refs(data, "views", "views"),
            concerns=_analysis_element_refs(data, "concerns", "concerns"),
            techniques=[str(value) for value in data.get("techniques", [])],
            dynamic_behavior_bindings=[
                AnalysisDynamicBehaviorBinding.from_json(item)
                for item in _list_field(
                    data, "dynamic_behavior_bindings", "dynamicBehaviorBindings"
                )
                if isinstance(item, dict)
            ],
            execution_context=AnalysisExecutionContext.from_json(
                _object_field(data, "execution_context", "executionContext")
            ),
            execution_plan=AnalysisExecutionPlan.from_json(
                _object_field(data, "execution_plan", "executionPlan")
            ),
            expected_artifacts=[
                AnalysisExpectedArtifact.from_json(item)
                for item in _list_field(data, "expected_artifacts", "expectedArtifacts")
                if isinstance(item, dict)
            ],
            readiness=str(data.get("readiness", "")),
            readiness_diagnostics=[
                AnalysisReadinessDiagnostic.from_json(item)
                for item in _list_field(
                    data, "readiness_diagnostics", "readinessDiagnostics"
                )
                if isinstance(item, dict)
            ],
        )


@dataclass(frozen=True)
class SemanticArtifact:
    id: str
    kind: str
    schema: str
    digest: str
    element_refs: list[SemanticElementRef]
    payload: Any

    @classmethod
    def from_json(cls, data: JsonObject) -> "SemanticArtifact":
        return cls(
            id=str(data.get("id", "")),
            kind=str(data.get("kind", "")),
            schema=str(data.get("schema", "")),
            digest=str(data.get("digest", "")),
            element_refs=[
                SemanticElementRef.from_json(item)
                for item in _list_field(data, "element_refs", "elementRefs")
                if isinstance(item, dict)
            ],
            payload=data.get("payload"),
        )


@dataclass(frozen=True)
class EvidenceNode:
    id: str
    kind: str
    label: str
    element_refs: list[SemanticElementRef]
    properties: JsonObject

    @classmethod
    def from_json(cls, data: JsonObject) -> "EvidenceNode":
        return cls(
            id=str(data.get("id", "")),
            kind=str(data.get("kind", "")),
            label=str(data.get("label", "")),
            element_refs=[
                SemanticElementRef.from_json(item)
                for item in _list_field(data, "element_refs", "elementRefs")
                if isinstance(item, dict)
            ],
            properties=_object_field(data, "properties", "properties"),
        )


@dataclass(frozen=True)
class EvidenceEdge:
    source_id: str
    target_id: str
    relation: str

    @classmethod
    def from_json(cls, data: JsonObject) -> "EvidenceEdge":
        return cls(
            source_id=str(_field(data, "source_id", "sourceId", "")),
            target_id=str(_field(data, "target_id", "targetId", "")),
            relation=str(data.get("relation", "")),
        )


@dataclass(frozen=True)
class EvidenceGraph:
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]

    @classmethod
    def from_json(cls, data: JsonObject) -> "EvidenceGraph":
        return cls(
            nodes=[
                EvidenceNode.from_json(item)
                for item in _list_field(data, "nodes", "nodes")
                if isinstance(item, dict)
            ],
            edges=[
                EvidenceEdge.from_json(item)
                for item in _list_field(data, "edges", "edges")
                if isinstance(item, dict)
            ],
        )


@dataclass(frozen=True)
class SemanticDiagnostic:
    code: str
    severity: str
    message: str
    element: SemanticElementRef | None

    @classmethod
    def from_json(cls, data: JsonObject) -> "SemanticDiagnostic":
        raw_element = data.get("element")
        return cls(
            code=str(data.get("code", "")),
            severity=str(data.get("severity", "")),
            message=str(data.get("message", "")),
            element=SemanticElementRef.from_json(raw_element)
            if isinstance(raw_element, dict)
            else None,
        )


@dataclass(frozen=True)
class AnalysisRunReport:
    run_id: str
    capability_id: str
    status: str
    target: JsonObject
    insights: list[JsonObject]
    artifacts: list[SemanticArtifact]
    evidence: EvidenceGraph
    diagnostics: list[SemanticDiagnostic]
    limitations: list[str]

    @classmethod
    def from_json(cls, data: JsonObject) -> "AnalysisRunReport":
        return cls(
            run_id=str(_field(data, "run_id", "runId", "")),
            capability_id=str(_field(data, "capability_id", "capabilityId", "")),
            status=str(data.get("status", "")),
            target=_object_field(data, "target", "target"),
            insights=[
                dict(item)
                for item in _list_field(data, "insights", "insights")
                if isinstance(item, dict)
            ],
            artifacts=[
                SemanticArtifact.from_json(item)
                for item in _list_field(data, "artifacts", "artifacts")
                if isinstance(item, dict)
            ],
            evidence=EvidenceGraph.from_json(
                _object_field(data, "evidence", "evidence")
            ),
            diagnostics=[
                SemanticDiagnostic.from_json(item)
                for item in _list_field(data, "diagnostics", "diagnostics")
                if isinstance(item, dict)
            ],
            limitations=[str(value) for value in data.get("limitations", [])],
        )

    def artifact(self, kind: str) -> SemanticArtifact:
        for artifact in self.artifacts:
            if artifact.kind == kind:
                return artifact
        raise KeyError(f"No analysis artifact of kind {kind!r}")

    def simulation_trace(self) -> "SimulationTrace":
        artifact = self.artifact("simulation_trace")
        if not isinstance(artifact.payload, dict):
            raise ValueError("simulation_trace artifact payload is not an object")
        return SimulationTrace.from_json(artifact.payload)

    def constraint_summary(self) -> JsonObject:
        artifact = self.artifact("constraint_analysis_summary")
        if not isinstance(artifact.payload, dict):
            raise ValueError("constraint_analysis_summary artifact payload is not an object")
        return dict(artifact.payload)

    def activity_summary(self) -> JsonObject:
        artifact = self.artifact("activity_execution_summary")
        if not isinstance(artifact.payload, dict):
            raise ValueError("activity_execution_summary artifact payload is not an object")
        return dict(artifact.payload)


def _analysis_element_refs(
    data: JsonObject, snake_name: str, camel_name: str
) -> list[AnalysisElementRef]:
    return [
        AnalysisElementRef.from_json(item)
        for item in _list_field(data, snake_name, camel_name)
        if isinstance(item, dict)
    ]


@dataclass(frozen=True)
class TraceChannel:
    id: str
    unit: str | None
    source: str

    @classmethod
    def from_json(cls, data: JsonObject) -> "TraceChannel":
        return cls(
            id=str(data["id"]),
            unit=data.get("unit"),
            source=str(data.get("source", "assign_effect")),
        )


@dataclass(frozen=True)
class ChannelData:
    """Time-series view of a single channel extracted from a SimulationTrace."""

    channel_id: str
    times: list[float]
    values: list[Any]

    def as_pairs(self) -> list[tuple[float, Any]]:
        return list(zip(self.times, self.values))


@dataclass(frozen=True)
class StateData:
    """State sequence for one subject extracted from a SimulationTrace."""

    subject_id: str
    times: list[float]
    states: list[list[str]]


@dataclass(frozen=True)
class SimulationTrace:
    scenario_id: str
    subject_id: str
    channels: list[TraceChannel]
    status: str
    _timeline: list[JsonObject]

    @classmethod
    def from_json(cls, data: JsonObject) -> "SimulationTrace":
        return cls(
            scenario_id=str(data["scenario_id"]),
            subject_id=str(data["subject_id"]),
            channels=[TraceChannel.from_json(c) for c in data.get("channels", [])],
            status=str(data.get("status", "completed")),
            _timeline=list(data.get("timeline", [])),
        )

    def channel(self, channel_id: str) -> ChannelData:
        """Return time-series for one channel, e.g. 'bed.temperature'."""
        times: list[float] = []
        values: list[Any] = []
        for entry in self._timeline:
            raw_values = entry.get("values", {})
            match = None
            if isinstance(raw_values, dict):
                for key, value in raw_values.items():
                    normalized = str(key).replace("|", ".")
                    if normalized == channel_id or normalized.endswith(f".{channel_id}"):
                        match = value
                        break
            elif isinstance(raw_values, list):
                for sample in raw_values:
                    if not isinstance(sample, dict):
                        continue
                    subject = str(sample.get("subject", "")).replace("|", ".")
                    feature = str(sample.get("feature", "")).replace("|", ".")
                    if not feature:
                        continue
                    normalized = f"{subject}.{feature}" if subject else feature
                    if feature == channel_id or normalized == channel_id or normalized.endswith(f".{channel_id}"):
                        match = sample.get("value")
                        break
            if match is not None:
                times.append(float(entry.get("t", 0.0)))
                values.append(match)
        return ChannelData(channel_id=channel_id, times=times, values=values)

    def states(self, subject_id: str) -> StateData:
        """Return active-state sequence for one subject.

        subject_id may be a short suffix (e.g. 'bed') or the full KIR id
        (e.g. 'subject.VoronTrident350.PrintSequence.bed'). Short names are
        matched against the last segment of each key in the trace.
        """
        times: list[float] = []
        states: list[list[str]] = []
        for entry in self._timeline:
            raw_states: dict = entry.get("states", {})
            matched: list[str] | None = None
            # exact match first
            if subject_id in raw_states:
                matched = raw_states[subject_id]
            else:
                # suffix match: "bed" matches "subject.VoronTrident350.PrintSequence.bed"
                for key, value in raw_states.items():
                    if key == subject_id or key.endswith(f".{subject_id}"):
                        matched = value
                        break
            if matched is not None:
                times.append(float(entry.get("t", 0.0)))
                # strip qualified prefixes from state names for readability
                short_states = [s.rsplit(".", 1)[-1] for s in matched]
                states.append(short_states)
        return StateData(subject_id=subject_id, times=times, states=states)

    @property
    def duration(self) -> float:
        if not self._timeline:
            return 0.0
        return float(self._timeline[-1].get("t", 0.0))


@dataclass
class PartRef:
    id: str
    name: str
    kind: str
    element_kind: str
    parent: "PartRef | None"
    depth: int
    _properties: JsonObject

    @classmethod
    def from_json(cls, data: JsonObject, parent_lookup: "dict[str, PartRef]") -> "PartRef":
        parent_id = data.get("parentId")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            kind=str(data.get("kind", "")),
            element_kind=str(data.get("elementKind", "")),
            parent=parent_lookup.get(parent_id) if parent_id else None,
            depth=int(data.get("depth", 0)),
            _properties=data.get("attributes") or {},
        )

    def attr(self, name: str, default: Any = None) -> Any:
        """Read an attribute value from model properties."""
        return self._properties.get(name, default)

    def attrs(self) -> dict[str, Any]:
        """All non-structural properties for this part."""
        skip = {
            "declared_name",
            "owner",
            "owning_type",
            "type",
            "source_file",
            "sourceFile",
            "definition",
        }
        return {k: v for k, v in self._properties.items() if k not in skip}

    def children(self, all_parts: list["PartRef"]) -> list["PartRef"]:
        return [
            part
            for part in all_parts
            if part.parent is not None and part.parent.id == self.id
        ]
