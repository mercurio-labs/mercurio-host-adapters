# Mercurio Python API Reference

This document describes the Python package in `mercurio-host-adapters/python`.
It covers the user-facing SDK, the source-backed authoring/session layer, the
Lab extension hooks, the advanced HTTP client helpers, the native PyO3 surface,
and the `mercurio_capability` process-provider SDK.

The release-facing API is intentionally small. Most user scripts should only
need:

```python
import mercurio
from mercurio import model

with mercurio.open("C:/models/demo") as runtime_model:
    rows = runtime_model.query("model.parts().count()")
    trace = runtime_model.analysis("PrintSequence").trace()

project = mercurio.create(package="Demo")
project.add(model.part("engine").typed("Engine"))
snapshot = project.compile()
```

The lower-level classes and raw DTOs remain documented for advanced integrations
and tests, but they are not the first-release mental model.

The package uses Python names in `snake_case`. Raw REST and KIR payloads may use
`camelCase`; helpers generally accept either where the backend already emits
both forms. Unless a section says otherwise, `JsonObject` means
`dict[str, Any]`.

## Runtime Modes

`mercurio.open()` chooses a runtime as follows:

1. In Lab kernel mode (`MERCURIO_LAB_KERNEL=1`) and with no path, it returns a
   `LabModel`.
2. If `mercurio._core` is importable and `executable` is not supplied, it opens
   the model in-process through the native PyO3 binding.
3. Otherwise it launches a Mercurio HTTP sidecar and returns a sidecar-backed
   `Model`.

The sidecar executable is discovered in this order:

1. Explicit `executable=...`.
2. `MERCURIO_EXE`.
3. `mercurio` on `PATH`.
4. A bundled `mercurio/bin/mercurio(.exe)` next to the Python package.

Use an explicit `executable=` when you need sidecar-only features even though the
native module is installed.

## Top-Level Package: `mercurio`

```python
import mercurio
```

### Functions

| API | Description |
| --- | --- |
| `mercurio.open(path=None, *, executable=None, timeout=60.0) -> Model | LabModel` | Open a model or Lab session. `path` is required outside Lab kernel mode. |
| `mercurio.create(path=None, *, package=None, stdlib=True, validate_each_mutation=True) -> Project` | Create a mutable project. Omit `path` for a fully in-memory project until `save(path)` is called. |
| `mercurio.project(path, *, validate=True) -> Project` | Open a mutable source-backed project session. |

### Common Exports

The top-level package intentionally exposes only `Model`, `Project`, `open`,
`create`, and `project`. Declaration factories live in `mercurio.model`:

| API | Description |
| --- | --- |
| `model.part(name)`, `model.part_def(name)` | Part usage and definition declarations. |
| `model.attr(name)`, `model.attr_def(name)` | Attribute usage and definition declarations. |
| `model.item(name)`, `model.item_def(name)` | Item usage and definition declarations. |
| `model.port(name)`, `model.port_def(name)` | Port usage and definition declarations. |
| `model.connection(name)`, `model.connection_def(name)` | Connection usage and definition declarations. |
| `model.action(name)`, `model.action_def(name)` | Action usage and definition declarations. |
| `model.constraint(name)`, `model.constraint_def(name)` | Constraint usage and definition declarations. |
| `model.analysis(name)`, `model.analysis_def(name)` | Analysis usage and definition declarations. |
| `model.requirement_def(name)` | Requirement definition declarations. |
| `model.state(name)`, `model.state_def(name)`, `model.transition(name)` | State-machine declarations. |

Implementation classes such as `ProjectSession`, `CompiledModel`, `SemanticRef`,
`ModelBuilder`, and the low-level DTOs remain importable from their owning
modules for advanced integrations, but they are not re-exported from
`import mercurio`.

## Opened Model API

`Model` is created by `mercurio.open(path)`. Use it as a context manager for
sidecar-backed models so the backend process is closed.

```python
with mercurio.open("C:/models/demo") as model:
    graph = model.graph()
```

### `Model`

| API | Description |
| --- | --- |
| `Model.from_native(workspace) -> Model` | Build a `Model` around a native `PyWorkspace`. |
| `parts() -> list[PartRef]` | Return part references sorted by model containment depth. |
| `part(name_or_id: str) -> PartRef` | Find a part by declared name or element id. Raises `KeyError` if missing. |
| `analysis_cases() -> list[AnalysisCaseInfo]` | List executable analysis cases. |
| `analysis_specs() -> list[AnalysisSpec]` | List inspectable analysis specs. |
| `analysis_case_spec(name_or_id: str) -> AnalysisSpec` | Find an analysis spec by case id or label. |
| `analysis(name_or_id) -> AnalysisHandle` | Return a small handle with `spec()`, `run(run_id=None)`, and `trace(run_id=None)`. |
| `run_analysis_report(case_id, *, run_id=None) -> AnalysisRunReport` | Run an analysis case and return the full report. |
| `run_analysis(case_id) -> SimulationTrace` | Convenience for `run_analysis_report(...).simulation_trace()`. |
| `model_metadata() -> JsonObject` | Return model metadata or raw model object, depending on backend. |
| `graph(scope="l2") -> JsonObject` | Return the shared graph view. |
| `search(query: str) -> list[JsonObject]` | Search model elements. |
| `element_details(element_id: str) -> JsonObject` | Return detailed element information. |
| `l2_explorer(seed_id, *, expanded_parents=None, expanded_children=None, include_reference_edges=True) -> JsonObject` | Return the L2 explorer graph for a seed element. |
| `metatype_explorer(seed_id, *, expanded_parents=None, expanded_children=None) -> JsonObject` | Return the metatype explorer graph for a seed element. |
| `render_view(document: JsonObject) -> JsonObject` | Render a Mercurio view document. Native mode currently supports parameterized `explorer.l2` and `explorer.metatype`. |
| `l2_explorer_view(...) -> JsonObject` | Render an `explorer.l2` view document. |
| `metatype_explorer_view(...) -> JsonObject` | Render an `explorer.metatype` view document. |
| `semantic_snapshot_json() -> str` | Return native semantic snapshot JSON. Requires native mode. |
| `run_cell(source, *, kind="query", language="mercurio_dsl", parameters=None, cell_id=None, session_id=None) -> CellRunReport` | Run through the shared session/cell API. |
| `query(source) -> object` | Run a Mercurio DSL query and return the `result` output value. |
| `dsl(source) -> object` | Run a Mercurio DSL query and return the `result` output value. |
| `query_dsl(source) -> object` | Alias for `dsl()`. |
| `run_action_dsl(source, *, cell_id=None, session_id=None) -> CellRunReport` | Run an action DSL cell. |
| `action_dsl(source) -> object` | Return the action DSL `result` output value. |
| `preview_dsl(source) -> object` | Alias for `action_dsl()`. |
| `run_analysis_dsl(source, *, run_id=None, capability_id="mercurio.dsl.analysis", subject_element_id=None, cell_id=None, session_id=None) -> CellRunReport` | Run an analysis DSL cell. |
| `analysis_dsl(source, *, run_id=None, capability_id="mercurio.dsl.analysis", subject_element_id=None) -> JsonObject` | Return the capability report from an analysis DSL cell. |
| `dsl_schema() -> JsonObject` | Return the DSL schema/introspection payload. |
| `close() -> None` | Close a sidecar project and backend process. Native models are no-op. |

