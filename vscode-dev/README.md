# Mercurio Language Workbench for VS Code

The extension discovers an installed Mercurio language server, verifies that
its version matches the extension, and provides SysML v2 and KerML diagnostics,
completion, navigation, rename, code actions, semantic tokens, and formatting.

Set mercurio.lsp.serverPath only when the server is not installed with
Mercurio and is not on PATH. Standard-library definitions are exposed through
a read-only virtual document provider.

Run npm run generate:grammar to regenerate the TextMate grammar from the
action-space keyword registry. Build the native server with
`cargo build --release -p mercurio-lsp-host`, then run `npm run package` to
create a platform-specific VSIX containing the server and bundled extension
dependencies. Set `MERCURIO_LSP_BINARY` when packaging a server from a
non-default location.
