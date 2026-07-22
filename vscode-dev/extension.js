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

class ContainmentTreeProvider {
  constructor(languageClient) {
    this.languageClient = languageClient;
    this.changeEmitter = new vscode.EventEmitter();
    this.onDidChangeTreeData = this.changeEmitter.event;
    this.snapshot = null;
  }

  refresh() {
    this.snapshot = null;
    this.changeEmitter.fire(undefined);
  }

  getTreeItem(element) {
    const collapsibleState = element.children?.length
      ? vscode.TreeItemCollapsibleState.Collapsed
      : vscode.TreeItemCollapsibleState.None;
    const item = new vscode.TreeItem(element.label, collapsibleState);
    item.id = element.id;
    item.description = element.description;
    item.tooltip = element.tooltip || element.label;
    item.iconPath = new vscode.ThemeIcon(element.icon || "symbol-object");
    item.contextValue = element.contextValue;
    if (element.uri && element.range) {
      item.command = {
        command: "mercurio.openContainmentElement",
        title: "Open Model Element",
        arguments: [element.uri, element.range],
      };
    }
    return item;
  }

  async getChildren(element) {
    if (element) return element.children || [];
    if (!this.snapshot) {
      try {
        const result = await this.languageClient.sendRequest("mercurio/projectContainment", {});
        this.snapshot = containmentRoots(result || {});
      } catch (error) {
        this.snapshot = [{
          id: "mercurio:containment:error",
          label: String(error.message || error),
          icon: "error",
          children: [],
        }];
      }
    }
    return this.snapshot;
  }
}

function containmentRoots(result) {
  const roots = (result.projects || []).map((project) => ({
    id: `project:${project.id}`,
    label: project.name || "Mercurio Project",
    description: project.mode === "descriptor" ? undefined : `(${project.mode} workspace)`,
    tooltip: project.descriptorUri || project.id,
    icon: "symbol-namespace",
    contextValue: "mercurioProject",
    children: (project.files || []).map(containmentFile),
  }));
  for (const [index, message] of (result.errors || []).entries()) {
    roots.push({
      id: `project-error:${index}`,
      label: message,
      tooltip: message,
      icon: "error",
      contextValue: "mercurioProjectError",
      children: [],
    });
  }
  return roots;
}

function containmentFile(file) {
  const label = file.path?.replace(/\\/g, "/").split("/").pop() || file.uri;
  return {
    id: `file:${file.uri}`,
    label,
    description: file.path,
    tooltip: file.path,
    icon: "file-code",
    contextValue: "mercurioSourceFile",
    children: (file.children || []).map((node) => containmentElement(file.uri, node)),
  };
}

function containmentElement(uri, node) {
  const range = {
    start: {
      line: Math.max(0, (node.start_line_number || 1) - 1),
      character: Math.max(0, (node.start_column || 1) - 1),
    },
    end: {
      line: Math.max(0, (node.end_line_number || 1) - 1),
      character: Math.max(0, (node.end_column || 1) - 1),
    },
  };
  return {
    id: `element:${uri}:${node.id}`,
    label: node.label || node.id,
    description: node.kind,
    tooltip: `${node.label || node.id} (${node.kind || "Element"})`,
    icon: semanticIcon(node.kind),
    contextValue: "mercurioModelElement",
    uri,
    range,
    children: (node.children || []).map((child) => containmentElement(uri, child)),
  };
}

function semanticIcon(kind = "") {
  const normalized = kind.toLowerCase();
  if (normalized.includes("package") || normalized.includes("namespace")) return "symbol-namespace";
  if (normalized.includes("definition")) return "symbol-class";
  if (normalized.includes("requirement")) return "checklist";
  if (normalized.includes("relationship") || normalized.includes("membership")) return "references";
  return "symbol-field";
}

async function openContainmentElement(uri, range) {
  const document = await vscode.workspace.openTextDocument(vscode.Uri.parse(uri));
  const editor = await vscode.window.showTextDocument(document);
  const start = new vscode.Position(range.start.line, range.start.character);
  const end = new vscode.Position(range.end.line, range.end.character);
  editor.selection = new vscode.Selection(start, start);
  editor.revealRange(new vscode.Range(start, end), vscode.TextEditorRevealType.InCenterIfOutsideViewport);
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
      fileEvents: [
        vscode.workspace.createFileSystemWatcher("**/*.{sysml,kerml}"),
        vscode.workspace.createFileSystemWatcher("**/.project.json"),
      ],
    },
  };
  client = new LanguageClient(
    "mercurio",
    "Mercurio Language Workbench",
    serverOptions,
    clientOptions
  );
  await client.start();
  const containmentProvider = new ContainmentTreeProvider(client);
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("mercurio.containment", containmentProvider),
    vscode.commands.registerCommand("mercurio.refreshContainment", () => containmentProvider.refresh()),
    vscode.commands.registerCommand("mercurio.openContainmentElement", openContainmentElement),
    client.onNotification("mercurio/projectContainmentChanged", () => containmentProvider.refresh()),
  );
}

async function deactivate() {
  if (client) await client.stop();
}

module.exports = {
  activate,
  deactivate,
  discoverServer,
  ContainmentTreeProvider,
  containmentRoots,
  containmentFile,
  containmentElement,
};
