use std::collections::BTreeSet;

use mercurio_kerml::KermlLanguageModule;
use mercurio_language_contracts::LanguageRegistry;
use mercurio_lsp::{CompletionKeyword, LanguageServer};
use mercurio_sysml::{
    SysmlEnvironmentError, SysmlLanguageModule, load_sysml_baseline, sysml_definition_keywords,
    sysml_relationship_keywords, sysml_usage_keywords,
};

pub fn create_language_server() -> Result<LanguageServer, SysmlEnvironmentError> {
    let mut registry = LanguageRegistry::new();
    registry.register(KermlLanguageModule);
    registry.register(SysmlLanguageModule);
    let library = load_sysml_baseline()?;
    Ok(LanguageServer::with_completion_keywords(
        registry,
        library,
        generated_completion_keywords(),
    ))
}

pub fn generated_completion_keywords() -> Vec<CompletionKeyword> {
    let mut keywords = BTreeSet::new();
    keywords.extend(sysml_definition_keywords().iter().copied());
    keywords.extend(sysml_usage_keywords().iter().copied());
    keywords.extend(sysml_relationship_keywords().iter().copied());
    keywords
        .into_iter()
        .map(|keyword| CompletionKeyword {
            label: keyword.to_string(),
            detail: "Generated SysML action-space keyword".to_string(),
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn completion_keywords_are_generated_and_exclude_legacy_block() {
        let keywords = generated_completion_keywords();
        assert!(keywords.iter().any(|keyword| keyword.label == "part"));
        assert!(keywords.iter().any(|keyword| keyword.label == "satisfy"));
        assert!(!keywords.iter().any(|keyword| keyword.label == "block"));
    }
}
