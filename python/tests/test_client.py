from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from mercurio.backend import Mercurio
from mercurio.errors import MercurioBackendError
from mercurio.models import (
    AnalysisCaseInfo,
    AnalysisRunReport,
    AnalysisSpec,
    PartRef,
    SimulationTrace,
)
from mercurio.runtime import Model, RawWorkspace


class FakeMercurioHandler(BaseHTTPRequestHandler):
    workspaces: dict[str, dict[str, Any]] = {}
    requests: list[dict[str, Any]] = []
    next_workspace = 1

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/version":
            self.write_json(
                {"service": "mercurio-foundation", "version": "0.1.0", "apiVersion": 1}
            )
            return
        if parsed.path == "/api/health":
            self.write_json(
                {"service": "mercurio-foundation", "version": "0.1.0", "status": "ok"}
            )
            return
        if parsed.path == "/api/releases/sysml":
            self.write_json(
                {
                    "releases": [
                        {
                            "release": "2026-01",
                            "selector": "2026-01",
                            "profileId": "sysml-2.0-metamodel-0.57.0",
                            "status": "latest",
                            "sysmlVersion": "2.0",
                            "pilotReleaseTag": "2026-01",
                            "pilotImplementationVersion": "0.57.0",
                            "stdlibLocator": "file:stdlib/stdlib.full.kir.json",
                            "pythonWrapperModule": "mercurio_sysml_2_0",
                            "aliases": ["0.57.0", "pilot-0.57.0"],
                        },
                        {
                            "release": "2026-04",
                            "selector": "2026-04",
                            "profileId": "sysml-2.0-pilot-2026-04",
                            "status": "supported",
                            "sysmlVersion": "2.0.0",
                            "pilotReleaseTag": "2026-04",
                            "pilotImplementationVersion": "2026-04",
                            "stdlibLocator": "file:stdlib/stdlib.full.kir.json",
                            "pythonWrapperModule": "mercurio_sysml_2_0",
                            "aliases": ["pilot-2026-04"],
                        }
                    ]
                }
            )
            return
        if parsed.path == "/api/workspaces":
            self.write_json(list(self.workspaces.values()))
            return
        if parsed.path.endswith("/graph"):
            self.requests.append({"method": "GET", "path": parsed.path})
            self.write_json(
                {
                    "nodes": [
                        {
                            "id": "type.Printer",
                            "kind": "PartDefinition",
                            "properties": {
                                "declared_name": "printer",
                                "type": "type.VoronPrinter",
                            },
                        },
                        {
                            "id": "type.Printer.bed",
                            "kind": "PartUsage",
                            "properties": {
                                "declared_name": "bed",
                                "owner": "type.Printer",
                                "type": "type.HeatedBed",
                                "temperature": 22.0,
                                "heatRate": 2.3,
                            },
                        },
                    ],
                    "edges": [],
                }
            )
            return
        if parsed.path.endswith("/parts"):
            self.requests.append({"method": "GET", "path": parsed.path})
            self.write_json(
                [
                    {
                        "id": "type.Printer",
                        "name": "printer",
                        "kind": "VoronPrinter",
                        "elementKind": "Model::Systems::PartDefinition",
                        "parentId": None,
                        "depth": 0,
                        "attributes": {},
                    },
                    {
                        "id": "type.Printer.bed",
                        "name": "bed",
                        "kind": "HeatedBed",
                        "elementKind": "Model::Parts::PartUsage",
                        "parentId": "type.Printer",
                        "depth": 1,
                        "attributes": {"temperature": 22.0, "heatRate": 2.3},
                    },
                ]
            )
            return
        if parsed.path.endswith("/simulation/analysis-cases"):
            self.requests.append({"method": "GET", "path": parsed.path})
            self.write_json(
                [{"id": "analysis.PrintSequence", "label": "PrintSequence", "subjectCount": 1}]
            )
            return
        if parsed.path.endswith("/analysis/specs"):
            self.requests.append({"method": "GET", "path": parsed.path})
            self.write_json(
                [
                    {
                        "caseRef": {
                            "elementId": "analysis.PrintSequence",
                            "kind": "AnalysisCaseUsage",
                            "label": "PrintSequence",
                        },
                        "modelRevision": "demo-revision",
                        "subjects": [
                            {
                                "elementId": "part.Printer",
                                "kind": "PartUsage",
                                "label": "printer",
                            }
                        ],
                        "techniques": ["dynamic_behavior", "constraint_evaluation"],
                        "dynamicBehaviorBindings": [
                            {
                                "subject": {
                                    "elementId": "part.Printer",
                                    "kind": "PartUsage",
                                    "label": "printer",
                                },
                                "behavior": {
                                    "elementId": "state.Printer.lifecycle",
                                    "kind": "StateUsage",
                                    "label": "lifecycle",
                                },
                                "kind": "state_machine",
                            }
                        ],
                        "executionContext": {
                            "initialValues": {
                                "part.Printer": {"bed_temperature": 22.0}
                            },
                            "clock": {"maxSteps": 12, "fixedStepS": 1.0},
                        },
                        "executionPlan": {
                            "steps": [
                                {
                                    "kind": "dynamic_behavior",
                                    "label": "Execute dynamic behavior",
                                    "techniques": ["dynamic_behavior"],
                                    "elements": [
                                        {
                                            "elementId": "part.Printer.lifecycle",
                                            "kind": "StateUsage",
                                        }
                                    ],
                                }
                            ]
                        },
                        "expectedArtifacts": [
                            {
                                "kind": "simulation_trace",
                                "schema": "mercurio.simulation.trace.v1",
                            }
                        ],
                        "readiness": "ready",
                        "readinessDiagnostics": [],
                    }
                ]
            )
            return
        if parsed.path.endswith("/editor/file"):
            query = parse_qs(parsed.query)
            self.write_json({"path": query["path"][0], "content": "package Demo {}"})
            return
        self.write_error(404, "not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self.read_json()
        self.requests.append({"method": "POST", "path": parsed.path, "json": payload})
        if parsed.path == "/api/workspaces":
            workspace_id = f"ws_{self.next_workspace:016x}"
            type(self).next_workspace += 1
            data = {
                "workspaceId": workspace_id,
                "workspaceRoot": payload["path"],
                "activePath": None,
                "project": {},
            }
            self.workspaces[workspace_id] = data
            self.write_json(data)
            return
        if parsed.path.endswith("/semantic/project/compile"):
            self.write_json(
                {
                    "ok": True,
                    "project_path": payload["project_path"],
                    "file_count": 1,
                    "success_count": 1,
                    "failure_count": 0,
                    "results": [{"path": "model.sysml", "ok": True}],
                }
            )
            return
        if parsed.path.endswith("/editor/parse"):
            self.write_json({"ok": True, "diagnostics": [], "element_count": 1})
            return
        if parsed.path.endswith("/analysis/cases/run"):
            trace = {
                "scenario_id": payload["id"],
                "subject_id": "bed",
                "channels": [
                    {
                        "id": "bed.temperature",
                        "unit": "C",
                        "source": "rate_effect",
                    },
                ],
                "status": "completed",
                "timeline": [
                    {
                        "t": 0.0,
                        "states": {"bed": ["Cold"]},
                        "values": {"bed|temperature": 22.0},
                        "events": [],
                    },
                    {
                        "t": 5.0,
                        "states": {"bed": ["Heating"]},
                        "values": {"bed|temperature": 33.5},
                        "events": [],
                    },
                ],
            }
            run_id = payload.get("runId", "api.analysis_case")
            self.write_json(
                {
                    "run_id": run_id,
                    "capability_id": "sysml.behavior.dynamic",
                    "status": "passed",
                    "target": {"kind": "element", "element_id": payload["id"]},
                    "artifacts": [
                        {
                            "id": f"artifact.{run_id}.simulation_trace",
                            "kind": "simulation_trace",
                            "schema": "mercurio.simulation.trace.v1",
                            "digest": "sha256:demo",
                            "element_refs": [
                                {
                                    "element_id": payload["id"],
                                    "label": "PrintSequence",
                                }
                            ],
                            "payload": trace,
                        },
                        {
                            "id": f"artifact.{run_id}.constraints",
                            "kind": "constraint_analysis_summary",
                            "schema": "mercurio.capability.sysml_constraint_analysis.v1",
                            "digest": "sha256:constraints",
                            "payload": {
                                "schema": "mercurio.capability.sysml_constraint_analysis.v1",
                                "constraintCount": 1,
                                "requirementCheckCount": 1,
                                "result": {
                                    "requirements": [
                                        {
                                            "id": "req.maxMass",
                                            "status": "satisfied",
                                            "margin": 5.0,
                                        }
                                    ]
                                },
                            },
                        }
                    ],
                    "evidence": {
                        "nodes": [
                            {
                                "id": f"evidence.{run_id}",
                                "kind": "analysis_run",
                                "label": "Simulation analysis case",
                                "element_refs": [
                                    {
                                        "element_id": payload["id"],
                                        "label": "PrintSequence",
                                    }
                                ],
                                "properties": {"scenario_id": payload["id"]},
                            }
                        ],
                        "edges": [],
                    },
                    "diagnostics": [],
                    "limitations": [],
                }
            )
            return
        if parsed.path.endswith("/simulation/run-analysis"):
            self.write_json(
                {
                    "scenario_id": payload["id"],
                    "subject_id": "bed",
                    "channels": [
                        {
                            "id": "bed.temperature",
                            "unit": "C",
                            "source": "rate_effect",
                        }
                    ],
                    "status": "completed",
                    "timeline": [
                        {
                            "t": 0.0,
                            "states": {"bed": ["Cold"]},
                            "values": {"bed|temperature": 22.0},
                            "events": [],
                        },
                        {
                            "t": 5.0,
                            "states": {"bed": ["Heating"]},
                            "values": {"bed|temperature": 33.5},
                            "events": [],
                        },
                    ],
                }
            )
            return
        self.write_error(404, "not found")

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        self.requests.append(
            {"method": "PUT", "path": parsed.path, "json": self.read_json()}
        )
        self.send_response(204)
        self.end_headers()

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        workspace_id = parsed.path.rsplit("/", 1)[-1]
        self.workspaces.pop(workspace_id, None)
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def write_json(self, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_error(self, status: int, message: str) -> None:
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "text/plain")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ClientTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeMercurioHandler.workspaces = {}
        FakeMercurioHandler.requests = []
        FakeMercurioHandler.next_workspace = 1
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeMercurioHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.backend = Mercurio.connect(f"http://{host}:{port}")

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_version_handshake_and_project_open(self) -> None:
        version = self.backend.version()
        self.assertEqual(version.api_version, 1)
        project = self.backend.open_project("C:/models/demo")
        self.assertEqual(project.project_id, "ws_0000000000000001")

    def test_sysml_release_catalog(self) -> None:
        releases = self.backend.list_sysml_releases()

        self.assertEqual(releases[0].release, "2026-01")
        self.assertEqual(releases[0].selector, "2026-01")
        self.assertEqual(releases[0].pilot_release_tag, "2026-01")
        self.assertEqual(releases[0].pilot_implementation_version, "0.57.0")
        self.assertEqual(releases[0].profile_id, "sysml-2.0-metamodel-0.57.0")
        self.assertIn("0.57.0", releases[0].aliases)
        self.assertIn("pilot-0.57.0", releases[0].aliases)
        self.assertEqual(releases[1].release, "2026-04")
        self.assertEqual(releases[1].selector, "2026-04")
        self.assertEqual(releases[1].profile_id, "sysml-2.0-pilot-2026-04")
        self.assertIn("pilot-2026-04", releases[1].aliases)

    def test_sysml_release_selector_resolution(self) -> None:
        by_selector = self.backend.resolve_sysml_release("2026-04")
        by_alias = self.backend.resolve_sysml_release("pilot-2026-04")
        by_profile = self.backend.resolve_sysml_release("sysml-2.0-pilot-2026-04")

        self.assertEqual(by_selector.profile_id, "sysml-2.0-pilot-2026-04")
        self.assertEqual(by_alias.profile_id, by_selector.profile_id)
        self.assertEqual(by_profile.profile_id, by_selector.profile_id)

        with self.assertRaisesRegex(ValueError, "unknown SysML release selector"):
            self.backend.resolve_sysml_release("2025-99")

    def test_compile_project_preview_shapes_staged_files(self) -> None:
        project = self.backend.open_project("C:/models/demo")
        result = project.compile_project_preview(
            staged_files={"model.sysml": "package Demo {}"}
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.file_count, 1)
        request = FakeMercurioHandler.requests[-1]
        self.assertEqual(
            request["path"],
            "/api/workspaces/ws_0000000000000001/semantic/project/compile",
        )
        self.assertEqual(
            request["json"]["staged_files"],
            [{"path": "model.sysml", "content": "package Demo {}"}],
        )

    def test_save_file_uses_project_scoped_put(self) -> None:
        project = self.backend.open_project("C:/models/demo")
        project.save_file("model.sysml", "package Demo {}")
        request = FakeMercurioHandler.requests[-1]
        self.assertEqual(request["method"], "PUT")
        self.assertEqual(
            request["path"],
            "/api/workspaces/ws_0000000000000001/editor/file",
        )

    def test_backend_errors_are_mapped(self) -> None:
        with self.assertRaises(MercurioBackendError) as context:
            self.backend.client.get("/api/missing")
        self.assertEqual(context.exception.status, 404)

    def test_simulation_trace_channel_extraction(self) -> None:
        trace = SimulationTrace.from_json(
            {
                "scenario_id": "s1",
                "subject_id": "bed",
                "channels": [
                    {"id": "bed.temperature", "unit": "C", "source": "rate_effect"}
                ],
                "status": "completed",
                "timeline": [
                    {
                        "t": 0.0,
                        "states": {"bed": ["Cold"]},
                        "values": {"bed|temperature": 22.0},
                        "events": [],
                    },
                    {
                        "t": 5.0,
                        "states": {"bed": ["Heating"]},
                        "values": {"bed|temperature": 33.5},
                        "events": [],
                    },
                    {
                        "t": 10.0,
                        "states": {"bed": ["Heating"]},
                        "values": {"bed|temperature": 45.0},
                        "events": [],
                    },
                ],
            }
        )

        channel = trace.channel("bed.temperature")
        self.assertEqual(channel.times, [0.0, 5.0, 10.0])
        self.assertEqual(channel.values, [22.0, 33.5, 45.0])

        states = trace.states("bed")
        self.assertEqual(states.times, [0.0, 5.0, 10.0])
        self.assertEqual(states.states, [["Cold"], ["Heating"], ["Heating"]])
        self.assertEqual(trace.duration, 10.0)

    def test_analysis_case_info_from_json(self) -> None:
        info = AnalysisCaseInfo.from_json(
            {"id": "abc", "label": "PrintSequence", "subjectCount": 3}
        )
        self.assertEqual(info.id, "abc")
        self.assertEqual(info.label, "PrintSequence")
        self.assertEqual(info.subject_count, 3)

    def test_analysis_spec_from_json(self) -> None:
        spec = AnalysisSpec.from_json(
            {
                "caseRef": {
                    "elementId": "analysis.PrintSequence",
                    "kind": "AnalysisCaseUsage",
                    "label": "PrintSequence",
                },
                "modelRevision": "demo-revision",
                "subjects": [{"elementId": "part.Printer", "kind": "PartUsage"}],
                "techniques": ["dynamic_behavior"],
                "dynamicBehaviorBindings": [
                    {
                        "subject": {"elementId": "part.Printer", "kind": "PartUsage"},
                        "behavior": {
                            "elementId": "state.Printer.lifecycle",
                            "kind": "StateUsage",
                            "label": "lifecycle",
                        },
                        "kind": "state_machine",
                    }
                ],
                "executionContext": {
                    "initialValues": {"part.Printer": {"bed_temperature": 22.0}},
                    "clock": {"maxSteps": 12},
                },
                "executionPlan": {
                    "steps": [
                        {
                            "kind": "dynamic_behavior",
                            "label": "Execute dynamic behavior",
                        }
                    ]
                },
                "expectedArtifacts": [
                    {
                        "kind": "simulation_trace",
                        "schema": "mercurio.simulation.trace.v1",
                    }
                ],
                "readiness": "ready",
            }
        )

        self.assertEqual(spec.case_ref.label, "PrintSequence")
        self.assertEqual(spec.model_revision, "demo-revision")
        self.assertEqual(spec.execution_context.clock.max_steps, 12)
        self.assertEqual(
            spec.execution_context.initial_values["part.Printer"]["bed_temperature"],
            22.0,
        )
        self.assertEqual(spec.dynamic_behavior_bindings[0].kind, "state_machine")
        self.assertEqual(
            spec.dynamic_behavior_bindings[0].behavior.label,
            "lifecycle",
        )
        self.assertEqual(spec.execution_plan.steps[0].kind, "dynamic_behavior")
        self.assertEqual(spec.expected_artifacts[0].kind, "simulation_trace")

    def test_analysis_run_report_from_json(self) -> None:
        report = AnalysisRunReport.from_json(
            {
                "run_id": "pytest.run",
                "capability_id": "sysml.behavior.dynamic",
                "status": "passed",
                "target": {
                    "kind": "element",
                    "element_id": "analysis.PrintSequence",
                },
                "artifacts": [
                    {
                        "id": "artifact.pytest.run.simulation_trace",
                        "kind": "simulation_trace",
                        "schema": "mercurio.simulation.trace.v1",
                        "digest": "sha256:demo",
                        "element_refs": [
                            {
                                "element_id": "analysis.PrintSequence",
                                "label": "PrintSequence",
                            }
                        ],
                        "payload": {
                            "scenario_id": "analysis.PrintSequence",
                            "subject_id": "bed",
                            "channels": [
                                {
                                    "id": "bed.temperature",
                                    "unit": "C",
                                    "source": "rate_effect",
                                }
                            ],
                            "status": "completed",
                            "timeline": [
                                {
                                    "t": 0.0,
                                    "states": {"bed": ["Cold"]},
                                    "values": {"bed|temperature": 22.0},
                                    "events": [],
                                }
                            ],
                        },
                    },
                    {
                        "id": "artifact.pytest.run.constraints",
                        "kind": "constraint_analysis_summary",
                        "schema": "mercurio.capability.sysml_constraint_analysis.v1",
                        "digest": "sha256:constraint-demo",
                        "element_refs": [
                            {
                                "element_id": "req.maxMass",
                                "label": "maxMass",
                            }
                        ],
                        "payload": {
                            "schema": "mercurio.capability.sysml_constraint_analysis.v1",
                            "analysisScope": "authored_model",
                            "constraintCount": 1,
                            "requirementCheckCount": 1,
                            "variableCount": 4,
                            "diagnosticCount": 0,
                            "result": {
                                "constraints": [
                                    {
                                        "id": "constraint.totalMass",
                                        "status": "satisfied",
                                    }
                                ],
                                "requirements": [
                                    {
                                        "id": "req.maxMass",
                                        "status": "satisfied",
                                    }
                                ],
                                "variables": [
                                    {"id": "totalMass", "value": 120.0},
                                    {"id": "maxMass", "value": 125.0},
                                ],
                                "diagnostics": [],
                            },
                        },
                    },
                    {
                        "id": "artifact.pytest.run.activity",
                        "kind": "activity_execution_summary",
                        "schema": "mercurio.analysis.activity_execution_summary.v1",
                        "digest": "sha256:activity-demo",
                        "element_refs": [
                            {
                                "element_id": "action.Printer.warmup",
                                "label": "warmup",
                            }
                        ],
                        "payload": {
                            "schema": "mercurio.analysis.activity_execution_summary.v1",
                            "analysisCase": {
                                "elementId": "analysis.PrintSequence",
                                "kind": "AnalysisCaseUsage",
                                "label": "PrintSequence",
                            },
                            "bindingCount": 1,
                            "status": "passed",
                            "executionState": "completed",
                            "bindings": [
                                {
                                    "subject": {
                                        "elementId": "part.Printer",
                                        "kind": "PartUsage",
                                        "label": "printer",
                                    },
                                    "behavior": {
                                        "elementId": "action.Printer.warmup",
                                        "kind": "ActionUsage",
                                        "label": "warmup",
                                    },
                                    "kind": "activity",
                                    "status": "passed",
                                    "executionState": "completed",
                                    "nodeCount": 2,
                                    "edgeCount": 1,
                                    "steps": [
                                        {
                                            "index": 0,
                                            "nodes": [
                                                {
                                                    "elementId": "action.Printer.warmup.home",
                                                    "kind": "ActionUsage",
                                                    "label": "home",
                                                }
                                            ],
                                        },
                                        {
                                            "index": 1,
                                            "nodes": [
                                                {
                                                    "elementId": "action.Printer.warmup.heat",
                                                    "kind": "ActionUsage",
                                                    "label": "heatBed",
                                                }
                                            ],
                                        },
                                    ],
                                    "flows": [
                                        {
                                            "id": "flow.Printer.warmup.home_to_heat",
                                            "source": "action.Printer.warmup.home",
                                            "target": "action.Printer.warmup.heat",
                                        }
                                    ],
                                    "blockedNodes": [],
                                }
                            ],
                        },
                    },
                ],
                "evidence": {
                    "nodes": [
                        {
                            "id": "evidence.pytest.run",
                            "kind": "analysis_run",
                            "label": "Simulation analysis case",
                            "element_refs": [
                                {
                                    "element_id": "analysis.PrintSequence",
                                    "label": "PrintSequence",
                                }
                            ],
                            "properties": {
                                "scenario_id": "analysis.PrintSequence",
                            },
                        }
                    ],
                    "edges": [],
                },
            }
        )

        self.assertEqual(report.run_id, "pytest.run")
        self.assertEqual(report.capability_id, "sysml.behavior.dynamic")
        self.assertEqual(report.artifacts[0].schema, "mercurio.simulation.trace.v1")
        self.assertEqual(
            report.artifacts[0].element_refs[0].element_id,
            "analysis.PrintSequence",
        )
        self.assertEqual(report.evidence.nodes[0].kind, "analysis_run")
        self.assertEqual(report.simulation_trace().channel("temperature").values, [22.0])
        self.assertEqual(
            report.constraint_summary()["result"]["requirements"][0]["status"],
            "satisfied",
        )
        self.assertEqual(
            report.activity_summary()["bindings"][0]["behavior"]["elementId"],
            "action.Printer.warmup",
        )
        self.assertEqual(
            report.activity_summary()["bindings"][0]["steps"][1]["nodes"][0][
                "elementId"
            ],
            "action.Printer.warmup.heat",
        )

    def test_project_simulation_methods_use_scoped_routes(self) -> None:
        project = self.backend.open_project("C:/models/demo")

        specs = project.list_analysis_specs()
        self.assertEqual(specs[0].case_ref.label, "PrintSequence")
        self.assertEqual(specs[0].execution_plan.steps[0].kind, "dynamic_behavior")
        self.assertEqual(
            specs[0].dynamic_behavior_bindings[0].behavior.element_id,
            "state.Printer.lifecycle",
        )
        self.assertEqual(
            FakeMercurioHandler.requests[-1]["path"],
            "/api/workspaces/ws_0000000000000001/analysis/specs",
        )

        cases = project.list_analysis_cases()
        self.assertEqual(cases[0].label, "PrintSequence")
        self.assertEqual(
            FakeMercurioHandler.requests[-1]["path"],
            "/api/workspaces/ws_0000000000000001/simulation/analysis-cases",
        )

        report = project.run_analysis_report("analysis.PrintSequence", run_id="pytest.run")
        self.assertEqual(report.run_id, "pytest.run")
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.artifact("simulation_trace").kind, "simulation_trace")
        self.assertEqual(report.simulation_trace().channel("temperature").values, [22.0, 33.5])
        self.assertEqual(
            FakeMercurioHandler.requests[-1]["path"],
            "/api/workspaces/ws_0000000000000001/analysis/cases/run",
        )
        self.assertEqual(FakeMercurioHandler.requests[-1]["json"]["runId"], "pytest.run")

        trace = project.run_analysis("analysis.PrintSequence")
        self.assertEqual(trace.status, "completed")
        self.assertEqual(trace.channel("temperature").values, [22.0, 33.5])
        self.assertEqual(
            FakeMercurioHandler.requests[-1]["path"],
            "/api/workspaces/ws_0000000000000001/analysis/cases/run",
        )

    def test_model_runtime_analysis_spec_finder(self) -> None:
        project = self.backend.open_project("C:/models/demo")
        rt = Model.__new__(Model)
        rt._backend = self.backend
        rt._project = project
        from mercurio.runtime import RawWorkspace as _RW

        rt.raw = _RW(project)

        spec = rt.analysis_case_spec("PrintSequence")
        self.assertEqual(spec.case_ref.element_id, "analysis.PrintSequence")
        self.assertEqual(spec.execution_context.clock.max_steps, 12)

        same_spec = rt.analysis_case_spec("analysis.PrintSequence")
        self.assertEqual(same_spec.case_ref.label, "PrintSequence")

        report = rt.run_analysis_report("analysis.PrintSequence", run_id="model.run")
        self.assertEqual(report.run_id, "model.run")
        self.assertEqual(report.simulation_trace().status, "completed")

        with self.assertRaises(KeyError):
            rt.analysis_case_spec("missing")

    def test_part_ref_tree_structure(self) -> None:
        root = PartRef(
            id="type.Printer",
            name="printer",
            kind="VoronPrinter",
            element_kind="PartDefinition",
            parent=None,
            depth=0,
            _properties={},
        )
        child = PartRef(
            id="type.Printer.bed",
            name="bed",
            kind="HeatedBed",
            element_kind="PartUsage",
            parent=root,
            depth=1,
            _properties={"temperature": 22.0, "heatRate": 2.3},
        )
        all_parts = [root, child]

        self.assertIs(child.parent, root)
        self.assertEqual(child.depth, 1)
        self.assertEqual(root.children(all_parts), [child])
        self.assertEqual(child.attr("temperature"), 22.0)
        self.assertEqual(child.attr("missing", 99), 99)
        self.assertIn("temperature", child.attrs())
        self.assertIn("heatRate", child.attrs())

    def test_project_parts_uses_parts_endpoint(self) -> None:
        project = self.backend.open_project("C:/models/demo")
        parts = project.parts()
        self.assertEqual(
            FakeMercurioHandler.requests[-1]["path"],
            "/api/workspaces/ws_0000000000000001/parts",
        )
        self.assertEqual([p.name for p in parts], ["printer", "bed"])
        self.assertEqual(parts[1].parent, parts[0])
        self.assertEqual(parts[1].depth, 1)
        self.assertEqual(parts[1].attr("temperature"), 22.0)
        self.assertEqual(parts[1].attr("missing", 99), 99)

    def test_model_runtime_part_finder(self) -> None:
        project = self.backend.open_project("C:/models/demo")
        rt = Model.__new__(Model)
        rt._backend = self.backend
        rt._project = project
        from mercurio.runtime import RawWorkspace as _RW
        rt.raw = _RW(project)

        bed = rt.part("bed")
        self.assertEqual(bed.name, "bed")
        self.assertEqual(bed.attr("temperature"), 22.0)

        printer = rt.part("type.Printer")
        self.assertEqual(printer.name, "printer")

        with self.assertRaises(KeyError):
            rt.part("nonexistent")

    def test_model_runtime_raw_delegates(self) -> None:
        project = self.backend.open_project("C:/models/demo")
        rt = Model.__new__(Model)
        rt._backend = self.backend
        rt._project = project
        from mercurio.runtime import RawWorkspace as _RW
        rt.raw = _RW(project)

        graph = rt.raw.graph()
        self.assertIn("nodes", graph)
        self.assertEqual(
            FakeMercurioHandler.requests[-1]["path"],
            "/api/workspaces/ws_0000000000000001/graph",
        )


if __name__ == "__main__":
    unittest.main()
