"""Showcase the Phase 1-7 analysis execution API from Python.

Run this against a Mercurio project/model that contains an AnalysisCaseDefinition:

    python python/examples/analysis_execution_showcase.py C:/models/printer --case PrintSequence

The script demonstrates:

- Phase 1: inspect the AnalysisSpec before execution.
- Phase 2: run an analysis case and inspect the AnalysisRunReport.
- Phase 3: read constraint/calculation/verification summaries.
- Phase 4-5: read activity execution summaries.
- Phase 6: inspect constraint-derived values in the dynamic trace.
- Phase 7: inspect rate and lookup-table continuous channels.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

import mercurio
from mercurio.models import AnalysisRunReport, AnalysisSpec, SimulationTrace


def main() -> None:
    args = parse_args()

    with mercurio.open(args.model) as model:
        spec = model.analysis_case_spec(args.case)
        print_spec(spec)

        report = model.run_analysis_report(
            spec.case_ref.element_id,
            run_id=args.run_id,
        )
        print_report(report)

        maybe_print_trace(report, args.subject, args.channels)
        maybe_print_constraint_summary(report)
        maybe_print_activity_summary(report)
        assert_harness_expectations(
            report,
            require_passed=args.require_passed,
            require_all_requirements=args.require_all_requirements,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Mercurio analysis case and print all Phase 1-7 artifacts.",
    )
    parser.add_argument(
        "model",
        help="Path accepted by mercurio.open(), such as a project directory or model file.",
    )
    parser.add_argument(
        "--case",
        default="PrintSequence",
        help="Analysis case label or element id.",
    )
    parser.add_argument(
        "--run-id",
        default="python.analysis-showcase",
        help="Stable run id to stamp on produced artifacts.",
    )
    parser.add_argument(
        "--subject",
        default=None,
        help="Optional subject id or short suffix for state timeline display.",
    )
    parser.add_argument(
        "--channels",
        nargs="*",
        default=None,
        help=(
            "Optional channel ids to print. If omitted, the script prints every "
            "channel listed in the trace."
        ),
    )
    parser.add_argument(
        "--require-passed",
        action="store_true",
        help="Exit non-zero unless the AnalysisRunReport status is passed.",
    )
    parser.add_argument(
        "--require-all-requirements",
        action="store_true",
        help=(
            "Exit non-zero unless every requirement in the constraint summary "
            "is satisfied or passed."
        ),
    )
    return parser.parse_args()


def print_spec(spec: AnalysisSpec) -> None:
    print_header("Analysis Spec")
    print(f"case: {display_ref(spec.case_ref)}")
    print(f"model revision: {spec.model_revision or '<unknown>'}")
    print(f"readiness: {spec.readiness}")
    print(f"techniques: {', '.join(spec.techniques) or '<none>'}")
    print_refs("subjects", spec.subjects)
    print_refs("inputs", spec.inputs)
    print_refs("assumptions", spec.assumptions)
    print_refs("objectives", spec.objectives)
    print_refs("calculations", spec.calculations)
    print_refs("constraints", spec.constraints)
    print_refs("requirements", spec.requirements)
    print_refs("verification cases", spec.verification_cases)
    print_refs("views", spec.views)
    print_refs("concerns", spec.concerns)
    print_execution_context(spec)

    if spec.dynamic_behavior_bindings:
        print("dynamic behavior bindings:")
        for binding in spec.dynamic_behavior_bindings:
            print(
                f"  - {display_ref(binding.subject)} -> "
                f"{binding.kind}: {display_ref(binding.behavior)}"
            )
    else:
        print("dynamic behavior bindings: <none>")

    if spec.execution_plan.steps:
        print("execution plan:")
        for index, step in enumerate(spec.execution_plan.steps, start=1):
            label = f" - {step.label}" if step.label else ""
            techniques = (
                f" techniques={','.join(step.techniques)}" if step.techniques else ""
            )
            print(f"  {index}. {step.kind}{label}{techniques}")
            for element in step.elements:
                print(f"     uses {display_ref(element)}")
    else:
        print("execution plan: <empty>")

    if spec.expected_artifacts:
        print("expected artifacts:")
        for artifact in spec.expected_artifacts:
            print(f"  - {artifact.kind} ({artifact.schema})")
    else:
        print("expected artifacts: <none>")

    if spec.readiness_diagnostics:
        print("readiness diagnostics:")
        for diagnostic in spec.readiness_diagnostics:
            print(f"  - [{diagnostic.severity}] {diagnostic.code}: {diagnostic.message}")


def print_execution_context(spec: AnalysisSpec) -> None:
    context = spec.execution_context
    if context.initial_values:
        print("initial values:")
        for subject_id, values in context.initial_values.items():
            print(f"  - {subject_id}: {json.dumps(values, sort_keys=True)}")
    else:
        print("initial values: <none>")

    if context.clock is not None:
        clock_values = {
            "max_steps": context.clock.max_steps,
            "step_duration_s": context.clock.step_duration_s,
            "max_time_s": context.clock.max_time_s,
            "fixed_step_s": context.clock.fixed_step_s,
            "sample_interval_s": context.clock.sample_interval_s,
            "change_loop_limit": context.clock.change_loop_limit,
        }
        configured = {
            key: value for key, value in clock_values.items() if value is not None
        }
        print(
            "clock: "
            + (json.dumps(configured, sort_keys=True) if configured else "<defaults>")
        )
    else:
        print("clock: <default>")

    if context.provider_bindings:
        print(f"provider bindings: {json.dumps(context.provider_bindings, sort_keys=True)}")
    else:
        print("provider bindings: <none>")


def print_report(report: AnalysisRunReport) -> None:
    print_header("Analysis Run Report")
    print(f"run id: {report.run_id}")
    print(f"capability: {report.capability_id}")
    print(f"status: {report.status}")
    print("artifacts:")
    for artifact in report.artifacts:
        print(f"  - {artifact.kind} ({artifact.schema}) digest={artifact.digest}")

    print("evidence:")
    print(f"  nodes: {len(report.evidence.nodes)}")
    for node in report.evidence.nodes[:5]:
        print(f"    - {node.kind}: {node.label}")
    if len(report.evidence.nodes) > 5:
        print(f"    ... {len(report.evidence.nodes) - 5} more")
    print(f"  edges: {len(report.evidence.edges)}")

    if report.diagnostics:
        print("diagnostics:")
        for diagnostic in report.diagnostics:
            element = (
                f" element={diagnostic.element.element_id}"
                if diagnostic.element is not None
                else ""
            )
            print(
                f"  - [{diagnostic.severity}] {diagnostic.code}: "
                f"{diagnostic.message}{element}"
            )

    if report.limitations:
        print("limitations:")
        for limitation in report.limitations:
            print(f"  - {limitation}")


def maybe_print_trace(
    report: AnalysisRunReport,
    subject_id: str | None,
    requested_channels: list[str] | None,
) -> None:
    try:
        trace = report.simulation_trace()
    except KeyError:
        return

    print_header("Simulation Trace")
    print(f"scenario: {trace.scenario_id}")
    print(f"primary subject: {trace.subject_id}")
    print(f"status: {trace.status}")

    source_counts = Counter(channel.source for channel in trace.channels)
    print("channel sources:")
    for source, count in sorted(source_counts.items()):
        print(f"  - {source}: {count}")

    print("channels:")
    channels = requested_channels or [channel.id for channel in trace.channels]
    for channel_id in channels:
        data = trace.channel(channel_id)
        if not data.values:
            print(f"  - {channel_id}: <no samples>")
            continue
        first_t, first_value = data.as_pairs()[0]
        last_t, last_value = data.as_pairs()[-1]
        source = trace_channel_source(trace, channel_id)
        print(
            f"  - {channel_id} [{source}]: "
            f"{first_value!r} at t={first_t:g} -> {last_value!r} at t={last_t:g} "
            f"({len(data.values)} samples)"
        )

    if subject_id is not None:
        states = trace.states(subject_id)
        print(f"states for {subject_id}:")
        state_pairs = list(zip(states.times, states.states))
        if not state_pairs:
            print("  <no state samples>")
        for t, active in state_pairs[:12]:
            print(f"  - t={t:g}: {', '.join(active)}")
        if len(state_pairs) > 12:
            print(f"  ... {len(state_pairs) - 12} more state samples")

    derived_channels = [
        channel.id for channel in trace.channels if channel.source == "derived_constraint"
    ]
    if derived_channels:
        print("constraint-derived dynamic channels:")
        for channel_id in derived_channels:
            pairs = trace.channel(channel_id).as_pairs()
            print(f"  - {channel_id}: {preview_pairs(pairs)}")

    lookup_channels = [
        channel.id for channel in trace.channels if channel.source == "lookup_table"
    ]
    if lookup_channels:
        print("lookup-table continuous channels:")
        for channel_id in lookup_channels:
            pairs = trace.channel(channel_id).as_pairs()
            print(f"  - {channel_id}: {preview_pairs(pairs)}")

    rate_channels = [
        channel.id for channel in trace.channels if channel.source == "rate_effect"
    ]
    if rate_channels:
        print("rate-integrated continuous channels:")
        for channel_id in rate_channels:
            pairs = trace.channel(channel_id).as_pairs()
            print(f"  - {channel_id}: {preview_pairs(pairs)}")


def maybe_print_constraint_summary(report: AnalysisRunReport) -> None:
    try:
        summary = report.constraint_summary()
    except KeyError:
        return

    print_header("Constraint / Calculation / Verification Summary")
    print_json_summary(summary)


def maybe_print_activity_summary(report: AnalysisRunReport) -> None:
    try:
        summary = report.activity_summary()
    except KeyError:
        return

    print_header("Activity Execution Summary")
    print(f"status: {summary.get('status', '<unknown>')}")
    print(f"execution state: {summary.get('executionState', '<unknown>')}")
    print(f"binding count: {summary.get('bindingCount', 0)}")

    for binding_index, binding in enumerate(summary.get("bindings", []), start=1):
        if not isinstance(binding, dict):
            continue
        behavior = binding.get("behavior", {})
        subject = binding.get("subject", {})
        behavior_id = behavior.get("elementId", "<behavior>")
        subject_id = subject.get("elementId", "<subject>")
        print(f"binding {binding_index}: {subject_id} -> {behavior_id}")
        for step in binding.get("steps", []):
            if not isinstance(step, dict):
                continue
            nodes = step.get("nodes", [])
            node_ids = [
                node.get("elementId", "<node>")
                for node in nodes
                if isinstance(node, dict)
            ]
            print(f"  step {step.get('index', '?')}: {', '.join(node_ids)}")
        blocked = binding.get("blockedNodes", [])
        if blocked:
            blocked_ids = [
                node.get("elementId", "<node>")
                for node in blocked
                if isinstance(node, dict)
            ]
            print(f"  blocked: {', '.join(blocked_ids)}")


def assert_harness_expectations(
    report: AnalysisRunReport,
    *,
    require_passed: bool,
    require_all_requirements: bool,
) -> None:
    failures: list[str] = []

    if require_passed and report.status != "passed":
        failures.append(f"expected report.status == 'passed', got {report.status!r}")

    if require_all_requirements:
        try:
            summary = report.constraint_summary()
        except KeyError:
            failures.append("expected a constraint_analysis_summary artifact")
        else:
            requirements = (
                summary.get("result", {}).get("requirements", [])
                if isinstance(summary.get("result"), dict)
                else []
            )
            if not requirements:
                failures.append("expected at least one requirement result")
            for requirement in requirements:
                if not isinstance(requirement, dict):
                    continue
                status = requirement.get("status")
                if status not in {"satisfied", "passed"}:
                    requirement_id = requirement.get("id", "<requirement>")
                    failures.append(f"{requirement_id} status is {status!r}")

    if failures:
        print_header("Harness Checks")
        for failure in failures:
            print(f"failed: {failure}")
        raise SystemExit(1)

    if require_passed or require_all_requirements:
        print_header("Harness Checks")
        print("passed")


def trace_channel_source(trace: SimulationTrace, channel_id: str) -> str:
    for channel in trace.channels:
        if channel.id == channel_id or channel.id.endswith(f".{channel_id}"):
            return channel.source
    return "unknown"


def print_refs(label: str, refs: list[Any]) -> None:
    if not refs:
        print(f"{label}: <none>")
        return
    print(f"{label}:")
    for ref in refs:
        print(f"  - {display_ref(ref)}")


def display_ref(ref: Any) -> str:
    label = getattr(ref, "label", None)
    element_id = getattr(ref, "element_id", None)
    kind = getattr(ref, "kind", None)
    rendered = label or element_id or "<unknown>"
    if kind:
        rendered = f"{rendered} [{kind}]"
    if element_id and label and element_id != label:
        rendered = f"{rendered} ({element_id})"
    return rendered


def preview_pairs(pairs: list[tuple[float, Any]], limit: int = 5) -> str:
    if not pairs:
        return "<no samples>"
    head = ", ".join(f"t={t:g}:{value!r}" for t, value in pairs[:limit])
    if len(pairs) > limit:
        head += f", ... t={pairs[-1][0]:g}:{pairs[-1][1]!r}"
    return head


def print_json_summary(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def print_header(title: str) -> None:
    print()
    print(title)
    print("=" * len(title))


if __name__ == "__main__":
    main()
