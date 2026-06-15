from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

SnapshotRow = dict[str, Any]
SnapshotInput = str | Iterable[SnapshotRow] | Any

DEFAULT_COMPARE_FIELDS = (
    "kind",
    "owner",
    "type",
    "specializes",
    "additional_types",
    "subsets",
    "redefines",
    "reference_target",
    "multiplicity",
    "multiplicity_lower",
    "multiplicity_upper",
    "direction",
    "is_end",
    "is_abstract",
)


@dataclass(frozen=True)
class SemanticSnapshotDifference:
    key: str
    field: str
    left: Any
    right: Any


def load_semantic_snapshot(value: SnapshotInput) -> list[SnapshotRow]:
    if hasattr(value, "semantic_snapshot_json"):
        value = value.semantic_snapshot_json()
    if isinstance(value, str):
        value = json.loads(value)
    rows = [normalize_semantic_snapshot_row(row) for row in value]
    rows.sort(key=semantic_snapshot_key)
    return rows


def semantic_snapshot_index(snapshot: SnapshotInput) -> dict[str, SnapshotRow]:
    return {semantic_snapshot_key(row): row for row in load_semantic_snapshot(snapshot)}


def compare_semantic_snapshots(
    left: SnapshotInput,
    right: SnapshotInput,
    *,
    fields: Iterable[str] = DEFAULT_COMPARE_FIELDS,
) -> list[SemanticSnapshotDifference]:
    left_index = semantic_snapshot_index(left)
    right_index = semantic_snapshot_index(right)
    differences: list[SemanticSnapshotDifference] = []

    for key in sorted(left_index.keys() - right_index.keys()):
        differences.append(SemanticSnapshotDifference(key, "<row>", left_index[key], None))
    for key in sorted(right_index.keys() - left_index.keys()):
        differences.append(SemanticSnapshotDifference(key, "<row>", None, right_index[key]))
    for key in sorted(left_index.keys() & right_index.keys()):
        for field in fields:
            left_value = left_index[key].get(field)
            right_value = right_index[key].get(field)
            if left_value != right_value:
                differences.append(
                    SemanticSnapshotDifference(key, field, left_value, right_value)
                )
    return differences


def normalize_semantic_snapshot_row(row: SnapshotRow) -> SnapshotRow:
    normalized = dict(row)
    for key, value in list(normalized.items()):
        if isinstance(value, list):
            normalized[key] = sorted(value, key=str)
    return normalized


def semantic_snapshot_key(row: SnapshotRow) -> str:
    return str(row.get("qualified_name") or row.get("id") or row.get("declared_name") or "")


__all__ = [
    "DEFAULT_COMPARE_FIELDS",
    "SemanticSnapshotDifference",
    "compare_semantic_snapshots",
    "load_semantic_snapshot",
    "semantic_snapshot_index",
    "semantic_snapshot_key",
]
