const vscode = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const command = vscode.workspace.getConfiguration("mercurio.lsp").get("serverPath");
  const serverOptions = { command, transport: TransportKind.stdio };
  const clientOptions = {
    documentSelector: [
      { scheme: "file", language: "sysml" },
      { scheme: "file", language: "kerml" }
    ],
    synchronize: { fileEvents: vscode.workspace.createFileSystemWatcher("**/*.{sysml,kerml}") }
  };
  client = new LanguageClient("mercurio", "Mercurio Language Workbench", serverOptions, clientOptions);
  context.subscriptions.push(client.start());
}

async function deactivate() {
  if (client) await client.stop();
}

module.exports = { activate, deactivate };
