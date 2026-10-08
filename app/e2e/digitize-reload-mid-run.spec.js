// Reload (or leave) while Auto Digitize runs, then come back. The job lives in
// the service and the panel only polls it, so a reload used to drop the poll
// and the result with it: the element came back idle, unstitched, and the
// service job ran on unattended. A started run is now remembered per element
// (lib/digitizeBusy.js rememberRun) and the next panel joins the service's job.
//
// Same service bootstrap and skip posture as digitize-auto-start.spec.js.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, uploadArtwork } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// The same flat two-squares fixture the stale-edits spec uses: black and red
// on white, which stage 0 reads as flat art -- so this spec's expected reading
// is the flat one. Nothing is offered beside a FLAT reading: the row is a
// statement there (Kent, 2026-09-30 -- "It's a photo" is gone and the
// engine's own detection answers instead; the flat switch that came back
// the same evening, "Sew as flat art", shows on tonal readings only).
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
// A vector logo with a `viewBox` and NO width/height — the shape SVGO and most
// hand-written exports produce, and the one Chrome hands back at its 300 px
// default size. Three inks on white: one blue circle, one red bar, one blue
// bar, so the ONLY honest answer is two thread colours.
const ART_SVG = path.join(__dirname, "fixtures", "vector_logo.svg");

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


test("reloading mid-run resumes the same service job and lands the stitches", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  // Slow every poll so the run is certainly still in flight when we reload
  // (a cache hit from an earlier spec would otherwise finish first).
  await page.route("**/jobs/*", async (route) => {
    await new Promise((r) => setTimeout(r, 1500));
    await route.continue();
  });
  const submitted = [];
  page.on("response", async (r) => {
    if (r.request().method() === "POST" && r.url().endsWith("/digitize")) {
      try { submitted.push((await r.json()).job_id); } catch (e) { /* ignore */ }
    }
  });

  await startStudio(page);
  await pickGarment(page, "Tote");
  await uploadArtwork(page, ART_PNG, { run: false });
  await page.locator(".dgp-run").click();
  await expect(page.locator(".dgp-run")).toBeDisabled(); // in flight
  await expect.poll(() => submitted.length).toBe(1);

  await page.reload();
  // The restored element resumes on its own: no second click.
  await expect.poll(() => submitted.length, { timeout: 60_000 }).toBe(2);
  // Same content -> the service hands back the SAME job, not a new orphan.
  expect(submitted[1]).toBe(submitted[0]);

  // The result lands and the panel is not left busy.
  await expect(page.getByRole("tab", { name: "Shapes" })).toBeVisible({ timeout: 120_000 });
  await expect(page.locator(".dgp-run")).toBeEnabled();
  await expect(page.locator(".dgp-run")).toHaveText(/Digitize/);
  expect(await page.evaluate(() => Object.keys(sessionStorage).filter((k) => k.startsWith("embot.digitizing.")))).toEqual([]);
});
