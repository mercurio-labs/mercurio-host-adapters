from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import contextmanager
from typing import Iterator

from mercurio_capability import CapabilityRequest, CapabilityRunner, Finding, ReasoningReport
from mercurio.capability import capability, run


DESCRIPTOR = {
    "id": "org.example.test",
    "kind": "mercurio.capability.kind/static-analysis",
    "name": "Test Capability",
    "version": "0.1.0",
    "api_version": "0.1",
    "deterministic": True,
    "input_artifact_kinds": ["kir"],
    "output_artifact_kinds": ["reasoning_report"],
}

REQUEST = {
    "request_id": "req-1",
    "capability_id": "org.example.test",
    "context": {
        "context_id": "ctx.accepted",
        "kind": "accepted",
        "artifact": {
            "artifact_key": "sha256-test",
            "kir_schema_version": "0.1",
        },
    },
    "parameters": {"mode": "strict"},
    "kir": {},
    "graph_facts": [],
}


@contextmanager
def captured_stdio(input_payload: object) -> Iterator[io.StringIO]:
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    output = io.StringIO()
    sys.stdin = io.StringIO(json.dumps(input_payload))
    sys.stdout = output
    try:
        yield output
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout


class CapabilityRunnerTests(unittest.TestCase):
    def test_main_package_capability_facade_reexports_runner_helpers(self) -> None:
        self.assertIs(capability, CapabilityRunner.capability)
        self.assertIs(run, CapabilityRunner.run)

    def test_runner_writes_reasoning_run_response(self) -> None:
        def analyze(request: CapabilityRequest) -> ReasoningReport:
            self.assertEqual(request.param("mode"), "strict")
            return request.report_passed(
                findings=[
                    Finding.info(
                        "finding.ok",
                        "Analysis completed",
                        "The capability ran successfully.",
                    )
                ]
            )

        with captured_stdio(REQUEST) as output:
            CapabilityRunner.run(analyze, capability_descriptor=DESCRIPTOR)

        response = json.loads(output.getvalue())
        self.assertEqual(response["metadata"]["runner"], "mercurio_capability/0.1")
        self.assertEqual(response["report"]["request_id"], "req-1")
        self.assertEqual(response["report"]["capability"]["id"], "org.example.test")
        self.assertEqual(response["report"]["status"], "passed")
        self.assertEqual(response["report"]["findings"][0]["severity"], "info")

    def test_runner_rejects_invalid_descriptor(self) -> None:
        def analyze(request: CapabilityRequest) -> ReasoningReport:
            return request.report_passed()

        descriptor = dict(DESCRIPTOR)
        descriptor.pop("kind")
        with captured_stdio(REQUEST) as output:
            with self.assertRaises(SystemExit) as exit_context:
                CapabilityRunner.run(analyze, capability_descriptor=descriptor)

        self.assertEqual(exit_context.exception.code, 1)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "descriptor_error")

    def test_runner_rejects_invalid_request(self) -> None:
        def analyze(request: CapabilityRequest) -> ReasoningReport:
            return request.report_passed()

        request = dict(REQUEST)
        request.pop("context")
        with captured_stdio(request) as output:
            with self.assertRaises(SystemExit) as exit_context:
                CapabilityRunner.run(analyze, capability_descriptor=DESCRIPTOR)

        self.assertEqual(exit_context.exception.code, 1)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "request_error")

    def test_runner_wraps_capability_exception(self) -> None:
        def analyze(request: CapabilityRequest) -> ReasoningReport:
            raise RuntimeError("boom")

        with captured_stdio(REQUEST) as output:
            with self.assertRaises(SystemExit) as exit_context:
                CapabilityRunner.run(analyze, capability_descriptor=DESCRIPTOR)

        self.assertEqual(exit_context.exception.code, 1)
        error = json.loads(output.getvalue())["error"]
        self.assertEqual(error["code"], "capability_error")
        self.assertIn("boom", error["message"])

    def test_runner_rejects_invalid_report_shape(self) -> None:
        def analyze(request: CapabilityRequest) -> ReasoningReport:
            return request.report_passed(
                findings=[Finding("bad", "Bad", "severe", "Invalid severity")]
            )

        with captured_stdio(REQUEST) as output:
            with self.assertRaises(SystemExit) as exit_context:
                CapabilityRunner.run(analyze, capability_descriptor=DESCRIPTOR)

        self.assertEqual(exit_context.exception.code, 1)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "response_error")


if __name__ == "__main__":
    unittest.main()
