use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::{Arc, OnceLock};

use mercurio_core::runtime::Runtime;
use mercurio_core::{
    AttributeWritePolicy, AuthoringProject, CapabilityRunStatus, CellKind, CellLanguage,
    CellOutput, CellOutputKind, CellRunReport, CellRunRequest, CellRunStatus, CommitMode,
    CommitResult, CommitStrategy, ContainerSelector, DslAnalysisRunRequest, DslAnalysisRunSpec,
    DslEngine, DslQueryRequest, DslQueryResult, ElementRef, ElementView, ForkElement, Graph,
    GraphScope, KirDocument, L2ExplorerRequestDto, MetamodelAttributeRegistry,
    MetatypeExplorerRequestDto, ModelFork, ModelSession, ModelWorkspace, Mutation,
    ProjectDescriptor, QualifiedName, SemanticChangeSet, SemanticEdit, SemanticMutation,
    SemanticTransaction, SessionError, TransactionOperation, WorkspaceSnapshot, WriteBackMode,
    WriteBackResult, collect_specialization_ancestors, default_language_profile, element_metatype,
    generate_python_wrappers, graph_view, l2_explorer_view, library_tree_view,
    metatype_explorer_view, model_metadata_view, resolve_project_descriptor_context, search_view,
};
use mercurio_simulation::run_analysis_case as run_sysml_analysis_case;
use mercurio_sysml::{
    StdlibLocator, SysmlModelForkExt, compile_sysml_text, compile_sysml_text_with_context,
    list_analysis_specs, load_authoring_project_from_sysml, load_sysml_baseline, parse_sysml,
    resolve_default_stdlib_locator,
};
use mercurio_view_model::{
    ElementDetailsDto, PartDto, element_details_from_graph, parts_from_graph,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyType};
use serde::{Deserialize, Serialize};

static DEFAULT_STDLIB_DOCUMENT: OnceLock<Result<KirDocument, String>> = OnceLock::new();
const PROJECT_DESCRIPTOR_FILE_NAME: &str = ".project.json";

#[pyclass(name = "WriteBackResult")]
#[derive(Debug, Clone)]
struct PyWriteBackResult {
    #[pyo3(get)]
    edited_files: BTreeMap<String, String>,
    #[pyo3(get)]
    changed_files: Vec<String>,
    #[pyo3(get)]
    changed_declarations: Vec<String>,
    #[pyo3(get)]
    mode: String,
    #[pyo3(get)]
    validation_ok: bool,
    #[pyo3(get)]
    validation_message: Option<String>,
}

#[pymethods]
impl PyWriteBackResult {
    fn __repr__(&self) -> String {
        format!(
            "WriteBackResult(changed_files={:?}, mode={:?}, validation_ok={})",
            self.changed_files, self.mode, self.validation_ok
        )
    }
}

#[pyclass(name = "SemanticModel")]
#[derive(Clone)]
struct PySemanticModel {
    document: Arc<KirDocument>,
    graph: Arc<Graph>,
    registry: Arc<MetamodelAttributeRegistry>,
}

#[pyclass(name = "PyWorkspace")]
#[derive(Clone)]
struct PyWorkspace {
    document: Arc<KirDocument>,
    graph: Arc<Graph>,
    registry: Arc<MetamodelAttributeRegistry>,
}

#[pymethods]
impl PyWorkspace {
    #[staticmethod]
    fn open(path: &str) -> PyResult<Self> {
        let document = compile_workspace_path(Path::new(path))?;
        let graph = Graph::from_document(document.clone())
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        let registry = MetamodelAttributeRegistry::build(&graph);
        Ok(Self {
            document: Arc::new(document),
            graph: Arc::new(graph),
            registry: Arc::new(registry),
        })
    }

    #[getter]
    fn stdlib_locator(&self) -> String {
        StdlibLocator::from_env()
            .unwrap_or_else(resolve_default_stdlib_locator)
            .as_uri()
    }

    fn model(&self) -> PyResult<String> {
        serde_json::to_string_pretty(self.document.as_ref())
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn graph(&self) -> PyResult<String> {
        serde_json::to_string_pretty(&self.graph.artifact())
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn parts(&self) -> Vec<PyPartRef> {
        parts_from_graph(&self.graph)
            .into_iter()
            .map(|inner| PyPartRef { inner })
            .collect()
    }

    fn element(&self, id: &str) -> Option<PyKirElement> {
        element_details_from_graph(&self.graph, id).map(|inner| PyKirElement { inner })
    }

    fn model_metadata_json(&self) -> PyResult<String> {
        model_metadata_json(&self.graph, &self.document)
    }

    #[pyo3(signature = (scope=None))]
    fn graph_view_json(&self, scope: Option<&str>) -> PyResult<String> {
        graph_view_json(&self.graph, scope)
    }

    fn search_json(&self, query: &str) -> PyResult<String> {
        search_json(&self.graph, query)
    }

    fn element_details_json(&self, element_id: &str) -> PyResult<String> {
        element_details_json(&self.graph, &self.registry, element_id)
    }

    fn l2_explorer_json(&self, request_json: &str) -> PyResult<String> {
        l2_explorer_json(&self.graph, request_json)
    }

    fn metatype_explorer_json(&self, request_json: &str) -> PyResult<String> {
        metatype_explorer_json(&self.graph, &self.registry, request_json)
    }

    fn library_tree_json(&self) -> PyResult<String> {
        library_tree_json(&self.graph)
    }

    fn compile(&self) -> PyResult<PySemanticModel> {
        py_semantic_model((*self.document).clone())
    }

    fn dsl_query_json(&self, source: &str) -> PyResult<String> {
        dsl_query_json(Arc::clone(&self.graph), source)
    }

    fn dsl_schema_json(&self) -> PyResult<String> {
        dsl_schema_json(&self.graph)
    }

    fn run_cell_json(&self, request_json: &str) -> PyResult<String> {
        run_cell_json(Arc::clone(&self.graph), request_json)
    }

    fn analysis_specs_json(&self) -> PyResult<String> {
        let runtime = Runtime::from_graph((*self.graph).clone())
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        let specs = list_analysis_specs(&runtime);
        serde_json::to_string(&specs).map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn analysis_run_json(&self, case_id: &str, run_id: &str) -> PyResult<String> {
        let runtime = Runtime::from_graph((*self.graph).clone())
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        let report = run_sysml_analysis_case(&runtime, case_id, run_id)
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        serde_json::to_string(&report).map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn list_analysis_cases(&self) -> PyResult<Vec<String>> {
        Err(PyValueError::new_err(
            "analysis cases are not available in the native read workspace yet; open with an HTTP sidecar executable for simulation",
        ))
    }

    fn run_analysis(&self, case_id: &str) -> PyResult<()> {
        Err(PyValueError::new_err(format!(
            "analysis case `{case_id}` is not available in the native read workspace yet"
        )))
    }
}

#[pyclass(name = "PyPartRef")]
#[derive(Debug, Clone)]
struct PyPartRef {
    inner: PartDto,
}

#[pymethods]
impl PyPartRef {
    #[getter]
    fn id(&self) -> &str {
        &self.inner.id
    }

    #[getter]
    fn name(&self) -> &str {
        &self.inner.name
    }

    #[getter]
    fn kind(&self) -> &str {
        &self.inner.kind
    }

    #[getter]
    fn element_kind(&self) -> &str {
        &self.inner.element_kind
    }

    #[getter]
    fn parent_id(&self) -> Option<&str> {
        self.inner.parent_id.as_deref()
    }

    #[getter]
    fn depth(&self) -> u32 {
        self.inner.depth
    }

    fn attr(&self, name: &str) -> PyResult<Option<String>> {
        self.inner
            .attributes
            .get(name)
            .map(serde_json::to_string)
            .transpose()
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner).map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }
}

#[pyclass(name = "PyKirElement")]
#[derive(Debug, Clone)]
struct PyKirElement {
    inner: ElementDetailsDto,
}

#[pymethods]
impl PyKirElement {
    #[getter]
    fn id(&self) -> &str {
        &self.inner.id
    }

    #[getter]
    fn label(&self) -> &str {
        &self.inner.label
    }

    #[getter]
    fn kind(&self) -> &str {
        &self.inner.kind
    }

    #[getter]
    fn layer(&self) -> u8 {
        self.inner.layer
    }

    fn json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(&self.inner)
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }
}

#[pymethods]
impl PySemanticModel {
    #[classmethod]
    fn from_kir_json(_cls: &Bound<'_, PyType>, content: String) -> PyResult<Self> {
        let document = KirDocument::from_str(&content)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        py_semantic_model(document)
    }

    fn element(&self, element_id: String) -> PyResult<PyElementView> {
        let node_id = self
            .graph
            .node_id(&element_id)
            .ok_or_else(|| PyValueError::new_err(format!("element not found: {element_id}")))?;
        Ok(PyElementView {
            graph: self.graph.clone(),
            registry: self.registry.clone(),
            node_id,
        })
    }

    fn elements(&self) -> Vec<PyElementView> {
        self.graph
            .elements()
            .iter()
            .map(|element| PyElementView {
                graph: self.graph.clone(),
                registry: self.registry.clone(),
                node_id: element.id,
            })
            .collect()
    }

    fn element_count(&self) -> usize {
        self.document.elements.len()
    }

    fn semantic_snapshot_json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(&semantic_snapshot_rows_with_graph(
            &self.document,
            Some(&self.graph),
        ))
        .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn generate_python_wrappers(&self, module_name: String) -> PyResult<BTreeMap<String, String>> {
        let profile =
            default_language_profile().map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(generate_python_wrappers(&self.document, &profile, &module_name).files)
    }

    fn model_metadata_json(&self) -> PyResult<String> {
        model_metadata_json(&self.graph, &self.document)
    }

    #[pyo3(signature = (scope=None))]
    fn graph_view_json(&self, scope: Option<&str>) -> PyResult<String> {
        graph_view_json(&self.graph, scope)
    }

    fn search_json(&self, query: &str) -> PyResult<String> {
        search_json(&self.graph, query)
    }

    fn element_details_json(&self, element_id: &str) -> PyResult<String> {
        element_details_json(&self.graph, &self.registry, element_id)
    }

    fn l2_explorer_json(&self, request_json: &str) -> PyResult<String> {
        l2_explorer_json(&self.graph, request_json)
    }

    fn metatype_explorer_json(&self, request_json: &str) -> PyResult<String> {
        metatype_explorer_json(&self.graph, &self.registry, request_json)
    }

    fn library_tree_json(&self) -> PyResult<String> {
        library_tree_json(&self.graph)
    }

    fn dsl_query_json(&self, source: &str) -> PyResult<String> {
        dsl_query_json(Arc::clone(&self.graph), source)
    }

    fn dsl_schema_json(&self) -> PyResult<String> {
        dsl_schema_json(&self.graph)
    }

    fn run_cell_json(&self, request_json: &str) -> PyResult<String> {
        run_cell_json(Arc::clone(&self.graph), request_json)
    }

    fn preview_transaction_json(&self, request_json: &str) -> PyResult<String> {
        preview_transaction_json(request_json)
    }

    fn __repr__(&self) -> String {
        format!("SemanticModel(elements={})", self.document.elements.len())
    }
}

#[pyclass(name = "ElementView")]
#[derive(Clone)]
struct PyElementView {
    graph: Arc<Graph>,
    registry: Arc<MetamodelAttributeRegistry>,
    node_id: mercurio_core::NodeId,
}

#[pymethods]
impl PyElementView {
    #[getter]
    fn id(&self) -> PyResult<String> {
        Ok(self.view()?.id().to_string())
    }

    #[getter]
    fn kind(&self) -> PyResult<String> {
        Ok(self.view()?.kind().to_string())
    }

    #[getter]
    fn layer(&self) -> PyResult<u8> {
        Ok(self.view()?.layer())
    }

    fn metatype_id(&self) -> PyResult<Option<String>> {
        Ok(self.view()?.metatype().map(|summary| summary.id))
    }

    fn get_json(&self, name: String) -> PyResult<Option<String>> {
        self.view()?
            .get(&name)
            .map(serde_json::to_string)
            .transpose()
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn effective_json(&self, name: String) -> PyResult<Option<String>> {
        self.view()?
            .effective(&name)
            .map(|value| serde_json::to_string(&value))
            .transpose()
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn get_str(&self, name: String) -> PyResult<Option<String>> {
        Ok(self.view()?.get_str(&name).map(str::to_string))
    }

    fn effective_str(&self, name: String) -> PyResult<Option<String>> {
        Ok(self
            .view()?
            .effective(&name)
            .and_then(|value| value.as_str().map(str::to_string)))
    }

    fn references(&self, relation: String) -> PyResult<Vec<PyElementView>> {
        Ok(self
            .view()?
            .references(&relation)
            .into_iter()
            .map(|view| PyElementView {
                graph: self.graph.clone(),
                registry: self.registry.clone(),
                node_id: view.node_id(),
            })
            .collect())
    }

    fn attribute_names(&self) -> PyResult<Vec<String>> {
        Ok(self
            .view()?
            .attributes()
            .map(|query| query.rows.into_iter().map(|row| row.name).collect())
            .unwrap_or_default())
    }

    fn __repr__(&self) -> PyResult<String> {
        let view = self.view()?;
        Ok(format!(
            "ElementView(id={:?}, kind={:?})",
            view.id(),
            view.kind()
        ))
    }
}

#[pyclass(name = "ForkElement")]
#[derive(Debug, Clone)]
struct PyForkElement {
    inner: ForkElement,
}

#[pymethods]
impl PyForkElement {
    #[getter]
    fn id(&self) -> String {
        self.inner.id.clone()
    }

    #[getter]
    fn qualified_name(&self) -> String {
        self.inner.qualified_name.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "ForkElement(id={:?}, qualified_name={:?})",
            self.inner.id, self.inner.qualified_name
        )
    }
}

#[pyclass(name = "CommitResult")]
#[derive(Debug, Clone)]
struct PyCommitResult {
    #[pyo3(get)]
    mode: String,
    #[pyo3(get)]
    strategy_used: String,
    #[pyo3(get)]
    base_revision: String,
    #[pyo3(get)]
    new_revision: String,
    #[pyo3(get)]
    changed_files: Vec<String>,
    #[pyo3(get)]
    edited_files: BTreeMap<String, String>,
    #[pyo3(get)]
    generated_elements: usize,
}

#[pymethods]
impl PyCommitResult {
    fn __repr__(&self) -> String {
        format!(
            "CommitResult(mode={:?}, strategy_used={:?}, changed_files={:?})",
            self.mode, self.strategy_used, self.changed_files
        )
    }
}

#[pyclass(name = "ModelWorkspace")]
#[derive(Clone)]
struct PyModelWorkspace {
    inner: ModelWorkspace,
}

#[pymethods]
impl PyModelWorkspace {
    #[classmethod]
    fn empty(_cls: &Bound<'_, PyType>) -> PyResult<Self> {
        let document = KirDocument {
            metadata: BTreeMap::new(),
            elements: Vec::new(),
        };
        Ok(Self {
            inner: ModelWorkspace::new(WorkspaceSnapshot::new(document).map_err(session_error)?),
        })
    }

    #[classmethod]
    fn from_kir_json(_cls: &Bound<'_, PyType>, content: String) -> PyResult<Self> {
        let document = KirDocument::from_str(&content)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(Self {
            inner: ModelWorkspace::new(WorkspaceSnapshot::new(document).map_err(session_error)?),
        })
    }

    #[classmethod]
    fn from_sysml_files(
        _cls: &Bound<'_, PyType>,
        files: BTreeMap<String, String>,
    ) -> PyResult<Self> {
        let project = load_authoring_project_from_sysml(files).map_err(authoring_error)?;
        Ok(Self {
            inner: ModelWorkspace::new(
                WorkspaceSnapshot::from_authoring_project(project).map_err(session_error)?,
            ),
        })
    }

    fn session(&self) -> PyModelSession {
        PyModelSession {
            inner: self.inner.session(),
        }
    }

    fn revision(&self) -> String {
        self.inner.current_snapshot().revision.fingerprint.clone()
    }
}

#[pyclass(name = "ModelSession")]
#[derive(Clone)]
struct PyModelSession {
    inner: ModelSession,
}

#[pymethods]
impl PyModelSession {
    fn fork(&self, label: String) -> PyModelFork {
        PyModelFork {
            inner: self.inner.fork(label),
        }
    }
}

#[pyclass(name = "ModelFork")]
struct PyModelFork {
    inner: ModelFork,
}

#[pymethods]
impl PyModelFork {
    #[pyo3(signature = (qualified_name, owner=None))]
    fn package(
        &mut self,
        qualified_name: String,
        owner: Option<&PyForkElement>,
    ) -> PyResult<PyForkElement> {
        self.inner
            .package(qualified_name, owner.map(|element| &element.inner))
            .map(py_fork_element)
            .map_err(session_error)
    }

    fn requirement(
        &mut self,
        owner: &PyForkElement,
        name: String,
        text: String,
    ) -> PyResult<PyForkElement> {
        self.inner
            .sysml_requirement(&owner.inner, name, text)
            .map(py_fork_element)
            .map_err(session_error)
    }

    fn requirements(
        &mut self,
        owner: &PyForkElement,
        items: Vec<(String, String)>,
    ) -> PyResult<Vec<PyForkElement>> {
        items
            .into_iter()
            .map(|(name, text)| {
                self.inner
                    .sysml_requirement(&owner.inner, name, text)
                    .map(py_fork_element)
                    .map_err(session_error)
            })
            .collect()
    }

    #[pyo3(signature = (owner, name, ty=None))]
    fn part(
        &mut self,
        owner: &PyForkElement,
        name: String,
        ty: Option<String>,
    ) -> PyResult<PyForkElement> {
        self.inner
            .sysml_part(&owner.inner, name, ty)
            .map(py_fork_element)
            .map_err(session_error)
    }

    fn rename_declaration(&mut self, element: String, new_name: String) -> PyResult<()> {
        self.inner
            .rename_declaration(element, new_name)
            .map_err(session_error)
    }

    fn validate(&self) -> PyResult<()> {
        self.inner.validate().map_err(session_error)
    }

    fn added_element_count(&self) -> usize {
        self.inner.overlay().added_elements.len()
    }

    #[pyo3(signature = (mode="preserve_source"))]
    fn commit(&self, mode: &str) -> PyResult<PyCommitResult> {
        self.inner
            .commit(parse_commit_mode(mode)?)
            .map(py_commit_result)
            .map_err(session_error)
    }
}

impl PyElementView {
    fn view(&self) -> PyResult<ElementView<'_>> {
        ElementView::new(&self.graph, &self.registry, self.node_id)
            .ok_or_else(|| PyRuntimeError::new_err("stale element view"))
    }
}

#[pyclass(name = "ModelBuilder")]
struct PyModelBuilder {
    project: AuthoringProject,
    library_context_document: Option<KirDocument>,
    validate_each_mutation: bool,
    pending_changed_files: BTreeSet<String>,
    pending_changed_declarations: BTreeSet<String>,
}

#[pymethods]
impl PyModelBuilder {
    #[new]
    #[pyo3(signature = (validate_each_mutation=true))]
    fn new(validate_each_mutation: bool) -> PyResult<Self> {
        Ok(Self {
            project: load_authoring_project_from_sysml(BTreeMap::new()).map_err(authoring_error)?,
            library_context_document: None,
            validate_each_mutation,
            pending_changed_files: BTreeSet::new(),
            pending_changed_declarations: BTreeSet::new(),
        })
    }

    #[classmethod]
    #[pyo3(signature = (files, validate_each_mutation=true))]
    fn from_sysml_files(
        _cls: &Bound<'_, PyType>,
        files: BTreeMap<String, String>,
        validate_each_mutation: bool,
    ) -> PyResult<Self> {
        let project = load_authoring_project_from_sysml(files).map_err(authoring_error)?;
        Ok(Self {
            project,
            library_context_document: None,
            validate_each_mutation,
            pending_changed_files: BTreeSet::new(),
            pending_changed_declarations: BTreeSet::new(),
        })
    }

    #[classmethod]
    #[pyo3(signature = (path, validate_each_mutation=true))]
    fn from_project(
        _cls: &Bound<'_, PyType>,
        path: PathBuf,
        validate_each_mutation: bool,
    ) -> PyResult<Self> {
        let sources = project_sources_for_open_path(&path)?;
        let project = load_authoring_project_from_sysml(sources.files).map_err(authoring_error)?;
        Ok(Self {
            project,
            library_context_document: sources.library_context_document,
            validate_each_mutation,
            pending_changed_files: BTreeSet::new(),
            pending_changed_declarations: BTreeSet::new(),
        })
    }

    fn add_package(&mut self, target_file: String, name: String) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::AddPackage {
            target_file,
            package_name: qname(&name),
        })
    }

