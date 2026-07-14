# Mercurio Adapter

Adapter crates for non-core Mercurio integration surfaces.

- `mercurio-python` exposes Python/native bindings.
- `mercurio-wasm` exposes browser/WebAssembly bindings.
- `mercurio-views` contains UI-oriented view DTOs and rendering helpers.

The foundation repo owns KIR, contracts, and semantic core behavior. This repo
owns adapter layers that depend on those APIs.

## Python SDK

The Python distribution is named `mercurio-sysml` and installs the `mercurio`
and `mercurio_capability` import packages:

```powershell
pip install mercurio-sysml
```

Build or install it from this repository root so maturin can use the canonical
`pyproject.toml`:

```powershell
maturin build --release
pip install -e ".[dev]"
```