### Raw Escape Hatch

`model.raw` exposes raw KIR-shaped responses.

| API | Description |
| --- | --- |
| `model.raw.graph(scope=None) -> JsonObject` | Raw graph payload. Native mode only supports the default compiled graph scope. |
| `model.raw.model() -> JsonObject` | Raw model payload. |
| `model.raw.element(element_id) -> JsonObject | None` | Raw element payload. |

## Runtime DTOs: `mercurio.models`

These dataclasses wrap common backend payloads.

### Backend And Project DTOs

| Type | Fields and APIs |
| --- | --- |
| `VersionInfo` | `service`, `version`, `api_version`; `from_json(data)`. |
| `SysmlReleaseInfo` | `release`, `selector`, `profile_id`, `status`, `sysml_version`, `pilot_release_tag`, `pilot_implementation_version`, `stdlib_locator`, `python_wrapper_module`, `aliases`; `from_json(data)`, `matches(selector)`. |
| `BackendStartupInfo` | `url`, `pid`, `version`, `api_version`; `from_json(data)`. |
| `ProjectInfo` / `WorkspaceInfo` | `project_id`, `project_root`, `active_path`, `project`; `workspace_id`, `workspace_root`; `from_open_json(data)`, `from_summary_json(data)`. |
| `SemanticProjectResult` | Wraps a semantic compile payload. Properties: `ok`, `file_count`, `success_count`, `failure_count`, `results`. |

### Analysis DTOs

| Type | Fields and APIs |
| --- | --- |
| `AnalysisCaseInfo` | `id`, `label`, `subject_count`; `from_json(data)`. |
| `AnalysisElementRef` | `element_id`, `kind`, `label`; `from_json(data)`. |
| `AnalysisExpectedArtifact` | `kind`, `schema`; `from_json(data)`. |
| `AnalysisReadinessDiagnostic` | `severity`, `code`, `message`, `element_id`; `from_json(data)`. |
| `AnalysisClockConfig` | `max_steps`, `step_duration_s`, `max_time_s`, `fixed_step_s`, `sample_interval_s`, `change_loop_limit`; `from_json(data)`. |
| `AnalysisExecutionContext` | `initial_values`, `clock`, `provider_bindings`; `from_json(data)`. |
| `AnalysisExecutionStep` | `kind`, `label`, `techniques`, `elements`; `from_json(data)`. |
| `AnalysisExecutionPlan` | `steps`; `from_json(data)`. |
| `AnalysisDynamicBehaviorBinding` | `subject`, `behavior`, `kind`; `from_json(data)`. |
| `AnalysisSpec` | `case_ref`, `model_revision`, `subjects`, `inputs`, `assumptions`, `objectives`, `calculations`, `constraints`, `requirements`, `verification_cases`, `views`, `concerns`, `techniques`, `dynamic_behavior_bindings`, `execution_context`, `execution_plan`, `expected_artifacts`, `readiness`, `readiness_diagnostics`; `from_json(data)`. |

### Report, Evidence, And Trace DTOs

| Type | Fields and APIs |
| --- | --- |
| `SemanticElementRef` | `element_id`, `qualified_name`, `label`; `from_json(data)`. |
| `SemanticArtifact` | `id`, `kind`, `schema`, `digest`, `element_refs`, `payload`; `from_json(data)`. |
| `EvidenceNode` | `id`, `kind`, `label`, `element_refs`, `properties`; `from_json(data)`. |
| `EvidenceEdge` | `source_id`, `target_id`, `relation`; `from_json(data)`. |
| `EvidenceGraph` | `nodes`, `edges`; `from_json(data)`. |
| `SemanticDiagnostic` | `code`, `severity`, `message`, `element`; `from_json(data)`. |
| `AnalysisRunReport` | `run_id`, `capability_id`, `status`, `target`, `insights`, `artifacts`, `evidence`, `diagnostics`, `limitations`; `artifact(kind)`, `simulation_trace()`, `constraint_summary()`, `activity_summary()`. |
| `TraceChannel` | `id`, `unit`, `source`; `from_json(data)`. |
| `ChannelData` | `channel_id`, `times`, `values`; `as_pairs()`. |
| `StateData` | `subject_id`, `times`, `states`. |
| `SimulationTrace` | `scenario_id`, `subject_id`, `channels`, `status`, `duration`; `channel(channel_id)`, `states(subject_id)`, `from_json(data)`. |
| `PartRef` | `id`, `name`, `kind`, `element_kind`, `parent`, `depth`; `attr(name, default=None)`, `attrs()`, `children(all_parts)`, `from_json(data, parent_lookup)`. |

