# mercurio-host-adapters/python - Agent Orientation

Thin Python HTTP client for a locally running Mercurio backend, plus the
`mercurio_capability` SDK for authoring process-backed capability providers.

---

## Package Layout

```
mercurio/
  __init__.py          - public API surface: mercurio.open(), Model
  runtime.py           - Model context manager wrapping backend + project
  backend.py           - private/advanced Mercurio.launch() / Mercurio.connect()
  project.py           - private/advanced project-scoped HTTP convenience layer
  workspace.py         - compatibility alias for project.py
  client.py            - low-level HTTP GET/POST helpers
  models.py            - implementation dataclasses and typed result objects
  errors.py            - MercurioError hierarchy
mercurio_capability/
  __init__.py          - CapabilityRunner, CapabilityRequest, Finding, ReasoningReport
tests/
  test_client.py       - unit and integration tests
examples/
  basic_workspace.py   - basic public API example
```

---

## Public API Direction

The supported top-level package API is intentionally small:

```python
import mercurio

with mercurio.open(".") as model:
    part = model.part("bed")
    trace = model.run_analysis("PrintSequence")
    graph = model.raw.graph()
```

`mercurio.open(path)` returns `Model`. `model.raw` is the raw KIR/HTTP escape
hatch. Low-level backend, client, project, runtime helper, and DTO classes
remain importable from their implementation modules for tests and advanced
integration, but they are not top-level public API.

`ModelRuntime` remains as `mercurio.runtime.ModelRuntime` only as a compatibility
alias for `Model`.

---

## Backend Discovery

The client finds the Mercurio executable in this order:

1. Explicit `executable=` argument to `mercurio.open()` or `Mercurio.launch()`.
2. `MERCURIO_EXE` environment variable.
3. `mercurio` on `PATH`.
4. Bundled executable shipped with the package.

---

## Capability SDK Contract

A process-backed capability is a standalone executable or Python script using
`CapabilityRunner`:

- Reads a `CapabilityRequest` JSON object from stdin.
- Writes a `ReasoningCapabilityRunResponse` JSON object to stdout.
- All other output goes to stderr and is ignored by the host.

Do not change this stdin/stdout ABI.

---

## Install & Test

```bash
cd mercurio-host-adapters
pip install -e ".[dev]"
pytest
pytest python/tests/test_client.py -v
```

---

## Key Conventions

- `__init__.py` is the public surface. Keep `__all__` limited to `open` and
  `Model`; do not add implementation DTOs, backend/client/project classes, or
  raw helper classes.
- All dataclasses use `frozen=True` except `PartRef`, which uses plain
  `@dataclass` because parent links are set after construction.
- Type alias `JsonObject = dict[str, Any]`; use it for raw JSON dicts.
- Wire format uses `camelCase` field names; Python attributes use `snake_case`.
  When a field may appear in either form, use `.get("snake_field",
  data.get("camelField", default))`.

---

## Further Reading

- [README.md](README.md) - quick-start and usage examples
- [../../../docs/typed-object-model-spec.md](../../../docs/typed-object-model-spec.md) - active typed model API spec
- [../../../docs/codex-python-simulation-api.md](../../../docs/codex-python-simulation-api.md) - older simulation API spec; tasks superseded by the typed object model spec should not be re-expanded into the public top-level API
