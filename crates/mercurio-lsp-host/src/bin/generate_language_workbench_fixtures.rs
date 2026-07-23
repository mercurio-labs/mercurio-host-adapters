use std::fs;
use std::path::PathBuf;

use mercurio_language_contracts::{LanguageService, SourceDocument};
use mercurio_sysml::{SysmlLanguageModule, load_sysml_baseline};
use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/language-workbench");
    let paths = [root.join("types.sysml"), root.join("use.sysml")];
    let documents = paths
        .iter()
        .map(|path| {
            let source = fs::read_to_string(path)?
                .replace("\r\n", "\n")
                .replace('\r', "\n");
            Ok(SourceDocument::new(
                path.file_name()
                    .and_then(|name| name.to_str())
                    .unwrap_or_default(),
                1,
                source,
            ))
        })
        .collect::<Result<Vec<_>, std::io::Error>>()?;
    let library = load_sysml_baseline()?;
    let service = SysmlLanguageModule;
    let mut expected = Vec::new();
    for document in &documents {
        let analysis = service
            .analyze_workspace(&documents, &document.source_name, &library)
            .ok_or("fixture language was not recognized")?;
        expected.push(json!({
            "sourceName": document.source_name,
            "revision": document.revision,
            "symbols": analysis.symbols.symbols,
            "references": analysis.references,
            "diagnostics": analysis.diagnostics,
        }));
    }
    fs::write(
        root.join("expectations.json"),
        serde_json::to_string_pretty(&json!({
            "schemaVersion": 1,
            "documents": expected
        }))? + "\n",
    )?;
    Ok(())
}
