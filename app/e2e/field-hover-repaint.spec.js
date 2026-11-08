// A cursor change never repaints the field (2026-11-07).
//
// In Svelte 5's legacy mode `canvas.style.cursor = x` invalidates `canvas`,
// which re-runs `$: if (canvas) { project; runtime; paint(); }`: every hover
// that set the cursor re-ran paint(), the full regenerate, and drew the whole
// field again to show nothing new. #1332 found it closing the simulator and
// fixed the two writes that ran there; this pins the edit-mode ones, in every
// edit mode, by counting the field's full renders while the pointer hovers.
//
// How a render is counted: renderRealistic (lib/preview.js) opens every field
// render by filling the whole canvas, `fillRect(0, 0, cw, ch)`. The init
// script counts exactly those calls on the `.hoop` canvas. A hover at a point
// is: settle there, zero the count, make eight 1 px moves that keep the same
// cursor, settle again, read the count. Each mode is swept on a grid first,
// so every cursor that mode shows is hovered, not one picked by hand.
//
// SERVICE_URL (the digitizer service at 127.0.0.1:8721): the digitized modes
// need it, so playwright.config.js runs this file in the serial step.
import { test, expect } from "@playwright/test";
import { pickGarment } from "./helpers.js";
import { useDigitizerService, digitizeSquares, enterReshape, drawRectangle, darkBBox, stableNodePx, reshapeNodePx, serviceUp, skipReason } from "./reshape-helpers.js";

useDigitizerService();

const FIELD = ".hoop canvas";

test.beforeEach(async ({ page }) => {
  // A sweep is ~400 pointer moves; before the fix each one re-ran paint(),
  // which took the zoomed and hand-drawn sweeps past the 30 s default.
  test.setTimeout(180_000);
  await page.addInitScript(() => {
    window.__fieldRenders = 0;
    const fill = CanvasRenderingContext2D.prototype.fillRect;
    CanvasRenderingContext2D.prototype.fillRect = function (x, y, w, h) {
      const c = this.canvas;
      if (x === 0 && y === 0 && c && c.closest && c.closest(".hoop") && w >= c.clientWidth - 1 && h >= c.clientHeight - 1) {
        window.__fieldRenders++;
      }
      return fill.apply(this, arguments);
    };
  });
});

const cursorOf = (page) => page.locator(FIELD).evaluate((c) => c.style.cursor || "default");
const renders = (page) => page.evaluate(() => window.__fieldRenders);
const settle = (page) => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 500)))));

// One point per cursor the field shows over a cols x rows grid, kept only
// where a 1 px step keeps the same cursor (so the hover below stays in one
// region and nothing but the cursor is being asked about).
async function sweep(page, { cols = 26, rows = 16 } = {}) {
  const box = await page.locator(FIELD).boundingBox();
  const found = new Map();
  for (let j = 1; j < rows; j++) {
    for (let i = 1; i < cols; i++) {
      const pt = { x: box.x + (box.width * i) / cols, y: box.y + (box.height * j) / rows };
      await page.mouse.move(pt.x, pt.y);
      const c = await cursorOf(page);
      if (found.has(c)) continue;
      await page.mouse.move(pt.x + 1, pt.y);
      if ((await cursorOf(page)) === c) found.set(c, pt);
    }
  }
  return found;
}

async function hoverRenders(page, pt) {
  await page.mouse.move(pt.x, pt.y);
  await settle(page);
  const cursor = await cursorOf(page);
  await page.evaluate(() => { window.__fieldRenders = 0; });
  for (let i = 0; i < 8; i++) await page.mouse.move(pt.x + (i % 2), pt.y);
  await settle(page);
  expect(await cursorOf(page)).toBe(cursor);
  return { cursor, renders: await renders(page) };
}

