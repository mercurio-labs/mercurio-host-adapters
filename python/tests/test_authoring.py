from __future__ import annotations

import importlib
import sys
import types
import unittest


class FakeNativeModelBuilder:
    instances: list["FakeNativeModelBuilder"] = []

    def __init__(self, validate_each_mutation: bool = True) -> None:
        self.validate_each_mutation = validate_each_mutation
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        FakeNativeModelBuilder.instances.append(self)

    def add_package(self, target_file: str, name: str) -> None:
        self.calls.append(("add_package", (target_file, name)))

    def add_import(
        self,
        target_file: str,
        path: str,
        package_name: str | None = None,
    ) -> None:
        self.calls.append(("add_import", (target_file, path, package_name)))

    def remove_import(
        self,
        target_file: str,
        path: str,
        package_name: str | None = None,
    ) -> None:
        self.calls.append(("remove_import", (target_file, path, package_name)))

    def add_definition(
        self,
        container: str,
        keyword: str,
        name: str,
        specializes: list[str] | None = None,
    ) -> None:
        self.calls.append(("add_definition", (container, keyword, name, specializes)))

    def add_usage(
        self,
        container: str,
        keyword: str,
        name: str,
        ty: str | None = None,
        specializes: list[str] | None = None,
    ) -> None:
        self.calls.append(("add_usage", (container, keyword, name, ty, specializes)))

    def set_expression(self, element: str, expression: str | None = None) -> None:
        self.calls.append(("set_expression", (element, expression)))

    def set_usage_type(self, element: str, ty: str | None = None) -> None:
        self.calls.append(("set_usage_type", (element, ty)))

    def set_attribute(self, element: str, attribute: str, value: object) -> None:
        self.calls.append(("set_attribute", (element, attribute, value)))

    def clear_attribute(self, element: str, attribute: str) -> None:
        self.calls.append(("clear_attribute", (element, attribute)))

    def add_attribute_value(self, element: str, attribute: str, value: object) -> None:
        self.calls.append(("add_attribute_value", (element, attribute, value)))

    def remove_attribute_value(self, element: str, attribute: str, value: object) -> None:
        self.calls.append(("remove_attribute_value", (element, attribute, value)))

    def remove_declaration(self, element: str) -> None:
        self.calls.append(("remove_declaration", (element,)))

    def update_specializations(self, element: str, specializes: list[str]) -> None:
        self.calls.append(("update_specializations", (element, specializes)))

    def move_declaration(self, element: str, destination: str) -> None:
        self.calls.append(("move_declaration", (element, destination)))

    def add_relationship(
        self,
        container: str,
        kind: str,
        source: str,
        target: str,
    ) -> None:
        self.calls.append(("add_relationship", (container, kind, source, target)))

    def add_metadata_annotation(
        self,
        element: str,
        metadata_type: str,
        properties: dict[str, str] | None = None,
    ) -> None:
        self.calls.append(("add_metadata_annotation", (element, metadata_type, properties)))

    def rendered_files(self) -> dict[str, str]:
        return {"model.sysml": ""}


class AuthoringCreateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        core = types.ModuleType("mercurio._core")
        core.ModelBuilder = FakeNativeModelBuilder
        core.WriteBackResult = object
        sys.modules["mercurio._core"] = core
        sys.modules.pop("mercurio.builder", None)
        sys.modules.pop("mercurio.authoring", None)
        cls.authoring = importlib.import_module("mercurio.authoring")

    def setUp(self) -> None:
        FakeNativeModelBuilder.instances.clear()

    def test_create_definition_delegates_to_native_builder(self) -> None:
        builder = self.authoring.ModelBuilder()

        qname = builder.create(
            "PartDefinition",
            "Vehicle",
            container="Demo",
            specializes=["BaseVehicle"],
            abstract=True,
        )

        self.assertEqual(qname, "Demo.Vehicle")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "part", "Vehicle", ["BaseVehicle"])),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle", "isAbstract", True)),
            native.calls,
        )

    def test_model_builder_forwards_validation_mode(self) -> None:
        self.authoring.ModelBuilder(validate_each_mutation=False)

        native = FakeNativeModelBuilder.instances[-1]
        self.assertFalse(native.validate_each_mutation)

    def test_in_package_can_skip_stdlib_imports(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("PilotSample", stdlib_imports=False)

        native = FakeNativeModelBuilder.instances[-1]
        self.assertEqual(native.calls, [("add_package", ("model.sysml", "PilotSample"))])

    def test_create_usage_applies_type_expression_and_attributes(self) -> None:
        builder = self.authoring.ModelBuilder()

        qname = builder.create(
            "AttributeUsage",
            "mass",
            container="Demo.Vehicle",
            type="ISQ::MassValue",
            additional_types=["BaseMassFeature"],
            subsets=["baseMass"],
            redefines=["oldMass"],
            reference_target="vehicle.mass",
            doc="Mass of the vehicle",
            body="first start;",
            expression="42 [kg]",
            multiplicity="1",
            direction="in",
            short_name="m",
            end=True,
            attributes={"unit": "kg"},
        )

        self.assertEqual(qname, "Demo.Vehicle.mass")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertEqual(
            native.calls[0],
            (
                "add_usage",
                ("Demo.Vehicle", "attribute", "mass", "ISQ::MassValue", None),
            ),
        )
        self.assertIn(
            ("set_expression", ("Demo.Vehicle.mass", "42 [kg]")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "additional_types", ["BaseMassFeature"])),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "subsets", ["baseMass"])),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "redefines", ["oldMass"])),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "reference_target", "vehicle.mass")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "doc", "Mass of the vehicle")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "rawBody", "first start;")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "multiplicity", "1")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "direction", "in")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "declaredShortName", "m")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "isEnd", True)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.mass", "unit", "kg")),
            native.calls,
        )

    def test_create_uses_default_package_when_available(self) -> None:
        builder = self.authoring.ModelBuilder()
        builder.in_package("Demo")

        qname = builder.create("ItemDefinition", "Signal")

        self.assertEqual(qname, "Demo.Signal")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "item", "Signal", None)),
            native.calls,
        )

    def test_create_perform_action_usage_uses_perform_keyword(self) -> None:
        builder = self.authoring.ModelBuilder()

        qname = builder.create("PerformActionUsage", "providePower", container="Demo")

        self.assertEqual(qname, "Demo.providePower")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo", "perform", "providePower", None, None)),
            native.calls,
        )

    def test_create_metadata_usage_uses_metadata_keyword_and_about_target(self) -> None:
        builder = self.authoring.ModelBuilder()

        qname = builder.create(
            "MetadataUsage",
            "vehicleSafety",
            container="Demo",
            type="Safety",
            reference_target="Vehicle",
        )

        self.assertEqual(qname, "Demo.vehicleSafety")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo", "metadata", "vehicleSafety", "Safety", None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.vehicleSafety", "reference_target", "Vehicle")),
            native.calls,
        )

    def test_create_metadata_definition_accepts_annotated_elements(self) -> None:
        builder = self.authoring.ModelBuilder()

        qname = builder.create(
            "MetadataDefinition",
            "SecurityFeature",
            container="Demo",
            annotated_elements=["SysML::PartDefinition", "SysML::PartUsage"],
        )

        self.assertEqual(qname, "Demo.SecurityFeature")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "metadata", "SecurityFeature", None)),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                (
                    "Demo.SecurityFeature",
                    "annotatedElements",
                    ["SysML::PartDefinition", "SysML::PartUsage"],
                ),
            ),
            native.calls,
        )

    def test_create_accepts_language_extension_keyword_arguments(self) -> None:
        builder = self.authoring.ModelBuilder()

        scenario = builder.create(
            "ScenarioDefinition",
            "DeviceFailure",
            container="Demo",
            language_extension_keyword=True,
        )
        port = builder.create(
            "PortDefinition",
            "ServiceDiscovery",
            container="Demo",
            language_extensions=["service"],
        )

        self.assertEqual(scenario, "Demo.DeviceFailure")
        self.assertEqual(port, "Demo.ServiceDiscovery")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "scenario", "DeviceFailure", None)),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                ("Demo.DeviceFailure", "isLanguageExtensionKeyword", True),
            ),
            native.calls,
        )
        self.assertIn(
            ("add_definition", ("Demo", "port", "ServiceDiscovery", None)),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                ("Demo.ServiceDiscovery", "languageExtensions", ["service"]),
            ),
            native.calls,
        )

    def test_create_maps_use_case_metaclasses_to_sysml_keyword(self) -> None:
        builder = self.authoring.ModelBuilder()

        definition = builder.create("UseCaseDefinition", "TransportPassenger", container="Demo")
        usage = builder.create(
            "UseCaseUsage",
            "transportPassenger",
            container="Demo",
            type="TransportPassenger",
        )

        self.assertEqual(definition, "Demo.TransportPassenger")
        self.assertEqual(usage, "Demo.transportPassenger")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "use-case", "TransportPassenger", None)),
            native.calls,
        )
        self.assertIn(
            (
                "add_usage",
                ("Demo", "use-case", "transportPassenger", "TransportPassenger", None),
            ),
            native.calls,
        )

    def test_create_transition_usage_accepts_state_shorthand_fields(self) -> None:
        builder = self.authoring.ModelBuilder()

        qname = builder.create(
            "TransitionUsage",
            "off_to_starting",
            container="Demo.VehicleStates",
            transition_source="off",
            trigger="VehicleStartSignal",
            transition_target="starting",
        )

        self.assertEqual(qname, "Demo.VehicleStates.off_to_starting")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo.VehicleStates", "transition", "off_to_starting", None, None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.VehicleStates.off_to_starting", "transitionSource", "off")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.VehicleStates.off_to_starting", "trigger", "VehicleStartSignal")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.VehicleStates.off_to_starting", "transitionTarget", "starting")),
            native.calls,
        )

    def test_create_constraint_usage_accepts_raw_body(self) -> None:
        builder = self.authoring.ModelBuilder()

        qname = builder.create(
            "ConstraintUsage",
            "massConstraint",
            container="Demo",
            type="MassConstraint",
            body="in totalMass = mass;",
        )

        self.assertEqual(qname, "Demo.massConstraint")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo", "constraint", "massConstraint", "MassConstraint", None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.massConstraint", "rawBody", "in totalMass = mass;")),
            native.calls,
        )

    def test_create_occurrence_and_individual_usage(self) -> None:
        builder = self.authoring.ModelBuilder()

        occurrence_qname = builder.create("OccurrenceUsage", "event1", container="Demo")
        individual_qname = builder.create(
            "PartUsage",
            "vehicle1",
            container="Demo",
            type="Vehicle",
            individual=True,
        )

        self.assertEqual(occurrence_qname, "Demo.event1")
        self.assertEqual(individual_qname, "Demo.vehicle1")
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo", "occurrence", "event1", None, None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo", "part", "vehicle1", "Vehicle", None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.vehicle1", "isIndividual", True)),
            native.calls,
        )

    def test_create_rejects_unsupported_metaclass(self) -> None:
        builder = self.authoring.ModelBuilder()

        with self.assertRaisesRegex(ValueError, "unsupported authoring metaclass"):
            builder.create("Comment", "note", container="Demo")

    def test_facade_exposes_native_mutation_helpers(self) -> None:
        builder = self.authoring.ModelBuilder()

        result = (
            builder.in_package("Demo")
            .add_import("Domain::*")
            .remove_import("Domain::*")
            .update_specializations("Demo.Vehicle", ["BaseVehicle"])
            .add_specialization("Demo.Vehicle", "ExtraVehicle")
            .remove_specialization("Demo.Vehicle", "ExtraVehicle")
            .set_type("Demo.Vehicle.engine", "Engine")
            .set_doc("Demo.Vehicle", "Vehicle documentation")
            .clear_doc("Demo.Vehicle")
            .set_attribute("Demo.Vehicle", "isAbstract", True)
            .clear_attribute("Demo.Vehicle", "isAbstract")
            .add_attribute_value("Demo.Vehicle", "specializes", "BaseVehicle")
            .remove_attribute_value("Demo.Vehicle", "specializes", "BaseVehicle")
            .move("Demo.Vehicle.engine", "Demo.Other")
            .add_relationship(
                "satisfy",
                "Demo.Vehicle",
                "Demo.Requirement",
                container="Demo.Vehicle",
            )
            .add_metadata("Demo.Vehicle", "Doc", {"text": "Vehicle"})
            .set_additional_types("Demo.Vehicle.engine", ["PoweredFeature"])
            .add_additional_type("Demo.Vehicle.engine", "AuxFeature")
            .remove_additional_type("Demo.Vehicle.engine", "AuxFeature")
            .set_subsets("Demo.Vehicle.engine", ["baseEngine"])
            .add_subset("Demo.Vehicle.engine", "backupEngine")
            .remove_subset("Demo.Vehicle.engine", "backupEngine")
            .set_redefines("Demo.Vehicle.engine", ["oldEngine"])
            .add_redefine("Demo.Vehicle.engine", "legacyEngine")
            .remove_redefine("Demo.Vehicle.engine", "legacyEngine")
            .set_reference_target("Demo.Vehicle.engine", "vehicle.engine")
            .clear_reference_target("Demo.Vehicle.engine")
            .remove("Demo.Vehicle.obsolete")
        )

        self.assertIs(result, builder)
        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(("add_import", ("model.sysml", "Domain::*", "Demo")), native.calls)
        self.assertIn(("remove_import", ("model.sysml", "Domain::*", "Demo")), native.calls)
        self.assertIn(
            ("update_specializations", ("Demo.Vehicle", ["BaseVehicle"])),
            native.calls,
        )
        self.assertIn(
            ("add_attribute_value", ("Demo.Vehicle", "specializes", "ExtraVehicle")),
            native.calls,
        )
        self.assertIn(
            ("remove_attribute_value", ("Demo.Vehicle", "specializes", "ExtraVehicle")),
            native.calls,
        )
        self.assertIn(("set_usage_type", ("Demo.Vehicle.engine", "Engine")), native.calls)
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle", "doc", "Vehicle documentation")),
            native.calls,
        )
        self.assertIn(("clear_attribute", ("Demo.Vehicle", "doc")), native.calls)
        self.assertIn(
            ("add_relationship", ("Demo.Vehicle", "satisfy", "Demo.Vehicle", "Demo.Requirement")),
            native.calls,
        )
        self.assertIn(
            ("add_metadata_annotation", ("Demo.Vehicle", "Doc", {"text": "Vehicle"})),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.engine", "additional_types", ["PoweredFeature"])),
            native.calls,
        )
        self.assertIn(
            ("add_attribute_value", ("Demo.Vehicle.engine", "additional_types", "AuxFeature")),
            native.calls,
        )
        self.assertIn(
            ("remove_attribute_value", ("Demo.Vehicle.engine", "additional_types", "AuxFeature")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.engine", "subsets", ["baseEngine"])),
            native.calls,
        )
        self.assertIn(
            ("add_attribute_value", ("Demo.Vehicle.engine", "subsets", "backupEngine")),
            native.calls,
        )
        self.assertIn(
            ("remove_attribute_value", ("Demo.Vehicle.engine", "subsets", "backupEngine")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.engine", "redefines", ["oldEngine"])),
            native.calls,
        )
        self.assertIn(
            ("add_attribute_value", ("Demo.Vehicle.engine", "redefines", "legacyEngine")),
            native.calls,
        )
        self.assertIn(
            ("remove_attribute_value", ("Demo.Vehicle.engine", "redefines", "legacyEngine")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.engine", "reference_target", "vehicle.engine")),
            native.calls,
        )
        self.assertIn(
            ("clear_attribute", ("Demo.Vehicle.engine", "reference_target")),
            native.calls,
        )
        self.assertIn(("remove_declaration", ("Demo.Vehicle.obsolete",)), native.calls)

    def test_relationship_requires_container_without_default_package(self) -> None:
        builder = self.authoring.ModelBuilder()

        with self.assertRaisesRegex(ValueError, "add_relationship"):
            builder.add_relationship("satisfy", "Demo.Vehicle", "Demo.Requirement")

    def test_typed_declarations_emit_doc_end_and_reference_target(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.PartDefinition("Vehicle")
            .doc("Vehicle documentation")
            .with_end(
                self.authoring.PartUsage("front")
                .typed("Wheel")
                .reference_target("vehicle.front")
                .doc("Front wheel")
            )
            .with_part(
                self.authoring.PartUsage("rear")
                .typed("Wheel")
                .reference_target("vehicle.rear")
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle", "doc", "Vehicle documentation")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.front", "doc", "Front wheel")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.front", "isEnd", True)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.front", "reference_target", "vehicle.front")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.rear", "reference_target", "vehicle.rear")),
            native.calls,
        )

    def test_usage_declarations_can_contain_nested_part_usages(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo", stdlib_imports=False).add(
            self.authoring.PartUsage("vehicle").with_part(
                self.authoring.PartUsage("interior").with_part(
                    self.authoring.PartUsage("seatBelt").multiplicity("2")
                )
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(("add_usage", ("Demo", "part", "vehicle", None, None)), native.calls)
        self.assertIn(
            ("add_usage", ("Demo.vehicle", "part", "interior", None, None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo.vehicle.interior", "part", "seatBelt", None, None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.vehicle.interior.seatBelt", "multiplicity", "2")),
            native.calls,
        )

    def test_typed_perform_action_usage_emits_perform_keyword(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.ActionDefinition("ProvidePower").with_action(
                self.authoring.PerformActionUsage("providePower")
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo.ProvidePower", "perform", "providePower", None, None)),
            native.calls,
        )

    def test_typed_occurrence_usage_emits_occurrence_keyword(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.OccurrenceDefinition("Sequence").with_action(
                self.authoring.OccurrenceUsage("publish")
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "occurrence", "Sequence", None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo.Sequence", "occurrence", "publish", None, None)),
            native.calls,
        )

    def test_typed_metadata_declarations_emit_metadata_keyword(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.MetadataDefinition("Safety")
            .annotates("SysML::PartDefinition")
            .annotates("SysML::PartUsage")
            .with_part(
                self.authoring.MetadataUsage("vehicleSafety")
                .typed("Safety")
                .reference_target("Vehicle")
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "metadata", "Safety", None)),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                (
                    "Demo.Safety",
                    "annotatedElements",
                    ["SysML::PartDefinition", "SysML::PartUsage"],
                ),
            ),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo.Safety", "metadata", "vehicleSafety", "Safety", None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Safety.vehicleSafety", "reference_target", "Vehicle")),
            native.calls,
        )

    def test_metadata_usage_about_accepts_multiple_targets(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.MetadataUsage("Safety").about(
                ["vehicle.seatBelt", "vehicle.airBag", "vehicle.bumper"]
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo", "metadata", "Safety", None, None)),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                (
                    "Demo.Safety",
                    "reference_target",
                    ["vehicle.seatBelt", "vehicle.airBag", "vehicle.bumper"],
                ),
            ),
            native.calls,
        )

    def test_typed_declarations_emit_language_extension_attributes(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.PortDefinition("ServiceDiscovery").language_extension("service")
        )
        builder.add(self.authoring.ActionDefinition("DeviceFailure").extension_keyword())

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("set_attribute", ("Demo.ServiceDiscovery", "languageExtensions", ["service"])),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.DeviceFailure", "isLanguageExtensionKeyword", True)),
            native.calls,
        )

    def test_typed_analysis_verification_use_case_and_view_wrappers(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(self.authoring.AnalysisDefinition("FuelEconomyAnalysis"))
        builder.add(self.authoring.AnalysisUsage("cityAnalysis").typed("FuelEconomyAnalysis"))
        builder.add(self.authoring.VerificationDefinition("MassTest"))
        builder.add(self.authoring.VerificationUsage("massTests").typed("MassTest"))
        builder.add(self.authoring.UseCaseDefinition("TransportPassenger"))
        builder.add(self.authoring.UseCaseUsage("transportPassenger").typed("TransportPassenger"))
        builder.add(self.authoring.ConcernDefinition("VehicleSafety"))
        builder.add(self.authoring.ViewDefinition("PartsTreeView"))
        builder.add(self.authoring.ViewUsage("vehiclePartsTree").typed("PartsTreeView"))
        builder.add(self.authoring.ViewpointDefinition("SystemViewpoint"))
        builder.add(self.authoring.StakeholderUsage("se").typed("SafetyEngineer"))

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_definition", ("Demo", "analysis", "FuelEconomyAnalysis", None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo", "analysis", "cityAnalysis", "FuelEconomyAnalysis", None)),
            native.calls,
        )
        self.assertIn(
            ("add_definition", ("Demo", "verification", "MassTest", None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo", "verification", "massTests", "MassTest", None)),
            native.calls,
        )
        self.assertIn(
            ("add_definition", ("Demo", "use-case", "TransportPassenger", None)),
            native.calls,
        )
        self.assertIn(
            (
                "add_usage",
                ("Demo", "use-case", "transportPassenger", "TransportPassenger", None),
            ),
            native.calls,
        )
        self.assertIn(
            ("add_definition", ("Demo", "concern", "VehicleSafety", None)),
            native.calls,
        )
        self.assertIn(
            ("add_definition", ("Demo", "view", "PartsTreeView", None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo", "view", "vehiclePartsTree", "PartsTreeView", None)),
            native.calls,
        )
        self.assertIn(
            ("add_definition", ("Demo", "viewpoint", "SystemViewpoint", None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo", "stakeholder", "se", "SafetyEngineer", None)),
            native.calls,
        )

    def test_typed_transition_usage_emits_state_shorthand_attributes(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.StateDefinition("VehicleStates").with_state(
                self.authoring.TransitionUsage("off_to_starting")
                .first("off")
                .accept("VehicleStartSignal")
                .then("starting")
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            (
                "add_usage",
                ("Demo.VehicleStates", "transition", "off_to_starting", None, None),
            ),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                ("Demo.VehicleStates.off_to_starting", "transitionSource", "off"),
            ),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                ("Demo.VehicleStates.off_to_starting", "trigger", "VehicleStartSignal"),
            ),
            native.calls,
        )
        self.assertIn(
            (
                "set_attribute",
                ("Demo.VehicleStates.off_to_starting", "transitionTarget", "starting"),
            ),
            native.calls,
        )

    def test_typed_transition_usage_emits_initial_state_marker(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.StateDefinition("VehicleStates").with_state(
                self.authoring.TransitionUsage("start").initial().then("off")
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo.VehicleStates", "transition", "start", None, None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.VehicleStates.start", "transitionSource", "start")),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.VehicleStates.start", "sourceIsInitial", True)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.VehicleStates.start", "transitionTarget", "off")),
            native.calls,
        )

    def test_connection_usage_connects_adds_endpoint_members(self) -> None:
        builder = self.authoring.ModelBuilder()

        builder.in_package("Demo").add(
            self.authoring.PartDefinition("Vehicle").with_part(
                self.authoring.ConnectionUsage("axle")
                .typed("AxleConnection")
                .connects(
                    "vehicle.leftWheel",
                    "vehicle.rightWheel",
                    source_name="left",
                    target_name="right",
                    source_type="Wheel",
                    target_type="Wheel",
                )
            )
        )

        native = FakeNativeModelBuilder.instances[-1]
        self.assertIn(
            ("add_usage", ("Demo.Vehicle", "connection", "axle", "AxleConnection", None)),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo.Vehicle.axle", "part", "left", "Wheel", None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.axle.left", "isEnd", True)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.axle.left", "reference_target", "vehicle.leftWheel")),
            native.calls,
        )
        self.assertIn(
            ("add_usage", ("Demo.Vehicle.axle", "part", "right", "Wheel", None)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.axle.right", "isEnd", True)),
            native.calls,
        )
        self.assertIn(
            ("set_attribute", ("Demo.Vehicle.axle.right", "reference_target", "vehicle.rightWheel")),
            native.calls,
        )


if __name__ == "__main__":
    unittest.main()