    #[pyo3(signature = (target_file, path, package_name=None))]
    fn add_import(
        &mut self,
        target_file: String,
        path: String,
        package_name: Option<String>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::AddImport {
            target_file,
            package_name: package_name.as_deref().map(qname),
            path: qname(&path),
        })
    }

    #[pyo3(signature = (target_file, path, package_name=None))]
    fn remove_import(
        &mut self,
        target_file: String,
        path: String,
        package_name: Option<String>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::RemoveImport {
            target_file,
            package_name: package_name.as_deref().map(qname),
            path: qname(&path),
        })
    }

    #[pyo3(signature = (container, keyword, name, specializes=None))]
    fn add_definition(
        &mut self,
        container: String,
        keyword: String,
        name: String,
        specializes: Option<Vec<String>>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::AddDefinition {
            container: selector(&container),
            keyword,
            name,
            specializes: qnames(specializes),
        })
    }

    fn remove_declaration(&mut self, element: String) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::RemoveDeclaration {
            qualified_name: qname(&element),
        })
    }

    fn update_specializations(
        &mut self,
        element: String,
        specializes: Vec<String>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::UpdateSpecializations {
            qualified_name: qname(&element),
            specializes: qnames(Some(specializes)),
        })
    }

    fn add_relationship(
        &mut self,
        container: String,
        kind: String,
        source: String,
        target: String,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::AddRelationship {
            container: selector(&container),
            kind,
            source: qname(&source),
            target: qname(&target),
        })
    }

    #[pyo3(signature = (element, metadata_type, properties=None))]
    fn add_metadata_annotation(
        &mut self,
        element: String,
        metadata_type: String,
        properties: Option<BTreeMap<String, String>>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::AddMetadataAnnotation {
            element: qname(&element),
            metadata_type,
            properties: properties.unwrap_or_default(),
        })
    }

    #[pyo3(signature = (container, keyword, name, ty=None, specializes=None))]
    fn add_usage(
        &mut self,
        container: String,
        keyword: String,
        name: String,
        ty: Option<String>,
        specializes: Option<Vec<String>>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::AddUsage {
            container: selector(&container),
            keyword,
            name,
            ty: ty.as_deref().map(qname),
            specializes: qnames(specializes),
        })
    }

    fn rename(&mut self, element: String, new_name: String) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::RenameDeclaration {
            qualified_name: qname(&element),
            new_name,
        })
    }

    #[pyo3(signature = (element, ty=None))]
    fn set_usage_type(
        &mut self,
        element: String,
        ty: Option<String>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::UpdateUsageType {
            qualified_name: qname(&element),
            ty: ty.as_deref().map(qname),
        })
    }

    #[pyo3(signature = (element, expression=None))]
    fn set_expression(
        &mut self,
        element: String,
        expression: Option<String>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::SetExpression {
            qualified_name: qname(&element),
            expression,
        })
    }

    fn set_attribute(
        &mut self,
        element: String,
        attribute: String,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_semantic_edit_and_write_back(SemanticEdit::SetAttribute {
            element: qname(&element),
            attribute,
            value: py_value_to_json(value)?,
            policy: AttributeWritePolicy::UpsertDirect,
        })
    }

    fn add_attribute_value(
        &mut self,
        element: String,
        attribute: String,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_semantic_edit_and_write_back(SemanticEdit::AddAttributeValue {
            element: qname(&element),
            attribute,
            value: py_value_to_json(value)?,
            policy: AttributeWritePolicy::UpsertDirect,
        })
    }

    fn remove_attribute_value(
        &mut self,
        element: String,
        attribute: String,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_semantic_edit_and_write_back(SemanticEdit::RemoveAttributeValue {
            element: qname(&element),
            attribute,
            value: py_value_to_json(value)?,
            policy: AttributeWritePolicy::UpsertDirect,
        })
    }

    fn clear_attribute(
        &mut self,
        element: String,
        attribute: String,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_semantic_edit_and_write_back(SemanticEdit::ClearAttribute {
            element: qname(&element),
            attribute,
            policy: AttributeWritePolicy::UpsertDirect,
        })
    }

    fn move_declaration(
        &mut self,
        element: String,
        destination: String,
    ) -> PyResult<PyWriteBackResult> {
        self.apply_and_write_back(Mutation::MoveDeclaration {
            qualified_name: qname(&element),
            destination: selector(&destination),
        })
    }

    fn render_file(&self, path: String) -> PyResult<String> {
        self.project.render_new_file(&path).map_err(authoring_error)
    }

    fn files(&self) -> Vec<String> {
        self.project
            .files()
            .map(|(path, _)| path.to_string())
            .collect()
    }

    fn rendered_files(&self) -> PyResult<BTreeMap<String, String>> {
        let mut rendered = BTreeMap::new();
        for (path, _) in self.project.files() {
            rendered.insert(
                path.to_string(),
                self.project
                    .render_new_file(path)
                    .map_err(authoring_error)?,
            );
        }
        Ok(rendered)
    }

    fn compile_json(&self) -> PyResult<String> {
        let document = self.compile_document()?;
        serde_json::to_string_pretty(&document)
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))
    }

    fn compile_model(&self) -> PyResult<PySemanticModel> {
        py_semantic_model(self.compile_document()?)
    }

    fn validate(&mut self) -> PyResult<PyWriteBackResult> {
        let changed_files = if self.pending_changed_files.is_empty() {
            self.project
                .files()
                .map(|(path, _)| path.to_string())
                .collect::<BTreeSet<_>>()
        } else {
            self.pending_changed_files.clone()
        };
        let changed_declarations = self
            .pending_changed_declarations
            .iter()
            .cloned()
            .collect::<Vec<_>>();
        let write_back = self
            .project
            .write_back_changed_files_and_update(&changed_files)
            .map_err(authoring_error)?;
        self.pending_changed_files.clear();
        self.pending_changed_declarations.clear();
        Ok(py_write_back_result(
            write_back,
            changed_files.into_iter().collect(),
            changed_declarations,
        ))
    }

    #[pyo3(signature = (directory, result_name=None))]
    fn write_handoff(&self, directory: PathBuf, result_name: Option<String>) -> PyResult<PathBuf> {
        let rendered = self.rendered_files()?;
        std::fs::create_dir_all(&directory).map_err(io_error)?;
        let files_dir = directory.join("files");
        std::fs::create_dir_all(&files_dir).map_err(io_error)?;

        let mut changed_files = Vec::new();
        for (path, content) in &rendered {
            let output_path = files_dir.join(path);
            if let Some(parent) = output_path.parent() {
                std::fs::create_dir_all(parent).map_err(io_error)?;
            }
            write_atomic(&output_path, content)?;
            changed_files.push(format!("files/{}", path.replace('\\', "/")));
        }

        let result_path = directory.join(result_name.unwrap_or_else(|| "result.json".to_string()));
        let primary_file = changed_files.first().cloned();
        let result = serde_json::json!({
            "status": "ok",
            "changed_files": changed_files,
            "primary_file": primary_file,
            "diagnostics": []
        });
        let result_text = serde_json::to_string_pretty(&result)
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        write_atomic(&result_path, &result_text)?;
        Ok(result_path)
    }

    fn __repr__(&self) -> String {
        format!(
            "ModelBuilder(files={:?}, validate_each_mutation={})",
            self.files(),
            self.validate_each_mutation
        )
    }
}

impl PyModelBuilder {
    fn apply_and_write_back(&mut self, mutation: Mutation) -> PyResult<PyWriteBackResult> {
        let result = self
            .project
            .apply_mutation(mutation)
            .map_err(authoring_error)?;
        let changed_files = result.changed_files.iter().cloned().collect::<Vec<_>>();
        let changed_declarations = result
            .changed_declarations
            .iter()
            .cloned()
            .collect::<Vec<_>>();
        if !self.validate_each_mutation {
            self.pending_changed_files
                .extend(result.changed_files.iter().cloned());
            self.pending_changed_declarations
                .extend(result.changed_declarations.iter().cloned());
            return self.deferred_write_back_result(changed_files, changed_declarations);
        }
        let write_back = self
            .project
            .write_back_mutation(&result)
            .map_err(authoring_error)?;
        Ok(py_write_back_result(
            write_back,
            changed_files,
            changed_declarations,
        ))
    }

    fn apply_semantic_edit_and_write_back(
        &mut self,
        edit: SemanticEdit,
    ) -> PyResult<PyWriteBackResult> {
        let result = self
            .project
            .apply_semantic_edit(edit)
            .map_err(authoring_error)?;
        let changed_files = result.changed_files.iter().cloned().collect::<Vec<_>>();
        let changed_declarations = result
            .changed_declarations
            .iter()
            .cloned()
            .collect::<Vec<_>>();
        if !self.validate_each_mutation {
            self.pending_changed_files
                .extend(result.changed_files.iter().cloned());
            self.pending_changed_declarations
                .extend(result.changed_declarations.iter().cloned());
            return self.deferred_write_back_result(changed_files, changed_declarations);
        }
        let write_back = self
            .project
            .write_back_mutation(&result)
            .map_err(authoring_error)?;
        Ok(py_write_back_result(
            write_back,
            changed_files,
            changed_declarations,
        ))
    }

    fn compile_document(&self) -> PyResult<KirDocument> {
        let rendered = self.rendered_files()?;
        if let Some(library_context) = &self.library_context_document {
            return compile_sysml_files_with_context(rendered, library_context);
        }
        compile_sysml_files_with_context(rendered, default_stdlib_document()?)
    }