## Source-Backed Sessions: `mercurio.session`

The session layer is for mutable source-backed projects, immutable compiled
snapshots, semantic queries, transactions, variants, and declarative simulation
configuration.

### Semantic References

`SemanticRef` is an immutable handle to one element in one compiled revision.

| API | Description |
| --- | --- |
| `qualified_name: str` | Stable qualified name in the compiled snapshot. |
| `kind: str` | KIR kind or SysML/KerML metaclass-derived kind. |
| `data: Mapping[str, Any]` | Frozen row data from the semantic snapshot. |
| `revision: str` | Revision hash of the owning `CompiledModel`. |
| `name: str` | Last segment of `qualified_name`. |
| `declared_name: str` | Declared name when available, otherwise `name`. |
| `model_layer: str` | Layer label such as `foundation`, `library`, `user`, or `derived`. |
| `metatype_name: str | None` | Direct metatype name when available. |
| `metatype_chain: list[str]` | Direct and inherited metatype names. |
| `attr(name, default=None)`, `get(name, default=None)` | Read row attributes. |
| `attrs() -> JsonObject` | Copy of row attributes. |
| `owner() -> str | None` | Owning qualified name or id. |
| `type_name() -> str | None` | First type/typed-by value. |
| `specializes() -> list[str]` | Specialization targets. |
| `is_metatype(expected, *, include_subtypes=True) -> bool` | Metatype match helper. |
| `children() -> list[SemanticRef]` | Direct contained children. |
| `walk() -> Iterable[SemanticRef]` | Depth-first containment traversal from this ref. |

Specialized refs:

| Type | API |
| --- | --- |
| `PartDefRef` | Adds `subtypes(*, transitive=True) -> list[PartDefRef]`. |
| `PartUsageRef` | No extra methods. |

### Query APIs

| API | Description |
| --- | --- |
| `SemanticQuery(refs)` | Chainable read-only query over refs. |
| `SemanticQuery.refs()`, `count()`, `first()` | Materialize or summarize refs. |
| `where(predicate)` | Filter with a Python predicate. |
| `where_kind_contains(text)` | Filter by substring in `kind`. |
| `where_metatype(expected)` | Filter by direct metatype. |
| `where_metatype_is(expected)` | Filter by direct or inherited metatype. |
| `where_model_layer(expected)` | Filter by model layer label. |
| `order_by(field)` | Sort by a selected field. |
| `select(fields) -> list[JsonObject]` | Project refs to records. Supported synthetic fields include `qualified_name`, `name`, `declared_name`, `kind`, `owner`, `type`, `revision`, `model_layer`, `metatype_name`, and `metatype_chain`. |
| `AnalysisQuery.elements() -> SemanticQuery` | Start a query over all refs. |
| `AnalysisQuery.refs(kind=None, where=None)` | Return refs filtered by kind substring and optional predicate. |
| `AnalysisQuery.part_defs(where=None)` | Return part definitions. |
| `AnalysisQuery.part_usages(where=None)` | Return part usages. |
| `AnalysisQuery.subtypes(base, *, transitive=True)` | Return `PartDefRef` subtypes of a base ref or name. |
| `AnalysisQuery.containment(root=None)` | Return containment traversal from root, or all roots. |

### Cell Reports

`CellRunReport` is the result of the shared session/cell execution path.

Fields: `cell_id`, `kind`, `status`, `outputs`, `artifacts`, `diagnostics`,
`capability_report`, `metadata`, and `session_id`.

| API | Description |
| --- | --- |
| `CellRunReport.from_dict(data) -> CellRunReport` | Parse a report payload. |
| `output(output_id) -> JsonObject` | Return a named output, or raise `KeyError`. |
| `result` | Shortcut for `output("result")["value"]`. |
| `to_dict() -> JsonObject` | Serialize back to a plain dict. |

### `CompiledModel`

`CompiledModel` is an immutable semantic snapshot compiled from a project or
variant.

| API | Description |
| --- | --- |
| `revision: str` | Hash of the semantic snapshot rows. |
| `query: AnalysisQuery` | Query facade for the compiled model. |
| `raw` | Native semantic model object. |
| `rows` | Frozen semantic snapshot rows. |
| `semantic_snapshot_json() -> str` | Raw snapshot JSON. |
| `refs() -> list[SemanticRef]` | All semantic refs. |
| `diff(other) -> list[SemanticSnapshotDifference]` | Compare this snapshot with another snapshot/model. |
| `to_records(refs=None) -> list[JsonObject]` | Export selected refs to records. |
| `to_frame(refs=None) -> pandas.DataFrame` | Export to pandas; raises if pandas is not installed. |
| `graph(relation="containment") -> JsonObject` | Return simple containment or specialization graph. |
| `model_metadata()`, `graph_view(scope="l2")`, `search(query)`, `element_details(element_id)` | Shared exploration APIs. |
| `l2_explorer(...)`, `metatype_explorer(...)`, `render_view(document)` | Shared explorer/view APIs. |
| `run_cell(...)`, `dsl(source)`, `query_dsl(source)` | Shared DSL query APIs. |
| `run_action_dsl(...)`, `action_dsl(source)`, `preview_dsl(source)` | Shared DSL action-preview APIs. |
| `run_analysis_dsl(...)`, `analysis_dsl(...)` | Shared DSL analysis APIs. |
| `dsl_schema() -> JsonObject` | DSL introspection schema. |
| `preview_transaction(request) -> JsonObject` | Preview a semantic transaction payload. |
| `simulation(name) -> SimulationConfiguration` | Create a declarative simulation configuration. |
| `resolve(value) -> SemanticRef` | Resolve a qualified name, short name, or ref-like object. |
| `part_def(name) -> PartDefRef`, `part_usage(name) -> PartUsageRef` | Resolve a single part definition/usage by short or qualified name. |
| `part_defs()`, `part_usages()` | Return typed refs. |
| `children_of(parent)`, `walk()`, `subtypes_of(base, *, transitive=True)` | Traversal helpers. |

