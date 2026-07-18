use std::collections::BTreeMap;

use mercurio_core::frontend::ast::{Declaration, GenericUsageDecl, SourceSpan};
use mercurio_core::{
    AssessmentSpec, AssessmentStatus, CapabilityRunStatus, ExecutionContext, Fact, Graph,
    KirDocument, MetamodelAttributeRegistry, RulePack, Runtime, RuntimeAssessmentRequest,
    load_default_rulepacks, run_graph_assessment, run_runtime_assessment,
};
use mercurio_kerml::{compile_kerml_text, parse_kerml};
use mercurio_lsp::LanguageServer;
use mercurio_lsp_host::create_language_server;
use mercurio_simulation::{
    ConcurrentSimulationScenario, ConcurrentSubjectScenario, SimulationStatus,
    StateMachineScenarioEvent, list_analysis_cases, run_analysis_case, run_concurrent_simulation,
};
use mercurio_sysml::{
    Diagnostic, SYSML_JSON_IMPORTER_VERSION, SemanticCompileStatus, SourceLanguage,
    SysmlJsonImportError, SysmlJsonImportOptions, SysmlJsonImportReport, SysmlModule,
    compile_sysml_text_with_context_report, import_sysml_abstract_syntax_json,
    import_sysml_api_elements, parse_sysml_recovering, project_state_machines,
    sysml_parsed_module_assessment_facts,
};
use mercurio_views::{
    DiagramError, DiagramRenderRequestDto, TableError, TableRenderRequestDto, list_diagram_kinds,
    list_table_kinds, list_view_kinds, render_diagram, render_table,
    view_catalog as build_view_catalog,
};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use wasm_bindgen::prelude::*;

const DEFAULT_STDLIB: &str = include_str!(
    "../../../../mercurio-sysml/resources/metamodels/sysml-2.0-metamodel-0.57.0/stdlib/stdlib.kir.json"
);

#[wasm_bindgen(start)]
pub fn start() {
    console_error_panic_hook::set_once();
}

#[wasm_bindgen]
pub struct MercurioLanguageServer {
    inner: LanguageServer,
}

#[wasm_bindgen]
impl MercurioLanguageServer {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Result<MercurioLanguageServer, JsValue> {
        create_language_server()
            .map(|inner| Self { inner })
            .map_err(|error| JsValue::from_str(&error.to_string()))
    }

    #[wasm_bindgen(js_name = handle)]
    pub fn handle(&mut self, message: JsValue) -> Result<JsValue, JsValue> {
        let message: Value = serde_wasm_bindgen::from_value(message)
            .map_err(|error| JsValue::from_str(&error.to_string()))?;
        serde_wasm_bindgen::to_value(&self.inner.handle(message))
            .map_err(|error| JsValue::from_str(&error.to_string()))
    }
}
#[wasm_bindgen(js_name = version)]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[wasm_bindgen(js_name = compileSysml)]
pub fn compile_sysml(input: &str, options: JsValue) -> JsValue {
    json_response(|| {
        let options = CompileOptions::from_js(options)?;
        let stdlib = load_library_context(SourceLanguage::Sysml, options.stdlib)?;
        let report =
            compile_sysml_text_with_context_report(input, &options.source_name, &[], &stdlib);
        let value = json!({
            "status": semantic_status(report.status),
            "document": report.document,
        });
        Ok(Response {
            ok: report.document.is_some() && report.diagnostics.is_empty(),
            value: Some(value),
            diagnostics: serde_json::to_value(report.diagnostics)?,
            errors: Vec::new(),
            metadata: metadata([
                ("sourceName", json!(options.source_name)),
                ("language", json!("sysml")),
            ]),
        })
    })
}

#[wasm_bindgen(js_name = compileKerml)]
pub fn compile_kerml(input: &str, options: JsValue) -> JsValue {
    json_response(|| {
        let options = CompileOptions::from_js(options)?;
        let stdlib = load_library_context(SourceLanguage::Kerml, options.stdlib)?;
        match compile_kerml_text(input, &options.source_name, &stdlib) {
            Ok(document) => Ok(success(
                json!({ "status": "ok", "document": document }),
                [
                    ("sourceName", json!(options.source_name)),
                    ("language", json!("kerml")),
                ],
            )),
            Err(error) => Ok(error_response(
                "compile",
                error.to_string(),
                Some(serde_json::to_value(vec![error])?),
            )),
        }
    })
}

#[wasm_bindgen(js_name = importSysmlAbstractSyntaxJson)]
pub fn wasm_import_sysml_abstract_syntax_json(input: &str, options: JsValue) -> JsValue {
    json_response(|| {
        let options = sysml_json_import_options_from_js(options)?;
        let report = import_sysml_abstract_syntax_json(input, options)?;
        import_response(report)
    })
}

#[wasm_bindgen(js_name = importSysmlApiElements)]
pub fn wasm_import_sysml_api_elements(elements: JsValue, metadata: JsValue) -> JsValue {
    json_response(|| {
        let elements: Vec<Value> = from_js(elements)?;
        let metadata = sysml_json_import_options_from_js(metadata)?;
        let report = import_sysml_api_elements(elements, metadata)?;
        import_response(report)
    })
}

#[wasm_bindgen(js_name = lint)]
pub fn lint(input: &str, language: &str, options: JsValue) -> JsValue {
    json_response(|| {
        let options = CompileOptions::from_js(options)?;
        let language = parse_language(language)?;
        let stdlib = load_library_context(language, options.stdlib)?;
        let report = lint_source(input, &options.source_name, language, &stdlib);
        Ok(Response {
            ok: !report.has_errors(),
            value: Some(serde_json::to_value(report)?),
            diagnostics: json!([]),
            errors: Vec::new(),
            metadata: metadata([("sourceName", json!(options.source_name))]),
        })
    })
}

#[wasm_bindgen(js_name = formatText)]
pub fn format_source(input: &str, language: &str) -> JsValue {
    json_response(|| {
        let language = parse_language(language)?;
        let formatted = format_source_text(input, language)?;
        Ok(success(
            json!({ "text": formatted }),
            [("language", json!(language_as_str(language)))],
        ))
    })
}

#[wasm_bindgen(js_name = listDiagramKinds)]
pub fn wasm_list_diagram_kinds() -> JsValue {
    json_response(|| Ok(success(serde_json::to_value(list_diagram_kinds())?, [])))
}

#[wasm_bindgen(js_name = listTableKinds)]
pub fn wasm_list_table_kinds() -> JsValue {
    json_response(|| Ok(success(serde_json::to_value(list_table_kinds())?, [])))
}

