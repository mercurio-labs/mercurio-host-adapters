# mercurio-host-adapters — Agent Orientation

Adapter crates for non-core Mercurio integration surfaces. Owns the Python HTTP client, WASM browser bindings, and Rust native bindings.

---

## Contents

| Path | Language | Role |
|------|----------|------|
| `python/` | Python | Thin HTTP client for the local Mercurio backend + capability authoring SDK |
| `crates/mercurio-python/` | Rust | Native Python bindings (PyO3 / maturin) |
| `crates/mercurio-wasm/` | Rust | WebAssembly bindings for browser embedding |

---

## Dependency Direction

```
mercurio-foundation  ←  mercurio-sysml  ←  mercurio-host-adapters
```

This workspace may depend on foundation and sysml crates. It must **not** be depended on by foundation or sysml.

---

## Build

```powershell
# Rust crates
cargo build

# WASM target
cargo build -p mercurio-wasm --target wasm32-unknown-unknown --release
```

---

## Sub-workspace Orientation

See [python/AGENTS.md](python/AGENTS.md) for detailed Python client guidance, capability SDK contract, install/test commands, and the active simulation task spec.

---

## Do Not Touch

- The stdin/stdout ABI of process-backed capabilities — see [python/AGENTS.md](python/AGENTS.md).
- `mercurio-foundation` or `mercurio-sysml` source files from within this workspace.