### Editing And Transactions

| API | Description |
| --- | --- |
| `SmallEdit.rename(new_name) -> SmallEdit` | Rename the target declaration. |
| `SmallEdit.set_type(target) -> SmallEdit` | Set or clear usage type. |
| `SmallEdit.set_value(value) -> SmallEdit` | Set expression text from `str(value)`. |
| `SmallEdit.set_attribute(name, value) -> SmallEdit` | Set a semantic attribute. |
| `SmallEdit.add_specialization(target) -> SmallEdit` | Add a specialization target. |
| `SmallEdit.remove() -> None` | Remove the target declaration. |
| `TransactionBuilder.rename(element, new_name) -> TransactionBuilder` | Queue a rename. |
| `TransactionBuilder.set_attribute(element, attribute, value) -> TransactionBuilder` | Queue an attribute write. |
| `TransactionBuilder.to_dict() -> JsonObject` | Serialize transaction actions. |
| `TransactionBuilder.preview() -> JsonObject` | Compile and preview the transaction. |
| `TransactionBuilder.apply() -> ProjectSession | Variant` | Apply queued edits to source. |

Editing through a `SemanticRef` compiled from an earlier source fingerprint
raises `StaleSemanticRefError`; recompile and resolve a fresh ref first.

### `ProjectSession`

`ProjectSession` is a mutable, source-backed project context.

| API | Description |
| --- | --- |
| `ProjectSession.open(path, *, validate=True) -> ProjectSession` | Load a descriptor, directory, or SysML file. |
| `ProjectSession.from_files(files, *, validate=True) -> ProjectSession` | Create from a `path -> source` mapping. |
| `in_package(name, *, stdlib_imports=True) -> ProjectSession` | Add/select a default package. |
| `add(declaration) -> ProjectSession` | Add an authoring declaration to the default package. |
| `edit(target) -> SmallEdit` | Create an edit facade for a ref/name. |
| `transaction(label) -> TransactionBuilder` | Create a transaction builder. |
| `compile() -> CompiledModel` | Compile current source into an immutable snapshot. |
| `to_sysml() -> dict[str, str]` | Render source files. |
| `source_fingerprint: str` | Hash of rendered source files. |
| `save(path=None) -> None` | Write source files. `path` is optional only when opened from a project. |
| `run_cell(...)`, `query(...)`, `dsl(...)`, `query_dsl(...)`, `run_action_dsl(...)`, `action_dsl(...)`, `preview_dsl(...)`, `run_analysis_dsl(...)`, `analysis_dsl(...)`, `dsl_schema()` | Compile current source and run shared cell/DSL APIs. |
| `model_metadata()`, `graph_view(scope="l2")`, `search(query)`, `element_details(element_id)`, `l2_explorer(...)`, `metatype_explorer(...)`, `render_view(document)` | Compile current source and run shared exploration/view APIs. |
| `trade_study(name) -> TradeStudy` | Start a named variant collection. |
| `simulation(name) -> SimulationConfiguration` | Create a declarative simulation configuration bound to source. |

### Trade Studies And Variants

| API | Description |
| --- | --- |
| `TradeStudy.variant(name) -> Variant` | Clone the base project source into a low-cost overlay. |
| `Variant.edit(target) -> SmallEdit` | Edit overlay source. |
| `Variant.transaction(label, *, allow_stale_base=False) -> TransactionBuilder` | Create a transaction builder. |
| `Variant.add(declaration) -> Variant` | Add a declaration to overlay source. |
| `Variant.compile(*, allow_stale_base=False) -> CompiledModel` | Compile overlay source. Raises `VariantBaseChangedError` if the base changed unless allowed. |
| `Variant.to_sysml() -> dict[str, str]` | Render overlay source files. |
| `Variant.source_fingerprint: str` | Overlay source hash. |
| `Variant.base_fingerprint: str | None` | Base source hash captured when forked. |
| `Variant.is_base_stale: bool` | Whether the base project has changed. |
| `Variant.assert_base_current() -> None` | Raise if base is stale. |
| `Variant.simulation(name) -> SimulationConfiguration` | Create declarative simulation config. |
| `Variant.run_cell(...)`, `query(...)`, `dsl(...)`, `query_dsl(...)`, `run_action_dsl(...)`, `action_dsl(...)`, `preview_dsl(...)`, `run_analysis_dsl(...)`, `analysis_dsl(...)`, `dsl_schema()` | Compile overlay and run shared cell/DSL APIs. Most accept `allow_stale_base`. |
| `Variant.model_metadata()`, `graph_view(...)`, `search(...)`, `element_details(...)`, `l2_explorer(...)`, `metatype_explorer(...)`, `render_view(...)` | Compile overlay and run shared exploration/view APIs. Most accept `allow_stale_base`. |

### `SimulationConfiguration`

Declarative simulation setup bound to a compiled model, project, or variant.
Execution is not wired to the layered Python API yet.

| API | Description |
| --- | --- |
| `name: str` | Configuration name. |
| `target` | `CompiledModel`, `ProjectSession`, or `Variant`. |
| `subject: str | None` | Qualified subject reference. |
| `settings: JsonObject` | User settings. |
| `model_revision: str | None` | Set for compiled-model targets. |
| `source_fingerprint: str | None` | Set for project/variant targets. |
| `for_subject(subject) -> SimulationConfiguration` | Bind a subject by ref-like object or name. |
| `configure(**settings) -> SimulationConfiguration` | Merge settings. |
| `to_dict() -> JsonObject` | Serialize configuration and provenance. |
| `run()` | Raises `NotImplementedError` until execution is wired. |