#[wasm_bindgen(js_name = listViewKinds)]
pub fn wasm_list_view_kinds() -> JsValue {
    json_response(|| Ok(success(serde_json::to_value(list_view_kinds())?, [])))
}

#[wasm_bindgen(js_name = viewCatalog)]
pub fn wasm_view_catalog(document: JsValue) -> JsValue {
    json_response(|| {
        let document: KirDocument = from_js(document)?;
        let graph = Graph::from_document(document)?;
        Ok(success(
            serde_json::to_value(build_view_catalog(&graph))?,
            [],
        ))
    })
}

#[wasm_bindgen(js_name = renderDiagram)]
pub fn wasm_render_diagram(document: JsValue, request: JsValue) -> JsValue {
    json_response(|| {
        let document: KirDocument = from_js(document)?;
        let request: DiagramRenderRequestDto = from_js(request)?;
        let graph = Graph::from_document(document)?;
        let registry = MetamodelAttributeRegistry::build(&graph);
        let view = render_diagram(&graph, &registry, request.spec)?;
        Ok(success(serde_json::to_value(view)?, []))
    })
}

#[wasm_bindgen(js_name = renderTable)]
pub fn wasm_render_table(document: JsValue, request: JsValue) -> JsValue {
    json_response(|| {
        let document: KirDocument = from_js(document)?;
        let request: TableRenderRequestDto = from_js(request)?;
        let graph = Graph::from_document(document)?;
        let registry = MetamodelAttributeRegistry::build(&graph);
        let view = render_table(&graph, &registry, request.spec)?;
        Ok(success(serde_json::to_value(view)?, []))
    })
}

#[wasm_bindgen(js_name = queryRuntime)]
pub fn wasm_query_runtime(document: JsValue, query: JsValue) -> JsValue {
    json_response(|| {
        let document: KirDocument = from_js(document)?;
        let query: RuntimeQuery = from_js(query)?;
        let runtime = Runtime::from_document(document)?;
        Ok(success(run_runtime_query(&runtime, query)?, []))
    })
}

#[wasm_bindgen(js_name = runAssessment)]
pub fn wasm_run_assessment(document: JsValue, spec: JsValue) -> JsValue {
    json_response(|| {
        let document: KirDocument = from_js(document)?;
        let spec: AssessmentSpec = from_js(spec)?;
        let graph = Graph::from_document(document)?;
        let rulepacks = load_default_rulepacks()?;
        let report = run_graph_assessment(&graph, &rulepacks, &spec)?;
        Ok(success(serde_json::to_value(report)?, []))
    })
}

#[wasm_bindgen(js_name = runSourceAssessment)]
pub fn wasm_run_source_assessment(input: &str, request: JsValue) -> JsValue {
    json_response(|| {
        let request: SourceAssessmentRequest = from_js(request)?;
        let language = parse_language(&request.language)?;
        if language != SourceLanguage::Sysml {
            return Err(WasmError::new(
                "language",
                "source assessments currently support SysML sources",
            ));
        }

        let command = request.command.clone().unwrap_or_else(|| {
            format!(
                "mercurio assess {} --spec {}",
                request.filename, request.spec.id
            )
        });
        let parse_report = match parse_sysml_recovering(input) {
            Ok(report) => report,
            Err(diagnostic) => {
                return Ok(success(
                    json!({
                        "assessmentId": request.spec.id,
                        "status": "failed",
                        "command": command,
                        "report": null,
                        "transcript": [
                            "checking source assessment...",
                            "parsing source...",
                            format!("parse error: {}", diagnostic.message),
                            "result: failed",
                        ],
                        "facts": {
                            "factCount": 0,
                            "predicates": [],
                            "items": [],
                        },
                        "diagnostics": [snippet_diagnostic(&diagnostic)],
                    }),
                    [("runtime", json!("wasm"))],
                ));
            }
        };

        let diagnostics = parse_report
            .diagnostics
            .iter()
            .map(snippet_diagnostic)
            .collect::<Vec<_>>();
        let mut facts = sysml_parsed_module_assessment_facts(&parse_report.module);
        facts.extend(request.facts);
        let result = run_runtime_assessment(RuntimeAssessmentRequest {
            spec: request.spec,
            rulepacks: request.rulepacks,
            facts,
        })?;
        let passed = diagnostics.is_empty() && result.report.status == AssessmentStatus::Pass;
        let mut transcript = vec![
            "checking source assessment...".to_string(),
            "parsing source...".to_string(),
            "building assessment fact base...".to_string(),
            format!("running assessment `{}`...", result.report.id),
        ];
        if !diagnostics.is_empty() {
            transcript.push(format!("diagnostics: {}", diagnostics.len()));
        }
        for assertion in &result.report.assertions {
            transcript.push(format!(
                "assert {}: {}",
                assertion.id,
                match assertion.status {
                    AssessmentStatus::Pass => "pass",
                    AssessmentStatus::Failed => "failed",
                }
            ));
        }
        transcript.push(format!(
            "result: {}",
            if passed { "pass" } else { "failed" }
        ));

        Ok(success(
            json!({
                "assessmentId": result.report.id,
                "status": if passed { "pass" } else { "failed" },
                "command": command,
                "report": result.report,
                "transcript": transcript,
                "facts": assessment_fact_summary(&result.facts),
                "diagnostics": diagnostics,
            }),
            [("runtime", json!("wasm"))],
        ))
    })
}

