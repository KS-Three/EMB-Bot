// The shape-outline overlay is a DIAGNOSTIC, not part of the preview.
//
// Every shape of a digitized element used to be stroked in cyan with a node
// on every vertex, permanently — not tied to selection, not tied to an edit
// mode, and unaffected by the "Realistic view" toggle (verified by measuring
// the live canvas: turning realistic thread off left the cyan exactly where
// it was). On the enthusiast_logo fixture that is 31 outlines laid over the
// artwork, so the one screen meant to answer "what will this look like
// sewn?" answered "here is a wireframe" instead.
//
// It now sits behind a toolbar toggle beside "Show jumps" and "Show trims",
// default off, which is what these tests pin: a clean canvas by default, the
// outlines on demand, and — the safety property — the SELECTED shape still
// outlined either way, because that highlight is what tells you which shape
// a Delete or a drag is about to act on.
//
// Same self-contained service bootstrap as digitize-shape-identity.spec.js
// (each e2e spec here duplicates that boilerplate rather than importing it,
// matching this directory's own convention).
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");

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

// Counts pixels of the two overlay colours EmbroideryField uses, straight off
// the live canvas. Cyan `rgba(0, 200, 255)` is an unselected outline; amber
// `rgba(255, 214, 64)` is the selected one. Loose bounds because both are
// drawn over a dark casing and antialiased against thread and fabric.
async function overlayPixels(page) {
  return page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let cyan = 0, amber = 0;
    for (let i = 0; i < d.length; i += 4) {
      const r = d[i], g = d[i + 1], b = d[i + 2];
      if (r < 90 && g > 140 && b > 180) cyan++;
      else if (r > 190 && g > 150 && g < 225 && b < 120) amber++;
    }
    return { cyan, amber };
  });
}

async function digitize(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();
  // No Digitize click: choosing the file starts the run (DigitizePanel's
  // sourcePng watcher).
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await page.waitForTimeout(1200); // let the field settle after the result lands
}

test("the digitized preview is clean by default, and the toggle brings the outlines back", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1440, height: 900 });
  await digitize(page);

  const toggle = page.locator('.zoomctl button[aria-label="Show shape outlines"]');
  await expect(toggle).toHaveAttribute("aria-pressed", "false");

  // Default: a stitch-out, not a wireframe. Before this change the same
  // measurement on the enthusiast_logo fixture returned ~2,184 cyan pixels.
  const off = await overlayPixels(page);
  expect(off.cyan).toBe(0);

  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await expect.poll(async () => (await overlayPixels(page)).cyan, { timeout: 10_000 })
    .toBeGreaterThan(100);

  // And back off again — a toggle that only works one way is half a feature.
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect.poll(async () => (await overlayPixels(page)).cyan, { timeout: 10_000 }).toBe(0);
});

test("the shape you click is still outlined with the toggle off", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1440, height: 900 });
  await digitize(page);

  // Shape picking targets the outline itself — a node or an edge, not the
  // shape's interior (see EmbroideryField's pointerdown: "grabbing a node or
  // a line edits the SHAPE while everywhere else inside the element still
  // moves the whole element"). So show the outlines, aim at one, then hide
  // them again: the risk this guards is that hiding by default quietly
  // breaks shape editing instead of decluttering it.
  const toggle = page.locator('.zoomctl button[aria-label="Show shape outlines"]');
  await toggle.click();
  await expect.poll(async () => (await overlayPixels(page)).cyan, { timeout: 10_000 })
    .toBeGreaterThan(100);

  // A point actually on an outline, read off the canvas rather than guessed.
  const target = await page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i] < 90 && d[i + 1] > 140 && d[i + 2] > 180) {
        const px = (i / 4) % c.width;
        const py = Math.floor(i / 4 / c.width);
        const r = c.getBoundingClientRect();
        // canvas px -> client px (the bitmap may be denser than its CSS box)
        return { x: r.left + (px / c.width) * r.width, y: r.top + (py / c.height) * r.height };
      }
    }
    return null;
  });
  expect(target).not.toBeNull();
  await page.mouse.click(target.x, target.y);

  await expect
    .poll(async () => (await overlayPixels(page)).amber, { timeout: 10_000 })
    .toBeGreaterThan(20);

  // Now hide them: the selected shape keeps its highlight, the other
  // outlines go. That highlight is what tells you which shape a Delete or a
  // drag is about to act on, so it has to survive the toggle.
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect.poll(async () => (await overlayPixels(page)).cyan, { timeout: 10_000 }).toBe(0);
  expect((await overlayPixels(page)).amber).toBeGreaterThan(20);
});