// Hover every cursor the sweep found, plus the cursor at each of `extra`
// (points too small for the grid: a node, an anchor); returns { cursor: renders }.
async function hoverAll(page, mode, expectCursors, extra = []) {
  const found = await sweep(page);
  for (const pt of extra) {
    await page.mouse.move(pt.x, pt.y);
    const c = await cursorOf(page);
    if (!found.has(c)) found.set(c, pt);
  }
  for (const c of expectCursors) expect([...found.keys()], `${mode}: the sweep reaches the ${c} cursor (${extra.length} extra points)`).toContain(c);
  const out = {};
  for (const [c, pt] of found) out[c] = (await hoverRenders(page, pt)).renders;
  test.info().annotations.push({ type: "hover renders", description: `${mode}: ${JSON.stringify(out)}` });
  console.log(`[hover renders] ${mode}: ${JSON.stringify(out)}`);
  // HOVER_MEASURE_ONLY=1 reports without failing: how the before counts
  // in the PR were read off unfixed code.
  if (!process.env.HOVER_MEASURE_ONLY) for (const [c, n] of Object.entries(out)) expect(n, `${mode}, cursor ${c}: renders during 8 hover moves`).toBe(0);
  return out;
}

async function seed(page, elements, selectedIds) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.evaluate(([els, sel]) => {
    localStorage.clear();
    const id = "hover-1";
    localStorage.setItem("embstudio:p:" + id, JSON.stringify({
      version: 2, garmentId: "left_chest", selectedId: sel[0], selectedIds: sel,
      elements: els, fabricRgb: [235, 232, 223], hoopId: null,
    }));
    localStorage.setItem("embstudio:index", JSON.stringify([{ id, name: "Hover", updatedAt: Date.now() }]));
    localStorage.setItem("embstudio:current", id);
  }, [elements, selectedIds]);
  await page.reload();
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
  await settle(page);
}

const textEl = (id, text, offsetYMm) => ({
  id, type: "text", text, fontKey: "medium_font", colorRgb: [20, 20, 20], colorRanges: [],
  weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0, sizeMm: 60, offsetXMm: 0, offsetYMm,
});

test("select mode: the element's body, handles, rotate grip and the field around it, then zoomed in", async ({ page }) => {
  await seed(page, [textEl("e1", "HOVER", 0)], ["e1"]);
  await hoverAll(page, "select", ["move", "default"]);
  await page.getByRole("button", { name: "Zoom in" }).click();
  await settle(page);
  await hoverAll(page, "select, zoomed", ["grab"]);
});

test("multi-select: the group box, its corners and the field around it", async ({ page }) => {
  await seed(page, [textEl("e1", "ONE", -12), textEl("e2", "TWO", 12)], ["e1", "e2"]);
  await hoverAll(page, "multi-select", ["move"]);
});

test("hand-drawn: a drawn rectangle, then Edit points on it (its anchors and the marquee)", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await drawRectangle(page);
  await settle(page);
  await hoverAll(page, "hand-drawn", ["move"]);
  // A click inside the rectangle opens its popover; Edit points makes its
  // anchors grabbable and everywhere else a marquee.
  const box = await page.locator(FIELD).boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Edit points" }).click();
  await expect(page.locator(FIELD)).toHaveAttribute("data-reshape", "on");
  await settle(page);
  // The hand-drawn lane reports no node positions; its anchors are the
  // stitched rectangle's corners, found the way field-reshape-mode (g) finds
  // them (darkBBox).
  const bb = await darkBBox(page);
  const corners = [[bb.x0, bb.y0], [bb.x1, bb.y0], [bb.x1, bb.y1], [bb.x0, bb.y1]].map(([x, y]) => bb.css(x, y));
  await hoverAll(page, "hand-drawn, Edit points", ["crosshair", "grab"], corners);
});

test("digitized: shape outlines, then Reshape mode's points and marquee", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await settle(page);
  await hoverAll(page, "digitized", ["pointer"]);
  await enterReshape(page);
  await settle(page);
  await stableNodePx(page);
  await hoverAll(page, "reshape", ["crosshair", "grab"], await reshapeNodePx(page));
});
