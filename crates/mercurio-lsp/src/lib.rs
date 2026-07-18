use std::collections::BTreeMap;
use std::io::{self, BufRead, Write};
use std::path::Path;

use mercurio_kir::KirDocument;
use mercurio_language_contracts::{
    LanguageAnalysis, LanguageRegistry, ScopeProvider, SourceDocument, SymbolDescriptor, TextRange,
    document_symbols,
};
use mercurio_model::{Graph, MetamodelAttributeRegistry, query_element_attributes};
use mercurio_semantic_services::mutation::ModelChangeEvent;
use mercurio_workspace::WorkspaceSymbolIndex;
use serde_json::{Value, json};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompletionKeyword {
    pub label: String,
    pub detail: String,
}

#[derive(Debug, Clone)]
struct OpenDocument {
    revision: u64,
    text: String,
}

pub struct LanguageServer {
    registry: LanguageRegistry,
    library: KirDocument,
    documents: BTreeMap<String, OpenDocument>,
    analyses: BTreeMap<String, LanguageAnalysis>,
    index: WorkspaceSymbolIndex,
    completion_keywords: Vec<CompletionKeyword>,
    shutdown: bool,
}

impl LanguageServer {
    pub fn new(registry: LanguageRegistry, library: KirDocument) -> Self {
        Self::with_completion_keywords(registry, library, Vec::new())
    }

    pub fn with_completion_keywords(
        registry: LanguageRegistry,
        library: KirDocument,
        mut completion_keywords: Vec<CompletionKeyword>,
    ) -> Self {
        completion_keywords.sort_by(|left, right| left.label.cmp(&right.label));
        completion_keywords.dedup_by(|left, right| left.label == right.label);
        let mut index = WorkspaceSymbolIndex::new();
        index.update(document_symbols(
            "",
            "mercurio-stdlib://library",
            0,
            &library,
        ));
        Self {
            registry,
            library,
            documents: BTreeMap::new(),
            analyses: BTreeMap::new(),
            index,
            completion_keywords,
            shutdown: false,
        }
    }

    pub fn handle(&mut self, message: Value) -> Vec<Value> {
        let id = message.get("id").cloned();
        let method = message
            .get("method")
            .and_then(Value::as_str)
            .unwrap_or_default();
        let params = message.get("params").cloned().unwrap_or(Value::Null);
        match method {
            "initialize" => vec![response(
                id,
                json!({"capabilities":{
                "textDocumentSync":{"openClose":true,"change":2},
                "documentSymbolProvider":true,"workspaceSymbolProvider":true,
                "definitionProvider":true,"referencesProvider":true,"hoverProvider":true,
                "completionProvider":{"triggerCharacters":[" ",":",".","@"]},
                "renameProvider":{"prepareProvider":true},
                "codeActionProvider":true,
                "semanticTokensProvider":{"legend":{"tokenTypes":["keyword","type","variable","property","namespace"],"tokenModifiers":["declaration","readonly"]},"full":true},
                "documentFormattingProvider":true
            },"serverInfo":{"name":"mercurio-lsp","version":env!("CARGO_PKG_VERSION")}}),
            )],
            "initialized" | "exit" => Vec::new(),
            "shutdown" => {
                self.shutdown = true;
                vec![response(id, Value::Null)]
            }
            "textDocument/didOpen" => self.did_open(&params),
            "textDocument/didChange" => self.did_change(&params),
            "textDocument/didClose" => self.did_close(&params),
            "textDocument/documentSymbol" => vec![response(id, self.document_symbols(&params))],
            "workspace/symbol" => vec![response(id, self.workspace_symbols(&params))],
            "textDocument/definition" => vec![response(id, self.definition(&params))],
            "textDocument/references" => vec![response(id, self.references(&params))],
            "textDocument/hover" => vec![response(id, self.hover(&params))],
            "textDocument/completion" => vec![response(id, self.completion(&params))],
            "textDocument/prepareRename" => vec![response(id, self.prepare_rename(&params))],
            "textDocument/rename" => vec![response(id, self.rename(&params))],
            "textDocument/codeAction" => vec![response(id, self.code_actions(&params))],
            "textDocument/semanticTokens/full" => vec![response(id, self.semantic_tokens(&params))],
            "textDocument/formatting" => vec![response(id, self.formatting(&params))],
            "mercurio/virtualDocument" => vec![response(id, self.virtual_document(&params))],
            _ if id.is_some() => vec![
                json!({"jsonrpc":"2.0","id":id,"error":{"code":-32601,"message":"method not found"}}),
            ],
            _ => Vec::new(),
        }
    }

