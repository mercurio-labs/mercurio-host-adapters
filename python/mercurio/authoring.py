from __future__ import annotations

from pathlib import Path
from typing import Any

from .builder import ModelBuilder as _NativeModelBuilder
from .stdlib import StdlibRef


_AUTHORABLE_DEFINITION_SUFFIX = "Definition"
_AUTHORABLE_USAGE_SUFFIX = "Usage"


def _keyword_from_metaclass(metaclass: str, suffix: str) -> str:
    keyword = {
        "PerformActionUsage": "perform",
        "UseCaseDefinition": "use-case",
        "UseCaseUsage": "use-case",
        "TransitionUsage": "transition",
    }.get(metaclass)
    if keyword is not None:
        return keyword
    stem = metaclass.removesuffix(suffix)
    if not stem:
        raise ValueError(f"unsupported authoring metaclass: {metaclass!r}")
    return stem[:1].lower() + stem[1:]


def _qnames(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (str, StdlibRef)) or hasattr(value, "qualified_name"):
        return [_ref(value)]
    return [_ref(item) for item in value]


def _ref_or_refs(value: Any) -> str | list[str]:
    values = _qnames(value)
    if values is None:
        raise ValueError("reference value must not be None")
    return values[0] if len(values) == 1 else values


def _ref(value: Any) -> str:
    if isinstance(value, StdlibRef):
        return value.qualified_name
    qualified_name = getattr(value, "qualified_name", None)
    if isinstance(qualified_name, str):
        return qualified_name
    return str(value)


