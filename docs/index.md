# Mercurio Python SDK

Mercurio provides native Python authoring, query, analysis, and capability
APIs for SysML v2 and KerML semantic models.

The distribution name and import package intentionally differ:

```console
pip install mercurio-sysml
```

```python
import mercurio
from mercurio import model

project = mercurio.create(package="Demo")
project.add(model.part_def("Vehicle"))
compiled = project.compile()
```

The wheel contains the native `mercurio._core` extension, the typed Python
facade, and the `mercurio_capability` process-provider SDK. Python 3.10 and
newer CPython releases use the same stable-ABI wheel for each platform.

```{toctree}
:maxdepth: 2
:caption: Documentation

api
release
```

## Project links

- [Source repository](https://github.com/mercurio-labs/mercurio-host-adapters)
- [Issue tracker](https://github.com/mercurio-labs/mercurio-host-adapters/issues)
- [Python examples](https://github.com/mercurio-labs/mercurio-examples/tree/main/python)
- [Rust crates](https://github.com/mercurio-labs/mercurio-foundation)