    pub fn is_shutdown(&self) -> bool {
        self.shutdown
    }

    pub fn model_changed(&mut self, _event: &ModelChangeEvent) -> Vec<Value> {
        self.refresh()
    }

    fn did_open(&mut self, params: &Value) -> Vec<Value> {
        let Some(document) = params.get("textDocument") else {
            return Vec::new();
        };
        let Some(uri) = document.get("uri").and_then(Value::as_str) else {
            return Vec::new();
        };
        self.documents.insert(
            uri.to_string(),
            OpenDocument {
                revision: revision(document),
                text: document
                    .get("text")
                    .and_then(Value::as_str)
                    .unwrap_or_default()
                    .to_string(),
            },
        );
        self.refresh()
    }

    fn did_change(&mut self, params: &Value) -> Vec<Value> {
        let Some(identifier) = params.get("textDocument") else {
            return Vec::new();
        };
        let Some(uri) = identifier.get("uri").and_then(Value::as_str) else {
            return Vec::new();
        };
        let Some(document) = self.documents.get_mut(uri) else {
            return Vec::new();
        };
        for change in params
            .get("contentChanges")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            let replacement = change
                .get("text")
                .and_then(Value::as_str)
                .unwrap_or_default();
            if let Some(range) = change.get("range") {
                let start = range
                    .get("start")
                    .and_then(|position| position_to_byte(&document.text, position));
                let end = range
                    .get("end")
                    .and_then(|position| position_to_byte(&document.text, position));
                if let (Some(start), Some(end)) = (start, end)
                    && start <= end
                    && end <= document.text.len()
                    && document.text.is_char_boundary(start)
                    && document.text.is_char_boundary(end)
                {
                    document.text.replace_range(start..end, replacement);
                }
            } else {
                document.text = replacement.to_string();
            }
        }
        document.revision = revision(identifier);
        self.refresh()
    }

    fn did_close(&mut self, params: &Value) -> Vec<Value> {
        let Some(uri) = document_uri(params) else {
            return Vec::new();
        };
        self.documents.remove(uri);
        self.analyses.remove(uri);
        self.index.remove(uri);
        vec![publish_diagnostics(uri, Vec::new())]
    }

    fn refresh(&mut self) -> Vec<Value> {
        let sources = self
            .documents
            .iter()
            .map(|(name, document)| SourceDocument::new(name, document.revision, &document.text))
            .collect::<Vec<_>>();
        for name in self.documents.keys().cloned().collect::<Vec<_>>() {
            let Some(service) = self.registry.service_for_path(Path::new(&name)) else {
                continue;
            };
            if let Some(analysis) = service.analyze_workspace(&sources, &name, &self.library) {
                self.index.update(analysis.symbols.clone());
                self.analyses.insert(name, analysis);
            }
        }
        self.analyses.iter().map(|(uri, analysis)| {
            let text = self.text(uri);
            let diagnostics = analysis.diagnostics.iter().map(|diagnostic| {
                let range = diagnostic.span.as_ref().map(|span| {
                    byte_range(text, TextRange::new(
                        mercurio_language_contracts::line_col_to_byte(text, span.start_line, span.start_col),
                        mercurio_language_contracts::line_col_to_byte(text, span.end_line, span.end_col),
                    ))
                }).unwrap_or_else(zero_range);
                json!({"range":range,"severity":1,"source":"mercurio","message":diagnostic.message})
            }).collect();
            publish_diagnostics(uri, diagnostics)
        }).collect()
    }

    fn document_symbols(&self, params: &Value) -> Value {
        let Some(uri) = document_uri(params) else {
            return json!([]);
        };
        let Some(analysis) = self.analyses.get(uri) else {
            return json!([]);
        };
        Value::Array(
            analysis
                .symbols
                .symbols
                .iter()
                .map(|symbol| {
                    json!({
                        "name":symbol.qualified_name,"detail":symbol.concept.as_str(),"kind":5,
                        "range":byte_range(self.text(uri),symbol.span),
                        "selectionRange":byte_range(self.text(uri),symbol.span)
                    })
                })
                .collect(),
        )
    }

    fn workspace_symbols(&self, params: &Value) -> Value {
        let query = params
            .get("query")
            .and_then(Value::as_str)
            .unwrap_or_default();
        Value::Array(self.index.symbols_by_qualified_name_prefix(query).iter()
            .map(|symbol| json!({"name":symbol.qualified_name,"kind":5,"location":self.location(symbol)})).collect())
    }

    fn definition(&self, params: &Value) -> Value {
        let Some((uri, offset)) = self.position(params) else {
            return Value::Null;
        };
        let Some(reference) = self
            .analyses
            .get(uri)
            .and_then(|analysis| analysis.resolve_reference(uri, offset))
        else {
            return Value::Null;
        };
        self.index
            .symbol_by_element_id(&reference.target_element_id)
            .map(|symbol| self.location(&symbol))
            .unwrap_or(Value::Null)
    }

    fn references(&self, params: &Value) -> Value {
        let Some((uri, offset)) = self.position(params) else {
            return json!([]);
        };
        let Some(analysis) = self.analyses.get(uri) else {
            return json!([]);
        };
        let declared_target = analysis.element_at(uri, offset).and_then(|element| {
            let symbol = self.index.symbol_by_element_id(&element.element_id)?;
            let declared_name = symbol.qualified_name.rsplit('.').next()?;
            (word_at(self.text(uri), offset) == declared_name).then_some(element.element_id)
        });
        let target = declared_target.or_else(|| {
            analysis
                .resolve_reference(uri, offset)
                .map(|reference| reference.target_element_id)
        });
        let Some(target) = target else {
            return json!([]);
        };
        let mut result = Vec::new();
        for (source, analysis) in &self.analyses {
            for reference in analysis.references(source) {
                if reference.target_element_id == target {
                    result.push(
                        json!({"uri":source,"range":byte_range(self.text(source),reference.span)}),
                    );
                }
            }
        }
        Value::Array(result)
    }

    fn completion(&self, params: &Value) -> Value {
        let Some((uri, offset)) = self.position(params) else {
            return json!([]);
        };
        let prefix = word_at(self.text(uri), offset);
        let mut items = BTreeMap::<String, Value>::new();
        if let Some(analysis) = self.analyses.get(uri) {
            for symbol in analysis.visible_symbols(uri, offset) {
                let label = symbol
                    .qualified_name
                    .rsplit(['.', ':'])
                    .find(|part| !part.is_empty())
                    .unwrap_or(symbol.qualified_name.as_str());
                if !prefix.is_empty() && !label.starts_with(prefix) {
                    continue;
                }
                items.entry(label.to_string()).or_insert_with(|| {
                    json!({
                        "label":label,
                        "kind":7,
                        "detail":symbol.concept.as_str(),
                        "documentation":symbol.qualified_name,
                        "insertText":label
                    })
                });
            }
        }
        for keyword in &self.completion_keywords {
            if !prefix.is_empty() && !keyword.label.starts_with(prefix) {
                continue;
            }
            items.entry(keyword.label.clone()).or_insert_with(|| {
                json!({
                    "label":keyword.label,
                    "kind":14,
                    "detail":keyword.detail,
                    "insertText":keyword.label
                })
            });
        }
        Value::Array(items.into_values().collect())
    }
    fn prepare_rename(&self, params: &Value) -> Value {
        let Some((uri, offset)) = self.position(params) else {
            return Value::Null;
        };
        let word = word_at(self.text(uri), offset);
        if word.is_empty() || self.target_at(uri, offset).is_none() {
            return Value::Null;
        }
        let range = word_range_at(self.text(uri), offset);
        json!({"range":byte_range(self.text(uri), range),"placeholder":word})
    }

    fn rename(&self, params: &Value) -> Value {
        let Some((uri, offset)) = self.position(params) else {
            return Value::Null;
        };
        let new_name = params
            .get("newName")
            .and_then(Value::as_str)
            .unwrap_or_default();
        if !is_identifier(new_name) {
            return Value::Null;
        }
        let Some(target) = self.target_at(uri, offset) else {
            return Value::Null;
        };
        let Some(symbol) = self.index.symbol_by_element_id(&target) else {
            return Value::Null;
        };
        let old_name = symbol
            .qualified_name
            .rsplit(['.', ':'])
            .find(|part| !part.is_empty())
            .unwrap_or(symbol.qualified_name.as_str());
        let mut changes = BTreeMap::<String, Vec<Value>>::new();
        if !symbol.source_name.is_empty() {
            let declaration_text = self.text(&symbol.source_name);
            if let Some(declaration_range) =
                identifier_range_in_span(declaration_text, symbol.span, old_name)
            {
                changes
                    .entry(symbol.source_name.clone())
                    .or_default()
                    .push(json!({"range":byte_range(declaration_text,declaration_range),"newText":new_name}));
            }
        }
        for (source, analysis) in &self.analyses {
            for reference in analysis.references(source) {
                if reference.target_element_id == target {
                    changes.entry(source.clone()).or_default().push(json!({
                        "range":byte_range(self.text(source),reference.span),
                        "newText":new_name
                    }));
                }
            }
        }
        json!({"changes":changes})
    }

    fn code_actions(&self, params: &Value) -> Value {
        let Some(uri) = document_uri(params) else {
            return json!([]);
        };
        let text = self.text(uri);
        let formatted = format_document_text(text, 4, true);
        if formatted == text {
            return json!([]);
        }
        json!([{
            "title":"Format document",
            "kind":"source.fixAll.mercurio",
            "isPreferred":true,
            "edit":{"changes":{uri:[{"range":full_document_range(text),"newText":formatted}]}}
        }])
    }

    fn semantic_tokens(&self, params: &Value) -> Value {
        let Some(uri) = document_uri(params) else {
            return json!({"data":[]});
        };
        let text = self.text(uri);
        let keywords = self
            .completion_keywords
            .iter()
            .map(|keyword| keyword.label.as_str())
            .collect::<std::collections::BTreeSet<_>>();
        let mut raw = Vec::<(u32, u32, u32, u32, u32)>::new();
        for (range, word) in identifier_ranges(text) {
            let position = byte_position(text, range.start_byte);
            let line = position
                .get("line")
                .and_then(Value::as_u64)
                .unwrap_or_default() as u32;
            let start = position
                .get("character")
                .and_then(Value::as_u64)
                .unwrap_or_default() as u32;
            let length = word.encode_utf16().count() as u32;
            let token_type = if keywords.contains(word) {
                0
            } else if word.chars().next().is_some_and(char::is_uppercase) {
                1
            } else {
                2
            };
            raw.push((line, start, length, token_type, 0));
        }
        let mut data = Vec::<u32>::new();
        let mut previous_line = 0;
        let mut previous_start = 0;
        for (line, start, length, token_type, modifiers) in raw {
            let delta_line = line - previous_line;
            let delta_start = if delta_line == 0 {
                start - previous_start
            } else {
                start
            };
            data.extend([delta_line, delta_start, length, token_type, modifiers]);
            previous_line = line;
            previous_start = start;
        }
        json!({"data":data})
    }

    fn formatting(&self, params: &Value) -> Value {
        let Some(uri) = document_uri(params) else {
            return json!([]);
        };
        let text = self.text(uri);
        let tab_size = params
            .get("options")
            .and_then(|options| options.get("tabSize"))
            .and_then(Value::as_u64)
            .unwrap_or(4) as usize;
        let insert_spaces = params
            .get("options")
            .and_then(|options| options.get("insertSpaces"))
            .and_then(Value::as_bool)
            .unwrap_or(true);
        let formatted = format_document_text(text, tab_size, insert_spaces);
        if formatted == text {
            json!([])
        } else {
            json!([{"range":full_document_range(text),"newText":formatted}])
        }
    }

    fn target_at(&self, uri: &str, offset: usize) -> Option<String> {
        let analysis = self.analyses.get(uri)?;
        let declared_target = analysis.element_at(uri, offset).and_then(|element| {
            let symbol = self.index.symbol_by_element_id(&element.element_id)?;
            let declared_name = symbol
                .qualified_name
                .rsplit(['.', ':'])
                .find(|part| !part.is_empty())?;
            (word_at(self.text(uri), offset) == declared_name).then(|| element.element_id.clone())
        });
        declared_target.or_else(|| {
            analysis
                .resolve_reference(uri, offset)
                .map(|reference| reference.target_element_id)
        })
    }
    fn hover(&self, params: &Value) -> Value {
        let Some((uri, offset)) = self.position(params) else {
            return Value::Null;
        };
        let Some(analysis) = self.analyses.get(uri) else {
            return Value::Null;
        };
        let declared_target = analysis.element_at(uri, offset).and_then(|element| {
            let symbol = self.index.symbol_by_element_id(&element.element_id)?;
            let declared_name = symbol.qualified_name.rsplit('.').next()?;
            (word_at(self.text(uri), offset) == declared_name).then_some(element.element_id)
        });
        let target = declared_target.or_else(|| {
            analysis
                .resolve_reference(uri, offset)
                .map(|reference| reference.target_element_id)
        });
        let Some(target) = target else {
            return Value::Null;
        };
        let mut document = self.library.clone();
        for analysis in self.analyses.values() {
            if let Some(compiled) = &analysis.document {
                document.elements.extend(compiled.elements.clone());
            }
        }
        document
            .elements
            .sort_by(|left, right| left.id.cmp(&right.id));
        document
            .elements
            .dedup_by(|left, right| left.id == right.id);
        let Ok(graph) = Graph::from_document(document) else {
            return Value::Null;
        };
        let registry = MetamodelAttributeRegistry::build(&graph);
        let Some(node_id) = graph.node_id(&target) else {
            return Value::Null;
        };
        let Some(query) = query_element_attributes(&graph, &registry, node_id, None) else {
            return Value::Null;
        };
        let effective = query
            .rows
            .iter()
            .filter_map(|row| {
                row.effective_value
                    .clone()
                    .map(|value| (row.name.clone(), value))
            })
            .collect::<BTreeMap<_, _>>();
        let metatype = query
            .metatype
            .as_ref()
            .map(|item| item.label.as_str())
            .unwrap_or("unknown");
        let chain = query
            .metatype_specialization_chain
            .iter()
            .map(|item| item.label.as_str())
            .collect::<Vec<_>>()
            .join(" -> ");
        json!({"contents":{"kind":"markdown","value":format!(
            "**{}**\\n\\nMetaclass: {}\\n\\nMetatype chain: {}\\n\\nEffective values:\\n{}",
            target, metatype, chain, serde_json::to_string_pretty(&effective).unwrap_or_default()
        )}})
    }

    fn virtual_document(&self, params: &Value) -> Value {
        let id = params
            .get("elementId")
            .and_then(Value::as_str)
            .unwrap_or_default();
        if id.is_empty() {
            return json!({"readOnly":true,"text":serde_json::to_string_pretty(&self.library).unwrap_or_default()});
        }
        self.library.elements.iter().find(|element| element.id == id)
            .map(|element| json!({"readOnly":true,"text":serde_json::to_string_pretty(element).unwrap_or_default()}))
            .unwrap_or(Value::Null)
    }

    fn position<'a>(&'a self, params: &'a Value) -> Option<(&'a str, usize)> {
        let uri = document_uri(params)?;
        Some((
            uri,
            position_to_byte(self.text(uri), params.get("position")?)?,
        ))
    }

    fn location(&self, symbol: &SymbolDescriptor) -> Value {
        let uri = if symbol.source_name.is_empty() {
            "mercurio-stdlib://library"
        } else {
            &symbol.source_name
        };
        json!({"uri":uri,"range":byte_range(self.text(&symbol.source_name),symbol.span)})
    }

    fn text(&self, uri: &str) -> &str {
        self.documents
            .get(uri)
            .map(|document| document.text.as_str())
            .unwrap_or_default()
    }
}