    fn deferred_write_back_result(
        &self,
        changed_files: Vec<String>,
        changed_declarations: Vec<String>,
    ) -> PyResult<PyWriteBackResult> {
        let mut edited_files = BTreeMap::new();
        for path in &changed_files {
            edited_files.insert(
                path.clone(),
                self.project
                    .render_new_file(path)
                    .map_err(authoring_error)?,
            );
        }
        Ok(PyWriteBackResult {
            edited_files,
            changed_files,
            changed_declarations,
            mode: "deferred".to_string(),
            validation_ok: true,
            validation_message: Some(
                "validation deferred; call validate() to compile and round-trip check".to_string(),
            ),
        })
    }
}

fn default_stdlib_document() -> PyResult<&'static KirDocument> {
    DEFAULT_STDLIB_DOCUMENT
        .get_or_init(|| load_sysml_baseline().map_err(|err| err.to_string()))
        .as_ref()
        .map_err(|err| PyRuntimeError::new_err(err.clone()))
}

struct ProjectSources {
    files: BTreeMap<String, String>,
    library_context_document: Option<KirDocument>,
}

fn compile_workspace_path(path: &Path) -> PyResult<KirDocument> {
    if path.is_file()
        && path.file_name().and_then(|value| value.to_str()) != Some(PROJECT_DESCRIPTOR_FILE_NAME)
    {
        let source = std::fs::read_to_string(path).map_err(io_error)?;
        return compile_sysml_text(
            &source,
            &path.display().to_string(),
            default_stdlib_document()?,
        )
        .map_err(|err| PyValueError::new_err(err.to_string()));
    }

    let sources = project_sources_for_open_path(path)?;
    if sources.files.is_empty() {
        return Err(PyValueError::new_err(format!(
            "workspace contains no .sysml files: {}",
            path.display()
        )));
    }
    if let Some(library_context) = sources.library_context_document {
        return compile_sysml_files_with_context(sources.files, &library_context);
    }
    compile_sysml_files_with_context(sources.files, default_stdlib_document()?)
}

fn project_sources_for_open_path(path: &Path) -> PyResult<ProjectSources> {
    if path.is_file() {
        if path.file_name().and_then(|value| value.to_str()) == Some(PROJECT_DESCRIPTOR_FILE_NAME) {
            return project_sources_from_descriptor(path);
        }
        let source = std::fs::read_to_string(path).map_err(io_error)?;
        let file_name = path
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or("model.sysml")
            .to_string();
        return Ok(ProjectSources {
            files: BTreeMap::from([(file_name, source)]),
            library_context_document: None,
        });
    }

    if !path.is_dir() {
        return Err(PyValueError::new_err(format!(
            "workspace path does not exist: {}",
            path.display()
        )));
    }

    if let Some(descriptor_path) = find_project_descriptor(path) {
        return project_sources_from_descriptor(&descriptor_path);
    }

    let mut files = BTreeMap::new();
    collect_sysml_files(path, path, &mut files)?;
    Ok(ProjectSources {
        files,
        library_context_document: None,
    })
}

fn project_sources_from_descriptor(descriptor_path: &Path) -> PyResult<ProjectSources> {
    let root = descriptor_path
        .parent()
        .ok_or_else(|| PyValueError::new_err("project descriptor has no parent directory"))?;
    let content = std::fs::read_to_string(descriptor_path).map_err(io_error)?;
    let descriptor: ProjectDescriptor =
        serde_json::from_str(&content).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let files = project_source_files(root, Some(&descriptor))?;
    let context = resolve_project_descriptor_context(descriptor_path)
        .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
    let library_context_document = if context.library_context_document.elements.is_empty() {
        None
    } else {
        Some(context.library_context_document)
    };
    Ok(ProjectSources {
        files,
        library_context_document,
    })
}

fn project_source_files(
    root: &Path,
    descriptor: Option<&ProjectDescriptor>,
) -> PyResult<BTreeMap<String, String>> {
    let mut files = BTreeMap::new();
    if let Some(descriptor) = descriptor {
        if !descriptor.model.entrypoints.is_empty() {
            for entrypoint in &descriptor.model.entrypoints {
                collect_sysml_path(root, &root.join(entrypoint), &mut files)?;
            }
            return Ok(files);
        }
        if !descriptor.model.source_roots.is_empty() {
            for source_root in &descriptor.model.source_roots {
                collect_sysml_path(root, &root.join(source_root), &mut files)?;
            }
            return Ok(files);
        }
    }
    collect_sysml_files(root, root, &mut files)?;
    Ok(files)
}

fn compile_sysml_files_with_context(
    files: BTreeMap<String, String>,
    library_context: &KirDocument,
) -> PyResult<KirDocument> {
    let mut context_modules = Vec::new();
    for source in files.values() {
        context_modules
            .push(parse_sysml(source).map_err(|err| PyValueError::new_err(err.to_string()))?);
    }

    let mut documents = Vec::new();
    for (path, content) in files {
        documents.push(
            compile_sysml_text_with_context(&content, &path, &context_modules, library_context)
                .map_err(|err| PyValueError::new_err(err.to_string()))?,
        );
    }
    KirDocument::merge(documents).map_err(|err| PyRuntimeError::new_err(err.to_string()))
}

fn find_project_descriptor(start: &Path) -> Option<PathBuf> {
    let mut current = start.to_path_buf();
    loop {
        let candidate = current.join(PROJECT_DESCRIPTOR_FILE_NAME);
        if candidate.is_file() {
            return Some(candidate);
        }
        if !current.pop() {
            return None;
        }
    }
}

fn collect_sysml_path(
    root: &Path,
    path: &Path,
    files: &mut BTreeMap<String, String>,
) -> PyResult<()> {
    if path.is_dir() {
        return collect_sysml_files(root, path, files);
    }
    if !path.is_file() {
        return Err(PyValueError::new_err(format!(
            "project source path does not exist: {}",
            path.display()
        )));
    }
    if path.extension().and_then(|value| value.to_str()) != Some("sysml") {
        return Ok(());
    }
    let relative = path
        .strip_prefix(root)
        .map_err(|err| PyRuntimeError::new_err(err.to_string()))?
        .to_string_lossy()
        .replace('\\', "/");
    let source = std::fs::read_to_string(path).map_err(io_error)?;
    files.insert(relative, source);
    Ok(())
}

fn collect_sysml_files(
    root: &Path,
    current: &Path,
    files: &mut BTreeMap<String, String>,
) -> PyResult<()> {
    for entry in std::fs::read_dir(current).map_err(io_error)? {
        let entry = entry.map_err(io_error)?;
        let path = entry.path();
        if path.is_dir() {
            collect_sysml_files(root, &path, files)?;
            continue;
        }
        collect_sysml_path(root, &path, files)?;
    }
    Ok(())
}

fn py_semantic_model(document: KirDocument) -> PyResult<PySemanticModel> {
    let graph = Graph::from_document(document.clone())
        .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
    let registry = MetamodelAttributeRegistry::build(&graph);
    Ok(PySemanticModel {
        document: Arc::new(document),
        graph: Arc::new(graph),
        registry: Arc::new(registry),
    })
}

fn native_dsl_engine() -> DslEngine {
    DslEngine::with_extensions(vec![mercurio_sysml::sysml_dsl_extension()])
}

fn dsl_query_json(graph: Arc<Graph>, source: &str) -> PyResult<String> {
    let result = native_dsl_engine()
        .execute_query(
            graph,
            DslQueryRequest {
                script: source.to_string(),
                script_name: None,
                limits: None,
            },
        )
        .map(|report| report.result)
        .map_err(|err| PyValueError::new_err(err.to_string()))?;
    serde_json::to_string(&result).map_err(|err| PyRuntimeError::new_err(err.to_string()))
}

fn dsl_schema_json(graph: &Graph) -> PyResult<String> {
    let schema = native_dsl_engine().schema_for(graph);
    serde_json::to_string(&schema).map_err(|err| PyRuntimeError::new_err(err.to_string()))
}

fn model_metadata_json(graph: &Graph, document: &KirDocument) -> PyResult<String> {
    to_json_string(&model_metadata_view(graph, document))
}

fn graph_view_json(graph: &Graph, scope: Option<&str>) -> PyResult<String> {
    to_json_string(&graph_view(graph, GraphScope::from_query(scope)))
}

fn search_json(graph: &Graph, query: &str) -> PyResult<String> {
    to_json_string(&search_view(graph, query))
}

fn element_details_json(
    graph: &Graph,
    registry: &MetamodelAttributeRegistry,
    element_id: &str,
) -> PyResult<String> {
    let details = mercurio_core::element_details(graph, registry, element_id)
        .ok_or_else(|| PyValueError::new_err(format!("element not found: {element_id}")))?;
    to_json_string(&details)
}

fn l2_explorer_json(graph: &Graph, request_json: &str) -> PyResult<String> {
    let request: L2ExplorerRequestDto =
        serde_json::from_str(request_json).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let view = l2_explorer_view(graph, &request)
        .ok_or_else(|| PyValueError::new_err(format!("element not found: {}", request.seed_id)))?;
    to_json_string(&view)
}

fn metatype_explorer_json(
    graph: &Graph,
    registry: &MetamodelAttributeRegistry,
    request_json: &str,
) -> PyResult<String> {
    let request: MetatypeExplorerRequestDto =
        serde_json::from_str(request_json).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let view = metatype_explorer_view(graph, registry, &request)
        .ok_or_else(|| PyValueError::new_err(format!("element not found: {}", request.seed_id)))?;
    to_json_string(&view)
}

fn library_tree_json(graph: &Graph) -> PyResult<String> {
    to_json_string(&library_tree_view(graph))
}

fn to_json_string<T: Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|err| PyRuntimeError::new_err(err.to_string()))
}

