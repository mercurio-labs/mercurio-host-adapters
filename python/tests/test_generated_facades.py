import json

from mercurio._generated import ElementFacade, ElementView
from mercurio._generated import facades, metamodel
from mercurio.session import CompiledModel


class _NativeModel:
    def semantic_snapshot_json(self) -> str:
        return json.dumps(
            [
                {
                    "id": "Demo.Vehicle",
                    "qualified_name": "Demo.Vehicle",
                    "kind": "PartDefinition",
                    "declared_name": "Vehicle",
                    "is_abstract": True,
                }
            ]
        )


def test_generated_facade_wraps_existing_semantic_refs() -> None:
    model = CompiledModel(_NativeModel())
    ref = model.resolve("Demo.Vehicle")

    wrapped = ref.facade()

    assert isinstance(wrapped, facades.PartDefinition)
    assert isinstance(wrapped, ElementFacade)
    assert wrapped.raw is ref
    assert wrapped.declared_name == "Vehicle"
    assert wrapped.is_abstract is True
    assert model.facade(ref).raw is ref
    all_facades = model.facades()
    assert len(all_facades) == 1
    assert isinstance(all_facades[0], facades.PartDefinition)
    assert all_facades[0].raw is ref


def test_legacy_generated_facade_names_remain_aliases() -> None:
    assert ElementView is ElementFacade
    assert metamodel.PartDefinition is facades.PartDefinition
    assert facades.wrap is not None
    assert facades.wrap(CompiledModel(_NativeModel()).resolve("Demo.Vehicle")).kind == "PartDefinition"