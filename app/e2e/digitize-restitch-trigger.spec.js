// MASTER_SCOPE area 5 carried an item -- "OPEN: the restitch trigger only
// exists on the Content step" -- written for the wizard, when
// DigitizePanel (which owns runDigitize) mounted only on step === "content"
// while the canvas edit tools mounted on every step. This spec is the
// verification that item asked for, against the configurator panel that
// replaced the wizard, driving the REAL digitizer service.
//
// What it pins, one test per situation the item named:
//
//   (a) a text element is selected,
//   (b) a different panel section is the one in use (Garment, below Design),
//   (c) nothing single is selected -- a multi-selection, the only
//       "no single element in front" state a project with elements can be in
//       (selectedId is never null while elements exist; clicking empty
//       fabric leaves the selection alone),
//
// and in each: a digitized-shape edit made on the canvas, then
//   1. NOTHING regenerates on its own (Kent's 2026-10-05 ruling: the
//      "Auto Digitize Image" button is the only thing that starts a run) --
//      the stitch count holds still through a wait longer than the old 2 s
//      auto-restitch debounce,
//   2. the edit is not lost: the element comes back with the run button
//      transparent (dgp-run-stale) and the edit pending,
//   3. one press of the button regenerates the stitches.
//
// Same service bootstrap and skip posture as digitize-stale-edits.spec.js:
// reuse a running service, start one from a venv if there is none, SKIP
// (never fail) with no digitizer venv. @playwright/test, not vitest.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, uploadArtwork, runDigitize } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Two squares side by side, centred (the same fixture field-shape-popover
// uses): a right-click 40% across the hoop lands inside the left one.
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
// Optional: set SHOT_DIR to keep screenshots of each state for a PR body.
const SHOT_DIR = process.env.SHOT_DIR || "";
if (SHOT_DIR) mkdirSync(SHOT_DIR, { recursive: true });
async function shot(page, name) {
  if (SHOT_DIR) await page.screenshot({ path: path.join(SHOT_DIR, name + ".png") });
}

const STATS = "span.stats";
// Longer than the 2 s debounce the removed auto-restitch used, so "nothing
// ran" is not just "it has not fired yet".
const QUIET_MS = 3500;

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

// ---- drives ----------------------------------------------------------------

async function digitizedDesign(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickGarment(page, "Tote");
  await uploadArtwork(page, ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
}

// The stitch count as the field's status line reads it: the whole project's,
// shown whichever panel is up (`.dgp-stats` lives in DigitizePanel and is
// gone whenever it is not mounted).
async function settledStats(page) {
  let value = "";
  await expect
    .poll(
      async () => {
        const reads = [];
        for (let i = 0; i < 3; i++) {
          reads.push(await page.locator(STATS).innerText());
          await page.waitForTimeout(300);
        }
        value = reads[0];
        return reads.every((r) => r === reads[0]);
      },
      { timeout: 30_000 },
    )
    .toBe(true);
  return value;
}

// The canvas edit: right-click inside the LEFT square -> "Add border". It
// writes shapeOverrides through `elupdate`, exactly what a node drag or a tier
// change writes, and it needs no aim at a one-pixel line.
async function addBorderOnLeftSquare(page) {
  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + box.width * 0.4, box.y + box.height * 0.5, { button: "right" });
  const menu = page.getByRole("menu", { name: "Shape and canvas tools" });
  await expect(menu).toBeVisible();
  await menu.getByRole("menuitem", { name: "Add border" }).click();
  await expect(menu).toHaveCount(0);
}

// Nothing started on its own: the count does not move for longer than the
// old debounce, and no run is in flight.
async function expectNothingRan(page, before) {
  await page.waitForTimeout(QUIET_MS);
  expect(await page.locator(STATS).innerText()).toBe(before);
  await expect(page.locator(".dgp-run", { hasText: "Digitizing…" })).toHaveCount(0);
}

// The edit is waiting for the button: the digitized element's panel is up,
// the button is transparent, and pressing it regenerates the stitches.
async function expectRestitchesOnButton(page, before) {
  const run = page.locator(".dgp-run");
  await expect(run).toHaveClass(/dgp-run-stale/);
  await expect(page.getByTestId("digitize-stale")).toBeVisible();
  await runDigitize(page);
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 120_000 }).not.toBe(before);
  await expect(run).not.toHaveClass(/dgp-run-stale/);
}