class ModelBuilder:
    def __init__(self) -> None:
        self._inner = _NativeModelBuilder()
        self._default_package: str | None = None
        self._default_file = "model.sysml"
        self._project_root: Path | None = None

    @classmethod
    def for_metamodel(cls, _id: str) -> "ModelBuilder":
        return cls()

    @classmethod
    def from_project(
        cls,
        path: str | Path,
        *,
        validate: bool = True,
    ) -> "ModelBuilder":
        """Load a descriptor-aware project into an editable builder.

        *path* may be a project directory, a ``.project.json`` descriptor, or a
        single ``.sysml`` file. When a project descriptor is present, its source
        roots and entrypoints select the loaded source files.
        """
        project_path = Path(path)
        obj = cls.__new__(cls)
        obj._inner = _NativeModelBuilder.from_project(str(project_path), validate)
        obj._default_package = None
        files = obj._inner.files()
        obj._default_file = files[0] if files else "model.sysml"
        if project_path.name == ".project.json":
            obj._project_root = project_path.parent
        elif project_path.is_dir():
            obj._project_root = project_path
        else:
            obj._project_root = project_path.parent
        return obj

    @classmethod
    def from_files(
        cls,
        files: dict[str, str],
        *,
        validate: bool = True,
    ) -> "ModelBuilder":
        """Load an existing set of SysML source files into an editable builder.

        *files* is a mapping of relative file paths to source text, e.g.::

            {"model/spacecraft.sysml": open("model/spacecraft.sysml").read()}

        The builder is seeded with the parsed content; subsequent calls to
        ``add()``, ``rename()``, etc. mutate it in-place.  Call ``save()``
        or ``to_sysml()`` to get the updated source.
        """
        obj = cls.__new__(cls)
        obj._inner = _NativeModelBuilder.from_sysml_files(files, validate)
        obj._default_package = None
        obj._default_file = next(iter(files)) if files else "model.sysml"
        obj._project_root = None
        return obj

    def in_package(self, name: str, *, stdlib_imports: bool = True) -> "ModelBuilder":
        self._inner.add_package(self._default_file, name)
        self._default_package = name
        if stdlib_imports:
            # bring standard library namespaces into scope inside the package
            for ns in (
                "ISQBase", "ISQSpaceTime", "ISQMechanics",
                "ISQThermodynamics", "ISQElectromagnetism",
                "SI", "ScalarValues",
            ):
                self._inner.add_import(self._default_file, f"{ns}::*", name)
        return self

    def add(self, element: "_Declaration") -> "ModelBuilder":
        if self._default_package is None:
            raise ValueError("call in_package() before add()")
        element._emit(self._inner, self._default_package)
        return self

    def rename(self, qualified_name: str, new_name: str) -> "ModelBuilder":
        """Rename any declared element by its qualified name."""
        self._inner.rename(qualified_name, new_name)
        return self

    def remove(self, qualified_name: str) -> "ModelBuilder":
        """Remove a declared element by its qualified name."""
        self._inner.remove_declaration(qualified_name)
        return self

    def add_import(
        self,
        path: Any,
        *,
        package: str | None = None,
        target_file: str | None = None,
    ) -> "ModelBuilder":
        """Add an import to a package or top-level source file."""
        self._inner.add_import(
            target_file or self._default_file,
            _ref(path),
            package or self._default_package,
        )
        return self

    def remove_import(
        self,
        path: Any,
        *,
        package: str | None = None,
        target_file: str | None = None,
    ) -> "ModelBuilder":
        """Remove an import from a package or top-level source file."""
        self._inner.remove_import(
            target_file or self._default_file,
            _ref(path),
            package or self._default_package,
        )
        return self

    def update_specializations(
        self,
        qualified_name: str,
        specializes: Any,
    ) -> "ModelBuilder":
        """Replace the specialization list for a declaration."""
        self._inner.update_specializations(qualified_name, _qnames(specializes) or [])
        return self

    def add_specialization(
        self,
        qualified_name: str,
        target: Any,
    ) -> "ModelBuilder":
        """Add one specialization target to a declaration."""
        self._inner.add_attribute_value(qualified_name, "specializes", _ref(target))
        return self

    def remove_specialization(
        self,
        qualified_name: str,
        target: Any,
    ) -> "ModelBuilder":
        """Remove one specialization target from a declaration."""
        self._inner.remove_attribute_value(qualified_name, "specializes", _ref(target))
        return self

    def set_type(self, qualified_name: str, target: Any | None) -> "ModelBuilder":
        """Set or clear the type of a usage."""
        self._inner.set_usage_type(
            qualified_name,
            None if target is None else _ref(target),
        )
        return self

    def set_expression(
        self, qualified_name: str, expression: str | None
    ) -> "ModelBuilder":
        """Set or clear the value expression on a usage."""
        self._inner.set_expression(qualified_name, expression)
        return self

    def set_doc(self, qualified_name: str, text: str) -> "ModelBuilder":
        """Set documentation text on a package or declaration."""
        self._inner.set_attribute(qualified_name, "doc", text)
        return self

    def clear_doc(self, qualified_name: str) -> "ModelBuilder":
        """Clear documentation text on a package or declaration."""
        self._inner.clear_attribute(qualified_name, "doc")
        return self

    def set_attribute(
        self,
        qualified_name: str,
        attribute: str,
        value: Any,
    ) -> "ModelBuilder":
        """Set a semantic attribute using the native authoring engine."""
        self._inner.set_attribute(qualified_name, attribute, value)
        return self

    def clear_attribute(
        self,
        qualified_name: str,
        attribute: str,
    ) -> "ModelBuilder":
        """Clear a semantic attribute using the native authoring engine."""
        self._inner.clear_attribute(qualified_name, attribute)
        return self

    def add_attribute_value(
        self,
        qualified_name: str,
        attribute: str,
        value: Any,
    ) -> "ModelBuilder":
        """Append a value to a list-valued semantic attribute."""
        self._inner.add_attribute_value(qualified_name, attribute, value)
        return self

    def remove_attribute_value(
        self,
        qualified_name: str,
        attribute: str,
        value: Any,
    ) -> "ModelBuilder":
        """Remove a value from a list-valued semantic attribute."""
        self._inner.remove_attribute_value(qualified_name, attribute, value)
        return self

    def move(self, qualified_name: str, destination: str) -> "ModelBuilder":
        """Move a declaration into another package or declaration container."""
        self._inner.move_declaration(qualified_name, destination)
        return self

    def add_relationship(
        self,
        kind: str,
        source: Any,
        target: Any,
        *,
        container: str | None = None,
    ) -> "ModelBuilder":
        """Add a relationship usage in a container."""
        target_container = container or self._default_package
        if target_container is None:
            raise ValueError("add_relationship() requires container= or a prior in_package() call")
        self._inner.add_relationship(
            target_container,
            kind,
            _ref(source),
            _ref(target),
        )
        return self

    def add_metadata(
        self,
        qualified_name: str,
        metadata_type: str,
        properties: dict[str, str] | None = None,
    ) -> "ModelBuilder":
        """Attach a metadata annotation to an element."""
        self._inner.add_metadata_annotation(
            qualified_name,
            metadata_type,
            properties,
        )
        return self

    def add_to(
        self, container: str, element: "_Declaration"
    ) -> "ModelBuilder":
        """Add an element into an existing container by qualified name.

        Use this (instead of ``add()``) when editing a model loaded with
        ``from_files()``, where the package is already defined.
        """
        element._emit(self._inner, container)
        return self

    def create(
        self,
        metaclass: str,
        name: str,
        *,
        container: str | None = None,
        type: Any = None,
        ty: Any = None,
        specializes: Any = None,
        additional_types: Any = None,
        subsets: Any = None,
        redefines: Any = None,
        reference_target: Any = None,
        transition_source: Any = None,
        transition_target: Any = None,
        trigger: str | None = None,
        doc: str | None = None,
        body: str | None = None,
        expression: str | None = None,
        multiplicity: str | None = None,
        direction: str | None = None,
        short_name: str | None = None,
        annotated_elements: Any = None,
        language_extensions: Any = None,
        language_extension_keyword: bool | None = None,
        abstract: bool | None = None,
        end: bool | None = None,
        individual: bool | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """Create an authorable SysML/KerML declaration by metaclass name.

        This is the generic escape hatch for metaclasses that do not yet have a
        typed convenience wrapper. It delegates to the native PyO3 builder.
        """
        target_container = container or self._default_package
        if target_container is None:
            raise ValueError("create() requires container= or a prior in_package() call")

        qname = f"{target_container}.{name}"
        if metaclass.endswith(_AUTHORABLE_DEFINITION_SUFFIX):
            keyword = _keyword_from_metaclass(metaclass, _AUTHORABLE_DEFINITION_SUFFIX)
            self._inner.add_definition(
                target_container,
                keyword,
                name,
                _qnames(specializes),
            )
        elif metaclass.endswith(_AUTHORABLE_USAGE_SUFFIX):
            keyword = _keyword_from_metaclass(metaclass, _AUTHORABLE_USAGE_SUFFIX)
            usage_type = type if type is not None else ty
            self._inner.add_usage(
                target_container,
                keyword,
                name,
                None if usage_type is None else _ref(usage_type),
                _qnames(specializes),
            )
        else:
            raise ValueError(
                f"unsupported authoring metaclass: {metaclass!r}; expected a *Definition or *Usage metaclass"
            )

        if expression is not None:
            self._inner.set_expression(qname, expression)
        if additional_types is not None:
            self._inner.set_attribute(qname, "additional_types", _qnames(additional_types) or [])
        if subsets is not None:
            self._inner.set_attribute(qname, "subsets", _qnames(subsets) or [])
        if redefines is not None:
            self._inner.set_attribute(qname, "redefines", _qnames(redefines) or [])
        if reference_target is not None:
            self._inner.set_attribute(qname, "reference_target", _ref_or_refs(reference_target))
        if transition_source is not None:
            self._inner.set_attribute(qname, "transitionSource", _ref(transition_source))
        if transition_target is not None:
            self._inner.set_attribute(qname, "transitionTarget", _ref(transition_target))
        if trigger is not None:
            self._inner.set_attribute(qname, "trigger", trigger)
        if doc is not None:
            self._inner.set_attribute(qname, "doc", doc)
        if body is not None:
            self._inner.set_attribute(qname, "rawBody", body)
        if multiplicity is not None:
            self._inner.set_attribute(qname, "multiplicity", multiplicity)
        if direction is not None:
            self._inner.set_attribute(qname, "direction", direction)
        if short_name is not None:
            self._inner.set_attribute(qname, "declaredShortName", short_name)
        if annotated_elements is not None:
            self._inner.set_attribute(
                qname,
                "annotatedElements",
                _qnames(annotated_elements) or [],
            )
        if language_extensions is not None:
            self._inner.set_attribute(
                qname,
                "languageExtensions",
                _qnames(language_extensions) or [],
            )
        if language_extension_keyword is not None:
            self._inner.set_attribute(
                qname,
                "isLanguageExtensionKeyword",
                language_extension_keyword,
            )
        if abstract is not None:
            self._inner.set_attribute(qname, "isAbstract", abstract)
        if end is not None:
            self._inner.set_attribute(qname, "isEnd", end)
        if individual is not None:
            self._inner.set_attribute(qname, "isIndividual", individual)
        for key, value in (attributes or {}).items():
            self._inner.set_attribute(qname, key, value)
        return qname

    def set_additional_types(self, qualified_name: str, values: Any) -> "ModelBuilder":
        """Replace the additional type list for a usage."""
        self._inner.set_attribute(qualified_name, "additional_types", _qnames(values) or [])
        return self

    def add_additional_type(self, qualified_name: str, value: Any) -> "ModelBuilder":
        """Add one additional type to a usage."""
        self._inner.add_attribute_value(qualified_name, "additional_types", _ref(value))
        return self

    def remove_additional_type(self, qualified_name: str, value: Any) -> "ModelBuilder":
        """Remove one additional type from a usage."""
        self._inner.remove_attribute_value(qualified_name, "additional_types", _ref(value))
        return self

    def set_subsets(self, qualified_name: str, values: Any) -> "ModelBuilder":
        """Replace the subsetted feature list for a usage."""
        self._inner.set_attribute(qualified_name, "subsets", _qnames(values) or [])
        return self

    def add_subset(self, qualified_name: str, value: Any) -> "ModelBuilder":
        """Add one subsetted feature to a usage."""
        self._inner.add_attribute_value(qualified_name, "subsets", _ref(value))
        return self

    def remove_subset(self, qualified_name: str, value: Any) -> "ModelBuilder":
        """Remove one subsetted feature from a usage."""
        self._inner.remove_attribute_value(qualified_name, "subsets", _ref(value))
        return self

    def set_redefines(self, qualified_name: str, values: Any) -> "ModelBuilder":
        """Replace the redefined feature list for a usage."""
        self._inner.set_attribute(qualified_name, "redefines", _qnames(values) or [])
        return self

    def add_redefine(self, qualified_name: str, value: Any) -> "ModelBuilder":
        """Add one redefined feature to a usage."""
        self._inner.add_attribute_value(qualified_name, "redefines", _ref(value))
        return self

    def remove_redefine(self, qualified_name: str, value: Any) -> "ModelBuilder":
        """Remove one redefined feature from a usage."""
        self._inner.remove_attribute_value(qualified_name, "redefines", _ref(value))
        return self

    def set_reference_target(self, qualified_name: str, target: Any) -> "ModelBuilder":
        """Set the explicit reference target for a usage."""
        self._inner.set_attribute(qualified_name, "reference_target", _ref(target))
        return self

    def clear_reference_target(self, qualified_name: str) -> "ModelBuilder":
        """Clear the explicit reference target for a usage."""
        self._inner.clear_attribute(qualified_name, "reference_target")
        return self

    def to_sysml(self) -> dict[str, str]:
        return self._inner.rendered_files()

    def compile(self):
        return self._inner.compile_model()

    def save(self, path: str | Path | None = None) -> None:
        if path is None:
            if self._project_root is None:
                raise ValueError("save() requires a path unless the builder was loaded from a project")
            root = self._project_root
        else:
            root = Path(path)
        for rel, source in self.to_sysml().items():
            output = root / rel
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(source, encoding="utf-8")


class _Declaration:
    _kind = "definition"
    _keyword = ""

    def __init__(self, name: str) -> None:
        self.name = name
        self._type: str | None = None
        self._specializes: list[str] = []
        self._members: list[_Declaration] = []
        self._expression: str | None = None
        self._multiplicity: str | None = None
        self._direction: str | None = None
        self._doc: str | None = None
        self._is_end = False
        self._reference_target: str | list[str] | None = None
        self._abstract = False
        self._annotated_elements: list[str] = []
        self._language_extensions: list[str] = []
        self._language_extension_keyword = False
        self._transition_source: str | None = None
        self._transition_target: str | None = None
        self._source_is_initial = False
        self._trigger: str | None = None

    @property
    def qualified_name(self) -> str:
        """Allow _ref() to resolve a definition or usage by its declared name."""
        return self.name

    def specializes(self, target: Any):
        self._specializes.append(_ref(target))
        return self

    def typed(self, target: Any):
        self._type = _ref(target)
        return self

    def expression(self, text: str):
        self._expression = text
        return self

    def multiplicity(self, text: str):
        self._multiplicity = text
        return self

    def direction(self, text: str):
        self._direction = text
        return self

    def doc(self, text: str):
        self._doc = text
        return self

    def abstract_(self):
        self._abstract = True
        return self

    def reference_target(self, target: Any):
        self._reference_target = _ref_or_refs(target)
        return self

    def language_extension(self, keyword: str):
        self._language_extensions.append(keyword)
        return self

    def extension_keyword(self):
        self._language_extension_keyword = True
        return self

    def first(self, source: Any):
        self._transition_source = _ref(source)
        return self

    def initial(self, source: Any = "start"):
        self._transition_source = _ref(source)
        self._source_is_initial = True
        return self

    def then(self, target: Any):
        self._transition_target = _ref(target)
        return self

    def accept(self, trigger: str):
        self._trigger = trigger
        return self

    def _as_end(self, target: Any | None = None):
        self._is_end = True
        if target is not None:
            self._reference_target = _ref_or_refs(target)
        return self

    def _emit(self, builder: _NativeModelBuilder, container: str) -> str:
        if self._kind == "definition":
            builder.add_definition(container, self._keyword, self.name, self._specializes or None)
        else:
            builder.add_usage(
                container,
                self._keyword,
                self.name,
                self._type,
                self._specializes or None,
            )
        qname = f"{container}.{self.name}"
        if self._expression is not None:
            builder.set_expression(qname, self._expression)
        if self._direction is not None:
            builder.set_attribute(qname, "direction", self._direction)
        if self._multiplicity is not None:
            builder.set_attribute(qname, "multiplicity", self._multiplicity)
        if self._doc is not None:
            builder.set_attribute(qname, "doc", self._doc)
        if self._abstract:
            builder.set_attribute(qname, "isAbstract", True)
        if self._is_end:
            builder.set_attribute(qname, "isEnd", True)
        if self._reference_target is not None:
            builder.set_attribute(qname, "reference_target", self._reference_target)
        if self._annotated_elements:
            builder.set_attribute(qname, "annotatedElements", self._annotated_elements)
        if self._language_extensions:
            builder.set_attribute(qname, "languageExtensions", self._language_extensions)
        if self._language_extension_keyword:
            builder.set_attribute(qname, "isLanguageExtensionKeyword", True)
        if self._transition_source is not None:
            builder.set_attribute(qname, "transitionSource", self._transition_source)
        if self._source_is_initial:
            builder.set_attribute(qname, "sourceIsInitial", True)
        if self._transition_target is not None:
            builder.set_attribute(qname, "transitionTarget", self._transition_target)
        if self._trigger is not None:
            builder.set_attribute(qname, "trigger", self._trigger)
        for member in self._members:
            member._emit(builder, qname)
        return qname


class _Definition(_Declaration):
    _kind = "definition"

    def _with(self, member: _Declaration):
        self._members.append(member)
        return self

    def with_part(self, member): return self._with(member)
    def with_item(self, member): return self._with(member)
    def with_attr(self, member): return self._with(member)
    def with_port(self, member): return self._with(member)
    def with_end(self, member): return self._with(member._as_end())
    def with_action(self, member): return self._with(member)
    def with_state(self, member): return self._with(member)


class _Usage(_Declaration):
    _kind = "usage"

    def _with(self, member: _Declaration):
        self._members.append(member)
        return self

    def with_part(self, member): return self._with(member)
    def with_item(self, member): return self._with(member)
    def with_attr(self, member): return self._with(member)
    def with_port(self, member): return self._with(member)
    def with_action(self, member): return self._with(member)
    def with_state(self, member): return self._with(member)

    def with_end(self, member):
        return self._with(member._as_end())

    def end(self, target: Any | None = None):
        return self._as_end(target)

    def connects(
        self,
        source: Any,
        target: Any,
        *,
        source_name: str = "source",
        target_name: str = "target",
        source_type: Any | None = None,
        target_type: Any | None = None,
    ):
        source_end = PartUsage(source_name).end(source)
        if source_type is not None:
            source_end.typed(source_type)
        target_end = PartUsage(target_name).end(target)
        if target_type is not None:
            target_end.typed(target_type)
        self.with_end(source_end)
        self.with_end(target_end)
        return self


class PartDefinition(_Definition): _keyword = "part"
class ItemDefinition(_Definition): _keyword = "item"
class AttributeDefinition(_Definition): _keyword = "attribute"
class PortDefinition(_Definition): _keyword = "port"
class ConnectionDefinition(_Definition): _keyword = "connection"
class ActionDefinition(_Definition): _keyword = "action"
class ActionUsage(_Usage): _keyword = "action"
class PerformActionUsage(_Usage): _keyword = "perform"
class ConstraintDefinition(_Definition): _keyword = "constraint"
class ConstraintUsage(_Usage): _keyword = "constraint"
class AnalysisDefinition(_Definition): _keyword = "analysis"
class AnalysisUsage(_Usage): _keyword = "analysis"
class VerificationDefinition(_Definition): _keyword = "verification"
class VerificationUsage(_Usage): _keyword = "verification"
class UseCaseDefinition(_Definition): _keyword = "use-case"
class UseCaseUsage(_Usage): _keyword = "use-case"
class ViewDefinition(_Definition): _keyword = "view"
class ViewUsage(_Usage): _keyword = "view"
class ViewpointDefinition(_Definition): _keyword = "viewpoint"
class ViewpointUsage(_Usage): _keyword = "viewpoint"
class ConcernDefinition(_Definition): _keyword = "concern"
class ConcernUsage(_Usage): _keyword = "concern"
class StakeholderUsage(_Usage): _keyword = "stakeholder"
class MetadataDefinition(_Definition):
    _keyword = "metadata"

    def annotates(self, target: Any):
        self._annotated_elements.append(_ref(target))
        return self

class MetadataUsage(_Usage):
    _keyword = "metadata"

    def about(self, targets: Any):
        return self.reference_target(targets)
class OccurrenceDefinition(_Definition): _keyword = "occurrence"
class OccurrenceUsage(_Usage): _keyword = "occurrence"
class IndividualDefinition(_Definition): _keyword = "individual"
class IndividualUsage(_Usage): _keyword = "individual"
class StateDefinition(_Definition): _keyword = "state"
class StateUsage(_Usage): _keyword = "state"
class TransitionUsage(_Usage): _keyword = "transition"
class RequirementDefinition(_Definition): _keyword = "requirement"
class InterfaceDefinition(_Definition): _keyword = "interface"


class PartUsage(_Usage): _keyword = "part"
class ItemUsage(_Usage): _keyword = "item"
class AttributeUsage(_Usage): _keyword = "attribute"
class PortUsage(_Usage): _keyword = "port"
class ConnectionUsage(_Usage): _keyword = "connection"


__all__ = [
    "ModelBuilder",
    "PartDefinition",
    "PartUsage",
    "ItemDefinition",
    "ItemUsage",
    "AttributeDefinition",
    "AttributeUsage",
    "PortDefinition",
    "PortUsage",
    "ConnectionDefinition",
    "ConnectionUsage",
    "ActionDefinition",
    "ActionUsage",
    "PerformActionUsage",
    "ConstraintDefinition",
    "ConstraintUsage",
    "AnalysisDefinition",
    "AnalysisUsage",
    "VerificationDefinition",
    "VerificationUsage",
    "UseCaseDefinition",
    "UseCaseUsage",
    "ViewDefinition",
    "ViewUsage",
    "ViewpointDefinition",
    "ViewpointUsage",
    "ConcernDefinition",
    "ConcernUsage",
    "StakeholderUsage",
    "MetadataDefinition",
    "MetadataUsage",
    "OccurrenceDefinition",
    "OccurrenceUsage",
    "IndividualDefinition",
    "IndividualUsage",
    "StateDefinition",
    "StateUsage",
    "TransitionUsage",
    "RequirementDefinition",
    "InterfaceDefinition",
]
