use mercurio_lsp::serve_stdio;
use mercurio_lsp_host::create_language_server;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    match std::env::args().nth(1).as_deref() {
        Some("--version") => {
            println!("{}", env!("CARGO_PKG_VERSION"));
            return Ok(());
        }
        Some("--metadata") => {
            println!(
                "{}",
                serde_json::to_string(&create_language_server()?.metadata())?
            );
            return Ok(());
        }
        _ => {}
    }
    serve_stdio(create_language_server()?)?;
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
        let mut server = create_language_server().unwrap();

        let metadata = server.handle(json!({
            "jsonrpc":"2.0","id":0,"method":"mercurio/serverMetadata","params":{}
        }));
        assert_eq!(
            metadata[0]
                .pointer("/result/protocolVersion")
                .and_then(Value::as_str),
            Some("1.0")
        );
        assert_eq!(
            metadata[0]
                .pointer("/result/projectDescriptorSchema/max")
                .and_then(Value::as_u64),
            Some(2)
        );

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

        let active_element = server.handle(json!({
            "jsonrpc":"2.0","id":12,"method":"mercurio/elementAtPosition",
            "params":{"textDocument":{"uri":first},"position":{"line":0,"character":30}}
        }));
        assert_eq!(
            active_element[0]
                .pointer("/result/uri")
                .and_then(Value::as_str),
            Some(first)
        );
        assert!(
            active_element[0]
                .pointer("/result/elementId")
                .and_then(Value::as_str)
                .is_some_and(|element_id| !element_id.is_empty())
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

        let symbol_completion = server.handle(json!({
            "jsonrpc":"2.0","id":5,"method":"textDocument/completion",
            "params":{"textDocument":{"uri":second},"position":{"line":0,"character":41}}
        }));
        assert!(
            symbol_completion[0]["result"]
                .as_array()
                .is_some_and(|items| { items.iter().any(|item| item["label"] == "Vehicle") })
        );
        let keyword_completion = server.handle(json!({
            "jsonrpc":"2.0","id":6,"method":"textDocument/completion",
            "params":{"textDocument":{"uri":second},"position":{"line":0,"character":13}}
        }));
        assert!(
            keyword_completion[0]["result"]
                .as_array()
                .is_some_and(|items| {
                    items.iter().any(|item| item["label"] == "part")
                        && !items.iter().any(|item| item["label"] == "block")
                })
        );
        let prepared = server.handle(json!({
            "jsonrpc":"2.0","id":7,"method":"textDocument/prepareRename",
            "params":{"textDocument":{"uri":second},"position":{"line":0,"character":41}}
        }));
        assert_eq!(
            prepared[0]
                .pointer("/result/placeholder")
                .and_then(Value::as_str),
            Some("Vehicle")
        );

        let rename = server.handle(json!({
            "jsonrpc":"2.0","id":8,"method":"textDocument/rename",
            "params":{"textDocument":{"uri":second},"position":{"line":0,"character":41},"newName":"Conveyance"}
        }));
        assert!(
            rename[0]
                .pointer("/result/changes")
                .and_then(Value::as_object)
                .is_some_and(|changes| changes.contains_key(first) && changes.contains_key(second))
        );

        let semantic_tokens = server.handle(json!({
            "jsonrpc":"2.0","id":9,"method":"textDocument/semanticTokens/full",
            "params":{"textDocument":{"uri":second}}
        }));
        assert!(
            semantic_tokens[0]
                .pointer("/result/data")
                .and_then(Value::as_array)
                .is_some_and(|data| !data.is_empty())
        );

        let formatting = server.handle(json!({
            "jsonrpc":"2.0","id":10,"method":"textDocument/formatting",
            "params":{"textDocument":{"uri":second},"options":{"tabSize":2,"insertSpaces":true}}
        }));
        assert!(
            formatting[0]["result"]
                .as_array()
                .is_some_and(|edits| !edits.is_empty())
        );

        let code_actions = server.handle(json!({
            "jsonrpc":"2.0","id":11,"method":"textDocument/codeAction",
            "params":{"textDocument":{"uri":second},"range":{
                "start":{"line":0,"character":0},"end":{"line":0,"character":48}
            },"context":{"diagnostics":[]}}
        }));
        assert!(
            code_actions[0]["result"]
                .as_array()
                .is_some_and(|actions| !actions.is_empty())
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
