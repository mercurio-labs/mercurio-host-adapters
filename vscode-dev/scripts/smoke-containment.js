const assert = require("assert");
const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { pathToFileURL } = require("url");

const extensionRoot = path.resolve(__dirname, "..");
const executable = process.platform === "win32" ? "mercurio-lsp-host.exe" : "mercurio-lsp-host";
const server = path.resolve(
  process.env.MERCURIO_LSP_BINARY || path.join(extensionRoot, "..", "target", "debug", executable)
);

function frame(message) {
  const body = JSON.stringify(message);
  return `Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`;
}

function client(processHandle) {
  let buffer = Buffer.alloc(0);
  const pending = new Map();
  processHandle.stdout.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    while (true) {
      const separator = buffer.indexOf("\r\n\r\n");
      if (separator < 0) return;
      const header = buffer.subarray(0, separator).toString("utf8");
      const match = /Content-Length:\s*(\d+)/i.exec(header);
      if (!match) throw new Error(`Missing Content-Length in ${header}`);
      const length = Number(match[1]);
      const bodyStart = separator + 4;
      if (buffer.length < bodyStart + length) return;
      const message = JSON.parse(buffer.subarray(bodyStart, bodyStart + length).toString("utf8"));
      buffer = buffer.subarray(bodyStart + length);
      const waiter = pending.get(message.id);
      if (waiter) {
        pending.delete(message.id);
        waiter.resolve(message);
      }
    }
  });
  return {
    request(id, method, params) {
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          pending.delete(id);
          reject(new Error(`Timed out waiting for ${method}`));
        }, 15000);
        pending.set(id, {
          resolve(message) {
            clearTimeout(timeout);
            resolve(message);
          },
        });
        processHandle.stdin.write(frame({ jsonrpc: "2.0", id, method, params }));
      });
    },
  };
}

async function main() {
  assert.ok(fs.existsSync(server), `LSP host is missing: ${server}`);
  const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), "mercurio-lsp-containment-"));
  const processHandle = childProcess.spawn(server, [], {
    stdio: ["pipe", "pipe", "inherit"],
    windowsHide: true,
  });
  try {
    fs.writeFileSync(
      path.join(projectRoot, ".project.json"),
      JSON.stringify({ version: 2, name: "Containment Smoke", model: { entrypoints: ["main.sysml"] } })
    );
    fs.writeFileSync(path.join(projectRoot, "main.sysml"), "package Demo {\n  part def Vehicle;\n}\n");
    const rpc = client(processHandle);
    const rootUri = pathToFileURL(projectRoot).toString();
    const initialized = await rpc.request(1, "initialize", {
      processId: process.pid,
      workspaceFolders: [{ uri: rootUri, name: "Containment Smoke" }],
    });
    assert.ok(initialized.result?.capabilities, JSON.stringify(initialized));
    const response = await rpc.request(2, "mercurio/projectContainment", {});
    assert.ifError(response.error);
    assert.equal(response.result.projects.length, 1);
    assert.equal(response.result.projects[0].mode, "descriptor");
    assert.equal(response.result.projects[0].files.length, 1);
    assert.equal(response.result.projects[0].files[0].path, "main.sysml");
    assert.equal(response.result.projects[0].files[0].children[0].label, "Demo");
    await rpc.request(3, "shutdown", null);
    processHandle.stdin.end();
    console.log("Containment smoke test passed.");
  } finally {
    if (!processHandle.killed) processHandle.kill();
    fs.rmSync(projectRoot, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
