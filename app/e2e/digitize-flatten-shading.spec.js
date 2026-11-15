// "Flatten shading" (PipelineConfig.bevel_ring_fold) through the real Studio
// and the real digitizer service. Kent 2026-11-14 on PR #1486: "Studio
// tickbox, OFF" -- the engine default stays OFF, the customer can tick it.
//
//   upload Golden Tee (a shaded 3D logo: gold ramp, dark bevel, keyline, drop
//   shadow) -> digitize unticked -> tick "Flatten shading" -> the design goes
//   stale -> re-digitize -> the generation changes (the fold flattens the
//   shading: fewer threads and stitches) -> resize -> the tick is still on and
//   the next run's request still carries it (that third POST is refused once
//   captured: the request is the question, and a third Golden Tee run would
//   cost minutes for nothing more).
//
// The request is read off the wire: unticked sends NO `bevel_ring_fold` key
// (absent is the service's own False), ticked sends `true`. The result says
// nothing extra about it (Kent's no-warnings ruling, 2026-10-02): no new
// customer-facing line mentions shading.
//
// The art is the git-tracked digitizer/testdata/photo/logo_golden_tee.jpg the
// Python suites read, not a copy (same convention as
// digitize-background-enclosed.spec.js). Service bootstrap as there: reuse a
// healthy service, else start the venv's. `E2E_SERVICE_URL` points the spec
// (and the Studio, through its `embstudio:digitizerUrl` seam) at a second
// instance on another port; unset, it is the default 8721.
import { test, expect } from "@playwright/test";
import { openAdvanced, runDigitize, setDesignWidth, uploadArtwork } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = process.env.E2E_SERVICE_URL || "http://127.0.0.1:8721";
const DEFAULT_SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART = path.join(__dirname, "../../digitizer/testdata/photo/logo_golden_tee.jpg");

async function healthy() {
  try {
    const r = await fetch(SERVICE_URL + "/health");
    if (!r.ok) return false;
    const h = await r.json();
    return !!h && h.status === "ok";
  } catch (e) {
    return false;
  }
}

// The venv is gitignored and lives with a real checkout; a linked worktree
// also looks in the main checkout (digitize-background-enclosed.spec.js).
function venvPythonCandidates() {
  const roots = [path.resolve(__dirname, "../..")];
  try {
    const m = readFileSync(path.join(roots[0], ".git"), "utf8").match(/^gitdir:\s*(.+)$/m);
    if (m) {
      const mainRoot = path.resolve(m[1].trim(), "../../..");
      if (mainRoot !== roots[0]) roots.push(mainRoot);
    }
  } catch (e) {
    // .git is a directory: a normal checkout
  }
  const out = [];
  for (const root of roots) {
    out.push(path.join(root, "digitizer", ".venv", "bin", "python"));
    out.push(path.join(root, "digitizer", ".venv", "Scripts", "python.exe"));
  }
  return out.filter(existsSync);
}

let serviceProc = null;
let serviceUp = false;
let skipReason = "";

