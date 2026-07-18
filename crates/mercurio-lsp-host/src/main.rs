use mercurio_kerml::KermlLanguageModule;
use mercurio_language_contracts::LanguageRegistry;
use mercurio_lsp::{LanguageServer, serve_stdio};
use mercurio_sysml::{SysmlLanguageModule, load_sysml_baseline};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut registry = LanguageRegistry::new();
    registry.register(KermlLanguageModule);
    registry.register(SysmlLanguageModule);
    let library = load_sysml_baseline()?;
    serve_stdio(LanguageServer::new(registry, library))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use mercurio_semantic_services::{
        ModelChangeEvent, ModelChangeProvenance, SemanticDiff, WorkspaceRevision,
    };
    use serde_json::{Value, json};

    #[test]
    fn lsp_harness_covers_incremental_sync_outline_and_navigation() {
        let mut registry = LanguageRegistry::new();
        registry.register(KermlLanguageModule);
        registry.register(SysmlLanguageModule);
        let library = load_sysml_baseline().unwrap();
        let mut server = LanguageServer::new(registry, library);

        let first = "file:///workspace/types.sysml";
        let second = "file:///workspace/use.sysml";
        server.handle(json!({
            "jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{
                "uri":first,"languageId":"sysml","version":1,
                "text":"package Demo { part def Vehicle; }"
            }}
        }));
        let diagnostics = server.handle(json!({
            "jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{
                "uri":second,"languageId":"sysml","version":1,
                "text":"package Use { import Demo::*; part car : Vehicle; }"
            }}
        }));
        assert!(diagnostics.iter().any(|message| {
            message.pointer("/params/uri").and_then(Value::as_str) == Some(second)
        }));

        let outline = server.handle(json!({
            "jsonrpc":"2.0","id":1,"method":"textDocument/documentSymbol",
            "params":{"textDocument":{"uri":first}}
        }));
        assert!(
            outline[0]["result"]
                .as_array()
                .is_some_and(|items| !items.is_empty())
        );

        let definition = server.handle(json!({
            "jsonrpc":"2.0","id":2,"method":"textDocument/definition",
            "params":{"textDocument":{"uri":second},"position":{"line":0,"character":41}}
        }));
        assert_eq!(
            definition[0].pointer("/result/uri").and_then(Value::as_str),
            Some(first)
        );

        let references = server.handle(json!({
            "jsonrpc":"2.0","id":3,"method":"textDocument/references",
            "params":{"textDocument":{"uri":first},"position":{"line":0,"character":25},"context":{"includeDeclaration":true}}
        }));
        assert!(
            references[0]["result"]
                .as_array()
                .is_some_and(|items| { items.iter().any(|location| location["uri"] == second) })
        );

        let hover = server.handle(json!({
            "jsonrpc":"2.0","id":4,"method":"textDocument/hover",
            "params":{"textDocument":{"uri":second},"position":{"line":0,"character":41}}
        }));
        assert!(
            hover[0]
                .pointer("/result/contents/value")
                .and_then(Value::as_str)
                .is_some_and(|value| value.contains("Effective values"))
        );

        let refreshed = server.handle(json!({
            "jsonrpc":"2.0","method":"textDocument/didChange","params":{
                "textDocument":{"uri":second,"version":2},
                "contentChanges":[{"range":{
                    "start":{"line":0,"character":41},"end":{"line":0,"character":48}
                },"text":"Missing"}]
            }
        }));
        let second_diagnostics = refreshed
            .iter()
            .find(|message| message.pointer("/params/uri").and_then(Value::as_str) == Some(second))
            .unwrap();
        assert!(
            second_diagnostics
                .pointer("/params/diagnostics")
                .and_then(Value::as_array)
                .is_some_and(|items| !items.is_empty())
        );

        let event = ModelChangeEvent::new(
            WorkspaceRevision {
                fingerprint: "before".to_string(),
            },
            WorkspaceRevision {
                fingerprint: "after".to_string(),
            },
            ModelChangeProvenance {
                mutation_id: "fixture-mutation".to_string(),
                actor: None,
            },
            SemanticDiff::default(),
        );
        let model_refresh = server.model_changed(&event);
        assert!(model_refresh.iter().any(|message| {
            message.pointer("/params/uri").and_then(Value::as_str) == Some(second)
                && message
                    .pointer("/params/diagnostics")
                    .and_then(Value::as_array)
                    .is_some_and(|items| !items.is_empty())
        }));
    }
}
