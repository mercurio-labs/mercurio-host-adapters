from __future__ import annotations

from typing import Any

from .base import ElementFacade, ElementView


class Element(ElementFacade):
    concept = None
    metatype_id = "KerML::Root::Element"
    metatype_ids = ("KerML::Root::Element",)
    kind_name = "Element"
    kind_names = ("Element",)

    @property
    def alias_ids(self) -> str | None:
        return self.effective_str("alias_ids")

    @property
    def declared_name(self) -> str | None:
        return self.effective_str("declared_name")

    @property
    def declared_short_name(self) -> str | None:
        return self.effective_str("declared_short_name")

    @property
    def doc(self) -> str | None:
        return self.effective_str("doc")

    @property
    def element_id(self) -> str | None:
        return self.effective_str("element_id")

    @property
    def is_implied_included(self) -> bool | None:
        return self.effective_bool("is_implied_included")

    @property
    def is_library_element(self) -> bool | None:
        return self.effective_bool("is_library_element")

    @property
    def name(self) -> str | None:
        return self.effective_str("name")

    @property
    def owned_annotation(self) -> str | None:
        return self.effective_str("owned_annotation")

    @property
    def owned_element(self) -> str | None:
        return self.effective_str("owned_element")

    @property
    def owned_relationship(self) -> str | None:
        return self.effective_str("owned_relationship")

    @property
    def owning_membership(self) -> str | None:
        return self.effective_str("owning_membership")

    @property
    def owning_namespace(self) -> str | None:
        return self.effective_str("owning_namespace")

    @property
    def owning_relationship(self) -> str | None:
        return self.effective_str("owning_relationship")

    @property
    def qualified_name(self) -> str | None:
        return self.effective_str("qualified_name")

    @property
    def short_name(self) -> str | None:
        return self.effective_str("short_name")

    @property
    def textual_representation(self) -> str | None:
        return self.effective_str("textual_representation")

class Namespace(Element):
    concept = None
    metatype_id = "KerML::Root::Namespace"
    metatype_ids = ("KerML::Root::Namespace",)
    kind_name = "Namespace"
    kind_names = ("Namespace",)

    @property
    def imported_membership(self) -> str | None:
        return self.effective_str("imported_membership")

    @property
    def member(self) -> str | None:
        return self.effective_str("member")

    @property
    def membership(self) -> str | None:
        return self.effective_str("membership")

    @property
    def owned_import(self) -> str | None:
        return self.effective_str("owned_import")

    @property
    def owned_membership(self) -> str | None:
        return self.effective_str("owned_membership")

class Type(Namespace):
    concept = None
    metatype_id = "KerML::Core::Type"
    metatype_ids = ("KerML::Core::Type",)
    kind_name = "Type"
    kind_names = ("Type",)

    @property
    def differencing_type(self) -> str | None:
        return self.effective_str("differencing_type")

    @property
    def directed_feature(self) -> str | None:
        return self.effective_str("directed_feature")

    @property
    def end_feature(self) -> str | None:
        return self.effective_str("end_feature")

    @property
    def feature(self) -> str | None:
        return self.effective_str("feature")

    @property
    def feature_membership(self) -> str | None:
        return self.effective_str("feature_membership")

    @property
    def inherited_feature(self) -> str | None:
        return self.effective_str("inherited_feature")

    @property
    def inherited_membership(self) -> str | None:
        return self.effective_str("inherited_membership")

    @property
    def input(self) -> str | None:
        return self.effective_str("input")

    @property
    def intersecting_type(self) -> str | None:
        return self.effective_str("intersecting_type")

    @property
    def is_abstract(self) -> bool | None:
        return self.effective_bool("is_abstract")

    @property
    def is_conjugated(self) -> bool | None:
        return self.effective_bool("is_conjugated")

    @property
    def is_sufficient(self) -> bool | None:
        return self.effective_bool("is_sufficient")

    @property
    def multiplicity(self) -> str | None:
        return self.effective_str("multiplicity")

    @property
    def output(self) -> str | None:
        return self.effective_str("output")

    @property
    def owned_conjugator(self) -> str | None:
        return self.effective_str("owned_conjugator")

    @property
    def owned_differencing(self) -> str | None:
        return self.effective_str("owned_differencing")

    @property
    def owned_disjoining(self) -> str | None:
        return self.effective_str("owned_disjoining")

    @property
    def owned_end_feature(self) -> str | None:
        return self.effective_str("owned_end_feature")

    @property
    def owned_feature_membership(self) -> str | None:
        return self.effective_str("owned_feature_membership")

    @property
    def owned_intersecting(self) -> str | None:
        return self.effective_str("owned_intersecting")

    @property
    def owned_unioning(self) -> str | None:
        return self.effective_str("owned_unioning")

    @property
    def unioning_type(self) -> str | None:
        return self.effective_str("unioning_type")

class Feature(Type):
    concept = None
    metatype_id = "KerML::Core::Feature"
    metatype_ids = ("KerML::Core::Feature",)
    kind_name = "Feature"
    kind_names = ("Feature",)

    @property
    def chaining_feature(self) -> str | None:
        return self.effective_str("chaining_feature")

    @property
    def cross_feature(self) -> str | None:
        return self.effective_str("cross_feature")

    @property
    def direction(self) -> str | None:
        return self.effective_str("direction")

    @property
    def end_owning_type(self) -> str | None:
        return self.effective_str("end_owning_type")

    @property
    def feature_target(self) -> str | None:
        return self.effective_str("feature_target")

    @property
    def featuring_type(self) -> str | None:
        return self.effective_str("featuring_type")

    @property
    def is_composite(self) -> bool | None:
        return self.effective_bool("is_composite")

    @property
    def is_constant(self) -> bool | None:
        return self.effective_bool("is_constant")

    @property
    def is_derived(self) -> bool | None:
        return self.effective_bool("is_derived")

    @property
    def is_end(self) -> bool | None:
        return self.effective_bool("is_end")

    @property
    def is_ordered(self) -> bool | None:
        return self.effective_bool("is_ordered")

    @property
    def is_portion(self) -> bool | None:
        return self.effective_bool("is_portion")

    @property
    def is_unique(self) -> bool | None:
        return self.effective_bool("is_unique")

    @property
    def is_variable(self) -> bool | None:
        return self.effective_bool("is_variable")

    @property
    def owned_cross_subsetting(self) -> str | None:
        return self.effective_str("owned_cross_subsetting")

    @property
    def owned_feature_chaining(self) -> str | None:
        return self.effective_str("owned_feature_chaining")

    @property
    def owned_feature_inverting(self) -> str | None:
        return self.effective_str("owned_feature_inverting")

    @property
    def owned_redefinition(self) -> str | None:
        return self.effective_str("owned_redefinition")

    @property
    def owned_reference_subsetting(self) -> str | None:
        return self.effective_str("owned_reference_subsetting")

    @property
    def owned_subsetting(self) -> str | None:
        return self.effective_str("owned_subsetting")

    @property
    def owned_type_featuring(self) -> str | None:
        return self.effective_str("owned_type_featuring")

    @property
    def owned_typing(self) -> str | None:
        return self.effective_str("owned_typing")

    @property
    def owning_feature_membership(self) -> str | None:
        return self.effective_str("owning_feature_membership")

    @property
    def owning_type(self) -> str | None:
        return self.effective_str("owning_type")

    @property
    def type(self) -> str | None:
        return self.effective_str("type")

class Usage(Feature):
    concept = None
    metatype_id = "SysML::Systems::Usage"
    metatype_ids = ("SysML::Systems::Usage",)
    kind_name = "Usage"
    kind_names = ("Usage",)

    @property
    def definition(self) -> str | None:
        return self.effective_str("definition")

    @property
    def directed_usage(self) -> str | None:
        return self.effective_str("directed_usage")

    @property
    def is_reference(self) -> bool | None:
        return self.effective_bool("is_reference")

    @property
    def is_variation(self) -> bool | None:
        return self.effective_bool("is_variation")

    @property
    def may_time_vary(self) -> bool | None:
        return self.effective_bool("may_time_vary")

    @property
    def nested_action(self) -> str | None:
        return self.effective_str("nested_action")

    @property
    def nested_allocation(self) -> str | None:
        return self.effective_str("nested_allocation")

    @property
    def nested_analysis_case(self) -> str | None:
        return self.effective_str("nested_analysis_case")

    @property
    def nested_attribute(self) -> str | None:
        return self.effective_str("nested_attribute")

    @property
    def nested_calculation(self) -> str | None:
        return self.effective_str("nested_calculation")

    @property
    def nested_case(self) -> str | None:
        return self.effective_str("nested_case")

    @property
    def nested_concern(self) -> str | None:
        return self.effective_str("nested_concern")

    @property
    def nested_connection(self) -> str | None:
        return self.effective_str("nested_connection")

    @property
    def nested_constraint(self) -> str | None:
        return self.effective_str("nested_constraint")

    @property
    def nested_enumeration(self) -> str | None:
        return self.effective_str("nested_enumeration")

    @property
    def nested_flow(self) -> str | None:
        return self.effective_str("nested_flow")

    @property
    def nested_interface(self) -> str | None:
        return self.effective_str("nested_interface")

    @property
    def nested_item(self) -> str | None:
        return self.effective_str("nested_item")

    @property
    def nested_metadata(self) -> str | None:
        return self.effective_str("nested_metadata")

    @property
    def nested_occurrence(self) -> str | None:
        return self.effective_str("nested_occurrence")

    @property
    def nested_part(self) -> str | None:
        return self.effective_str("nested_part")

    @property
    def nested_port(self) -> str | None:
        return self.effective_str("nested_port")

    @property
    def nested_reference(self) -> str | None:
        return self.effective_str("nested_reference")

    @property
    def nested_rendering(self) -> str | None:
        return self.effective_str("nested_rendering")

    @property
    def nested_requirement(self) -> str | None:
        return self.effective_str("nested_requirement")

    @property
    def nested_state(self) -> str | None:
        return self.effective_str("nested_state")

    @property
    def nested_transition(self) -> str | None:
        return self.effective_str("nested_transition")

    @property
    def nested_usage(self) -> str | None:
        return self.effective_str("nested_usage")

    @property
    def nested_use_case(self) -> str | None:
        return self.effective_str("nested_use_case")

    @property
    def nested_verification_case(self) -> str | None:
        return self.effective_str("nested_verification_case")

    @property
    def nested_view(self) -> str | None:
        return self.effective_str("nested_view")

    @property
    def nested_viewpoint(self) -> str | None:
        return self.effective_str("nested_viewpoint")

    @property
    def owning_definition(self) -> str | None:
        return self.effective_str("owning_definition")

    @property
    def owning_usage(self) -> str | None:
        return self.effective_str("owning_usage")

    @property
    def usage(self) -> str | None:
        return self.effective_str("usage")

    @property
    def variant(self) -> str | None:
        return self.effective_str("variant")

    @property
    def variant_membership(self) -> str | None:
        return self.effective_str("variant_membership")

class OccurrenceUsage(Usage):
    concept = None
    metatype_id = "SysML::Systems::OccurrenceUsage"
    metatype_ids = ("SysML::Systems::OccurrenceUsage",)
    kind_name = "OccurrenceUsage"
    kind_names = ("OccurrenceUsage",)

    @property
    def individual_definition(self) -> str | None:
        return self.effective_str("individual_definition")

    @property
    def is_individual(self) -> bool | None:
        return self.effective_bool("is_individual")

    @property
    def occurrence_definition(self) -> str | None:
        return self.effective_str("occurrence_definition")

    @property
    def portion_kind(self) -> str | None:
        return self.effective_str("portion_kind")

class Step(Feature):
    concept = None
    metatype_id = "KerML::Kernel::Step"
    metatype_ids = ("KerML::Kernel::Step",)
    kind_name = "Step"
    kind_names = ("Step",)

    @property
    def behavior(self) -> str | None:
        return self.effective_str("behavior")

    @property
    def parameter(self) -> str | None:
        return self.effective_str("parameter")

class ActionUsage(OccurrenceUsage, Step):
    concept = None
    metatype_id = "SysML::Systems::ActionUsage"
    metatype_ids = ("SysML::Systems::ActionUsage",)
    kind_name = "ActionUsage"
    kind_names = ("ActionUsage",)

    @property
    def action_definition(self) -> str | None:
        return self.effective_str("action_definition")

class AcceptActionUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::AcceptActionUsage"
    metatype_ids = ("SysML::Systems::AcceptActionUsage",)
    kind_name = "AcceptActionUsage"
    kind_names = ("AcceptActionUsage",)

    @property
    def payload_argument(self) -> str | None:
        return self.effective_str("payload_argument")

    @property
    def payload_parameter(self) -> str | None:
        return self.effective_str("payload_parameter")

    @property
    def receiver_argument(self) -> str | None:
        return self.effective_str("receiver_argument")

class Classifier(Type):
    concept = None
    metatype_id = "KerML::Core::Classifier"
    metatype_ids = ("KerML::Core::Classifier",)
    kind_name = "Classifier"
    kind_names = ("Classifier",)

    @property
    def owned_subclassification(self) -> str | None:
        return self.effective_str("owned_subclassification")

class Class(Classifier):
    concept = None
    metatype_id = "KerML::Kernel::Class"
    metatype_ids = ("KerML::Kernel::Class",)
    kind_name = "Class"
    kind_names = ("Class",)

class Behavior(Class):
    concept = None
    metatype_id = "KerML::Kernel::Behavior"
    metatype_ids = ("KerML::Kernel::Behavior",)
    kind_name = "Behavior"
    kind_names = ("Behavior",)

    @property
    def parameter(self) -> str | None:
        return self.effective_str("parameter")

    @property
    def step(self) -> str | None:
        return self.effective_str("step")

