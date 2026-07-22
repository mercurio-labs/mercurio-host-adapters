const childProcess = require("child_process");
const path = require("path");

const extensionRoot = path.resolve(__dirname, "..");
const packageJson = require(path.join(extensionRoot, "package.json"));
const targets = {
  "win32-x64": "win32-x64",
  "win32-arm64": "win32-arm64",
  "darwin-x64": "darwin-x64",
  "darwin-arm64": "darwin-arm64",
  "linux-x64": "linux-x64",
  "linux-arm64": "linux-arm64",
  "linux-arm": "linux-armhf",
};
const target = targets[`${process.platform}-${process.arch}`];
if (!target) throw new Error(`Unsupported VS Code target: ${process.platform}-${process.arch}`);

const output = path.join(
  extensionRoot,
  `${packageJson.name}-${packageJson.version}-${target}.vsix`
);
const npmCli = process.env.npm_execpath;
if (!npmCli) throw new Error("npm_execpath is unavailable; run this script through npm run package.");

const result = childProcess.spawnSync(
  process.execPath,
  [npmCli, "exec", "--", "vsce", "package", "--no-dependencies", "--target", target, "--out", output],
  { cwd: extensionRoot, encoding: "utf8", stdio: "inherit", windowsHide: true }
);
if (result.error || result.status !== 0) {
  throw new Error(`VSIX packaging failed: ${result.error || `exit code ${result.status}`}`);
}

console.log(`Created ${output}`);