test.beforeAll(async () => {
  if (await healthy()) {
    serviceUp = true; // a developer's own instance -- reuse, never kill
    return;
  }
  const [python] = venvPythonCandidates();
  if (!python) {
    skipReason = "digitizer service is not running and no venv python was found.";
    return;
  }
  const port = new URL(SERVICE_URL).port || "8721";
  serviceProc = spawn(python, ["-m", "digitizer_service", "--port", port], {
    cwd: path.resolve(__dirname, "../../digitizer"),
    stdio: "ignore",
  });
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (await healthy()) {
      serviceUp = true;
      return;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  skipReason = "digitizer service failed to answer /health within 30s of being started (" + python + ").";
});

test.afterAll(() => {
  if (serviceProc) serviceProc.kill("SIGTERM");
});

// The `config` field of every /digitize POST, in order. Read through a route
// (as helpers.js `pinDigitizeConfig` does): Chromium's plain request event
// carries no body for a multipart upload with a file in it. Past
// `watch.abortAfter` requests the POST is captured and refused, so a step that
// only asks what the Studio SENDS costs no digitize.
async function watchConfigs(page) {
  const watch = { configs: [], abortAfter: Infinity };
  await page.route("**/digitize", async (route) => {
    const req = route.request();
    const buf = req.postDataBuffer();
    const m = req.method() === "POST" && buf && /name="config"\r\n\r\n(\{[^\r\n]*\})/.exec(buf.toString("latin1"));
    if (m) watch.configs.push(JSON.parse(m[1]));
    if (m && watch.configs.length > watch.abortAfter) return route.abort();
    return route.continue();
  });
  return watch;
}

const SHADING_WORDS = /shading|bevel|flatten/gi;
// Golden Tee is a heavy job (about 3 to 9 minutes a run on a loaded laptop),
// and a ticked run misses the generation cache: stages 0-4 run again.
const RUN_MS = 900_000;

test("Flatten shading: unticked sends nothing, ticked re-digitizes Golden Tee flatter, and the tick survives a resize", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(2 * RUN_MS + 120_000);
  if (SERVICE_URL !== DEFAULT_SERVICE_URL) {
    await page.addInitScript((url) => localStorage.setItem("embstudio:digitizerUrl", url), SERVICE_URL);
  }
  const watch = await watchConfigs(page);
  const configs = watch.configs;
  const stats = page.locator(".dgp-stats");
  const run = page.locator(".dgp-run");
  const body = page.locator("body");

  await page.goto("/");
  await uploadArtwork(page, ART, { run: false });
  await setDesignWidth(page, 60);
  const box = page.getByTestId("flatten-shading");
  await expect(box).not.toBeChecked();

  // ---- unticked: the request carries no key, as for any design before ----
  await runDigitize(page);
  await expect(stats).toBeVisible({ timeout: RUN_MS });
  await expect(run).toHaveText("Auto Digitize Image", { timeout: RUN_MS });
  expect(configs).toHaveLength(1);
  expect("bevel_ring_fold" in configs[0]).toBe(false);
  const off = await stats.innerText();
  const wordsOff = ((await body.innerText()).match(SHADING_WORDS) || []).length;

  // ---- ticked: stale, then a re-digitize whose generation changed --------
  await openAdvanced(page);
  await box.check();
  await expect(run).toHaveClass(/dgp-run-stale/);
  await runDigitize(page);
  await expect(stats).not.toHaveText(off, { timeout: RUN_MS });
  await expect(run).toHaveText("Auto Digitize Image", { timeout: RUN_MS });
  expect(configs).toHaveLength(2);
  expect(configs[1].bevel_ring_fold).toBe(true);
  expect({ ...configs[1], bevel_ring_fold: undefined }).toEqual({ ...configs[0], bevel_ring_fold: undefined });
  const on = await stats.innerText();
  const colours = (s) => Number(/(\d+) colou?rs?/.exec(s)[1]);
  const stitches = (s) => Number(/([\d,]+) stitches/.exec(s)[1].replace(/,/g, ""));
  expect(colours(on) < colours(off) || stitches(on) < stitches(off), `${off} -> ${on}`).toBe(true);
  // nothing new for the customer to read about it
  expect(((await body.innerText()).match(SHADING_WORDS) || []).length).toBe(wordsOff);

  // ---- a resize keeps it: the next run still asks for it -----------------
  watch.abortAfter = 2;
  await setDesignWidth(page, 50);
  await expect(box).toBeChecked();
  await expect(run).toHaveClass(/dgp-run-stale/);
  await runDigitize(page);
  await expect.poll(() => configs.length, { timeout: 30_000 }).toBe(3);
  expect(configs[2]).toMatchObject({ bevel_ring_fold: true, target_width_mm: 50 });
  await expect(box).toBeChecked();
});
