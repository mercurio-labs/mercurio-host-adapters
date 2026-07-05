# mercurio-wasm

Browser-facing WebAssembly adapter for `mercurio-foundation` and the SysML language services.

The design keeps Rust domain logic in foundation/SysML crates and exposes a compact JSON API at the JS boundary. Browser callers can use one-shot functions for simple workflows or `MercurioSession` to keep compiled sources and derived indexes in memory.

## Build

```powershell
cargo check -p mercurio-wasm --target wasm32-unknown-unknown
wasm-pack build crates/mercurio-wasm --target web
```

## API Shape

Every exported operation returns:

```json
{
  "ok": true,
  "value": {},
  "diagnostics": [],
  "errors": [],
  "metadata": {}
}
```

Main exports:

- `compileSysml(input, options)`
- `compileKerml(input, options)`
- `lint(input, language, options)`
- `formatText(input, language)`
- `renderDiagram(document, request)`
- `renderTable(document, request)`
- `queryRuntime(document, query)`
- `runAssessment(document, spec)`
- `new MercurioSession(options)`

`options.stdlib` may provide a KIR stdlib document. If omitted, the module uses the lightweight SysML stdlib embedded from the sibling `mercurio-sysml` repository.