#[wasm_bindgen(js_name = runSourceEvaluation)]
pub fn wasm_run_source_evaluation(input: &str, request: JsValue) -> JsValue {
    json_response(|| {
        let request: SourceEvaluationRequest = from_js(request)?;
        let language = parse_language(&request.language)?;
        if language != SourceLanguage::Sysml {
            return Err(WasmError::new(
                "language",
                "source evaluation currently supports SysML sources",
            ));
        }

        let stdlib = load_stdlib(None)?;
        let report = compile_sysml_text_with_context_report(input, &request.filename, &[], &stdlib);
        let diagnostics = report
            .diagnostics
            .iter()
            .map(snippet_diagnostic)
            .collect::<Vec<_>>();
        let Some(document) = report.document else {
            return Ok(success(
                json!({
                    "evaluationId": request.evaluation_id,
                    "status": "failed",
                    "diagnostics": diagnostics,
                    "scenarios": [],
                    "error": "source did not produce an evaluatable semantic document",
                }),
                [("runtime", json!("wasm"))],
            ));
        };
        if !diagnostics.is_empty() {
            return Ok(success(
                json!({
                    "evaluationId": request.evaluation_id,
                    "status": "failed",
                    "diagnostics": diagnostics,
                    "scenarios": [],
                    "error": "Resolve semantic diagnostics before evaluating this expression.",
                }),
                [("runtime", json!("wasm"))],
            ));
        }

        let merged_document = KirDocument::merge([stdlib, document])?;
        let runtime = Runtime::from_document(merged_document.clone())?;
        let mut scenario_results = Vec::new();
        for scenario in request.scenarios {
            let feature_id =
                find_feature_id(&merged_document, &scenario.feature_name).ok_or_else(|| {
                    WasmError::new(
                        "evaluation",
                        format!("feature `{}` not found", scenario.feature_name),
                    )
                })?;
            let owner_id = scenario
                .owner_name
                .as_deref()
                .and_then(|owner_name| find_owner_id_by_name(&merged_document, owner_name))
                .or_else(|| find_owner_id_for_feature(&merged_document, &feature_id))
                .ok_or_else(|| {
                    WasmError::new(
                        "evaluation",
                        format!("owner for feature `{}` not found", scenario.feature_name),
                    )
                })?;
            let mut context = ExecutionContext::default();
            for parameter in &scenario.parameters {
                context.values.insert(
                    (owner_id.clone(), parameter.name.clone()),
                    parameter.value.clone(),
                );
            }
            let result = runtime.evaluate(&feature_id, &owner_id, &context);
            scenario_results.push(match result {
                Ok(result) => json!({
                    "id": scenario.id,
                    "label": scenario.label,
                    "featureId": feature_id,
                    "ownerId": owner_id,
                    "ok": true,
                    "value": result.value,
                    "valueType": value_type(&result.value),
                    "explanation": result.explanation,
                    "error": null,
                    "parameters": scenario.parameters,
                }),
                Err(err) => json!({
                    "id": scenario.id,
                    "label": scenario.label,
                    "featureId": feature_id,
                    "ownerId": owner_id,
                    "ok": false,
                    "value": null,
                    "valueType": null,
                    "explanation": [],
                    "error": err.to_string(),
                    "parameters": scenario.parameters,
                }),
            });
        }

        let passed = scenario_results
            .iter()
            .all(|scenario| scenario.get("ok").and_then(Value::as_bool).unwrap_or(false));
        Ok(success(
            json!({
                "evaluationId": request.evaluation_id,
                "status": if passed { "pass" } else { "failed" },
                "diagnostics": diagnostics,
                "scenarios": scenario_results,
                "error": null,
            }),
            [("runtime", json!("wasm"))],
        ))
    })
}

#[wasm_bindgen(js_name = parseSysmlSnippet)]
pub fn wasm_parse_sysml_snippet(input: &str, request: JsValue) -> JsValue {
    json_response(|| {
        let request: SnippetParseRequest = from_js(request)?;
        let parse_report = match parse_sysml_recovering(input) {
            Ok(report) => report,
            Err(diagnostic) => {
                return Ok(success(
                    json!({
                        "diagnostics": [snippet_diagnostic(&diagnostic)],
                        "symbols": [],
                        "outline": [],
                    }),
                    [
                        ("runtime", json!("wasm")),
                        ("sourceName", json!(request.path)),
                    ],
                ));
            }
        };
        if !parse_report.diagnostics.is_empty() {
            return Ok(success(
                json!({
                    "diagnostics": parse_report.diagnostics.iter().map(snippet_diagnostic).collect::<Vec<_>>(),
                    "symbols": [],
                    "outline": [],
                }),
                [
                    ("runtime", json!("wasm")),
                    ("sourceName", json!(request.path)),
                ],
            ));
        }

        let mut symbols = Vec::new();
        let mut outline = Vec::new();
        if parse_report.module.members.is_empty() {
            if let Some(package) = &parse_report.module.package {
                let id = package.name.as_colon_string();
                outline.push(package_outline_node(
                    &id,
                    &id,
                    &package.span,
                    &package.members,
                    &mut symbols,
                ));
            }
        } else {
            for declaration in &parse_report.module.members {
                outline.push(declaration_outline_node(declaration, None, &mut symbols));
            }
        }
        let stdlib = load_stdlib(None)?;
        let semantic_report =
            compile_sysml_text_with_context_report(input, &request.path, &[], &stdlib);
        let diagnostics = semantic_report
            .diagnostics
            .iter()
            .map(snippet_diagnostic)
            .collect::<Vec<_>>();

        Ok(success(
            json!({
                "diagnostics": diagnostics,
                "symbols": symbols,
                "outline": outline,
            }),
            [
                ("runtime", json!("wasm")),
                ("sourceName", json!(request.path)),
            ],
        ))
    })
}

#[wasm_bindgen(js_name = MercurioSession)]
pub struct MercurioSession {
    stdlib: KirDocument,
    sources: Vec<SessionSource>,
}

#[wasm_bindgen(js_class = MercurioSession)]
impl MercurioSession {
    #[wasm_bindgen(constructor)]
    pub fn new(options: JsValue) -> Result<MercurioSession, JsValue> {
        let options = CompileOptions::from_js(options).map_err(js_error)?;
        let stdlib = load_stdlib(options.stdlib).map_err(js_error)?;
        Ok(Self {
            stdlib,
            sources: Vec::new(),
        })
    }

    #[wasm_bindgen(js_name = addSource)]
    pub fn add_source(&mut self, language: &str, source_name: &str, input: &str) -> JsValue {
        json_response(|| {
            let language = parse_language(language)?;
            let context = self
                .sources
                .iter()
                .map(|source| source.module.clone())
                .collect::<Vec<_>>();
            let module = match language {
                SourceLanguage::Sysml => parse_sysml_recovering(input)?.module,
                SourceLanguage::Kerml => parse_kerml(input)?,
            };
            let document = match language {
                SourceLanguage::Sysml => compile_sysml_text_with_context_report(
                    input,
                    source_name,
                    &context,
                    &self.stdlib,
                )
                .document
                .ok_or_else(|| WasmError::new("compile", "SysML compilation failed"))?,
                SourceLanguage::Kerml => compile_kerml_text(input, source_name, &self.stdlib)?,
            };
            self.sources.push(SessionSource {
                source_name: source_name.to_string(),
                language,
                module,
                document,
            });
            Ok(success(
                json!({ "sourceName": source_name, "sourceCount": self.sources.len() }),
                [("language", json!(language_as_str(language)))],
            ))
        })
    }

    #[wasm_bindgen(js_name = clear)]
    pub fn clear(&mut self) {
        self.sources.clear();
    }

