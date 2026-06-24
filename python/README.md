# Mercurio Python SDK

This package is a typed Python client for Mercurio models.

For a full API reference, see [`API.md`](API.md).

Most scripts should use the small facade:

- `mercurio.open(path)` for read/query/analysis workflows.
- `mercurio.project(path)` for source-backed authoring and edits.
- `mercurio.create(path=None, package=...)` for new projects, including fully
  in-memory projects when `path` is omitted.
- `from mercurio import model` for declaration factories such as
  `model.part_def(...)`, `model.part(...)`, and `model.attr(...)`.
- `mercurio.capability` for process-provider capability authoring.

```python
import mercurio
from mercurio import model

with mercurio.open("C:/models/demo") as runtime_model:
    rows = runtime_model.query("model.parts().count()")

project = mercurio.create(package="Demo")
project.add(model.part_def("Vehicle").with_part(model.part("engine").typed("Engine")))
```

## Analysis Specs And Simulation

`AnalysisSpec` is the inspectable plan for an analysis case. It lets Python code
check the subject, required techniques, dynamic behavior bindings, expected
artifacts, execution plan, and readiness diagnostics before running anything:

```python
import mercurio

with mercurio.open("C:/models/demo") as model:
    spec = model.analysis_case_spec("PrintSequence")

    assert spec.readiness in {"ready", "partial"}
    assert spec.execution_plan.steps[0].kind == "dynamic_behavior"

    for binding in spec.dynamic_behavior_bindings:
        print(binding.subject.label, binding.kind, binding.behavior.label)

    report = model.run_analysis_report(
        spec.case_ref.element_id,
        run_id="notebook.print-sequence",
    )
    trace = report.simulation_trace()
    summary = report.constraint_summary()  # when the case performs static checks
    activity = report.activity_summary()  # when the case binds activity behavior
```

State-machine bindings are executable by the current simulation path. Activity
bindings are projected in the same `dynamic_behavior_bindings` list and report a
readiness warning until activity execution is implemented.

Calculation, constraint evaluation, and verification analysis cases return the
same `AnalysisRunReport` shape with a `constraint_analysis_summary` artifact.
`constraint_summary()` exposes that payload for notebooks and tests.
Dynamic simulation traces also include supported constraint-derived values as
ordinary trace channels when the model defines simple path-target equality
constraints.
State `do_behavior` can also drive precomputed lookup-table curves; those
values appear in `simulation_trace()` as ordinary channels with source
`lookup_table`.
Activity-bound dynamic behavior cases return an `activity_execution_summary`
artifact as soon as activity behavior is projected. Simple deterministic
action/succession DAGs report completed execution steps; unsupported activity
semantics report partial status with diagnostics.

`run_analysis()` remains available as a convenience when the caller only wants
the simulation trace:

```python
with mercurio.open("C:/models/demo") as model:
    trace = model.run_analysis("PrintSequence")
```

For a fuller end-to-end example, see
[`examples/analysis_execution_showcase.py`](examples/analysis_execution_showcase.py).
It inspects the analysis spec, runs the case, prints simulation channels,
state-machine state timelines, constraint and activity summaries, rate and
lookup-table channels, evidence, diagnostics, and optional harness checks:

```powershell
python examples/analysis_execution_showcase.py C:/models/demo --case PrintSequence --subject bed --require-passed
```

## Semantic Legality

The Python facade exposes the same core semantic legality service used by AI,
REST, UI transports, and CLI probes:

```python
with mercurio.open("C:/models/demo") as model:
    report = model.can_relate("satisfy", "part", "requirement")
    assert report["status"] in {"Allowed", "AllowedWithWarnings"}
```

In Lab notebooks, `mercurio.open()` returns a `LabModel`; its `can_contain`,
`can_specialize`, `can_type_usage`, `can_relate`, and `can_write_attribute`
methods delegate to the workspace model instead of implementing separate
Python-side rules.

Use `semantic_next_actions()` to ask the same core service for allowed,
blocked, and unknown candidate actions for an element kind. Returned actions
include a core-assigned `rank`, with lower ranks preferred:

```python
with mercurio.open("C:/models/demo") as model:
    actions = model.semantic_next_actions(
        "part",
        element="HybridVehicle.vehicle",
        candidate_target_kinds=["requirement", "part"],
        candidate_attributes=["id", "text"],
    )
```

## Source-backed Project Sessions

For authoring, small edits, semantic queries, variants, and future simulation
configuration, use a mutable project session and compile immutable semantic
snapshots from it:

```python
import mercurio
from mercurio import model

project = mercurio.project("C:/models/vehicle/.project.json")

decl = model.part("engine").typed("Engine")
project.add(decl)

snapshot = project.compile()
engine = snapshot.resolve(decl)
```

`project` is mutable and source-backed. `snapshot` is an immutable compiled
snapshot with a stable revision hash. `engine` is an immutable semantic ref into
that one snapshot.

Small edits are routed through the project session, even when the target came
from a semantic ref:

```python
project.edit(engine).rename("motor")

snapshot2 = project.compile()
motor = snapshot2.part_usage("motor")
```

The old `engine` ref remains tied to the old model revision. Recompile and
resolve again after edits.

If source changes after a ref was compiled, using that stale ref for another
edit raises `StaleSemanticRefError`. This keeps semantic refs as immutable facts
instead of live mutable handles.

Semantic refs support analysis-style traversal and queries:

```python
vehicle = snapshot.part_def("Vehicle")
subtypes = vehicle.subtypes(transitive=True)
children = list(vehicle.walk())

subtypes = snapshot.query.subtypes("Vehicle")
part_rows = snapshot.to_records(snapshot.query.part_defs())
containment = snapshot.graph("containment")
specialization = snapshot.graph("specialization")
```

Compiled models also support snapshot comparison:

```python
before = project.compile()
project.edit("VehicleExample.Vehicle.engine").rename("motor")
after = project.compile()

differences = before.diff(after)
```

Trade-study variants are low-cost overlays over rendered project source:

```python
study = project.trade_study("battery-sizing")

small = study.variant("small-pack")
large = study.variant("large-pack")

small.edit("VehicleExample.ElectricCar.batteryCapacity").set_value("50 [kW*h]")
large.edit("VehicleExample.ElectricCar.batteryCapacity").set_value("90 [kW*h]")

small_model = small.compile()
large_model = large.compile()
```

Variants record the base source fingerprint used to create the overlay:

```python
assert large.base_fingerprint == project.source_fingerprint
```

By default, compiling a variant fails if the base project has changed since the
variant was forked. This keeps trade studies revision-pinned:

```python
if large.is_base_stale:
    large_model = large.compile(allow_stale_base=True)  # explicit stale overlay
else:
    large_model = large.compile()
```

Simulation configuration is declarative. Execution is intentionally a future
layer, but configurations can already be bound to a compiled model, project, or
variant and serialized with revision/source provenance:

```python
sim = large_model.simulation("drive-cycle")
sim.for_subject("VehicleExample.ElectricCar").configure(duration=100, step=0.1)

config = sim.to_dict()
```

The compatibility API remains available:

```python
with mercurio.open("C:/models/demo") as model:
    parts = model.parts()
```

## Performance Baselines

Python performance baselines are opt-in so normal unit tests stay stable:

```powershell
$env:MERCURIO_RUN_PERF_BASELINES = "1"
python -m pytest tests/test_performance_baselines.py -q -s
```

The default targets are intentionally aggressive for interactive use:

| Baseline | Target |
|----------|--------|
| small-model authoring | <= 100 ms |
| small-model loading | <= 200 ms |
| small-model editing | <= 100 ms |
| small-model variant clone | <= 100 ms |

Override a target when collecting exploratory numbers:

```powershell
$env:MERCURIO_PERF_AUTHOR_SMALL_MODEL_MS = "250"
$env:MERCURIO_PERF_ITERATIONS = "5"
```

Attach to an already-running backend:

```python
from mercurio.backend import Mercurio

backend = Mercurio.connect("http://127.0.0.1:49152")
project = backend.open_project("C:/models/demo")
```

The first release expects a Mercurio executable installed separately. Discovery order:

1. Explicit `executable=` argument.
2. `MERCURIO_EXE` environment variable.
3. `mercurio` on `PATH`.
4. Future bundled executable in the Python wheel.

## Capability Authoring

The package also includes `mercurio_capability`, a small SDK for authoring
process-provider capabilities. A capability reads one JSON request from stdin
and writes a `ReasoningCapabilityRunResponse` JSON object to stdout.

Minimal capability:

```python
from mercurio.capability import CapabilityRequest, Finding, ReasoningReport, capability, run


@capability(
    id="org.example.hello",
    kind="mercurio.capability.kind/static-analysis",
    name="Hello Capability",
    input_artifact_kinds=["kir"],
    output_artifact_kinds=["reasoning_report"],
)
def analyze(request: CapabilityRequest) -> ReasoningReport:
    return request.report_passed(
        findings=[
            Finding.info(
                "hello.ok",
                "Capability ran",
                f"Request {request.request_id} was handled.",
            )
        ]
    )


if __name__ == "__main__":
    run(analyze)
```

Project plugin manifest excerpt:

```json
{
  "capabilities": [
    {
      "capability": {
        "id": "org.example.hello",
        "kind": "mercurio.capability.kind/static-analysis",
        "name": "Hello Capability",
        "version": "0.1.0",
        "api_version": "0.1",
        "deterministic": true,
        "input_artifact_kinds": ["kir"],
        "output_artifact_kinds": ["reasoning_report"]
      },
      "provider": {
        "kind": "process",
        "command": ["python", "plugins/hello/analyze.py"]
      }
    }
  ]
}
```

`CapabilityRunner` validates the descriptor, request, and emitted report shape
before writing stdout. Capability exceptions are returned as structured transport
errors so the Mercurio host can surface a clear failure.
