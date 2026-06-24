"""Lab-kernel context: LabModel, event emission, parameter sweep."""
from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from .extensions.base import AnalysisBridge

_LAB_MODE: bool = os.environ.get("MERCURIO_LAB_KERNEL") == "1"
_WORKSPACE: str = os.environ.get("MERCURIO_WORKSPACE", "")


def _emit(msg: dict[str, Any]) -> None:
    """Write a structured JSON event to the kernel's real stdout.

    Uses sys.__stdout__ to bypass per-cell capture so the reader thread
    receives it as a top-level protocol message rather than cell output.
    """
    if not _LAB_MODE:
        return
    out = sys.__stdout__ or sys.stdout
    out.write(json.dumps(msg) + "\n")
    out.flush()


@dataclass
class LabModel:
    """An in-Lab model session — a named parameter set that appears in VariantExplorer."""

    label: str
    handle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _params: dict[str, Any] = field(default_factory=dict, repr=False)
    _parent_id: str | None = field(default=None, repr=False)
    _workspace: str = field(default="", repr=False)
    _model: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        _emit({
            "type": "handle_created",
            "handleId": self.handle_id,
            "label": self.label,
            "parentId": self._parent_id,
            "params": self._params,
        })

    @property
    def params(self) -> dict[str, Any]:
        """Read-only copy of this model's parameter overrides."""
        return dict(self._params)

    @property
    def workspace(self) -> str:
        return self._workspace

    def fork(self, label: str, **params: Any) -> "LabModel":
        """Create a variant with parameter overrides merged on top of this model."""
        return LabModel(
            label=label,
            _params={**self._params, **params},
            _parent_id=self.handle_id,
            _workspace=self._workspace,
        )

    @property
    def raw(self) -> dict[str, Any]:
        """Escape hatch: direct access to the parameter dict."""
        return self._params

    def semantic_model(self):
        """Open the active workspace through the normal Mercurio model facade."""
        if self._model is None:
            if not self._workspace:
                raise RuntimeError("LabModel has no workspace path")
            self._model = _open_workspace_model(self._workspace)
        return self._model

    def check_semantic_legality(
        self,
        operation: dict[str, Any],
        *,
        facts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self.semantic_model().check_semantic_legality(operation, facts=facts)

    def semantic_next_actions(
        self,
        element_kind: str,
        *,
        element: str | None = None,
        candidate_target_kinds: list[str] | None = None,
        candidate_attributes: list[str] | None = None,
        facts: list[dict[str, Any]] | None = None,
        max_actions: int | None = None,
    ) -> dict[str, Any]:
        return self.semantic_model().semantic_next_actions(
            element_kind,
            element=element,
            candidate_target_kinds=candidate_target_kinds,
            candidate_attributes=candidate_attributes,
            facts=facts,
            max_actions=max_actions,
        )

    def can_contain(self, container_kind: str, child_kind: str) -> dict[str, Any]:
        return self.semantic_model().can_contain(container_kind, child_kind)

    def can_specialize(self, source_kind: str, target_kind: str) -> dict[str, Any]:
        return self.semantic_model().can_specialize(source_kind, target_kind)

    def can_type_usage(self, usage_kind: str, definition_kind: str) -> dict[str, Any]:
        return self.semantic_model().can_type_usage(usage_kind, definition_kind)

    def can_relate(
        self,
        relationship_kind: str,
        source_kind: str,
        target_kind: str,
    ) -> dict[str, Any]:
        return self.semantic_model().can_relate(
            relationship_kind,
            source_kind,
            target_kind,
        )

    def can_write_attribute(self, kind: str, attribute: str) -> dict[str, Any]:
        return self.semantic_model().can_write_attribute(kind, attribute)

    def __repr__(self) -> str:
        params_str = ", ".join(f"{k}={v!r}" for k, v in self._params.items())
        suffix = f"[{params_str}]" if params_str else ""
        return f"LabModel({self.label!r}{suffix})"


def _open_workspace_model(path: str):
    from . import open as open_model

    return open_model(path)


def open_lab(path: str | None = None, *, label: str | None = None) -> LabModel:
    """Open the workspace model as a LabModel in the Lab kernel context."""
    workspace = path or _WORKSPACE
    resolved_label = label or (Path(workspace).name if workspace else "model")
    return LabModel(label=resolved_label, _workspace=workspace)


def parameter_sweep(
    model: LabModel,
    param: str,
    values: Iterable[Any],
    *,
    label_template: str = "{param}={value}",
) -> list[LabModel]:
    """Fork *model* once per value and return the list of variants.

    Each fork emits ``lab:handle_created`` so all variants appear in
    VariantExplorer immediately.
    """
    return [
        model.fork(label_template.format(param=param, value=v), **{param: v})
        for v in values
    ]


def batch_run(
    variants: list[LabModel],
    analysis: str,
    *,
    bridge_name: str | None = None,
) -> list[dict[str, Any]]:
    """Run *analysis* over every variant using the named extension bridge.

    Raises ``ExtensionNotInstalledError`` with a pip install hint when the
    requested bridge is not installed.
    """
    from .extensions import get_bridge

    bridge = get_bridge(bridge_name or analysis)
    return [bridge.run(v) for v in variants]