    #[wasm_bindgen(js_name = document)]
    pub fn document(&self) -> JsValue {
        json_response(|| {
            let document = self.merged_document()?;
            Ok(success(
                serde_json::to_value(document)?,
                [("sourceCount", json!(self.sources.len()))],
            ))
        })
    }

    #[wasm_bindgen(js_name = listViewKinds)]
    pub fn list_view_kinds(&self) -> JsValue {
        json_response(|| Ok(success(serde_json::to_value(list_view_kinds())?, [])))
    }

    #[wasm_bindgen(js_name = viewCatalog)]
    pub fn view_catalog(&self) -> JsValue {
        json_response(|| {
            let graph = self.graph()?;
            Ok(success(
                serde_json::to_value(build_view_catalog(&graph))?,
                [],
            ))
        })
    }

    #[wasm_bindgen(js_name = renderDiagram)]
    pub fn render_diagram(&self, request: JsValue) -> JsValue {
        json_response(|| {
            let request: DiagramRenderRequestDto = from_js(request)?;
            let graph = self.graph()?;
            let registry = MetamodelAttributeRegistry::build(&graph);
            let view = render_diagram(&graph, &registry, request.spec)?;
            Ok(success(serde_json::to_value(view)?, []))
        })
    }

    #[wasm_bindgen(js_name = renderTable)]
    pub fn render_table(&self, request: JsValue) -> JsValue {
        json_response(|| {
            let request: TableRenderRequestDto = from_js(request)?;
            let graph = self.graph()?;
            let registry = MetamodelAttributeRegistry::build(&graph);
            let view = render_table(&graph, &registry, request.spec)?;
            Ok(success(serde_json::to_value(view)?, []))
        })
    }

    #[wasm_bindgen(js_name = queryRuntime)]
    pub fn query_runtime(&self, query: JsValue) -> JsValue {
        json_response(|| {
            let query: RuntimeQuery = from_js(query)?;
            let runtime = Runtime::from_document(self.merged_document()?)?;
            Ok(success(run_runtime_query(&runtime, query)?, []))
        })
    }

    #[wasm_bindgen(js_name = runAssessment)]
    pub fn run_assessment(&self, spec: JsValue) -> JsValue {
        json_response(|| {
            let spec: AssessmentSpec = from_js(spec)?;
            let graph = self.graph()?;
            let rulepacks = load_default_rulepacks()?;
            let report = run_graph_assessment(&graph, &rulepacks, &spec)?;
            Ok(success(serde_json::to_value(report)?, []))
        })
    }

    /// Return all state machines found in the compiled document.
    /// Each entry carries enough information for the UI to present a picker.
    #[wasm_bindgen(js_name = listStateMachines)]
    pub fn list_state_machines(&self) -> JsValue {
        json_response(|| {
            let runtime = Runtime::from_document(self.merged_document()?)?;
            let machines = project_state_machines(&runtime);
            let items = machines
                .iter()
                .map(|m| {
                    let initial = m
                        .states
                        .iter()
                        .find(|s| s.is_initial)
                        .map(|s| s.id.as_str());
                    json!({
                        "id":             m.id,
                        "label":          m.label,
                        "stateCount":     m.states.len(),
                        "transitionCount": m.transitions.len(),
                        "initialStateId": initial,
                        "states": m.states.iter().map(|s| {
                            json!({
                                "id": s.id,
                                "label": s.label,
                                "parentStateId": s.parent_state_id,
                                "isInitial": s.is_initial,
                                "isFinal": s.is_final,
                            })
                        }).collect::<Vec<_>>(),
                        "transitions": m.transitions.iter().map(|t| {
                            json!({
                                "id": t.id,
                                "source": t.source,
                                "target": t.target,
                                "trigger": t.trigger,
                                "triggerKind": t.trigger_kind,
                            })
                        }).collect::<Vec<_>>(),
                    })
                })
                .collect::<Vec<_>>();
            Ok(success(serde_json::to_value(items)?, []))
        })
    }

    /// Return candidate simulation subjects — elements that carry behaviour
    /// (IndividualUsage / IndividualDefinition, or any typed feature).
    #[wasm_bindgen(js_name = listSimulationSubjects)]
    pub fn list_simulation_subjects(&self) -> JsValue {
        json_response(|| {
            let doc = self.merged_document()?;
            // Prefer explicitly-individual elements; fall back to any named feature with a type.
            let mut items: Vec<Value> = doc
                .elements
                .iter()
                .filter(|e| e.kind.contains("Individual"))
                .map(element_to_subject_json)
                .collect();
            if items.is_empty() {
                items = doc
                    .elements
                    .iter()
                    .filter(|e| {
                        e.properties.contains_key("type")
                            && e.properties.contains_key("declared_name")
                            && !e.kind.contains("KerML")
                            && !e.kind.contains("SysML::Systems::PartDefinition")
                    })
                    .take(50)
                    .map(element_to_subject_json)
                    .collect();
            }
            Ok(success(serde_json::to_value(items)?, []))
        })
    }

    /// Return authored analysis cases that can be run as native scenarios.
    #[wasm_bindgen(js_name = listAnalysisCases)]
    pub fn list_analysis_cases(&self) -> JsValue {
        json_response(|| {
            let runtime = Runtime::from_document(self.merged_document()?)?;
            let items = list_analysis_cases(&runtime);
            Ok(success(serde_json::to_value(items)?, []))
        })
    }

    /// Run a simulation and return a `SimulationTrace`.
    ///
    /// `request` shape:
    /// ```json
    /// {
    ///   "subjectId":     "feature.MyPkg.myPart",
    ///   "machineId":     "MyStateMachine",
    ///   "maxSteps":      200,
    ///   "stepDurationS": 1.0,
    ///   "initialValues": { "feature.MyPkg.myPart|temperature": 22.0 },
    ///   "events":        [{ "id": "e1", "trigger": "start" }]
    /// }
    /// ```
    #[wasm_bindgen(js_name = runSimulation)]
    pub fn run_simulation(&self, request: JsValue) -> JsValue {
        json_response(|| {
            let req: WasmSimulationRequest = from_js(request)?;
            let runtime = Runtime::from_document(self.merged_document()?)?;

            // Convert "subject|feature" string keys to (String, String) tuples.
            let values = req
                .initial_values
                .into_iter()
                .filter_map(|(k, v)| {
                    let (subj, feat) = k.split_once('|')?;
                    Some(((subj.to_string(), feat.to_string()), v))
                })
                .collect();

            let events = req
                .events
                .into_iter()
                .map(|e| StateMachineScenarioEvent {
                    id: e.id,
                    trigger: e.trigger,
                })
                .collect();

            let scenario = ConcurrentSimulationScenario {
                id: "wasm.simulation".to_string(),
                subjects: vec![ConcurrentSubjectScenario {
                    subject_id: req.subject_id,
                    machine_id: req.machine_id,
                    initial_state_id: None,
                    events,
                }],
                max_steps: req.max_steps.unwrap_or(200),
                clock_config: None,
                initial_values: values,
                step_duration_s: req.step_duration_s.unwrap_or(1.0),
                requirements: Vec::new(),
                objectives: Vec::new(),
            };

            let trace = run_concurrent_simulation(&runtime, scenario)
                .map_err(|e| WasmError::new("simulation", e.to_string()))?;
            let completed = matches!(trace.status, SimulationStatus::Completed);
            Ok(Response {
                ok: completed,
                value: Some(
                    serde_json::to_value(&trace)
                        .map_err(|e| WasmError::new("serialize", e.to_string()))?,
                ),
                diagnostics: json!([]),
                errors: Vec::new(),
                metadata: metadata([
                    ("stepCount", json!(trace.timeline.len())),
                    ("status", json!(format!("{:?}", trace.status))),
                ]),
            })
        })
    }

