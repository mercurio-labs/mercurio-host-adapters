from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import mercurio
from mercurio.session import (
    AnalysisQuery,
    CompiledModel,
    SimulationConfiguration,
    ProjectSession,
    StaleSemanticRefError,
    VariantBaseChangedError,
)


class FakeSemanticModel:
    def __init__(self, rows):
        self._rows = rows

    def semantic_snapshot_json(self) -> str:
        return json.dumps(self._rows)


class FakeBuilder:
    def __init__(self, rows=None, files=None):
        self.rows = rows or []
        self.files = files or {"model.sysml": ""}
        self.renames: list[tuple[str, str]] = []
        self.types: list[tuple[str, str | None]] = []
        self.expressions: list[tuple[str, str]] = []

    def compile(self):
        return FakeSemanticModel(self.rows)

    def to_sysml(self):
        return dict(self.files)

    def rename(self, target, new_name):
        self.renames.append((target, new_name))

    def set_type(self, target, ty):
        self.types.append((target, ty))

    def set_expression(self, target, expression):
        self.expressions.append((target, expression))


class SessionLayerTests(unittest.TestCase):
    def vehicle_rows(self):
        return [
            {
                "qualified_name": "VehicleExample.Vehicle",
                "kind": "SysML::Systems::PartDefinition",
                "owner": "VehicleExample",
            },
            {
                "qualified_name": "VehicleExample.Car",
                "kind": "SysML::Systems::PartDefinition",
                "owner": "VehicleExample",
                "specializes": ["VehicleExample.Vehicle"],
            },
            {
                "qualified_name": "VehicleExample.ElectricCar",
                "kind": "SysML::Systems::PartDefinition",
                "owner": "VehicleExample",
                "specializes": ["VehicleExample.Car"],
            },
            {
                "qualified_name": "VehicleExample.Vehicle.engine",
                "kind": "SysML::PartUsage",
                "owner": "VehicleExample.Vehicle",
                "type": "VehicleExample.Engine",
            },
        ]

    def test_package_root_exports_layered_api_without_native_builder(self) -> None:
        expected = {
            "AnalysisQuery",
            "CompiledModel",
            "PartDefRef",
            "PartUsageRef",
            "ProjectSession",
            "SemanticRef",
            "SimulationConfiguration",
            "SmallEdit",
            "StaleSemanticRefError",
            "TradeStudy",
            "Variant",
            "VariantBaseChangedError",
            "open",
            "open_project",
        }

        self.assertTrue(expected.issubset(set(mercurio.__all__)))
        self.assertIs(mercurio.CompiledModel, CompiledModel)
        self.assertIs(mercurio.AnalysisQuery, AnalysisQuery)
        self.assertIs(mercurio.SimulationConfiguration, SimulationConfiguration)

    def test_compiled_model_exposes_immutable_refs_with_revision(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))

        vehicle = model.part_def("Vehicle")

        self.assertEqual(vehicle.qualified_name, "VehicleExample.Vehicle")
        self.assertEqual(vehicle.revision, model.revision)
        with self.assertRaises(Exception):
            vehicle.qualified_name = "Other"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            vehicle.data["kind"] = "Other"  # type: ignore[index]
        with self.assertRaises(TypeError):
            model.rows[0]["kind"] = "Other"  # type: ignore[index]

    def test_part_def_subtypes_are_transitive(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))

        names = [ref.name for ref in model.part_def("Vehicle").subtypes(transitive=True)]

        self.assertEqual(names, ["Car", "ElectricCar"])

    def test_refs_walk_containment(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))

        names = [ref.name for ref in model.part_def("Vehicle").walk()]

        self.assertEqual(names, ["Vehicle", "engine"])

    def test_query_service_filters_and_walks_containment(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))

        subtype_names = [ref.name for ref in model.query.subtypes("Vehicle")]
        contained_names = [ref.name for ref in model.query.containment("Vehicle")]
        usage_names = [ref.name for ref in model.query.part_usages(lambda ref: ref.type_name() == "VehicleExample.Engine")]

        self.assertEqual(subtype_names, ["Car", "ElectricCar"])
        self.assertEqual(contained_names, ["Vehicle", "engine"])
        self.assertEqual(usage_names, ["engine"])

    def test_records_and_graph_exports_are_revisioned(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))

        records = model.to_records(model.query.part_defs())
        containment_graph = model.graph("containment")
        specialization_graph = model.graph("specialization")

        self.assertEqual(records[0]["revision"], model.revision)
        self.assertIn(
            {
                "source": "VehicleExample.Vehicle",
                "target": "VehicleExample.Vehicle.engine",
                "relation": "owns",
            },
            containment_graph["edges"],
        )
        self.assertIn(
            {
                "source": "VehicleExample.Car",
                "target": "VehicleExample.Vehicle",
                "relation": "specializes",
            },
            specialization_graph["edges"],
        )

    def test_model_diff_delegates_to_semantic_snapshot_compare(self) -> None:
        left = CompiledModel(FakeSemanticModel(self.vehicle_rows()))
        right_rows = self.vehicle_rows()
        right_rows[0] = dict(right_rows[0], kind="SysML::PartUsage")
        right = CompiledModel(FakeSemanticModel(right_rows))

        differences = left.diff(right)

        self.assertEqual(differences[0].key, "VehicleExample.Vehicle")
        self.assertEqual(differences[0].field, "kind")

    def test_notebook_reprs_summarize_without_mutation(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))
        project = ProjectSession(FakeBuilder(self.vehicle_rows(), {"model.sysml": "part def Vehicle;"}))
        variant_builder = FakeBuilder(self.vehicle_rows(), project.to_sysml())
        with patch("mercurio.session._model_builder_class") as builders:
            builders.return_value.from_files.return_value = variant_builder
            variant = project.trade_study("study").variant("baseline")

        self.assertIn("CompiledModel", repr(model))
        self.assertIn(model.revision[:12], model._repr_html_())
        self.assertIn("ProjectSession", repr(project))
        self.assertIn("Variant", repr(variant))

    def test_to_frame_reports_pandas_requirement_when_missing(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))
        with patch.dict("sys.modules", {"pandas": None}):
            with self.assertRaisesRegex(RuntimeError, "requires pandas"):
                model.to_frame()

    def test_small_edit_routes_mutation_to_project_builder(self) -> None:
        builder = FakeBuilder(self.vehicle_rows())
        project = ProjectSession(builder)
        engine = project.compile().part_usage("engine")

        project.edit(engine).rename("motor").set_type("ElectricMotor")

        self.assertEqual(builder.renames, [("VehicleExample.Vehicle.engine", "motor")])
        self.assertEqual(builder.types, [("VehicleExample.Vehicle.motor", "ElectricMotor")])

    def test_project_edit_rejects_stale_semantic_ref_after_source_change(self) -> None:
        builder = FakeBuilder(self.vehicle_rows(), {"model.sysml": "part vehicle engine;"})
        project = ProjectSession(builder)
        engine = project.compile().part_usage("engine")

        builder.files["model.sysml"] = "part vehicle motor;"

        with self.assertRaises(StaleSemanticRefError):
            project.edit(engine).rename("motor")

    def test_variant_starts_from_base_files_and_compiles_independently(self) -> None:
        base = ProjectSession(FakeBuilder(self.vehicle_rows(), {"model.sysml": "part def Vehicle;"}))
        with patch("mercurio.session._model_builder_class") as builders:
            builders.return_value.from_files.return_value = FakeBuilder(self.vehicle_rows(), base.to_sysml())
            variant = base.trade_study("battery-sizing").variant("large-pack")

        model = variant.compile()

        self.assertEqual(model.part_def("Vehicle").name, "Vehicle")
        self.assertEqual(variant.to_sysml(), {"model.sysml": "part def Vehicle;"})
        self.assertEqual(variant.base_fingerprint, base.source_fingerprint)
        self.assertEqual(variant.source_fingerprint, base.source_fingerprint)

    def test_variant_compile_requires_current_base_by_default(self) -> None:
        base_builder = FakeBuilder(self.vehicle_rows(), {"model.sysml": "part def Vehicle;"})
        base = ProjectSession(base_builder)
        with patch("mercurio.session._model_builder_class") as builders:
            builders.return_value.from_files.return_value = FakeBuilder(self.vehicle_rows(), base.to_sysml())
            variant = base.trade_study("battery-sizing").variant("large-pack")

        base_builder.files["model.sysml"] = "part def Vehicle { attribute mass; }"

        self.assertTrue(variant.is_base_stale)
        with self.assertRaises(VariantBaseChangedError):
            variant.compile()

        self.assertEqual(
            variant.compile(allow_stale_base=True).part_def("Vehicle").name,
            "Vehicle",
        )

    def test_variant_edit_rejects_stale_semantic_ref_after_overlay_change(self) -> None:
        base = ProjectSession(FakeBuilder(self.vehicle_rows(), {"model.sysml": "part vehicle engine;"}))
        variant_builder = FakeBuilder(self.vehicle_rows(), base.to_sysml())
        with patch("mercurio.session._model_builder_class") as builders:
            builders.return_value.from_files.return_value = variant_builder
            variant = base.trade_study("battery-sizing").variant("large-pack")

        engine = variant.compile().part_usage("engine")
        variant_builder.files["model.sysml"] = "part vehicle motor;"

        with self.assertRaises(StaleSemanticRefError):
            variant.edit(engine).rename("motor")

    def test_simulation_configuration_records_model_revision(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))
        vehicle = model.part_def("Vehicle")

        config = model.simulation("drive-cycle").for_subject(vehicle).configure(duration=100, step=0.1)

        self.assertEqual(
            config.to_dict(),
            {
                "name": "drive-cycle",
                "subject": "VehicleExample.Vehicle",
                "settings": {"duration": 100, "step": 0.1},
                "model_revision": model.revision,
                "source_fingerprint": None,
            },
        )
        self.assertIn("SimulationConfiguration", repr(config))
        self.assertIn("drive-cycle", config._repr_html_())
        with self.assertRaisesRegex(NotImplementedError, "not wired"):
            config.run()

    def test_simulation_html_repr_escapes_values(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.vehicle_rows()))

        config = model.simulation("<script>").for_subject("Vehicle").configure(label="<b>")

        html = config._repr_html_()
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;b&gt;", html)
        self.assertNotIn("<script>", html)

    def test_project_simulation_configuration_records_source_fingerprint(self) -> None:
        project = ProjectSession(FakeBuilder(self.vehicle_rows(), {"model.sysml": "part def Vehicle;"}))

        config = project.simulation("authoring-check").for_subject("Vehicle").configure(seed="none")

        self.assertEqual(config.model_revision, None)
        self.assertEqual(config.source_fingerprint, project.source_fingerprint)
        self.assertEqual(config.to_dict()["settings"], {"seed": "none"})


if __name__ == "__main__":
    unittest.main()
