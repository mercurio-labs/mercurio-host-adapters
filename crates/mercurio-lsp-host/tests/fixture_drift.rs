use std::fs;
use std::process::Command;

use serde_json::Value;

#[test]
fn compiler_oracle_fixture_is_regenerable_and_contains_cross_file_parity() {
    let path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/language-workbench/expectations.json");
    let before = fs::read_to_string(&path).unwrap();
    let status = Command::new(env!("CARGO_BIN_EXE_generate_language_workbench_fixtures"))
        .status()
        .unwrap();
    assert!(status.success());
    let after = fs::read_to_string(&path).unwrap();
    fs::write(&path, &before).unwrap();
    assert_eq!(after.replace("\r\n", "\n"), before.replace("\r\n", "\n"));

    let expected: Value = serde_json::from_str(&before).unwrap();
    let documents = expected["documents"].as_array().unwrap();
    assert!(
        documents
            .iter()
            .flat_map(|document| document["symbols"].as_array().unwrap())
            .any(|symbol| symbol["qualified_name"] == "Demo.Vehicle")
    );
    assert!(
        documents
            .iter()
            .flat_map(|document| document["references"].as_array().unwrap())
            .any(|reference| {
                reference["source_name"] == "use.sysml"
                    && reference["target_element_id"] == "type.Demo.Vehicle"
                    && reference["target_source_name"] == "types.sysml"
            })
    );
}
