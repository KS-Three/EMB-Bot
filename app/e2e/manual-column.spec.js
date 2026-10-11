// End-to-end for hand-drawn satin columns (2026-09-30 manual-digitizing gaps
// spec §6 and its 2026-10-01 amendment; plan
// docs/superpowers/plans/2026-10-01-manual-columns.md, Task 7). A column is an
// OPEN spine plus a drawn width; the engine sews satin between the two rails
// that width implies. No digitizer service is involved -- the hand-drawn lane
// stitches in the browser.
//
// Helpers are copied from manual-cutout.spec.js by this directory's
// convention (no imports across spec files): "dark" is thread only INSIDE the
// fabric, a row or column counts toward a box only with MIN_RUN dark pixels,
// every box is read after three agreeing reads, and the field's drag hint is
// closed by its own X before any canvas coordinate is read.
import { test, expect } from "@playwright/test";
import { pickGarment } from "./helpers.js";

const STATS = "span.stats";
const MIN_RUN = 12;
const WIDE = "Over 6.5 mm sewn — long satin stitches can snag. Consider a fill, or two columns.";

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

// "81×39 mm" out of the caption -> [81, 39].
const sizeOf = (stats) => stats.match(/(\d+)×(\d+) mm/).slice(1, 3).map(Number);
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
const rect = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

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

// The caption only — for reads with the popover open, whose selection chrome
// keeps the pixels moving.
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

async function changedFrom(page, prev) {
  await expect.poll(() => readStats(page), { timeout: 30_000 }).not.toBe(prev);
  const out = await settle(page);
  test.info().annotations.push({ type: "caption", description: `${prev} -> ${out.stats}` });
  return out;
}

// The dark box of the columns in [xMin, xMax] (canvas px; the whole fabric
// by default), counting a row or column with `minRun` dark pixels or more.
async function darkBBox(page, xMin = 0, xMax = 1e9, minRun = MIN_RUN) {
  return page.evaluate(([MIN_RUN, boxSrc, xMin, xMax]) => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const f = eval(boxSrc)(d, c.width, c.height);
    if (!f) return null;
    const xa = Math.max(f.x0, xMin), xb = Math.min(f.x1, xMax);
    const rows = new Uint32Array(c.height), cols = new Uint32Array(c.width);
    for (let y = f.y0; y <= f.y1; y++) for (let x = xa; x <= xb; x++) {
      const i = (y * c.width + x) * 4;
      if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) { rows[y]++; cols[x]++; }
    }
    let x0 = -1, x1 = -1, y0 = -1, y1 = -1;
    for (let x = 0; x < c.width; x++) if (cols[x] >= MIN_RUN) { if (x0 < 0) x0 = x; x1 = x; }
    for (let y = 0; y < c.height; y++) if (rows[y] >= MIN_RUN) { if (y0 < 0) y0 = y; y1 = y; }
    return x0 < 0 || y0 < 0 ? null : { x0, y0, x1, y1 };
  }, [minRun, FABRIC_BOX_SRC, Math.round(xMin), Math.round(xMax)]);
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

async function popoverAt(page, p) {
  await page.mouse.click(p.x, p.y);
  const dlg = page.getByRole("dialog");
  await expect(dlg).toBeVisible();
  return dlg;
}
async function closePopover(page) {
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
}

// The anchor of the SELECTED hand-drawn shape near canvas px `p`: the field's
// right-click offers Remove point only on one. Returns its CSS px, or null.
async function findAnchor(page, g, p) {
  const offs = [[0, 0]];
  for (const r of [3, 6, 9, 12]) for (const [dx, dy] of [[r, 0], [-r, 0], [0, r], [0, -r], [r, r], [-r, -r], [r, -r], [-r, r]]) offs.push([dx, dy]);
  for (const [dx, dy] of offs) {
    const c = g.css(p.x + dx / g.k, p.y + dy / g.k);
    await page.mouse.click(c.x, c.y, { button: "right" });
    await expect(page.locator(".fieldmenu")).toBeVisible();
    const has = (await page.locator(".fieldmenu button").filter({ hasText: "Remove point" }).count()) > 0;
    await page.keyboard.press("Escape");
    await expect(page.locator(".fieldmenu")).toBeHidden();
    if (has) return c;
  }
  return null;
}