## Authoring API: `mercurio.authoring`

The authoring API is a Python facade over the native Rust authoring engine. It
can load existing projects, mutate source, render SysML files, and compile to a
native semantic model.

### `ModelBuilder`

| API | Description |
| --- | --- |
| `ModelBuilder(validate_each_mutation=True)` | Create an empty builder. |
| `ModelBuilder.for_metamodel(id) -> ModelBuilder` | Constructor reserved for release/profile selection; currently returns a default builder. |
| `ModelBuilder.from_project(path, *, validate=True) -> ModelBuilder` | Load a descriptor-aware project, directory, descriptor file, or single SysML file. |
| `ModelBuilder.from_files(files, *, validate=True) -> ModelBuilder` | Load a `path -> source` mapping. |
| `in_package(name, *, stdlib_imports=True) -> ModelBuilder` | Add/select the default package and optionally import common stdlib namespaces. |
| `add(element) -> ModelBuilder` | Add a typed declaration into the default package. |
| `add_to(container, element) -> ModelBuilder` | Add a typed declaration into an existing container. |
| `add_element(metaclass, name, *, container=None, type=None, ty=None, specializes=None, properties=None, profile=None) -> str` | Create a semantic element by metaclass through the native rule-backed mutation surface. |
| `create(metaclass, name, *, container=None, type=None, ty=None, specializes=None, additional_types=None, subsets=None, redefines=None, reference_target=None, transition_source=None, transition_target=None, trigger=None, doc=None, body=None, expression=None, multiplicity=None, direction=None, short_name=None, annotated_elements=None, language_extensions=None, language_extension_keyword=None, abstract=None, end=None, individual=None, attributes=None) -> str` | Generic semantic metaclass escape hatch. Delegates creation through `add_element()` and then applies additional semantic attributes. Returns the created qualified name. |
| `rename(qualified_name, new_name) -> ModelBuilder` | Rename a declaration. |
| `remove(qualified_name) -> ModelBuilder` | Remove a declaration. |
| `add_import(path, *, package=None, target_file=None) -> ModelBuilder` | Add an import. |
| `remove_import(path, *, package=None, target_file=None) -> ModelBuilder` | Remove an import. |
| `update_specializations(qualified_name, specializes) -> ModelBuilder` | Replace all specialization targets. |
| `add_specialization(qualified_name, target) -> ModelBuilder` | Add one specialization target. |
| `remove_specialization(qualified_name, target) -> ModelBuilder` | Remove one specialization target. |
| `set_type(qualified_name, target) -> ModelBuilder` | Set or clear usage type. |
| `set_expression(qualified_name, expression) -> ModelBuilder` | Set or clear value expression. |
| `set_doc(qualified_name, text) -> ModelBuilder` | Set documentation text. |
| `clear_doc(qualified_name) -> ModelBuilder` | Clear documentation text. |
| `set_attribute(qualified_name, attribute, value) -> ModelBuilder` | Set a semantic attribute. |
| `clear_attribute(qualified_name, attribute) -> ModelBuilder` | Clear a semantic attribute. |
| `add_attribute_value(qualified_name, attribute, value) -> ModelBuilder` | Append to a list-valued semantic attribute. |
| `remove_attribute_value(qualified_name, attribute, value) -> ModelBuilder` | Remove from a list-valued semantic attribute. |
| `move(qualified_name, destination) -> ModelBuilder` | Move a declaration to another container. |
| `add_relationship(kind, source, target, *, container=None) -> ModelBuilder` | Add a relationship usage in a container. |
| `add_metadata(qualified_name, metadata_type, properties=None) -> ModelBuilder` | Attach metadata to an element. |
| `set_additional_types()`, `add_additional_type()`, `remove_additional_type()` | Manage usage `additional_types`. |
| `set_subsets()`, `add_subset()`, `remove_subset()` | Manage subsetted features. |
| `set_redefines()`, `add_redefine()`, `remove_redefine()` | Manage redefined features. |
| `set_reference_target(qualified_name, target) -> ModelBuilder` | Set explicit reference target. |
| `clear_reference_target(qualified_name) -> ModelBuilder` | Clear explicit reference target. |
| `to_sysml() -> dict[str, str]` | Render source files. |
| `compile()` | Compile to native `SemanticModel`. |
| `save(path=None) -> None` | Write rendered source files. |

### Typed Declaration Fluent API

All typed declaration objects accept a `name` in the constructor and support:

| API | Description |
| --- | --- |
| `specializes(target)` | Add a specialization target. |
| `typed(target)` | Set usage type. |
| `expression(text)` | Set usage expression. |
| `multiplicity(text)` | Set multiplicity text. |
| `direction(text)` | Set direction text. |
| `doc(text)` | Set documentation text. |
| `abstract_()` | Mark as abstract. |
| `reference_target(target)` | Set explicit reference target. |
| `language_extension(keyword)` | Add a language extension keyword. |
| `extension_keyword()` | Mark as a language extension keyword definition. |
| `first(source)`, `initial(source="start")`, `then(target)`, `accept(trigger)` | Transition shorthand helpers. |

Definitions support:

`with_part()`, `with_item()`, `with_attr()`, `with_port()`, `with_end()`,
`with_action()`, and `with_state()`.

Usages support:

`with_part()`, `with_item()`, `with_attr()`, `with_port()`, `with_action()`,
`with_state()`, `with_end()`, `end(target=None)`, and:

```python
ConnectionUsage("axle").connects(
    "vehicle.leftWheel",
    "vehicle.rightWheel",
    source_name="left",
    target_name="right",
    source_type="Wheel",
    target_type="Wheel",
)
```

Metadata helpers:

