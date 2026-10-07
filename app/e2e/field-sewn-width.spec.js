// "Sewn width" is a VIEW toggle beside Outlines / Jumps / Trims (2026-10-06):
// every satin column is cut wider than its artwork by the fabric's pull
// compensation on each rail, and the canvas draws that column plus the
// thread, so a satin letter reads about twice as heavy on screen as it sews.
// Kent read Hotel Fremont's letters as "waaaay thicker than they should be";
// the pro's own file of the same logo rendered at the same weight. The
// toggle takes the pull back off each satin strand (lib/sewnWidth.js,
// strands.js's shrinkSatinStrands) and nothing in the design moves.
//
// What these tests pin, off the live canvas: the toggle is off by default
// and enabled once a digitized design with satin spans is on the field;
// on, the thread covers measurably LESS of the fabric (the columns got
// narrower); off again restores the file's view. The design's stitch
// caption does not change at any point — a view only.
//
// Same self-contained service bootstrap as field-outlines.spec.js (each
// e2e spec here duplicates that boilerplate rather than importing it,
// matching this directory's own convention).
import { test, expect } from "@playwright/test";
import { startStudio, uploadArtwork } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
// The lettering fixture: ENTHUSIAST sews as satin columns, which is what the
// toggle acts on (two-squares.png is two fills and would leave it disabled).
const ART_PNG = path.join(__dirname, "fixtures", "enthusiast_logo.png");

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
    const stat = readFileSync(path.join(roots[0], ".git"), "utf8");
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
    serviceUp = true;
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
  skipReason = "digitizer service failed to answer /health within 30s of being started (" + python + ").";
});

test.afterAll(() => {
  if (serviceProc) serviceProc.kill("SIGTERM");
});

// Dark pixels straight off the live canvas: the lettering fixture sews in
// dark thread on a light fabric, and the surround outside the hoop is dark
// too but never changes, so the DIFFERENCE between two readings is thread
// and only thread. `snapshot` keeps the current bitmap on the page;
// `darkAndChanged` reads how many pixels are dark now and how many differ
// from that snapshot.
async function snapshot(page) {
  await page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    window.__sewnSnap = c.getContext("2d").getImageData(0, 0, c.width, c.height).data.slice();
  });
}

async function darkAndChanged(page) {
  return page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const s = window.__sewnSnap;
    let dark = 0, changed = 0;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i] + d[i + 1] + d[i + 2] < 240) dark++;
      if (s && (Math.abs(d[i] - s[i]) + Math.abs(d[i + 1] - s[i + 1]) + Math.abs(d[i + 2] - s[i + 2]) > 60)) changed++;
    }
    return { dark, changed };
  });
}

async function digitize(page) {
  // The default garment is Left Chest (pique knit, 0.3 mm a side), which is
  // the pull the assertions below are sized for.
  await startStudio(page);
  await uploadArtwork(page, ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 180_000 });
  await page.waitForTimeout(1200); // let the field settle after the result lands
}

test("sewn width is off by default, narrows the satin on, and the file is untouched", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(360_000);

  await page.setViewportSize({ width: 1440, height: 900 });
  await digitize(page);

  const toggle = page.locator('.zoomctl button[aria-label="Show sewn width"]');
  await expect(toggle).toBeEnabled();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  const caption = await page.locator("span.stats").innerText();
  expect(caption).toMatch(/stitches/);

  // Zoom in on the lettering: at fit zoom a millimetre is four pixels and a
  // 0.3 mm step per rail is under the thread's own line floor, so the view
  // barely changes on screen (223 pixels measured). Four steps in, it is a
  // measurable region of the canvas.
  const zoomIn = page.locator('button[aria-label="Zoom in"]');
  for (let i = 0; i < 4; i++) await zoomIn.click();
  await page.waitForTimeout(800);
  await snapshot(page);
  const off = await darkAndChanged(page);
  expect(off.dark).toBeGreaterThan(1000);
  expect(off.changed).toBe(0);

  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  // Pique knit is 0.3 mm a side: a 1 mm satin column draws 0.6 mm narrower.
  // Thread pixels go, nothing comes: the canvas changes by at least a few
  // hundred pixels and the dark count falls. Loose on purpose — the
  // fixture's satin share and the zoom set the exact figure.
  await expect.poll(async () => (await darkAndChanged(page)).changed, { timeout: 10_000 })
    .toBeGreaterThan(300);
  expect((await darkAndChanged(page)).dark).toBeLessThan(off.dark);
  // a view: the design's own numbers do not move
  expect(await page.locator("span.stats").innerText()).toBe(caption);

  // and back off again restores the file's view, pixel for pixel: the
  // realistic render is deterministic for one design and view
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect.poll(async () => (await darkAndChanged(page)).changed, { timeout: 10_000 })
    .toBe(0);
  expect(await page.locator("span.stats").innerText()).toBe(caption);
});