    /// Run a concurrent multi-subject simulation.
    #[wasm_bindgen(js_name = runConcurrentSimulation)]
    pub fn run_concurrent_simulation(&self, request: JsValue) -> JsValue {
        json_response(|| {
            let req: WasmConcurrentSimulationRequest = from_js(request)?;
            let runtime = Runtime::from_document(self.merged_document()?)?;
            let subject_count = req.subjects.len();

            let initial_values = req
                .initial_values
                .into_iter()
                .filter_map(|(key, value)| {
                    let (subject, feature) = key.split_once('|')?;
                    Some(((subject.to_string(), feature.to_string()), value))
                })
                .collect();

            let subjects = req
                .subjects
                .into_iter()
                .map(|subject| ConcurrentSubjectScenario {
                    subject_id: subject.subject_id,
                    machine_id: subject.machine_id,
                    initial_state_id: None,
                    events: subject
                        .events
                        .into_iter()
                        .map(|event| StateMachineScenarioEvent {
                            id: event.id,
                            trigger: event.trigger,
                        })
                        .collect(),
                })
                .collect();

            let scenario = ConcurrentSimulationScenario {
                id: "wasm.concurrent".to_string(),
                subjects,
                max_steps: req.max_steps.unwrap_or(300),
                step_duration_s: req.step_duration_s.unwrap_or(1.0),
                clock_config: None,
                initial_values,
                requirements: Vec::new(),
                objectives: Vec::new(),
            };

            let trace = run_concurrent_simulation(&runtime, scenario)
                .map_err(|error| WasmError::new("simulation", error.to_string()))?;
            let completed = matches!(trace.status, SimulationStatus::Completed);
            Ok(Response {
                ok: completed,
                value: Some(
                    serde_json::to_value(&trace)
                        .map_err(|error| WasmError::new("serialize", error.to_string()))?,
                ),
                diagnostics: json!([]),
                errors: Vec::new(),
                metadata: metadata([
                    ("stepCount", json!(trace.timeline.len())),
                    ("subjectCount", json!(subject_count)),
                ]),
            })
        })
    }

    /// Run an authored AnalysisCaseDefinition by ID and return a capability report.
    #[wasm_bindgen(js_name = runAnalysisCase)]
    pub fn run_analysis_case(&self, analysis_case_id: String) -> JsValue {
        json_response(|| {
            let runtime = Runtime::from_document(self.merged_document()?)?;
            let run_id = format!("wasm.analysis_case.{analysis_case_id}");
            let report = run_analysis_case(&runtime, &analysis_case_id, &run_id)
                .map_err(|error| WasmError::new("simulation", error.to_string()))?;
            let completed = matches!(report.status, CapabilityRunStatus::Passed);
            let step_count = report
                .artifacts
                .iter()
                .find(|artifact| artifact.kind == "simulation_trace")
                .and_then(|artifact| artifact.payload.get("timeline"))
                .and_then(Value::as_array)
                .map_or(0, Vec::len);
            Ok(Response {
                ok: completed,
                value: Some(
                    serde_json::to_value(&report)
                        .map_err(|error| WasmError::new("serialize", error.to_string()))?,
                ),
                diagnostics: json!([]),
                errors: Vec::new(),
                metadata: metadata([
                    ("stepCount", json!(step_count)),
                    ("analysisCaseId", json!(analysis_case_id)),
                ]),
            })
        })
    }
}

impl MercurioSession {
    fn merged_document(&self) -> Result<KirDocument, WasmError> {
        let mut elements = self.stdlib.elements.clone();
        for source in &self.sources {
            elements.extend(source.document.elements.clone());
        }
        let document = KirDocument {
            metadata: BTreeMap::from([
                ("source_count".to_string(), json!(self.sources.len())),
                (
                    "sources".to_string(),
                    json!(
                        self.sources
                            .iter()
                            .map(|source| json!({
                                "sourceName": source.source_name,
                                "language": language_as_str(source.language),
                                "elementCount": source.document.elements.len(),
                            }))
                            .collect::<Vec<_>>()
                    ),
                ),
            ]),
            elements,
        };
        document.validate()?;
        Ok(document)
    }

    fn graph(&self) -> Result<Graph, WasmError> {
        Ok(Graph::from_document(self.merged_document()?)?)
    }
}

struct SessionSource {
    source_name: String,
    language: SourceLanguage,
    module: SysmlModule,
    document: KirDocument,
}