// A straight column across the middle of the side canvas: its spine is the
// horizontal mid-line of the stitched box, so (centre x, centre y) is on it.
const SPINE = [[0.25, 0.5], [0.75, 0.5]];
const centreOf = (bb) => ({ x: (bb.x0 + bb.x1) / 2, y: (bb.y0 + bb.y1) / 2 });

// Draw the one column and return the settled design, drag hint closed.
async function oneColumn(page) {
  await toContent(page);
  await openDrawing(page);
  await setMode(page, "Column");
  await expect(page.locator(".mp-modehint")).toHaveText("Click along the middle of the stroke, then double-click to finish.");
  await drawPoly(page, SPINE);
  await expect(page.locator(".mp-shaperow")).toHaveCount(1);
  await expect(page.locator(".mp-shaperow").first()).toContainText("Shape 1 · Column");
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  await closeDragHint(page);
  return settle(page);
}

// The Width input and its note in the popover.
const popWidth = (dlg) => dlg.getByRole("spinbutton", { name: "Width" });
const popNote = (dlg) => dlg.locator(".shapepop-note");
const sewnOf = (note) => Number(note.match(/^Sews ([\d.]+) mm/)[1]);

test("(a) Column mode: a drawn spine sews, as a column, and its spine is thread", async ({ page }) => {
  test.setTimeout(120_000);
  const s = await oneColumn(page);
  expect(count(s.stats)).toBeGreaterThan(0);
  const mid = centreOf(s.bb);
  expect(await darkNear(page, mid.x, mid.y)).toBe(true);
  // A 4.0 mm column is far longer than it is wide.
  expect(s.bb.x1 - s.bb.x0).toBeGreaterThan(4 * (s.bb.y1 - s.bb.y0));
});

test("(b) the hoop popover: Width in mm with a sews-note; a new width re-sews; past 6.5 mm it warns and still sews", async ({ page }) => {
  test.setTimeout(120_000);
  const s = await oneColumn(page);
  const g = await geom(page);
  const mid = centreOf(s.bb);
  const dlg = await popoverAt(page, g.css(mid.x, mid.y));
  await expect(dlg).toHaveAttribute("aria-label", "Shape 1 · Column");
  await expect(popWidth(dlg)).toHaveValue(/^\d+(\.\d)?$/);
  await expect(popNote(dlg)).toHaveText(/^Sews \d+\.\d mm on .+\.$/);
  // Neither a stitch type nor a Cut out switch: a column is always satin.
  await expect(dlg.getByRole("combobox", { name: "Stitch type" })).toHaveCount(0);
  await expect(dlg.getByRole("switch", { name: "Cut out" })).toHaveCount(0);

  const before = await readStats(page);
  await popWidth(dlg).fill("6.0");
  await popWidth(dlg).press("Enter");
  const six = await statsChangedFrom(page, before);
  // A satin's stitch count follows its LENGTH (one cross per spacing step),
  // so a wider column re-sews at the same count — the caption's height grows.
  expect(sizeOf(six)[1]).toBeGreaterThan(sizeOf(before)[1]);
  await expect(popWidth(dlg)).toHaveValue("6");
  await expect(popNote(dlg)).toHaveText(/^Sews 6\.\d mm on /);

  await popWidth(dlg).fill("7.0");
  await popWidth(dlg).press("Enter");
  await expect(popNote(dlg)).toHaveText(WIDE);
  const seven = await statsChangedFrom(page, six);
  expect(count(seven)).toBeGreaterThan(0);
});

