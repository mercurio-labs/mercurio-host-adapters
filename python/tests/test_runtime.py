from __future__ import annotations

import unittest

from mercurio.runtime import Model


class FakeSemanticModel:
    def semantic_snapshot_json(self) -> str:
        return '[{"qualified_name": "Demo.Vehicle"}]'


class FakeNativeWorkspace:
    def compile(self) -> FakeSemanticModel:
        return FakeSemanticModel()


class RuntimeModelTests(unittest.TestCase):
    def test_native_model_exposes_semantic_snapshot_json(self) -> None:
        model = Model.from_native(FakeNativeWorkspace())

        self.assertEqual(
            model.semantic_snapshot_json(),
            '[{"qualified_name": "Demo.Vehicle"}]',
        )

    def test_sidecar_model_reports_semantic_snapshot_requirement(self) -> None:
        model = Model.__new__(Model)
        model._workspace = None
        model._project = object()
        model._backend = object()

        with self.assertRaisesRegex(RuntimeError, "native workspace"):
            model.semantic_snapshot_json()


if __name__ == "__main__":
    unittest.main()