/// JSON-friendly simulation request (initial_values keyed as "subject|feature").
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct WasmSimulationRequest {
    subject_id: String,
    machine_id: String,
    #[serde(default)]
    max_steps: Option<usize>,
    #[serde(default)]
    step_duration_s: Option<f64>,
    #[serde(default)]
    initial_values: BTreeMap<String, Value>,
    #[serde(default)]
    events: Vec<WasmSimulationEvent>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct WasmConcurrentSimulationRequest {
    subjects: Vec<WasmConcurrentSubject>,
    #[serde(default)]
    max_steps: Option<usize>,
    #[serde(default)]
    step_duration_s: Option<f64>,
    #[serde(default)]
    initial_values: BTreeMap<String, Value>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct WasmConcurrentSubject {
    subject_id: String,
    machine_id: String,
    #[serde(default)]
    events: Vec<WasmSimulationEvent>,
}

#[derive(Deserialize)]
struct WasmSimulationEvent {
    id: String,
    trigger: String,
}

fn element_to_subject_json(e: &mercurio_core::ir::KirElement) -> Value {
    json!({
        "id":    e.id,
        "label": e.properties.get("declared_name").and_then(Value::as_str).unwrap_or(&e.id),
        "typeId": e.properties.get("type").and_then(Value::as_str),
        "kind":  e.kind,
    })
}

#[derive(Default)]
struct CompileOptions {
    source_name: String,
    stdlib: Option<KirDocument>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeQuery {
    kind: RuntimeQueryKind,
    #[serde(default)]
    type_id: Option<String>,
    #[serde(default)]
    feature_id: Option<String>,
    #[serde(default)]
    owner_id: Option<String>,
    #[serde(default)]
    context: RuntimeContextDto,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
enum RuntimeQueryKind {
    Subtypes,
    Features,
    Evaluate,
}

#[derive(Default, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeContextDto {
    #[serde(default)]
    version: u64,
    #[serde(default)]
    values: Vec<RuntimeValueDto>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeValueDto {
    owner_id: String,
    feature_id: String,
    value: Value,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SourceAssessmentRequest {
    spec: AssessmentSpec,
    #[serde(default)]
    rulepacks: Vec<RulePack>,
    #[serde(default)]
    facts: Vec<Fact>,
    #[serde(default = "default_source_name")]
    filename: String,
    #[serde(default = "default_source_language")]
    language: String,
    #[serde(default)]
    command: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SourceEvaluationRequest {
    evaluation_id: String,
    scenarios: Vec<SourceEvaluationScenario>,
    #[serde(default = "default_source_name")]
    filename: String,
    #[serde(default = "default_source_language")]
    language: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SourceEvaluationScenario {
    id: String,
    label: String,
    feature_name: String,
    #[serde(default)]
    owner_name: Option<String>,
    #[serde(default)]
    parameters: Vec<SourceEvaluationParameter>,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SourceEvaluationParameter {
    name: String,
    #[serde(default)]
    label: Option<String>,
    value: Value,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SnippetParseRequest {
    #[serde(default = "default_source_name")]
    path: String,
}

impl CompileOptions {
    fn from_js(value: JsValue) -> Result<Self, WasmError> {
        if value.is_null() || value.is_undefined() {
            return Ok(Self {
                source_name: "memory.sysml".to_string(),
                stdlib: None,
            });
        }
        let raw: Value = from_js(value)?;
        let source_name = raw
            .get("sourceName")
            .or_else(|| raw.get("source_name"))
            .and_then(Value::as_str)
            .unwrap_or("memory.sysml")
            .to_string();
        let stdlib = raw
            .get("stdlib")
            .cloned()
            .map(serde_json::from_value)
            .transpose()?;
        Ok(Self {
            source_name,
            stdlib,
        })
    }
}

fn sysml_json_import_options_from_js(value: JsValue) -> Result<SysmlJsonImportOptions, WasmError> {
    if value.is_null() || value.is_undefined() {
        return Ok(SysmlJsonImportOptions::default());
    }
    from_js(value)
}

fn import_response(report: SysmlJsonImportReport) -> Result<Response, WasmError> {
    let ok = !report.has_errors();
    let diagnostics = serde_json::to_value(&report.diagnostics)?;
    let metadata = report.metadata.clone();
    Ok(Response {
        ok,
        value: Some(json!({
            "status": if ok { "ok" } else { "partial" },
            "document": report.document,
            "importerVersion": SYSML_JSON_IMPORTER_VERSION,
        })),
        diagnostics,
        errors: Vec::new(),
        metadata,
    })
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Response {
    ok: bool,
    value: Option<Value>,
    diagnostics: Value,
    errors: Vec<WasmError>,
    metadata: BTreeMap<String, Value>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct WasmError {
    code: String,
    message: String,
}

impl WasmError {
    fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
        }
    }
}

impl std::fmt::Display for WasmError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for WasmError {}

impl From<serde_json::Error> for WasmError {
    fn from(value: serde_json::Error) -> Self {
        Self::new("json", value.to_string())
    }
}

macro_rules! impl_error {
    ($source:ty, $code:literal) => {
        impl From<$source> for WasmError {
            fn from(value: $source) -> Self {
                Self::new($code, value.to_string())
            }
        }
    };
}

impl_error!(mercurio_core::DatalogError, "datalog");
impl_error!(mercurio_core::GraphError, "graph");
impl_error!(mercurio_core::KirError, "kir");
impl_error!(mercurio_core::RuntimeError, "runtime");
impl_error!(mercurio_core::AssessmentError, "assessment");
impl_error!(DiagramError, "diagram");
impl_error!(TableError, "table");
impl_error!(Diagnostic, "diagnostic");
impl_error!(SysmlJsonImportError, "sysmlJsonImport");

fn load_stdlib(stdlib: Option<KirDocument>) -> Result<KirDocument, WasmError> {
    match stdlib {
        Some(document) => {
            document.validate()?;
            Ok(document)
        }
        None => KirDocument::from_str(DEFAULT_STDLIB).map_err(Into::into),
    }
}

fn load_library_context(
    language: SourceLanguage,
    library_context: Option<KirDocument>,
) -> Result<KirDocument, WasmError> {
    match library_context {
        Some(document) => {
            document.validate()?;
            Ok(document)
        }
        None if language == SourceLanguage::Sysml => load_stdlib(None),
        None => Ok(KirDocument {
            metadata: BTreeMap::new(),
            elements: Vec::new(),
        }),
    }
}

fn parse_language(language: &str) -> Result<SourceLanguage, WasmError> {
    match language.to_ascii_lowercase().as_str() {
        "sysml" | "sysml2" => Ok(SourceLanguage::Sysml),
        "kerml" => Ok(SourceLanguage::Kerml),
        _ => Err(WasmError::new(
            "language",
            format!("unsupported source language: {language}"),
        )),
    }
}

fn language_as_str(language: SourceLanguage) -> &'static str {
    match language {
        SourceLanguage::Sysml => "sysml",
        SourceLanguage::Kerml => "kerml",
    }
}

fn format_source_text(input: &str, _language: SourceLanguage) -> Result<String, WasmError> {
    Ok(input.to_string())
}

#[derive(Serialize)]
struct LintReport {
    status: &'static str,
    diagnostics: Vec<Diagnostic>,
}

impl LintReport {
    fn has_errors(&self) -> bool {
        !self.diagnostics.is_empty()
    }
}

fn lint_source(
    input: &str,
    source_name: &str,
    language: SourceLanguage,
    stdlib: &KirDocument,
) -> LintReport {
    match language {
        SourceLanguage::Sysml => {
            let report = compile_sysml_text_with_context_report(input, source_name, &[], stdlib);
            LintReport {
                status: semantic_status(report.status),
                diagnostics: report.diagnostics,
            }
        }
        SourceLanguage::Kerml => match parse_kerml(input) {
            Ok(_) => LintReport {
                status: "ok",
                diagnostics: Vec::new(),
            },
            Err(diagnostic) => LintReport {
                status: "failed",
                diagnostics: vec![diagnostic],
            },
        },
    }
}

fn semantic_status(status: SemanticCompileStatus) -> &'static str {
    match status {
        SemanticCompileStatus::Ok => "ok",
        SemanticCompileStatus::Partial => "partial",
        SemanticCompileStatus::Failed => "failed",
    }
}

fn assessment_fact_summary(facts: &[Fact]) -> Value {
    let mut predicates = facts
        .iter()
        .map(|fact| fact.predicate.clone())
        .collect::<Vec<_>>();
    predicates.sort();
    predicates.dedup();
    json!({
        "factCount": facts.len(),
        "predicates": predicates,
        "items": facts,
    })
}

fn find_feature_id(document: &KirDocument, feature_name: &str) -> Option<String> {
    document
        .elements
        .iter()
        .find(|element| {
            element_name(&element.properties) == Some(feature_name)
                && element.properties.contains_key("expression_ir")
        })
        .or_else(|| {
            document
                .elements
                .iter()
                .find(|element| element_name(&element.properties) == Some(feature_name))
        })
        .map(|element| element.id.clone())
}

fn find_owner_id_by_name(document: &KirDocument, owner_name: &str) -> Option<String> {
    document
        .elements
        .iter()
        .find(|element| element_name(&element.properties) == Some(owner_name))
        .map(|element| element.id.clone())
}

fn find_owner_id_for_feature(document: &KirDocument, feature_id: &str) -> Option<String> {
    document
        .elements
        .iter()
        .find(|element| {
            property_array_contains(&element.properties, "features", feature_id)
                || property_array_contains(&element.properties, "members", feature_id)
                || property_array_contains(&element.properties, "member_ids", feature_id)
        })
        .map(|element| element.id.clone())
}

fn property_array_contains(
    properties: &BTreeMap<String, Value>,
    key: &str,
    expected: &str,
) -> bool {
    properties
        .get(key)
        .and_then(Value::as_array)
        .map(|values| values.iter().any(|value| value.as_str() == Some(expected)))
        .unwrap_or(false)
}

fn element_name(properties: &BTreeMap<String, Value>) -> Option<&str> {
    properties
        .get("declared_name")
        .or_else(|| properties.get("name"))
        .and_then(Value::as_str)
}

fn value_type(value: &Value) -> &'static str {
    match value {
        Value::Null => "null",
        Value::Bool(_) => "boolean",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}

fn snippet_diagnostic(diagnostic: &mercurio_core::frontend::diagnostics::Diagnostic) -> Value {
    let (line, column) = diagnostic
        .span
        .as_ref()
        .map(|span| (span.start_line, span.start_col))
        .unwrap_or((1, 1));
    json!({
        "severity": "error",
        "message": diagnostic.message,
        "startLineNumber": line,
        "startColumn": column,
        "endLineNumber": diagnostic.span.as_ref().map(|span| span.end_line).unwrap_or(line),
        "endColumn": diagnostic.span.as_ref().map(|span| span.end_col).unwrap_or(column),
        "start_line_number": line,
        "start_column": column,
        "end_line_number": diagnostic.span.as_ref().map(|span| span.end_line).unwrap_or(line),
        "end_column": diagnostic.span.as_ref().map(|span| span.end_col).unwrap_or(column),
        "line": line,
        "column": column,
    })
}

fn push_ast_symbol(symbols: &mut Vec<Value>, id: &str, kind: &str, label: &str, span: &SourceSpan) {
    symbols.push(json!({
        "id": id,
        "kind": kind,
        "label": label,
        "startLineNumber": span.start_line,
        "start_line_number": span.start_line,
    }));
}

fn declaration_outline_node(
    declaration: &Declaration,
    owner: Option<&str>,
    symbols: &mut Vec<Value>,
) -> Value {
    if let Some(definition) = declaration.as_definition_like() {
        let id = scoped_ast_id(owner, &definition.name);
        let kind = format!("{}Definition", pascal_keyword(&definition.keyword));
        push_ast_symbol(symbols, &id, &kind, &definition.name, &definition.span);
        let children = definition
            .members
            .iter()
            .map(|member| declaration_outline_node(member, Some(&id), symbols))
            .collect::<Vec<_>>();
        return json!({
            "id": id,
            "elementId": id,
            "element_id": id,
            "label": definition.name,
            "kind": kind,
            "properties": ast_properties(&definition.name, &definition.span),
            "children": children,
        });
    }
    if let Some(usage) = declaration.as_usage_like() {
        return usage_outline_node(&usage, owner, symbols);
    }

    match declaration {
        Declaration::Package(package) => {
            let name = package.name.as_colon_string();
            let id = scoped_ast_id(owner, &name);
            package_outline_node(&id, &name, &package.span, &package.members, symbols)
        }
        Declaration::GenericDefinition(_) | Declaration::GenericUsage(_) => {
            unreachable!("definition-like and usage-like declarations are handled above")
        }
        Declaration::Import(import) => {
            let name = import.path.as_colon_string();
            let id = scoped_ast_id(owner, &name);
            push_ast_symbol(symbols, &id, "Import", &name, &import.span);
            json!({
                "id": id,
                "elementId": id,
                "element_id": id,
                "label": name,
                "kind": "Import",
                "properties": ast_properties(&name, &import.span),
                "children": [],
            })
        }
        Declaration::Alias(alias) => {
            let id = scoped_ast_id(owner, &alias.name);
            push_ast_symbol(symbols, &id, "Alias", &alias.name, &alias.span);
            json!({
                "id": id,
                "elementId": id,
                "element_id": id,
                "label": alias.name,
                "kind": "Alias",
                "properties": ast_properties(&alias.name, &alias.span),
                "children": [],
            })
        }
    }
}

fn package_outline_node(
    id: &str,
    name: &str,
    span: &SourceSpan,
    members: &[Declaration],
    symbols: &mut Vec<Value>,
) -> Value {
    push_ast_symbol(symbols, id, "Package", name, span);
    let children = members
        .iter()
        .map(|member| declaration_outline_node(member, Some(id), symbols))
        .collect::<Vec<_>>();
    json!({
        "id": id,
        "elementId": id,
        "element_id": id,
        "label": name,
        "kind": "Package",
        "properties": ast_properties(name, span),
        "children": children,
    })
}

fn usage_outline_node(
    usage: &GenericUsageDecl,
    owner: Option<&str>,
    symbols: &mut Vec<Value>,
) -> Value {
    let id = scoped_ast_id(owner, &usage.name);
    let kind = format!("{}Usage", pascal_keyword(&usage.keyword));
    push_ast_symbol(symbols, &id, &kind, &usage.name, &usage.span);
    let children = usage
        .body_members
        .iter()
        .map(|member| declaration_outline_node(member, Some(&id), symbols))
        .collect::<Vec<_>>();
    json!({
        "id": id,
        "elementId": id,
        "element_id": id,
        "label": usage.name,
        "kind": kind,
        "properties": ast_properties(&usage.name, &usage.span),
        "children": children,
    })
}

fn scoped_ast_id(owner: Option<&str>, name: &str) -> String {
    owner
        .map(|owner| format!("{owner}::{name}"))
        .unwrap_or_else(|| name.to_string())
}

fn ast_properties(name: &str, span: &SourceSpan) -> Value {
    json!({
        "name": name,
        "metadata": {
            "name": name,
            "source_span": {
                "start_line": span.start_line,
                "start_col": span.start_col,
                "end_line": span.end_line,
                "end_col": span.end_col,
            },
        },
        "source_span": {
            "start_line": span.start_line,
            "start_col": span.start_col,
            "end_line": span.end_line,
            "end_col": span.end_col,
        },
    })
}

fn pascal_keyword(keyword: &str) -> String {
    keyword
        .split(|character: char| !character.is_ascii_alphanumeric())
        .filter(|part| !part.is_empty())
        .map(|part| {
            let mut chars = part.chars();
            match chars.next() {
                Some(first) => first.to_ascii_uppercase().to_string() + chars.as_str(),
                None => String::new(),
            }
        })
        .collect::<String>()
}

fn default_source_name() -> String {
    "memory.sysml".to_string()
}

fn default_source_language() -> String {
    "sysml".to_string()
}

fn run_runtime_query(runtime: &Runtime, query: RuntimeQuery) -> Result<Value, WasmError> {
    match query.kind {
        RuntimeQueryKind::Subtypes => {
            let type_id = required(query.type_id, "typeId")?;
            let result = runtime.get_subtypes(&type_id)?;
            Ok(json!({
                "value": result.value,
                "explanation": result.explanation,
            }))
        }
        RuntimeQueryKind::Features => {
            let type_id = required(query.type_id, "typeId")?;
            let result = runtime.get_features(&type_id)?;
            Ok(json!({
                "value": result.value,
                "explanation": result.explanation,
            }))
        }
        RuntimeQueryKind::Evaluate => {
            let feature_id = required(query.feature_id, "featureId")?;
            let owner_id = required(query.owner_id, "ownerId")?;
            let context = execution_context(query.context);
            let result = runtime.evaluate(&feature_id, &owner_id, &context)?;
            Ok(json!({
                "value": result.value,
                "explanation": result.explanation,
            }))
        }
    }
}

fn execution_context(context: RuntimeContextDto) -> ExecutionContext {
    let values = context
        .values
        .into_iter()
        .map(|entry| ((entry.owner_id, entry.feature_id), entry.value))
        .collect();
    ExecutionContext {
        values,
        version: context.version,
    }
}

fn required(value: Option<String>, field: &str) -> Result<String, WasmError> {
    value.ok_or_else(|| WasmError::new("query", format!("missing runtime query field: {field}")))
}

fn from_js<T>(value: JsValue) -> Result<T, WasmError>
where
    T: serde::de::DeserializeOwned,
{
    serde_wasm_bindgen::from_value(value).map_err(|err| WasmError::new("js", err.to_string()))
}

fn to_js<T>(value: &T) -> JsValue
where
    T: Serialize,
{
    serde_wasm_bindgen::to_value(value).unwrap_or_else(|err| {
        JsValue::from_str(&format!("failed to serialize wasm response: {err}"))
    })
}

fn json_response(action: impl FnOnce() -> Result<Response, WasmError>) -> JsValue {
    match action() {
        Ok(response) => to_js(&response),
        Err(error) => to_js(&Response {
            ok: false,
            value: None,
            diagnostics: json!([]),
            errors: vec![error],
            metadata: BTreeMap::new(),
        }),
    }
}

fn success<const N: usize>(value: Value, metadata_items: [(&str, Value); N]) -> Response {
    Response {
        ok: true,
        value: Some(value),
        diagnostics: json!([]),
        errors: Vec::new(),
        metadata: metadata(metadata_items),
    }
}

fn error_response(code: &str, message: String, diagnostics: Option<Value>) -> Response {
    Response {
        ok: false,
        value: None,
        diagnostics: diagnostics.unwrap_or_else(|| json!([])),
        errors: vec![WasmError::new(code, message)],
        metadata: BTreeMap::new(),
    }
}

fn metadata<const N: usize>(items: [(&str, Value); N]) -> BTreeMap<String, Value> {
    items
        .into_iter()
        .map(|(key, value)| (key.to_string(), value))
        .collect()
}

fn js_error(error: WasmError) -> JsValue {
    JsValue::from_str(&error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_stdlib_is_valid_kir() {
        let document = load_stdlib(None).unwrap();
        assert!(!document.elements.is_empty());
    }

    #[test]
    fn default_stdlib_resolves_port_and_interface_definitions() {
        let stdlib = load_stdlib(None).unwrap();
        let report = compile_sysml_text_with_context_report(
            "package Demo {
                item def Command;

                port def CommandPort {
                    item command: Command;
                }

                interface def CommandInterface {
                    end controller: CommandPort;
                    end rotor: CommandPort;
                }
            }",
            "ports.sysml",
            &[],
            &stdlib,
        );

        assert!(
            report.diagnostics.is_empty(),
            "unexpected diagnostics: {:?}",
            report.diagnostics
        );
        assert!(report.document.is_some());
    }

    #[test]
    fn session_merges_user_sources_with_stdlib() {
        let stdlib = load_stdlib(None).unwrap();
        let module = parse_sysml_recovering("package Demo { }").unwrap().module;
        let document =
            compile_sysml_text_with_context_report("package Demo { }", "demo.sysml", &[], &stdlib)
                .document
                .unwrap();
        let mut session = MercurioSession {
            stdlib,
            sources: Vec::new(),
        };

        session.sources.push(SessionSource {
            source_name: "demo.sysml".to_string(),
            language: SourceLanguage::Sysml,
            module,
            document,
        });
        assert!(session.merged_document().unwrap().elements.len() > session.stdlib.elements.len());
    }
}
