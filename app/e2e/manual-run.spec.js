// End to end for hand-drawn lines — open runs (2026-09-30 manual-digitizing
// gaps spec §7; plan docs/superpowers/plans/2026-10-11-manual-open-runs.md,
// Task 7). A line is an OPEN path that sews a running stitch along itself (a
// bean by default), and converts to a satin column and back (ruling 8). No
// digitizer service is involved -- the hand-drawn lane stitches in the browser.
//
// Helpers are copied from manual-column.spec.js by this directory's
// convention (no imports across spec files): "dark" is thread only INSIDE the
// fabric, a row or column counts toward a box only with MIN_RUN dark pixels,
// every box is read after three agreeing reads, and the field's drag hint is
// closed by its own X before any canvas coordinate is read.
import { test, expect } from "@playwright/test";
import { pickGarment } from "./helpers.js";

const STATS = "span.stats";
const MIN_RUN = 12;

const FABRIC_BOX_SRC = `(function (d, w, h) {
  let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4;
    if (d[i + 3] > 200 && d[i] > 150 && d[i + 1] > 150 && d[i + 2] > 150) {
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
  }
  if (x1 < 0) return null;
  const tx = Math.round((x1 - x0) * 0.03), ty = Math.round((y1 - y0) * 0.03);
  return { x0: x0 + tx, x1: x1 - tx, y0: y0 + ty, y1: y1 - ty };
})`;

const count = (stats) => Number(stats.match(/([\d,]+) stitches/)[1].replace(/,/g, ""));

async function toContent(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
}

async function openDrawing(page) {
  await page.locator(".hoop canvas").click({ button: "right" });
  await page.locator(".fieldmenu button").filter({ hasText: "Draw shapes" }).click();
  await expect(page.locator(".mp-canvas")).toBeVisible();
}

async function setMode(page, label) {
  const btn = page.getByRole("group", { name: "Drawing mode" }).getByRole("button", { name: label, exact: true });
  await btn.click();
  await expect(btn).toHaveAttribute("aria-pressed", "true");
}

// Click the given points (fractions of the side canvas's displayed box), then
// Enter to finish.
async function drawPoly(page, pts) {
  const mp = page.locator(".mp-canvas");
  const box = await mp.boundingBox();
  for (const [fx, fy] of pts) await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
  await mp.focus();
  await page.keyboard.press("Enter");
}

async function closeDragHint(page) {
  const x = page.getByRole("button", { name: "Dismiss hint" });
  if (await x.count()) {
    await x.first().click();
    await expect(x).toHaveCount(0);
  }
}

async function readStats(page) {
  return (await page.locator(STATS).count()) ? page.locator(STATS).innerText() : null;
}

async function statsChangedFrom(page, prev) {
  await expect.poll(() => readStats(page), { timeout: 30_000 }).not.toBe(prev);
  let last = null;
  await expect.poll(async () => {
    const a = await readStats(page);
    await page.waitForTimeout(400);
    const b = await readStats(page);
    last = b;
    return a === b;
  }, { timeout: 30_000 }).toBe(true);
  test.info().annotations.push({ type: "caption", description: `${prev} -> ${last}` });
  return last;
}

async function darkBBox(page) {
  return page.evaluate(([MIN_RUN, boxSrc]) => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const f = eval(boxSrc)(d, c.width, c.height);
    if (!f) return null;
    const rows = new Uint32Array(c.height), cols = new Uint32Array(c.width);
    for (let y = f.y0; y <= f.y1; y++) for (let x = f.x0; x <= f.x1; x++) {
      const i = (y * c.width + x) * 4;
      if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) { rows[y]++; cols[x]++; }
    }
    // A thin line has few dark pixels per column; count a column with any,
    // and a row by the run threshold (the line is long horizontally).
    let x0 = -1, x1 = -1, y0 = -1, y1 = -1;
    for (let x = 0; x < c.width; x++) if (cols[x] >= 1) { if (x0 < 0) x0 = x; x1 = x; }
    for (let y = 0; y < c.height; y++) if (rows[y] >= MIN_RUN) { if (y0 < 0) y0 = y; y1 = y; }
    return x0 < 0 || y0 < 0 ? null : { x0, y0, x1, y1 };
  }, [MIN_RUN, FABRIC_BOX_SRC]);
}

async function darkNear(page, x, y, r = 3) {
  return page.evaluate(([x, y, r, boxSrc]) => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const f = eval(boxSrc)(d, c.width, c.height);
    if (!f) return false;
    for (let yy = Math.max(f.y0, y - r); yy <= Math.min(f.y1, y + r); yy++) {
      for (let xx = Math.max(f.x0, x - r); xx <= Math.min(f.x1, x + r); xx++) {
        const i = (yy * c.width + xx) * 4;
        if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) return true;
      }
    }
    return false;
  }, [Math.round(x), Math.round(y), r, FABRIC_BOX_SRC]);
}

