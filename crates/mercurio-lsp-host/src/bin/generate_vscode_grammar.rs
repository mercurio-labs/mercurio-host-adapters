use std::env;
use std::fs;
use std::path::PathBuf;

use mercurio_lsp_host::generated_completion_keywords;
use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let output = env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("vscode-dev/grammars/mercurio.tmLanguage.json"));
    let keyword_pattern = generated_completion_keywords()
        .into_iter()
        .map(|keyword| regex_escape(&keyword.label))
        .collect::<Vec<_>>()
        .join("|");
    let grammar = json!({
        "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
        "name": "Mercurio Systems Modeling",
        "scopeName": "source.mercurio",
        "patterns": [
            {"include":"#comments"},
            {"include":"#strings"},
            {"include":"#numbers"},
            {"name":"keyword.control.mercurio","match":format!(r"\b(?:{keyword_pattern})\b")},
            {"name":"entity.name.type.mercurio","match":r"\b[A-Z][A-Za-z0-9_]*\b"}
        ],
        "repository": {
            "comments":{"patterns":[
                {"name":"comment.line.double-slash.mercurio","match":r"//.*$"},
                {"name":"comment.block.mercurio","begin":r"/\*","end":r"\*/"}
            ]},
            "strings":{"patterns":[
                {"name":"string.quoted.double.mercurio","begin":"\"","end":"\"","patterns":[
                    {"name":"constant.character.escape.mercurio","match":r"\\."}
                ]}
            ]},
            "numbers":{"patterns":[
                {"name":"constant.numeric.mercurio","match":r"\b\d+(?:\.\d+)?\b"}
            ]}
        }
    });
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        output,
        format!("{}\n", serde_json::to_string_pretty(&grammar)?),
    )?;
    Ok(())
}

fn regex_escape(value: &str) -> String {
    let mut escaped = String::new();
    for character in value.chars() {
        if matches!(
            character,
            '.' | '+' | '*' | '?' | '^' | '$' | '(' | ')' | '[' | ']' | '{' | '}' | '|' | '\\'
        ) {
            escaped.push('\\');
        }
        escaped.push(character);
    }
    escaped
}
