# Mercurio language workbench VS Code dev harness

This unpublished extension is a smoke client for the standard-IO LSP host.

1. Build `mercurio-lsp-host` from the host-adapters workspace.
2. Run `npm install` in this directory.
3. Open this directory in VS Code and press F5.
4. Set `mercurio.lsp.serverPath` when the binary is not on PATH.
5. Open a SysML or KerML fixture and verify diagnostics, outline, definition,
   references, and hover.

Packaging, syntax grammar generation, discovery, and marketplace publication
belong to gated LW-9 and are intentionally absent.
