from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Callable

from .types import (
    CapabilityRequest,
    JsonObject,
    ReasoningReport,
    validate_capability_descriptor,
)

CapabilityFn = Callable[[CapabilityRequest], "ReasoningReport | dict[str, Any]"]


class CapabilityRunner:
    """
    Entry-point harness for process-provider capabilities.

    Usage — decorator form (descriptor declared once):

        @CapabilityRunner.capability(
            id="org.example.my-analysis",
            kind="mercurio.capability.kind/custom-reasoning",
            name="My Analysis",
        )
        def analyze(request: CapabilityRequest) -> ReasoningReport:
            ...
            return request.report_passed(findings=[...], artifacts=[...])

        if __name__ == "__main__":
            CapabilityRunner.run(analyze)

    Usage — explicit form:

        def analyze(request: CapabilityRequest) -> ReasoningReport:
            ...

        if __name__ == "__main__":
            CapabilityRunner.run(analyze, capability_descriptor={...})
    """

    @staticmethod
    def run(
        fn: CapabilityFn,
        *,
        capability_descriptor: JsonObject | None = None,
    ) -> None:
        descriptor = capability_descriptor or getattr(fn, "_mercurio_descriptor", {})

        try:
            validate_capability_descriptor(descriptor)
        except Exception as exc:
            _write_transport_error("descriptor_error", f"Invalid capability descriptor: {exc}")
            sys.exit(1)

        try:
            raw = json.load(sys.stdin)
        except Exception as exc:
            _write_transport_error("parse_error", f"Failed to parse request: {exc}")
            sys.exit(1)

        try:
            request = CapabilityRequest.from_json(raw)
            request._descriptor = descriptor
        except Exception as exc:
            _write_transport_error("request_error", f"Failed to build request: {exc}")
            sys.exit(1)

        try:
            report = fn(request)
        except Exception as exc:
            _write_transport_error(
                "capability_error",
                f"Capability raised an exception: {exc}",
                detail=traceback.format_exc(),
            )
            sys.exit(1)

        try:
            effect = getattr(fn, "_mercurio_effect", "observe")
            if isinstance(report, dict):
                # Mutate-effect capability returned a CapabilityModelPatch dict.
                if effect != "mutate":
                    raise ValueError(
                        "only mutate-effect capabilities may return a patch dict; "
                        "observe-effect capabilities must return ReasoningReport"
                    )
                # Emit a minimal ReasoningReport with the patch in metadata so the
                # host can surface it for user review before writing to source.
                import hashlib, uuid as _uuid
                patch_json = json.dumps(report, default=str)
                patch_id = hashlib.sha256(patch_json.encode()).hexdigest()[:16]
                stub_report: JsonObject = {
                    "status": "passed",
                    "findings": [],
                    "artifacts": [],
                    "evidence": {"nodes": [], "edges": []},
                }
                json.dump(
                    {
                        "report": stub_report,
                        "metadata": {
                            "runner": "mercurio_capability/0.1",
                            "effect": "mutate",
                            "patch": report,
                            "patchId": patch_id,
                        },
                    },
                    sys.stdout,
                    default=str,
                )
            else:
                if not isinstance(report, ReasoningReport):
                    raise ValueError("capability function must return ReasoningReport or (for mutate-effect) a CapabilityModelPatch dict")
                metadata: JsonObject = {"runner": "mercurio_capability/0.1"}
                if effect == "mutate":
                    metadata["effect"] = "mutate"
                json.dump(
                    {
                        "report": report.to_json(),
                        "metadata": metadata,
                    },
                    sys.stdout,
                    default=str,
                )
        except Exception as exc:
            _write_transport_error(
                "response_error",
                f"Failed to serialize capability response: {exc}",
                detail=traceback.format_exc(),
            )
            sys.exit(1)

    @staticmethod
    def capability(
        *,
        id: str,
        kind: str,
        name: str,
        version: str = "0.1.0",
        deterministic: bool = True,
        input_artifact_kinds: list[str] | None = None,
        output_artifact_kinds: list[str] | None = None,
        applicability_types: list[str] | None = None,
        also_workspace: bool = False,
        effect: str = "observe",
        composes: list[str] | None = None,
    ) -> Callable[[CapabilityFn], CapabilityFn]:
        """Decorator that attaches a capability descriptor to the function.

        Args:
            applicability_types: KerML/SysML metamodel type names this capability applies to
                (e.g. ``["PartDefinition", "ItemDefinition"]``).  When omitted the capability
                is considered workspace-scoped.
            also_workspace: When *True* the capability also appears in the workspace panel even
                if ``applicability_types`` is set.
            effect: ``"observe"`` (default) or ``"mutate"``.  Mutating capabilities may return a
                ``CapabilityModelPatch`` proposal that the host will ask the user to review.
            composes: List of capability ids that should be run as sub-capabilities before this
                capability executes.  Their reports are injected into ``request.sub_reports``.
        """
        descriptor: JsonObject = {
            "id": id,
            "kind": kind,
            "name": name,
            "version": version,
            "api_version": "0.1",
            "deterministic": deterministic,
            "input_artifact_kinds": input_artifact_kinds or ["kir"],
            "output_artifact_kinds": output_artifact_kinds or ["table", "reasoning_report"],
        }
        applicability: JsonObject = {}
        if applicability_types:
            applicability["types"] = applicability_types
        if also_workspace:
            applicability["also_workspace"] = True

        def decorator(fn: CapabilityFn) -> CapabilityFn:
            fn._mercurio_descriptor = descriptor  # type: ignore[attr-defined]
            fn._mercurio_applicability = applicability  # type: ignore[attr-defined]
            fn._mercurio_effect = effect  # type: ignore[attr-defined]
            fn._mercurio_composes = composes or []  # type: ignore[attr-defined]
            return fn

        return decorator


def _write_transport_error(code: str, message: str, *, detail: str | None = None) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if detail:
        payload["detail"] = detail
    json.dump({"error": payload}, sys.stdout)
