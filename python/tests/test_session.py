from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import mercurio
from mercurio.session import (
    AnalysisQuery,
    CellRunReport,
    CompiledModel,
    SimulationConfiguration,
    ProjectSession,
    SemanticQuery,
    StaleSemanticRefError,
    TransactionBuilder,
    VariantBaseChangedError,
)


class FakeSemanticModel:
    def __init__(self, rows):
        self._rows = rows

    def semantic_snapshot_json(self) -> str:
        return json.dumps(self._rows)


class FakeDslSemanticModel(FakeSemanticModel):
    def model_metadata_json(self) -> str:
        return json.dumps({
            "element_count": len(self._rows),
            "edge_count": 0,
            "library_element_count": 0,
            "user_element_count": len(self._rows),
            "layers": [2],
            "relations": [],
            "graph_scopes": ["l2", "l2_plus_context", "full"],
            "default_graph_scope": "l2",
        })

    def graph_view_json(self, scope: str | None = None) -> str:
        return json.dumps({
            "nodes": [
                {
                    "id": row.get("id") or row.get("qualified_name"),
                    "label": str(row.get("qualified_name", "")).rsplit(".", 1)[-1],
                    "kind": row.get("kind"),
                    "layer": 2,
                    "property_count": len(row),
                }
                for row in self._rows
            ],
            "edges": [],
            "scope": scope or "l2",
        })

    def search_json(self, query: str) -> str:
        query = query.lower()
        return json.dumps([
            {
                "id": row.get("id") or row.get("qualified_name"),
                "label": str(row.get("qualified_name", "")).rsplit(".", 1)[-1],
                "kind": row.get("kind"),
                "layer": 2,
            }
            for row in self._rows
            if query in str(row.get("qualified_name", "")).lower()
        ])

    def element_details_json(self, element_id: str) -> str:
        for row in self._rows:
            if row.get("qualified_name") == element_id or row.get("id") == element_id:
                return json.dumps({
                    "id": element_id,
                    "label": str(row.get("qualified_name", element_id)).rsplit(".", 1)[-1],
                    "kind": row.get("kind"),
                    "layer": 2,
                    "metatype": None,
                    "metatype_specialization_chain": [],
                    "direct_properties": dict(row),
                    "inherited_properties": [],
                    "effective_properties": dict(row),
                    "property_table": {"rows": []},
                    "specialization_chain": [],
                    "inbound": [],
                    "outbound": [],
                })
        raise KeyError(element_id)

    def l2_explorer_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        return json.dumps({
            "seed_id": request["seed_id"],
            "nodes": [
                {
                    "id": request["seed_id"],
                    "label": request["seed_id"].rsplit(".", 1)[-1],
                    "kind": "PartDefinition",
                    "layer": 2,
                    "attributes": [],
                    "specializes_count": 0,
                    "specialized_by_count": 0,
                    "is_seed": True,
                }
            ],
            "edges": [],
        })

    def metatype_explorer_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        return json.dumps({
            "seed_id": request["seed_id"],
            "nodes": [
                {
                    "id": request["seed_id"],
                    "label": request["seed_id"].rsplit(".", 1)[-1],
                    "kind": "PartDefinition",
                    "layer": 2,
                    "attributes": [],
                    "specializes_count": 0,
                    "specialized_by_count": 0,
                    "is_seed": True,
                }
            ],
            "edges": [],
        })

    def run_cell_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        if request["kind"] == "analysis":
            capability = {
                "id": request["parameters"].get("capabilityId", "mercurio.dsl.analysis"),
                "status": "passed",
                "artifacts": [],
                "diagnostics": [],
            }
            return json.dumps({
                "cellId": request.get("cellId", "dsl.analysis"),
                "kind": request["kind"],
                "status": "passed",
                "outputs": [
                    {
                        "id": "capability_report",
                        "kind": "capability_report",
                        "value": capability,
                    }
                ],
                "artifacts": [],
                "diagnostics": [],
                "capabilityReport": capability,
                "metadata": {},
            })
        if request["kind"] == "action":
            return json.dumps({
                "cellId": request.get("cellId", "dsl.action"),
                "kind": "action",
                "status": "passed",
                "outputs": [
                    {
                        "id": "result",
                        "kind": "json",
                        "mimeType": "application/vnd.mercurio.dsl.action-preview+json",
                        "value": {
                            "schema": "mercurio.semantic_transaction.v1",
                            "status": "previewed",
                            "applied": False,
                            "operation_count": 1,
                        },
                    }
                ],
                "artifacts": [],
                "diagnostics": [],
                "metadata": {},
            })
        return json.dumps({
            "cellId": request.get("cellId", "dsl.query"),
            "kind": request["kind"],
            "status": "passed",
            "outputs": [
                {
                    "id": "result",
                    "kind": "table",
                    "mimeType": "application/vnd.mercurio.dsl.query+json",
                    "value": {
                        "columns": ["value"],
                        "rows": [[len(self._rows)]],
                    },
                }
            ],
            "artifacts": [],
            "diagnostics": [],
            "metadata": {"language": request.get("language")},
        })

    def dsl_schema_json(self) -> str:
        return json.dumps({
            "element_kinds": ["PartDefinition", "PartUsage"],
            "fields": [{"name": "kind", "kind": "scalar"}],
            "stdlib_functions": ["ModelContext.parts"],
        })