class Definition(Classifier):
    concept = None
    metatype_id = "SysML::Systems::Definition"
    metatype_ids = ("SysML::Systems::Definition",)
    kind_name = "Definition"
    kind_names = ("Definition",)

    @property
    def directed_usage(self) -> str | None:
        return self.effective_str("directed_usage")

    @property
    def is_variation(self) -> bool | None:
        return self.effective_bool("is_variation")

    @property
    def owned_action(self) -> str | None:
        return self.effective_str("owned_action")

    @property
    def owned_allocation(self) -> str | None:
        return self.effective_str("owned_allocation")

    @property
    def owned_analysis_case(self) -> str | None:
        return self.effective_str("owned_analysis_case")

    @property
    def owned_attribute(self) -> str | None:
        return self.effective_str("owned_attribute")

    @property
    def owned_calculation(self) -> str | None:
        return self.effective_str("owned_calculation")

    @property
    def owned_case(self) -> str | None:
        return self.effective_str("owned_case")

    @property
    def owned_concern(self) -> str | None:
        return self.effective_str("owned_concern")

    @property
    def owned_connection(self) -> str | None:
        return self.effective_str("owned_connection")

    @property
    def owned_constraint(self) -> str | None:
        return self.effective_str("owned_constraint")

    @property
    def owned_enumeration(self) -> str | None:
        return self.effective_str("owned_enumeration")

    @property
    def owned_flow(self) -> str | None:
        return self.effective_str("owned_flow")

    @property
    def owned_interface(self) -> str | None:
        return self.effective_str("owned_interface")

    @property
    def owned_item(self) -> str | None:
        return self.effective_str("owned_item")

    @property
    def owned_metadata(self) -> str | None:
        return self.effective_str("owned_metadata")

    @property
    def owned_occurrence(self) -> str | None:
        return self.effective_str("owned_occurrence")

    @property
    def owned_part(self) -> str | None:
        return self.effective_str("owned_part")

    @property
    def owned_port(self) -> str | None:
        return self.effective_str("owned_port")

    @property
    def owned_reference(self) -> str | None:
        return self.effective_str("owned_reference")

    @property
    def owned_rendering(self) -> str | None:
        return self.effective_str("owned_rendering")

    @property
    def owned_requirement(self) -> str | None:
        return self.effective_str("owned_requirement")

    @property
    def owned_state(self) -> str | None:
        return self.effective_str("owned_state")

    @property
    def owned_transition(self) -> str | None:
        return self.effective_str("owned_transition")

    @property
    def owned_usage(self) -> str | None:
        return self.effective_str("owned_usage")

    @property
    def owned_use_case(self) -> str | None:
        return self.effective_str("owned_use_case")

    @property
    def owned_verification_case(self) -> str | None:
        return self.effective_str("owned_verification_case")

    @property
    def owned_view(self) -> str | None:
        return self.effective_str("owned_view")

    @property
    def owned_viewpoint(self) -> str | None:
        return self.effective_str("owned_viewpoint")

    @property
    def usage(self) -> str | None:
        return self.effective_str("usage")

    @property
    def variant(self) -> str | None:
        return self.effective_str("variant")

    @property
    def variant_membership(self) -> str | None:
        return self.effective_str("variant_membership")

class OccurrenceDefinition(Class, Definition):
    concept = None
    metatype_id = "SysML::Systems::OccurrenceDefinition"
    metatype_ids = ("SysML::Systems::OccurrenceDefinition",)
    kind_name = "OccurrenceDefinition"
    kind_names = ("OccurrenceDefinition",)

    @property
    def is_individual(self) -> bool | None:
        return self.effective_bool("is_individual")

class ActionDefinition(Behavior, OccurrenceDefinition):
    concept = None
    metatype_id = "SysML::Systems::ActionDefinition"
    metatype_ids = ("SysML::Systems::ActionDefinition",)
    kind_name = "ActionDefinition"
    kind_names = ("ActionDefinition",)

    @property
    def action(self) -> str | None:
        return self.effective_str("action")

class Relationship(Element):
    concept = None
    metatype_id = "KerML::Root::Relationship"
    metatype_ids = ("KerML::Root::Relationship",)
    kind_name = "Relationship"
    kind_names = ("Relationship",)

    @property
    def is_implied(self) -> bool | None:
        return self.effective_bool("is_implied")

    @property
    def owned_related_element(self) -> str | None:
        return self.effective_str("owned_related_element")

    @property
    def owning_related_element(self) -> str | None:
        return self.effective_str("owning_related_element")

    @property
    def related_element(self) -> str | None:
        return self.effective_str("related_element")

    @property
    def source(self) -> str | None:
        return self.effective_str("source")

    @property
    def target(self) -> str | None:
        return self.effective_str("target")

class Membership(Relationship):
    concept = None
    metatype_id = "KerML::Root::Membership"
    metatype_ids = ("KerML::Root::Membership",)
    kind_name = "Membership"
    kind_names = ("Membership",)

    @property
    def member_element(self) -> str | None:
        return self.effective_str("member_element")

    @property
    def member_element_id(self) -> str | None:
        return self.effective_str("member_element_id")

    @property
    def member_name(self) -> str | None:
        return self.effective_str("member_name")

    @property
    def member_short_name(self) -> str | None:
        return self.effective_str("member_short_name")

    @property
    def membership_owning_namespace(self) -> str | None:
        return self.effective_str("membership_owning_namespace")

    @property
    def visibility(self) -> str | None:
        return self.effective_str("visibility")

class OwningMembership(Membership):
    concept = None
    metatype_id = "KerML::Root::OwningMembership"
    metatype_ids = ("KerML::Root::OwningMembership",)
    kind_name = "OwningMembership"
    kind_names = ("OwningMembership",)

    @property
    def owned_member_element(self) -> str | None:
        return self.effective_str("owned_member_element")

    @property
    def owned_member_element_id(self) -> str | None:
        return self.effective_str("owned_member_element_id")

    @property
    def owned_member_name(self) -> str | None:
        return self.effective_str("owned_member_name")

    @property
    def owned_member_short_name(self) -> str | None:
        return self.effective_str("owned_member_short_name")

class FeatureMembership(OwningMembership):
    concept = None
    metatype_id = "KerML::Core::FeatureMembership"
    metatype_ids = ("KerML::Core::FeatureMembership",)
    kind_name = "FeatureMembership"
    kind_names = ("FeatureMembership",)

    @property
    def owned_member_feature(self) -> str | None:
        return self.effective_str("owned_member_feature")

    @property
    def owning_type(self) -> str | None:
        return self.effective_str("owning_type")

class ParameterMembership(FeatureMembership):
    concept = None
    metatype_id = "KerML::Kernel::ParameterMembership"
    metatype_ids = ("KerML::Kernel::ParameterMembership",)
    kind_name = "ParameterMembership"
    kind_names = ("ParameterMembership",)

    @property
    def owned_member_parameter(self) -> str | None:
        return self.effective_str("owned_member_parameter")

class ActorMembership(ParameterMembership):
    concept = None
    metatype_id = "SysML::Systems::ActorMembership"
    metatype_ids = ("SysML::Systems::ActorMembership",)
    kind_name = "ActorMembership"
    kind_names = ("ActorMembership",)

    @property
    def owned_actor_parameter(self) -> str | None:
        return self.effective_str("owned_actor_parameter")

class Association(Classifier, Relationship):
    concept = None
    metatype_id = "KerML::Kernel::Association"
    metatype_ids = ("KerML::Kernel::Association",)
    kind_name = "Association"
    kind_names = ("Association",)

    @property
    def association_end(self) -> str | None:
        return self.effective_str("association_end")

    @property
    def related_type(self) -> str | None:
        return self.effective_str("related_type")

    @property
    def source_type(self) -> str | None:
        return self.effective_str("source_type")

    @property
    def target_type(self) -> str | None:
        return self.effective_str("target_type")

class Structure(Class):
    concept = None
    metatype_id = "KerML::Kernel::Structure"
    metatype_ids = ("KerML::Kernel::Structure",)
    kind_name = "Structure"
    kind_names = ("Structure",)

class AssociationStructure(Association, Structure):
    concept = None
    metatype_id = "KerML::Kernel::AssociationStructure"
    metatype_ids = ("KerML::Kernel::AssociationStructure",)
    kind_name = "AssociationStructure"
    kind_names = ("AssociationStructure",)

class ItemDefinition(OccurrenceDefinition, Structure):
    concept = None
    metatype_id = "SysML::Systems::ItemDefinition"
    metatype_ids = ("SysML::Systems::ItemDefinition",)
    kind_name = "ItemDefinition"
    kind_names = ("ItemDefinition",)

class PartDefinition(ItemDefinition):
    concept = None
    metatype_id = "SysML::Systems::PartDefinition"
    metatype_ids = ("SysML::Systems::PartDefinition",)
    kind_name = "PartDefinition"
    kind_names = ("PartDefinition",)

class ConnectionDefinition(AssociationStructure, PartDefinition):
    concept = None
    metatype_id = "SysML::Systems::ConnectionDefinition"
    metatype_ids = ("SysML::Systems::ConnectionDefinition",)
    kind_name = "ConnectionDefinition"
    kind_names = ("ConnectionDefinition",)

    @property
    def connection_end(self) -> str | None:
        return self.effective_str("connection_end")

    @property
    def is_sufficient(self) -> bool | None:
        return self.effective_bool("is_sufficient")

class AllocationDefinition(ConnectionDefinition):
    concept = None
    metatype_id = "SysML::Systems::AllocationDefinition"
    metatype_ids = ("SysML::Systems::AllocationDefinition",)
    kind_name = "AllocationDefinition"
    kind_names = ("AllocationDefinition",)

    @property
    def allocation(self) -> str | None:
        return self.effective_str("allocation")

class Connector(Feature, Relationship):
    concept = None
    metatype_id = "KerML::Kernel::Connector"
    metatype_ids = ("KerML::Kernel::Connector",)
    kind_name = "Connector"
    kind_names = ("Connector",)

    @property
    def association(self) -> str | None:
        return self.effective_str("association")

    @property
    def connector_end(self) -> str | None:
        return self.effective_str("connector_end")

    @property
    def default_featuring_type(self) -> str | None:
        return self.effective_str("default_featuring_type")

    @property
    def related_feature(self) -> str | None:
        return self.effective_str("related_feature")

    @property
    def source_feature(self) -> str | None:
        return self.effective_str("source_feature")

    @property
    def target_feature(self) -> str | None:
        return self.effective_str("target_feature")

class ConnectorAsUsage(Connector, Usage):
    concept = None
    metatype_id = "SysML::Systems::ConnectorAsUsage"
    metatype_ids = ("SysML::Systems::ConnectorAsUsage",)
    kind_name = "ConnectorAsUsage"
    kind_names = ("ConnectorAsUsage",)

class ItemUsage(OccurrenceUsage):
    concept = None
    metatype_id = "SysML::Systems::ItemUsage"
    metatype_ids = ("SysML::Systems::ItemUsage",)
    kind_name = "ItemUsage"
    kind_names = ("ItemUsage",)

    @property
    def item_definition(self) -> str | None:
        return self.effective_str("item_definition")

class PartUsage(ItemUsage):
    concept = None
    metatype_id = "SysML::Systems::PartUsage"
    metatype_ids = ("SysML::Systems::PartUsage",)
    kind_name = "PartUsage"
    kind_names = ("PartUsage",)

    @property
    def part_definition(self) -> str | None:
        return self.effective_str("part_definition")

class ConnectionUsage(ConnectorAsUsage, PartUsage):
    concept = None
    metatype_id = "SysML::Systems::ConnectionUsage"
    metatype_ids = ("SysML::Systems::ConnectionUsage",)
    kind_name = "ConnectionUsage"
    kind_names = ("ConnectionUsage",)

    @property
    def connection_definition(self) -> str | None:
        return self.effective_str("connection_definition")

class AllocationUsage(ConnectionUsage):
    concept = None
    metatype_id = "SysML::Systems::AllocationUsage"
    metatype_ids = ("SysML::Systems::AllocationUsage",)
    kind_name = "AllocationUsage"
    kind_names = ("AllocationUsage",)

    @property
    def allocation_definition(self) -> str | None:
        return self.effective_str("allocation_definition")

class Function(Behavior):
    concept = None
    metatype_id = "KerML::Kernel::Function"
    metatype_ids = ("KerML::Kernel::Function",)
    kind_name = "Function"
    kind_names = ("Function",)

    @property
    def expression(self) -> str | None:
        return self.effective_str("expression")

    @property
    def is_model_level_evaluable(self) -> bool | None:
        return self.effective_bool("is_model_level_evaluable")

    @property
    def result(self) -> str | None:
        return self.effective_str("result")

class CalculationDefinition(ActionDefinition, Function):
    concept = None
    metatype_id = "SysML::Systems::CalculationDefinition"
    metatype_ids = ("SysML::Systems::CalculationDefinition",)
    kind_name = "CalculationDefinition"
    kind_names = ("CalculationDefinition",)

    @property
    def calculation(self) -> str | None:
        return self.effective_str("calculation")

class CaseDefinition(CalculationDefinition):
    concept = None
    metatype_id = "SysML::Systems::CaseDefinition"
    metatype_ids = ("SysML::Systems::CaseDefinition",)
    kind_name = "CaseDefinition"
    kind_names = ("CaseDefinition",)

    @property
    def actor_parameter(self) -> str | None:
        return self.effective_str("actor_parameter")

    @property
    def objective_requirement(self) -> str | None:
        return self.effective_str("objective_requirement")

    @property
    def subject_parameter(self) -> str | None:
        return self.effective_str("subject_parameter")

class AnalysisCaseDefinition(CaseDefinition):
    concept = None
    metatype_id = "SysML::Systems::AnalysisCaseDefinition"
    metatype_ids = ("SysML::Systems::AnalysisCaseDefinition",)
    kind_name = "AnalysisCaseDefinition"
    kind_names = ("AnalysisCaseDefinition",)

    @property
    def result_expression(self) -> str | None:
        return self.effective_str("result_expression")

class Expression(Step):
    concept = None
    metatype_id = "KerML::Kernel::Expression"
    metatype_ids = ("KerML::Kernel::Expression",)
    kind_name = "Expression"
    kind_names = ("Expression",)

    @property
    def function(self) -> str | None:
        return self.effective_str("function")

    @property
    def is_model_level_evaluable(self) -> bool | None:
        return self.effective_bool("is_model_level_evaluable")

    @property
    def result(self) -> str | None:
        return self.effective_str("result")

class CalculationUsage(ActionUsage, Expression):
    concept = None
    metatype_id = "SysML::Systems::CalculationUsage"
    metatype_ids = ("SysML::Systems::CalculationUsage",)
    kind_name = "CalculationUsage"
    kind_names = ("CalculationUsage",)

    @property
    def calculation_definition(self) -> str | None:
        return self.effective_str("calculation_definition")

class CaseUsage(CalculationUsage):
    concept = None
    metatype_id = "SysML::Systems::CaseUsage"
    metatype_ids = ("SysML::Systems::CaseUsage",)
    kind_name = "CaseUsage"
    kind_names = ("CaseUsage",)

    @property
    def actor_parameter(self) -> str | None:
        return self.effective_str("actor_parameter")

    @property
    def case_definition(self) -> str | None:
        return self.effective_str("case_definition")

    @property
    def objective_requirement(self) -> str | None:
        return self.effective_str("objective_requirement")

    @property
    def subject_parameter(self) -> str | None:
        return self.effective_str("subject_parameter")

class AnalysisCaseUsage(CaseUsage):
    concept = None
    metatype_id = "SysML::Systems::AnalysisCaseUsage"
    metatype_ids = ("SysML::Systems::AnalysisCaseUsage",)
    kind_name = "AnalysisCaseUsage"
    kind_names = ("AnalysisCaseUsage",)

    @property
    def analysis_case_definition(self) -> str | None:
        return self.effective_str("analysis_case_definition")

    @property
    def result_expression(self) -> str | None:
        return self.effective_str("result_expression")

