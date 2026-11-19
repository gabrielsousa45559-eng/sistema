const { spawn, spawnSync } = require("node:child_process");
const path = require("node:path");

const root = __dirname;
const windows = process.platform === "win32";
const candidates = windows
  ? [["py", ["-3", "--version"]], ["python", ["--version"]]]
  : [["python3", ["--version"]], ["python", ["--version"]]];

let python;
for (const [command, args] of candidates) {
  const check = spawnSync(command, args, { cwd: root, stdio: "ignore" });
  if (!check.error && check.status === 0) {
    python = command;
    break;
  }
}

if (!python) {
  console.error("NexoFlow precisa do Python 3 instalado no servidor para iniciar server.py.");
  process.exit(1);
}

const pythonArgs = windows && python === "py" ? ["-3", "server.py"] : ["server.py"];
const child = spawn(python, pythonArgs, {
  cwd: root,
  stdio: "inherit",
  env: {
    ...process.env,
    HOST: process.env.HOST || "0.0.0.0",
    PORT: process.env.PORT || "8765",
  },
});

child.on("error", (error) => {
  console.error(`Não foi possível iniciar o backend Python: ${error.message}`);
  process.exitCode = 1;
});

child.on("exit", (code, signal) => {
  if (signal) {
    console.error(`Backend Python finalizado pelo sinal ${signal}.`);
    process.exitCode = 1;
  } else {
    process.exitCode = code ?? 1;
  }
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}
