from __future__ import annotations

import json
import unittest

from mercurio.semantic import compare_semantic_snapshots, load_semantic_snapshot


class FakeSemanticModel:
    def __init__(self, rows):
        self._rows = rows

    def semantic_snapshot_json(self) -> str:
        return json.dumps(self._rows)


class SemanticSnapshotTests(unittest.TestCase):
    def test_loads_snapshot_from_model_json_and_rows(self) -> None:
        rows = [
            {
                "qualified_name": "Demo.Vehicle",
                "kind": "SysML::Systems::PartDefinition",
                "specializes": ["B", "A"],
            }
        ]

        from_model = load_semantic_snapshot(FakeSemanticModel(rows))
        from_json = load_semantic_snapshot(json.dumps(rows))
        from_rows = load_semantic_snapshot(rows)

        self.assertEqual(from_model, from_json)
        self.assertEqual(from_json, from_rows)
        self.assertEqual(from_model[0]["specializes"], ["A", "B"])

    def test_compare_ignores_list_order(self) -> None:
        left = [
            {
                "qualified_name": "Demo.Vehicle",
                "kind": "SysML::Systems::PartDefinition",
                "specializes": ["B", "A"],
            }
        ]
        right = [
            {
                "qualified_name": "Demo.Vehicle",
                "kind": "SysML::Systems::PartDefinition",
                "specializes": ["A", "B"],
            }
        ]

        self.assertEqual(compare_semantic_snapshots(left, right), [])

    def test_compare_equivalent_authoring_and_source_snapshots(self) -> None:
        authored = [
            {
                "qualified_name": "Demo.Vehicle",
                "kind": "SysML::Systems::PartDefinition",
                "owner": "namespace.Demo",
            },
            {
                "qualified_name": "Demo.Vehicle.engine",
                "kind": "SysML::PartUsage",
                "owner": "type.Demo.Vehicle",
                "type": "type.Demo.Engine",
                "subsets": ["A", "B"],
            },
        ]
        parsed_source = [
            {
                "qualified_name": "Demo.Vehicle.engine",
                "kind": "SysML::PartUsage",
                "owner": "type.Demo.Vehicle",
                "type": "type.Demo.Engine",
                "subsets": ["B", "A"],
            },
            {
                "qualified_name": "Demo.Vehicle",
                "kind": "SysML::Systems::PartDefinition",
                "owner": "namespace.Demo",
            },
        ]

        self.assertEqual(compare_semantic_snapshots(authored, parsed_source), [])

    def test_compare_reports_missing_and_changed_rows(self) -> None:
        left = [
            {"qualified_name": "Demo.Vehicle", "kind": "SysML::Systems::PartDefinition"},
            {"qualified_name": "Demo.Engine", "kind": "SysML::Systems::PartDefinition"},
        ]
        right = [
            {"qualified_name": "Demo.Vehicle", "kind": "SysML::PartUsage"},
            {"qualified_name": "Demo.Wheel", "kind": "SysML::Systems::PartDefinition"},
        ]

        differences = compare_semantic_snapshots(left, right)

        self.assertIn(("Demo.Engine", "<row>"), [(diff.key, diff.field) for diff in differences])
        self.assertIn(("Demo.Wheel", "<row>"), [(diff.key, diff.field) for diff in differences])
        self.assertIn(("Demo.Vehicle", "kind"), [(diff.key, diff.field) for diff in differences])

    def test_compare_reports_multiplicity_differences(self) -> None:
        left = [
            {
                "qualified_name": "Demo.Vehicle.wheel",
                "kind": "SysML::PartUsage",
                "multiplicity": "4",
            }
        ]
        right = [
            {
                "qualified_name": "Demo.Vehicle.wheel",
                "kind": "SysML::PartUsage",
                "multiplicity": "3",
            }
        ]

        differences = compare_semantic_snapshots(left, right)

        self.assertIn(
            ("Demo.Vehicle.wheel", "multiplicity"),
            [(diff.key, diff.field) for diff in differences],
        )


if __name__ == "__main__":
    unittest.main()
