from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from mercurio.lab import LabModel
from mercurio.runtime import Model


class FakeSemanticModel:
    def semantic_snapshot_json(self) -> str:
        return '[{"qualified_name": "Demo.Vehicle"}]'


class FakeNativeWorkspace:
    def compile(self) -> FakeSemanticModel:
        return FakeSemanticModel()

    def model_metadata_json(self) -> str:
        return '{"element_count":1,"edge_count":0,"library_element_count":0,"user_element_count":1}'

    def graph_view_json(self, scope: str | None = None) -> str:
        return (
            '{"nodes":[{"id":"type.Demo.Vehicle","label":"Vehicle","kind":"PartDefinition",'
            '"layer":2,"property_count":1}],"edges":[]}'
        )

    def search_json(self, query: str) -> str:
        return '[{"id":"type.Demo.Vehicle","label":"Vehicle","kind":"PartDefinition","layer":2}]'

    def element_details_json(self, element_id: str) -> str:
        return (
            '{"id":"type.Demo.Vehicle","label":"Vehicle","kind":"PartDefinition","layer":2,'
            '"metatype":null,"metatype_specialization_chain":[],"direct_properties":{},'
            '"inherited_properties":[],"effective_properties":{},"property_table":{"rows":[]},'
            '"specialization_chain":[],"inbound":[],"outbound":[]}'
        )

    def semantic_legality_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        return json.dumps({
            "schemaVersion": "mercurio.semantic_legality.v1",
            "operation": request["operation"],
            "status": "Blocked",
            "answer": {
                "status": "denied",
                "message": "satisfy relationships must target a requirement-like element",
            },
            "diagnostics": [
                {
                    "code": "sysml.satisfy.target_requirement",
                    "severity": "error",
                    "message": "satisfy relationships must target requirement-like elements",
                    "subjects": ["part"],
                    "source": "Rulepack",
                    "sourceFacts": [],
                }
            ],
        })

    def semantic_next_actions_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        return json.dumps({
            "schemaVersion": "mercurio.semantic_next_actions.v1",
            "legalitySchemaVersion": "mercurio.semantic_legality.v1",
            "element": request.get("element"),
            "elementKind": request["elementKind"],
            "actions": [
                {
                    "element": request.get("element"),
                    "operation": {
                        "kind": "addRelationship",
                        "relationshipKind": "satisfy",
                        "targetKind": "requirement",
                    },
                    "status": "Allowed",
                    "summary": "allowed",
                    "legality": {
                        "schemaVersion": "mercurio.semantic_legality.v1",
                        "operation": {
                            "kind": "relationship",
                            "relationshipKind": "satisfy",
                            "sourceKind": request["elementKind"],
                            "targetKind": "requirement",
                        },
                        "status": "Allowed",
                        "answer": {"status": "allowed"},
                        "diagnostics": [],
                    },
                }
            ],
            "truncated": False,
        })

    def model_explorer_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        return json.dumps({
            "seed_id": request["seed_id"],
            "nodes": [{"id": request["seed_id"], "label": "Vehicle", "is_seed": True}],
            "edges": [],
        })

    def metatype_explorer_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        return json.dumps({
            "seed_id": request["seed_id"],
            "nodes": [{"id": request["seed_id"], "label": "Vehicle", "is_seed": True}],
            "edges": [],
        })

    def run_cell_json(self, request_json: str) -> str:
        request = json.loads(request_json)
        if request["kind"] == "analysis":
            return (
                '{"cellId":"dsl.analysis","kind":"analysis","status":"passed",'
                '"outputs":[{"id":"capability_report","kind":"capability_report",'
                '"value":{"id":"mercurio.dsl.analysis","status":"passed"}}],'
                '"artifacts":[],"diagnostics":[],"capabilityReport":{"id":"mercurio.dsl.analysis","status":"passed"},'
                '"metadata":{}}'
            )
        if request["kind"] == "action":
            return (
                '{"cellId":"dsl.action","kind":"action","status":"passed",'
                '"outputs":[{"id":"result","kind":"json",'
                '"value":{"schema":"mercurio.semantic_transaction.v1","status":"previewed","applied":false}}],'
                '"artifacts":[],"diagnostics":[],"metadata":{}}'
            )
        return (
            '{"cellId":"dsl.query","kind":"query","status":"passed",'
            '"outputs":[{"id":"result","kind":"table","value":{"columns":["value"],"rows":[[7]]}}],'
            '"artifacts":[],"diagnostics":[],"metadata":{}}'
        )

    def dsl_schema_json(self) -> str:
        return '{"element_kinds":["PartDefinition"],"fields":[],"stdlib_functions":["ModelContext.parts"]}'

    def analysis_specs_json(self) -> str:
        return json.dumps([
            {
                "caseRef": {
                    "elementId": "analysis.Demo.PrintSequence",
                    "kind": "AnalysisUsage",
                    "label": "PrintSequence",
                },
                "modelRevision": "rev.fake",
                "readiness": "ready",
            }
        ])

    def analysis_run_json(self, case_id: str, run_id: str) -> str:
        return json.dumps({
            "runId": run_id,
            "capabilityId": "analysis.Demo.PrintSequence",
            "status": "passed",
            "target": {"id": case_id},
            "insights": [],
            "artifacts": [
                {
                    "id": "trace",
                    "kind": "simulation_trace",
                    "schema": "mercurio.simulation_trace.v1",
                    "digest": "fake",
                    "elementRefs": [],
                    "payload": {
                        "scenario_id": "PrintSequence",
                        "subject_id": "Demo.printer",
                        "channels": [],
                        "timeline": [],
                    },
                }
            ],
            "evidence": {"nodes": [], "edges": []},
            "diagnostics": [],
            "limitations": [],
        })