| Type | Extra API |
| --- | --- |
| `MetadataDefinition` | `annotates(target)` |
| `MetadataUsage` | `about(targets)` |

### Typed Declaration Classes

Definitions:

`PartDefinition`, `ItemDefinition`, `AttributeDefinition`, `PortDefinition`,
`ConnectionDefinition`, `ActionDefinition`, `ConstraintDefinition`,
`AnalysisDefinition`, `VerificationDefinition`, `UseCaseDefinition`,
`ViewDefinition`, `ViewpointDefinition`, `ConcernDefinition`,
`MetadataDefinition`, `OccurrenceDefinition`, `IndividualDefinition`,
`StateDefinition`, `RequirementDefinition`, and `InterfaceDefinition`.

Usages:

`PartUsage`, `ItemUsage`, `AttributeUsage`, `PortUsage`, `ConnectionUsage`,
`ActionUsage`, `PerformActionUsage`, `ConstraintUsage`, `AnalysisUsage`,
`VerificationUsage`, `UseCaseUsage`, `ViewUsage`, `ViewpointUsage`,
`ConcernUsage`, `StakeholderUsage`, `MetadataUsage`, `OccurrenceUsage`,
`IndividualUsage`, `StateUsage`, and `TransitionUsage`.

## Standard Library References: `mercurio.stdlib`

| API | Description |
| --- | --- |
| `StdlibRef(qualified_name)` | Reference-like value used by authoring helpers. `id` returns `qualified_name`. |
| `isq.<quantity>` | Maps common quantity names to ISQ `*Value` types, for example `isq.mass -> ISQBase::MassValue`. |
| `si.<unit>` | Maps to lowercase SI names, for example `si.kilogram -> SI::kilogram`. |
| `scalar_values.<name>` | Maps snake_case to PascalCase, for example `scalar_values.real -> ScalarValues::Real`. |

Use `StdlibRef("Package::Name")` for less common stdlib references.

## Semantic Snapshot Utilities: `mercurio.semantic`

| API | Description |
| --- | --- |
| `DEFAULT_COMPARE_FIELDS` | Default fields compared by `compare_semantic_snapshots()`. |
| `SemanticSnapshotDifference` | Dataclass with `key`, `field`, `left`, and `right`. |
| `load_semantic_snapshot(value) -> list[SnapshotRow]` | Accepts JSON string, iterable rows, or object with `semantic_snapshot_json()`. |
| `semantic_snapshot_index(snapshot) -> dict[str, SnapshotRow]` | Index rows by semantic key. |
| `compare_semantic_snapshots(left, right, *, fields=DEFAULT_COMPARE_FIELDS) -> list[SemanticSnapshotDifference]` | Order-insensitive snapshot comparison. |
| `normalize_semantic_snapshot_row(row) -> SnapshotRow` | Normalize list-valued fields for comparison. |
| `semantic_snapshot_key(row) -> str` | Key by `qualified_name`, `id`, or `declared_name`. |

## Lab API: `mercurio.lab`

Lab mode is enabled with `MERCURIO_LAB_KERNEL=1`.

| API | Description |
| --- | --- |
| `LabModel(label, handle_id=..., _params=..., _parent_id=None, _workspace="")` | In-Lab model/variant handle. Emits a structured handle-created event in Lab mode. |
| `LabModel.params` | Copy of parameter overrides. |
| `LabModel.workspace` | Workspace path. |
| `LabModel.fork(label, **params) -> LabModel` | Create a variant with merged parameter overrides. |
| `LabModel.raw` | Raw parameter dictionary. |
| `open_lab(path=None, *, label=None) -> LabModel` | Open a Lab model handle. |
| `parameter_sweep(model, param, values, *, label_template="{param}={value}") -> list[LabModel]` | Fork one variant per value. |
| `batch_run(variants, analysis, *, bridge_name=None) -> list[dict[str, Any]]` | Run an installed analysis bridge over variants. |

## Extension API: `mercurio.extensions`

Extensions are installed as separate Python packages using entry point groups:

| Entry Point Group | Purpose |
| --- | --- |
| `mercurio.bridges` | Analysis bridges. |
| `mercurio.renderers` | Output renderers. |

| API | Description |
| --- | --- |
| `AnalysisBridge` | Abstract base class with `name` property and `run(model) -> dict[str, Any]`. |
| `OutputRenderer` | Abstract base class with `output_type` property and `render_spec(data) -> dict[str, Any]`. |
| `ExtensionNotInstalledError` | Raised when a bridge or renderer is missing. |
| `load_bridges() -> dict[str, AnalysisBridge]` | Discover bridge entry points. |
| `load_renderers() -> dict[str, OutputRenderer]` | Discover renderer entry points. |
| `get_bridge(name) -> AnalysisBridge` | Return a named bridge or raise with an install hint. |
| `get_renderer(name) -> OutputRenderer` | Return a named renderer or raise. |

## Advanced HTTP API

These modules are importable for tests and integrations that need direct HTTP
control. Most users should prefer `mercurio.open()` and `mercurio.project()`.

### `mercurio.backend.Mercurio`

| API | Description |
| --- | --- |
| `Mercurio.connect(url, *, timeout=30.0) -> Mercurio` | Connect to an already-running backend and check API compatibility. |
| `Mercurio.launch(*, executable=None, workspace=None, host="127.0.0.1", port=0, timeout=30.0) -> Mercurio` | Launch a sidecar backend. |
| `ensure_compatible() -> VersionInfo` | Require API version `1`. |
| `health() -> dict`, `version() -> VersionInfo` | Backend status. |
| `list_sysml_releases() -> list[SysmlReleaseInfo]` | List supported SysML releases. |
| `resolve_sysml_release(selector) -> SysmlReleaseInfo` | Resolve selector locally from listed releases. |
| `open_project(path, *, mode="lazy") -> MercurioProject` | Open a project/workspace. |
| `open_workspace(path, *, mode="lazy") -> MercurioProject` | Alias for `open_project()`. |
| `close() -> None` | Stop a launched backend process. |