#[derive(Debug, Deserialize)]
struct PyTransactionPreviewRequest {
    label: String,
    #[serde(default)]
    actions: Vec<PyTransactionAction>,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
enum PyTransactionAction {
    RenameDeclaration {
        element: String,
        new_name: String,
    },
    SetAttribute {
        element: String,
        attribute: String,
        value: serde_json::Value,
    },
}

fn preview_transaction_json(request_json: &str) -> PyResult<String> {
    let request: PyTransactionPreviewRequest =
        serde_json::from_str(request_json).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let actions = request
        .actions
        .into_iter()
        .map(py_transaction_action_to_mutation)
        .collect::<Vec<_>>();
    let operations = if actions.is_empty() {
        Vec::new()
    } else {
        vec![TransactionOperation::change_set(SemanticChangeSet::new(
            format!("{} change set 1", request.label),
            actions,
        ))]
    };
    let transaction = SemanticTransaction::new(request.label, None, operations);
    to_json_string(&transaction.preview_report(Default::default()))
}

fn py_transaction_action_to_mutation(action: PyTransactionAction) -> SemanticMutation {
    match action {
        PyTransactionAction::RenameDeclaration { element, new_name } => {
            SemanticMutation::RenameDeclaration {
                element: ElementRef::new(element),
                new_name,
            }
        }
        PyTransactionAction::SetAttribute {
            element,
            attribute,
            value,
        } => SemanticMutation::SetAttribute {
            element: ElementRef::new(element),
            attribute,
            value,
        },
    }
}

fn run_cell_json(graph: Arc<Graph>, request_json: &str) -> PyResult<String> {
    let request: CellRunRequest =
        serde_json::from_str(request_json).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let report = run_cell_on_graph(graph, request)?;
    serde_json::to_string(&report).map_err(|err| PyRuntimeError::new_err(err.to_string()))
}

fn run_cell_on_graph(graph: Arc<Graph>, request: CellRunRequest) -> PyResult<CellRunReport> {
    let cell_id = request
        .cell_id
        .clone()
        .unwrap_or_else(|| default_cell_id(&request));
    match (&request.kind, request.language.as_ref()) {
        (CellKind::Query, None | Some(CellLanguage::MercurioDsl)) => {
            let result = native_dsl_engine()
                .execute_query(
                    graph,
                    DslQueryRequest {
                        script: request.source,
                        script_name: None,
                        limits: None,
                    },
                )
                .map(|report| report.result)
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            Ok(CellRunReport {
                session_id: request.session_id,
                cell_id,
                kind: CellKind::Query,
                status: CellRunStatus::Passed,
                outputs: vec![CellOutput {
                    id: "result".to_string(),
                    kind: CellOutputKind::Table,
                    mime_type: Some("application/vnd.mercurio.dsl.query+json".to_string()),
                    value: serde_json::to_value(result)
                        .map_err(|err| PyRuntimeError::new_err(err.to_string()))?,
                }],
                artifacts: Vec::new(),
                diagnostics: Vec::new(),
                capability_report: None,
                metadata: BTreeMap::new(),
            })
        }
        (CellKind::Action, None | Some(CellLanguage::MercurioDsl)) => {
            let result = native_dsl_engine()
                .execute_query(
                    graph,
                    DslQueryRequest {
                        script: request.source,
                        script_name: None,
                        limits: None,
                    },
                )
                .map(|report| dsl_query_result_to_value(report.result))
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            Ok(CellRunReport {
                session_id: request.session_id,
                cell_id,
                kind: CellKind::Action,
                status: CellRunStatus::Passed,
                outputs: vec![CellOutput {
                    id: "result".to_string(),
                    kind: CellOutputKind::Json,
                    mime_type: Some("application/vnd.mercurio.dsl.action-preview+json".to_string()),
                    value: result,
                }],
                artifacts: Vec::new(),
                diagnostics: Vec::new(),
                capability_report: None,
                metadata: BTreeMap::new(),
            })
        }
        (CellKind::Analysis, None | Some(CellLanguage::MercurioDsl)) => {
            let report = native_dsl_engine()
                .execute_analysis_run(
                    graph,
                    DslAnalysisRunRequest {
                        spec: DslAnalysisRunSpec {
                            run_id: string_parameter(&request.parameters, "runId", "run_id")
                                .unwrap_or_else(|| "dsl-analysis-run".to_string()),
                            capability_id: string_parameter(
                                &request.parameters,
                                "capabilityId",
                                "capability_id",
                            )
                            .unwrap_or_else(|| "mercurio.dsl.analysis".to_string()),
                            script: request.source,
                            subject_element_id: string_parameter(
                                &request.parameters,
                                "subjectElementId",
                                "subject_element_id",
                            ),
                        },
                        script_name: None,
                        limits: None,
                    },
                )
                .map(|report| report.report)
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            Ok(CellRunReport {
                session_id: request.session_id,
                cell_id,
                kind: CellKind::Analysis,
                status: cell_status_from_capability(report.status),
                outputs: vec![CellOutput {
                    id: "capability_report".to_string(),
                    kind: CellOutputKind::CapabilityReport,
                    mime_type: Some("application/vnd.mercurio.capability-run+json".to_string()),
                    value: serde_json::to_value(&report)
                        .map_err(|err| PyRuntimeError::new_err(err.to_string()))?,
                }],
                artifacts: report.artifacts.clone(),
                diagnostics: report.diagnostics.clone(),
                capability_report: Some(report),
                metadata: BTreeMap::new(),
            })
        }
        _ => Err(PyValueError::new_err(format!(
            "unsupported native Python cell kind/language combination: kind={:?} language={:?}",
            request.kind, request.language
        ))),
    }
}

fn default_cell_id(request: &CellRunRequest) -> String {
    match (&request.kind, request.language.as_ref()) {
        (CellKind::Query, None | Some(CellLanguage::MercurioDsl)) => "dsl.query".to_string(),
        (CellKind::Action, None | Some(CellLanguage::MercurioDsl)) => "dsl.action".to_string(),
        (CellKind::Analysis, None | Some(CellLanguage::MercurioDsl)) => "dsl.analysis".to_string(),
        _ => "cell".to_string(),
    }
}

fn dsl_query_result_to_value(result: DslQueryResult) -> serde_json::Value {
    if result.rows.len() == 1 {
        let row = &result.rows[0];
        if result.columns.len() == 1 && result.columns[0] == "value" {
            return row.first().cloned().unwrap_or(serde_json::Value::Null);
        }
        let mut object = serde_json::Map::new();
        for (index, column) in result.columns.iter().enumerate() {
            object.insert(
                column.clone(),
                row.get(index).cloned().unwrap_or(serde_json::Value::Null),
            );
        }
        return serde_json::Value::Object(object);
    }
    serde_json::to_value(result).unwrap_or(serde_json::Value::Null)
}

fn string_parameter(
    parameters: &BTreeMap<String, serde_json::Value>,
    camel_key: &str,
    snake_key: &str,
) -> Option<String> {
    parameters
        .get(camel_key)
        .or_else(|| parameters.get(snake_key))
        .and_then(serde_json::Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .map(ToOwned::to_owned)
}

fn cell_status_from_capability(status: CapabilityRunStatus) -> CellRunStatus {
    match status {
        CapabilityRunStatus::Passed => CellRunStatus::Passed,
        CapabilityRunStatus::Failed => CellRunStatus::Failed,
        CapabilityRunStatus::Error => CellRunStatus::Error,
        CapabilityRunStatus::Inconclusive
        | CapabilityRunStatus::Partial
        | CapabilityRunStatus::NotApplicable => CellRunStatus::Partial,
    }
}

#[cfg(test)]
fn semantic_snapshot_rows(document: &KirDocument) -> Vec<BTreeMap<String, serde_json::Value>> {
    semantic_snapshot_rows_with_graph(document, None)
}

fn semantic_snapshot_rows_with_graph(
    document: &KirDocument,
    graph: Option<&Graph>,
) -> Vec<BTreeMap<String, serde_json::Value>> {
    let mut rows = document
        .elements
        .iter()
        .map(|element| {
            let mut row = BTreeMap::new();
            row.insert(
                "id".to_string(),
                serde_json::Value::String(element.id.clone()),
            );
            row.insert(
                "kind".to_string(),
                serde_json::Value::String(element.kind.clone()),
            );
            row.insert("layer".to_string(), serde_json::json!(element.layer));
            row.insert(
                "model_layer".to_string(),
                serde_json::Value::String(snapshot_model_layer_label(element.layer).to_string()),
            );
            copy_snapshot_property(
                &mut row,
                &element.properties,
                "qualified_name",
                "qualified_name",
            );
            copy_snapshot_property(
                &mut row,
                &element.properties,
                "declared_name",
                "declared_name",
            );
            copy_first_snapshot_property(
                &mut row,
                &element.properties,
                "owner",
                &["owner", "owning_type", "featuring_type"],
            );
            copy_first_snapshot_property(&mut row, &element.properties, "type", &["type"]);
            copy_first_snapshot_property(
                &mut row,
                &element.properties,
                "specializes",
                &["specializes"],
            );
            copy_first_snapshot_property(
                &mut row,
                &element.properties,
                "additional_types",
                &["additional_types"],
            );
            copy_first_snapshot_property(
                &mut row,
                &element.properties,
                "subsets",
                &["subsetted_features", "subsets"],
            );
            copy_first_snapshot_property(
                &mut row,
                &element.properties,
                "redefines",
                &["redefined_features", "redefines"],
            );
            copy_first_snapshot_property(
                &mut row,
                &element.properties,
                "reference_target",
                &["reference_target", "target_ref", "target"],
            );
            copy_snapshot_property(
                &mut row,
                &element.properties,
                "multiplicity",
                "multiplicity",
            );
            copy_snapshot_property(
                &mut row,
                &element.properties,
                "multiplicity_lower",
                "multiplicity_lower",
            );
            copy_snapshot_property(
                &mut row,
                &element.properties,
                "multiplicity_upper",
                "multiplicity_upper",
            );
            copy_snapshot_property(&mut row, &element.properties, "direction", "direction");
            copy_snapshot_property(&mut row, &element.properties, "is_end", "is_end");
            copy_snapshot_property(&mut row, &element.properties, "is_abstract", "is_abstract");
            add_snapshot_metatype_fields(&mut row, graph, element);
            row
        })
        .collect::<Vec<_>>();
    rows.sort_by(|left, right| {
        snapshot_sort_key(left)
            .cmp(&snapshot_sort_key(right))
            .then_with(|| snapshot_string(left, "id").cmp(&snapshot_string(right, "id")))
    });
    rows
}

fn add_snapshot_metatype_fields(
    row: &mut BTreeMap<String, serde_json::Value>,
    graph: Option<&Graph>,
    element: &mercurio_core::KirElement,
) {
    if let Some((direct, chain)) =
        graph.and_then(|graph| snapshot_metatype_from_graph(graph, &element.id))
    {
        row.insert(
            "metatype_name".to_string(),
            serde_json::Value::String(direct),
        );
        row.insert(
            "metatype_chain".to_string(),
            serde_json::Value::Array(chain.into_iter().map(serde_json::Value::String).collect()),
        );
        return;
    }

    let chain = snapshot_fallback_metatype_chain(element);
    if let Some(direct) = chain.first() {
        row.insert(
            "metatype_name".to_string(),
            serde_json::Value::String(direct.clone()),
        );
    }
    row.insert(
        "metatype_chain".to_string(),
        serde_json::Value::Array(chain.into_iter().map(serde_json::Value::String).collect()),
    );
}

fn snapshot_metatype_from_graph(graph: &Graph, element_id: &str) -> Option<(String, Vec<String>)> {
    let node_id = graph.node_id(element_id)?;
    let metatype = element_metatype(graph, node_id)?;
    let direct = snapshot_metamodel_element_label(metatype);
    let mut chain = Vec::new();
    snapshot_push_unique(&mut chain, direct.clone());
    for ancestor in collect_specialization_ancestors(graph, metatype.id) {
        snapshot_push_unique(&mut chain, snapshot_metamodel_element_label(ancestor));
    }
    for ancestor in snapshot_fallback_metatype_ancestor_names(&direct) {
        snapshot_push_unique(&mut chain, ancestor);
    }
    Some((direct, chain))
}

fn snapshot_metamodel_element_label(element: &mercurio_core::graph::Element) -> String {
    element
        .properties
        .get("declared_name")
        .and_then(serde_json::Value::as_str)
        .map(str::to_string)
        .unwrap_or_else(|| snapshot_metatype_tail(&element.element_id).to_string())
}

fn snapshot_fallback_metatype_chain(element: &mercurio_core::KirElement) -> Vec<String> {
    let direct = snapshot_direct_metatype_candidate(element)
        .unwrap_or_else(|| snapshot_metatype_tail(&element.kind).to_string());
    let mut chain = Vec::new();
    snapshot_push_unique(&mut chain, direct.clone());
    for ancestor in snapshot_fallback_metatype_ancestor_names(&direct) {
        snapshot_push_unique(&mut chain, ancestor);
    }
    chain
}

fn snapshot_direct_metatype_candidate(element: &mercurio_core::KirElement) -> Option<String> {
    let value = element.properties.get("metatype").or_else(|| {
        element
            .properties
            .get("metadata")
            .and_then(|metadata| metadata.get("metatype"))
    })?;
    snapshot_collect_metatype_value_candidates(value)
        .into_iter()
        .next()
        .map(|candidate| snapshot_metatype_tail(&candidate).to_string())
}

fn snapshot_collect_metatype_value_candidates(value: &serde_json::Value) -> Vec<String> {
    let mut values = Vec::new();
    snapshot_collect_metatype_value_candidates_into(value, &mut values);
    values
}

fn snapshot_collect_metatype_value_candidates_into(
    value: &serde_json::Value,
    values: &mut Vec<String>,
) {
    match value {
        serde_json::Value::String(value) => snapshot_push_unique(values, value.clone()),
        serde_json::Value::Array(items) => {
            for item in items {
                snapshot_collect_metatype_value_candidates_into(item, values);
            }
        }
        serde_json::Value::Object(object) => {
            for key in [
                "label",
                "name",
                "declared_name",
                "qualified_name",
                "id",
                "element_id",
            ] {
                if let Some(value) = object.get(key).and_then(serde_json::Value::as_str) {
                    snapshot_push_unique(values, value.to_string());
                }
            }
        }
        _ => {}
    }
}

fn snapshot_fallback_metatype_ancestor_names(name: &str) -> Vec<String> {
    const NONE: &[&str] = &[];
    const ELEMENT: &[&str] = &["Element"];
    const NAMESPACE: &[&str] = &["Namespace", "Element"];
    const TYPE: &[&str] = &["Type", "Namespace", "Element"];
    const CLASSIFIER: &[&str] = &["Classifier", "Type", "Namespace", "Element"];
    const FEATURE: &[&str] = &["Feature", "Element"];
    const RELATIONSHIP: &[&str] = &["Relationship", "Element"];

    let key = snapshot_normalize_metatype_key(snapshot_metatype_tail(name));
    let ancestors = match key.as_str() {
        "element" => NONE,
        "namespace" => ELEMENT,
        "package" => NAMESPACE,
        "type" => NAMESPACE,
        "classifier" => TYPE,
        "class" => CLASSIFIER,
        "feature" | "step" => ELEMENT,
        "relationship" | "dependency" | "membership" | "specialization" => ELEMENT,
        _ if key.ends_with("definition") => CLASSIFIER,
        _ if key.ends_with("usage") => FEATURE,
        _ if key.ends_with("relationship") => RELATIONSHIP,
        _ if !key.is_empty() => ELEMENT,
        _ => NONE,
    };
    ancestors.iter().map(|name| (*name).to_string()).collect()
}

fn snapshot_model_layer_label(layer: u8) -> &'static str {
    match layer {
        0 => "foundation",
        1 => "library",
        2 => "user",
        3 => "derived",
        _ => "other",
    }
}

fn snapshot_normalize_metatype_key(value: &str) -> String {
    value
        .trim()
        .trim_matches('"')
        .trim_matches('\'')
        .chars()
        .filter(|value| value.is_ascii_alphanumeric())
        .map(|value| value.to_ascii_lowercase())
        .collect()
}

fn snapshot_metatype_tail(value: &str) -> &str {
    let trimmed = value.trim();
    trimmed
        .rsplit(|ch| matches!(ch, ':' | '.' | '/' | '#'))
        .find(|segment| !segment.is_empty())
        .unwrap_or(trimmed)
}

fn snapshot_push_unique(values: &mut Vec<String>, value: impl Into<String>) {
    let value = value.into();
    if !value.trim().is_empty() && !values.iter().any(|existing| existing == &value) {
        values.push(value);
    }
}

fn copy_first_snapshot_property(
    row: &mut BTreeMap<String, serde_json::Value>,
    properties: &BTreeMap<String, serde_json::Value>,
    output_name: &str,
    input_names: &[&str],
) {
    for input_name in input_names {
        if copy_snapshot_property(row, properties, output_name, input_name) {
            return;
        }
    }
}

fn copy_snapshot_property(
    row: &mut BTreeMap<String, serde_json::Value>,
    properties: &BTreeMap<String, serde_json::Value>,
    output_name: &str,
    input_name: &str,
) -> bool {
    let Some(value) = properties.get(input_name) else {
        return false;
    };
    row.insert(
        output_name.to_string(),
        normalize_snapshot_value(value.clone()),
    );
    true
}

fn normalize_snapshot_value(value: serde_json::Value) -> serde_json::Value {
    match value {
        serde_json::Value::Array(values) => {
            let mut values = values
                .into_iter()
                .map(normalize_snapshot_value)
                .collect::<Vec<_>>();
            values.sort_by_key(|value| value.to_string());
            serde_json::Value::Array(values)
        }
        other => other,
    }
}

fn snapshot_sort_key(row: &BTreeMap<String, serde_json::Value>) -> String {
    snapshot_string(row, "qualified_name")
        .or_else(|| snapshot_string(row, "declared_name"))
        .unwrap_or_default()
}

fn snapshot_string(row: &BTreeMap<String, serde_json::Value>, key: &str) -> Option<String> {
    row.get(key)
        .and_then(|value| value.as_str().map(str::to_string))
}

#[pymodule]
fn mercurio_core_native(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    register_module(module)
}

#[pymodule]
fn _core(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    register_module(module)
}

fn register_module(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyWorkspace>()?;
    module.add_class::<PyPartRef>()?;
    module.add_class::<PyKirElement>()?;
    module.add_class::<PyModelBuilder>()?;
    module.add_class::<PyWriteBackResult>()?;
    module.add_class::<PySemanticModel>()?;
    module.add_class::<PyElementView>()?;
    module.add_class::<PyModelWorkspace>()?;
    module.add_class::<PyModelSession>()?;
    module.add_class::<PyModelFork>()?;
    module.add_class::<PyForkElement>()?;
    module.add_class::<PyCommitResult>()?;
    Ok(())
}

fn py_write_back_result(
    write_back: WriteBackResult,
    changed_files: Vec<String>,
    changed_declarations: Vec<String>,
) -> PyWriteBackResult {
    PyWriteBackResult {
        edited_files: write_back.edited_files,
        changed_files,
        changed_declarations,
        mode: match write_back.mode {
            WriteBackMode::LocalizedPatch => "localized_patch",
            WriteBackMode::CanonicalRewrite => "canonical_rewrite",
        }
        .to_string(),
        validation_ok: write_back.validation.ok,
        validation_message: write_back.validation.message,
    }
}

fn qname(value: &str) -> QualifiedName {
    QualifiedName::parse(value)
}

fn qnames(values: Option<Vec<String>>) -> Vec<QualifiedName> {
    values
        .unwrap_or_default()
        .iter()
        .map(|value| qname(value))
        .collect()
}

fn py_value_to_json(value: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    if value.is_none() {
        return Ok(serde_json::Value::Null);
    }
    if let Ok(value) = value.extract::<bool>() {
        return Ok(serde_json::Value::Bool(value));
    }
    if let Ok(value) = value.extract::<i64>() {
        return Ok(serde_json::json!(value));
    }
    if let Ok(value) = value.extract::<f64>() {
        return Ok(serde_json::json!(value));
    }
    if let Ok(value) = value.extract::<String>() {
        return Ok(serde_json::Value::String(value));
    }
    if let Ok(values) = value.extract::<Vec<String>>() {
        return Ok(serde_json::json!(values));
    }
    Err(PyValueError::new_err(
        "attribute value must be None, bool, int, float, str, or list[str]",
    ))
}

fn parse_commit_mode(value: &str) -> PyResult<CommitMode> {
    match value {
        "preserve_source" => Ok(CommitMode::PreserveSource),
        "rewrite_source" => Ok(CommitMode::RewriteSource),
        other => Err(PyValueError::new_err(format!(
            "unsupported commit mode `{other}`; expected preserve_source or rewrite_source"
        ))),
    }
}

fn py_fork_element(inner: ForkElement) -> PyForkElement {
    PyForkElement { inner }
}

fn py_commit_result(result: CommitResult) -> PyCommitResult {
    PyCommitResult {
        mode: match result.mode {
            CommitMode::PreserveSource => "preserve_source",
            CommitMode::RewriteSource => "rewrite_source",
        }
        .to_string(),
        strategy_used: match result.strategy_used {
            CommitStrategy::MutatorPlan => "mutator_plan",
            CommitStrategy::GeneratedCompanionFiles => "generated_companion_files",
            CommitStrategy::RewriteGeneratedSource => "rewrite_generated_source",
            CommitStrategy::NoOp => "no_op",
        }
        .to_string(),
        base_revision: result.base_revision.fingerprint,
        new_revision: result.new_revision.fingerprint,
        changed_files: result.changed_files.into_iter().collect(),
        edited_files: result.edited_files,
        generated_elements: result.generated_elements,
    }
}

fn selector(value: &str) -> ContainerSelector {
    if let Some(path) = value.strip_prefix("file:") {
        return ContainerSelector::File {
            target_file: path.to_string(),
        };
    }
    let qualified_name = qname(value);
    if qualified_name.0.len() <= 1 {
        ContainerSelector::Package { qualified_name }
    } else {
        ContainerSelector::Declaration { qualified_name }
    }
}

fn authoring_error(err: mercurio_core::AuthoringError) -> PyErr {
    PyValueError::new_err(err.to_string())
}

fn session_error(err: SessionError) -> PyErr {
    PyValueError::new_err(err.to_string())
}

fn io_error(err: std::io::Error) -> PyErr {
    PyRuntimeError::new_err(err.to_string())
}

fn write_atomic(path: &Path, content: &str) -> PyResult<()> {
    let mut tmp = path.to_path_buf();
    let file_name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("output");
    tmp.set_file_name(format!("{file_name}.tmp"));
    std::fs::write(&tmp, content).map_err(io_error)?;
    if path.exists() {
        std::fs::remove_file(path).map_err(io_error)?;
    }
    std::fs::rename(&tmp, path).map_err(io_error)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::{
        PyModelBuilder, PyModelWorkspace, PyWorkspace, compile_workspace_path, dsl_query_json,
        dsl_schema_json, graph_view_json, l2_explorer_json, metatype_explorer_json,
        model_metadata_json, preview_transaction_json, project_sources_from_descriptor,
        run_cell_json, search_json, semantic_snapshot_rows,
    };
    use mercurio_core::{Graph, KirDocument, KirElement, MetamodelAttributeRegistry};
    use pyo3::IntoPyObjectExt;
    use pyo3::Python;
    use pyo3::types::PyType;

    fn dsl_test_graph() -> std::sync::Arc<Graph> {
        std::sync::Arc::new(
            Graph::from_document(KirDocument {
                metadata: BTreeMap::new(),
                elements: vec![KirElement {
                    id: "type.Demo.Vehicle".to_string(),
                    kind: "PartDefinition".to_string(),
                    layer: 2,
                    properties: BTreeMap::from([(
                        "declared_name".to_string(),
                        serde_json::json!("Vehicle"),
                    )]),
                }],
            })
            .unwrap(),
        )
    }

    #[test]
    fn native_python_dsl_query_uses_shared_dsl_engine() {
        let result: serde_json::Value = serde_json::from_str(
            &dsl_query_json(dsl_test_graph(), "model.parts().count()").unwrap(),
        )
        .unwrap();

        assert_eq!(result["columns"], serde_json::json!(["value"]));
        assert_eq!(result["rows"][0][0], serde_json::json!(1));
    }

    #[test]
    fn native_python_cell_runner_returns_shared_cell_report() {
        let request = serde_json::json!({
            "kind": "query",
            "language": "mercurio_dsl",
            "source": "model.parts().select([\"declared_name\"])",
            "parameters": {}
        })
        .to_string();
        let report: serde_json::Value =
            serde_json::from_str(&run_cell_json(dsl_test_graph(), &request).unwrap()).unwrap();

        assert_eq!(report["cellId"], serde_json::json!("dsl.query"));
        assert_eq!(report["status"], serde_json::json!("passed"));
        assert_eq!(report["outputs"][0]["id"], serde_json::json!("result"));
        assert_eq!(
            report["outputs"][0]["value"]["rows"][0][0],
            serde_json::json!("Vehicle")
        );
    }

    #[test]
    fn native_python_analysis_cell_runner_returns_capability_report() {
        let request = serde_json::json!({
            "kind": "analysis",
            "language": "mercurio_dsl",
            "source": "#{verdict: \"pass\", total_mass_kg: 12.0}",
            "parameters": {
                "runId": "mass-check",
                "capabilityId": "mercurio.dsl.analysis",
                "subjectElementId": "type.Demo.Vehicle"
            }
        })
        .to_string();
        let report: serde_json::Value =
            serde_json::from_str(&run_cell_json(dsl_test_graph(), &request).unwrap()).unwrap();

        assert_eq!(report["cellId"], serde_json::json!("dsl.analysis"));
        assert_eq!(report["kind"], serde_json::json!("analysis"));
        assert_eq!(report["status"], serde_json::json!("passed"));
        assert_eq!(
            report["outputs"][0]["id"],
            serde_json::json!("capability_report")
        );
        assert_eq!(
            report["capabilityReport"]["capability_id"],
            serde_json::json!("mercurio.dsl.analysis")
        );
    }

    #[test]
    fn native_python_action_cell_runner_returns_preview_report() {
        let request = serde_json::json!({
            "kind": "action",
            "language": "mercurio_dsl",
            "source": "model.transaction(\"rename vehicle\").rename(\"type.Demo.Vehicle\", \"VehicleRenamed\").preview()",
            "parameters": {}
        })
        .to_string();
        let report: serde_json::Value =
            serde_json::from_str(&run_cell_json(dsl_test_graph(), &request).unwrap()).unwrap();

        assert_eq!(report["cellId"], serde_json::json!("dsl.action"));
        assert_eq!(report["kind"], serde_json::json!("action"));
        assert_eq!(report["status"], serde_json::json!("passed"));
        assert_eq!(report["outputs"][0]["id"], serde_json::json!("result"));
        assert_eq!(report["outputs"][0]["kind"], serde_json::json!("json"));
        assert_eq!(
            report["outputs"][0]["value"]["schema"],
            serde_json::json!("mercurio.semantic_transaction.v1")
        );
        assert_eq!(
            report["outputs"][0]["value"]["status"],
            serde_json::json!("previewed")
        );
        assert_eq!(
            report["outputs"][0]["value"]["operations"][0]["kind"],
            serde_json::json!("change_set")
        );
    }

    #[test]
    fn native_python_transaction_preview_uses_structured_actions() {
        let request = serde_json::json!({
            "label": "python transaction",
            "actions": [
                {
                    "kind": "rename_declaration",
                    "element": "type.Demo.Vehicle",
                    "new_name": "VehicleRenamed"
                },
                {
                    "kind": "set_attribute",
                    "element": "type.Demo.Vehicle",
                    "attribute": "doc",
                    "value": "checked"
                }
            ]
        })
        .to_string();
        let report: serde_json::Value =
            serde_json::from_str(&preview_transaction_json(&request).unwrap()).unwrap();

        assert_eq!(report["status"], serde_json::json!("previewed"));
        assert_eq!(report["operation_count"], serde_json::json!(1));
        assert_eq!(
            report["operations"][0]["kind"],
            serde_json::json!("change_set")
        );
        assert_eq!(
            report["operations"][0]["change_set"]["actions"][0]["RenameDeclaration"]["new_name"],
            serde_json::json!("VehicleRenamed")
        );
        assert_eq!(
            report["operations"][0]["change_set"]["actions"][1]["SetAttribute"]["value"],
            serde_json::json!("checked")
        );
    }

    #[test]
    fn native_python_dsl_schema_includes_sysml_extension() {
        let graph = dsl_test_graph();
        let schema: serde_json::Value =
            serde_json::from_str(&dsl_schema_json(&graph).unwrap()).unwrap();

        assert!(
            schema["stdlib_functions"]
                .as_array()
                .unwrap()
                .iter()
                .any(|value| value == "ModelContext.requirements")
        );
    }

    #[test]
    fn native_python_exploration_views_use_foundation_dtos() {
        let graph = dsl_test_graph();
        let document = KirDocument {
            metadata: BTreeMap::new(),
            elements: vec![KirElement {
                id: "type.Demo.Vehicle".to_string(),
                kind: "PartDefinition".to_string(),
                layer: 2,
                properties: BTreeMap::from([(
                    "declared_name".to_string(),
                    serde_json::json!("Vehicle"),
                )]),
            }],
        };
        let metadata: serde_json::Value =
            serde_json::from_str(&model_metadata_json(&graph, &document).unwrap()).unwrap();
        let scoped_graph: serde_json::Value =
            serde_json::from_str(&graph_view_json(&graph, Some("l2")).unwrap()).unwrap();
        let search: serde_json::Value =
            serde_json::from_str(&search_json(&graph, "vehicle").unwrap()).unwrap();

        assert_eq!(metadata["user_element_count"], serde_json::json!(1));
        assert_eq!(
            scoped_graph["nodes"][0]["id"],
            serde_json::json!("type.Demo.Vehicle")
        );
        assert_eq!(search[0]["label"], serde_json::json!("Vehicle"));
    }

    #[test]
    fn native_python_explorer_views_serialize_shared_dtos() {
        let graph = dsl_test_graph();
        let registry = MetamodelAttributeRegistry::build(&graph);
        let l2_request = serde_json::json!({
            "seed_id": "type.Demo.Vehicle",
            "expanded_parents": [],
            "expanded_children": [],
            "include_reference_edges": true
        })
        .to_string();
        let metatype_request = serde_json::json!({
            "seed_id": "type.Demo.Vehicle",
            "expanded_parents": [],
            "expanded_children": []
        })
        .to_string();

        let l2: serde_json::Value =
            serde_json::from_str(&l2_explorer_json(&graph, &l2_request).unwrap()).unwrap();
        let metatype: serde_json::Value = serde_json::from_str(
            &metatype_explorer_json(&graph, &registry, &metatype_request).unwrap(),
        )
        .unwrap();

        assert_eq!(l2["seed_id"], serde_json::json!("type.Demo.Vehicle"));
        assert_eq!(l2["nodes"][0]["is_seed"], serde_json::json!(true));
        assert_eq!(metatype["seed_id"], serde_json::json!("type.Demo.Vehicle"));
    }

    #[test]
    fn builder_creates_renders_and_compiles_model() {
        let mut builder = PyModelBuilder::new(true).unwrap();

        builder
            .add_package("model.sysml".to_string(), "Demo".to_string())
            .unwrap();
        builder
            .add_definition(
                "Demo".to_string(),
                "part".to_string(),
                "Engine".to_string(),
                None,
            )
            .unwrap();
        builder
            .add_definition(
                "Demo".to_string(),
                "part".to_string(),
                "Vehicle".to_string(),
                None,
            )
            .unwrap();
        builder
            .add_usage(
                "Demo.Vehicle".to_string(),
                "part".to_string(),
                "engine".to_string(),
                Some("Engine".to_string()),
                None,
            )
            .unwrap();

        let rendered = builder.render_file("model.sysml".to_string()).unwrap();
        assert!(rendered.contains("package Demo"));
        assert!(rendered.contains("part def Vehicle"));
        assert!(rendered.contains("part engine: Engine"));

        let compiled = builder.compile_json().unwrap();
        assert!(compiled.contains("type.Demo.Vehicle"));
        assert!(compiled.contains("feature.Demo.Vehicle.engine"));

        let model = builder.compile_model().unwrap();
        let snapshot_json = model.semantic_snapshot_json().unwrap();
        let snapshot: Vec<serde_json::Value> = serde_json::from_str(&snapshot_json).unwrap();
        assert!(snapshot.iter().any(|row| {
            row.get("qualified_name").and_then(|value| value.as_str()) == Some("Demo.Vehicle")
                && row.get("kind").and_then(|value| value.as_str())
                    == Some("SysML::Systems::PartDefinition")
        }));
        assert!(snapshot.iter().any(|row| {
            row.get("qualified_name").and_then(|value| value.as_str())
                == Some("Demo.Vehicle.engine")
                && row.get("kind").and_then(|value| value.as_str()) == Some("SysML::PartUsage")
                && row.get("type").and_then(|value| value.as_str()) == Some("type.Demo.Engine")
        }));
    }

    #[test]
    fn builder_renders_quoted_names_for_pilot_structural_examples() {
        let mut builder = PyModelBuilder::new(true).unwrap();

        builder
            .add_package("model.sysml".to_string(), "Subsetting Example".to_string())
            .unwrap();
        builder
            .add_definition(
                "Subsetting Example".to_string(),
                "part".to_string(),
                "Vehicle Part".to_string(),
                None,
            )
            .unwrap();
        builder
            .add_definition(
                "Subsetting Example".to_string(),
                "part".to_string(),
                "Vehicle Definition".to_string(),
                Some(vec!["Subsetting Example.Vehicle Part".to_string()]),
            )
            .unwrap();
        builder
            .add_usage(
                "Subsetting Example.Vehicle Definition".to_string(),
                "part".to_string(),
                "front wheel".to_string(),
                Some("Vehicle Part".to_string()),
                None,
            )
            .unwrap();

        let rendered = builder.render_file("model.sysml".to_string()).unwrap();
        assert!(rendered.contains("package 'Subsetting Example'"));
        assert!(rendered.contains("part def 'Vehicle Part';"));
        assert!(rendered.contains(
            "part def 'Vehicle Definition' specializes 'Subsetting Example'::'Vehicle Part'"
        ));
        assert!(rendered.contains("part 'front wheel': 'Vehicle Part';"));

        let model = builder.compile_model().unwrap();
        let snapshot_json = model.semantic_snapshot_json().unwrap();
        let snapshot: Vec<serde_json::Value> = serde_json::from_str(&snapshot_json).unwrap();
        assert!(snapshot.iter().any(|row| {
            row.get("qualified_name").and_then(|value| value.as_str())
                == Some("Subsetting Example.Vehicle Definition.front wheel")
                && row.get("type").and_then(|value| value.as_str())
                    == Some("type.Subsetting Example.Vehicle Part")
        }));
    }

    #[test]
    fn builder_renders_short_names_for_pilot_structural_examples() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let mut builder = PyModelBuilder::new(true).unwrap();
            builder
                .add_package("model.sysml".to_string(), "Demo".to_string())
                .unwrap();
            builder
                .add_definition(
                    "Demo".to_string(),
                    "attribute".to_string(),
                    "Mass".to_string(),
                    None,
                )
                .unwrap();
            builder
                .add_usage(
                    "Demo".to_string(),
                    "attribute".to_string(),
                    "mass".to_string(),
                    Some("Mass".to_string()),
                    None,
                )
                .unwrap();

            let value = "m".into_bound_py_any(py).unwrap();
            builder
                .set_attribute(
                    "Demo.mass".to_string(),
                    "declaredShortName".to_string(),
                    &value,
                )
                .unwrap();

            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("attribute <m> mass: Mass;"));
            builder.compile_model().unwrap();
        });
    }

    #[test]
    fn semantic_snapshot_matches_equivalent_authored_and_source_models() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let mut authored = PyModelBuilder::new(true).unwrap();
            authored
                .add_package("model.sysml".to_string(), "Demo".to_string())
                .unwrap();
            authored
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "Engine".to_string(),
                    None,
                )
                .unwrap();
            authored
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "Vehicle".to_string(),
                    None,
                )
                .unwrap();
            authored
                .add_usage(
                    "Demo.Vehicle".to_string(),
                    "part".to_string(),
                    "engine".to_string(),
                    Some("Engine".to_string()),
                    None,
                )
                .unwrap();

            let cls = PyType::new::<PyModelBuilder>(py);
            let source = PyModelBuilder::from_sysml_files(
                &cls,
                BTreeMap::from([(
                    "model.sysml".to_string(),
                    "package Demo { part def Engine; part def Vehicle { part engine: Engine; } }"
                        .to_string(),
                )]),
                true,
            )
            .unwrap();

            let authored_document = authored.compile_document().unwrap();
            let source_document = source.compile_document().unwrap();
            let authored_rows = semantic_snapshot_rows(&authored_document);
            let source_rows = semantic_snapshot_rows(&source_document);

            for qualified_name in ["Demo.Engine", "Demo.Vehicle", "Demo.Vehicle.engine"] {
                let authored_row = snapshot_row(&authored_rows, qualified_name);
                let source_row = snapshot_row(&source_rows, qualified_name);
                for field in ["kind", "owner", "type", "specializes", "subsets"] {
                    assert_eq!(
                        authored_row.get(field),
                        source_row.get(field),
                        "{qualified_name}.{field}"
                    );
                }
            }
        });
    }

    #[test]
    fn native_descriptor_open_snapshot_matches_equivalent_authoring_model() {
        let root = temp_dir("descriptor_equivalence");
        write_file(
            &root.join("model").join("main.sysml"),
            "package Demo { part def Engine; part def Vehicle { part engine: Engine; } }\n",
        );
        write_file(
            &root.join(".project.json"),
            r#"{
  "schema": "dev.mercurio.project.v2",
  "version": 2,
  "model": {
    "entrypoints": ["model/main.sysml"]
  }
}"#,
        );

        let workspace =
            PyWorkspace::open(root.join(".project.json").to_string_lossy().as_ref()).unwrap();
        let opened_model = workspace.compile().unwrap();

        let mut authored = PyModelBuilder::new(true).unwrap();
        authored
            .add_package("model.sysml".to_string(), "Demo".to_string())
            .unwrap();
        authored
            .add_definition(
                "Demo".to_string(),
                "part".to_string(),
                "Engine".to_string(),
                None,
            )
            .unwrap();
        authored
            .add_definition(
                "Demo".to_string(),
                "part".to_string(),
                "Vehicle".to_string(),
                None,
            )
            .unwrap();
        authored
            .add_usage(
                "Demo.Vehicle".to_string(),
                "part".to_string(),
                "engine".to_string(),
                Some("Engine".to_string()),
                None,
            )
            .unwrap();
        let authored_model = authored.compile_model().unwrap();

        assert_snapshot_rows_match(
            &semantic_snapshot_rows(&opened_model.document),
            &semantic_snapshot_rows(&authored_model.document),
            &["Demo.Engine", "Demo.Vehicle", "Demo.Vehicle.engine"],
            &["kind", "owner", "type", "specializes", "subsets"],
        );
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn python_edit_existing_example_matches_equivalent_authoring_model() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_| {
            let example_root = Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
                .join("..")
                .join("mercurio-examples")
                .join("python-edit-existing");
            let workspace = PyWorkspace::open(
                example_root
                    .join(".project.json")
                    .to_string_lossy()
                    .as_ref(),
            )
            .unwrap();
            let opened_model = workspace.compile().unwrap();

            let mut authored = PyModelBuilder::new(false).unwrap();
            authored
                .add_package(
                    "model/sensor_system.sysml".to_string(),
                    "SensorSystem".to_string(),
                )
                .unwrap();
            for import_path in [
                "ISQBase::*",
                "ISQSpaceTime::*",
                "ISQElectromagnetism::*",
                "ScalarValues::*",
            ] {
                authored
                    .add_import(
                        "model/sensor_system.sysml".to_string(),
                        import_path.to_string(),
                        Some("SensorSystem".to_string()),
                    )
                    .unwrap();
            }

            add_sensor_definition(
                &mut authored,
                "TemperatureSensor",
                &[
                    ("mass", "ISQBase::MassValue"),
                    ("sampling_rate", "ISQSpaceTime::FrequencyValue"),
                    (
                        "supply_voltage",
                        "ISQElectromagnetism::ElectricPotentialValue",
                    ),
                ],
            );
            add_sensor_definition(
                &mut authored,
                "PressureSensor",
                &[
                    ("mass", "ISQBase::MassValue"),
                    ("sampling_rate", "ISQSpaceTime::FrequencyValue"),
                    (
                        "supply_voltage",
                        "ISQElectromagnetism::ElectricPotentialValue",
                    ),
                ],
            );
            add_sensor_definition(
                &mut authored,
                "HumiditySensor",
                &[
                    ("mass", "ISQBase::MassValue"),
                    ("sampling_rate", "ISQSpaceTime::FrequencyValue"),
                    ("resolution", "ScalarValues::Real"),
                ],
            );
            authored
                .add_definition(
                    "SensorSystem".to_string(),
                    "part".to_string(),
                    "SensorArray".to_string(),
                    None,
                )
                .unwrap();
            for (name, ty) in [
                ("total_mass", "ISQBase::MassValue"),
                ("channel_count", "ScalarValues::Integer"),
            ] {
                authored
                    .add_usage(
                        "SensorSystem.SensorArray".to_string(),
                        "attribute".to_string(),
                        name.to_string(),
                        Some(ty.to_string()),
                        None,
                    )
                    .unwrap();
            }
            for (name, ty) in [
                ("temperature_sensor", "TemperatureSensor"),
                ("pressure_sensor", "PressureSensor"),
                ("humidity_sensor", "HumiditySensor"),
            ] {
                authored
                    .add_usage(
                        "SensorSystem.SensorArray".to_string(),
                        "part".to_string(),
                        name.to_string(),
                        Some(ty.to_string()),
                        None,
                    )
                    .unwrap();
            }
            authored
                .add_usage(
                    "SensorSystem.SensorArray".to_string(),
                    "attribute".to_string(),
                    "power_budget".to_string(),
                    Some("ISQMechanics::PowerValue".to_string()),
                    None,
                )
                .unwrap();
            let authored_model = authored.compile_model().unwrap();

            assert_snapshot_rows_match(
                &semantic_snapshot_rows(&opened_model.document),
                &semantic_snapshot_rows(&authored_model.document),
                &[
                    "SensorSystem.TemperatureSensor",
                    "SensorSystem.PressureSensor",
                    "SensorSystem.SensorArray",
                    "SensorSystem.SensorArray.temperature_sensor",
                    "SensorSystem.SensorArray.pressure_sensor",
                    "SensorSystem.SensorArray.humidity_sensor",
                    "SensorSystem.SensorArray.power_budget",
                    "SensorSystem.HumiditySensor",
                    "SensorSystem.HumiditySensor.resolution",
                ],
                &["kind", "owner", "type"],
            );
        });
    }

    #[test]
    fn python_stdlib_authoring_example_matches_equivalent_authoring_model() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_| {
            let example_root = Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
                .join("..")
                .join("mercurio-examples")
                .join("python-stdlib-authoring");
            let workspace = PyWorkspace::open(
                example_root
                    .join(".project.json")
                    .to_string_lossy()
                    .as_ref(),
            )
            .unwrap();
            let opened_model = workspace.compile().unwrap();

            let mut authored = PyModelBuilder::new(false).unwrap();
            authored
                .add_package("model.sysml".to_string(), "SatelliteModel".to_string())
                .unwrap();
            for import_path in [
                "ISQBase::*",
                "ISQSpaceTime::*",
                "ISQMechanics::*",
                "ISQThermodynamics::*",
                "ISQElectromagnetism::*",
                "SI::*",
                "ScalarValues::*",
            ] {
                authored
                    .add_import(
                        "model.sysml".to_string(),
                        import_path.to_string(),
                        Some("SatelliteModel".to_string()),
                    )
                    .unwrap();
            }

            add_part_definition_with_attributes(
                &mut authored,
                "SatelliteModel",
                "Structure",
                &[
                    ("dry_mass", "ISQBase::MassValue"),
                    ("length", "ISQBase::LengthValue"),
                    ("width", "ISQBase::LengthValue"),
                    ("height", "ISQBase::LengthValue"),
                ],
            );
            add_part_definition_with_attributes(
                &mut authored,
                "SatelliteModel",
                "PowerSystem",
                &[
                    ("mass", "ISQBase::MassValue"),
                    ("solar_array_area", "ISQSpaceTime::AreaValue"),
                    ("peak_power", "ISQMechanics::PowerValue"),
                    ("battery_capacity", "ISQThermodynamics::EnergyValue"),
                    ("bus_voltage", "ISQElectromagnetism::ElectricPotentialValue"),
                ],
            );
            add_part_definition_with_attributes(
                &mut authored,
                "SatelliteModel",
                "ThermalControl",
                &[
                    ("mass", "ISQBase::MassValue"),
                    ("temp_min", "ISQBase::ThermodynamicTemperatureValue"),
                    ("temp_max", "ISQBase::ThermodynamicTemperatureValue"),
                    ("heat_dissipation", "ISQMechanics::PowerValue"),
                ],
            );
            add_part_definition_with_attributes(
                &mut authored,
                "SatelliteModel",
                "Satellite",
                &[
                    ("total_mass", "ISQBase::MassValue"),
                    ("orbit_altitude", "ISQBase::LengthValue"),
                    ("design_life", "ISQBase::DurationValue"),
                    ("name", "ScalarValues::String"),
                ],
            );
            for (name, ty) in [
                ("structure", "Structure"),
                ("power", "PowerSystem"),
                ("thermal", "ThermalControl"),
            ] {
                authored
                    .add_usage(
                        "SatelliteModel.Satellite".to_string(),
                        "part".to_string(),
                        name.to_string(),
                        Some(ty.to_string()),
                        None,
                    )
                    .unwrap();
            }
            let authored_model = authored.compile_model().unwrap();

            assert_snapshot_rows_match(
                &semantic_snapshot_rows(&opened_model.document),
                &semantic_snapshot_rows(&authored_model.document),
                &[
                    "SatelliteModel.Structure",
                    "SatelliteModel.Structure.dry_mass",
                    "SatelliteModel.PowerSystem",
                    "SatelliteModel.PowerSystem.peak_power",
                    "SatelliteModel.ThermalControl",
                    "SatelliteModel.ThermalControl.temp_min",
                    "SatelliteModel.Satellite",
                    "SatelliteModel.Satellite.structure",
                    "SatelliteModel.Satellite.power",
                    "SatelliteModel.Satellite.thermal",
                ],
                &["kind", "owner", "type"],
            );
        });
    }

    #[test]
    fn project_plugin_pacti_example_matches_equivalent_authoring_model() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_| {
            let example_root = Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
                .join("..")
                .join("mercurio-examples")
                .join("project-plugin-pacti-analysis");
            let workspace = PyWorkspace::open(
                example_root
                    .join(".project.json")
                    .to_string_lossy()
                    .as_ref(),
            )
            .unwrap();
            let opened_model = workspace.compile().unwrap();

            let mut authored = PyModelBuilder::new(false).unwrap();
            authored
                .add_package(
                    "model/contract-demo.sysml".to_string(),
                    "ContractDemo".to_string(),
                )
                .unwrap();
            authored
                .add_definition(
                    "ContractDemo".to_string(),
                    "part".to_string(),
                    "PowerController".to_string(),
                    None,
                )
                .unwrap();
            authored
                .add_usage(
                    "ContractDemo".to_string(),
                    "part".to_string(),
                    "controller".to_string(),
                    Some("PowerController".to_string()),
                    None,
                )
                .unwrap();
            let authored_model = authored.compile_model().unwrap();

            assert_snapshot_rows_match(
                &semantic_snapshot_rows(&opened_model.document),
                &semantic_snapshot_rows(&authored_model.document),
                &["ContractDemo.PowerController", "ContractDemo.controller"],
                &["kind", "owner", "type"],
            );
        });
    }

    #[test]
    fn structural_connectivity_example_matches_equivalent_authoring_model() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_| {
            let example_root = Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
                .join("..")
                .join("mercurio-examples")
                .join("structural-connectivity");
            let workspace = PyWorkspace::open(
                example_root
                    .join(".project.json")
                    .to_string_lossy()
                    .as_ref(),
            )
            .unwrap();
            let opened_model = workspace.compile().unwrap();

            let mut authored = PyModelBuilder::new(false).unwrap();
            authored
                .add_package(
                    "model/satellite-system.sysml".to_string(),
                    "SatelliteSystem".to_string(),
                )
                .unwrap();

            for name in [
                "Satellite",
                "PayloadAssembly",
                "SpacecraftBus",
                "CommunicationsSubsystem",
                "ElectricalPowerSubsystem",
                "AttitudeControlSubsystem",
                "ThermalControlSubsystem",
                "OpticalImager",
                "ImageProcessor",
                "RFTransceiver",
                "DeployableAntenna",
                "SolarArray",
                "LithiumIonBattery",
                "PowerDistributionUnit",
                "ReactionWheel",
                "StarTracker",
                "HeatPipe",
                "Radiator",
                "DebugProbe",
                "GroundSupportInterface",
            ] {
                authored
                    .add_definition(
                        "SatelliteSystem".to_string(),
                        "part".to_string(),
                        name.to_string(),
                        None,
                    )
                    .unwrap();
            }
            for (name, parts) in [
                (
                    "Satellite",
                    vec![
                        ("payload", "PayloadAssembly"),
                        ("bus", "SpacecraftBus"),
                        ("comms", "CommunicationsSubsystem"),
                    ],
                ),
                (
                    "PayloadAssembly",
                    vec![("imager", "OpticalImager"), ("processor", "ImageProcessor")],
                ),
                (
                    "SpacecraftBus",
                    vec![
                        ("eps", "ElectricalPowerSubsystem"),
                        ("adcs", "AttitudeControlSubsystem"),
                        ("thermal", "ThermalControlSubsystem"),
                    ],
                ),
                (
                    "CommunicationsSubsystem",
                    vec![("rf", "RFTransceiver"), ("antenna", "DeployableAntenna")],
                ),
                (
                    "ElectricalPowerSubsystem",
                    vec![
                        ("panels", "SolarArray"),
                        ("battery", "LithiumIonBattery"),
                        ("pdu", "PowerDistributionUnit"),
                    ],
                ),
                (
                    "AttitudeControlSubsystem",
                    vec![
                        ("rw1", "ReactionWheel"),
                        ("rw2", "ReactionWheel"),
                        ("rw3", "ReactionWheel"),
                        ("starTracker", "StarTracker"),
                    ],
                ),
                (
                    "ThermalControlSubsystem",
                    vec![("heatPipe", "HeatPipe"), ("radiator", "Radiator")],
                ),
                ("DebugProbe", vec![("interface", "GroundSupportInterface")]),
            ] {
                add_part_usages(&mut authored, "SatelliteSystem", name, &parts);
            }
            let authored_model = authored.compile_model().unwrap();

            assert_snapshot_rows_match(
                &semantic_snapshot_rows(&opened_model.document),
                &semantic_snapshot_rows(&authored_model.document),
                &[
                    "SatelliteSystem.Satellite",
                    "SatelliteSystem.Satellite.payload",
                    "SatelliteSystem.PayloadAssembly.imager",
                    "SatelliteSystem.SpacecraftBus.eps",
                    "SatelliteSystem.AttitudeControlSubsystem.starTracker",
                    "SatelliteSystem.DebugProbe",
                    "SatelliteSystem.DebugProbe.interface",
                    "SatelliteSystem.GroundSupportInterface",
                ],
                &["kind", "owner", "type"],
            );
        });
    }

    #[test]
    fn voron_trident_example_matches_equivalent_authorable_structure() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let example_root = Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
                .join("..")
                .join("mercurio-examples")
                .join("voron-trident-simulation");
            let workspace = PyWorkspace::open(
                example_root
                    .join(".project.json")
                    .to_string_lossy()
                    .as_ref(),
            )
            .unwrap();
            let opened_model = workspace.compile().unwrap();

            let mut authored = PyModelBuilder::new(false).unwrap();
            authored
                .add_package(
                    "model/voron-trident-350.sysml".to_string(),
                    "VoronTrident350".to_string(),
                )
                .unwrap();
            authored
                .add_import(
                    "model/voron-trident-350.sysml".to_string(),
                    "ScalarValues::*".to_string(),
                    Some("VoronTrident350".to_string()),
                )
                .unwrap();

            for name in [
                "VoronPrinter",
                "HeatedBed",
                "Hotend",
                "CoreXYMotionSystem",
                "XYCarriage",
                "ZLeadscrew",
                "IndxToolchanger",
                "ToolDock",
                "Electronics",
            ] {
                authored
                    .add_definition(
                        "VoronTrident350".to_string(),
                        "part".to_string(),
                        name.to_string(),
                        None,
                    )
                    .unwrap();
            }

            add_attribute_usages(
                &mut authored,
                "VoronTrident350.VoronPrinter",
                &[
                    ("buildVolume_x", "Real", Some("350.0")),
                    ("buildVolume_y", "Real", Some("350.0")),
                    ("buildVolume_z", "Real", Some("250.0")),
                    ("bed_temperature", "Real", Some("22.0")),
                    ("hotend_temperature", "Real", Some("22.0")),
                ],
            );
            add_part_usages(
                &mut authored,
                "VoronTrident350",
                "VoronPrinter",
                &[
                    ("bed", "HeatedBed"),
                    ("hotend", "Hotend"),
                    ("motion", "CoreXYMotionSystem"),
                    ("toolchanger", "IndxToolchanger"),
                    ("electronics", "Electronics"),
                ],
            );
            add_attribute_usages(
                &mut authored,
                "VoronTrident350.HeatedBed",
                &[
                    ("temperature", "Real", Some("22.0")),
                    ("targetTemp", "Real", Some("110.0")),
                    ("heatRate", "Real", Some("2.3")),
                    ("bedDimension", "Real", Some("350.0")),
                ],
            );
            add_attribute_usages(
                &mut authored,
                "VoronTrident350.Hotend",
                &[
                    ("temperature", "Real", Some("22.0")),
                    ("targetTemp", "Real", Some("250.0")),
                    ("heatRate", "Real", Some("5.0")),
                ],
            );
            add_attribute_usages(
                &mut authored,
                "VoronTrident350.CoreXYMotionSystem",
                &[
                    ("position_x", "Real", Some("0.0")),
                    ("position_y", "Real", Some("0.0")),
                ],
            );
            add_part_usages(
                &mut authored,
                "VoronTrident350",
                "CoreXYMotionSystem",
                &[("xCarriage", "XYCarriage"), ("zDrive", "ZLeadscrew")],
            );
            authored
                .set_attribute(
                    "VoronTrident350.CoreXYMotionSystem.zDrive".to_string(),
                    "multiplicity".to_string(),
                    &"3".into_bound_py_any(py).unwrap(),
                )
                .unwrap();
            add_attribute_usages(
                &mut authored,
                "VoronTrident350.IndxToolchanger",
                &[("activeTool", "Real", Some("0.0"))],
            );
            add_part_usages(
                &mut authored,
                "VoronTrident350",
                "IndxToolchanger",
                &[("dock", "ToolDock")],
            );
            authored
                .set_attribute(
                    "VoronTrident350.IndxToolchanger.dock".to_string(),
                    "multiplicity".to_string(),
                    &"6".into_bound_py_any(py).unwrap(),
                )
                .unwrap();
            add_attribute_usages(
                &mut authored,
                "VoronTrident350.ToolDock",
                &[("occupied", "Boolean", Some("true"))],
            );
            add_attribute_usages(
                &mut authored,
                "VoronTrident350.Electronics",
                &[
                    ("inputVoltage", "Real", Some("24.0")),
                    ("cpuLoad", "Real", Some("0.0")),
                ],
            );
            authored
                .add_usage(
                    "VoronTrident350".to_string(),
                    "individual part".to_string(),
                    "voron".to_string(),
                    Some("VoronPrinter".to_string()),
                    None,
                )
                .unwrap();
            let authored_model = authored.compile_model().unwrap();

            assert_snapshot_rows_match(
                &semantic_snapshot_rows(&opened_model.document),
                &semantic_snapshot_rows(&authored_model.document),
                &[
                    "VoronTrident350.VoronPrinter",
                    "VoronTrident350.VoronPrinter.buildVolume_x",
                    "VoronTrident350.VoronPrinter.bed",
                    "VoronTrident350.VoronPrinter.toolchanger",
                    "VoronTrident350.HeatedBed.temperature",
                    "VoronTrident350.Hotend.heatRate",
                    "VoronTrident350.CoreXYMotionSystem.zDrive",
                    "VoronTrident350.IndxToolchanger.dock",
                    "VoronTrident350.ToolDock.occupied",
                    "VoronTrident350.Electronics.inputVoltage",
                ],
                &["kind", "owner", "type"],
            );
            assert_snapshot_rows_match(
                &semantic_snapshot_rows(&opened_model.document),
                &semantic_snapshot_rows(&authored_model.document),
                &[
                    "VoronTrident350.CoreXYMotionSystem.zDrive",
                    "VoronTrident350.IndxToolchanger.dock",
                ],
                &["multiplicity", "multiplicity_lower", "multiplicity_upper"],
            );
        });
    }

    #[test]
    fn builder_can_defer_validation_until_requested() {
        let mut builder = PyModelBuilder::new(false).unwrap();

        let package_result = builder
            .add_package("model.sysml".to_string(), "Demo".to_string())
            .unwrap();
        assert_eq!(package_result.mode, "deferred");

        builder
            .add_definition(
                "Demo".to_string(),
                "part".to_string(),
                "Vehicle".to_string(),
                None,
            )
            .unwrap();

        let rendered = builder.rendered_files().unwrap();
        assert!(rendered["model.sysml"].contains("part def Vehicle"));

        let validation = builder.validate().unwrap();
        assert_eq!(validation.mode, "canonical_rewrite");
        assert!(validation.validation_ok);
        assert_eq!(validation.changed_files, vec!["model.sysml"]);
    }

    #[test]
    fn builder_can_set_abstract_attribute_and_render_sysml() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let mut builder = PyModelBuilder::new(true).unwrap();
            builder
                .add_package("model.sysml".to_string(), "Demo".to_string())
                .unwrap();
            builder
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "Vehicle".to_string(),
                    None,
                )
                .unwrap();

            let value = true.into_bound_py_any(py).unwrap();
            let result = builder
                .set_attribute("Demo.Vehicle".to_string(), "isAbstract".to_string(), &value)
                .unwrap();
            assert!(result.validation_ok);

            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("abstract part def Vehicle;"));

            let compiled = builder.compile_json().unwrap();
            assert!(compiled.contains("\"is_abstract\": true"));
        });
    }

    #[test]
    fn builder_exposes_native_authoring_mutation_coverage() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let mut builder = PyModelBuilder::new(true).unwrap();
            builder
                .add_package("model.sysml".to_string(), "Demo".to_string())
                .unwrap();
            builder
                .add_import(
                    "model.sysml".to_string(),
                    "Base::*".to_string(),
                    Some("Demo".to_string()),
                )
                .unwrap();
            builder
                .remove_import(
                    "model.sysml".to_string(),
                    "Base::*".to_string(),
                    Some("Demo".to_string()),
                )
                .unwrap();
            builder
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "RemoveMe".to_string(),
                    None,
                )
                .unwrap();
            builder
                .remove_declaration("Demo.RemoveMe".to_string())
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(!rendered.contains("part def RemoveMe"));

            builder
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "BaseVehicle".to_string(),
                    None,
                )
                .unwrap();
            builder
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "Vehicle".to_string(),
                    None,
                )
                .unwrap();
            builder
                .update_specializations("Demo.Vehicle".to_string(), vec!["BaseVehicle".to_string()])
                .unwrap();
            builder
                .add_metadata_annotation(
                    "Demo.Vehicle".to_string(),
                    "Doc".to_string(),
                    Some(BTreeMap::from([(
                        "text".to_string(),
                        "Vehicle documentation".to_string(),
                    )])),
                )
                .unwrap();
            builder
                .add_definition(
                    "Demo".to_string(),
                    "requirement".to_string(),
                    "MassLimit".to_string(),
                    None,
                )
                .unwrap();
            builder
                .add_relationship(
                    "Demo.Vehicle".to_string(),
                    "satisfy".to_string(),
                    "Demo.Vehicle".to_string(),
                    "Demo.MassLimit".to_string(),
                )
                .unwrap();

            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(!rendered.contains("import Base::*"));
            assert!(rendered.contains("part def Vehicle specializes BaseVehicle"));
            assert!(rendered.contains("@Doc"));
            assert!(rendered.contains("text = \"Vehicle documentation\";"));
            assert!(rendered.contains("satisfy requirement MassLimit;"));

            builder
                .add_relationship(
                    "Demo".to_string(),
                    "flow".to_string(),
                    "Demo.Vehicle".to_string(),
                    "Demo.MassLimit".to_string(),
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("flow from Demo.Vehicle to Demo.MassLimit;"));

            builder
                .add_usage(
                    "Demo".to_string(),
                    "perform".to_string(),
                    "providePower".to_string(),
                    None,
                    None,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("perform action providePower;"));

            builder
                .add_definition(
                    "Demo".to_string(),
                    "action".to_string(),
                    "ProvidePower".to_string(),
                    None,
                )
                .unwrap();
            let value = "first start;\nthen done;".into_bound_py_any(py).unwrap();
            builder
                .set_attribute(
                    "Demo.ProvidePower".to_string(),
                    "rawBody".to_string(),
                    &value,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("first start;"));
            assert!(rendered.contains("then done;"));

            builder
                .add_definition(
                    "Demo".to_string(),
                    "constraint".to_string(),
                    "MassConstraint".to_string(),
                    None,
                )
                .unwrap();
            builder
                .add_usage(
                    "Demo".to_string(),
                    "constraint".to_string(),
                    "massConstraint".to_string(),
                    Some("MassConstraint".to_string()),
                    None,
                )
                .unwrap();
            let value = "in totalMass = mass;".into_bound_py_any(py).unwrap();
            builder
                .set_attribute(
                    "Demo.massConstraint".to_string(),
                    "rawBody".to_string(),
                    &value,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("constraint massConstraint: MassConstraint {"));
            assert!(rendered.contains("in totalMass = mass;"));

            builder
                .add_usage(
                    "Demo".to_string(),
                    "occurrence".to_string(),
                    "publish".to_string(),
                    None,
                    None,
                )
                .unwrap();
            builder
                .add_usage(
                    "Demo".to_string(),
                    "part".to_string(),
                    "vehicle1".to_string(),
                    Some("Vehicle".to_string()),
                    None,
                )
                .unwrap();
            let value = true.into_bound_py_any(py).unwrap();
            builder
                .set_attribute(
                    "Demo.vehicle1".to_string(),
                    "isIndividual".to_string(),
                    &value,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("occurrence publish;"));
            assert!(rendered.contains("individual part vehicle1: Vehicle;"));

            builder
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "ExtraVehicle".to_string(),
                    None,
                )
                .unwrap();
            let value = "ExtraVehicle".into_bound_py_any(py).unwrap();
            builder
                .add_attribute_value(
                    "Demo.Vehicle".to_string(),
                    "specializes".to_string(),
                    &value,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("BaseVehicle, ExtraVehicle"));

            builder
                .remove_attribute_value(
                    "Demo.Vehicle".to_string(),
                    "specializes".to_string(),
                    &value,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(!rendered.contains("BaseVehicle, ExtraVehicle"));

            builder
                .add_definition(
                    "Demo".to_string(),
                    "part".to_string(),
                    "BaseFeature".to_string(),
                    None,
                )
                .unwrap();
            let value = "BaseFeature".into_bound_py_any(py).unwrap();
            builder
                .add_usage(
                    "Demo".to_string(),
                    "part".to_string(),
                    "vehicle".to_string(),
                    Some("Vehicle".to_string()),
                    None,
                )
                .unwrap();
            builder
                .add_attribute_value(
                    "Demo.vehicle".to_string(),
                    "additional_types".to_string(),
                    &value,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("part vehicle: Vehicle :> BaseFeature"));

            let value = "Vehicle".into_bound_py_any(py).unwrap();
            builder
                .set_attribute(
                    "Demo.vehicle".to_string(),
                    "reference_target".to_string(),
                    &value,
                )
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("references Vehicle"));
            builder
                .clear_attribute("Demo.vehicle".to_string(), "reference_target".to_string())
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(!rendered.contains("references Vehicle"));

            let value = "Vehicle usage".into_bound_py_any(py).unwrap();
            builder
                .set_attribute("Demo.vehicle".to_string(), "doc".to_string(), &value)
                .unwrap();
            let value = true.into_bound_py_any(py).unwrap();
            builder
                .set_attribute("Demo.vehicle".to_string(), "isEnd".to_string(), &value)
                .unwrap();
            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("doc /* Vehicle usage */"));
            assert!(rendered.contains("end part vehicle: Vehicle"));
        });
    }

    #[test]
    fn builder_recreates_pilot_state_definition_example_1_subset() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let mut builder = PyModelBuilder::new(true).unwrap();
            builder
                .add_package(
                    "model.sysml".to_string(),
                    "State Definition Example-1".to_string(),
                )
                .unwrap();
            for signal in ["VehicleStartSignal", "VehicleOnSignal", "VehicleOffSignal"] {
                builder
                    .add_definition(
                        "State Definition Example-1".to_string(),
                        "attribute".to_string(),
                        signal.to_string(),
                        None,
                    )
                    .unwrap();
            }
            builder
                .add_definition(
                    "State Definition Example-1".to_string(),
                    "state".to_string(),
                    "VehicleStates".to_string(),
                    None,
                )
                .unwrap();
            for state in ["off", "starting", "on"] {
                builder
                    .add_usage(
                        "State Definition Example-1.VehicleStates".to_string(),
                        "state".to_string(),
                        state.to_string(),
                        None,
                        None,
                    )
                    .unwrap();
            }
            for (name, source, trigger, target) in [
                ("off_to_starting", "off", "VehicleStartSignal", "starting"),
                ("starting_to_on", "starting", "VehicleOnSignal", "on"),
                ("on_to_off", "on", "VehicleOffSignal", "off"),
            ] {
                let qname = format!("State Definition Example-1.VehicleStates.{name}");
                builder
                    .add_usage(
                        "State Definition Example-1.VehicleStates".to_string(),
                        "transition".to_string(),
                        name.to_string(),
                        None,
                        None,
                    )
                    .unwrap();
                let value = source.into_bound_py_any(py).unwrap();
                builder
                    .set_attribute(qname.clone(), "transitionSource".to_string(), &value)
                    .unwrap();
                let value = trigger.into_bound_py_any(py).unwrap();
                builder
                    .set_attribute(qname.clone(), "trigger".to_string(), &value)
                    .unwrap();
                let value = target.into_bound_py_any(py).unwrap();
                builder
                    .set_attribute(qname, "transitionTarget".to_string(), &value)
                    .unwrap();
            }

            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("package 'State Definition Example-1'"));
            assert!(rendered.contains("attribute def VehicleStartSignal;"));
            assert!(rendered.contains("state def VehicleStates {"));
            assert!(rendered.contains("state off;"));
            assert!(rendered.contains(
                "transition off_to_starting first off accept VehicleStartSignal then starting;"
            ));
            assert!(rendered.contains(
                "transition starting_to_on first starting accept VehicleOnSignal then on;"
            ));
            assert!(
                rendered
                    .contains("transition on_to_off first on accept VehicleOffSignal then off;")
            );
            builder.compile_json().unwrap();
        });
    }

    #[test]
    fn builder_recreates_pilot_metadata_example_1_subset() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let mut builder = PyModelBuilder::new(true).unwrap();
            builder
                .add_package("model.sysml".to_string(), "Metadata Example-1".to_string())
                .unwrap();
            builder
                .add_definition(
                    "Metadata Example-1".to_string(),
                    "metadata".to_string(),
                    "SafetyFeature".to_string(),
                    None,
                )
                .unwrap();
            builder
                .add_definition(
                    "Metadata Example-1".to_string(),
                    "metadata".to_string(),
                    "SecurityFeature".to_string(),
                    None,
                )
                .unwrap();
            let annotated = vec![
                "SysML::PartDefinition".to_string(),
                "SysML::PartUsage".to_string(),
            ]
            .into_bound_py_any(py)
            .unwrap();
            builder
                .set_attribute(
                    "Metadata Example-1.SecurityFeature".to_string(),
                    "annotatedElements".to_string(),
                    &annotated,
                )
                .unwrap();

            builder
                .add_usage(
                    "Metadata Example-1".to_string(),
                    "part".to_string(),
                    "vehicle".to_string(),
                    None,
                    None,
                )
                .unwrap();
            for section in ["interior", "bodyAssy"] {
                builder
                    .add_usage(
                        "Metadata Example-1.vehicle".to_string(),
                        "part".to_string(),
                        section.to_string(),
                        None,
                        None,
                    )
                    .unwrap();
            }
            for part in ["alarm", "seatBelt", "frontSeat", "driverAirBag"] {
                builder
                    .add_usage(
                        "Metadata Example-1.vehicle.interior".to_string(),
                        "part".to_string(),
                        part.to_string(),
                        None,
                        None,
                    )
                    .unwrap();
            }
            for (part, multiplicity) in [("seatBelt", "2"), ("frontSeat", "2")] {
                let value = multiplicity.into_bound_py_any(py).unwrap();
                builder
                    .set_attribute(
                        format!("Metadata Example-1.vehicle.interior.{part}"),
                        "multiplicity".to_string(),
                        &value,
                    )
                    .unwrap();
            }
            for part in ["body", "bumper", "keylessEntry"] {
                builder
                    .add_usage(
                        "Metadata Example-1.vehicle.bodyAssy".to_string(),
                        "part".to_string(),
                        part.to_string(),
                        None,
                        None,
                    )
                    .unwrap();
            }

            for (metadata_type, targets) in [
                (
                    "SafetyFeature",
                    vec![
                        "vehicle::interior::seatBelt".to_string(),
                        "vehicle::interior::driverAirBag".to_string(),
                        "vehicle::bodyAssy::bumper".to_string(),
                    ],
                ),
                (
                    "SecurityFeature",
                    vec![
                        "vehicle::interior::alarm".to_string(),
                        "vehicle::bodyAssy::keylessEntry".to_string(),
                    ],
                ),
            ] {
                builder
                    .add_usage(
                        "Metadata Example-1".to_string(),
                        "metadata".to_string(),
                        metadata_type.to_string(),
                        None,
                        None,
                    )
                    .unwrap();
                let value = targets.into_bound_py_any(py).unwrap();
                builder
                    .set_attribute(
                        format!("Metadata Example-1.{metadata_type}"),
                        "referenceTarget".to_string(),
                        &value,
                    )
                    .unwrap();
            }

            let rendered = builder.render_file("model.sysml".to_string()).unwrap();
            assert!(rendered.contains("package 'Metadata Example-1'"));
            assert!(rendered.contains("metadata def SafetyFeature;"));
            assert!(rendered.contains("metadata def SecurityFeature {"));
            assert!(rendered.contains(":> annotatedElement : SysML::PartDefinition;"));
            assert!(rendered.contains(":> annotatedElement : SysML::PartUsage;"));
            assert!(rendered.contains("part seatBelt[2];"));
            assert!(rendered.contains("part frontSeat[2];"));
            assert!(rendered.contains("metadata SafetyFeature about vehicle::interior::seatBelt, vehicle::interior::driverAirBag, vehicle::bodyAssy::bumper;"));
            assert!(rendered.contains("metadata SecurityFeature about vehicle::interior::alarm, vehicle::bodyAssy::keylessEntry;"));
            builder.compile_json().unwrap();
        });
    }

    #[test]
    fn session_fork_python_surface_builds_and_commits_generated_package() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let cls = PyType::new::<PyModelWorkspace>(py);
            let workspace = PyModelWorkspace::empty(&cls).unwrap();
            let session = workspace.session();
            let mut fork = session.fork("python session".to_string());
            let package = fork
                .package("SyntheticRequirements".to_string(), None)
                .unwrap();
            fork.requirements(
                &package,
                vec![
                    (
                        "Req00001".to_string(),
                        "Generated requirement 1".to_string(),
                    ),
                    (
                        "Req00002".to_string(),
                        "Generated requirement 2".to_string(),
                    ),
                ],
            )
            .unwrap();
            fork.part(&package, "controller".to_string(), None).unwrap();

            let result = fork.commit("rewrite_source").unwrap();

            assert_eq!(result.strategy_used, "rewrite_generated_source");
            assert_eq!(result.generated_elements, 4);
            assert!(
                result.edited_files["generated/synthetic_requirements.model"]
                    .contains("requirement Req00001")
            );
            assert!(
                result.edited_files["generated/synthetic_requirements.model"]
                    .contains("part controller")
            );
        });
    }

    #[test]
    fn descriptor_source_roots_limit_native_source_collection() {
        let root = temp_dir("descriptor_source_roots");
        write_file(&root.join("model").join("main.sysml"), "package Demo {}\n");
        write_file(
            &root.join("ignored").join("other.sysml"),
            "not valid sysml on purpose",
        );
        write_file(
            &root.join(".project.json"),
            r#"{
  "schema": "dev.mercurio.project.v2",
  "version": 2,
  "model": {
    "sourceRoots": ["model"]
  }
}"#,
        );

        let files = project_sources_from_descriptor(&root.join(".project.json"))
            .unwrap()
            .files;

        assert_eq!(files.len(), 1);
        assert!(files.contains_key("model/main.sysml"));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn descriptor_entrypoints_override_source_roots() {
        let root = temp_dir("descriptor_entrypoints");
        write_file(&root.join("model").join("main.sysml"), "package Main {}\n");
        write_file(
            &root.join("model").join("extra.sysml"),
            "package Extra {}\n",
        );
        write_file(
            &root.join(".project.json"),
            r#"{
  "schema": "dev.mercurio.project.v2",
  "version": 2,
  "model": {
    "sourceRoots": ["model"],
    "entrypoints": ["model/main.sysml"]
  }
}"#,
        );

        let files = project_sources_from_descriptor(&root.join(".project.json"))
            .unwrap()
            .files;

        assert_eq!(files.len(), 1);
        assert!(files.contains_key("model/main.sysml"));
        assert!(!files.contains_key("model/extra.sysml"));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn descriptor_dependencies_resolve_native_library_context() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_| {
            let root = temp_dir("descriptor_dependencies");
            write_file(&root.join("model").join("main.sysml"), "package Demo {}\n");
            write_file(
                &root.join("dependency.kir.json"),
                r#"{
  "metadata": {
    "kir_schema_version": "0.2"
  },
  "elements": [
    {
      "id": "Dependency::Thing",
      "kind": "PartDefinition",
      "layer": 1,
      "properties": {}
    }
  ]
}"#,
            );
            write_file(
                &root.join(".project.json"),
                r#"{
  "schema": "dev.mercurio.project.v2",
  "version": 2,
  "model": {
    "entrypoints": ["model/main.sysml"]
  },
  "dependencies": [
    {
      "id": "dependency",
      "role": "baseline",
      "provider": {
        "kind": "precompiled_kir_artifact",
        "path": "dependency.kir.json"
      }
    }
  ]
}"#,
            );

            let sources =
                super::project_sources_from_descriptor(&root.join(".project.json")).unwrap();

            assert!(sources.library_context_document.is_some());
            assert!(
                !sources
                    .library_context_document
                    .as_ref()
                    .unwrap()
                    .elements
                    .is_empty()
            );
            std::fs::remove_dir_all(root).unwrap();
        });
    }

    #[test]
    fn native_compile_accepts_project_descriptor_path() {
        let root = temp_dir("descriptor_compile");
        write_file(
            &root.join("model").join("main.sysml"),
            "package Demo { part def Thing; }\n",
        );
        write_file(
            &root.join(".project.json"),
            r#"{
  "schema": "dev.mercurio.project.v2",
  "version": 2,
  "model": {
    "entrypoints": ["model/main.sysml"]
  }
}"#,
        );

        let document = compile_workspace_path(&root.join(".project.json")).unwrap();

        assert!(
            document
                .elements
                .iter()
                .any(|element| element.id == "type.Demo.Thing")
        );
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn model_builder_from_project_uses_descriptor_source_set() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let root = temp_dir("builder_from_project");
            write_file(&root.join("model").join("main.sysml"), "package Main {}\n");
            write_file(
                &root.join("ignored").join("other.sysml"),
                "package Other {}\n",
            );
            write_file(
                &root.join(".project.json"),
                r#"{
  "schema": "dev.mercurio.project.v2",
  "version": 2,
  "model": {
    "entrypoints": ["model/main.sysml"]
  }
}"#,
            );

            let cls = PyType::new::<PyModelBuilder>(py);
            let builder = PyModelBuilder::from_project(&cls, root.clone(), true).unwrap();
            let rendered = builder.rendered_files().unwrap();

            assert_eq!(rendered.len(), 1);
            assert!(rendered.contains_key("model/main.sysml"));
            assert!(!rendered.contains_key("ignored/other.sysml"));
            std::fs::remove_dir_all(root).unwrap();
        });
    }

    fn temp_dir(label: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!(
            "mercurio_python_{label}_{}_{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).unwrap();
        root
    }

    fn write_file(path: &Path, content: &str) {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(path, content).unwrap();
    }

    fn add_sensor_definition(
        builder: &mut PyModelBuilder,
        name: &str,
        attributes: &[(&str, &str)],
    ) {
        add_part_definition_with_attributes(builder, "SensorSystem", name, attributes);
    }

    fn add_part_definition_with_attributes(
        builder: &mut PyModelBuilder,
        package_name: &str,
        name: &str,
        attributes: &[(&str, &str)],
    ) {
        builder
            .add_definition(
                package_name.to_string(),
                "part".to_string(),
                name.to_string(),
                None,
            )
            .unwrap();
        for (attribute_name, ty) in attributes {
            builder
                .add_usage(
                    format!("{package_name}.{name}"),
                    "attribute".to_string(),
                    (*attribute_name).to_string(),
                    Some((*ty).to_string()),
                    None,
                )
                .unwrap();
        }
    }

    fn add_part_usages(
        builder: &mut PyModelBuilder,
        package_name: &str,
        definition_name: &str,
        parts: &[(&str, &str)],
    ) {
        for (part_name, ty) in parts {
            builder
                .add_usage(
                    format!("{package_name}.{definition_name}"),
                    "part".to_string(),
                    (*part_name).to_string(),
                    Some((*ty).to_string()),
                    None,
                )
                .unwrap();
        }
    }

    fn add_attribute_usages(
        builder: &mut PyModelBuilder,
        container: &str,
        attributes: &[(&str, &str, Option<&str>)],
    ) {
        for (attribute_name, ty, expression) in attributes {
            builder
                .add_usage(
                    container.to_string(),
                    "attribute".to_string(),
                    (*attribute_name).to_string(),
                    Some((*ty).to_string()),
                    None,
                )
                .unwrap();
            if let Some(expression) = expression {
                builder
                    .set_expression(
                        format!("{container}.{attribute_name}"),
                        Some((*expression).to_string()),
                    )
                    .unwrap();
            }
        }
    }

    fn snapshot_row<'a>(
        rows: &'a [BTreeMap<String, serde_json::Value>],
        qualified_name: &str,
    ) -> &'a BTreeMap<String, serde_json::Value> {
        rows.iter()
            .find(|row| {
                row.get("qualified_name").and_then(|value| value.as_str()) == Some(qualified_name)
            })
            .unwrap_or_else(|| panic!("missing semantic snapshot row for {qualified_name}"))
    }

    fn assert_snapshot_rows_match(
        left: &[BTreeMap<String, serde_json::Value>],
        right: &[BTreeMap<String, serde_json::Value>],
        qualified_names: &[&str],
        fields: &[&str],
    ) {
        for qualified_name in qualified_names {
            let left_row = snapshot_row(left, qualified_name);
            let right_row = snapshot_row(right, qualified_name);
            for field in fields {
                assert_eq!(
                    left_row.get(*field),
                    right_row.get(*field),
                    "{qualified_name}.{field}"
                );
            }
        }
    }
}
