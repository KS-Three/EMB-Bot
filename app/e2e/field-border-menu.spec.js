// End-to-end test for the border on the canvas (Kent's 2026-09-09 ask: a
// clickable satin border on the image — right-click a recognised shape, Add,
// Remove). Drives the REAL digitizer service through the real field:
//
//   upload art -> digitize -> right-click a shape's outline -> the menu names
//   the shape and offers "Add border" above the drawing tools -> choose it ->
//   the Digitize panel's Border select for that shape reads "auto" and the
//   design restitches (the stats line moves) -> right-click INSIDE the same
//   shape -> "Remove border" -> the select reads "off". A right-click on the
//   empty field still shows the drawing tools alone, and Escape closes it.
//
// Same self-contained service bootstrap and fixture as field-outlines.spec.js
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
// Screenshots of the open menu, for the look-at-it step (COOKBOOK: a Studio
// change is not verified until it has been looked at in a browser). Written
// only when asked for, so CI's run stays a test and not a screenshot job.
const SHOT_DIR = process.env.BORDER_MENU_SHOTS || "";

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

// A point actually on an outline, read off the live canvas rather than
// guessed: the first cyan (unselected outline) pixel in raster order, which on
// this fixture is the top edge of a square. Client px, so the mouse can use it.
async function outlinePoint(page) {
  const toggle = page.locator('.zoomctl button[aria-label="Show shape outlines"]');
  if ((await toggle.getAttribute("aria-pressed")) !== "true") await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  return expect
    .poll(
      () =>
        page.evaluate(() => {
          const c = document.querySelector(".hoop canvas");
          const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
          for (let i = 0; i < d.length; i += 4) {
            if (d[i] < 90 && d[i + 1] > 140 && d[i + 2] > 180) {
              const px = (i / 4) % c.width;
              const py = Math.floor(i / 4 / c.width);
              const r = c.getBoundingClientRect();
              return { x: r.left + (px / c.width) * r.width, y: r.top + (py / c.height) * r.height };
            }
          }
          return null;
        }),
      { timeout: 10_000 },
    )
    .not.toBeNull()
    .then(() =>
      page.evaluate(() => {
        const c = document.querySelector(".hoop canvas");
        const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
        for (let i = 0; i < d.length; i += 4) {
          if (d[i] < 90 && d[i + 1] > 140 && d[i + 2] > 180) {
            const px = (i / 4) % c.width;
            const py = Math.floor(i / 4 / c.width);
            const r = c.getBoundingClientRect();
            return { x: r.left + (px / c.width) * r.width, y: r.top + (py / c.height) * r.height };
          }
        }
        return null;
      }),
    );
}

// The per-shape rows sit behind a closed-by-default "Edit shapes" disclosure;
// anything that reads a row has to open it first. Idempotent.
async function openShapeRows(page) {
  const btn = page.getByRole("button", { name: /^Edit shapes/ });
  await expect(btn).toBeVisible({ timeout: 120_000 });
  if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
}

async function borderSelectValues(page) {
  await openShapeRows(page);
  return page.locator('select[aria-label^="Border — "]').evaluateAll((els) => els.map((e) => e.value));
}

test("right-click a shape: Add border reaches the panel's select and the stitch-out; Remove takes it back", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1440, height: 900 });
  await digitize(page);
  const statsBefore = await page.locator(".dgp-stats").innerText();

  const at = await outlinePoint(page);
  await page.mouse.click(at.x, at.y, { button: "right" });

  const menu = page.getByRole("menu", { name: "Shape and canvas tools" });
  await expect(menu).toBeVisible();
  const add = menu.getByRole("menuitem", { name: "Add border" });
  await expect(add).toBeVisible();
  // The drawing tools are still on the same menu — the shape section joins
  // them, it does not replace them.
  await expect(menu.getByRole("menuitem", { name: "Draw shapes" })).toBeVisible();
  await expect(menu.getByRole("menuitem", { name: "Remove border" })).toHaveCount(0);
  if (SHOT_DIR) await page.screenshot({ path: path.join(SHOT_DIR, "border-menu-add-1440.png") });

  await add.click();
  await expect(menu).toHaveCount(0);

  // The same field the panel's own Border select edits.
  await expect.poll(() => borderSelectValues(page), { timeout: 10_000 }).toContain("auto");
  // ...and the design restitches on its own after the idle pause: the stats
  // line changes (a satin border on a square is hundreds of stitches).
  await expect.poll(() => page.locator(".dgp-stats").innerText(), { timeout: 120_000 }).not.toBe(statsBefore);

  // Right-click INSIDE the same square (just below its top edge): the border
  // is the outline, but the command needs no aim at a one-pixel line.
  await page.mouse.click(at.x, at.y + 14, { button: "right" });
  await expect(menu).toBeVisible();
  const remove = menu.getByRole("menuitem", { name: "Remove border" });
  await expect(remove).toBeVisible();
  await expect(menu.getByRole("menuitem", { name: "Use design setting" })).toBeVisible();
  if (SHOT_DIR) await page.screenshot({ path: path.join(SHOT_DIR, "border-menu-remove-1440.png") });
  await remove.click();
  await expect(menu).toHaveCount(0);
  await expect.poll(() => borderSelectValues(page), { timeout: 10_000 }).toContain("off");
});

test("a right-click on the empty field shows the drawing tools alone, and Escape closes it", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1024, height: 768 });
  await digitize(page);

  const canvas = page.locator(".hoop canvas");
  const box = await canvas.boundingBox();
  // The top-left corner of the field is hoop, not design.
  await page.mouse.click(box.x + 6, box.y + 6, { button: "right" });
  const tools = page.getByRole("menu", { name: "Canvas tools" });
  await expect(tools).toBeVisible();
  await expect(tools.getByRole("menuitem", { name: "Draw shapes" })).toBeVisible();
  await expect(page.getByRole("menuitem", { name: /border/ })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(tools).toHaveCount(0);

  // And the shape menu at the narrower width, for the look-at-it step.
  const at = await outlinePoint(page);
  await page.mouse.click(at.x, at.y, { button: "right" });
  const menu = page.getByRole("menu", { name: "Shape and canvas tools" });
  await expect(menu).toBeVisible();
  if (SHOT_DIR) await page.screenshot({ path: path.join(SHOT_DIR, "border-menu-add-1024.png") });
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
});