`Mercurio` is a context manager.

### `mercurio.client.MercurioClient`

Low-level JSON HTTP wrapper.

| API | Description |
| --- | --- |
| `MercurioClient(base_url, *, timeout=30.0)` | Create a client. |
| `health()`, `version()` | Backend status. |
| `list_sysml_releases()`, `resolve_sysml_release(selector)` | Release helpers. |
| `open_project(path, *, mode="lazy") -> ProjectInfo` | POST `/api/workspaces`. |
| `open_workspace(path, *, mode="lazy") -> ProjectInfo` | Alias. |
| `list_projects()`, `list_workspaces()` | List open projects/workspaces. |
| `delete_project(project_id)`, `delete_workspace(workspace_id)` | Close workspace on backend. |
| `get(path, query=None)`, `post(path, payload=None, query=None)`, `put(path, payload=None, query=None)`, `delete(path, query=None)` | Raw JSON request helpers. |

HTTP errors are raised as `MercurioBackendError`.

### `mercurio.project.MercurioProject`

Project-scoped HTTP convenience layer.

| API | Description |
| --- | --- |
| `project_id`, `workspace_id` | Backend workspace id. |
| `model()`, `graph(scope=None)`, `element(element_id)`, `search(query_text)` | Model read APIs. |
| `render_view(document)`, `l2_explorer(...)`, `metatype_explorer(...)` | View/explorer APIs. |
| `mounted_library_trees() -> list[JsonObject]` | Mounted library tree payloads. |
| `files()`, `read_file(path)`, `save_file(path, content)` | Editor file APIs. |
| `parse_preview(path, content)`, `compile_file_preview(path, content)`, `lint_preview(path, content)`, `format_preview(path, content)`, `refresh(path)` | Editor preview APIs. |
| `workspace_session() -> JsonObject` | Semantic workspace session payload. |
| `run_cell(request) -> JsonObject`, `dsl_query(source) -> JsonObject`, `dsl_action(source) -> JsonObject`, `action_dsl(source) -> JsonObject`, `dsl_schema() -> JsonObject` | Session/DSL APIs. |
| `compile_project(project_path=".", *, staged_files=None) -> SemanticProjectResult` | Compile project preview. |
| `compile_project_preview(...) -> SemanticProjectResult` | Same implementation as `compile_project()`. |
| `lint_project_preview(project_path=".", *, staged_files=None) -> JsonObject` | Project lint preview. |
| `list_analysis_specs() -> list[AnalysisSpec]`, `list_analysis_cases() -> list[AnalysisCaseInfo]`, `analysis_opportunities() -> AnalysisOpportunityReport` | Analysis listing and semantic opportunity discovery. |
| `run_analysis_report(case_id, *, run_id=None) -> AnalysisRunReport`, `run_analysis(case_id) -> SimulationTrace` | Analysis execution. |
| `parts() -> list[PartRef]` | Part tree. |
| `close() -> None` | Delete the backend workspace. |

`MercurioWorkspace` is an alias for `MercurioProject`.

### `mercurio.process`

| API | Description |
| --- | --- |
| `discover_executable(explicit=None) -> str` | Resolve a sidecar executable. |
| `launch_backend(*, executable=None, workspace=None, host="127.0.0.1", port=0, timeout=15.0) -> BackendProcess` | Launch backend and parse startup JSON. |
| `BackendProcess.url` | Startup URL. |
| `BackendProcess.close() -> None` | Terminate the process. |

## Native PyO3 API: `mercurio._core`

`mercurio._core` is the native extension module. User scripts normally go
through `mercurio.open()`, `mercurio.create()`, and `mercurio.project()`, but the stubs
define the lower-level native surface.

### Native Authoring

| API | Description |
| --- | --- |
| `WriteBackResult` | Fields: `edited_files`, `changed_files`, `changed_declarations`, `mode`, `validation_ok`, `validation_message`. |
| `ModelBuilder(...)` | Native builder used by `mercurio.authoring.ModelBuilder`. |
| `ModelBuilder.from_project(path, validate_each_mutation=True)` | Load project source. |
| `ModelBuilder.from_sysml_files(files, validate_each_mutation=True)` | Load source mapping. |
| `add_package()`, `add_element()`, `add_import()`, `remove_import()`, `add_definition()`, `add_usage()`, `remove_declaration()`, `update_specializations()`, `add_relationship()`, `add_metadata_annotation()`, `set_expression()`, `set_usage_type()`, `set_attribute()`, `add_attribute_value()`, `remove_attribute_value()`, `clear_attribute()`, `move_declaration()` | Native authoring mutations returning `WriteBackResult`; `add_definition()` and `add_usage()` remain compatibility helpers. |
| `render_file(path)`, `files()`, `rendered_files()`, `compile_json()`, `compile_model()`, `validate()` | Native rendering, compile, and validation helpers. |

### Native Semantic Model And Workspace

