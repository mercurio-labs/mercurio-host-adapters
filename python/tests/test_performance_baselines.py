from __future__ import annotations

import os
import statistics
import time
import unittest


SMALL_MODEL_SOURCE = """package VehicleExample {
  part def Vehicle {
    part engine : Engine;
  }

  part def Engine;
}
"""


def _enabled() -> bool:
    return os.environ.get("MERCURIO_RUN_PERF_BASELINES") == "1"


def _threshold(name: str, default_ms: float) -> float:
    value = os.environ.get(f"MERCURIO_PERF_{name.upper()}_MS")
    return default_ms if value is None else float(value)


def _iterations() -> int:
    return max(1, int(os.environ.get("MERCURIO_PERF_ITERATIONS", "3")))


def _measure_ms(fn, *, iterations: int) -> float:
    samples: list[float] = []
    fn()
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


class PythonPerformanceBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not _enabled():
            raise unittest.SkipTest(
                "set MERCURIO_RUN_PERF_BASELINES=1 to run Python performance baselines"
            )
        try:
            from mercurio.authoring import ModelBuilder, PartDefinition, PartUsage
            from mercurio.session import ProjectSession
        except ImportError as exc:
            raise unittest.SkipTest(f"native Python authoring API is unavailable: {exc}") from exc
        cls.ModelBuilder = ModelBuilder
        cls.PartDefinition = PartDefinition
        cls.PartUsage = PartUsage
        cls.ProjectSession = ProjectSession

    def test_python_api_performance_baselines(self) -> None:
        iterations = _iterations()
        baselines = {
            "author_small_model": (
                _threshold("author_small_model", 100.0),
                self._author_small_model,
            ),
            "load_small_model": (
                _threshold("load_small_model", 200.0),
                self._load_small_model,
            ),
            "edit_small_model": (
                _threshold("edit_small_model", 100.0),
                self._edit_small_model,
            ),
            "clone_small_model": (
                _threshold("clone_small_model", 100.0),
                self._clone_small_model,
            ),
        }

        results = {
            name: _measure_ms(fn, iterations=iterations)
            for name, (_target, fn) in baselines.items()
        }

        print("\nMercurio Python performance baselines")
        for name, elapsed_ms in results.items():
            target_ms = baselines[name][0]
            print(f"  {name}: {elapsed_ms:.1f} ms target <= {target_ms:.1f} ms")

        failures = [
            f"{name}: {elapsed_ms:.1f} ms > {baselines[name][0]:.1f} ms"
            for name, elapsed_ms in results.items()
            if elapsed_ms > baselines[name][0]
        ]
        if failures:
            self.fail("Python performance baseline failures:\n" + "\n".join(failures))

    def _author_small_model(self) -> None:
        builder = (
            self.ModelBuilder(validate_each_mutation=False)
            .in_package("VehicleExample", stdlib_imports=False)
            .add(self.PartDefinition("Engine"))
            .add(
                self.PartDefinition("Vehicle").with_part(
                    self.PartUsage("engine").typed("Engine")
                )
            )
        )
        builder.to_sysml()

    def _load_small_model(self) -> None:
        self.ProjectSession.from_files(
            {"model.sysml": SMALL_MODEL_SOURCE},
            validate=False,
        )

    def _edit_small_model(self) -> None:
        project = self.ProjectSession.from_files(
            {"model.sysml": SMALL_MODEL_SOURCE},
            validate=False,
        )
        project.edit("VehicleExample.Vehicle.engine").rename("motor")

    def _clone_small_model(self) -> None:
        project = self.ProjectSession.from_files(
            {"model.sysml": SMALL_MODEL_SOURCE},
            validate=False,
        )
        project.trade_study("baseline").variant("clone")
