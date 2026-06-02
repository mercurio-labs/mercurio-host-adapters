# Mercurio Adapter

Adapter crates for non-core Mercurio integration surfaces.

- `mercurio-python` exposes Python/native bindings.
- `mercurio-wasm` exposes browser/WebAssembly bindings.
- `mercurio-views` contains UI-oriented view DTOs and rendering helpers.

The foundation repo owns KIR, contracts, and semantic core behavior. This repo
owns adapter layers that depend on those APIs.
