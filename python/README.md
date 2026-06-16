# Mercurio Python SDK

This package is a typed Python client for Mercurio models.

```python
import mercurio

with mercurio.open("C:/models/demo") as model:
    bed = model.part("bed")
    trace = model.run_analysis("PrintSequence")
    graph = model.raw.graph()
```

## Source-backed Project Sessions

For authoring, small edits, semantic queries, variants, and future simulation
configuration, use a mutable project session and compile immutable semantic
snapshots from it:

```python
import mercurio
from mercurio.authoring import PartUsage

project = mercurio.open_project("C:/models/vehicle/.project.json")

decl = PartUsage("engine").typed("Engine")
project.add(decl)

model = project.compile()
engine = model.resolve(decl)
```

`project` is mutable and source-backed. `model` is an immutable compiled
snapshot with a stable revision hash. `engine` is an immutable semantic ref into
that one snapshot.

Small edits are routed through the project session, even when the target came
from a semantic ref:

```python
project.edit(engine).rename("motor")

model2 = project.compile()
motor = model2.part_usage("motor")
```

The old `engine` ref remains tied to the old model revision. Recompile and
resolve again after edits.

If source changes after a ref was compiled, using that stale ref for another
edit raises `StaleSemanticRefError`. This keeps semantic refs as immutable facts
instead of live mutable handles.

Semantic refs support analysis-style traversal and queries:

```python
vehicle = model.part_def("Vehicle")
subtypes = vehicle.subtypes(transitive=True)
children = list(vehicle.walk())

subtypes = model.query.subtypes("Vehicle")
part_rows = model.to_records(model.query.part_defs())
containment = model.graph("containment")
specialization = model.graph("specialization")
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
from mercurio_capability import CapabilityRequest, CapabilityRunner, Finding, ReasoningReport


@CapabilityRunner.capability(
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
    CapabilityRunner.run(analyze)
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
