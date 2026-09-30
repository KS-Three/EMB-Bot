// The Layers list and the canvas point at the same shape (2026-09-30).
//
// Before this, `selectedShapeId` in EmbroideryField was set from a canvas hit
// only — its own comment said so — and a row in a thirty-row list had no way
// to say which outline it was, nor the canvas which row. Three things are
// pinned here, each read off the live canvas rather than off component
// state: hovering a row draws that shape's outline (white) on the field with
// the outlines toggle OFF; clicking a row's name selects the shape (amber);
// and clicking a shape on the canvas marks its row in the list.
//
// Code-based @playwright/test spec, against the real digitizer service, the
// same way e2e/field-outlines.spec.js runs (its service bootstrap is copied
// here rather than shared so each file stays runnable on its own).
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

// Pixels of the three outline colours EmbroideryField draws, off the live
// canvas: cyan for an unselected outline (toggle on), amber for the selected
// shape, white for the hovered one. Loose bounds — every one is drawn over a
// dark casing and antialiased against thread and fabric. The white core is
// 0.95 alpha over that casing, which lands at ~248 on the centre line, so
// the white test is 240: below that, above the Natural fabric's (235,232,223).
async function overlayPixels(page) {
  return page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let cyan = 0, amber = 0, white = 0;
    for (let i = 0; i < d.length; i += 4) {
      const r = d[i], g = d[i + 1], b = d[i + 2];
      if (r < 90 && g > 140 && b > 180) cyan++;
      else if (r > 190 && g > 150 && g < 225 && b < 120) amber++;
      else if (r > 240 && g > 240 && b > 240) white++;
    }
    return { cyan, amber, white };
  });
}

async function digitize(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await page.waitForTimeout(1200);
  // The rows live on the Shapes tab, behind the closed-by-default "Edit
  // shapes" disclosure.
  await page.getByRole("tab", { name: "Shapes" }).click();
  await page.getByRole("button", { name: /^Edit shapes/ }).click();
  await expect(page.locator(".dgp-layer").first()).toBeVisible();
}

// A point on a cyan outline pixel, in client px, with the outlines shown and
// then hidden again — the same route e2e/field-outlines.spec.js takes to
// click a shape.
async function outlinePoint(page) {
  const toggle = page.locator('.zoomctl button[aria-label="Show shape outlines"]');
  await toggle.click();
  await expect.poll(async () => (await overlayPixels(page)).cyan, { timeout: 10_000 }).toBeGreaterThan(100);
  const target = await page.evaluate(() => {
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
  });
  await toggle.click();
  await expect.poll(async () => (await overlayPixels(page)).cyan, { timeout: 10_000 }).toBe(0);
  return target;
}

test("hovering a row outlines its shape on the canvas, and leaving it clears the outline", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await digitize(page);

  // Outlines are off by default, so a white outline can only be the hover.
  const before = await overlayPixels(page);
  expect(before.cyan).toBe(0);

  const row = page.locator(".dgp-layer:not(.dead):not(.unstitched)").first();
  await row.hover();
  await expect(row).toHaveClass(/\bdgp-layer-hover\b/);
  await expect.poll(async () => (await overlayPixels(page)).white, { timeout: 10_000 })
    .toBeGreaterThan(before.white + 40);

  // Off the list entirely (the topbar), so no other row picks the hover up.
  await page.locator(".topbar").hover();
  await expect(row).not.toHaveClass(/\bdgp-layer-hover\b/);
  await expect.poll(async () => (await overlayPixels(page)).white, { timeout: 10_000 })
    .toBeLessThanOrEqual(before.white + 5);
});

test("clicking a row's name selects the shape on the canvas (amber), and the row shows selected", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await digitize(page);

  expect((await overlayPixels(page)).amber).toBe(0);
  const row = page.locator(".dgp-layer:not(.dead):not(.unstitched)").first();
  await row.locator(".dgp-lname-btn").click();
  await expect(row).toHaveClass(/\bdgp-layer-sel\b/);
  await expect.poll(async () => (await overlayPixels(page)).amber, { timeout: 10_000 }).toBeGreaterThan(40);
});

test("clicking a shape on the canvas marks its row in the list, and clicking away clears it", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await digitize(page);

  const target = await outlinePoint(page);
  expect(target).not.toBeNull();
  await page.mouse.click(target.x, target.y);
  await expect.poll(async () => (await overlayPixels(page)).amber, { timeout: 10_000 }).toBeGreaterThan(40);
  await expect(page.locator(".dgp-layer.dgp-layer-sel")).toHaveCount(1);

  // The canvas is the source of truth for the selection: dropping it there
  // (a click on bare fabric, which the field treats as "away from every
  // outline") drops the row's mark too.
  const canvas = page.locator(".hoop canvas");
  const box = await canvas.boundingBox();
  await page.mouse.click(box.x + 12, box.y + 12);
  await expect(page.locator(".dgp-layer.dgp-layer-sel")).toHaveCount(0);
});
