"""Simplified capability authoring facade.

This module re-exports the process-provider SDK from ``mercurio_capability`` so
user code can stay under the main ``mercurio`` namespace.
"""

from __future__ import annotations

from mercurio_capability import (
    Artifact,
    CapabilityRequest,
    CapabilityRunner,
    ElementRef,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNode,
    Finding,
    JsonObject,
    ReasoningReport,
    SourceSpanRef,
)

capability = CapabilityRunner.capability
run = CapabilityRunner.run

__all__ = [
    "Artifact",
    "CapabilityRequest",
    "CapabilityRunner",
    "ElementRef",
    "EvidenceEdge",
    "EvidenceGraph",
    "EvidenceNode",
    "Finding",
    "JsonObject",
    "ReasoningReport",
    "SourceSpanRef",
    "capability",
    "run",
]