class FakeProject:
    def __init__(self) -> None:
        self.requests = []
        self.render_requests = []

    def model(self):
        return {"element_count": 2, "user_element_count": 2}

    def graph(self, *, scope: str | None = None):
        return {
            "nodes": [{"id": "type.Demo.Requirement", "label": "Requirement"}],
            "edges": [],
            "scope": scope,
        }

    def search(self, query):
        return [{"id": "type.Demo.Requirement", "label": query}]

    def element(self, element_id):
        return {"id": element_id, "label": element_id.rsplit(".", 1)[-1]}

    def check_semantic_legality(self, operation, *, facts=None):
        self.requests.append({"operation": operation, "facts": list(facts or ())})
        return {
            "schemaVersion": "mercurio.semantic_legality.v1",
            "operation": operation,
            "status": "Allowed",
            "answer": {"status": "allowed"},
            "diagnostics": [],
        }

    def semantic_next_actions(
        self,
        element_kind,
        *,
        element=None,
        candidate_target_kinds=None,
        candidate_attributes=None,
        facts=None,
        max_actions=None,
    ):
        self.requests.append({
            "element_kind": element_kind,
            "element": element,
            "candidate_target_kinds": list(candidate_target_kinds or ()),
            "candidate_attributes": list(candidate_attributes or ()),
            "facts": list(facts or ()),
            "max_actions": max_actions,
        })
        return {
            "schemaVersion": "mercurio.semantic_next_actions.v1",
            "legalitySchemaVersion": "mercurio.semantic_legality.v1",
            "elementKind": element_kind,
            "actions": [],
            "truncated": False,
        }

    def render_view(self, document):
        self.render_requests.append(document)
        model = document["model"]
        if document["kind"] == "explorer.model":
            return {
                "kind": "explorer.model",
                "document": document,
                "modelExplorer": {
                    "seed_id": model["root"],
                    "nodes": [],
                    "edges": [],
                },
            }
        return {
            "kind": "explorer.metatype",
            "document": document,
            "metatypeExplorer": {
                "seed_id": model["root"],
                "nodes": [],
                "edges": [],
            },
        }

    def model_explorer(self, seed_id, **kwargs):
        response = self.render_view({
            "schema": "mercurio.view.v1",
            "version": 1,
            "kind": "explorer.model",
            "mode": "visualization",
            "model": {
                "version": 1,
                "kind": "model_explorer",
                "title": "Model Explorer",
                "root": seed_id,
                **kwargs,
            },
        })
        return response["modelExplorer"]

    def metatype_explorer(self, seed_id, **kwargs):
        response = self.render_view({
            "schema": "mercurio.view.v1",
            "version": 1,
            "kind": "explorer.metatype",
            "mode": "visualization",
            "model": {
                "version": 1,
                "kind": "metatype_explorer",
                "title": "Metatype Explorer",
                "root": seed_id,
                **kwargs,
            },
        })
        return response["metatypeExplorer"]

    def run_cell(self, request):
        self.requests.append(request)
        if request["kind"] == "analysis":
            capability = {
                "id": request["parameters"].get("capabilityId", "mercurio.dsl.analysis"),
                "status": "passed",
            }
            return {
                "cellId": request.get("cellId", "dsl.analysis"),
                "kind": "analysis",
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
            }
        if request["kind"] == "action":
            return {
                "cellId": request.get("cellId", "dsl.action"),
                "kind": "action",
                "status": "passed",
                "outputs": [
                    {
                        "id": "result",
                        "kind": "json",
                        "value": {
                            "schema": "mercurio.semantic_transaction.v1",
                            "status": "previewed",
                            "applied": False,
                        },
                    }
                ],
                "artifacts": [],
                "diagnostics": [],
                "metadata": {},
            }
        return {
            "cellId": request.get("cellId", "dsl.query"),
            "kind": request["kind"],
            "status": "passed",
            "outputs": [
                {
                    "id": "result",
                    "kind": "table",
                    "value": {"columns": ["value"], "rows": [[11]]},
                }
            ],
            "artifacts": [],
            "diagnostics": [],
            "metadata": {},
        }

    def dsl_schema(self):
        return {
            "element_kinds": ["RequirementUsage"],
            "fields": [],
            "stdlib_functions": ["ModelContext.requirements"],
        }


