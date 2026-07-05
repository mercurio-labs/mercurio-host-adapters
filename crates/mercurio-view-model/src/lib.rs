use std::collections::{HashMap, HashSet};

use mercurio_core::graph::Graph;
use mercurio_core::metamodel::MetamodelAttributeRegistry;
pub use mercurio_views::{
    ElementDetailsDto, ElementPropertyRowDto, ElementPropertyTableDto, ExplorerAttributeDto,
    InheritedPropertyValueDto, element_details,
};
use serde::Serialize;
use serde_json::Value;

#[derive(Debug, Clone, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct PartDto {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub element_kind: String,
    pub parent_id: Option<String>,
    pub depth: u32,
    pub attributes: serde_json::Map<String, Value>,
}

pub fn parts_from_graph(graph: &Graph) -> Vec<PartDto> {
    const SKIP_PROPS: &[&str] = &[
        "declared_name",
        "name",
        "owner",
        "owning_type",
        "type",
        "source_file",
        "sourceFile",
        "definition",
    ];

    let part_elements = graph
        .elements()
        .iter()
        .filter(|element| is_part_kind(&element.kind))
        .collect::<Vec<_>>();

    let part_id_set = part_elements
        .iter()
        .map(|element| element.element_id.as_str())
        .collect::<HashSet<_>>();

    let parent_map = part_elements
        .iter()
        .map(|element| {
            let parent = element
                .properties
                .get("owner")
                .or_else(|| element.properties.get("owning_type"))
                .and_then(Value::as_str)
                .filter(|parent| part_id_set.contains(*parent));
            (element.element_id.as_str(), parent)
        })
        .collect::<HashMap<_, _>>();

    let mut depths = HashMap::new();
    for element in &part_elements {
        let id = element.element_id.as_str();
        if depths.contains_key(id) {
            continue;
        }
        let mut chain = vec![id];
        let mut current = id;
        while let Some(Some(parent)) = parent_map.get(current) {
            current = parent;
            chain.push(current);
            if depths.contains_key(parent) {
                break;
            }
        }
        let base = depths.get(current).copied().unwrap_or(0);
        for (index, segment) in chain.iter().rev().enumerate() {
            depths.insert(*segment, base + index as u32);
        }
    }

    part_elements
        .iter()
        .map(|element| {
            let properties = &element.properties;
            let name = properties
                .get("declared_name")
                .or_else(|| properties.get("name"))
                .and_then(Value::as_str)
                .unwrap_or_else(|| element.element_id.rsplit('.').next().unwrap_or(""))
                .to_string();
            let kind = properties
                .get("type")
                .or_else(|| properties.get("definition"))
                .and_then(Value::as_str)
                .unwrap_or("")
                .rsplit('.')
                .next()
                .unwrap_or("")
                .to_string();
            let attributes = properties
                .iter()
                .filter(|(key, _)| !SKIP_PROPS.iter().any(|skip| *skip == key.as_ref()))
                .map(|(key, value)| (key.to_string(), value.clone()))
                .collect();

            PartDto {
                id: element.element_id.clone(),
                name,
                kind,
                element_kind: element.kind.to_string(),
                parent_id: parent_map[element.element_id.as_str()].map(str::to_string),
                depth: depths
                    .get(element.element_id.as_str())
                    .copied()
                    .unwrap_or(0),
                attributes,
            }
        })
        .collect()
}

fn is_part_kind(kind: &str) -> bool {
    matches!(
        kind,
        "PartUsage"
            | "PartDefinition"
            | "IndividualUsage"
            | "model.PartUsage"
            | "model.PartDefinition"
            | "model.IndividualUsage"
            | "Model::PartUsage"
            | "Model::Systems::PartUsage"
            | "Model::Systems::PartDefinition"
            | "SysML::PartUsage"
            | "SysML::PartDefinition"
            | "SysML::Parts::PartUsage"
            | "SysML::Parts::PartDefinition"
            | "SysML::Systems::PartUsage"
            | "SysML::Systems::PartDefinition"
    )
}

pub fn element_details_from_graph(graph: &Graph, id: &str) -> Option<ElementDetailsDto> {
    let registry = MetamodelAttributeRegistry::build(graph);
    element_details(graph, &registry, id)
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use mercurio_core::{Graph, KirDocument, KirElement};

    use super::*;

    #[test]
    fn projects_part_hierarchy() {
        let document = KirDocument {
            metadata: BTreeMap::new(),
            elements: vec![
                KirElement {
                    id: "type.Demo.Vehicle".to_string(),
                    kind: "PartDefinition".to_string(),
                    layer: 2,
                    properties: BTreeMap::from([(
                        "declared_name".to_string(),
                        Value::String("Vehicle".to_string()),
                    )]),
                },
                KirElement {
                    id: "feature.Demo.Vehicle.engine".to_string(),
                    kind: "PartUsage".to_string(),
                    layer: 2,
                    properties: BTreeMap::from([
                        (
                            "declared_name".to_string(),
                            Value::String("engine".to_string()),
                        ),
                        (
                            "owner".to_string(),
                            Value::String("type.Demo.Vehicle".to_string()),
                        ),
                    ]),
                },
            ],
        };
        let graph = Graph::from_document(document).expect("test graph");
        let parts = parts_from_graph(&graph);

        assert_eq!(parts.len(), 2);
        assert_eq!(parts[1].parent_id.as_deref(), Some("type.Demo.Vehicle"));
        assert_eq!(parts[1].depth, 1);
    }

    #[test]
    fn part_projection_uses_known_kinds_not_substrings() {
        let document = KirDocument {
            metadata: BTreeMap::new(),
            elements: vec![
                KirElement {
                    id: "feature.Demo.Vehicle.engine".to_string(),
                    kind: "SysML::Systems::PartUsage".to_string(),
                    layer: 2,
                    properties: BTreeMap::from([(
                        "declared_name".to_string(),
                        Value::String("engine".to_string()),
                    )]),
                },
                KirElement {
                    id: "diagnostic.Demo.NotPart".to_string(),
                    kind: "DiagnosticPartUsageMarker".to_string(),
                    layer: 2,
                    properties: BTreeMap::new(),
                },
            ],
        };
        let graph = Graph::from_document(document).expect("test graph");
        let parts = parts_from_graph(&graph);

        assert_eq!(parts.len(), 1);
        assert_eq!(parts[0].id, "feature.Demo.Vehicle.engine");
    }
}
