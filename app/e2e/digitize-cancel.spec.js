// Cancel a running digitize, then digitize again (2026-11-12). A job runs 60
// to 600 s and the panel used to offer wait-or-reload. Cancel sits beside the
// status line while a run is in flight: it tells the service to stop the job
// (POST /jobs/{id}/cancel, which frees the one worker at the next stage seam)
// and puts the panel back to idle with the artwork and settings kept. A
// cancel is not an error and nothing is shown as one.
//
// Same service bootstrap and skip posture as digitize-reload-mid-run.spec.js.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, uploadArtwork, setDesignWidth, pinDigitizeConfig, watchConsole } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Lettering on a mark: seconds of work at this width rather than the fraction
// of one the two-squares fixture takes, so the job is certainly still running
// when Cancel is pressed.
const ART_PNG = path.join(__dirname, "fixtures", "enthusiast_logo.png");
// The width typed into the panel, and the setting the spec checks is kept.
const WIDTH_MM = 97;
// What the service is actually sent: that width plus under a micron that no
// earlier run has used. On a developer's reused service an identical request
// is answered from the job cache, finished, with nothing left to cancel --
// and the second run of this very spec would be that request.
const sentWidthMm = () => WIDTH_MM + (Date.now() % 1_000_000) / 1e9;

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

function venvPythonCandidates() {
  const roots = [path.resolve(__dirname, "../..")];
  try {
    const stat = readFileSync(path.join(roots[0], ".git"), "utf8"); // throws when .git is a directory
    const m = stat.match(/^gitdir:\s*(.+)$/m);
    if (m) {
      const mainRoot = path.resolve(m[1].trim(), "../../..");
      if (mainRoot !== roots[0]) roots.push(mainRoot);
    }
  } catch (e) {
    // .git is a directory: a normal checkout, nothing to add
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
    skipReason =
      "digitizer service is not running and no venv python was found. " +
      "Start it manually: `python -m digitizer_service` in digitizer/.";
    return;
  }
  serviceProc = spawn(python, ["-m", "digitizer_service"], {
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
  skipReason = "digitizer service failed to answer /health within 30s of being started.";
});

test.afterAll(() => {
  if (serviceProc) serviceProc.kill("SIGTERM");
});

const jobState = async (id) => (await (await fetch(SERVICE_URL + "/jobs/" + id)).json()).state;
const inflight = async () => (await (await fetch(SERVICE_URL + "/health")).json()).jobs.inflight;

test("cancel a running digitize, then digitize again", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  // Nothing red in DevTools either. Typing the width supersedes the pre-run
  // /recount and /classify asks, which the panel aborts by design.
  const guard = watchConsole(page, { ignore: [/\/recount/, /\/classify/] });
  const submitted = [];
  const cancels = [];
  page.on("response", async (r) => {
    if (r.request().method() !== "POST") return;
    try {
      if (r.url().endsWith("/digitize")) submitted.push((await r.json()).job_id);
      else if (/\/jobs\/[^/]+\/cancel$/.test(r.url())) cancels.push({ status: r.status(), ...(await r.json()) });
    } catch (e) { /* ignore */ }
  });

  await pinDigitizeConfig(page, { target_width_mm: sentWidthMm() });
  await startStudio(page);
  await pickGarment(page, "Tote");
  await uploadArtwork(page, ART_PNG, { run: false });
  await setDesignWidth(page, WIDTH_MM);

  const run = page.locator(".dgp-run");
  const cancel = page.getByRole("button", { name: "Cancel digitizing" });
  await expect(cancel).toHaveCount(0); // only while a run is in flight

  await expect(run).toBeEnabled({ timeout: 30_000 });
  await run.click();
  await expect(page.locator(".dgp-status", { hasText: "Digitizing your art" })).toBeVisible({ timeout: 60_000 });
  await expect(cancel).toBeVisible();
  await expect(cancel).toHaveText("Cancel");

  // By keyboard: it is a button in the tab order, straight after the run button.
  await cancel.focus();
  await page.keyboard.press("Enter");

  // Back to idle: no run, no Cancel, no error, and focus on the way to run again.
  await expect(run).toBeEnabled();
  await expect(run).toHaveText("Auto Digitize Image");
  await expect(cancel).toHaveCount(0);
  await expect(run).toBeFocused();
  await expect(page.locator(".dgp-error")).toHaveCount(0);
  await expect(page.locator(".dgp-status", { hasText: /Digitizing|Cancelling|Sending/ })).toHaveCount(0);
  // The artwork and the settings are the ones the customer left.
  await expect(page.getByLabel("Design width")).toHaveValue(String(WIDTH_MM));
  expect(await page.evaluate(() => Object.keys(sessionStorage).filter((k) => k.startsWith("embot.digitizing.")))).toEqual([]);

  // The service heard it: the job reads cancelled (a state, not an error)...
  await expect.poll(() => cancels.length).toBe(1);
  expect(submitted).toHaveLength(1);
  expect(cancels).toEqual([{ status: 200, job_id: submitted[0], state: "cancelled" }]);
  expect(await jobState(submitted[0])).toBe("cancelled");
  // ...and its worker stops at the next stage seam instead of finishing the job.
  await expect.poll(inflight, { timeout: 60_000 }).toBe(0);

  // Digitize again: a fresh job (not a replay of the cancelled one) that lands.
  await run.click();
  await expect.poll(() => submitted.length, { timeout: 30_000 }).toBe(2);
  expect(submitted[1]).not.toBe(submitted[0]);
  await expect(page.locator(".dgp-stats")).toContainText(/[\d,]+ stitches/, { timeout: 180_000 });
  await expect(run).toBeEnabled();
  await expect(run).toHaveText("Auto Digitize Image");
  await expect(cancel).toHaveCount(0);
  expect(await jobState(submitted[1])).toBe("done");
  expect(cancels).toHaveLength(1);
  guard.expectClean();
});