pub fn serve_stdio(mut server: LanguageServer) -> io::Result<()> {
    let mut reader = io::BufReader::new(io::stdin().lock());
    let mut writer = io::stdout().lock();
    while let Some(message) = read_message(&mut reader)? {
        let exit = message.get("method").and_then(Value::as_str) == Some("exit");
        for response in server.handle(message) {
            write_message(&mut writer, &response)?;
        }
        if exit {
            break;
        }
    }
    Ok(())
}

pub fn read_message(reader: &mut impl BufRead) -> io::Result<Option<Value>> {
    let mut length = None;
    loop {
        let mut header = String::new();
        if reader.read_line(&mut header)? == 0 {
            return Ok(None);
        }
        if header == "\r\n" || header == "\n" {
            break;
        }
        if let Some(value) = header.strip_prefix("Content-Length:") {
            length = value.trim().parse().ok()
        }
    }
    let Some(length) = length else {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "missing Content-Length",
        ));
    };
    let mut bytes = vec![0; length];
    std::io::Read::read_exact(reader, &mut bytes)?;
    serde_json::from_slice(&bytes)
        .map(Some)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))
}

pub fn write_message(writer: &mut impl Write, message: &Value) -> io::Result<()> {
    let bytes = serde_json::to_vec(message).map_err(io::Error::other)?;
    write!(writer, "Content-Length: {}\r\n\r\n", bytes.len())?;
    writer.write_all(&bytes)?;
    writer.flush()
}