class AnnotatingElement(Element):
    concept = None
    metatype_id = "KerML::Root::AnnotatingElement"
    metatype_ids = ("KerML::Root::AnnotatingElement",)
    kind_name = "AnnotatingElement"
    kind_names = ("AnnotatingElement",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def annotation(self) -> str | None:
        return self.effective_str("annotation")

    @property
    def owned_annotating_relationship(self) -> str | None:
        return self.effective_str("owned_annotating_relationship")

    @property
    def owning_annotating_relationship(self) -> str | None:
        return self.effective_str("owning_annotating_relationship")

class Annotation(Relationship):
    concept = None
    metatype_id = "KerML::Root::Annotation"
    metatype_ids = ("KerML::Root::Annotation",)
    kind_name = "Annotation"
    kind_names = ("Annotation",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def annotating_element(self) -> str | None:
        return self.effective_str("annotating_element")

    @property
    def owned_annotating_element(self) -> str | None:
        return self.effective_str("owned_annotating_element")

    @property
    def owning_annotated_element(self) -> str | None:
        return self.effective_str("owning_annotated_element")

    @property
    def owning_annotating_element(self) -> str | None:
        return self.effective_str("owning_annotating_element")

class BooleanExpression(Expression):
    concept = None
    metatype_id = "KerML::Kernel::BooleanExpression"
    metatype_ids = ("KerML::Kernel::BooleanExpression",)
    kind_name = "BooleanExpression"
    kind_names = ("BooleanExpression",)

    @property
    def predicate(self) -> str | None:
        return self.effective_str("predicate")

class ConstraintUsage(BooleanExpression, OccurrenceUsage):
    concept = None
    metatype_id = "SysML::Systems::ConstraintUsage"
    metatype_ids = ("SysML::Systems::ConstraintUsage",)
    kind_name = "ConstraintUsage"
    kind_names = ("ConstraintUsage",)

    @property
    def constraint_definition(self) -> str | None:
        return self.effective_str("constraint_definition")

class Invariant(BooleanExpression):
    concept = None
    metatype_id = "KerML::Kernel::Invariant"
    metatype_ids = ("KerML::Kernel::Invariant",)
    kind_name = "Invariant"
    kind_names = ("Invariant",)

    @property
    def is_negated(self) -> bool | None:
        return self.effective_bool("is_negated")

class AssertConstraintUsage(ConstraintUsage, Invariant):
    concept = None
    metatype_id = "SysML::Systems::AssertConstraintUsage"
    metatype_ids = ("SysML::Systems::AssertConstraintUsage",)
    kind_name = "AssertConstraintUsage"
    kind_names = ("AssertConstraintUsage",)

    @property
    def asserted_constraint(self) -> str | None:
        return self.effective_str("asserted_constraint")

class AssignmentActionUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::AssignmentActionUsage"
    metatype_ids = ("SysML::Systems::AssignmentActionUsage",)
    kind_name = "AssignmentActionUsage"
    kind_names = ("AssignmentActionUsage",)

    @property
    def referent(self) -> str | None:
        return self.effective_str("referent")

    @property
    def target_argument(self) -> str | None:
        return self.effective_str("target_argument")

    @property
    def value_expression(self) -> str | None:
        return self.effective_str("value_expression")

class DataType(Classifier):
    concept = None
    metatype_id = "KerML::Kernel::DataType"
    metatype_ids = ("KerML::Kernel::DataType",)
    kind_name = "DataType"
    kind_names = ("DataType",)

class AttributeDefinition(DataType, Definition):
    concept = None
    metatype_id = "SysML::Systems::AttributeDefinition"
    metatype_ids = ("SysML::Systems::AttributeDefinition",)
    kind_name = "AttributeDefinition"
    kind_names = ("AttributeDefinition",)

class AttributeUsage(Usage):
    concept = None
    metatype_id = "SysML::Systems::AttributeUsage"
    metatype_ids = ("SysML::Systems::AttributeUsage",)
    kind_name = "AttributeUsage"
    kind_names = ("AttributeUsage",)

    @property
    def attribute_definition(self) -> str | None:
        return self.effective_str("attribute_definition")

    @property
    def is_reference(self) -> bool | None:
        return self.effective_bool("is_reference")

class BindingConnector(Connector):
    concept = None
    metatype_id = "KerML::Kernel::BindingConnector"
    metatype_ids = ("KerML::Kernel::BindingConnector",)
    kind_name = "BindingConnector"
    kind_names = ("BindingConnector",)

class BindingConnectorAsUsage(BindingConnector, ConnectorAsUsage):
    concept = None
    metatype_id = "SysML::Systems::BindingConnectorAsUsage"
    metatype_ids = ("SysML::Systems::BindingConnectorAsUsage",)
    kind_name = "BindingConnectorAsUsage"
    kind_names = ("BindingConnectorAsUsage",)

class CausationMetadata(ElementFacade):
    concept = None
    metatype_id = "CauseAndEffect::CausationMetadata"
    metatype_ids = ("CauseAndEffect::CausationMetadata",)
    kind_name = "CausationMetadata"
    kind_names = ("CausationMetadata",)

    @property
    def is_necessary(self) -> bool | None:
        return self.effective_bool("is_necessary")

    @property
    def is_sufficient(self) -> bool | None:
        return self.effective_bool("is_sufficient")

    @property
    def probability(self) -> float | None:
        return self.effective_float("probability")

class Metaobject(ElementFacade):
    concept = None
    metatype_id = "Metaobjects::Metaobject"
    metatype_ids = ("Metaobjects::Metaobject",)
    kind_name = "Metaobject"
    kind_names = ("Metaobject",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def self(self) -> str | None:
        return self.effective_str("self")

class SemanticMetadata(Metaobject):
    concept = None
    metatype_id = "Metaobjects::SemanticMetadata"
    metatype_ids = ("Metaobjects::SemanticMetadata",)
    kind_name = "SemanticMetadata"
    kind_names = ("SemanticMetadata",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class CausationSemanticMetadadata(CausationMetadata, SemanticMetadata):
    concept = None
    metatype_id = "CauseAndEffect::CausationSemanticMetadadata"
    metatype_ids = ("CauseAndEffect::CausationSemanticMetadadata",)
    kind_name = "CausationSemanticMetadadata"
    kind_names = ("CausationSemanticMetadadata",)

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class CauseMetadata(SemanticMetadata):
    concept = None
    metatype_id = "CauseAndEffect::CauseMetadata"
    metatype_ids = ("CauseAndEffect::CauseMetadata",)
    kind_name = "CauseMetadata"
    kind_names = ("CauseMetadata",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class InstantiationExpression(Expression):
    concept = None
    metatype_id = "KerML::Kernel::InstantiationExpression"
    metatype_ids = ("KerML::Kernel::InstantiationExpression",)
    kind_name = "InstantiationExpression"
    kind_names = ("InstantiationExpression",)

    @property
    def argument(self) -> str | None:
        return self.effective_str("argument")

    @property
    def instantiated_type(self) -> str | None:
        return self.effective_str("instantiated_type")

class InvocationExpression(InstantiationExpression):
    concept = None
    metatype_id = "KerML::Kernel::InvocationExpression"
    metatype_ids = ("KerML::Kernel::InvocationExpression",)
    kind_name = "InvocationExpression"
    kind_names = ("InvocationExpression",)

class OperatorExpression(InvocationExpression):
    concept = None
    metatype_id = "KerML::Kernel::OperatorExpression"
    metatype_ids = ("KerML::Kernel::OperatorExpression",)
    kind_name = "OperatorExpression"
    kind_names = ("OperatorExpression",)

    @property
    def operator(self) -> str | None:
        return self.effective_str("operator")

class CollectExpression(OperatorExpression):
    concept = None
    metatype_id = "KerML::Kernel::CollectExpression"
    metatype_ids = ("KerML::Kernel::CollectExpression",)
    kind_name = "CollectExpression"
    kind_names = ("CollectExpression",)

    @property
    def operator(self) -> str | None:
        return self.effective_str("operator")

class Comment(AnnotatingElement):
    concept = None
    metatype_id = "KerML::Root::Comment"
    metatype_ids = ("KerML::Root::Comment",)
    kind_name = "Comment"
    kind_names = ("Comment",)

    @property
    def body(self) -> str | None:
        return self.effective_str("body")

    @property
    def locale(self) -> str | None:
        return self.effective_str("locale")

class Predicate(Function):
    concept = None
    metatype_id = "KerML::Kernel::Predicate"
    metatype_ids = ("KerML::Kernel::Predicate",)
    kind_name = "Predicate"
    kind_names = ("Predicate",)

class ConstraintDefinition(OccurrenceDefinition, Predicate):
    concept = None
    metatype_id = "SysML::Systems::ConstraintDefinition"
    metatype_ids = ("SysML::Systems::ConstraintDefinition",)
    kind_name = "ConstraintDefinition"
    kind_names = ("ConstraintDefinition",)

class RequirementDefinition(ConstraintDefinition):
    concept = None
    metatype_id = "SysML::Systems::RequirementDefinition"
    metatype_ids = ("SysML::Systems::RequirementDefinition",)
    kind_name = "RequirementDefinition"
    kind_names = ("RequirementDefinition",)

    @property
    def actor_parameter(self) -> str | None:
        return self.effective_str("actor_parameter")

    @property
    def assumed_constraint(self) -> str | None:
        return self.effective_str("assumed_constraint")

    @property
    def framed_concern(self) -> str | None:
        return self.effective_str("framed_concern")

    @property
    def req_id(self) -> str | None:
        return self.effective_str("req_id")

    @property
    def required_constraint(self) -> str | None:
        return self.effective_str("required_constraint")

    @property
    def stakeholder_parameter(self) -> str | None:
        return self.effective_str("stakeholder_parameter")

    @property
    def subject_parameter(self) -> str | None:
        return self.effective_str("subject_parameter")

    @property
    def text(self) -> str | None:
        return self.effective_str("text")

class ConcernDefinition(RequirementDefinition):
    concept = None
    metatype_id = "SysML::Systems::ConcernDefinition"
    metatype_ids = ("SysML::Systems::ConcernDefinition",)
    kind_name = "ConcernDefinition"
    kind_names = ("ConcernDefinition",)

class RequirementUsage(ConstraintUsage):
    concept = None
    metatype_id = "SysML::Systems::RequirementUsage"
    metatype_ids = ("SysML::Systems::RequirementUsage",)
    kind_name = "RequirementUsage"
    kind_names = ("RequirementUsage",)

    @property
    def actor_parameter(self) -> str | None:
        return self.effective_str("actor_parameter")

    @property
    def assumed_constraint(self) -> str | None:
        return self.effective_str("assumed_constraint")

    @property
    def framed_concern(self) -> str | None:
        return self.effective_str("framed_concern")

    @property
    def req_id(self) -> str | None:
        return self.effective_str("req_id")

    @property
    def required_constraint(self) -> str | None:
        return self.effective_str("required_constraint")

    @property
    def requirement_definition(self) -> str | None:
        return self.effective_str("requirement_definition")

    @property
    def stakeholder_parameter(self) -> str | None:
        return self.effective_str("stakeholder_parameter")

    @property
    def subject_parameter(self) -> str | None:
        return self.effective_str("subject_parameter")

    @property
    def text(self) -> str | None:
        return self.effective_str("text")

class ConcernUsage(RequirementUsage):
    concept = None
    metatype_id = "SysML::Systems::ConcernUsage"
    metatype_ids = ("SysML::Systems::ConcernUsage",)
    kind_name = "ConcernUsage"
    kind_names = ("ConcernUsage",)

    @property
    def concern_definition(self) -> str | None:
        return self.effective_str("concern_definition")

class PortDefinition(OccurrenceDefinition, Structure):
    concept = None
    metatype_id = "SysML::Systems::PortDefinition"
    metatype_ids = ("SysML::Systems::PortDefinition",)
    kind_name = "PortDefinition"
    kind_names = ("PortDefinition",)

    @property
    def conjugated_port_definition(self) -> str | None:
        return self.effective_str("conjugated_port_definition")

class ConjugatedPortDefinition(PortDefinition):
    concept = None
    metatype_id = "SysML::Systems::ConjugatedPortDefinition"
    metatype_ids = ("SysML::Systems::ConjugatedPortDefinition",)
    kind_name = "ConjugatedPortDefinition"
    kind_names = ("ConjugatedPortDefinition",)

    @property
    def original_port_definition(self) -> str | None:
        return self.effective_str("original_port_definition")

    @property
    def owned_port_conjugator(self) -> str | None:
        return self.effective_str("owned_port_conjugator")

class Specialization(Relationship):
    concept = None
    metatype_id = "KerML::Core::Specialization"
    metatype_ids = ("KerML::Core::Specialization",)
    kind_name = "Specialization"
    kind_names = ("Specialization",)

    @property
    def general(self) -> str | None:
        return self.effective_str("general")

    @property
    def owning_type(self) -> str | None:
        return self.effective_str("owning_type")

    @property
    def specific(self) -> str | None:
        return self.effective_str("specific")

class FeatureTyping(Specialization):
    concept = None
    metatype_id = "KerML::Core::FeatureTyping"
    metatype_ids = ("KerML::Core::FeatureTyping",)
    kind_name = "FeatureTyping"
    kind_names = ("FeatureTyping",)

    @property
    def owning_feature(self) -> str | None:
        return self.effective_str("owning_feature")

    @property
    def type(self) -> str | None:
        return self.effective_str("type")

    @property
    def typed_feature(self) -> str | None:
        return self.effective_str("typed_feature")

class ConjugatedPortTyping(FeatureTyping):
    concept = None
    metatype_id = "SysML::Systems::ConjugatedPortTyping"
    metatype_ids = ("SysML::Systems::ConjugatedPortTyping",)
    kind_name = "ConjugatedPortTyping"
    kind_names = ("ConjugatedPortTyping",)

    @property
    def conjugated_port_definition(self) -> str | None:
        return self.effective_str("conjugated_port_definition")

    @property
    def port_definition(self) -> str | None:
        return self.effective_str("port_definition")

class Conjugation(Relationship):
    concept = None
    metatype_id = "KerML::Core::Conjugation"
    metatype_ids = ("KerML::Core::Conjugation",)
    kind_name = "Conjugation"
    kind_names = ("Conjugation",)

    @property
    def conjugated_type(self) -> str | None:
        return self.effective_str("conjugated_type")

    @property
    def original_type(self) -> str | None:
        return self.effective_str("original_type")

    @property
    def owning_type(self) -> str | None:
        return self.effective_str("owning_type")

class ConstructorExpression(InstantiationExpression):
    concept = None
    metatype_id = "KerML::Kernel::ConstructorExpression"
    metatype_ids = ("KerML::Kernel::ConstructorExpression",)
    kind_name = "ConstructorExpression"
    kind_names = ("ConstructorExpression",)

class ControlNode(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::ControlNode"
    metatype_ids = ("SysML::Systems::ControlNode",)
    kind_name = "ControlNode"
    kind_names = ("ControlNode",)

class Subsetting(Specialization):
    concept = None
    metatype_id = "KerML::Core::Subsetting"
    metatype_ids = ("KerML::Core::Subsetting",)
    kind_name = "Subsetting"
    kind_names = ("Subsetting",)

    @property
    def owning_feature(self) -> str | None:
        return self.effective_str("owning_feature")

    @property
    def subsetted_feature(self) -> str | None:
        return self.effective_str("subsetted_feature")

    @property
    def subsetting_feature(self) -> str | None:
        return self.effective_str("subsetting_feature")

class CrossSubsetting(Subsetting):
    concept = None
    metatype_id = "KerML::Core::CrossSubsetting"
    metatype_ids = ("KerML::Core::CrossSubsetting",)
    kind_name = "CrossSubsetting"
    kind_names = ("CrossSubsetting",)

    @property
    def crossed_feature(self) -> str | None:
        return self.effective_str("crossed_feature")

    @property
    def crossing_feature(self) -> str | None:
        return self.effective_str("crossing_feature")

class DecisionNode(ControlNode):
    concept = None
    metatype_id = "SysML::Systems::DecisionNode"
    metatype_ids = ("SysML::Systems::DecisionNode",)
    kind_name = "DecisionNode"
    kind_names = ("DecisionNode",)

class Dependency(Relationship):
    concept = None
    metatype_id = "KerML::Root::Dependency"
    metatype_ids = ("KerML::Root::Dependency",)
    kind_name = "Dependency"
    kind_names = ("Dependency",)

    @property
    def client(self) -> str | None:
        return self.effective_str("client")

    @property
    def supplier(self) -> str | None:
        return self.effective_str("supplier")

class DerivationMetadata(SemanticMetadata):
    concept = None
    metatype_id = "RequirementDerivation::DerivationMetadata"
    metatype_ids = ("RequirementDerivation::DerivationMetadata",)
    kind_name = "DerivationMetadata"
    kind_names = ("DerivationMetadata",)

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class DerivedRequirementMetadata(SemanticMetadata):
    concept = None
    metatype_id = "RequirementDerivation::DerivedRequirementMetadata"
    metatype_ids = ("RequirementDerivation::DerivedRequirementMetadata",)
    kind_name = "DerivedRequirementMetadata"
    kind_names = ("DerivedRequirementMetadata",)

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class Differencing(Relationship):
    concept = None
    metatype_id = "KerML::Core::Differencing"
    metatype_ids = ("KerML::Core::Differencing",)
    kind_name = "Differencing"
    kind_names = ("Differencing",)

    @property
    def differencing_type(self) -> str | None:
        return self.effective_str("differencing_type")

    @property
    def type_differenced(self) -> str | None:
        return self.effective_str("type_differenced")

class Disjoining(Relationship):
    concept = None
    metatype_id = "KerML::Core::Disjoining"
    metatype_ids = ("KerML::Core::Disjoining",)
    kind_name = "Disjoining"
    kind_names = ("Disjoining",)

    @property
    def disjoining_type(self) -> str | None:
        return self.effective_str("disjoining_type")

    @property
    def owning_type(self) -> str | None:
        return self.effective_str("owning_type")

    @property
    def type_disjoined(self) -> str | None:
        return self.effective_str("type_disjoined")

class Documentation(Comment):
    concept = None
    metatype_id = "KerML::Root::Documentation"
    metatype_ids = ("KerML::Root::Documentation",)
    kind_name = "Documentation"
    kind_names = ("Documentation",)

    @property
    def documented_element(self) -> str | None:
        return self.effective_str("documented_element")

class EffectMetadata(SemanticMetadata):
    concept = None
    metatype_id = "CauseAndEffect::EffectMetadata"
    metatype_ids = ("CauseAndEffect::EffectMetadata",)
    kind_name = "EffectMetadata"
    kind_names = ("EffectMetadata",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class ElementFilterMembership(OwningMembership):
    concept = None
    metatype_id = "KerML::Kernel::ElementFilterMembership"
    metatype_ids = ("KerML::Kernel::ElementFilterMembership",)
    kind_name = "ElementFilterMembership"
    kind_names = ("ElementFilterMembership",)

    @property
    def condition(self) -> str | None:
        return self.effective_str("condition")

class EndFeatureMembership(FeatureMembership):
    concept = None
    metatype_id = "KerML::Core::EndFeatureMembership"
    metatype_ids = ("KerML::Core::EndFeatureMembership",)
    kind_name = "EndFeatureMembership"
    kind_names = ("EndFeatureMembership",)

    @property
    def owned_member_feature(self) -> str | None:
        return self.effective_str("owned_member_feature")

class EnumerationDefinition(AttributeDefinition):
    concept = None
    metatype_id = "SysML::Systems::EnumerationDefinition"
    metatype_ids = ("SysML::Systems::EnumerationDefinition",)
    kind_name = "EnumerationDefinition"
    kind_names = ("EnumerationDefinition",)

    @property
    def enumerated_value(self) -> str | None:
        return self.effective_str("enumerated_value")

    @property
    def is_variation(self) -> bool | None:
        return self.effective_bool("is_variation")

class EnumerationUsage(AttributeUsage):
    concept = None
    metatype_id = "SysML::Systems::EnumerationUsage"
    metatype_ids = ("SysML::Systems::EnumerationUsage",)
    kind_name = "EnumerationUsage"
    kind_names = ("EnumerationUsage",)

    @property
    def enumeration_definition(self) -> str | None:
        return self.effective_str("enumeration_definition")

class EventOccurrenceUsage(OccurrenceUsage):
    concept = None
    metatype_id = "SysML::Systems::EventOccurrenceUsage"
    metatype_ids = ("SysML::Systems::EventOccurrenceUsage",)
    kind_name = "EventOccurrenceUsage"
    kind_names = ("EventOccurrenceUsage",)

    @property
    def event_occurrence(self) -> str | None:
        return self.effective_str("event_occurrence")

    @property
    def is_reference(self) -> bool | None:
        return self.effective_bool("is_reference")

class PerformActionUsage(ActionUsage, EventOccurrenceUsage):
    concept = None
    metatype_id = "SysML::Systems::PerformActionUsage"
    metatype_ids = ("SysML::Systems::PerformActionUsage",)
    kind_name = "PerformActionUsage"
    kind_names = ("PerformActionUsage",)

    @property
    def performed_action(self) -> str | None:
        return self.effective_str("performed_action")

class StateUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::StateUsage"
    metatype_ids = ("SysML::Systems::StateUsage",)
    kind_name = "StateUsage"
    kind_names = ("StateUsage",)

    @property
    def do_action(self) -> str | None:
        return self.effective_str("do_action")

    @property
    def entry_action(self) -> str | None:
        return self.effective_str("entry_action")

    @property
    def exit_action(self) -> str | None:
        return self.effective_str("exit_action")

    @property
    def is_parallel(self) -> bool | None:
        return self.effective_bool("is_parallel")

    @property
    def state_definition(self) -> str | None:
        return self.effective_str("state_definition")

class ExhibitStateUsage(PerformActionUsage, StateUsage):
    concept = None
    metatype_id = "SysML::Systems::ExhibitStateUsage"
    metatype_ids = ("SysML::Systems::ExhibitStateUsage",)
    kind_name = "ExhibitStateUsage"
    kind_names = ("ExhibitStateUsage",)

    @property
    def exhibited_state(self) -> str | None:
        return self.effective_str("exhibited_state")

class Import(Relationship):
    concept = None
    metatype_id = "KerML::Root::Import"
    metatype_ids = ("KerML::Root::Import",)
    kind_name = "Import"
    kind_names = ("Import",)

    @property
    def import_owning_namespace(self) -> str | None:
        return self.effective_str("import_owning_namespace")

    @property
    def imported_element(self) -> str | None:
        return self.effective_str("imported_element")

    @property
    def is_import_all(self) -> bool | None:
        return self.effective_bool("is_import_all")

    @property
    def is_recursive(self) -> bool | None:
        return self.effective_bool("is_recursive")

    @property
    def visibility(self) -> str | None:
        return self.effective_str("visibility")

class Expose(Import):
    concept = None
    metatype_id = "SysML::Systems::Expose"
    metatype_ids = ("SysML::Systems::Expose",)
    kind_name = "Expose"
    kind_names = ("Expose",)

    @property
    def is_import_all(self) -> bool | None:
        return self.effective_bool("is_import_all")

    @property
    def visibility(self) -> str | None:
        return self.effective_str("visibility")

class FeatureChainExpression(OperatorExpression):
    concept = None
    metatype_id = "KerML::Kernel::FeatureChainExpression"
    metatype_ids = ("KerML::Kernel::FeatureChainExpression",)
    kind_name = "FeatureChainExpression"
    kind_names = ("FeatureChainExpression",)

    @property
    def operator(self) -> str | None:
        return self.effective_str("operator")

    @property
    def target_feature(self) -> str | None:
        return self.effective_str("target_feature")

class FeatureChaining(Relationship):
    concept = None
    metatype_id = "KerML::Core::FeatureChaining"
    metatype_ids = ("KerML::Core::FeatureChaining",)
    kind_name = "FeatureChaining"
    kind_names = ("FeatureChaining",)

    @property
    def chaining_feature(self) -> str | None:
        return self.effective_str("chaining_feature")

    @property
    def feature_chained(self) -> str | None:
        return self.effective_str("feature_chained")

class FeatureInverting(Relationship):
    concept = None
    metatype_id = "KerML::Core::FeatureInverting"
    metatype_ids = ("KerML::Core::FeatureInverting",)
    kind_name = "FeatureInverting"
    kind_names = ("FeatureInverting",)

    @property
    def feature_inverted(self) -> str | None:
        return self.effective_str("feature_inverted")

    @property
    def inverting_feature(self) -> str | None:
        return self.effective_str("inverting_feature")

    @property
    def owning_feature(self) -> str | None:
        return self.effective_str("owning_feature")

class FeatureReferenceExpression(Expression):
    concept = None
    metatype_id = "KerML::Kernel::FeatureReferenceExpression"
    metatype_ids = ("KerML::Kernel::FeatureReferenceExpression",)
    kind_name = "FeatureReferenceExpression"
    kind_names = ("FeatureReferenceExpression",)

    @property
    def referent(self) -> str | None:
        return self.effective_str("referent")

class FeatureValue(OwningMembership):
    concept = None
    metatype_id = "KerML::Kernel::FeatureValue"
    metatype_ids = ("KerML::Kernel::FeatureValue",)
    kind_name = "FeatureValue"
    kind_names = ("FeatureValue",)

    @property
    def feature_with_value(self) -> str | None:
        return self.effective_str("feature_with_value")

    @property
    def is_default(self) -> bool | None:
        return self.effective_bool("is_default")

    @property
    def is_initial(self) -> bool | None:
        return self.effective_bool("is_initial")

    @property
    def value(self) -> str | None:
        return self.effective_str("value")

class Flow(Connector, Step):
    concept = None
    metatype_id = "KerML::Kernel::Flow"
    metatype_ids = ("KerML::Kernel::Flow",)
    kind_name = "Flow"
    kind_names = ("Flow",)

    @property
    def flow_end(self) -> str | None:
        return self.effective_str("flow_end")

    @property
    def interaction(self) -> str | None:
        return self.effective_str("interaction")

    @property
    def payload_feature(self) -> str | None:
        return self.effective_str("payload_feature")

    @property
    def payload_type(self) -> str | None:
        return self.effective_str("payload_type")

    @property
    def source_output_feature(self) -> str | None:
        return self.effective_str("source_output_feature")

    @property
    def target_input_feature(self) -> str | None:
        return self.effective_str("target_input_feature")

class Interaction(Association, Behavior):
    concept = None
    metatype_id = "KerML::Kernel::Interaction"
    metatype_ids = ("KerML::Kernel::Interaction",)
    kind_name = "Interaction"
    kind_names = ("Interaction",)

class FlowDefinition(ActionDefinition, Interaction):
    concept = None
    metatype_id = "SysML::Systems::FlowDefinition"
    metatype_ids = ("SysML::Systems::FlowDefinition",)
    kind_name = "FlowDefinition"
    kind_names = ("FlowDefinition",)

    @property
    def flow_end(self) -> str | None:
        return self.effective_str("flow_end")

class FlowEnd(Feature):
    concept = None
    metatype_id = "KerML::Kernel::FlowEnd"
    metatype_ids = ("KerML::Kernel::FlowEnd",)
    kind_name = "FlowEnd"
    kind_names = ("FlowEnd",)

class FlowUsage(ActionUsage, ConnectorAsUsage, Flow):
    concept = None
    metatype_id = "SysML::Systems::FlowUsage"
    metatype_ids = ("SysML::Systems::FlowUsage",)
    kind_name = "FlowUsage"
    kind_names = ("FlowUsage",)

    @property
    def flow_definition(self) -> str | None:
        return self.effective_str("flow_definition")

class LoopActionUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::LoopActionUsage"
    metatype_ids = ("SysML::Systems::LoopActionUsage",)
    kind_name = "LoopActionUsage"
    kind_names = ("LoopActionUsage",)

    @property
    def body_action(self) -> str | None:
        return self.effective_str("body_action")

class ForLoopActionUsage(LoopActionUsage):
    concept = None
    metatype_id = "SysML::Systems::ForLoopActionUsage"
    metatype_ids = ("SysML::Systems::ForLoopActionUsage",)
    kind_name = "ForLoopActionUsage"
    kind_names = ("ForLoopActionUsage",)

    @property
    def loop_variable(self) -> str | None:
        return self.effective_str("loop_variable")

    @property
    def seq_argument(self) -> str | None:
        return self.effective_str("seq_argument")

class ForkNode(ControlNode):
    concept = None
    metatype_id = "SysML::Systems::ForkNode"
    metatype_ids = ("SysML::Systems::ForkNode",)
    kind_name = "ForkNode"
    kind_names = ("ForkNode",)

class RequirementConstraintMembership(FeatureMembership):
    concept = None
    metatype_id = "SysML::Systems::RequirementConstraintMembership"
    metatype_ids = ("SysML::Systems::RequirementConstraintMembership",)
    kind_name = "RequirementConstraintMembership"
    kind_names = ("RequirementConstraintMembership",)

    @property
    def owned_constraint(self) -> str | None:
        return self.effective_str("owned_constraint")

    @property
    def referenced_constraint(self) -> str | None:
        return self.effective_str("referenced_constraint")

class FramedConcernMembership(RequirementConstraintMembership):
    concept = None
    metatype_id = "SysML::Systems::FramedConcernMembership"
    metatype_ids = ("SysML::Systems::FramedConcernMembership",)
    kind_name = "FramedConcernMembership"
    kind_names = ("FramedConcernMembership",)

    @property
    def owned_concern(self) -> str | None:
        return self.effective_str("owned_concern")

    @property
    def referenced_concern(self) -> str | None:
        return self.effective_str("referenced_concern")

class Icon(ElementFacade):
    concept = None
    metatype_id = "ImageMetadata::Icon"
    metatype_ids = ("ImageMetadata::Icon",)
    kind_name = "Icon"
    kind_names = ("Icon",)

    @property
    def full_image(self) -> str | None:
        return self.effective_str("full_image")

    @property
    def small_image(self) -> str | None:
        return self.effective_str("small_image")

class IfActionUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::IfActionUsage"
    metatype_ids = ("SysML::Systems::IfActionUsage",)
    kind_name = "IfActionUsage"
    kind_names = ("IfActionUsage",)

    @property
    def else_action(self) -> str | None:
        return self.effective_str("else_action")

    @property
    def if_argument(self) -> str | None:
        return self.effective_str("if_argument")

    @property
    def then_action(self) -> str | None:
        return self.effective_str("then_action")

class UseCaseUsage(CaseUsage):
    concept = None
    metatype_id = "SysML::Systems::UseCaseUsage"
    metatype_ids = ("SysML::Systems::UseCaseUsage",)
    kind_name = "UseCaseUsage"
    kind_names = ("UseCaseUsage",)

    @property
    def included_use_case(self) -> str | None:
        return self.effective_str("included_use_case")

    @property
    def use_case_definition(self) -> str | None:
        return self.effective_str("use_case_definition")

class IncludeUseCaseUsage(PerformActionUsage, UseCaseUsage):
    concept = None
    metatype_id = "SysML::Systems::IncludeUseCaseUsage"
    metatype_ids = ("SysML::Systems::IncludeUseCaseUsage",)
    kind_name = "IncludeUseCaseUsage"
    kind_names = ("IncludeUseCaseUsage",)

    @property
    def use_case_included(self) -> str | None:
        return self.effective_str("use_case_included")

class IndexExpression(OperatorExpression):
    concept = None
    metatype_id = "KerML::Kernel::IndexExpression"
    metatype_ids = ("KerML::Kernel::IndexExpression",)
    kind_name = "IndexExpression"
    kind_names = ("IndexExpression",)

    @property
    def operator(self) -> str | None:
        return self.effective_str("operator")

class InterfaceDefinition(ConnectionDefinition):
    concept = None
    metatype_id = "SysML::Systems::InterfaceDefinition"
    metatype_ids = ("SysML::Systems::InterfaceDefinition",)
    kind_name = "InterfaceDefinition"
    kind_names = ("InterfaceDefinition",)

    @property
    def interface_end(self) -> str | None:
        return self.effective_str("interface_end")

class InterfaceUsage(ConnectionUsage):
    concept = None
    metatype_id = "SysML::Systems::InterfaceUsage"
    metatype_ids = ("SysML::Systems::InterfaceUsage",)
    kind_name = "InterfaceUsage"
    kind_names = ("InterfaceUsage",)

    @property
    def interface_definition(self) -> str | None:
        return self.effective_str("interface_definition")

class Intersecting(Relationship):
    concept = None
    metatype_id = "KerML::Core::Intersecting"
    metatype_ids = ("KerML::Core::Intersecting",)
    kind_name = "Intersecting"
    kind_names = ("Intersecting",)

    @property
    def intersecting_type(self) -> str | None:
        return self.effective_str("intersecting_type")

    @property
    def type_intersected(self) -> str | None:
        return self.effective_str("type_intersected")

class Issue(ElementFacade):
    concept = None
    metatype_id = "ModelingMetadata::Issue"
    metatype_ids = ("ModelingMetadata::Issue",)
    kind_name = "Issue"
    kind_names = ("Issue",)

    @property
    def text(self) -> str | None:
        return self.effective_str("text")

class JoinNode(ControlNode):
    concept = None
    metatype_id = "SysML::Systems::JoinNode"
    metatype_ids = ("SysML::Systems::JoinNode",)
    kind_name = "JoinNode"
    kind_names = ("JoinNode",)

class Package(Namespace):
    concept = None
    metatype_id = "KerML::Kernel::Package"
    metatype_ids = ("KerML::Kernel::Package",)
    kind_name = "Package"
    kind_names = ("Package",)

    @property
    def filter_condition(self) -> str | None:
        return self.effective_str("filter_condition")

class LibraryPackage(Package):
    concept = None
    metatype_id = "KerML::Kernel::LibraryPackage"
    metatype_ids = ("KerML::Kernel::LibraryPackage",)
    kind_name = "LibraryPackage"
    kind_names = ("LibraryPackage",)

    @property
    def is_standard(self) -> bool | None:
        return self.effective_bool("is_standard")

class LiteralExpression(Expression):
    concept = None
    metatype_id = "KerML::Kernel::LiteralExpression"
    metatype_ids = ("KerML::Kernel::LiteralExpression",)
    kind_name = "LiteralExpression"
    kind_names = ("LiteralExpression",)

class LiteralBoolean(LiteralExpression):
    concept = None
    metatype_id = "KerML::Kernel::LiteralBoolean"
    metatype_ids = ("KerML::Kernel::LiteralBoolean",)
    kind_name = "LiteralBoolean"
    kind_names = ("LiteralBoolean",)

    @property
    def value(self) -> bool | None:
        return self.effective_bool("value")

class LiteralInfinity(LiteralExpression):
    concept = None
    metatype_id = "KerML::Kernel::LiteralInfinity"
    metatype_ids = ("KerML::Kernel::LiteralInfinity",)
    kind_name = "LiteralInfinity"
    kind_names = ("LiteralInfinity",)

class LiteralInteger(LiteralExpression):
    concept = None
    metatype_id = "KerML::Kernel::LiteralInteger"
    metatype_ids = ("KerML::Kernel::LiteralInteger",)
    kind_name = "LiteralInteger"
    kind_names = ("LiteralInteger",)

    @property
    def value(self) -> int | None:
        return self.effective_int("value")

class LiteralRational(LiteralExpression):
    concept = None
    metatype_id = "KerML::Kernel::LiteralRational"
    metatype_ids = ("KerML::Kernel::LiteralRational",)
    kind_name = "LiteralRational"
    kind_names = ("LiteralRational",)

    @property
    def value(self) -> str | None:
        return self.effective_str("value")

class LiteralString(LiteralExpression):
    concept = None
    metatype_id = "KerML::Kernel::LiteralString"
    metatype_ids = ("KerML::Kernel::LiteralString",)
    kind_name = "LiteralString"
    kind_names = ("LiteralString",)

    @property
    def value(self) -> str | None:
        return self.effective_str("value")

class MeasureOfEffectiveness(SemanticMetadata):
    concept = None
    metatype_id = "ParametersOfInterestMetadata::MeasureOfEffectiveness"
    metatype_ids = ("ParametersOfInterestMetadata::MeasureOfEffectiveness",)
    kind_name = "MeasureOfEffectiveness"
    kind_names = ("MeasureOfEffectiveness",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class MeasureOfPerformance(SemanticMetadata):
    concept = None
    metatype_id = "ParametersOfInterestMetadata::MeasureOfPerformance"
    metatype_ids = ("ParametersOfInterestMetadata::MeasureOfPerformance",)
    kind_name = "MeasureOfPerformance"
    kind_names = ("MeasureOfPerformance",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class MembershipImport(Import):
    concept = None
    metatype_id = "KerML::Root::MembershipImport"
    metatype_ids = ("KerML::Root::MembershipImport",)
    kind_name = "MembershipImport"
    kind_names = ("MembershipImport",)

    @property
    def imported_membership(self) -> str | None:
        return self.effective_str("imported_membership")

class MembershipExpose(Expose, MembershipImport):
    concept = None
    metatype_id = "SysML::Systems::MembershipExpose"
    metatype_ids = ("SysML::Systems::MembershipExpose",)
    kind_name = "MembershipExpose"
    kind_names = ("MembershipExpose",)

class MergeNode(ControlNode):
    concept = None
    metatype_id = "SysML::Systems::MergeNode"
    metatype_ids = ("SysML::Systems::MergeNode",)
    kind_name = "MergeNode"
    kind_names = ("MergeNode",)

class Metaclass(Structure):
    concept = None
    metatype_id = "KerML::Kernel::Metaclass"
    metatype_ids = ("KerML::Kernel::Metaclass",)
    kind_name = "Metaclass"
    kind_names = ("Metaclass",)

class MetadataAccessExpression(Expression):
    concept = None
    metatype_id = "KerML::Kernel::MetadataAccessExpression"
    metatype_ids = ("KerML::Kernel::MetadataAccessExpression",)
    kind_name = "MetadataAccessExpression"
    kind_names = ("MetadataAccessExpression",)

    @property
    def referenced_element(self) -> str | None:
        return self.effective_str("referenced_element")

class MetadataDefinition(ItemDefinition, Metaclass):
    concept = None
    metatype_id = "SysML::Systems::MetadataDefinition"
    metatype_ids = ("SysML::Systems::MetadataDefinition",)
    kind_name = "MetadataDefinition"
    kind_names = ("MetadataDefinition",)

class MetadataFeature(AnnotatingElement, Feature):
    concept = None
    metatype_id = "KerML::Kernel::MetadataFeature"
    metatype_ids = ("KerML::Kernel::MetadataFeature",)
    kind_name = "MetadataFeature"
    kind_names = ("MetadataFeature",)

    @property
    def metaclass(self) -> str | None:
        return self.effective_str("metaclass")

class MetadataItem(Metaobject):
    concept = None
    metatype_id = "Metadata::MetadataItem"
    metatype_ids = ("Metadata::MetadataItem",)
    kind_name = "MetadataItem"
    kind_names = ("MetadataItem",)

    @property
    def self(self) -> str | None:
        return self.effective_str("self")

class MetadataUsage(ItemUsage, MetadataFeature):
    concept = None
    metatype_id = "SysML::Systems::MetadataUsage"
    metatype_ids = ("SysML::Systems::MetadataUsage",)
    kind_name = "MetadataUsage"
    kind_names = ("MetadataUsage",)

    @property
    def metadata_definition(self) -> str | None:
        return self.effective_str("metadata_definition")

class MetamodelFeature(ElementFacade):
    concept = None
    metatype_id = None
    metatype_ids = ()
    kind_name = "MetamodelFeature"
    kind_names = ("MetamodelFeature",)

class MulticausationSemanticMetadata(CausationMetadata, SemanticMetadata):
    concept = None
    metatype_id = "CauseAndEffect::MulticausationSemanticMetadata"
    metatype_ids = ("CauseAndEffect::MulticausationSemanticMetadata",)
    kind_name = "MulticausationSemanticMetadata"
    kind_names = ("MulticausationSemanticMetadata",)

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class Multiplicity(Feature):
    concept = None
    metatype_id = "KerML::Core::Multiplicity"
    metatype_ids = ("KerML::Core::Multiplicity",)
    kind_name = "Multiplicity"
    kind_names = ("Multiplicity",)

class MultiplicityRange(Multiplicity):
    concept = None
    metatype_id = "KerML::Kernel::MultiplicityRange"
    metatype_ids = ("KerML::Kernel::MultiplicityRange",)
    kind_name = "MultiplicityRange"
    kind_names = ("MultiplicityRange",)

    @property
    def bound(self) -> str | None:
        return self.effective_str("bound")

    @property
    def lower_bound(self) -> str | None:
        return self.effective_str("lower_bound")

    @property
    def upper_bound(self) -> str | None:
        return self.effective_str("upper_bound")

class NamespaceImport(Import):
    concept = None
    metatype_id = "KerML::Root::NamespaceImport"
    metatype_ids = ("KerML::Root::NamespaceImport",)
    kind_name = "NamespaceImport"
    kind_names = ("NamespaceImport",)

    @property
    def imported_namespace(self) -> str | None:
        return self.effective_str("imported_namespace")

class NamespaceExpose(Expose, NamespaceImport):
    concept = None
    metatype_id = "SysML::Systems::NamespaceExpose"
    metatype_ids = ("SysML::Systems::NamespaceExpose",)
    kind_name = "NamespaceExpose"
    kind_names = ("NamespaceExpose",)

class NullExpression(Expression):
    concept = None
    metatype_id = "KerML::Kernel::NullExpression"
    metatype_ids = ("KerML::Kernel::NullExpression",)
    kind_name = "NullExpression"
    kind_names = ("NullExpression",)

class ObjectiveMembership(FeatureMembership):
    concept = None
    metatype_id = "SysML::Systems::ObjectiveMembership"
    metatype_ids = ("SysML::Systems::ObjectiveMembership",)
    kind_name = "ObjectiveMembership"
    kind_names = ("ObjectiveMembership",)

    @property
    def owned_objective_requirement(self) -> str | None:
        return self.effective_str("owned_objective_requirement")

class OriginalRequirementMetadata(SemanticMetadata):
    concept = None
    metatype_id = "RequirementDerivation::OriginalRequirementMetadata"
    metatype_ids = ("RequirementDerivation::OriginalRequirementMetadata",)
    kind_name = "OriginalRequirementMetadata"
    kind_names = ("OriginalRequirementMetadata",)

    @property
    def base_type(self) -> str | None:
        return self.effective_str("base_type")

class PayloadFeature(Feature):
    concept = None
    metatype_id = "KerML::Kernel::PayloadFeature"
    metatype_ids = ("KerML::Kernel::PayloadFeature",)
    kind_name = "PayloadFeature"
    kind_names = ("PayloadFeature",)

class PortConjugation(Conjugation):
    concept = None
    metatype_id = "SysML::Systems::PortConjugation"
    metatype_ids = ("SysML::Systems::PortConjugation",)
    kind_name = "PortConjugation"
    kind_names = ("PortConjugation",)

    @property
    def conjugated_port_definition(self) -> str | None:
        return self.effective_str("conjugated_port_definition")

    @property
    def original_port_definition(self) -> str | None:
        return self.effective_str("original_port_definition")

class PortUsage(OccurrenceUsage):
    concept = None
    metatype_id = "SysML::Systems::PortUsage"
    metatype_ids = ("SysML::Systems::PortUsage",)
    kind_name = "PortUsage"
    kind_names = ("PortUsage",)

    @property
    def port_definition(self) -> str | None:
        return self.effective_str("port_definition")

class Rationale(ElementFacade):
    concept = None
    metatype_id = "ModelingMetadata::Rationale"
    metatype_ids = ("ModelingMetadata::Rationale",)
    kind_name = "Rationale"
    kind_names = ("Rationale",)

    @property
    def explanation(self) -> str | None:
        return self.effective_str("explanation")

    @property
    def text(self) -> str | None:
        return self.effective_str("text")

class Redefinition(Subsetting):
    concept = None
    metatype_id = "KerML::Core::Redefinition"
    metatype_ids = ("KerML::Core::Redefinition",)
    kind_name = "Redefinition"
    kind_names = ("Redefinition",)

    @property
    def redefined_feature(self) -> str | None:
        return self.effective_str("redefined_feature")

    @property
    def redefining_feature(self) -> str | None:
        return self.effective_str("redefining_feature")

class ReferenceSubsetting(Subsetting):
    concept = None
    metatype_id = "KerML::Core::ReferenceSubsetting"
    metatype_ids = ("KerML::Core::ReferenceSubsetting",)
    kind_name = "ReferenceSubsetting"
    kind_names = ("ReferenceSubsetting",)

    @property
    def referenced_feature(self) -> str | None:
        return self.effective_str("referenced_feature")

    @property
    def referencing_feature(self) -> str | None:
        return self.effective_str("referencing_feature")

class ReferenceUsage(Usage):
    concept = None
    metatype_id = "SysML::Systems::ReferenceUsage"
    metatype_ids = ("SysML::Systems::ReferenceUsage",)
    kind_name = "ReferenceUsage"
    kind_names = ("ReferenceUsage",)

    @property
    def is_reference(self) -> bool | None:
        return self.effective_bool("is_reference")

class Refinement(ElementFacade):
    concept = None
    metatype_id = "ModelingMetadata::Refinement"
    metatype_ids = ("ModelingMetadata::Refinement",)
    kind_name = "Refinement"
    kind_names = ("Refinement",)

    @property
    def annotated_element(self) -> str | None:
        return self.effective_str("annotated_element")

class RenderingDefinition(PartDefinition):
    concept = None
    metatype_id = "SysML::Systems::RenderingDefinition"
    metatype_ids = ("SysML::Systems::RenderingDefinition",)
    kind_name = "RenderingDefinition"
    kind_names = ("RenderingDefinition",)

    @property
    def rendering(self) -> str | None:
        return self.effective_str("rendering")

class RenderingUsage(PartUsage):
    concept = None
    metatype_id = "SysML::Systems::RenderingUsage"
    metatype_ids = ("SysML::Systems::RenderingUsage",)
    kind_name = "RenderingUsage"
    kind_names = ("RenderingUsage",)

    @property
    def rendering_definition(self) -> str | None:
        return self.effective_str("rendering_definition")

class RequirementVerificationMembership(RequirementConstraintMembership):
    concept = None
    metatype_id = "SysML::Systems::RequirementVerificationMembership"
    metatype_ids = ("SysML::Systems::RequirementVerificationMembership",)
    kind_name = "RequirementVerificationMembership"
    kind_names = ("RequirementVerificationMembership",)

    @property
    def owned_requirement(self) -> str | None:
        return self.effective_str("owned_requirement")

    @property
    def verified_requirement(self) -> str | None:
        return self.effective_str("verified_requirement")

class ResultExpressionMembership(FeatureMembership):
    concept = None
    metatype_id = "KerML::Kernel::ResultExpressionMembership"
    metatype_ids = ("KerML::Kernel::ResultExpressionMembership",)
    kind_name = "ResultExpressionMembership"
    kind_names = ("ResultExpressionMembership",)

    @property
    def owned_result_expression(self) -> str | None:
        return self.effective_str("owned_result_expression")

class ReturnParameterMembership(ParameterMembership):
    concept = None
    metatype_id = "KerML::Kernel::ReturnParameterMembership"
    metatype_ids = ("KerML::Kernel::ReturnParameterMembership",)
    kind_name = "ReturnParameterMembership"
    kind_names = ("ReturnParameterMembership",)

class Risk(ElementFacade):
    concept = None
    metatype_id = "RiskMetadata::Risk"
    metatype_ids = ("RiskMetadata::Risk",)
    kind_name = "Risk"
    kind_names = ("Risk",)

    @property
    def cost_risk(self) -> str | None:
        return self.effective_str("cost_risk")

    @property
    def schedule_risk(self) -> str | None:
        return self.effective_str("schedule_risk")

    @property
    def technical_risk(self) -> str | None:
        return self.effective_str("technical_risk")

    @property
    def total_risk(self) -> str | None:
        return self.effective_str("total_risk")

class SatisfyRequirementUsage(AssertConstraintUsage, RequirementUsage):
    concept = None
    metatype_id = "SysML::Systems::SatisfyRequirementUsage"
    metatype_ids = ("SysML::Systems::SatisfyRequirementUsage",)
    kind_name = "SatisfyRequirementUsage"
    kind_names = ("SatisfyRequirementUsage",)

    @property
    def satisfied_requirement(self) -> str | None:
        return self.effective_str("satisfied_requirement")

    @property
    def satisfying_feature(self) -> str | None:
        return self.effective_str("satisfying_feature")

class SelectExpression(OperatorExpression):
    concept = None
    metatype_id = "KerML::Kernel::SelectExpression"
    metatype_ids = ("KerML::Kernel::SelectExpression",)
    kind_name = "SelectExpression"
    kind_names = ("SelectExpression",)

    @property
    def operator(self) -> str | None:
        return self.effective_str("operator")

class SendActionUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::SendActionUsage"
    metatype_ids = ("SysML::Systems::SendActionUsage",)
    kind_name = "SendActionUsage"
    kind_names = ("SendActionUsage",)

    @property
    def payload_argument(self) -> str | None:
        return self.effective_str("payload_argument")

    @property
    def receiver_argument(self) -> str | None:
        return self.effective_str("receiver_argument")

    @property
    def sender_argument(self) -> str | None:
        return self.effective_str("sender_argument")

class StakeholderMembership(ParameterMembership):
    concept = None
    metatype_id = "SysML::Systems::StakeholderMembership"
    metatype_ids = ("SysML::Systems::StakeholderMembership",)
    kind_name = "StakeholderMembership"
    kind_names = ("StakeholderMembership",)

    @property
    def owned_stakeholder_parameter(self) -> str | None:
        return self.effective_str("owned_stakeholder_parameter")

class StateDefinition(ActionDefinition):
    concept = None
    metatype_id = "SysML::Systems::StateDefinition"
    metatype_ids = ("SysML::Systems::StateDefinition",)
    kind_name = "StateDefinition"
    kind_names = ("StateDefinition",)

    @property
    def do_action(self) -> str | None:
        return self.effective_str("do_action")

    @property
    def entry_action(self) -> str | None:
        return self.effective_str("entry_action")

    @property
    def exit_action(self) -> str | None:
        return self.effective_str("exit_action")

    @property
    def is_parallel(self) -> bool | None:
        return self.effective_bool("is_parallel")

    @property
    def state(self) -> str | None:
        return self.effective_str("state")

class StateSubactionMembership(FeatureMembership):
    concept = None
    metatype_id = "SysML::Systems::StateSubactionMembership"
    metatype_ids = ("SysML::Systems::StateSubactionMembership",)
    kind_name = "StateSubactionMembership"
    kind_names = ("StateSubactionMembership",)

    @property
    def action(self) -> str | None:
        return self.effective_str("action")

class StatusInfo(ElementFacade):
    concept = None
    metatype_id = "ModelingMetadata::StatusInfo"
    metatype_ids = ("ModelingMetadata::StatusInfo",)
    kind_name = "StatusInfo"
    kind_names = ("StatusInfo",)

    @property
    def originator(self) -> str | None:
        return self.effective_str("originator")

    @property
    def risk(self) -> str | None:
        return self.effective_str("risk")

    @property
    def status(self) -> str | None:
        return self.effective_str("status")

class Subclassification(Specialization):
    concept = None
    metatype_id = "KerML::Core::Subclassification"
    metatype_ids = ("KerML::Core::Subclassification",)
    kind_name = "Subclassification"
    kind_names = ("Subclassification",)

    @property
    def owning_classifier(self) -> str | None:
        return self.effective_str("owning_classifier")

    @property
    def subclassifier(self) -> str | None:
        return self.effective_str("subclassifier")

    @property
    def superclassifier(self) -> str | None:
        return self.effective_str("superclassifier")

class SubjectMembership(ParameterMembership):
    concept = None
    metatype_id = "SysML::Systems::SubjectMembership"
    metatype_ids = ("SysML::Systems::SubjectMembership",)
    kind_name = "SubjectMembership"
    kind_names = ("SubjectMembership",)

    @property
    def owned_subject_parameter(self) -> str | None:
        return self.effective_str("owned_subject_parameter")

class Succession(Connector):
    concept = None
    metatype_id = "KerML::Kernel::Succession"
    metatype_ids = ("KerML::Kernel::Succession",)
    kind_name = "Succession"
    kind_names = ("Succession",)

class SuccessionAsUsage(ConnectorAsUsage, Succession):
    concept = None
    metatype_id = "SysML::Systems::SuccessionAsUsage"
    metatype_ids = ("SysML::Systems::SuccessionAsUsage",)
    kind_name = "SuccessionAsUsage"
    kind_names = ("SuccessionAsUsage",)

class SuccessionFlow(Flow, Succession):
    concept = None
    metatype_id = "KerML::Kernel::SuccessionFlow"
    metatype_ids = ("KerML::Kernel::SuccessionFlow",)
    kind_name = "SuccessionFlow"
    kind_names = ("SuccessionFlow",)

class SuccessionFlowUsage(FlowUsage, SuccessionFlow):
    concept = None
    metatype_id = "SysML::Systems::SuccessionFlowUsage"
    metatype_ids = ("SysML::Systems::SuccessionFlowUsage",)
    kind_name = "SuccessionFlowUsage"
    kind_names = ("SuccessionFlowUsage",)

class TerminateActionUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::TerminateActionUsage"
    metatype_ids = ("SysML::Systems::TerminateActionUsage",)
    kind_name = "TerminateActionUsage"
    kind_names = ("TerminateActionUsage",)

    @property
    def terminated_occurrence_argument(self) -> str | None:
        return self.effective_str("terminated_occurrence_argument")

class TextualRepresentation(AnnotatingElement):
    concept = None
    metatype_id = "KerML::Root::TextualRepresentation"
    metatype_ids = ("KerML::Root::TextualRepresentation",)
    kind_name = "TextualRepresentation"
    kind_names = ("TextualRepresentation",)

    @property
    def body(self) -> str | None:
        return self.effective_str("body")

    @property
    def language(self) -> str | None:
        return self.effective_str("language")

    @property
    def represented_element(self) -> str | None:
        return self.effective_str("represented_element")

class ToolExecution(ElementFacade):
    concept = None
    metatype_id = "AnalysisTooling::ToolExecution"
    metatype_ids = ("AnalysisTooling::ToolExecution",)
    kind_name = "ToolExecution"
    kind_names = ("ToolExecution",)

    @property
    def tool_name(self) -> str | None:
        return self.effective_str("tool_name")

    @property
    def uri(self) -> str | None:
        return self.effective_str("uri")

class ToolVariable(ElementFacade):
    concept = None
    metatype_id = "AnalysisTooling::ToolVariable"
    metatype_ids = ("AnalysisTooling::ToolVariable",)
    kind_name = "ToolVariable"
    kind_names = ("ToolVariable",)

    @property
    def name(self) -> str | None:
        return self.effective_str("name")

class TransitionFeatureMembership(FeatureMembership):
    concept = None
    metatype_id = "SysML::Systems::TransitionFeatureMembership"
    metatype_ids = ("SysML::Systems::TransitionFeatureMembership",)
    kind_name = "TransitionFeatureMembership"
    kind_names = ("TransitionFeatureMembership",)

    @property
    def transition_feature(self) -> str | None:
        return self.effective_str("transition_feature")

class TransitionUsage(ActionUsage):
    concept = None
    metatype_id = "SysML::Systems::TransitionUsage"
    metatype_ids = ("SysML::Systems::TransitionUsage",)
    kind_name = "TransitionUsage"
    kind_names = ("TransitionUsage",)

    @property
    def effect_action(self) -> str | None:
        return self.effective_str("effect_action")

    @property
    def guard_expression(self) -> str | None:
        return self.effective_str("guard_expression")

    @property
    def source(self) -> str | None:
        return self.effective_str("source")

    @property
    def succession(self) -> str | None:
        return self.effective_str("succession")

    @property
    def target(self) -> str | None:
        return self.effective_str("target")

    @property
    def trigger_action(self) -> str | None:
        return self.effective_str("trigger_action")

class TriggerInvocationExpression(InvocationExpression):
    concept = None
    metatype_id = "SysML::Systems::TriggerInvocationExpression"
    metatype_ids = ("SysML::Systems::TriggerInvocationExpression",)
    kind_name = "TriggerInvocationExpression"
    kind_names = ("TriggerInvocationExpression",)

class TypeFeaturing(Relationship):
    concept = None
    metatype_id = "KerML::Core::TypeFeaturing"
    metatype_ids = ("KerML::Core::TypeFeaturing",)
    kind_name = "TypeFeaturing"
    kind_names = ("TypeFeaturing",)

    @property
    def feature_of_type(self) -> str | None:
        return self.effective_str("feature_of_type")

    @property
    def featuring_type(self) -> str | None:
        return self.effective_str("featuring_type")

    @property
    def owning_feature_of_type(self) -> str | None:
        return self.effective_str("owning_feature_of_type")

class Unioning(Relationship):
    concept = None
    metatype_id = "KerML::Core::Unioning"
    metatype_ids = ("KerML::Core::Unioning",)
    kind_name = "Unioning"
    kind_names = ("Unioning",)

    @property
    def type_unioned(self) -> str | None:
        return self.effective_str("type_unioned")

    @property
    def unioning_type(self) -> str | None:
        return self.effective_str("unioning_type")

class UseCaseDefinition(CaseDefinition):
    concept = None
    metatype_id = "SysML::Systems::UseCaseDefinition"
    metatype_ids = ("SysML::Systems::UseCaseDefinition",)
    kind_name = "UseCaseDefinition"
    kind_names = ("UseCaseDefinition",)

    @property
    def included_use_case(self) -> str | None:
        return self.effective_str("included_use_case")

class VariantMembership(OwningMembership):
    concept = None
    metatype_id = "SysML::Systems::VariantMembership"
    metatype_ids = ("SysML::Systems::VariantMembership",)
    kind_name = "VariantMembership"
    kind_names = ("VariantMembership",)

    @property
    def owned_variant_usage(self) -> str | None:
        return self.effective_str("owned_variant_usage")

class VerificationCaseDefinition(CaseDefinition):
    concept = None
    metatype_id = "SysML::Systems::VerificationCaseDefinition"
    metatype_ids = ("SysML::Systems::VerificationCaseDefinition",)
    kind_name = "VerificationCaseDefinition"
    kind_names = ("VerificationCaseDefinition",)

    @property
    def verified_requirement(self) -> str | None:
        return self.effective_str("verified_requirement")

class VerificationCaseUsage(CaseUsage):
    concept = None
    metatype_id = "SysML::Systems::VerificationCaseUsage"
    metatype_ids = ("SysML::Systems::VerificationCaseUsage",)
    kind_name = "VerificationCaseUsage"
    kind_names = ("VerificationCaseUsage",)

    @property
    def verification_case_definition(self) -> str | None:
        return self.effective_str("verification_case_definition")

    @property
    def verified_requirement(self) -> str | None:
        return self.effective_str("verified_requirement")

class VerificationMethod(ElementFacade):
    concept = None
    metatype_id = "VerificationCases::VerificationMethod"
    metatype_ids = ("VerificationCases::VerificationMethod",)
    kind_name = "VerificationMethod"
    kind_names = ("VerificationMethod",)

class ViewDefinition(PartDefinition):
    concept = None
    metatype_id = "SysML::Systems::ViewDefinition"
    metatype_ids = ("SysML::Systems::ViewDefinition",)
    kind_name = "ViewDefinition"
    kind_names = ("ViewDefinition",)

    @property
    def satisfied_viewpoint(self) -> str | None:
        return self.effective_str("satisfied_viewpoint")

    @property
    def view(self) -> str | None:
        return self.effective_str("view")

    @property
    def view_condition(self) -> str | None:
        return self.effective_str("view_condition")

    @property
    def view_rendering(self) -> str | None:
        return self.effective_str("view_rendering")

class ViewRenderingMembership(FeatureMembership):
    concept = None
    metatype_id = "SysML::Systems::ViewRenderingMembership"
    metatype_ids = ("SysML::Systems::ViewRenderingMembership",)
    kind_name = "ViewRenderingMembership"
    kind_names = ("ViewRenderingMembership",)

    @property
    def owned_rendering(self) -> str | None:
        return self.effective_str("owned_rendering")

    @property
    def referenced_rendering(self) -> str | None:
        return self.effective_str("referenced_rendering")

class ViewUsage(PartUsage):
    concept = None
    metatype_id = "SysML::Systems::ViewUsage"
    metatype_ids = ("SysML::Systems::ViewUsage",)
    kind_name = "ViewUsage"
    kind_names = ("ViewUsage",)

    @property
    def exposed_element(self) -> str | None:
        return self.effective_str("exposed_element")

    @property
    def satisfied_viewpoint(self) -> str | None:
        return self.effective_str("satisfied_viewpoint")

    @property
    def view_condition(self) -> str | None:
        return self.effective_str("view_condition")

    @property
    def view_definition(self) -> str | None:
        return self.effective_str("view_definition")

    @property
    def view_rendering(self) -> str | None:
        return self.effective_str("view_rendering")

class ViewpointDefinition(RequirementDefinition):
    concept = None
    metatype_id = "SysML::Systems::ViewpointDefinition"
    metatype_ids = ("SysML::Systems::ViewpointDefinition",)
    kind_name = "ViewpointDefinition"
    kind_names = ("ViewpointDefinition",)

    @property
    def viewpoint_stakeholder(self) -> str | None:
        return self.effective_str("viewpoint_stakeholder")

class ViewpointUsage(RequirementUsage):
    concept = None
    metatype_id = "SysML::Systems::ViewpointUsage"
    metatype_ids = ("SysML::Systems::ViewpointUsage",)
    kind_name = "ViewpointUsage"
    kind_names = ("ViewpointUsage",)

    @property
    def viewpoint_definition(self) -> str | None:
        return self.effective_str("viewpoint_definition")

    @property
    def viewpoint_stakeholder(self) -> str | None:
        return self.effective_str("viewpoint_stakeholder")

class WhileLoopActionUsage(LoopActionUsage):
    concept = None
    metatype_id = "SysML::Systems::WhileLoopActionUsage"
    metatype_ids = ("SysML::Systems::WhileLoopActionUsage",)
    kind_name = "WhileLoopActionUsage"
    kind_names = ("WhileLoopActionUsage",)

    @property
    def until_argument(self) -> str | None:
        return self.effective_str("until_argument")

    @property
    def while_argument(self) -> str | None:
        return self.effective_str("while_argument")

METAMODEL_CLASSES = (
    Element,
    Namespace,
    Type,
    Feature,
    Usage,
    OccurrenceUsage,
    Step,
    ActionUsage,
    AcceptActionUsage,
    Classifier,
    Class,
    Behavior,
    Definition,
    OccurrenceDefinition,
    ActionDefinition,
    Relationship,
    Membership,
    OwningMembership,
    FeatureMembership,
    ParameterMembership,
    ActorMembership,
    Association,
    Structure,
    AssociationStructure,
    ItemDefinition,
    PartDefinition,
    ConnectionDefinition,
    AllocationDefinition,
    Connector,
    ConnectorAsUsage,
    ItemUsage,
    PartUsage,
    ConnectionUsage,
    AllocationUsage,
    Function,
    CalculationDefinition,
    CaseDefinition,
    AnalysisCaseDefinition,
    Expression,
    CalculationUsage,
    CaseUsage,
    AnalysisCaseUsage,
    AnnotatingElement,
    Annotation,
    BooleanExpression,
    ConstraintUsage,
    Invariant,
    AssertConstraintUsage,
    AssignmentActionUsage,
    DataType,
    AttributeDefinition,
    AttributeUsage,
    BindingConnector,
    BindingConnectorAsUsage,
    CausationMetadata,
    Metaobject,
    SemanticMetadata,
    CausationSemanticMetadadata,
    CauseMetadata,
    InstantiationExpression,
    InvocationExpression,
    OperatorExpression,
    CollectExpression,
    Comment,
    Predicate,
    ConstraintDefinition,
    RequirementDefinition,
    ConcernDefinition,
    RequirementUsage,
    ConcernUsage,
    PortDefinition,
    ConjugatedPortDefinition,
    Specialization,
    FeatureTyping,
    ConjugatedPortTyping,
    Conjugation,
    ConstructorExpression,
    ControlNode,
    Subsetting,
    CrossSubsetting,
    DecisionNode,
    Dependency,
    DerivationMetadata,
    DerivedRequirementMetadata,
    Differencing,
    Disjoining,
    Documentation,
    EffectMetadata,
    ElementFilterMembership,
    EndFeatureMembership,
    EnumerationDefinition,
    EnumerationUsage,
    EventOccurrenceUsage,
    PerformActionUsage,
    StateUsage,
    ExhibitStateUsage,
    Import,
    Expose,
    FeatureChainExpression,
    FeatureChaining,
    FeatureInverting,
    FeatureReferenceExpression,
    FeatureValue,
    Flow,
    Interaction,
    FlowDefinition,
    FlowEnd,
    FlowUsage,
    LoopActionUsage,
    ForLoopActionUsage,
    ForkNode,
    RequirementConstraintMembership,
    FramedConcernMembership,
    Icon,
    IfActionUsage,
    UseCaseUsage,
    IncludeUseCaseUsage,
    IndexExpression,
    InterfaceDefinition,
    InterfaceUsage,
    Intersecting,
    Issue,
    JoinNode,
    Package,
    LibraryPackage,
    LiteralExpression,
    LiteralBoolean,
    LiteralInfinity,
    LiteralInteger,
    LiteralRational,
    LiteralString,
    MeasureOfEffectiveness,
    MeasureOfPerformance,
    MembershipImport,
    MembershipExpose,
    MergeNode,
    Metaclass,
    MetadataAccessExpression,
    MetadataDefinition,
    MetadataFeature,
    MetadataItem,
    MetadataUsage,
    MetamodelFeature,
    MulticausationSemanticMetadata,
    Multiplicity,
    MultiplicityRange,
    NamespaceImport,
    NamespaceExpose,
    NullExpression,
    ObjectiveMembership,
    OriginalRequirementMetadata,
    PayloadFeature,
    PortConjugation,
    PortUsage,
    Rationale,
    Redefinition,
    ReferenceSubsetting,
    ReferenceUsage,
    Refinement,
    RenderingDefinition,
    RenderingUsage,
    RequirementVerificationMembership,
    ResultExpressionMembership,
    ReturnParameterMembership,
    Risk,
    SatisfyRequirementUsage,
    SelectExpression,
    SendActionUsage,
    StakeholderMembership,
    StateDefinition,
    StateSubactionMembership,
    StatusInfo,
    Subclassification,
    SubjectMembership,
    Succession,
    SuccessionAsUsage,
    SuccessionFlow,
    SuccessionFlowUsage,
    TerminateActionUsage,
    TextualRepresentation,
    ToolExecution,
    ToolVariable,
    TransitionFeatureMembership,
    TransitionUsage,
    TriggerInvocationExpression,
    TypeFeaturing,
    Unioning,
    UseCaseDefinition,
    VariantMembership,
    VerificationCaseDefinition,
    VerificationCaseUsage,
    VerificationMethod,
    ViewDefinition,
    ViewRenderingMembership,
    ViewUsage,
    ViewpointDefinition,
    ViewpointUsage,
    WhileLoopActionUsage,
)

METAMODEL_CLASS_BY_METATYPE = {
    "KerML::Root::Element": Element,
    "KerML::Root::Namespace": Namespace,
    "KerML::Core::Type": Type,
    "KerML::Core::Feature": Feature,
    "SysML::Systems::Usage": Usage,
    "SysML::Systems::OccurrenceUsage": OccurrenceUsage,
    "KerML::Kernel::Step": Step,
    "SysML::Systems::ActionUsage": ActionUsage,
    "SysML::Systems::AcceptActionUsage": AcceptActionUsage,
    "KerML::Core::Classifier": Classifier,
    "KerML::Kernel::Class": Class,
    "KerML::Kernel::Behavior": Behavior,
    "SysML::Systems::Definition": Definition,
    "SysML::Systems::OccurrenceDefinition": OccurrenceDefinition,
    "SysML::Systems::ActionDefinition": ActionDefinition,
    "KerML::Root::Relationship": Relationship,
    "KerML::Root::Membership": Membership,
    "KerML::Root::OwningMembership": OwningMembership,
    "KerML::Core::FeatureMembership": FeatureMembership,
    "KerML::Kernel::ParameterMembership": ParameterMembership,
    "SysML::Systems::ActorMembership": ActorMembership,
    "KerML::Kernel::Association": Association,
    "KerML::Kernel::Structure": Structure,
    "KerML::Kernel::AssociationStructure": AssociationStructure,
    "SysML::Systems::ItemDefinition": ItemDefinition,
    "SysML::Systems::PartDefinition": PartDefinition,
    "SysML::Systems::ConnectionDefinition": ConnectionDefinition,
    "SysML::Systems::AllocationDefinition": AllocationDefinition,
    "KerML::Kernel::Connector": Connector,
    "SysML::Systems::ConnectorAsUsage": ConnectorAsUsage,
    "SysML::Systems::ItemUsage": ItemUsage,
    "SysML::Systems::PartUsage": PartUsage,
    "SysML::Systems::ConnectionUsage": ConnectionUsage,
    "SysML::Systems::AllocationUsage": AllocationUsage,
    "KerML::Kernel::Function": Function,
    "SysML::Systems::CalculationDefinition": CalculationDefinition,
    "SysML::Systems::CaseDefinition": CaseDefinition,
    "SysML::Systems::AnalysisCaseDefinition": AnalysisCaseDefinition,
    "KerML::Kernel::Expression": Expression,
    "SysML::Systems::CalculationUsage": CalculationUsage,
    "SysML::Systems::CaseUsage": CaseUsage,
    "SysML::Systems::AnalysisCaseUsage": AnalysisCaseUsage,
    "KerML::Root::AnnotatingElement": AnnotatingElement,
    "KerML::Root::Annotation": Annotation,
    "KerML::Kernel::BooleanExpression": BooleanExpression,
    "SysML::Systems::ConstraintUsage": ConstraintUsage,
    "KerML::Kernel::Invariant": Invariant,
    "SysML::Systems::AssertConstraintUsage": AssertConstraintUsage,
    "SysML::Systems::AssignmentActionUsage": AssignmentActionUsage,
    "KerML::Kernel::DataType": DataType,
    "SysML::Systems::AttributeDefinition": AttributeDefinition,
    "SysML::Systems::AttributeUsage": AttributeUsage,
    "KerML::Kernel::BindingConnector": BindingConnector,
    "SysML::Systems::BindingConnectorAsUsage": BindingConnectorAsUsage,
    "CauseAndEffect::CausationMetadata": CausationMetadata,
    "Metaobjects::Metaobject": Metaobject,
    "Metaobjects::SemanticMetadata": SemanticMetadata,
    "CauseAndEffect::CausationSemanticMetadadata": CausationSemanticMetadadata,
    "CauseAndEffect::CauseMetadata": CauseMetadata,
    "KerML::Kernel::InstantiationExpression": InstantiationExpression,
    "KerML::Kernel::InvocationExpression": InvocationExpression,
    "KerML::Kernel::OperatorExpression": OperatorExpression,
    "KerML::Kernel::CollectExpression": CollectExpression,
    "KerML::Root::Comment": Comment,
    "KerML::Kernel::Predicate": Predicate,
    "SysML::Systems::ConstraintDefinition": ConstraintDefinition,
    "SysML::Systems::RequirementDefinition": RequirementDefinition,
    "SysML::Systems::ConcernDefinition": ConcernDefinition,
    "SysML::Systems::RequirementUsage": RequirementUsage,
    "SysML::Systems::ConcernUsage": ConcernUsage,
    "SysML::Systems::PortDefinition": PortDefinition,
    "SysML::Systems::ConjugatedPortDefinition": ConjugatedPortDefinition,
    "KerML::Core::Specialization": Specialization,
    "KerML::Core::FeatureTyping": FeatureTyping,
    "SysML::Systems::ConjugatedPortTyping": ConjugatedPortTyping,
    "KerML::Core::Conjugation": Conjugation,
    "KerML::Kernel::ConstructorExpression": ConstructorExpression,
    "SysML::Systems::ControlNode": ControlNode,
    "KerML::Core::Subsetting": Subsetting,
    "KerML::Core::CrossSubsetting": CrossSubsetting,
    "SysML::Systems::DecisionNode": DecisionNode,
    "KerML::Root::Dependency": Dependency,
    "RequirementDerivation::DerivationMetadata": DerivationMetadata,
    "RequirementDerivation::DerivedRequirementMetadata": DerivedRequirementMetadata,
    "KerML::Core::Differencing": Differencing,
    "KerML::Core::Disjoining": Disjoining,
    "KerML::Root::Documentation": Documentation,
    "CauseAndEffect::EffectMetadata": EffectMetadata,
    "KerML::Kernel::ElementFilterMembership": ElementFilterMembership,
    "KerML::Core::EndFeatureMembership": EndFeatureMembership,
    "SysML::Systems::EnumerationDefinition": EnumerationDefinition,
    "SysML::Systems::EnumerationUsage": EnumerationUsage,
    "SysML::Systems::EventOccurrenceUsage": EventOccurrenceUsage,
    "SysML::Systems::PerformActionUsage": PerformActionUsage,
    "SysML::Systems::StateUsage": StateUsage,
    "SysML::Systems::ExhibitStateUsage": ExhibitStateUsage,
    "KerML::Root::Import": Import,
    "SysML::Systems::Expose": Expose,
    "KerML::Kernel::FeatureChainExpression": FeatureChainExpression,
    "KerML::Core::FeatureChaining": FeatureChaining,
    "KerML::Core::FeatureInverting": FeatureInverting,
    "KerML::Kernel::FeatureReferenceExpression": FeatureReferenceExpression,
    "KerML::Kernel::FeatureValue": FeatureValue,
    "KerML::Kernel::Flow": Flow,
    "KerML::Kernel::Interaction": Interaction,
    "SysML::Systems::FlowDefinition": FlowDefinition,
    "KerML::Kernel::FlowEnd": FlowEnd,
    "SysML::Systems::FlowUsage": FlowUsage,
    "SysML::Systems::LoopActionUsage": LoopActionUsage,
    "SysML::Systems::ForLoopActionUsage": ForLoopActionUsage,
    "SysML::Systems::ForkNode": ForkNode,
    "SysML::Systems::RequirementConstraintMembership": RequirementConstraintMembership,
    "SysML::Systems::FramedConcernMembership": FramedConcernMembership,
    "ImageMetadata::Icon": Icon,
    "SysML::Systems::IfActionUsage": IfActionUsage,
    "SysML::Systems::UseCaseUsage": UseCaseUsage,
    "SysML::Systems::IncludeUseCaseUsage": IncludeUseCaseUsage,
    "KerML::Kernel::IndexExpression": IndexExpression,
    "SysML::Systems::InterfaceDefinition": InterfaceDefinition,
    "SysML::Systems::InterfaceUsage": InterfaceUsage,
    "KerML::Core::Intersecting": Intersecting,
    "ModelingMetadata::Issue": Issue,
    "SysML::Systems::JoinNode": JoinNode,
    "KerML::Kernel::Package": Package,
    "KerML::Kernel::LibraryPackage": LibraryPackage,
    "KerML::Kernel::LiteralExpression": LiteralExpression,
    "KerML::Kernel::LiteralBoolean": LiteralBoolean,
    "KerML::Kernel::LiteralInfinity": LiteralInfinity,
    "KerML::Kernel::LiteralInteger": LiteralInteger,
    "KerML::Kernel::LiteralRational": LiteralRational,
    "KerML::Kernel::LiteralString": LiteralString,
    "ParametersOfInterestMetadata::MeasureOfEffectiveness": MeasureOfEffectiveness,
    "ParametersOfInterestMetadata::MeasureOfPerformance": MeasureOfPerformance,
    "KerML::Root::MembershipImport": MembershipImport,
    "SysML::Systems::MembershipExpose": MembershipExpose,
    "SysML::Systems::MergeNode": MergeNode,
    "KerML::Kernel::Metaclass": Metaclass,
    "KerML::Kernel::MetadataAccessExpression": MetadataAccessExpression,
    "SysML::Systems::MetadataDefinition": MetadataDefinition,
    "KerML::Kernel::MetadataFeature": MetadataFeature,
    "Metadata::MetadataItem": MetadataItem,
    "SysML::Systems::MetadataUsage": MetadataUsage,
    "CauseAndEffect::MulticausationSemanticMetadata": MulticausationSemanticMetadata,
    "KerML::Core::Multiplicity": Multiplicity,
    "KerML::Kernel::MultiplicityRange": MultiplicityRange,
    "KerML::Root::NamespaceImport": NamespaceImport,
    "SysML::Systems::NamespaceExpose": NamespaceExpose,
    "KerML::Kernel::NullExpression": NullExpression,
    "SysML::Systems::ObjectiveMembership": ObjectiveMembership,
    "RequirementDerivation::OriginalRequirementMetadata": OriginalRequirementMetadata,
    "KerML::Kernel::PayloadFeature": PayloadFeature,
    "SysML::Systems::PortConjugation": PortConjugation,
    "SysML::Systems::PortUsage": PortUsage,
    "ModelingMetadata::Rationale": Rationale,
    "KerML::Core::Redefinition": Redefinition,
    "KerML::Core::ReferenceSubsetting": ReferenceSubsetting,
    "SysML::Systems::ReferenceUsage": ReferenceUsage,
    "ModelingMetadata::Refinement": Refinement,
    "SysML::Systems::RenderingDefinition": RenderingDefinition,
    "SysML::Systems::RenderingUsage": RenderingUsage,
    "SysML::Systems::RequirementVerificationMembership": RequirementVerificationMembership,
    "KerML::Kernel::ResultExpressionMembership": ResultExpressionMembership,
    "KerML::Kernel::ReturnParameterMembership": ReturnParameterMembership,
    "RiskMetadata::Risk": Risk,
    "SysML::Systems::SatisfyRequirementUsage": SatisfyRequirementUsage,
    "KerML::Kernel::SelectExpression": SelectExpression,
    "SysML::Systems::SendActionUsage": SendActionUsage,
    "SysML::Systems::StakeholderMembership": StakeholderMembership,
    "SysML::Systems::StateDefinition": StateDefinition,
    "SysML::Systems::StateSubactionMembership": StateSubactionMembership,
    "ModelingMetadata::StatusInfo": StatusInfo,
    "KerML::Core::Subclassification": Subclassification,
    "SysML::Systems::SubjectMembership": SubjectMembership,
    "KerML::Kernel::Succession": Succession,
    "SysML::Systems::SuccessionAsUsage": SuccessionAsUsage,
    "KerML::Kernel::SuccessionFlow": SuccessionFlow,
    "SysML::Systems::SuccessionFlowUsage": SuccessionFlowUsage,
    "SysML::Systems::TerminateActionUsage": TerminateActionUsage,
    "KerML::Root::TextualRepresentation": TextualRepresentation,
    "AnalysisTooling::ToolExecution": ToolExecution,
    "AnalysisTooling::ToolVariable": ToolVariable,
    "SysML::Systems::TransitionFeatureMembership": TransitionFeatureMembership,
    "SysML::Systems::TransitionUsage": TransitionUsage,
    "SysML::Systems::TriggerInvocationExpression": TriggerInvocationExpression,
    "KerML::Core::TypeFeaturing": TypeFeaturing,
    "KerML::Core::Unioning": Unioning,
    "SysML::Systems::UseCaseDefinition": UseCaseDefinition,
    "SysML::Systems::VariantMembership": VariantMembership,
    "SysML::Systems::VerificationCaseDefinition": VerificationCaseDefinition,
    "SysML::Systems::VerificationCaseUsage": VerificationCaseUsage,
    "VerificationCases::VerificationMethod": VerificationMethod,
    "SysML::Systems::ViewDefinition": ViewDefinition,
    "SysML::Systems::ViewRenderingMembership": ViewRenderingMembership,
    "SysML::Systems::ViewUsage": ViewUsage,
    "SysML::Systems::ViewpointDefinition": ViewpointDefinition,
    "SysML::Systems::ViewpointUsage": ViewpointUsage,
    "SysML::Systems::WhileLoopActionUsage": WhileLoopActionUsage,
}

METAMODEL_CLASS_BY_KIND = {
    "Element": Element,
    "Namespace": Namespace,
    "Type": Type,
    "Feature": Feature,
    "Usage": Usage,
    "OccurrenceUsage": OccurrenceUsage,
    "Step": Step,
    "ActionUsage": ActionUsage,
    "AcceptActionUsage": AcceptActionUsage,
    "Classifier": Classifier,
    "Class": Class,
    "Behavior": Behavior,
    "Definition": Definition,
    "OccurrenceDefinition": OccurrenceDefinition,
    "ActionDefinition": ActionDefinition,
    "Relationship": Relationship,
    "Membership": Membership,
    "OwningMembership": OwningMembership,
    "FeatureMembership": FeatureMembership,
    "ParameterMembership": ParameterMembership,
    "ActorMembership": ActorMembership,
    "Association": Association,
    "Structure": Structure,
    "AssociationStructure": AssociationStructure,
    "ItemDefinition": ItemDefinition,
    "PartDefinition": PartDefinition,
    "ConnectionDefinition": ConnectionDefinition,
    "AllocationDefinition": AllocationDefinition,
    "Connector": Connector,
    "ConnectorAsUsage": ConnectorAsUsage,
    "ItemUsage": ItemUsage,
    "PartUsage": PartUsage,
    "ConnectionUsage": ConnectionUsage,
    "AllocationUsage": AllocationUsage,
    "Function": Function,
    "CalculationDefinition": CalculationDefinition,
    "CaseDefinition": CaseDefinition,
    "AnalysisCaseDefinition": AnalysisCaseDefinition,
    "Expression": Expression,
    "CalculationUsage": CalculationUsage,
    "CaseUsage": CaseUsage,
    "AnalysisCaseUsage": AnalysisCaseUsage,
    "AnnotatingElement": AnnotatingElement,
    "Annotation": Annotation,
    "BooleanExpression": BooleanExpression,
    "ConstraintUsage": ConstraintUsage,
    "Invariant": Invariant,
    "AssertConstraintUsage": AssertConstraintUsage,
    "AssignmentActionUsage": AssignmentActionUsage,
    "DataType": DataType,
    "AttributeDefinition": AttributeDefinition,
    "AttributeUsage": AttributeUsage,
    "BindingConnector": BindingConnector,
    "BindingConnectorAsUsage": BindingConnectorAsUsage,
    "CausationMetadata": CausationMetadata,
    "Metaobject": Metaobject,
    "SemanticMetadata": SemanticMetadata,
    "CausationSemanticMetadadata": CausationSemanticMetadadata,
    "CauseMetadata": CauseMetadata,
    "InstantiationExpression": InstantiationExpression,
    "InvocationExpression": InvocationExpression,
    "OperatorExpression": OperatorExpression,
    "CollectExpression": CollectExpression,
    "Comment": Comment,
    "Predicate": Predicate,
    "ConstraintDefinition": ConstraintDefinition,
    "RequirementDefinition": RequirementDefinition,
    "ConcernDefinition": ConcernDefinition,
    "RequirementUsage": RequirementUsage,
    "ConcernUsage": ConcernUsage,
    "PortDefinition": PortDefinition,
    "ConjugatedPortDefinition": ConjugatedPortDefinition,
    "Specialization": Specialization,
    "FeatureTyping": FeatureTyping,
    "ConjugatedPortTyping": ConjugatedPortTyping,
    "Conjugation": Conjugation,
    "ConstructorExpression": ConstructorExpression,
    "ControlNode": ControlNode,
    "Subsetting": Subsetting,
    "CrossSubsetting": CrossSubsetting,
    "DecisionNode": DecisionNode,
    "Dependency": Dependency,
    "DerivationMetadata": DerivationMetadata,
    "DerivedRequirementMetadata": DerivedRequirementMetadata,
    "Differencing": Differencing,
    "Disjoining": Disjoining,
    "Documentation": Documentation,
    "EffectMetadata": EffectMetadata,
    "ElementFilterMembership": ElementFilterMembership,
    "EndFeatureMembership": EndFeatureMembership,
    "EnumerationDefinition": EnumerationDefinition,
    "EnumerationUsage": EnumerationUsage,
    "EventOccurrenceUsage": EventOccurrenceUsage,
    "PerformActionUsage": PerformActionUsage,
    "StateUsage": StateUsage,
    "ExhibitStateUsage": ExhibitStateUsage,
    "Import": Import,
    "Expose": Expose,
    "FeatureChainExpression": FeatureChainExpression,
    "FeatureChaining": FeatureChaining,
    "FeatureInverting": FeatureInverting,
    "FeatureReferenceExpression": FeatureReferenceExpression,
    "FeatureValue": FeatureValue,
    "Flow": Flow,
    "Interaction": Interaction,
    "FlowDefinition": FlowDefinition,
    "FlowEnd": FlowEnd,
    "FlowUsage": FlowUsage,
    "LoopActionUsage": LoopActionUsage,
    "ForLoopActionUsage": ForLoopActionUsage,
    "ForkNode": ForkNode,
    "RequirementConstraintMembership": RequirementConstraintMembership,
    "FramedConcernMembership": FramedConcernMembership,
    "Icon": Icon,
    "IfActionUsage": IfActionUsage,
    "UseCaseUsage": UseCaseUsage,
    "IncludeUseCaseUsage": IncludeUseCaseUsage,
    "IndexExpression": IndexExpression,
    "InterfaceDefinition": InterfaceDefinition,
    "InterfaceUsage": InterfaceUsage,
    "Intersecting": Intersecting,
    "Issue": Issue,
    "JoinNode": JoinNode,
    "Package": Package,
    "LibraryPackage": LibraryPackage,
    "LiteralExpression": LiteralExpression,
    "LiteralBoolean": LiteralBoolean,
    "LiteralInfinity": LiteralInfinity,
    "LiteralInteger": LiteralInteger,
    "LiteralRational": LiteralRational,
    "LiteralString": LiteralString,
    "MeasureOfEffectiveness": MeasureOfEffectiveness,
    "MeasureOfPerformance": MeasureOfPerformance,
    "MembershipImport": MembershipImport,
    "MembershipExpose": MembershipExpose,
    "MergeNode": MergeNode,
    "Metaclass": Metaclass,
    "MetadataAccessExpression": MetadataAccessExpression,
    "MetadataDefinition": MetadataDefinition,
    "MetadataFeature": MetadataFeature,
    "MetadataItem": MetadataItem,
    "MetadataUsage": MetadataUsage,
    "MetamodelFeature": MetamodelFeature,
    "MulticausationSemanticMetadata": MulticausationSemanticMetadata,
    "Multiplicity": Multiplicity,
    "MultiplicityRange": MultiplicityRange,
    "NamespaceImport": NamespaceImport,
    "NamespaceExpose": NamespaceExpose,
    "NullExpression": NullExpression,
    "ObjectiveMembership": ObjectiveMembership,
    "OriginalRequirementMetadata": OriginalRequirementMetadata,
    "PayloadFeature": PayloadFeature,
    "PortConjugation": PortConjugation,
    "PortUsage": PortUsage,
    "Rationale": Rationale,
    "Redefinition": Redefinition,
    "ReferenceSubsetting": ReferenceSubsetting,
    "ReferenceUsage": ReferenceUsage,
    "Refinement": Refinement,
    "RenderingDefinition": RenderingDefinition,
    "RenderingUsage": RenderingUsage,
    "RequirementVerificationMembership": RequirementVerificationMembership,
    "ResultExpressionMembership": ResultExpressionMembership,
    "ReturnParameterMembership": ReturnParameterMembership,
    "Risk": Risk,
    "SatisfyRequirementUsage": SatisfyRequirementUsage,
    "SelectExpression": SelectExpression,
    "SendActionUsage": SendActionUsage,
    "StakeholderMembership": StakeholderMembership,
    "StateDefinition": StateDefinition,
    "StateSubactionMembership": StateSubactionMembership,
    "StatusInfo": StatusInfo,
    "Subclassification": Subclassification,
    "SubjectMembership": SubjectMembership,
    "Succession": Succession,
    "SuccessionAsUsage": SuccessionAsUsage,
    "SuccessionFlow": SuccessionFlow,
    "SuccessionFlowUsage": SuccessionFlowUsage,
    "TerminateActionUsage": TerminateActionUsage,
    "TextualRepresentation": TextualRepresentation,
    "ToolExecution": ToolExecution,
    "ToolVariable": ToolVariable,
    "TransitionFeatureMembership": TransitionFeatureMembership,
    "TransitionUsage": TransitionUsage,
    "TriggerInvocationExpression": TriggerInvocationExpression,
    "TypeFeaturing": TypeFeaturing,
    "Unioning": Unioning,
    "UseCaseDefinition": UseCaseDefinition,
    "VariantMembership": VariantMembership,
    "VerificationCaseDefinition": VerificationCaseDefinition,
    "VerificationCaseUsage": VerificationCaseUsage,
    "VerificationMethod": VerificationMethod,
    "ViewDefinition": ViewDefinition,
    "ViewRenderingMembership": ViewRenderingMembership,
    "ViewUsage": ViewUsage,
    "ViewpointDefinition": ViewpointDefinition,
    "ViewpointUsage": ViewpointUsage,
    "WhileLoopActionUsage": WhileLoopActionUsage,
}


def _call_or_value(element: Any, name: str):
    value = getattr(element, name, None)
    return value() if callable(value) else value


def class_for(element: Any) -> type[ElementFacade]:
    metatype_id = _call_or_value(element, "metatype_id")
    if metatype_id in METAMODEL_CLASS_BY_METATYPE:
        return METAMODEL_CLASS_BY_METATYPE[metatype_id]
    kind = _call_or_value(element, "kind")
    if kind in METAMODEL_CLASS_BY_KIND:
        return METAMODEL_CLASS_BY_KIND[kind]
    return ElementFacade


def facade(element: Any) -> ElementFacade:
    return class_for(element).wrap(element)


def wrap(element: Any) -> ElementFacade:
    """Compatibility alias for facade()."""
    return facade(element)