async function geom(page) {
  const hb = await page.locator(".hoop canvas").boundingBox();
  const cw = await page.evaluate(() => document.querySelector(".hoop canvas").width);
  const k = hb.width / cw;
  return { hb, k, css: (x, y) => ({ x: hb.x + x * k, y: hb.y + y * k }) };
}

async function settle(page) {
  let out = null;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) {
      reads.push({ stats: await readStats(page), bb: await darkBBox(page) });
      await page.waitForTimeout(250);
    }
    out = reads[0];
    const j = JSON.stringify(reads[0]);
    return out.stats !== null && out.bb !== null && reads.every((r) => JSON.stringify(r) === j);
  }, { timeout: 30_000 }).toBe(true);
  return out;
}

// A straight line across the middle of the side canvas: the stitched box's
// centre is on it.
const LINE = [[0.25, 0.5], [0.75, 0.5]];
const centreOf = (bb) => ({ x: (bb.x0 + bb.x1) / 2, y: (bb.y0 + bb.y1) / 2 });

async function oneLine(page) {
  await toContent(page);
  await openDrawing(page);
  await setMode(page, "Line");
  await expect(page.locator(".mp-modehint")).toHaveText("Click along the line, then double-click to finish.");
  await drawPoly(page, LINE);
  await expect(page.locator(".mp-shaperow")).toHaveCount(1);
  await expect(page.locator(".mp-shaperow").first()).toContainText("Shape 1 · Line");
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  await closeDragHint(page);
  return settle(page);
}

test("(a) Line mode: a drawn line sews, as a thin run, and the line is thread", async ({ page }) => {
  test.setTimeout(120_000);
  const s = await oneLine(page);
  expect(count(s.stats)).toBeGreaterThan(0);
  const mid = centreOf(s.bb);
  expect(await darkNear(page, mid.x, mid.y)).toBe(true);
  // A run is a line, not an area: far wider than it is tall.
  expect(s.bb.x1 - s.bb.x0).toBeGreaterThan(10 * Math.max(1, s.bb.y1 - s.bb.y0));
});

test("(b)+(c) the hoop popover: passes re-sew the line; Make it a column, then Make it a line, gives the same line back", async ({ page }) => {
  test.setTimeout(150_000);
  const s = await oneLine(page);
  const bean = count(s.stats);
  const g = await geom(page);
  const mid = centreOf(s.bb);
  await page.mouse.click(g.css(mid.x, mid.y).x, g.css(mid.x, mid.y).y);
  const dlg = page.getByRole("dialog");
  await expect(dlg).toBeVisible();
  await expect(dlg).toHaveAttribute("aria-label", "Shape 1 · Line");
  const passes = dlg.getByRole("combobox", { name: "Passes" });
  await expect(passes).toHaveValue("3");
  await expect(dlg.getByRole("spinbutton", { name: "Stitch length" })).toHaveValue("0.73");
  // a line is never satin and never a cut-out
  await expect(dlg.getByRole("combobox", { name: "Stitch type" })).toHaveCount(0);
  await expect(dlg.getByRole("switch", { name: "Cut out" })).toHaveCount(0);

  await passes.selectOption("1");
  const single = count(await statsChangedFrom(page, s.stats));
  const ratio = single / bean;
  test.info().annotations.push({ type: "passes", description: `bean ${bean}, single ${single}, ratio ${ratio.toFixed(3)}` });
  expect(ratio).toBeGreaterThan(0.25);
  expect(ratio).toBeLessThan(0.45);

  // (c) ruling 8: to a column — 4.0 mm wide at the fit it is in — and back.
  const before = await readStats(page);
  await dlg.getByRole("button", { name: "Make it a column" }).click();
  await expect(dlg).toHaveAttribute("aria-label", "Shape 1 · Column");
  await statsChangedFrom(page, before);
  await expect(page.locator(".mp-shaperow").first()).toContainText("Shape 1 · Column");
  await expect(dlg.getByRole("spinbutton", { name: "Width" })).toHaveValue("4");
  const asColumn = await readStats(page);
  await dlg.getByRole("button", { name: "Make it a line" }).click();
  await expect(dlg).toHaveAttribute("aria-label", "Shape 1 · Line");
  const back = await statsChangedFrom(page, asColumn);
  await expect(page.locator(".mp-shaperow").first()).toContainText("Shape 1 · Line");
  // the spine came back as drawn and the passes went back to the default bean
  expect(count(back)).toBe(bean);
});

test("screenshot: a bent line on the hoop", async ({ page }) => {
  test.skip(!process.env.EMB_SHOTS, "set EMB_SHOTS=1 to write docs/screens/manual-run-2026-10-11.png");
  test.setTimeout(120_000);
  await toContent(page);
  await openDrawing(page);
  await setMode(page, "Line");
  await drawPoly(page, [[0.1, 0.65], [0.3, 0.3], [0.5, 0.65], [0.7, 0.3], [0.9, 0.6]]);
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  await closeDragHint(page);
  // a bent line has no long dark row for settle()'s box: wait on the caption
  await statsChangedFrom(page, null);
  await page.screenshot({ path: "../docs/screens/manual-run-2026-10-11.png" });
});