| API | Description |
| --- | --- |
| `ElementView` | Fields `id`, `kind`, `layer`; methods `metatype_id()`, `get_json(name)`, `effective_json(name)`, `get_str(name)`, `effective_str(name)`, `references(relation)`, `attribute_names()`. |
| `SemanticModel.from_kir_json(content)` | Create from KIR JSON. |
| `SemanticModel.element(element_id)`, `elements()`, `element_count()` | Semantic element access. |
| `semantic_snapshot_json()`, `generate_python_wrappers(module_name)` | Snapshot and wrapper generation. |
| `model_metadata_json()`, `graph_view_json(scope=None)`, `search_json(query)`, `element_details_json(element_id)`, `l2_explorer_json(request_json)`, `metatype_explorer_json(request_json)`, `library_tree_json()` | Exploration payloads as JSON strings. |
| `dsl_query_json(source)`, `dsl_schema_json()`, `run_cell_json(request_json)`, `preview_transaction_json(request_json)` | DSL/session payloads as JSON strings. |
| `PyWorkspace.open(path)` | Native workspace open. |
| `PyWorkspace.model()`, `graph()`, `parts()`, `element(id)`, `compile()` | Native workspace raw/model access. |
| `PyWorkspace.model_metadata_json()`, `graph_view_json(scope=None)`, `search_json(query)`, `element_details_json(element_id)`, `l2_explorer_json(request_json)`, `metatype_explorer_json(request_json)`, `library_tree_json()`, `dsl_query_json(source)`, `dsl_schema_json()`, `run_cell_json(request_json)`, `analysis_specs_json()`, `analysis_run_json(case_id, run_id)` | Native workspace JSON APIs. |

## Capability SDK: `mercurio.capability`

`mercurio.capability` re-exports the process-backed capability SDK from
`mercurio_capability`. A provider
reads one `CapabilityRequest` JSON object from stdin and writes a
`ReasoningCapabilityRunResponse` JSON object to stdout. Any non-protocol output
should go to stderr.

### Minimal Capability

```python
from mercurio.capability import CapabilityRequest, Finding, capability, run


@capability(
    id="org.example.hello",
    kind="mercurio.capability.kind/static-analysis",
    name="Hello Capability",
)
def analyze(request: CapabilityRequest):
    return request.report_passed(
        findings=[
            Finding.info("hello.ok", "Capability ran", "The request was handled.")
        ]
    )


if __name__ == "__main__":
    run(analyze)
```

### `CapabilityRunner`

| API | Description |
| --- | --- |
| `capability(...)` | Simplified alias for `CapabilityRunner.capability(...)`. |
| `run(fn, *, capability_descriptor=None) -> None` | Simplified alias for `CapabilityRunner.run(...)`. |
| `CapabilityRunner.run(fn, *, capability_descriptor=None) -> None` | Validate descriptor, parse stdin, call `fn(request)`, serialize report or transport error to stdout. |
| `CapabilityRunner.capability(*, id, kind, name, version="0.1.0", deterministic=True, input_artifact_kinds=None, output_artifact_kinds=None, applicability_types=None, also_workspace=False, effect="observe", composes=None)` | Decorator that attaches descriptor and host metadata to a function. |

`effect="mutate"` allows the function to return a patch dict; observe-effect
capabilities must return `ReasoningReport`.

### Capability Types

| Type | Fields and APIs |
| --- | --- |
| `ElementRef` | `element_id`, `qualified_name=None`, `label=None`; `to_json()`. |
| `SourceSpanRef` | `file`, `start_line`, `start_col`, `end_line`, `end_col`; `to_json()`. |
| `Finding` | `id`, `title`, `severity`, `message`, `elements`, `source_spans`, `evidence_ids`, `properties`; factories `info()`, `warning()`, `error()`, `critical()`; `to_json()`. |
| `Artifact` | `id`, `kind`, `schema`, `digest`, `payload`, `element_refs`; factories `table()` and `markdown()`; `to_json()`. |
| `EvidenceNode` | `id`, `kind`, `label`, `element_refs`, `source_spans`, `properties`; `to_json()`. |
| `EvidenceEdge` | `source_id`, `target_id`, `relation`; `to_json()`. |
| `EvidenceGraph` | `nodes`, `edges`; `to_json()`. |
| `ReasoningReport` | `request_id`, `capability_descriptor`, `context`, `status`, `findings`, `artifacts`, `evidence`; factories `passed()`, `failed()`, `inconclusive()`; `to_json()`. |
| `CapabilityRequest` | `request_id`, `capability_id`, `context`, `focus`, `parameters`, `kir`, `graph_facts`, `kir_content_hash`, `sub_reports`; `from_json(data)`, `param(key, default=None)`, `sub_report(capability_id)`, `report_passed()`, `report_failed()`, `report_inconclusive()`. |

Validation constants:

| Name | Values |
| --- | --- |
| `FINDING_SEVERITIES` | `info`, `warning`, `error`, `critical`. |
| `REASONING_STATUSES` | `passed`, `failed`, `inconclusive`, `error`. |
| `EVIDENCE_NODE_KINDS` | `kir_element`, `source_span`, `fact`, `rule`, `analysis_run`, `plugin`, `artifact`, `human_decision`. |
| `EVIDENCE_RELATIONS` | `supports`, `derived_from`, `produced_by`, `consumed`, `affects`, `explains`. |

## Errors

| Error | Raised When |
| --- | --- |
| `MercurioError` | Base Python client exception. |
| `MercurioBackendError(status, message)` | HTTP backend returns an error response. |
| `MercurioLaunchError` | Sidecar executable cannot be discovered or launched. |
| `StaleSemanticRefError` | Editing through a semantic ref from stale source. |
| `VariantBaseChangedError` | Compiling a variant after base source changed without `allow_stale_base=True`. |
| `ExtensionNotInstalledError` | Requested Lab bridge/renderer is not installed. |

## Conventions And Caveats

- Prefer `mercurio.open()` for read/analysis workflows and
  `mercurio.create()`/`mercurio.project()` for source-backed authoring.
- Treat `model.raw`, `MercurioClient`, and `MercurioProject` as escape hatches.
- `CompiledModel`, `SemanticRef`, and `CellRunReport` are immutable snapshots of
  compiled/session state; first-release edits go through `Project` or `Variant`.
- `SimulationConfiguration.run()` is intentionally not implemented in the
  layered Python API yet. Use `to_dict()` for declarative configuration and
  `Model.run_analysis()`/`run_analysis_report()` for currently executable
  analysis cases.
- Sidecar DTOs use REST/KIR payloads under the hood. For raw payloads, expect
  backend schema evolution and prefer typed helpers when available.
