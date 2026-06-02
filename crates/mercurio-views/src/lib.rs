use std::collections::{BTreeSet, VecDeque};
use std::time::Instant;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use mercurio_core::graph::{Element, Graph, NodeId};
use mercurio_core::metadata_annotations_named;
use mercurio_core::metamodel::{
    MetamodelAttributeRegistry, collect_specialization_ancestors, effective_properties,
    element_metatype, query_element_attributes,
};

const DEFAULT_MAX_DEPTH: usize = 8;
const DEFAULT_MAX_NODES: usize = 350;
const DEFAULT_MAX_EDGES: usize = 900;
const MAX_RELATION_FANOUT_PER_NODE: usize = 250;
const TIMING_WARNING_THRESHOLD_MS: u128 = 250;
pub const VIEW_SCHEMA: &str = "mercurio.view.v1";
pub const VIEW_SPEC_VERSION: u8 = 1;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DiagramKindDto {
    Structure,
    Activity,
    PackageTree,
    CompositionGraph,
    ReferenceGraph,
    DependencyGraph,
    MetatypeInstanceMap,
    ImpactView,
    PropertyInheritance,
    ValidationView,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DiagramDirectionDto {
    Parents,
    Children,
    Both,
}

impl Default for DiagramDirectionDto {
    fn default() -> Self {
        Self::Children
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramQueryOptionsDto {
    #[serde(default = "default_diagram_relations")]
    pub relations: Vec<String>,
    #[serde(default)]
    pub direction: DiagramDirectionDto,
    #[serde(default = "default_diagram_depth")]
    pub depth: usize,
    #[serde(default = "default_true")]
    pub include_libraries: bool,
    #[serde(default = "default_true")]
    pub include_user_model: bool,
    #[serde(default = "default_max_nodes")]
    pub max_nodes: usize,
    #[serde(default = "default_max_edges")]
    pub max_edges: usize,
}

impl Default for DiagramQueryOptionsDto {
    fn default() -> Self {
        Self {
            relations: default_diagram_relations(),
            direction: DiagramDirectionDto::default(),
            depth: default_diagram_depth(),
            include_libraries: true,
            include_user_model: true,
            max_nodes: default_max_nodes(),
            max_edges: default_max_edges(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramLayoutOptionsDto {
    #[serde(default = "default_layout_engine")]
    pub engine: String,
    #[serde(default = "default_layout_direction")]
    pub direction: String,
}

impl Default for DiagramLayoutOptionsDto {
    fn default() -> Self {
        Self {
            engine: default_layout_engine(),
            direction: default_layout_direction(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramStyleOptionsDto {
    #[serde(default = "default_true")]
    pub show_attributes: bool,
    #[serde(default = "default_true")]
    pub show_edge_labels: bool,
    #[serde(default)]
    pub group_by_layer: bool,
}

impl Default for DiagramStyleOptionsDto {
    fn default() -> Self {
        Self {
            show_attributes: true,
            show_edge_labels: true,
            group_by_layer: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramSpecDto {
    pub version: u8,
    pub kind: DiagramKindDto,
    pub title: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub root: Option<String>,
    #[serde(default)]
    pub query: DiagramQueryOptionsDto,
    #[serde(default)]
    pub layout: DiagramLayoutOptionsDto,
    #[serde(default)]
    pub style: DiagramStyleOptionsDto,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramRenderRequestDto {
    pub spec: DiagramSpecDto,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ViewModeDto {
    Visualization,
    Creation,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ViewDocumentDto {
    pub schema: String,
    pub version: u8,
    pub kind: String,
    pub mode: ViewModeDto,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub diagram: Option<DiagramSpecDto>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub table: Option<TableSpecDto>,
}

impl ViewDocumentDto {
    pub fn diagram(spec: DiagramSpecDto) -> Self {
        Self {
            schema: VIEW_SCHEMA.to_string(),
            version: VIEW_SPEC_VERSION,
            kind: format!("diagram.{}", diagram_kind_name(&spec.kind)),
            mode: ViewModeDto::Visualization,
            diagram: Some(spec),
            table: None,
        }
    }

    pub fn table(spec: TableSpecDto) -> Self {
        Self {
            schema: VIEW_SCHEMA.to_string(),
            version: VIEW_SPEC_VERSION,
            kind: "table".to_string(),
            mode: ViewModeDto::Visualization,
            diagram: None,
            table: Some(spec),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TableKindDto {
    Elements,
    Requirements,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableColumnSpecDto {
    pub key: String,
    pub label: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableSpecDto {
    pub version: u8,
    pub kind: TableKindDto,
    pub title: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub root: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target_type: Option<String>,
    #[serde(default)]
    pub query: DiagramQueryOptionsDto,
    #[serde(default)]
    pub columns: Vec<TableColumnSpecDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableRenderRequestDto {
    pub spec: TableSpecDto,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableViewDto {
    pub spec: TableSpecDto,
    pub columns: Vec<TableColumnSpecDto>,
    #[serde(default)]
    pub available_columns: Vec<TableColumnSpecDto>,
    pub rows: Vec<TableRowDto>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableRowDto {
    pub id: String,
    pub element: String,
    pub cells: Vec<TableCellDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableCellDto {
    pub key: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ViewValidationDiagnostic {
    pub code: &'static str,
    pub path: String,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DiagramViewDto {
    pub spec: DiagramSpecDto,
    pub symbols: Vec<DiagramSymbolDto>,
    pub nodes: Vec<DiagramNodeDto>,
    pub edges: Vec<DiagramEdgeDto>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramSymbolDto {
    pub id: String,
    pub element: String,
    pub role: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub relation: Option<String>,
    #[serde(default)]
    pub properties: serde_json::Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DiagramNodeDto {
    pub id: String,
    pub symbol: String,
    pub label: String,
    pub kind: String,
    pub layer: u8,
    pub badges: Vec<String>,
    pub attributes: Vec<DiagramAttributeDto>,
    pub properties: serde_json::Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramAttributeDto {
    pub name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub type_label: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiagramEdgeDto {
    pub id: String,
    pub symbol: String,
    pub source: String,
    pub target: String,
    pub relation: String,
    pub label: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DiagramError {
    UnsupportedKind(DiagramKindDto),
    UnsupportedVersion(u8),
    MissingRoot,
    RootNotFound(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TableError {
    UnsupportedKind(TableKindDto),
    UnsupportedVersion(u8),
    RootNotFound(String),
}

impl std::fmt::Display for TableError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnsupportedKind(kind) => write!(f, "table kind is not implemented: {kind:?}"),
            Self::UnsupportedVersion(version) => {
                write!(f, "unsupported table spec version: {version}")
            }
            Self::RootNotFound(root) => write!(f, "table root not found: {root}"),
        }
    }
}

impl std::error::Error for TableError {}

impl std::fmt::Display for DiagramError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnsupportedKind(kind) => write!(f, "diagram kind is not implemented: {kind:?}"),
            Self::UnsupportedVersion(version) => {
                write!(f, "unsupported diagram spec version: {version}")
            }
            Self::MissingRoot => write!(f, "diagram root is required"),
            Self::RootNotFound(root) => write!(f, "diagram root not found: {root}"),
        }
    }
}

impl std::error::Error for DiagramError {}

pub fn list_diagram_kinds() -> Vec<DiagramKindDto> {
    vec![
        DiagramKindDto::Structure,
        DiagramKindDto::Activity,
        DiagramKindDto::PackageTree,
        DiagramKindDto::CompositionGraph,
        DiagramKindDto::ReferenceGraph,
        DiagramKindDto::DependencyGraph,
        DiagramKindDto::MetatypeInstanceMap,
        DiagramKindDto::ImpactView,
        DiagramKindDto::PropertyInheritance,
        DiagramKindDto::ValidationView,
    ]
}

pub fn list_table_kinds() -> Vec<TableKindDto> {
    vec![TableKindDto::Elements, TableKindDto::Requirements]
}

pub fn validate_view_document(
    document: &ViewDocumentDto,
) -> Result<(), Vec<ViewValidationDiagnostic>> {
    let mut diagnostics = Vec::new();
    if document.schema != VIEW_SCHEMA {
        diagnostics.push(view_diagnostic(
            "view.schema",
            "/schema",
            format!("expected schema `{VIEW_SCHEMA}`"),
        ));
    }
    if document.version != VIEW_SPEC_VERSION {
        diagnostics.push(view_diagnostic(
            "view.version",
            "/version",
            format!("expected version {VIEW_SPEC_VERSION}"),
        ));
    }
    match (&document.diagram, &document.table) {
        (Some(diagram), None) => {
            let expected = format!("diagram.{}", diagram_kind_name(&diagram.kind));
            if document.kind != expected {
                diagnostics.push(view_diagnostic(
                    "view.kind",
                    "/kind",
                    format!("expected kind `{expected}` for diagram payload"),
                ));
            }
            validate_diagram_spec(diagram, "/diagram", &mut diagnostics);
        }
        (None, Some(table)) => {
            let expected = "table";
            if document.kind != expected {
                diagnostics.push(view_diagnostic(
                    "view.kind",
                    "/kind",
                    format!("expected kind `{expected}` for table payload"),
                ));
            }
            validate_table_spec(table, "/table", &mut diagnostics);
        }
        (None, None) => diagnostics.push(view_diagnostic(
            "view.payload",
            "/",
            "view document must contain one payload".to_string(),
        )),
        (Some(_), Some(_)) => diagnostics.push(view_diagnostic(
            "view.payload",
            "/",
            "view document must not contain multiple payloads".to_string(),
        )),
    }

    if diagnostics.is_empty() {
        Ok(())
    } else {
        Err(diagnostics)
    }
}

fn validate_diagram_spec(
    spec: &DiagramSpecDto,
    path: &str,
    diagnostics: &mut Vec<ViewValidationDiagnostic>,
) {
    validate_common_spec(spec.version, &spec.title, &spec.query, path, diagnostics);
    if spec.layout.engine.trim().is_empty() {
        diagnostics.push(view_diagnostic(
            "view.diagram.layout.engine",
            format!("{path}/layout/engine"),
            "layout engine is required".to_string(),
        ));
    }
    let direction = spec.layout.direction.to_ascii_uppercase();
    if !matches!(direction.as_str(), "LR" | "RL" | "TB" | "BT") {
        diagnostics.push(view_diagnostic(
            "view.diagram.layout.direction",
            format!("{path}/layout/direction"),
            "layout direction must be one of LR, RL, TB, BT".to_string(),
        ));
    }
}

fn validate_table_spec(
    spec: &TableSpecDto,
    path: &str,
    diagnostics: &mut Vec<ViewValidationDiagnostic>,
) {
    validate_common_spec(spec.version, &spec.title, &spec.query, path, diagnostics);
    let mut column_keys = BTreeSet::new();
    for (index, column) in spec.columns.iter().enumerate() {
        if column.key.trim().is_empty() {
            diagnostics.push(view_diagnostic(
                "view.table.column.key",
                format!("{path}/columns/{index}/key"),
                "column key is required".to_string(),
            ));
        }
        if !column_keys.insert(column.key.clone()) {
            diagnostics.push(view_diagnostic(
                "view.table.column.key.duplicate",
                format!("{path}/columns/{index}/key"),
                format!("duplicate column key `{}`", column.key),
            ));
        }
        if column.label.trim().is_empty() {
            diagnostics.push(view_diagnostic(
                "view.table.column.label",
                format!("{path}/columns/{index}/label"),
                "column label is required".to_string(),
            ));
        }
        if let Some(path_value) = &column.path {
            validate_column_path(
                path_value,
                format!("{path}/columns/{index}/path"),
                diagnostics,
            );
        } else {
            validate_column_path(
                &column.key,
                format!("{path}/columns/{index}/key"),
                diagnostics,
            );
        }
    }
}

fn validate_column_path(
    path_value: &str,
    path: String,
    diagnostics: &mut Vec<ViewValidationDiagnostic>,
) {
    if path_value
        .split('.')
        .any(|segment| segment.trim().is_empty())
    {
        diagnostics.push(view_diagnostic(
            "view.table.column.path",
            path,
            "column path segments must not be empty".to_string(),
        ));
    }
}

fn validate_common_spec(
    version: u8,
    title: &str,
    query: &DiagramQueryOptionsDto,
    path: &str,
    diagnostics: &mut Vec<ViewValidationDiagnostic>,
) {
    if version != VIEW_SPEC_VERSION {
        diagnostics.push(view_diagnostic(
            "view.spec.version",
            format!("{path}/version"),
            format!("expected spec version {VIEW_SPEC_VERSION}"),
        ));
    }
    if title.trim().is_empty() {
        diagnostics.push(view_diagnostic(
            "view.spec.title",
            format!("{path}/title"),
            "title is required".to_string(),
        ));
    }
    if query.max_nodes == 0 {
        diagnostics.push(view_diagnostic(
            "view.query.max_nodes",
            format!("{path}/query/max_nodes"),
            "max_nodes must be greater than zero".to_string(),
        ));
    }
    if query.max_edges == 0 {
        diagnostics.push(view_diagnostic(
            "view.query.max_edges",
            format!("{path}/query/max_edges"),
            "max_edges must be greater than zero".to_string(),
        ));
    }
}

fn view_diagnostic(
    code: &'static str,
    path: impl Into<String>,
    message: String,
) -> ViewValidationDiagnostic {
    ViewValidationDiagnostic {
        code,
        path: path.into(),
        message,
    }
}

pub fn render_table(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    mut spec: TableSpecDto,
) -> Result<TableViewDto, TableError> {
    if spec.version != 1 {
        return Err(TableError::UnsupportedVersion(spec.version));
    }

    match spec.kind {
        TableKindDto::Elements => render_elements_table(graph, metamodel_registry, &mut spec),
        TableKindDto::Requirements => {
            render_requirements_table(graph, metamodel_registry, &mut spec)
        }
    }
}

fn render_elements_table(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    spec: &mut TableSpecDto,
) -> Result<TableViewDto, TableError> {
    let target_type = normalized_target_type(spec.target_type.as_deref());
    let available_columns =
        available_table_columns(graph, metamodel_registry, target_type.as_deref());
    let columns = if spec.columns.is_empty() {
        default_table_columns(&available_columns)
    } else {
        spec.columns.clone()
    };
    let visible_ids = if let Some(root) =
        spec.root.as_deref().filter(|root| !root.trim().is_empty())
    {
        let root =
            resolve_root(graph, root).ok_or_else(|| TableError::RootNotFound(root.to_string()))?;
        collect_structure_ids(graph, root.id, &spec.query, &default_diagram_relations()).visible_ids
    } else {
        graph.elements().iter().map(|element| element.id).collect()
    };

    let mut rows = visible_ids
        .iter()
        .filter_map(|node_id| graph.element(*node_id))
        .filter(|element| include_element(element, &spec.query))
        .filter(|element| table_target_matches(graph, element, target_type.as_deref()))
        .map(|element| table_row(graph, element, &columns))
        .collect::<Vec<_>>();
    rows.sort_by(|left, right| left.id.cmp(&right.id));

    let mut warnings = Vec::new();
    if rows.is_empty() {
        warnings.push("No elements matched the requested filters.".to_string());
    }

    Ok(TableViewDto {
        spec: spec.clone(),
        columns,
        available_columns,
        rows,
        warnings,
    })
}

fn render_requirements_table(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    spec: &mut TableSpecDto,
) -> Result<TableViewDto, TableError> {
    let target_type = normalized_target_type(spec.target_type.as_deref())
        .or_else(|| Some("Requirement".to_string()));
    let available_columns =
        available_table_columns(graph, metamodel_registry, target_type.as_deref());
    let columns = if spec.columns.is_empty() {
        default_requirements_columns()
    } else {
        spec.columns.clone()
    };
    let visible_ids =
        if let Some(root) = spec.root.as_deref().filter(|root| !root.trim().is_empty()) {
            let root = resolve_root(graph, root)
                .ok_or_else(|| TableError::RootNotFound(root.to_string()))?;
            collect_structure_ids(
                graph,
                root.id,
                &spec.query,
                &[
                    "owner".to_string(),
                    "satisfy".to_string(),
                    "verify".to_string(),
                ],
            )
            .visible_ids
        } else {
            graph.elements().iter().map(|element| element.id).collect()
        };

    let mut rows = visible_ids
        .iter()
        .filter_map(|node_id| graph.element(*node_id))
        .filter(|element| include_element(element, &spec.query))
        .filter(|element| table_target_matches(graph, element, target_type.as_deref()))
        .map(|element| table_row(graph, element, &columns))
        .collect::<Vec<_>>();
    rows.sort_by(|left, right| left.id.cmp(&right.id));

    let mut warnings = Vec::new();
    if rows.is_empty() {
        warnings.push("No requirements matched the requested filters.".to_string());
    }

    Ok(TableViewDto {
        spec: spec.clone(),
        columns,
        available_columns,
        rows,
        warnings,
    })
}

fn default_elements_columns() -> Vec<TableColumnSpecDto> {
    [
        ("id", "ID"),
        ("name", "Name"),
        ("kind", "Kind"),
        ("owner", "Owner"),
        ("source_file", "Source"),
    ]
    .into_iter()
    .map(|(key, label)| TableColumnSpecDto {
        key: key.to_string(),
        label: label.to_string(),
        path: None,
    })
    .collect()
}

fn default_requirements_columns() -> Vec<TableColumnSpecDto> {
    [
        ("requirement_id", "ID"),
        ("name", "Name"),
        ("text", "Text"),
        ("status", "Status"),
        ("owner", "Owner"),
    ]
    .into_iter()
    .map(|(key, label)| TableColumnSpecDto {
        key: key.to_string(),
        label: label.to_string(),
        path: None,
    })
    .collect()
}

fn normalized_target_type(target_type: Option<&str>) -> Option<String> {
    target_type
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}

fn default_table_columns(available_columns: &[TableColumnSpecDto]) -> Vec<TableColumnSpecDto> {
    let preferred = ["id", "name", "kind", "owner", "source_file"];
    let mut columns = preferred
        .iter()
        .filter_map(|key| {
            available_columns
                .iter()
                .find(|column| column.key == *key)
                .cloned()
        })
        .collect::<Vec<_>>();
    if columns.is_empty() {
        columns = default_elements_columns();
    }
    columns
}

fn available_table_columns(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    target_type: Option<&str>,
) -> Vec<TableColumnSpecDto> {
    let mut keys = BTreeSet::new();
    let mut columns = Vec::new();
    for column in default_elements_columns() {
        if keys.insert(column.key.clone()) {
            columns.push(column);
        }
    }

    if let Some(target_type) = target_type {
        for element in graph.elements() {
            if !table_type_identifier_matches(element, target_type) {
                continue;
            }
            for declaration in metamodel_registry.declared_attributes_for(&element.element_id) {
                if keys.insert(declaration.name.clone()) {
                    columns.push(TableColumnSpecDto {
                        key: declaration.name.clone(),
                        label: title_from_column_key(&declaration.name),
                        path: Some(declaration.name.clone()),
                    });
                }
            }
            let Some(query) = query_element_attributes(graph, metamodel_registry, element.id, None)
            else {
                continue;
            };
            for row in query.rows {
                if keys.insert(row.name.clone()) {
                    columns.push(TableColumnSpecDto {
                        key: row.name.clone(),
                        label: title_from_column_key(&row.name),
                        path: Some(row.name),
                    });
                }
            }
        }
    }

    columns.sort_by(|left, right| {
        column_sort_rank(&left.key)
            .cmp(&column_sort_rank(&right.key))
            .then_with(|| left.label.cmp(&right.label))
    });
    columns
}

fn column_sort_rank(key: &str) -> usize {
    match key {
        "id" => 0,
        "name" => 1,
        "kind" => 2,
        "owner" => 3,
        "source_file" => 4,
        _ => 10,
    }
}

fn title_from_column_key(key: &str) -> String {
    key.split('_')
        .filter(|segment| !segment.is_empty())
        .map(|segment| {
            let mut chars = segment.chars();
            match chars.next() {
                Some(first) => format!("{}{}", first.to_uppercase(), chars.as_str()),
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn table_target_matches(graph: &Graph, element: &Element, target_type: Option<&str>) -> bool {
    let Some(target_type) = target_type else {
        return true;
    };
    if table_type_is_element(target_type) {
        return true;
    }
    table_type_identifier_matches(element, target_type)
        || element_metatype(graph, element.id)
            .is_some_and(|metatype| table_type_identifier_matches(metatype, target_type))
        || collect_specialization_ancestors(graph, element.id)
            .into_iter()
            .any(|ancestor| table_type_identifier_matches(ancestor, target_type))
}

fn table_type_is_element(target_type: &str) -> bool {
    let normalized = canonical_table_type(target_type);
    normalized == "element" || normalized.ends_with("::element")
}

fn table_type_identifier_matches(element: &Element, target_type: &str) -> bool {
    let target = canonical_table_type(target_type);
    [element.element_id.as_str(), element.kind.as_str()]
        .into_iter()
        .any(|candidate| {
            let candidate = canonical_table_type(candidate);
            candidate == target
                || candidate.ends_with(&format!("::{target}"))
                || (!target.contains("::") && label_for_id(&candidate).contains(&target))
        })
}

fn canonical_table_type(value: &str) -> String {
    let normalized = value
        .trim()
        .replace('.', "::")
        .replace(' ', "")
        .to_ascii_lowercase();
    normalized
        .strip_suffix("def")
        .map(|stem| format!("{stem}definition"))
        .unwrap_or(normalized)
}

fn table_row(graph: &Graph, element: &Element, columns: &[TableColumnSpecDto]) -> TableRowDto {
    TableRowDto {
        id: element.element_id.clone(),
        element: element.element_id.clone(),
        cells: columns
            .iter()
            .map(|column| TableCellDto {
                key: column.key.clone(),
                value: table_cell_value(graph, element, column),
            })
            .collect(),
    }
}

fn table_cell_value(graph: &Graph, element: &Element, column: &TableColumnSpecDto) -> String {
    let path = column.path.as_deref().unwrap_or(&column.key);
    if path.starts_with("metadata[") {
        return resolve_metadata_path(element, path).unwrap_or_default();
    }
    if path.contains('.') {
        return resolve_element_path(graph, element, path).unwrap_or_default();
    }

    match path {
        "id" | "element" => element.element_id.clone(),
        "kind" => element.kind.clone(),
        "owner" => effective_property_text(graph, element, "owner")
            .or_else(|| owner_label(graph, element))
            .unwrap_or_default(),
        "name" => effective_property_text(graph, element, "declared_name")
            .or_else(|| effective_property_text(graph, element, "name"))
            .unwrap_or_else(|| label_for_id(&element.element_id)),
        "text" => effective_property_text(graph, element, "text")
            .or_else(|| effective_property_text(graph, element, "body"))
            .or_else(|| effective_property_text(graph, element, "doc"))
            .unwrap_or_default(),
        other => effective_property_text(graph, element, other).unwrap_or_default(),
    }
}

fn resolve_metadata_path(element: &Element, path: &str) -> Option<String> {
    let remainder = path.strip_prefix("metadata[")?;
    let (type_name, field_path) = remainder.split_once("].")?;
    if type_name.trim().is_empty() || field_path.trim().is_empty() {
        return None;
    }
    metadata_annotations_named(&element.properties, type_name)
        .into_iter()
        .find_map(|annotation| value_path_text(&annotation.properties, field_path))
}

fn value_path_text(value: &Value, path: &str) -> Option<String> {
    let mut current = value;
    for segment in path.split('.') {
        if segment.trim().is_empty() {
            return None;
        }
        current = current.get(segment)?;
    }
    Some(value_to_text(current))
}

fn resolve_element_path(graph: &Graph, element: &Element, path: &str) -> Option<String> {
    let mut segments = path.split('.');
    let first = segments.next()?;
    let mut current = resolve_element_reference(graph, element, first)?;
    let mut tail = segments.peekable();
    while let Some(segment) = tail.next() {
        if tail.peek().is_none() {
            return match segment {
                "id" | "element" => Some(current.element_id.clone()),
                "kind" => Some(current.kind.clone()),
                "name" => property_text(current, "declared_name")
                    .or_else(|| property_text(current, "name"))
                    .or_else(|| Some(label_for_id(&current.element_id))),
                other => property_text(current, other),
            };
        }
        current = resolve_element_reference(graph, current, segment)?;
    }
    Some(label_for_id(&current.element_id))
}

fn resolve_element_reference<'a>(
    graph: &'a Graph,
    element: &'a Element,
    key: &str,
) -> Option<&'a Element> {
    if key == "self" {
        return Some(element);
    }
    property_text(element, key)
        .and_then(|id| graph.element_by_element_id(&id))
        .or_else(|| {
            graph
                .outgoing(element.id, key)
                .next()
                .and_then(|edge| graph.element(edge.target))
        })
}

fn owner_label(graph: &Graph, element: &Element) -> Option<String> {
    graph
        .outgoing(element.id, "owner")
        .next()
        .and_then(|edge| graph.element(edge.target))
        .map(|owner| label_for_id(&owner.element_id))
}

fn property_text(element: &Element, key: &str) -> Option<String> {
    element.properties.get(key).map(value_to_text)
}

fn effective_property_text(graph: &Graph, element: &Element, key: &str) -> Option<String> {
    property_text(element, key).or_else(|| {
        let ancestors = collect_specialization_ancestors(graph, element.id);
        effective_properties(&ancestors, &element.properties)
            .get(key)
            .map(value_to_text)
    })
}

fn value_to_text(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::Bool(value) => value.to_string(),
        Value::Number(value) => value.to_string(),
        Value::String(value) => value.clone(),
        Value::Array(values) => values
            .iter()
            .map(value_to_text)
            .collect::<Vec<_>>()
            .join(", "),
        Value::Object(_) => value.to_string(),
    }
}

pub fn render_diagram(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    spec: DiagramSpecDto,
) -> Result<DiagramViewDto, DiagramError> {
    if spec.version != 1 {
        return Err(DiagramError::UnsupportedVersion(spec.version));
    }

    match spec.kind {
        DiagramKindDto::Structure => render_structure_diagram(graph, metamodel_registry, spec),
        DiagramKindDto::Activity => render_activity_diagram(graph, metamodel_registry, spec),
        _ => Err(DiagramError::UnsupportedKind(spec.kind)),
    }
}

fn render_activity_diagram(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    mut spec: DiagramSpecDto,
) -> Result<DiagramViewDto, DiagramError> {
    if spec.query.relations.is_empty() {
        spec.query.relations = vec![
            "owner".to_string(),
            "control_flow".to_string(),
            "object_flow".to_string(),
        ];
    }

    let mut view = render_structure_diagram(graph, metamodel_registry, spec)?;
    apply_activity_symbol_defaults(&mut view);
    Ok(view)
}

fn apply_activity_symbol_defaults(view: &mut DiagramViewDto) {
    let node_roles = view
        .nodes
        .iter()
        .map(|node| (node.symbol.clone(), activity_node_symbol(node)))
        .collect::<std::collections::BTreeMap<_, _>>();

    for symbol in &mut view.symbols {
        if symbol.role == "element" {
            if let Some((role, properties)) = node_roles.get(&symbol.id) {
                symbol.role = role.clone();
                symbol.properties = properties.clone();
            }
        } else if symbol.role == "edge" {
            let relation = symbol.relation.as_deref().unwrap_or_default();
            symbol.properties = edge_symbol_properties(relation);
        }
    }
}

fn activity_node_symbol(node: &DiagramNodeDto) -> (String, serde_json::Map<String, Value>) {
    let kind = node.kind.to_ascii_lowercase();
    let mut properties = serde_json::Map::new();
    let (role, shape) = if kind.contains("activity") {
        ("frame", "activity_frame")
    } else if kind.contains("object") {
        ("object_node", "object_node")
    } else if kind.contains("actionusage") || kind.ends_with("::action") {
        ("action", "action")
    } else if kind.contains("decision") {
        ("decision", "decision")
    } else if kind.contains("merge") {
        ("merge", "decision")
    } else if kind.contains("initial") {
        ("initial", "initial")
    } else if kind.contains("final") {
        ("activity_final", "activity_final")
    } else if kind.contains("parameter") {
        ("parameter", "parameter")
    } else {
        ("element", "node")
    };
    properties.insert("shape".to_string(), Value::String(shape.to_string()));
    if role == "object_node" {
        properties.insert("streaming".to_string(), Value::Bool(true));
    }
    (role.to_string(), properties)
}

fn render_structure_diagram(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    spec: DiagramSpecDto,
) -> Result<DiagramViewDto, DiagramError> {
    let total_start = Instant::now();
    let mut timings = Vec::new();
    let mut warnings = Vec::new();

    let relation_start = Instant::now();
    let relations = if spec.query.relations.is_empty() {
        default_diagram_relations()
    } else {
        spec.query.relations.clone()
    };
    timings.push(("relations", relation_start.elapsed()));

    let traversal_start = Instant::now();
    let traversal = if let Some(root) = spec.root.as_deref().filter(|root| !root.trim().is_empty())
    {
        let root_start = Instant::now();
        let root = resolve_root(graph, root)
            .ok_or_else(|| DiagramError::RootNotFound(root.to_string()))?;
        timings.push(("root", root_start.elapsed()));
        collect_structure_ids(graph, root.id, &spec.query, &relations)
    } else {
        collect_unrooted_structure_ids(graph, &spec.query)
    };
    timings.push(("traversal", traversal_start.elapsed()));
    warnings.extend(traversal.warnings);

    let node_start = Instant::now();
    let mut nodes = traversal
        .visible_ids
        .iter()
        .filter_map(|node_id| graph.element(*node_id))
        .filter(|element| include_element(element, &spec.query))
        .take(effective_max_nodes(&spec.query))
        .map(|element| diagram_node(graph, metamodel_registry, element))
        .collect::<Vec<_>>();
    nodes.sort_by(|left, right| left.id.cmp(&right.id));
    timings.push(("nodes", node_start.elapsed()));

    if nodes.is_empty() {
        warnings.push("No diagram nodes matched the requested filters.".to_string());
    }
    if traversal.visible_ids.len() > nodes.len() {
        warnings.push(format!(
            "Diagram node limit reached; showing {} of {} traversed nodes.",
            nodes.len(),
            traversal.visible_ids.len()
        ));
    }

    let edge_start = Instant::now();
    let retained_ids = nodes
        .iter()
        .map(|node| node.id.as_str())
        .collect::<BTreeSet<_>>();
    let mut edges = Vec::new();
    let max_edges = effective_max_edges(&spec.query);
    'node_edges: for node_id in &traversal.visible_ids {
        for edge in graph.outgoing_edges(*node_id) {
            if !relations.iter().any(|relation| relation == &edge.relation) {
                continue;
            }
            let Some(source) = graph.element_id(edge.source) else {
                continue;
            };
            let Some(target) = graph.element_id(edge.target) else {
                continue;
            };
            if retained_ids.contains(source) && retained_ids.contains(target) {
                edges.push(DiagramEdgeDto {
                    id: format!("{}:{}:{}", edge.relation, source, target),
                    symbol: symbol_id_for_edge(&edge.relation, source, target),
                    source: source.to_string(),
                    target: target.to_string(),
                    relation: edge.relation.clone(),
                    label: edge.relation.clone(),
                });
                if edges.len() >= max_edges {
                    warnings.push(format!(
                        "Diagram edge limit reached; showing first {max_edges} matching edges."
                    ));
                    break 'node_edges;
                }
            }
        }
    }
    edges.sort_by(|left, right| left.id.cmp(&right.id));
    edges.dedup_by(|left, right| left.id == right.id);
    timings.push(("edges", edge_start.elapsed()));

    timings.push(("total", total_start.elapsed()));
    let slow_phases = timings
        .iter()
        .filter(|(_, elapsed)| elapsed.as_millis() >= TIMING_WARNING_THRESHOLD_MS)
        .map(|(phase, elapsed)| format!("{phase}={}ms", elapsed.as_millis()))
        .collect::<Vec<_>>();
    if !slow_phases.is_empty() {
        warnings.push(format!(
            "Diagram render timing: {}.",
            slow_phases.join(", ")
        ));
    }

    Ok(DiagramViewDto {
        spec,
        symbols: nodes
            .iter()
            .map(|node| DiagramSymbolDto {
                id: node.symbol.clone(),
                element: node.id.clone(),
                role: "element".to_string(),
                source: None,
                target: None,
                relation: None,
                properties: serde_json::Map::new(),
            })
            .chain(edges.iter().map(|edge| DiagramSymbolDto {
                id: edge.symbol.clone(),
                element: edge.id.clone(),
                role: "edge".to_string(),
                source: Some(symbol_id_for_element(&edge.source)),
                target: Some(symbol_id_for_element(&edge.target)),
                relation: Some(edge.relation.clone()),
                properties: edge_symbol_properties(edge.relation.as_str()),
            }))
            .collect(),
        nodes,
        edges,
        warnings,
    })
}

struct StructureTraversal {
    visible_ids: BTreeSet<NodeId>,
    warnings: Vec<String>,
}

fn collect_structure_ids(
    graph: &Graph,
    root_id: NodeId,
    query: &DiagramQueryOptionsDto,
    relations: &[String],
) -> StructureTraversal {
    let mut visited = BTreeSet::new();
    let mut queue = VecDeque::from([(root_id, 0usize)]);
    let mut warnings = Vec::new();
    let max_depth = query.depth.min(DEFAULT_MAX_DEPTH);
    let max_nodes = effective_max_nodes(query);
    if query.depth > max_depth {
        warnings.push(format!(
            "Diagram depth limit reached; requested depth {} capped at {max_depth}.",
            query.depth
        ));
    }

    while let Some((node_id, depth)) = queue.pop_front() {
        if !visited.insert(node_id) {
            continue;
        }
        if visited.len() >= max_nodes {
            warnings.push(format!(
                "Diagram traversal node limit reached at {max_nodes} nodes."
            ));
            break;
        }
        if depth >= max_depth {
            continue;
        }

        if matches!(
            query.direction,
            DiagramDirectionDto::Parents | DiagramDirectionDto::Both
        ) {
            for relation in relations {
                let adjacent = parent_node_ids(graph, node_id, relation).collect::<Vec<_>>();
                for adjacent_id in adjacent.iter().take(MAX_RELATION_FANOUT_PER_NODE) {
                    queue.push_back((*adjacent_id, depth + 1));
                }
                if adjacent.len() > MAX_RELATION_FANOUT_PER_NODE {
                    warnings.push(format!(
                        "Diagram relation fan-out limit reached for `{relation}`."
                    ));
                }
            }
        }

        if matches!(
            query.direction,
            DiagramDirectionDto::Children | DiagramDirectionDto::Both
        ) {
            for relation in relations {
                let adjacent = child_node_ids(graph, node_id, relation).collect::<Vec<_>>();
                for adjacent_id in adjacent.iter().take(MAX_RELATION_FANOUT_PER_NODE) {
                    queue.push_back((*adjacent_id, depth + 1));
                }
                if adjacent.len() > MAX_RELATION_FANOUT_PER_NODE {
                    warnings.push(format!(
                        "Diagram relation fan-out limit reached for incoming `{relation}`."
                    ));
                }
            }
        }
    }

    StructureTraversal {
        visible_ids: visited,
        warnings,
    }
}

fn parent_node_ids<'a>(
    graph: &'a Graph,
    node_id: NodeId,
    relation: &'a str,
) -> Box<dyn Iterator<Item = NodeId> + 'a> {
    if relation == "part" {
        Box::new(graph.incoming(node_id, relation).map(|edge| edge.source))
    } else {
        Box::new(graph.outgoing(node_id, relation).map(|edge| edge.target))
    }
}

fn child_node_ids<'a>(
    graph: &'a Graph,
    node_id: NodeId,
    relation: &'a str,
) -> Box<dyn Iterator<Item = NodeId> + 'a> {
    if relation == "part" {
        Box::new(graph.outgoing(node_id, relation).map(|edge| edge.target))
    } else {
        Box::new(graph.incoming(node_id, relation).map(|edge| edge.source))
    }
}

fn collect_unrooted_structure_ids(
    graph: &Graph,
    query: &DiagramQueryOptionsDto,
) -> StructureTraversal {
    let max_nodes = effective_max_nodes(query);
    let matching_elements = graph
        .elements()
        .iter()
        .filter(|element| include_element(element, query))
        .collect::<Vec<_>>();
    let mut visible_ids = matching_elements
        .iter()
        .copied()
        .filter(|element| is_top_level_package(graph, element))
        .take(max_nodes)
        .map(|element| element.id)
        .collect::<BTreeSet<_>>();
    if !visible_ids.is_empty() {
        collect_owned_descendant_ids(graph, query, &mut visible_ids, max_nodes);
    }
    if visible_ids.is_empty() {
        visible_ids = matching_elements
            .iter()
            .copied()
            .take(max_nodes)
            .map(|element| element.id)
            .collect::<BTreeSet<_>>();
    }
    let mut warnings = Vec::new();
    if matching_elements.len() > visible_ids.len() {
        warnings.push(format!(
            "Diagram node limit reached; showing first {} matching nodes.",
            visible_ids.len()
        ));
    }

    StructureTraversal {
        visible_ids,
        warnings,
    }
}

fn collect_owned_descendant_ids(
    graph: &Graph,
    query: &DiagramQueryOptionsDto,
    visible_ids: &mut BTreeSet<NodeId>,
    max_nodes: usize,
) {
    let max_depth = query.depth.min(DEFAULT_MAX_DEPTH);
    let ownership_relations = ["owner", "ownedElement", "ownedMember"];
    let mut queue = visible_ids
        .iter()
        .copied()
        .map(|node_id| (node_id, 0usize))
        .collect::<VecDeque<_>>();

    while let Some((node_id, depth)) = queue.pop_front() {
        if visible_ids.len() >= max_nodes || depth >= max_depth {
            continue;
        }

        for relation in ownership_relations {
            for edge in graph
                .incoming(node_id, relation)
                .take(MAX_RELATION_FANOUT_PER_NODE)
            {
                let child_id = edge.source;
                if visible_ids.len() >= max_nodes {
                    return;
                }
                if graph
                    .element(child_id)
                    .is_some_and(|element| include_element(element, query))
                    && visible_ids.insert(child_id)
                {
                    queue.push_back((child_id, depth + 1));
                }
            }
            for edge in graph
                .outgoing(node_id, relation)
                .take(MAX_RELATION_FANOUT_PER_NODE)
            {
                let child_id = edge.target;
                if visible_ids.len() >= max_nodes {
                    return;
                }
                if graph
                    .element(child_id)
                    .is_some_and(|element| include_element(element, query))
                    && visible_ids.insert(child_id)
                {
                    queue.push_back((child_id, depth + 1));
                }
            }
        }
    }
}

fn is_top_level_package(graph: &Graph, element: &Element) -> bool {
    if !element.kind.to_ascii_lowercase().contains("package") {
        return false;
    }
    owner_ids(element).all(|owner| graph.element_by_element_id(owner).is_none())
}

fn owner_ids(element: &Element) -> impl Iterator<Item = &str> {
    element
        .properties
        .get("owner")
        .into_iter()
        .flat_map(|value| match value {
            Value::String(owner) => vec![owner.as_str()],
            Value::Array(values) => values
                .iter()
                .filter_map(|entry| entry.as_str())
                .collect::<Vec<_>>(),
            _ => Vec::new(),
        })
}

fn resolve_root<'a>(graph: &'a Graph, root: &str) -> Option<&'a Element> {
    if let Some(element) = graph.element_by_element_id(root) {
        return Some(element);
    }

    let normalized_root = root.trim().to_ascii_lowercase();
    graph.elements().iter().find(|element| {
        label_for_id(&element.element_id).to_ascii_lowercase() == normalized_root
            || element
                .element_id
                .rsplit("::")
                .next()
                .is_some_and(|name| name.eq_ignore_ascii_case(root))
            || element
                .element_id
                .rsplit('.')
                .next()
                .is_some_and(|name| name.eq_ignore_ascii_case(root))
    })
}

fn include_element(element: &Element, query: &DiagramQueryOptionsDto) -> bool {
    if element.layer < 2 {
        return query.include_libraries;
    }

    query.include_user_model
}

fn diagram_node(
    graph: &Graph,
    metamodel_registry: &MetamodelAttributeRegistry,
    element: &Element,
) -> DiagramNodeDto {
    let attributes = mercurio_core::metamodel::query_element_attributes(
        graph,
        metamodel_registry,
        element.id,
        None,
    )
    .map(|query| query.rows)
    .unwrap_or_default()
    .into_iter()
    .map(|attribute| DiagramAttributeDto {
        name: attribute.name,
        type_label: attribute
            .effective_value
            .as_ref()
            .map(|value| value_type_label(value).to_string()),
    })
    .collect();

    DiagramNodeDto {
        id: element.element_id.clone(),
        symbol: symbol_id_for_element(&element.element_id),
        label: label_for_id(&element.element_id),
        kind: element.kind.clone(),
        layer: element.layer,
        badges: vec![format!("L{}", element.layer)],
        attributes,
        properties: element
            .properties
            .iter()
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect(),
    }
}

fn symbol_id_for_element(id: &str) -> String {
    format!(
        "symbol.{}",
        id.chars()
            .map(|character| {
                if character.is_ascii_alphanumeric() {
                    character
                } else {
                    '_'
                }
            })
            .collect::<String>()
    )
}

fn symbol_id_for_edge(relation: &str, source: &str, target: &str) -> String {
    format!(
        "symbol.edge.{}.{}.{}",
        sanitize_symbol_segment(relation),
        sanitize_symbol_segment(source),
        sanitize_symbol_segment(target)
    )
}

fn sanitize_symbol_segment(value: &str) -> String {
    value
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() {
                character
            } else {
                '_'
            }
        })
        .collect()
}

fn edge_symbol_properties(relation: &str) -> serde_json::Map<String, Value> {
    let mut properties = serde_json::Map::new();
    properties.insert(
        "route".to_string(),
        Value::String(default_route(relation).to_string()),
    );
    properties.insert(
        "source_decoration".to_string(),
        Value::String(default_source_decoration(relation).to_string()),
    );
    properties.insert(
        "target_decoration".to_string(),
        Value::String(default_target_decoration(relation).to_string()),
    );
    properties.insert(
        "label_placement".to_string(),
        Value::String("above".to_string()),
    );
    properties
}

fn default_route(relation: &str) -> &'static str {
    match relation {
        "part" | "control_flow" | "object_flow" => "orthogonal",
        "source" | "target" | "transition" => "straight",
        _ => "straight",
    }
}

fn default_source_decoration(relation: &str) -> &'static str {
    match relation {
        "part" => "filled_diamond",
        _ => "none",
    }
}

fn default_target_decoration(relation: &str) -> &'static str {
    match relation {
        "specializes" => "hollow_triangle",
        "part" | "source" | "target" | "transition" | "control_flow" | "object_flow" => {
            "open_arrow"
        }
        _ => "open_arrow",
    }
}

fn label_for_id(id: &str) -> String {
    id.rsplit("::")
        .next()
        .and_then(|segment| segment.rsplit('.').next())
        .filter(|segment| !segment.is_empty())
        .unwrap_or(id)
        .to_string()
}

fn default_diagram_relations() -> Vec<String> {
    vec!["specializes".to_string()]
}

fn default_diagram_depth() -> usize {
    3
}

fn default_max_nodes() -> usize {
    DEFAULT_MAX_NODES
}

fn default_max_edges() -> usize {
    DEFAULT_MAX_EDGES
}

fn effective_max_nodes(query: &DiagramQueryOptionsDto) -> usize {
    query.max_nodes.clamp(1, DEFAULT_MAX_NODES)
}

fn effective_max_edges(query: &DiagramQueryOptionsDto) -> usize {
    query.max_edges.clamp(1, DEFAULT_MAX_EDGES)
}

fn default_layout_engine() -> String {
    "dagre".to_string()
}

fn default_layout_direction() -> String {
    "LR".to_string()
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use serde_json::json;

    use super::*;
    use mercurio_core::graph::{Edge, Element, GraphArtifact};

    fn sample_graph() -> (Graph, MetamodelAttributeRegistry) {
        let artifact = GraphArtifact {
            elements: vec![
                element(0, "SysML::Systems::PartDefinition", "SysML::Metaclass", 1),
                element(1, "pkg.Vehicle", "SysML::Package", 2),
                element(2, "type.Vehicle.Car", "SysML::Systems::PartDefinition", 2),
                element(
                    3,
                    "type.Vehicle.Engine",
                    "SysML::Systems::PartDefinition",
                    2,
                ),
                element(
                    4,
                    "req.Vehicle.SafeStart",
                    "SysML::Requirements::RequirementUsage",
                    2,
                ),
                element(
                    5,
                    "state.Vehicle.DriveMode",
                    "SysML::States::StateDefinition",
                    2,
                ),
                element(
                    6,
                    "state.Vehicle.DriveMode.Off",
                    "SysML::States::StateUsage",
                    2,
                ),
                element(
                    7,
                    "state.Vehicle.DriveMode.Starting",
                    "SysML::States::StateUsage",
                    2,
                ),
                element(
                    8,
                    "state.Vehicle.DriveMode.Running",
                    "SysML::States::StateUsage",
                    2,
                ),
                element(
                    9,
                    "state.Vehicle.DriveMode.Fault",
                    "SysML::States::StateUsage",
                    2,
                ),
                element(
                    10,
                    "transition.Vehicle.DriveMode.start",
                    "SysML::States::TransitionUsage",
                    2,
                ),
                element(
                    11,
                    "transition.Vehicle.DriveMode.ready",
                    "SysML::States::TransitionUsage",
                    2,
                ),
                element(
                    12,
                    "transition.Vehicle.DriveMode.fail",
                    "SysML::States::TransitionUsage",
                    2,
                ),
                element(
                    13,
                    "activity.Vehicle.ProvidePower",
                    "SysML::Actions::ActivityDefinition",
                    2,
                ),
                element(
                    14,
                    "action.Vehicle.ProvidePower.ProportionPower",
                    "SysML::Actions::ActionUsage",
                    2,
                ),
                element(
                    15,
                    "action.Vehicle.ProvidePower.ProvideGasPower",
                    "SysML::Actions::ActionUsage",
                    2,
                ),
                element(
                    16,
                    "object.Vehicle.ProvidePower.battCond",
                    "SysML::Actions::ObjectNode",
                    2,
                ),
                element(17, "KerML::Root::Comment", "KerML::Metaclass", 1),
                element(18, "KerML::Root::Comment::body", "KerML::Feature", 1),
                element(19, "KerML::Root::Comment::locale", "KerML::Feature", 1),
                element(20, "comment.Vehicle.Note", "KerML::Root::Comment", 2),
                element(
                    21,
                    "comment.Vehicle.LocalizedNote",
                    "KerML::Root::TextualRepresentation",
                    2,
                ),
            ],
            edges: vec![
                edge(2, 0, "specializes"),
                edge(3, 0, "specializes"),
                edge(2, 3, "part"),
                edge(2, 1, "owner"),
                edge(3, 1, "owner"),
                edge(4, 1, "owner"),
                edge(5, 1, "owner"),
                edge(6, 5, "owner"),
                edge(7, 5, "owner"),
                edge(8, 5, "owner"),
                edge(9, 5, "owner"),
                edge(10, 5, "owner"),
                edge(11, 5, "owner"),
                edge(12, 5, "owner"),
                edge(10, 6, "source"),
                edge(10, 7, "target"),
                edge(11, 7, "source"),
                edge(11, 8, "target"),
                edge(12, 8, "source"),
                edge(12, 9, "target"),
                edge(13, 1, "owner"),
                edge(14, 13, "owner"),
                edge(15, 13, "owner"),
                edge(16, 13, "owner"),
                edge(16, 14, "object_flow"),
                edge(14, 15, "control_flow"),
                edge(17, 18, "features"),
                edge(17, 19, "features"),
                edge(21, 17, "specializes"),
            ],
        };
        let graph = Graph::from_artifact(artifact).expect("sample graph should be valid");
        let registry = MetamodelAttributeRegistry::build(&graph);
        (graph, registry)
    }

    fn element(id: u32, element_id: &str, kind: &str, layer: u8) -> Element {
        let mut properties = BTreeMap::new();
        properties.insert("declared_name".to_string(), json!(label_for_id(element_id)));
        if element_id == "KerML::Root::Comment" {
            properties.insert(
                "features".to_string(),
                json!(["KerML::Root::Comment::body", "KerML::Root::Comment::locale"]),
            );
        }
        if element_id == "comment.Vehicle.Note" {
            properties.insert("body".to_string(), json!("Package-level review note."));
            properties.insert("locale".to_string(), json!("en-US"));
        }
        if element_id == "comment.Vehicle.LocalizedNote" {
            properties.insert("body".to_string(), json!("Localized package note."));
            properties.insert("locale".to_string(), json!("fr-FR"));
        }
        if kind.contains("Requirement") {
            properties.insert("requirement_id".to_string(), json!("REQ-001"));
            properties.insert(
                "text".to_string(),
                json!("Vehicle shall prevent unsafe starts."),
            );
            properties.insert(
                "metadata".to_string(),
                json!({
                    "RequirementLifecycle": {
                        "properties": {
                            "status": "approved",
                            "owner": "Safety Team",
                            "reviewDate": "2026-05-27"
                        }
                    }
                }),
            );
        }
        Element {
            id,
            element_id: element_id.to_string(),
            kind: kind.to_string(),
            layer,
            properties,
        }
    }

    fn edge(source: u32, target: u32, relation: &str) -> Edge {
        Edge {
            source,
            target,
            relation: relation.to_string(),
        }
    }

    fn render_sample(spec: DiagramSpecDto) -> DiagramViewDto {
        let (graph, registry) = sample_graph();
        render_diagram(&graph, &registry, spec).expect("sample diagram should render")
    }

    fn render_table_sample(spec: TableSpecDto) -> TableViewDto {
        let (graph, registry) = sample_graph();
        render_table(&graph, &registry, spec).expect("sample table should render")
    }

    fn structure_spec(root: Option<&str>, relations: Vec<&str>) -> DiagramSpecDto {
        DiagramSpecDto {
            version: 1,
            kind: DiagramKindDto::Structure,
            title: "Sample".to_string(),
            description: None,
            root: root.map(str::to_string),
            query: DiagramQueryOptionsDto {
                relations: relations.into_iter().map(str::to_string).collect(),
                direction: DiagramDirectionDto::Children,
                depth: 3,
                include_libraries: false,
                include_user_model: true,
                max_nodes: 350,
                max_edges: 900,
            },
            layout: DiagramLayoutOptionsDto::default(),
            style: DiagramStyleOptionsDto::default(),
        }
    }

    #[test]
    fn structure_diagram_renders_sample_package_containment() {
        let view = render_sample(structure_spec(Some("pkg.Vehicle"), vec!["owner"]));

        assert!(view.nodes.iter().any(|node| node.id == "pkg.Vehicle"));
        assert!(view.nodes.iter().any(|node| node.id == "type.Vehicle.Car"));
        assert!(
            view.symbols
                .iter()
                .any(|symbol| symbol.element == "type.Vehicle.Car"
                    && symbol.id == "symbol.type_Vehicle_Car")
        );
        assert!(
            view.nodes
                .iter()
                .any(|node| node.id == "state.Vehicle.DriveMode")
        );
        assert!(view.edges.iter().any(|edge| {
            edge.source == "type.Vehicle.Car"
                && edge.target == "pkg.Vehicle"
                && edge.relation == "owner"
        }));
        assert!(view.warnings.is_empty());
    }

    #[test]
    fn structure_diagram_preserves_part_relationship() {
        let view = render_sample(structure_spec(Some("type.Vehicle.Car"), vec!["part"]));

        assert!(view.nodes.iter().any(|node| node.id == "type.Vehicle.Car"));
        assert!(
            view.nodes
                .iter()
                .any(|node| node.id == "type.Vehicle.Engine")
        );
        assert!(view.edges.iter().any(|edge| {
            edge.source == "type.Vehicle.Car"
                && edge.target == "type.Vehicle.Engine"
                && edge.relation == "part"
        }));
        let part_edge = view
            .edges
            .iter()
            .find(|edge| edge.relation == "part")
            .expect("part edge should render");
        let part_symbol = view
            .symbols
            .iter()
            .find(|symbol| symbol.id == part_edge.symbol)
            .expect("part edge should have a symbol");
        assert_eq!(part_symbol.role, "edge");
        assert_eq!(
            part_symbol.source.as_deref(),
            Some("symbol.type_Vehicle_Car")
        );
        assert_eq!(
            part_symbol.target.as_deref(),
            Some("symbol.type_Vehicle_Engine")
        );
        assert_eq!(part_symbol.relation.as_deref(), Some("part"));
        assert_eq!(
            part_symbol
                .properties
                .get("route")
                .and_then(|value| value.as_str()),
            Some("orthogonal")
        );
        assert_eq!(
            part_symbol
                .properties
                .get("source_decoration")
                .and_then(|value| value.as_str()),
            Some("filled_diamond")
        );
        assert_eq!(
            part_symbol
                .properties
                .get("target_decoration")
                .and_then(|value| value.as_str()),
            Some("open_arrow")
        );
    }

    #[test]
    fn structure_diagram_validates_unknown_root() {
        let (graph, registry) = sample_graph();
        let error = render_diagram(
            &graph,
            &registry,
            structure_spec(Some("Vehicle::Missing"), vec!["owner"]),
        )
        .expect_err("unknown root should fail");

        assert_eq!(
            error,
            DiagramError::RootNotFound("Vehicle::Missing".to_string())
        );
    }

    #[test]
    fn structure_diagram_honors_include_library_filter() {
        let mut spec = structure_spec(Some("SysML::Systems::PartDefinition"), vec!["specializes"]);
        spec.query.include_libraries = true;
        spec.query.include_user_model = true;
        let with_libraries = render_sample(spec.clone());
        assert!(
            with_libraries
                .nodes
                .iter()
                .any(|node| node.id == "SysML::Systems::PartDefinition")
        );

        spec.query.include_libraries = false;
        let without_libraries = render_sample(spec);
        assert!(
            without_libraries
                .nodes
                .iter()
                .all(|node| node.id != "SysML::Systems::PartDefinition")
        );
    }

    #[test]
    fn structure_diagram_reports_edge_limit() {
        let mut spec = structure_spec(
            Some("state.Vehicle.DriveMode"),
            vec!["owner", "source", "target"],
        );
        spec.query.max_edges = 2;
        let view = render_sample(spec);

        assert_eq!(view.edges.len(), 2);
        assert!(
            view.warnings
                .iter()
                .any(|warning| warning.contains("Diagram edge limit reached"))
        );
    }

    #[test]
    fn activity_diagram_assigns_activity_symbol_roles() {
        let view = render_sample(DiagramSpecDto {
            version: 1,
            kind: DiagramKindDto::Activity,
            title: "Provide Power Activity".to_string(),
            description: None,
            root: Some("activity.Vehicle.ProvidePower".to_string()),
            query: DiagramQueryOptionsDto {
                relations: Vec::new(),
                direction: DiagramDirectionDto::Children,
                depth: 3,
                include_libraries: false,
                include_user_model: true,
                max_nodes: 350,
                max_edges: 900,
            },
            layout: DiagramLayoutOptionsDto::default(),
            style: DiagramStyleOptionsDto::default(),
        });

        let action = view
            .symbols
            .iter()
            .find(|symbol| symbol.element == "action.Vehicle.ProvidePower.ProportionPower")
            .expect("activity action should have a symbol");
        assert_eq!(action.role, "action");
        assert_eq!(
            action
                .properties
                .get("shape")
                .and_then(|value| value.as_str()),
            Some("action")
        );

        let flow = view
            .symbols
            .iter()
            .find(|symbol| symbol.relation.as_deref() == Some("object_flow"))
            .expect("activity object flow should have a symbol");
        assert_eq!(flow.role, "edge");
        assert_eq!(
            flow.properties
                .get("route")
                .and_then(|value| value.as_str()),
            Some("orthogonal")
        );
        assert_eq!(
            flow.properties
                .get("target_decoration")
                .and_then(|value| value.as_str()),
            Some("open_arrow")
        );
    }

    #[test]
    fn requirements_table_renders_requirement_rows() {
        let view = render_table_sample(TableSpecDto {
            version: 1,
            kind: TableKindDto::Requirements,
            title: "Requirements".to_string(),
            description: None,
            root: Some("pkg.Vehicle".to_string()),
            target_type: None,
            query: DiagramQueryOptionsDto {
                relations: vec!["owner".to_string()],
                direction: DiagramDirectionDto::Children,
                depth: 2,
                include_libraries: false,
                include_user_model: true,
                max_nodes: 350,
                max_edges: 900,
            },
            columns: Vec::new(),
        });

        assert_eq!(view.columns.len(), 5);
        let row = view
            .rows
            .iter()
            .find(|row| row.element == "req.Vehicle.SafeStart")
            .expect("requirement row should render");
        assert!(
            row.cells
                .iter()
                .any(|cell| { cell.key == "requirement_id" && cell.value == "REQ-001" })
        );
        assert!(
            row.cells
                .iter()
                .any(|cell| cell.key == "text" && cell.value.contains("unsafe starts"))
        );
    }

    #[test]
    fn view_document_round_trips_diagram_spec() {
        let document = ViewDocumentDto::diagram(structure_spec(Some("pkg.Vehicle"), vec!["owner"]));

        validate_view_document(&document).expect("document should validate");
        let json = serde_json::to_string_pretty(&document).unwrap();
        let decoded: ViewDocumentDto = serde_json::from_str(&json).unwrap();

        assert_eq!(decoded.schema, VIEW_SCHEMA);
        assert_eq!(decoded.version, VIEW_SPEC_VERSION);
        assert_eq!(decoded.kind, "diagram.structure");
        assert!(decoded.diagram.is_some());
        assert!(decoded.table.is_none());
        assert_eq!(decoded, document);
    }

    #[test]
    fn view_document_round_trips_table_spec() {
        let document = ViewDocumentDto::table(TableSpecDto {
            version: 1,
            kind: TableKindDto::Requirements,
            title: "Requirements".to_string(),
            description: None,
            root: Some("pkg.Vehicle".to_string()),
            target_type: None,
            query: DiagramQueryOptionsDto::default(),
            columns: vec![TableColumnSpecDto {
                key: "requirement_id".to_string(),
                label: "ID".to_string(),
                path: None,
            }],
        });

        validate_view_document(&document).expect("document should validate");
        let decoded: ViewDocumentDto =
            serde_json::from_str(&serde_json::to_string(&document).unwrap()).unwrap();

        assert_eq!(decoded.kind, "table");
        assert!(decoded.diagram.is_none());
        assert!(decoded.table.is_some());
        assert_eq!(decoded, document);
    }

    #[test]
    fn view_document_validation_rejects_mismatched_payload() {
        let mut document =
            ViewDocumentDto::diagram(structure_spec(Some("pkg.Vehicle"), vec!["owner"]));
        document.kind = "table".to_string();

        let diagnostics =
            validate_view_document(&document).expect_err("mismatched kind should fail");

        assert!(
            diagnostics
                .iter()
                .any(|diagnostic| diagnostic.code == "view.kind")
        );
    }

    #[test]
    fn view_document_validation_rejects_bad_table_columns() {
        let document = ViewDocumentDto::table(TableSpecDto {
            version: 1,
            kind: TableKindDto::Requirements,
            title: "Requirements".to_string(),
            description: None,
            root: None,
            target_type: None,
            query: DiagramQueryOptionsDto::default(),
            columns: vec![
                TableColumnSpecDto {
                    key: "id".to_string(),
                    label: "ID".to_string(),
                    path: None,
                },
                TableColumnSpecDto {
                    key: "id".to_string(),
                    label: String::new(),
                    path: None,
                },
            ],
        });

        let diagnostics =
            validate_view_document(&document).expect_err("invalid columns should fail");

        assert!(
            diagnostics
                .iter()
                .any(|diagnostic| { diagnostic.code == "view.table.column.key.duplicate" })
        );
        assert!(
            diagnostics
                .iter()
                .any(|diagnostic| diagnostic.code == "view.table.column.label")
        );
    }

    #[test]
    fn requirements_table_supports_attribute_path_columns() {
        let view = render_table_sample(TableSpecDto {
            version: 1,
            kind: TableKindDto::Requirements,
            title: "Requirements".to_string(),
            description: None,
            root: Some("pkg.Vehicle".to_string()),
            target_type: None,
            query: DiagramQueryOptionsDto {
                relations: vec!["owner".to_string()],
                direction: DiagramDirectionDto::Children,
                depth: 2,
                include_libraries: false,
                include_user_model: true,
                max_nodes: 350,
                max_edges: 900,
            },
            columns: vec![
                TableColumnSpecDto {
                    key: "id".to_string(),
                    label: "ID".to_string(),
                    path: Some("requirement_id".to_string()),
                },
                TableColumnSpecDto {
                    key: "owner_name".to_string(),
                    label: "Owner Name".to_string(),
                    path: Some("owner.declared_name".to_string()),
                },
            ],
        });

        let row = view.rows.first().expect("requirement row should render");
        assert!(
            row.cells
                .iter()
                .any(|cell| { cell.key == "id" && cell.value == "REQ-001" })
        );
        assert!(
            row.cells
                .iter()
                .any(|cell| { cell.key == "owner_name" && cell.value == "Vehicle" })
        );
    }

    #[test]
    fn requirements_table_supports_metadata_path_columns() {
        let view = render_table_sample(TableSpecDto {
            version: 1,
            kind: TableKindDto::Requirements,
            title: "Requirement Lifecycle".to_string(),
            description: None,
            root: Some("pkg.Vehicle".to_string()),
            target_type: None,
            query: DiagramQueryOptionsDto {
                relations: vec!["owner".to_string()],
                direction: DiagramDirectionDto::Children,
                depth: 2,
                include_libraries: false,
                include_user_model: true,
                max_nodes: 350,
                max_edges: 900,
            },
            columns: vec![
                TableColumnSpecDto {
                    key: "status".to_string(),
                    label: "Status".to_string(),
                    path: Some("metadata[RequirementLifecycle].status".to_string()),
                },
                TableColumnSpecDto {
                    key: "owner".to_string(),
                    label: "Owner".to_string(),
                    path: Some("metadata[RequirementLifecycle].owner".to_string()),
                },
                TableColumnSpecDto {
                    key: "review_date".to_string(),
                    label: "Review Date".to_string(),
                    path: Some("metadata[RequirementLifecycle].reviewDate".to_string()),
                },
            ],
        });

        let row = view.rows.first().expect("requirement row should render");
        assert!(
            row.cells
                .iter()
                .any(|cell| cell.key == "status" && cell.value == "approved")
        );
        assert!(
            row.cells
                .iter()
                .any(|cell| cell.key == "owner" && cell.value == "Safety Team")
        );
        assert!(
            row.cells
                .iter()
                .any(|cell| cell.key == "review_date" && cell.value == "2026-05-27")
        );
    }

    #[test]
    fn element_table_filters_by_type_and_subtypes() {
        let view = render_table_sample(TableSpecDto {
            version: 1,
            kind: TableKindDto::Elements,
            title: "Comments".to_string(),
            description: None,
            root: None,
            target_type: Some("Comment".to_string()),
            query: DiagramQueryOptionsDto::default(),
            columns: vec![
                TableColumnSpecDto {
                    key: "name".to_string(),
                    label: "Name".to_string(),
                    path: None,
                },
                TableColumnSpecDto {
                    key: "body".to_string(),
                    label: "Body".to_string(),
                    path: Some("body".to_string()),
                },
                TableColumnSpecDto {
                    key: "locale".to_string(),
                    label: "Locale".to_string(),
                    path: Some("locale".to_string()),
                },
            ],
        });

        assert!(
            view.rows
                .iter()
                .any(|row| row.element == "comment.Vehicle.Note")
        );
        assert!(
            view.rows
                .iter()
                .any(|row| row.element == "comment.Vehicle.LocalizedNote")
        );
        assert!(
            view.rows
                .iter()
                .all(|row| row.element.contains("Comment") || row.element.contains("comment."))
        );
        assert!(
            view.available_columns
                .iter()
                .any(|column| column.key == "body")
        );
        assert!(
            view.available_columns
                .iter()
                .any(|column| column.key == "locale")
        );
    }
}

fn default_true() -> bool {
    true
}

fn diagram_kind_name(kind: &DiagramKindDto) -> &'static str {
    match kind {
        DiagramKindDto::Structure => "structure",
        DiagramKindDto::Activity => "activity",
        DiagramKindDto::PackageTree => "package_tree",
        DiagramKindDto::CompositionGraph => "composition_graph",
        DiagramKindDto::ReferenceGraph => "reference_graph",
        DiagramKindDto::DependencyGraph => "dependency_graph",
        DiagramKindDto::MetatypeInstanceMap => "metatype_instance_map",
        DiagramKindDto::ImpactView => "impact_view",
        DiagramKindDto::PropertyInheritance => "property_inheritance",
        DiagramKindDto::ValidationView => "validation_view",
    }
}

fn value_type_label(value: &Value) -> &'static str {
    match value {
        Value::Null => "null",
        Value::Bool(_) => "boolean",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}
