# mercurio-host-adapters/python — Agent Orientation

Thin Python HTTP client for a locally running Mercurio backend, plus the `mercurio_capability` SDK for authoring process-backed capability providers.

---

## Package Layout

```
mercurio/
  __init__.py          — public API surface, mercurio.open() entry point, __all__
  backend.py           — Mercurio.launch() / Mercurio.connect(), process lifecycle
  workspace.py         — MercurioWorkspace: compile_project, model, graph, element, parts, simulation methods
  models.py            — dataclasses: AnalysisCaseInfo, SimulationTrace, TraceChannel, ChannelData, StateData, PartRef, …
  client.py            — low-level HTTP GET/POST helpers
  errors.py            — MercurioError hierarchy
  runtime.py           — ModelRuntime: context manager wrapping backend + workspace (may not exist yet — see task spec)
mercurio_capability/
  __init__.py          — CapabilityRunner, CapabilityRequest, Finding, ReasoningReport
tests/
  test_client.py       — unit and integration tests
examples/
  view.py              — reference usage script
```

---

## Backend Discovery

The client finds the Mercurio executable in this order:
1. Explicit `executable=` argument to `Mercurio.launch()`
2. `MERCURIO_EXE` environment variable
3. `mercurio` on `PATH`
4. Bundled executable shipped with the package

---

## Capability SDK Contract

A process-backed capability is a standalone executable (or Python script using `CapabilityRunner`):
- Reads a `CapabilityRequest` JSON object from **stdin**
- Writes a `ReasoningCapabilityRunResponse` JSON object to **stdout**
- All other output goes to **stderr** (ignored by the host)

**Do not change this stdin/stdout ABI.**

---

## Install & Test

```bash
pip install -e ".[dev]"
pytest
pytest tests/test_client.py -v
```

---

## Active Task — Simulation API (see `docs/codex-python-simulation-api.md`)

The task spec at [`../../../docs/codex-python-simulation-api.md`](../../../docs/codex-python-simulation-api.md) describes Tasks 2, 3, and 4 for this workspace:

**Files to create or extend:**

| File | What to add |
|------|-------------|
| `mercurio/models.py` | `AnalysisCaseInfo`, `SimulationTrace`, `TraceChannel`, `ChannelData`, `StateData`, `PartRef` |
| `mercurio/workspace.py` | `list_analysis_cases()`, `run_analysis()`, `parts()` |
| `mercurio/__init__.py` | Exports for all new types + `open()` function; update `__all__` |
| `mercurio/runtime.py` | New file: `ModelRuntime` class |
| `tests/test_client.py` | Unit tests for new types and methods |

**Do NOT touch:**
- `backend.py`, `client.py`, `errors.py`, `process.py`
- `mercurio_capability/` internals
- Any Rust code

---

## Key Conventions

- All dataclasses use `frozen=True` (immutable) except `PartRef`, which uses plain `@dataclass` because parent links are set after construction (use `object.__setattr__` if needed).
- Type alias `JsonObject = dict[str, Any]` — use it for raw JSON dicts.
- Wire format uses `camelCase` field names; Python attributes use `snake_case`. When a field may appear in either form, use `.get("snake_field", data.get("camelField", default))`.
- `__init__.py` is the only public surface — all new types must appear in `__all__`.

---

## Further Reading

- [README.md](README.md) — quick-start and usage examples
- [../../../docs/codex-python-simulation-api.md](../../../docs/codex-python-simulation-api.md) — full task spec with target code and test cases