fn response(id: Option<Value>, result: Value) -> Value {
    json!({"jsonrpc":"2.0","id":id.unwrap_or(Value::Null),"result":result})
}
fn revision(value: &Value) -> u64 {
    value
        .get("version")
        .and_then(Value::as_i64)
        .unwrap_or_default()
        .max(0) as u64
}
fn document_uri(params: &Value) -> Option<&str> {
    params.get("textDocument")?.get("uri")?.as_str()
}
fn publish_diagnostics(uri: &str, diagnostics: Vec<Value>) -> Value {
    json!({"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"uri":uri,"diagnostics":diagnostics}})
}
fn word_at(text: &str, offset: usize) -> &str {
    let offset = offset.min(text.len());
    let start = text[..offset]
        .rfind(|character: char| !(character.is_alphanumeric() || character == '_'))
        .map(|index| index + 1)
        .unwrap_or_default();
    let end = text[offset..]
        .find(|character: char| !(character.is_alphanumeric() || character == '_'))
        .map(|index| offset + index)
        .unwrap_or(text.len());
    &text[start..end]
}
fn is_identifier(value: &str) -> bool {
    let mut chars = value.chars();
    chars
        .next()
        .is_some_and(|character| character == '_' || character.is_alphabetic())
        && chars.all(|character| character == '_' || character.is_alphanumeric())
}
fn word_range_at(text: &str, offset: usize) -> TextRange {
    let offset = offset.min(text.len());
    let start = text[..offset]
        .rfind(|character: char| !(character.is_alphanumeric() || character == '_'))
        .map(|index| index + 1)
        .unwrap_or_default();
    let end = text[offset..]
        .find(|character: char| !(character.is_alphanumeric() || character == '_'))
        .map(|index| offset + index)
        .unwrap_or(text.len());
    TextRange::new(start, end)
}
fn identifier_range_in_span(text: &str, span: TextRange, identifier: &str) -> Option<TextRange> {
    let start = span.start_byte.min(text.len());
    let end = span.end_byte.min(text.len());
    let slice = text.get(start..end)?;
    identifier_ranges(slice)
        .find(|(_, word)| *word == identifier)
        .map(|(range, _)| TextRange::new(start + range.start_byte, start + range.end_byte))
}
fn identifier_ranges(text: &str) -> impl Iterator<Item = (TextRange, &str)> {
    let mut ranges = Vec::new();
    let mut start = None;
    for (offset, character) in text.char_indices() {
        let identifier = character == '_' || character.is_alphanumeric();
        match (start, identifier) {
            (None, true) => start = Some(offset),
            (Some(begin), false) => {
                ranges.push((TextRange::new(begin, offset), &text[begin..offset]));
                start = None;
            }
            _ => {}
        }
    }
    if let Some(begin) = start {
        ranges.push((TextRange::new(begin, text.len()), &text[begin..]));
    }
    ranges.into_iter()
}
fn format_document_text(text: &str, tab_size: usize, insert_spaces: bool) -> String {
    if text.is_empty() {
        return String::new();
    }
    let unit = if insert_spaces {
        " ".repeat(tab_size.max(1))
    } else {
        "\t".to_string()
    };
    let mut depth = 0usize;
    let mut output = String::new();
    for raw_line in text.lines() {
        let line = raw_line.trim();
        if line.is_empty() {
            if !output.ends_with("\n\n") {
                output.push('\n');
            }
            continue;
        }
        let leading_closes = line
            .chars()
            .take_while(|character| *character == '}')
            .count();
        depth = depth.saturating_sub(leading_closes);
        output.push_str(&unit.repeat(depth));
        output.push_str(line);
        output.push('\n');
        let opens = line.chars().filter(|character| *character == '{').count();
        let closes = line.chars().filter(|character| *character == '}').count();
        depth = depth
            .saturating_add(opens)
            .saturating_sub(closes.saturating_sub(leading_closes));
    }
    output
}
fn full_document_range(text: &str) -> Value {
    json!({"start":{"line":0,"character":0},"end":byte_position(text,text.len())})
}
fn position_to_byte(text: &str, position: &Value) -> Option<usize> {
    let line = position.get("line")?.as_u64()? as usize;
    let character = position.get("character")?.as_u64()? as usize;
    let start = text
        .split_inclusive('\n')
        .take(line)
        .map(str::len)
        .sum::<usize>();
    let line_text = text.split_inclusive('\n').nth(line)?;
    let mut utf16 = 0;
    for (byte, value) in line_text.char_indices() {
        if utf16 >= character {
            return Some(start + byte);
        }
        utf16 += value.len_utf16();
    }
    Some(start + line_text.trim_end_matches(['\r', '\n']).len())
}
fn byte_range(text: &str, range: TextRange) -> Value {
    json!({"start":byte_position(text,range.start_byte),"end":byte_position(text,range.end_byte)})
}
fn byte_position(text: &str, offset: usize) -> Value {
    let mut safe = offset.min(text.len());
    while !text.is_char_boundary(safe) {
        safe -= 1
    }
    let prefix = &text[..safe];
    let line = prefix.bytes().filter(|byte| *byte == b'\n').count();
    let start = prefix
        .rfind('\n')
        .map(|index| index + 1)
        .unwrap_or_default();
    json!({"line":line,"character":prefix[start..].encode_utf16().count()})
}
fn zero_range() -> Value {
    json!({"start":{"line":0,"character":0},"end":{"line":0,"character":0}})
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn framing_and_utf16_conversion_are_stable() {
        let value = json!({"jsonrpc":"2.0","id":1,"method":"initialize"});
        let mut bytes = Vec::new();
        write_message(&mut bytes, &value).unwrap();
        assert_eq!(
            read_message(&mut io::BufReader::new(bytes.as_slice())).unwrap(),
            Some(value)
        );
        let text = "a😀b\nnext";
        assert_eq!(
            position_to_byte(text, &json!({"line":0,"character":3})),
            Some(5)
        );
        assert_eq!(byte_position(text, 5), json!({"line":0,"character":3}));
    }
}
