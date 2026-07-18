# Release and installation

## Supported artifact

The beta release is distributed as native stable-ABI wheels. Source
distributions are deferred until the cross-repository Rust dependencies can be
built from their crates.io versions in a clean source archive.

The release matrix currently builds:

- Windows x86-64
- Linux x86-64 and ARM64
- macOS Apple Silicon
- CPython 3.10 through 3.14

## Build locally

Check out `mercurio-host-adapters`, `mercurio-foundation`, and
`mercurio-sysml` as sibling directories, then run from the adapters root:

```console
maturin build --release
```

Install the resulting wheel into a clean virtual environment:

```console
python -m venv .venv
.venv/Scripts/python -m pip install target/wheels/mercurio_sysml-*.whl
```

On Linux or macOS, use `.venv/bin/python` instead.

## Release gates

Every published build must pass all of these gates:

1. Rust adapter tests and the Python source suite.
2. Installation of the built wheel, not an editable source tree.
3. Imports of `mercurio`, `mercurio._core`, `mercurio.capability`, and
   `mercurio_capability`.
4. The Python facade-tour examples against the installed wheel.
5. Python 3.10 through 3.14 stable-ABI import tests.
6. TestPyPI installation before production PyPI approval.