class RuntimeModelTests(unittest.TestCase):
    def test_native_model_exposes_semantic_snapshot_json(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        self.assertEqual(
            model.semantic_snapshot_json(),
            '[{"qualified_name": "Demo.Vehicle"}]',
        )

    def test_sidecar_model_reports_semantic_snapshot_requirement(self) -> None:
        model = Model.__new__(Model)
        model._workspace = None
        model._project = object()
        model._backend = object()

        with self.assertRaisesRegex(RuntimeError, "native workspace"):
            model.semantic_snapshot_json()

    def test_native_model_runs_dsl_cells(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        report = model.run_cell("model.parts().count()")

        self.assertEqual(report.result["rows"], [[7]])
        self.assertEqual(model.dsl("model.parts().count()")["rows"], [[7]])
        self.assertEqual(model.query("model.parts().count()")["rows"], [[7]])
        self.assertIn("ModelContext.parts", model.dsl_schema()["stdlib_functions"])

    def test_native_model_analysis_facade_runs_named_case(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        handle = model.analysis("PrintSequence")
        report = handle.run(run_id="facade-run")
        trace = handle.trace(run_id="facade-trace")

        self.assertEqual(handle.spec().case_ref.element_id, "analysis.Demo.PrintSequence")
        self.assertEqual(report.run_id, "facade-run")
        self.assertEqual(report.status, "passed")
        self.assertEqual(trace.scenario_id, "PrintSequence")

    def test_native_model_runs_analysis_dsl_cells(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        report = model.run_analysis_dsl("#{verdict: \"pass\"}", run_id="mass-check")

        self.assertEqual(report.kind, "analysis")
        self.assertEqual(report.capability_report["status"], "passed")
        self.assertEqual(model.analysis_dsl("#{verdict: \"pass\"}")["id"], "mercurio.dsl.analysis")

    def test_native_model_runs_action_dsl_cells(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        report = model.run_action_dsl('model.transaction("rename").preview()')

        self.assertEqual(report.kind, "action")
        self.assertEqual(report.result["status"], "previewed")
        self.assertFalse(model.preview_dsl("model.changes().preview()")["applied"])

    def test_native_model_exposes_shared_exploration_views(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        self.assertEqual(model.model_metadata()["user_element_count"], 1)
        self.assertEqual(model.graph()["nodes"][0]["label"], "Vehicle")
        self.assertEqual(model.search("vehicle")[0]["id"], "type.Demo.Vehicle")
        self.assertEqual(model.element_details("type.Demo.Vehicle")["label"], "Vehicle")
        self.assertEqual(
            model.model_explorer("type.Demo.Vehicle")["seed_id"],
            "type.Demo.Vehicle",
        )
        rendered = model.metatype_explorer_view("type.Demo.Vehicle")
        self.assertEqual(rendered["metatypeExplorer"]["seed_id"], "type.Demo.Vehicle")

    def test_native_model_checks_semantic_legality_through_core(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        report = model.can_relate("satisfy", "part", "part")

        self.assertEqual(report["status"], "Blocked")
        self.assertEqual(report["operation"]["kind"], "relationship")
        self.assertEqual(report["diagnostics"][0]["source"], "Rulepack")

    def test_native_model_gets_semantic_next_actions_through_core(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        report = model.semantic_next_actions(
            "part",
            element="HybridVehicle.vehicle",
            candidate_target_kinds=["requirement"],
            candidate_attributes=["text"],
        )

        self.assertEqual(report["schemaVersion"], "mercurio.semantic_next_actions.v1")
        self.assertEqual(report["elementKind"], "part")
        self.assertEqual(report["actions"][0]["operation"]["kind"], "addRelationship")

    def test_sidecar_model_runs_dsl_cells_through_project_api(self) -> None:
        project = FakeProject()
        model = Model.__new__(Model)
        model._workspace = None
        model._project = project
        model._backend = object()

        result = model.query_dsl("model.requirements().count()")

        self.assertEqual(result["rows"], [[11]])
        self.assertEqual(project.requests[0]["language"], "mercurio_dsl")
        self.assertIn("ModelContext.requirements", model.dsl_schema()["stdlib_functions"])

    def test_sidecar_model_runs_analysis_dsl_cells_through_project_api(self) -> None:
        project = FakeProject()
        model = Model.__new__(Model)
        model._workspace = None
        model._project = project
        model._backend = object()

        result = model.analysis_dsl("#{verdict: \"pass\"}", run_id="sidecar-analysis")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(project.requests[0]["kind"], "analysis")
        self.assertEqual(project.requests[0]["parameters"]["runId"], "sidecar-analysis")

    def test_sidecar_model_runs_action_dsl_cells_through_project_api(self) -> None:
        project = FakeProject()
        model = Model.__new__(Model)
        model._workspace = None
        model._project = project
        model._backend = object()

        result = model.action_dsl('model.transaction("rename").preview()')

        self.assertEqual(result["status"], "previewed")
        self.assertEqual(project.requests[0]["kind"], "action")
        self.assertEqual(project.requests[0]["language"], "mercurio_dsl")

    def test_sidecar_model_exposes_shared_exploration_views(self) -> None:
        project = FakeProject()
        model = Model.__new__(Model)
        model._workspace = None
        model._project = project
        model._backend = object()

        self.assertEqual(model.model_metadata()["user_element_count"], 2)
        self.assertEqual(model.graph(scope="full")["scope"], "full")
        self.assertEqual(model.search("req")[0]["label"], "req")
        self.assertEqual(model.element_details("type.Demo.Requirement")["label"], "Requirement")
        self.assertEqual(
            model.model_explorer("type.Demo.Requirement")["seed_id"],
            "type.Demo.Requirement",
        )
        rendered = model.render_view({
            "schema": "mercurio.view.v1",
            "version": 1,
            "kind": "explorer.metatype",
            "mode": "visualization",
            "model": {
                "version": 1,
                "kind": "metatype_explorer",
                "title": "Metatype Explorer",
                "root": "type.Demo.Requirement",
            },
        })
        self.assertEqual(rendered["metatypeExplorer"]["seed_id"], "type.Demo.Requirement")

    def test_sidecar_model_checks_semantic_legality_through_project_api(self) -> None:
        project = FakeProject()
        model = Model.__new__(Model)
        model._workspace = None
        model._project = project
        model._backend = object()

        report = model.can_write_attribute("requirement", "text")

        self.assertEqual(report["status"], "Allowed")
        self.assertEqual(project.requests[0]["operation"]["kind"], "attributeWrite")

    def test_sidecar_model_gets_semantic_next_actions_through_project_api(self) -> None:
        project = FakeProject()
        model = Model.__new__(Model)
        model._workspace = None
        model._project = project
        model._backend = object()

        report = model.semantic_next_actions(
            "part",
            element="HybridVehicle.vehicle",
            candidate_target_kinds=["requirement"],
            candidate_attributes=["text"],
            max_actions=4,
        )

        self.assertEqual(report["schemaVersion"], "mercurio.semantic_next_actions.v1")
        self.assertEqual(project.requests[0]["element_kind"], "part")
        self.assertEqual(project.requests[0]["element"], "HybridVehicle.vehicle")
        self.assertEqual(project.requests[0]["max_actions"], 4)

    def test_lab_model_delegates_semantic_legality_to_workspace_model(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())
        lab_model = LabModel(label="demo", _workspace="C:/models/demo")

        with patch("mercurio.lab._open_workspace_model", return_value=model) as opener:
            report = lab_model.can_relate("satisfy", "part", "part")

        opener.assert_called_once_with("C:/models/demo")
        self.assertEqual(report["status"], "Blocked")
        self.assertIs(lab_model.semantic_model(), model)

    def test_lab_model_delegates_semantic_next_actions_to_workspace_model(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())
        lab_model = LabModel(label="demo", _workspace="C:/models/demo")

        with patch("mercurio.lab._open_workspace_model", return_value=model) as opener:
            report = lab_model.semantic_next_actions(
                "part",
                candidate_target_kinds=["requirement"],
            )

        opener.assert_called_once_with("C:/models/demo")
        self.assertEqual(report["schemaVersion"], "mercurio.semantic_next_actions.v1")
        self.assertIs(lab_model.semantic_model(), model)


if __name__ == "__main__":
    unittest.main()

