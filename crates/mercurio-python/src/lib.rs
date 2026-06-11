use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::{Arc, OnceLock};

use mercurio_core::{
    AttributeWritePolicy, AuthoringProject, CommitMode, CommitResult, CommitStrategy,
    ContainerSelector, ElementView, ForkElement, Graph, KirDocument, MetamodelAttributeRegistry,
    ModelFork, ModelSession, ModelWorkspace, Mutation, QualifiedName, SemanticEdit, SessionError,
    WorkspaceSnapshot, WriteBackMode, WriteBackResult, default_language_profile,
    generate_python_wrappers,
};
use mercurio_sysml::{
    StdlibLocator, SysmlModelForkExt, compile_sysml_text, load_authoring_project_from_sysml,
    load_sysml_baseline, resolve_default_stdlib_locator,
};
use mercurio_view_model::{
    ElementDetailsDto, PartDto, element_details_from_graph, parts_from_graph,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyType};

static DEFAULT_STDLIB_DOCUMENT: OnceLock<Result<KirDocument, String>> = OnceLock::new();

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
}

#[pymethods]
impl PyWorkspace {
    #[staticmethod]
    fn open(path: &str) -> PyResult<Self> {
        let document = compile_workspace_path(Path::new(path))?;
        let graph = Graph::from_document(document.clone())
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(Self {
            document: Arc::new(document),
            graph: Arc::new(graph),
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

    fn compile(&self) -> PyResult<PySemanticModel> {
        py_semantic_model((*self.document).clone())
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

    fn generate_python_wrappers(&self, module_name: String) -> PyResult<BTreeMap<String, String>> {
        let profile =
            default_language_profile().map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(generate_python_wrappers(&self.document, &profile, &module_name).files)
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
        let stdlib = default_stdlib_document()?;
        let mut documents = Vec::new();
        for (path, content) in rendered {
            documents.push(
                compile_sysml_text(&content, &path, stdlib)
                    .map_err(|err| PyValueError::new_err(err.to_string()))?,
            );
        }
        KirDocument::merge(documents).map_err(|err| PyRuntimeError::new_err(err.to_string()))
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

fn compile_workspace_path(path: &Path) -> PyResult<KirDocument> {
    if path.is_file() {
        let source = std::fs::read_to_string(path).map_err(io_error)?;
        return compile_sysml_text(
            &source,
            &path.display().to_string(),
            default_stdlib_document()?,
        )
        .map_err(|err| PyValueError::new_err(err.to_string()));
    }

    if !path.is_dir() {
        return Err(PyValueError::new_err(format!(
            "workspace path does not exist: {}",
            path.display()
        )));
    }

    let mut files = BTreeMap::new();
    collect_sysml_files(path, path, &mut files)?;
    if files.is_empty() {
        return Err(PyValueError::new_err(format!(
            "workspace contains no .sysml files: {}",
            path.display()
        )));
    }
    let project = load_authoring_project_from_sysml(files).map_err(authoring_error)?;
    project.compile_kir_document().map_err(authoring_error)
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
        if path.extension().and_then(|value| value.to_str()) != Some("sysml") {
            continue;
        }
        let relative = path
            .strip_prefix(root)
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?
            .to_string_lossy()
            .replace('\\', "/");
        let source = std::fs::read_to_string(&path).map_err(io_error)?;
        files.insert(relative, source);
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
    use super::{PyModelBuilder, PyModelWorkspace};
    use pyo3::IntoPyObjectExt;
    use pyo3::Python;
    use pyo3::types::PyType;

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
}
