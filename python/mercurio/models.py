from __future__ import annotations

from dataclasses import dataclass
from typing import Any


JsonObject = dict[str, Any]


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
class WorkspaceInfo:
    workspace_id: str
    workspace_root: str | None
    active_path: str | None
    project: JsonObject | None

    @classmethod
    def from_open_json(cls, data: JsonObject) -> "WorkspaceInfo":
        return cls(
            workspace_id=str(data["workspaceId"]),
            workspace_root=data.get("workspaceRoot"),
            active_path=data.get("activePath"),
            project=data.get("project"),
        )

    @classmethod
    def from_summary_json(cls, data: JsonObject) -> "WorkspaceInfo":
        return cls(
            workspace_id=str(data["workspaceId"]),
            workspace_root=data.get("workspaceRoot"),
            active_path=data.get("activePath"),
            project=data.get("project"),
        )


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
            for key, value in raw_values.items():
                normalized = str(key).replace("|", ".")
                if normalized == channel_id or normalized.endswith(f".{channel_id}"):
                    match = value
                    break
            if match is not None:
                times.append(float(entry.get("t", 0.0)))
                values.append(match)
        return ChannelData(channel_id=channel_id, times=times, values=values)

    def states(self, subject_id: str) -> StateData:
        """Return active-state sequence for one subject."""
        times: list[float] = []
        states: list[list[str]] = []
        for entry in self._timeline:
            subject_states = entry.get("states", {}).get(subject_id)
            if subject_states is not None:
                times.append(float(entry.get("t", 0.0)))
                states.append(list(subject_states))
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
