const childProcess = require("child_process");
const fs = require("fs");
const path = require("path");

const extensionRoot = path.resolve(__dirname, "..");
const packageJson = require(path.join(extensionRoot, "package.json"));
const executable = process.platform === "win32" ? "mercurio-lsp-host.exe" : "mercurio-lsp-host";
const defaultSource = path.resolve(extensionRoot, "..", "target", "release", executable);
const source = path.resolve(process.env.MERCURIO_LSP_BINARY || defaultSource);
const destinationDirectory = path.join(extensionRoot, "server");
const destination = path.join(destinationDirectory, executable);

if (!fs.existsSync(source)) {
  throw new Error(
    `Mercurio LSP host not found at ${source}. ` +
      "Build it with cargo build --release -p mercurio-lsp-host or set MERCURIO_LSP_BINARY."
  );
}

const probe = childProcess.spawnSync(source, ["--version"], {
  encoding: "utf8",
  windowsHide: true,
  shell: false,
});
if (probe.error || probe.status !== 0) {
  throw new Error(`Could not execute ${source} --version: ${probe.error || probe.stderr}`);
}

const serverVersion = probe.stdout.trim();
if (serverVersion !== packageJson.version) {
  throw new Error(
    `Mercurio LSP host version ${serverVersion} does not match extension ${packageJson.version}.`
  );
}

fs.mkdirSync(destinationDirectory, { recursive: true });
fs.copyFileSync(source, destination);
if (process.platform !== "win32") fs.chmodSync(destination, 0o755);

console.log(`Staged ${source} as ${destination}`);