class FakeTransactionSemanticModel(FakeSemanticModel):
    def run_cell_json(self, request_json: str) -> str:
        raise AssertionError("transaction preview must not delegate to DSL cells")

    def preview_transaction_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        return json.dumps({
            "schema": "mercurio.semantic_transaction.v1",
            "transaction_id": "txn.fake",
            "label": request["label"],
            "status": "previewed",
            "operation_count": 0 if not request["actions"] else 1,
            "operations": [
                {
                    "kind": "change_set",
                    "change_set": {
                        "actions": request["actions"],
                    },
                }
            ] if request["actions"] else [],
            "semantic_diff": {},
            "applied": False,
            "metadata": {},
        })


class FakeBuilder:
    def __init__(self, rows=None, files=None):
        self.rows = rows or []
        self.files = files or {"model.sysml": ""}
        self.renames: list[tuple[str, str]] = []
        self.types: list[tuple[str, str | None]] = []
        self.expressions: list[tuple[str, str]] = []
        self.attributes: list[tuple[str, str, object]] = []

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

    def set_attribute(self, target, attribute, value):
        self.attributes.append((target, attribute, value))


class FakeDslBuilder(FakeBuilder):
    def compile(self):
        return FakeDslSemanticModel(self.rows)


class FakeTransactionBuilder(FakeBuilder):
    def compile(self):
        return FakeTransactionSemanticModel(self.rows)


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

    def package_rows(self):
        return [
            {
                "qualified_name": "UavModel",
                "declared_name": "UavModel",
                "kind": "SysML::Package",
                "layer": 2,
                "model_layer": "user",
                "metatype_name": "Package",
                "metatype_chain": ["Package", "Namespace", "Element"],
            },
            {
                "qualified_name": "UavModel.Airframe",
                "declared_name": "Airframe",
                "kind": "SysML::Systems::PartDefinition",
                "layer": 2,
                "model_layer": "user",
                "metatype_name": "PartDefinition",
                "metatype_chain": ["PartDefinition", "Classifier", "Type", "Namespace", "Element"],
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
            "SemanticQuery",
            "SimulationConfiguration",
            "SmallEdit",
            "StaleSemanticRefError",
            "TradeStudy",
            "TransactionBuilder",
            "Variant",
            "VariantBaseChangedError",
            "open",
            "open_project",
        }

        self.assertTrue(expected.issubset(set(mercurio.__all__)))
        self.assertIs(mercurio.CompiledModel, CompiledModel)
        self.assertIs(mercurio.AnalysisQuery, AnalysisQuery)
        self.assertIs(mercurio.SemanticQuery, SemanticQuery)
        self.assertIs(mercurio.TransactionBuilder, TransactionBuilder)
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

    def test_fluent_query_filters_metatypes_and_selects_fields(self) -> None:
        model = CompiledModel(FakeSemanticModel(self.package_rows()))

        rows = (
            model.query.elements()
            .where_model_layer("user")
            .where_metatype_is("KerML.Package")
            .order_by("qualified_name")
            .select(["qualified_name", "declared_name", "metatype_chain", "model_layer"])
        )

        self.assertEqual(
            rows,
            [
                {
                    "qualified_name": "UavModel",
                    "declared_name": "UavModel",
                    "metatype_chain": ["Package", "Namespace", "Element"],
                    "model_layer": "user",
                }
            ],
        )
        self.assertEqual(model.query.where_metatype_is("Package").count(), 1)
        self.assertTrue(model.resolve("UavModel").is_metatype("Package"))

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

    def test_compiled_model_runs_dsl_through_shared_cell_report(self) -> None:
        model = CompiledModel(FakeDslSemanticModel(self.vehicle_rows()))

        report = model.run_cell("model.parts().count()", cell_id="cell-1")

        self.assertIsInstance(report, CellRunReport)
        self.assertEqual(report.cell_id, "cell-1")
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.result["rows"], [[4]])
        self.assertEqual(model.dsl("model.parts().count()")["rows"], [[4]])
        self.assertIn("ModelContext.parts", model.dsl_schema()["stdlib_functions"])

    def test_compiled_model_runs_analysis_dsl_through_shared_cell_report(self) -> None:
        model = CompiledModel(FakeDslSemanticModel(self.vehicle_rows()))

        report = model.run_analysis_dsl(
            "#{verdict: \"pass\"}",
            run_id="mass-check",
            subject_element_id="type.Demo.Vehicle",
        )

        self.assertEqual(report.kind, "analysis")
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.capability_report["id"], "mercurio.dsl.analysis")
        self.assertEqual(model.analysis_dsl("#{verdict: \"pass\"}")["status"], "passed")

    def test_compiled_model_runs_action_dsl_through_shared_cell_report(self) -> None:
        model = CompiledModel(FakeDslSemanticModel(self.vehicle_rows()))

        report = model.run_action_dsl(
            'model.transaction("rename").rename("VehicleExample.Vehicle", "Vehicle2").preview()',
            cell_id="cell-action",
        )

        self.assertEqual(report.cell_id, "cell-action")
        self.assertEqual(report.kind, "action")
        self.assertEqual(report.result["schema"], "mercurio.semantic_transaction.v1")
        self.assertEqual(report.result["status"], "previewed")
        self.assertFalse(report.result["applied"])
        self.assertEqual(model.preview_dsl("model.changes().preview()")["operation_count"], 1)

    def test_project_transaction_previews_and_applies_source_edits(self) -> None:
        builder = FakeTransactionBuilder(self.vehicle_rows(), {"model.sysml": "part def Vehicle;"})
        project = ProjectSession(builder)

        transaction = (
            project.transaction("python transaction")
            .rename("VehicleExample.Vehicle.engine", "motor")
            .set_attribute("VehicleExample.Vehicle", "doc", "checked")
        )
        preview = transaction.preview()
        transaction.apply()

        self.assertEqual(preview["status"], "previewed")
        self.assertEqual(transaction.to_dict()["actions"][0]["kind"], "rename_declaration")
        self.assertEqual(preview["operations"][0]["change_set"]["actions"][1]["value"], "checked")
        self.assertEqual(builder.renames, [("VehicleExample.Vehicle.engine", "motor")])
        self.assertEqual(builder.attributes, [("VehicleExample.Vehicle", "doc", "checked")])

    def test_compiled_model_exposes_shared_exploration_views(self) -> None:
        model = CompiledModel(FakeDslSemanticModel(self.vehicle_rows()))

        self.assertEqual(model.model_metadata()["user_element_count"], 4)
        self.assertEqual(model.graph_view()["nodes"][0]["id"], "VehicleExample.Vehicle")
        self.assertEqual(model.search("electric")[0]["label"], "ElectricCar")
        self.assertEqual(
            model.element_details("VehicleExample.Vehicle")["label"],
            "Vehicle",
        )
        self.assertEqual(
            model.l2_explorer("VehicleExample.Vehicle")["nodes"][0]["is_seed"],
            True,
        )
        rendered = model.render_view({
            "schema": "mercurio.view.v1",
            "version": 1,
            "kind": "explorer.metatype",
            "mode": "visualization",
            "parameters": {"seedId": "VehicleExample.Vehicle"},
        })
        self.assertEqual(rendered["metatypeExplorer"]["seed_id"], "VehicleExample.Vehicle")

    def test_project_session_and_variant_run_dsl_after_compile(self) -> None:
        base = ProjectSession(FakeDslBuilder(self.vehicle_rows(), {"model.sysml": "part def Vehicle;"}))
        with patch("mercurio.session._model_builder_class") as builders:
            builders.return_value.from_files.return_value = FakeDslBuilder(self.vehicle_rows(), base.to_sysml())
            variant = base.trade_study("battery-sizing").variant("large-pack")

        self.assertEqual(base.dsl("model.parts().count()")["rows"], [[4]])
        self.assertEqual(variant.query_dsl("model.parts().count()")["rows"], [[4]])
        self.assertEqual(base.action_dsl("model.changes().preview()")["status"], "previewed")
        self.assertEqual(
            variant.preview_dsl(
                "model.changes().preview()",
                allow_stale_base=True,
            )["schema"],
            "mercurio.semantic_transaction.v1",
        )
        self.assertEqual(base.search("vehicle")[0]["label"], "Vehicle")
        self.assertEqual(
            variant.metatype_explorer(
                "VehicleExample.Vehicle",
                allow_stale_base=True,
            )["seed_id"],
            "VehicleExample.Vehicle",
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