function digitizedRow(page) {
  return page.locator(".elrow").filter({ hasNotText: /^T\b/ }).first();
}

// ---- (a) a text element is selected ---------------------------------------

test("(a) text selected: a canvas edit on the digitized shape is kept, waits, and restitches on the button", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizedDesign(page);

  // Add text: it becomes the selected element and the panel is TextStep, so
  // DigitizePanel (and its run button) is not mounted.
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.getByPlaceholder("Type a name or word")).toBeVisible();
  await expect(page.locator(".dgp-run")).toHaveCount(0);
  const before = await settledStats(page);
  await shot(page, "a1-text-selected");

  // The canvas edit lands on the digitized element: a canvas edit selects the
  // element it edits, so the selection hands over from the text.
  await addBorderOnLeftSquare(page);
  await expect(page.locator(".dgp-run")).toBeVisible();
  await expect(page.getByPlaceholder("Type a name or word")).toHaveCount(0);
  await expectNothingRan(page, before);
  await shot(page, "a2-edited-pending");

  // ...and the edit survives a trip back to the text, with the stitches still
  // the previous request's (the canvas hatches them; the button waits).
  await page.locator(".elrow").filter({ hasText: /^T\b/ }).first().click();
  await expect(page.getByPlaceholder("Type a name or word")).toBeVisible();
  await expect(page.locator(".dgp-run")).toHaveCount(0);
  expect(await page.locator(STATS).innerText()).toBe(before);

  await digitizedRow(page).click();
  await shot(page, "a3-back-on-digitized-transparent-button");
  await expectRestitchesOnButton(page, before);
  await shot(page, "a4-restitched");
});

// ---- (b) another section of the panel is the one in use --------------------

test("(b) Garment section in use: a canvas edit on the digitized shape is kept, waits, and restitches on the button", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizedDesign(page);

  // The configurator has no steps: Design and Garment are two sections of one
  // scroll, both always mounted. Work in the Garment section -- scroll it
  // into view and change the garment -- then edit on the canvas.
  await page.locator('[data-section="garment"]').scrollIntoViewIfNeeded();
  await pickGarment(page, "Left Chest");
  const before = await settledStats(page);
  await shot(page, "b1-garment-section");

  await addBorderOnLeftSquare(page);
  await expectNothingRan(page, before);
  await shot(page, "b2-edited-pending");

  // The button is in the Design section, which is still mounted behind the
  // scroll: pressing it from here regenerates.
  await page.locator('[data-section="garment"]').scrollIntoViewIfNeeded();
  await expectRestitchesOnButton(page, before);
  await shot(page, "b3-restitched");
});

// ---- (c) no single element in front: a multi-selection ---------------------

test("(c) multi-selection (no single element's panel): a canvas edit brings the element's panel forward, waits, and restitches on the button", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizedDesign(page);

  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.getByPlaceholder("Type a name or word")).toBeVisible();
  // Ctrl+click the digitized row last: it becomes the primary of a two-element
  // selection, and ContentStep shows the group panel instead of its panel.
  await digitizedRow(page).click({ modifiers: ["Control"] });
  await expect(page.getByRole("heading", { name: "2 selected" })).toBeVisible();
  await expect(page.locator(".dgp-run")).toHaveCount(0);
  const before = await settledStats(page);
  await shot(page, "c1-multi-selected");

  await addBorderOnLeftSquare(page);
  await expectNothingRan(page, before);
  await shot(page, "c2-edited-pending");

  // A canvas edit on a digitized shape hands the selection to that shape --
  // the same rule as (a) -- so the element's panel, with the transparent
  // button and the edit pending, is already in front. Without it the edit was
  // accepted under the group panel, which has no run button, and the only
  // sign of an unsewn edit was the hatching on the canvas.
  await expect(page.getByRole("heading", { name: "2 selected" })).toHaveCount(0);
  await expect(page.locator(".dgp-run")).toBeVisible();
  await expectRestitchesOnButton(page, before);
  await shot(page, "c3-restitched");
});