test("(c) ruling 12: scaling the design 1.5x scales the drawn width 1.5x; the sewn width stays drawn + the same pull comp", async ({ page }) => {
  test.setTimeout(150_000);
  const s = await oneColumn(page);
  // Read from the side panel's assign box (the column is selected there once
  // finished): the same numbers as the popover, through the same helper.
  const panelWidth = page.locator(".mp-assign .mp-width input");
  const panelNote = page.locator(".mp-assign .mp-width-note");
  const read = async () => ({ drawn: Number(await panelWidth.inputValue()), sewn: sewnOf(await panelNote.innerText()) });
  await expect(panelNote).toHaveText(/^Sews /);
  const w1 = await read();
  // ruling 9, through the fit the column actually got
  expect(w1.drawn).toBeCloseTo(4.0, 1);

  const size = page.locator(".sizepanel").getByRole("spinbutton", { name: "Width" });
  const was = Number(await size.inputValue());
  // 1.5x, not 2x: 4.0 mm doubled is 8.0, past the 6.5 mm warning, whose note
  // quotes no figure.
  await size.fill(String(1.5 * was));
  await size.press("Enter");
  await changedFrom(page, s.stats);
  await expect(panelWidth).not.toHaveValue(String(w1.drawn.toFixed(1)));
  const w2 = await read();

  expect(Math.abs(w2.drawn - 1.5 * w1.drawn)).toBeLessThanOrEqual(0.1);
  // One decimal on both sides, so the difference carries up to 0.1 of rounding.
  expect(Math.abs((w2.sewn - w2.drawn) - (w1.sewn - w1.drawn))).toBeLessThanOrEqual(0.1);
  test.info().annotations.push({ type: "ruling12", description: JSON.stringify({ w1, w2 }) });
});

test("(d)+(e) dragging a spine anchor re-sews the column and moves nothing else; a closed shape beside it keeps its own popover", async ({ page }) => {
  test.setTimeout(150_000);
  await toContent(page);
  await openDrawing(page);
  // Shape 1: a rectangle on the left, drawn first in Shape mode.
  await drawPoly(page, rect(0.05, 0.3, 0.25, 0.7));
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  const one = await settle(page);
  // Shape 2: a column on the right, its spine on the rectangle's mid-line.
  await setMode(page, "Column");
  await drawPoly(page, [[0.4, 0.5], [0.85, 0.5]]);
  await expect(page.locator(".mp-shaperow")).toHaveCount(2);
  await expect(page.locator(".mp-shaperow").nth(1)).toContainText("Shape 2 · Column");
  await closeDragHint(page);
  const both = await changedFrom(page, one.stats);

  // The rectangle alone, by a run far taller than the column is wide; the
  // side canvas's fractions map onto the hoop through it (0.2 wide).
  const RECT_RUN = 40;
  const rect0 = await darkBBox(page, 0, 1e9, RECT_RUN);
  expect(rect0).not.toBeNull();
  const unit = (rect0.x1 - rect0.x0) / 0.2;
  const at = (fx, fy) => ({ x: rect0.x0 + (fx - 0.05) * unit, y: rect0.y0 + (fy - 0.3) * unit * (400 / 600) });
  const gapX = at(0.325, 0.5).x;
  const rectBefore = await darkBBox(page, 0, gapX, RECT_RUN);

  // Select the column on the hoop (its popover opens; close it, the selection stays).
  const g0 = await geom(page);
  const colMid = { x: at(0.6, 0.5).x, y: (rect0.y0 + rect0.y1) / 2 };
  const dlg = await popoverAt(page, g0.css(colMid.x, colMid.y));
  await expect(dlg).toHaveAttribute("aria-label", "Shape 2 · Column");
  await closePopover(page);
  const ready = await settle(page);
  const g = await geom(page);
  const end = await findAnchor(page, g, { x: at(0.85, 0.5).x, y: (rect0.y0 + rect0.y1) / 2 });
  expect(end, "no anchor found at the column's right end").not.toBeNull();

  await page.mouse.move(end.x, end.y);
  await page.mouse.down();
  await page.mouse.move(end.x, end.y - 40, { steps: 12 });
  await page.mouse.up();
  const after = await changedFrom(page, ready.stats);
  expect(count(after.stats)).not.toBe(count(ready.stats));

  // The rectangle did not move (2 px).
  const rectAfter = await darkBBox(page, 0, gapX, RECT_RUN);
  expect(rectAfter).not.toBeNull();
  for (const k of ["x0", "y0", "x1", "y1"]) expect(Math.abs(rectAfter[k] - rectBefore[k]), k).toBeLessThanOrEqual(2);

  // (e) the closed shape is untouched by any of it: its popover still offers Fill/Satin.
  const rc = centreOf(rectAfter);
  const dlg2 = await popoverAt(page, (await geom(page)).css(rc.x, rc.y));
  await expect(dlg2).toHaveAttribute("aria-label", "Shape 1 · Fill");
  const type = dlg2.getByRole("combobox", { name: "Stitch type" });
  await expect(type).toHaveCount(1);
  await expect(type.locator("option")).toHaveText(["Fill", "Satin"]);
});
