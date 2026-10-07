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
import { pickGarment, uploadArtwork } from "./helpers.js";
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

// Pixels the thread covers, straight off the live canvas: anything that is
// not the fabric. The fabric is read from the canvas's own corner (inside the
// hoop but outside the design), so the count does not depend on which swatch
// the garment picked; a loose per-channel distance absorbs the weave.
async function threadPixels(page) {
  return page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    // a fabric sample: the median of a small patch 12 px in from the top-left
    // of the hoop's inside, which the design never reaches at fit zoom
    const sx = Math.floor(c.width * 0.3), sy = Math.floor(c.height * 0.12);
    const rs = [], gs = [], bs = [];
    for (let y = sy; y < sy + 6; y++) for (let x = sx; x < sx + 6; x++) {
      const i = (y * c.width + x) * 4;
      rs.push(d[i]); gs.push(d[i + 1]); bs.push(d[i + 2]);
    }
    const med = (a) => a.sort((p, q) => p - q)[Math.floor(a.length / 2)];
    const fr = med(rs), fg = med(gs), fb = med(bs);
    let n = 0;
    for (let i = 0; i < d.length; i += 4) {
      if (Math.abs(d[i] - fr) + Math.abs(d[i + 1] - fg) + Math.abs(d[i + 2] - fb) > 90) n++;
    }
    return n;
  });
}

async function digitize(page) {
  await page.goto("/");
  await pickGarment(page, "Polo");
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

  const off = await threadPixels(page);
  expect(off).toBeGreaterThan(1000);

  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  // Pique knit is 0.3 mm a side: a 1 mm satin column draws 0.6 mm narrower,
  // so the thread covers measurably less fabric. The bound is loose on
  // purpose — the fixture's satin share and the zoom set the exact figure.
  await expect.poll(async () => await threadPixels(page), { timeout: 10_000 })
    .toBeLessThan(off * 0.97);
  // a view: the design's own numbers do not move
  expect(await page.locator("span.stats").innerText()).toBe(caption);

  // and back off again restores the file's view, to the pixel budget of a
  // repaint (the realistic render is deterministic for one design and view)
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect.poll(async () => await threadPixels(page), { timeout: 10_000 })
    .toBeGreaterThan(off * 0.995);
  expect(await page.locator("span.stats").innerText()).toBe(caption);
});
