"""Declaration factories for the first-release Python API."""

from __future__ import annotations

from .authoring import (
    ActionDefinition,
    ActionUsage,
    AnalysisDefinition,
    AnalysisUsage,
    AttributeDefinition,
    AttributeUsage,
    ConnectionDefinition,
    ConnectionUsage,
    ConstraintDefinition,
    ConstraintUsage,
    ItemDefinition,
    ItemUsage,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
    RequirementDefinition,
    StateDefinition,
    StateUsage,
    TransitionUsage,
)


def part(name: str) -> PartUsage:
    return PartUsage(name)


def part_def(name: str) -> PartDefinition:
    return PartDefinition(name)


def attr(name: str) -> AttributeUsage:
    return AttributeUsage(name)


def attr_def(name: str) -> AttributeDefinition:
    return AttributeDefinition(name)


def item(name: str) -> ItemUsage:
    return ItemUsage(name)


def item_def(name: str) -> ItemDefinition:
    return ItemDefinition(name)


def port(name: str) -> PortUsage:
    return PortUsage(name)


def port_def(name: str) -> PortDefinition:
    return PortDefinition(name)


def connection(name: str) -> ConnectionUsage:
    return ConnectionUsage(name)


def connection_def(name: str) -> ConnectionDefinition:
    return ConnectionDefinition(name)


def action(name: str) -> ActionUsage:
    return ActionUsage(name)


def action_def(name: str) -> ActionDefinition:
    return ActionDefinition(name)


def constraint(name: str) -> ConstraintUsage:
    return ConstraintUsage(name)


def constraint_def(name: str) -> ConstraintDefinition:
    return ConstraintDefinition(name)


def analysis(name: str) -> AnalysisUsage:
    return AnalysisUsage(name)


def analysis_def(name: str) -> AnalysisDefinition:
    return AnalysisDefinition(name)


def requirement_def(name: str) -> RequirementDefinition:
    return RequirementDefinition(name)


def state(name: str) -> StateUsage:
    return StateUsage(name)


def state_def(name: str) -> StateDefinition:
    return StateDefinition(name)


def transition(name: str) -> TransitionUsage:
    return TransitionUsage(name)


__all__ = [
    "action",
    "action_def",
    "analysis",
    "analysis_def",
    "attr",
    "attr_def",
    "connection",
    "connection_def",
    "constraint",
    "constraint_def",
    "item",
    "item_def",
    "part",
    "part_def",
    "port",
    "port_def",
    "requirement_def",
    "state",
    "state_def",
    "transition",
]
