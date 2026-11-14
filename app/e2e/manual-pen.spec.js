// End to end for the pen: a DRAG on the side canvas draws a Line or a Column
// in one gesture (spec docs/superpowers/specs/2026-11-13-pen-auto-branch-design.md
// section 2). No digitizer service is involved -- the hand-drawn lane stitches
// in the browser.
//
// Helpers are copied from manual-run.spec.js by this directory's convention
// (no imports across spec files).
import { test, expect } from "@playwright/test";
import { pickGarment, openAdvanced } from "./helpers.js";

const STATS = "span.stats";
const count = (stats) => Number(stats.match(/([\d,]+) stitches/)[1].replace(/,/g, ""));

async function toContent(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
}

async function openDrawing(page) {
  await page.locator(".hoop canvas").click({ button: "right" });
  await page.locator(".fieldmenu button").filter({ hasText: "Draw shapes" }).click();
  await openAdvanced(page);
  await expect(page.locator(".mp-canvas")).toBeVisible();
}

async function setMode(page, label) {
  const btn = page.getByRole("group", { name: "Drawing mode" }).getByRole("button", { name: label, exact: true });
  await btn.click();
  await expect(btn).toHaveAttribute("aria-pressed", "true");
}

// Press at the first point, move through the rest, release at the last. Points
// are fractions of the side canvas's displayed box.
async function dragStroke(page, pts) {
  const mp = page.locator(".mp-canvas");
  await mp.scrollIntoViewIfNeeded();
  const box = await mp.boundingBox();
  const at = ([fx, fy]) => [box.x + box.width * fx, box.y + box.height * fy];
  const [x0, y0] = at(pts[0]);
  await page.mouse.move(x0, y0);
  await page.mouse.down();
  for (const p of pts.slice(1)) {
    const [x, y] = at(p);
    await page.mouse.move(x, y, { steps: 8 });
  }
  await page.mouse.up();
}

async function stitchCount(page) {
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  let last = null;
  await expect.poll(async () => {
    const a = await page.locator(STATS).innerText();
    await page.waitForTimeout(400);
    const b = await page.locator(STATS).innerText();
    last = b;
    return a === b;
  }, { timeout: 30_000 }).toBe(true);
  return count(last);
}

test("(p1) Line mode: one drag is one line, and it sews", async ({ page }) => {
  test.setTimeout(120_000);
  await toContent(page);
  await openDrawing(page);
  await setMode(page, "Line");
  await expect(page.locator(".mp-modehint")).toHaveText("Drag along the line to draw it. Or click along it, then double-click to finish.");
  await dragStroke(page, [[0.2, 0.3], [0.5, 0.6], [0.8, 0.3]]);
  await expect(page.locator(".mp-shaperow")).toHaveCount(1);
  await expect(page.locator(".mp-shaperow").first()).toContainText("Shape 1 · Line");
  // the drag left no draft behind: nothing to undo, nothing to finish
  await expect(page.getByRole("button", { name: "Undo point" })).toBeDisabled();
  expect(await stitchCount(page)).toBeGreaterThan(0);
});

test("(p2) Column mode: two drags are two columns, and click-drawing still works beside them", async ({ page }) => {
  test.setTimeout(150_000);
  await toContent(page);
  await openDrawing(page);
  await setMode(page, "Column");
  await dragStroke(page, [[0.2, 0.3], [0.8, 0.3]]);
  await expect(page.locator(".mp-shaperow")).toHaveCount(1);
  await expect(page.locator(".mp-shaperow").first()).toContainText("Shape 1 · Column");
  const one = await stitchCount(page);
  expect(one).toBeGreaterThan(0);

  await dragStroke(page, [[0.2, 0.7], [0.5, 0.8], [0.8, 0.7]]);
  await expect(page.locator(".mp-shaperow")).toHaveCount(2);
  await expect(page.locator(".mp-shaperow").nth(1)).toContainText("Shape 2 · Column");
  await expect.poll(() => stitchCount(page), { timeout: 30_000 }).toBeGreaterThan(one);

  // a click is still a click: two of them and Enter draw a third column
  const mp = page.locator(".mp-canvas");
  const box = await mp.boundingBox();
  await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.5);
  await page.mouse.click(box.x + box.width * 0.7, box.y + box.height * 0.5);
  await mp.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".mp-shaperow")).toHaveCount(3);
});
