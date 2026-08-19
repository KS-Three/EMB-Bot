// predev step 2 (after copy-engine): make sure the localhost digitizer
// service is up before Studio starts, so the artwork lane decision
// (project.js resolveArtworkType) has a healthy service to route to and a
// beginner's first "Logo patch" upload lands in the pipeline, not the
// browser fallback. NEVER blocks dev: if the venv is missing or the service
// won't come up, we warn and exit 0 — Studio's own offline handling (the
// ContentStep offline note) is the honest fallback, same as before this
// script existed.
//
// Spawn contract mirrors .claude/launch.json's "digitizer" entry: the venv
// interpreter, -m digitizer_service, port 8721, cwd digitizer/.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const PORT = 8721;
const HEALTH_URL = `http://127.0.0.1:${PORT}/health`;

// Probe /health until it answers ok, up to `attempts` probes with a sleep
// between failures. Injected fetch/sleep so the spec can drive it without
// network or timers. Any failure mode (refused, non-ok, bad JSON) is just
// "not yet"; the only outcomes are true (healthy) and false (budget spent).
export async function waitHealthy({ fetchFn = globalThis.fetch, sleepFn = (ms) => new Promise((r) => setTimeout(r, ms)), attempts = 30, intervalMs = 500 } = {}) {
  for (let i = 0; i < attempts; i++) {
    try {
      const r = await fetchFn(HEALTH_URL);
      if (r.ok) {
        await r.json(); // parses = the service, not something else on the port
        return true;
      }
    } catch (e) {
      // not up yet -- fall through to the sleep
    }
    if (i < attempts - 1) await sleepFn(intervalMs);
  }
  return false;
}

async function main() {
  // One quick probe: already running (Kent started it by hand, or a
  // previous dev run left it up) means nothing to do.
  if (await waitHealthy({ attempts: 1 })) {
    console.log(`digitizer service already up on :${PORT}`);
    return;
  }

  const appDir = dirname(dirname(fileURLToPath(import.meta.url)));
  const digitizerDir = join(dirname(appDir), "digitizer");
  const python = join(digitizerDir, ".venv", "Scripts", "python.exe");

  if (!existsSync(python)) {
    console.warn(`digitizer venv not found (${python}) — Studio will run with artwork on the browser-lane fallback`);
    return;
  }

  console.log("starting digitizer service…");
  const child = spawn(python, ["-m", "digitizer_service", "--port", String(PORT)], {
    cwd: digitizerDir,
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  });
  child.unref(); // outlive this script; vite's exit must not kill the service

  if (await waitHealthy()) {
    console.log(`digitizer service up on :${PORT}`);
  } else {
    console.warn("digitizer service did not become healthy in time — Studio will run with artwork on the browser-lane fallback");
  }
}

// Import-safe for the spec: only run when executed as a script.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
