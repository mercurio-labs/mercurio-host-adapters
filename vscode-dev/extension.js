const fs = require("fs");
const path = require("path");
const childProcess = require("child_process");
const vscode = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function serverCandidates(context) {
  const configured = vscode.workspace.getConfiguration("mercurio.lsp").get("serverPath");
  const executable = process.platform === "win32" ? "mercurio-lsp-host.exe" : "mercurio-lsp-host";
  return [
    configured,
    process.env.MERCURIO_LSP_PATH,
    path.join(context.extensionPath, "server", executable),
    process.platform === "win32"
      ? path.join(process.env.LOCALAPPDATA || "", "Mercurio", executable)
      : "/usr/local/bin/mercurio-lsp-host",
    process.platform === "win32"
      ? path.join(process.env.LOCALAPPDATA || "", "Programs", "Mercurio", executable)
      : "/opt/Mercurio/mercurio-lsp-host",
    process.platform === "win32"
      ? path.join(process.env.ProgramFiles || "", "Mercurio", executable)
      : "/Applications/Mercurio.app/Contents/MacOS/mercurio-lsp-host",
    "mercurio-lsp-host",
  ].filter(Boolean);
}

function discoverServer(context) {
  for (const candidate of serverCandidates(context)) {
    if (candidate.includes(path.sep) && !fs.existsSync(candidate)) continue;
    const probe = childProcess.spawnSync(candidate, ["--version"], {
      encoding: "utf8",
      windowsHide: true,
      shell: false,
    });
    if (!probe.error && probe.status === 0) {
      return { command: candidate, version: probe.stdout.trim() };
    }
  }
  throw new Error(
    "Mercurio language server was not found. Install Mercurio or set mercurio.lsp.serverPath."
  );
}

async function activate(context) {
  let discovered;
  try {
    discovered = discoverServer(context);
  } catch (error) {
    void vscode.window.showErrorMessage(String(error.message || error));
    return;
  }
  const expected = context.extension.packageJSON.version;
  if (discovered.version !== expected) {
    void vscode.window.showErrorMessage(
      "Mercurio language server version " + discovered.version +
      " does not match extension " + expected + "."
    );
    return;
  }
  const provider = vscode.workspace.registerTextDocumentContentProvider(
    "mercurio-stdlib",
    {
      async provideTextDocumentContent(uri) {
        const result = await client.sendRequest("mercurio/virtualDocument", {
          uri: uri.toString(),
        });
        return result?.text || "";
      },
    }
  );
  context.subscriptions.push(provider);

  const serverOptions = { command: discovered.command, transport: TransportKind.stdio };
  const clientOptions = {
    documentSelector: [
      { scheme: "file", language: "sysml" },
      { scheme: "file", language: "kerml" },
    ],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher("**/*.{sysml,kerml}"),
    },
  };
  client = new LanguageClient(
    "mercurio",
    "Mercurio Language Workbench",
    serverOptions,
    clientOptions
  );
  await client.start();
}

async function deactivate() {
  if (client) await client.stop();
}

module.exports = { activate, deactivate, discoverServer };