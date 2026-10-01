// End-to-end for cut-outs (holes) in hand-drawn shapes (2026-09-30 manual-
// digitizing gaps spec §5, ruling 11): a shape marked Cut out sews nothing and
// removes its area from the smallest shape that contains it. No digitizer
// service is involved -- the hand-drawn lane stitches in the browser.
//
// How a nested pair is drawn. In the side canvas's SHAPE mode a click inside a
// finished shape SELECTS it (PR #104), so a shape cannot be started inside
// another; in HOLE mode a click always places a point. So the inner shape is
// always drawn in Hole mode -- it is born `Shape 2 · Cut out` -- and a test that
// needs it as an ordinary shape turns Cut out OFF from the side panel's assign
// box first. That OFF state is also how each test reads its "two shapes, no
// hole" stitch count.
//
// How the pixels are read: the same rules as field-node-edit.spec.js, whose
// helpers are copied here by this directory's convention (no imports across
// spec files). The stitches are black thread (the default colour); "dark" is
// thread only INSIDE the fabric (FABRIC_BOX_SRC), and a row or column counts
// toward a box only with MIN_RUN dark pixels, so the overlay's anchor-dot
// casings stay out of it. Every box is read after three agreeing reads.
//
// The field's drag hint ("Drag the design to move it ...") sits in flow above
// the hoop and the first press on the field dismisses it, which moves the
// canvas ~76 px. Each test closes it by its own X before reading any canvas
// coordinate.
import { test, expect } from "@playwright/test";
import { pickGarment } from "./helpers.js";

const STATS = "span.stats";
const MIN_RUN = 12;
const HOLD_HINT = "A cut-out has to stay inside its shape.";

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
const rect = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

// Close the field's drag hint by its own X, if it is up, so the canvas stops
// moving before any coordinate is read.
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

// The caption must first CHANGE from `prev`, then settle. Each change is kept
// as an annotation (the JSON reporter carries it), so a run records its counts.
async function changedFrom(page, prev) {
  await expect.poll(() => readStats(page), { timeout: 30_000 }).not.toBe(prev);
  const out = await settle(page);
  test.info().annotations.push({ type: "caption", description: `${prev} -> ${out.stats}` });
  return out;
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
    let x0 = -1, x1 = -1, y0 = -1, y1 = -1;
    for (let x = 0; x < c.width; x++) if (cols[x] >= MIN_RUN) { if (x0 < 0) x0 = x; x1 = x; }
    for (let y = 0; y < c.height; y++) if (rows[y] >= MIN_RUN) { if (y0 < 0) y0 = y; y1 = y; }
    return x0 < 0 || y0 < 0 ? null : { x0, y0, x1, y1 };
  }, [MIN_RUN, FABRIC_BOX_SRC]);
}

// Is there a dark (thread) pixel within `r` canvas px of (x, y)?
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

// The side panel's Cut out switch for the selected shape.
const panelSwitch = (page) => page.locator(".mp-assign").getByRole("switch", { name: "Cut out" });

// Shape 1 = a rectangle over 0.2..0.8 of the side canvas (Shape mode); Shape 2
// = `inner` drawn in Hole mode inside it, born a cut-out. Returns the three
// stitch counts: one shape alone, with the cut-out, and with Cut out turned OFF
// (two shapes, no hole). Leaves Cut out OFF, Shape mode back on, the drag hint
// closed, and the design settled.
async function nestedPair(page, inner) {
  await toContent(page);
  await openDrawing(page);
  await drawPoly(page, rect(0.2, 0.2, 0.8, 0.8));
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  await closeDragHint(page);
  const one = await settle(page);

  await setMode(page, "Hole");
  await drawPoly(page, inner);
  const rows = page.locator(".mp-shaperow");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(1)).toContainText("Shape 2 · Cut out");
  const cut = await changedFrom(page, one.stats);

  // Finishing selected Shape 2, so the assign box is its.
  await expect(panelSwitch(page)).toHaveAttribute("aria-checked", "true");
  await panelSwitch(page).click();
  await expect(panelSwitch(page)).toHaveAttribute("aria-checked", "false");
  await expect(rows.nth(1)).toContainText("Shape 2 · Fill");
  const two = await changedFrom(page, cut.stats);
  await setMode(page, "Shape");
  return { one, cut, two };
}

// Click (CSS px) on the hoop; returns the popover dialog that opens.
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

// Inner square 0.4..0.6 inside the 0.2..0.8 square: its middle is the middle
// of the stitched box, and its corners sit at 1/3 and 2/3 of it.
const INNER_SQUARE = rect(0.4, 0.4, 0.6, 0.6);
const centreOf = (bb) => ({ x: (bb.x0 + bb.x1) / 2, y: (bb.y0 + bb.y1) / 2 });

// (a) and (b) share the toggle on the hoop; each test reaches it on its own.
async function cutOnHoop(page, s) {
  const g = await geom(page);
  const mid = centreOf(s.bb);
  const dlg = await popoverAt(page, g.css(mid.x, mid.y));
  await expect(dlg).toHaveAttribute("aria-label", "Shape 2 · Fill");
  await dlg.getByRole("switch", { name: "Cut out" }).click();
  const after = await changedFrom(page, s.stats);
  return { dlg, after };
}

test("(a) Cut out on the hoop cuts: the count drops, the popover says what it cuts, the hole is bare fabric", async ({ page }) => {
  test.setTimeout(120_000);
  const { two } = await nestedPair(page, INNER_SQUARE);
  // Control: with Cut out off, the middle of the design is thread.
  const mid0 = centreOf(two.bb);
  expect(await darkNear(page, mid0.x, mid0.y)).toBe(true);

  const { dlg, after } = await cutOnHoop(page, two);
  expect(count(after.stats)).toBeLessThan(count(two.stats));
  await expect(dlg).toHaveAttribute("aria-label", "Shape 2 · Cut out");
  await expect(dlg.locator(".shapepop-head")).toContainText("Shape 2 · Cut out");
  await expect(dlg.locator(".shapepop-note")).toHaveText("Cuts Shape 1.");
  await expect(page.locator(".mp-shaperow").nth(1)).toContainText("Shape 2 · Cut out");

  // The hole's middle, read after the popover closes and the view settles: no
  // thread within 3 canvas px. The outer box is Shape 1's and did not shrink.
  await closePopover(page);
  const s = await settle(page);
  const mid = centreOf(s.bb);
  expect(await darkNear(page, mid.x, mid.y)).toBe(false);
  // ...while the parent's body, halfway between its edge and the hole, is thread.
  expect(await darkNear(page, s.bb.x0 + (s.bb.x1 - s.bb.x0) / 6, mid.y)).toBe(true);
});

test("(b) Cut out off gives the stitches back: the count returns to exactly the two-shape count", async ({ page }) => {
  test.setTimeout(120_000);
  const { two } = await nestedPair(page, INNER_SQUARE);
  const { dlg, after } = await cutOnHoop(page, two);
  expect(count(after.stats)).toBeLessThan(count(two.stats));
  await dlg.getByRole("switch", { name: "Cut out" }).click();
  const back = await changedFrom(page, after.stats);
  expect(back.stats).toBe(two.stats);
  await expect(dlg).toHaveAttribute("aria-label", "Shape 2 · Fill");
});

test("(c) a triangle cuts: a three-point cut-out lowers the count below the parent's own", async ({ page }) => {
  test.setTimeout(120_000);
  // Before 2026-10-01 the engine kept only holes of four or more points, so a
  // triangle cut-out sewed EXACTLY the parent's count. Strictly less is the fix.
  const { one, cut, two } = await nestedPair(page, [[0.5, 0.35], [0.65, 0.62], [0.35, 0.62]]);
  expect(count(cut.stats)).toBeLessThan(count(one.stats));
  expect(count(two.stats)).toBeGreaterThan(count(one.stats));
  // And from the hoop, the same way as (a).
  const { dlg, after } = await cutOnHoop(page, two);
  expect(count(after.stats)).toBeLessThan(count(two.stats));
  expect(after.stats).toBe(cut.stats);
  await expect(dlg.locator(".shapepop-note")).toHaveText("Cuts Shape 1.");
});

test("(d) a cut-out's anchor dragged far outside its shape holds: the hint shows, it still cuts, the parent does not move", async ({ page }) => {
  test.setTimeout(150_000);
  const { one, two } = await nestedPair(page, INNER_SQUARE);
  // Back on, from the side panel (Shape 2 is still the selected row).
  await panelSwitch(page).click();
  await expect(panelSwitch(page)).toHaveAttribute("aria-checked", "true");
  const on = await changedFrom(page, two.stats);
  expect(count(on.stats)).toBeLessThan(count(two.stats));

  // Select the cut-out on the hoop (a click in the hole opens its popover),
  // close the popover, and read the box AFTER the selection's re-fit.
  const g0 = await geom(page);
  const m0 = centreOf(on.bb);
  const dlg = await popoverAt(page, g0.css(m0.x, m0.y));
  await expect(dlg).toHaveAttribute("aria-label", "Shape 2 · Cut out");
  await closePopover(page);
  const before = await settle(page);
  const g = await geom(page);
  const W = before.bb.x1 - before.bb.x0, H = before.bb.y1 - before.bb.y0;
  const tr = await findAnchor(page, g, { x: before.bb.x0 + (2 * W) / 3, y: before.bb.y0 + H / 3 });
  expect(tr, "no anchor found at the cut-out's top-right corner").not.toBeNull();

  await page.mouse.move(tr.x, tr.y);
  await page.mouse.down();
  await page.mouse.move(tr.x + 300, tr.y - 300, { steps: 30 });
  // The hint shows while the drag is held.
  await expect(page.getByTestId("shape-edit-error")).toHaveText(HOLD_HINT);
  await page.mouse.up();

  const after = await changedFrom(page, before.stats);
  // It still cuts: below the two-shape count, and below the parent ALONE --
  // a cut-out let outside would cut nothing and sew exactly `one`...
  expect(count(after.stats)).toBeLessThan(count(two.stats));
  expect(count(after.stats)).toBeLessThan(count(one.stats));
  // ...and the hole is still where it was: its old middle is bare fabric. (This
  // replaced four reads of the whole dark box, which an ESCAPED cut-out would
  // not have changed either — it sews nothing. An escaped one would put thread
  // back here; a held one keeps every corner but the dragged one, and the
  // dragged one only moved outward, so the old middle stays inside the hole.)
  const mHole = centreOf(before.bb);
  expect(await darkNear(page, mHole.x, mHole.y)).toBe(false);
  // Still Shape 1's cut-out.
  const m1 = centreOf(after.bb);
  const dlg2 = await popoverAt(page, (await geom(page)).css(m1.x, m1.y));
  await expect(dlg2).toHaveAttribute("aria-label", "Shape 2 · Cut out");
  await expect(dlg2.locator(".shapepop-note")).toHaveText("Cuts Shape 1.");
});

test("(e) Hole mode: a shape drawn inside another is born a cut-out and the count drops", async ({ page }) => {
  test.setTimeout(120_000);
  await toContent(page);
  await openDrawing(page);
  await drawPoly(page, rect(0.2, 0.2, 0.8, 0.8));
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  const one = await settle(page);
  await setMode(page, "Hole");
  await expect(page.locator(".mp-modehint")).toHaveText("Draw inside a shape — it cuts that shape.");
  await drawPoly(page, INNER_SQUARE);
  const rows = page.locator(".mp-shaperow");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(1)).toHaveText("Shape 2 · Cut out");
  const cut = await changedFrom(page, one.stats);
  expect(count(cut.stats)).toBeLessThan(count(one.stats));
  // The assign box (Shape 2 is selected) says what it cuts.
  await expect(page.locator(".mp-assign .mp-cutnote")).toHaveText("Cuts Shape 1.");
});

// "81×39 mm" out of the caption -> [81, 39].
const sizeOf = (stats) => stats.match(/(\d+)×(\d+) mm/).slice(1, 3).map(Number);

// The dark box of the columns left of `xMax` only (canvas px) — Shape 1's own
// box while Shape 2 still sews to its right.
async function darkBBoxLeftOf(page, xMax) {
  return page.evaluate(([MIN_RUN, boxSrc, xMax]) => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const f = eval(boxSrc)(d, c.width, c.height);
    if (!f) return null;
    const x1f = Math.min(f.x1, xMax);
    const rows = new Uint32Array(c.height), cols = new Uint32Array(c.width);
    for (let y = f.y0; y <= f.y1; y++) for (let x = f.x0; x <= x1f; x++) {
      const i = (y * c.width + x) * 4;
      if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) { rows[y]++; cols[x]++; }
    }
    let x0 = -1, x1 = -1, y0 = -1, y1 = -1;
    for (let x = 0; x < c.width; x++) if (cols[x] >= MIN_RUN) { if (x0 < 0) x0 = x; x1 = x; }
    for (let y = 0; y < c.height; y++) if (rows[y] >= MIN_RUN) { if (y0 < 0) y0 = y; y1 = y; }
    return x0 < 0 || y0 < 0 ? null : { x0, y0, x1, y1 };
  }, [MIN_RUN, FABRIC_BOX_SRC, Math.round(xMax)]);
}

test("(f) a cut-out outside every shape says it cuts nothing, and switching it on the hoop moves nothing else", async ({ page }) => {
  test.setTimeout(120_000);
  await toContent(page);
  await openDrawing(page);
  await drawPoly(page, rect(0.15, 0.25, 0.45, 0.75));
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  const one = await settle(page);
  await drawPoly(page, rect(0.55, 0.25, 0.85, 0.75));
  await expect(page.locator(".mp-shaperow")).toHaveCount(2);
  await closeDragHint(page);
  const both = await changedFrom(page, one.stats);
  // The right half of the joint box is Shape 2; the gap between them is its
  // middle (0.45..0.55 of 0.15..0.85).
  const g = await geom(page);
  const gapX = (both.bb.x0 + both.bb.x1) / 2;
  const p = g.css(both.bb.x0 + 0.8 * (both.bb.x1 - both.bb.x0), (both.bb.y0 + both.bb.y1) / 2);
  const dlg = await popoverAt(page, p);
  await expect(dlg).toHaveAttribute("aria-label", "Shape 2 · Fill");
  // Shape 1's own box, read with the popover open and the view settled.
  const ready = await settle(page);
  expect(ready.stats).toBe(both.stats);
  const s1Before = await darkBBoxLeftOf(page, gapX);
  expect(s1Before).not.toBeNull();

  await dlg.getByRole("switch", { name: "Cut out" }).click();
  await expect(dlg).toHaveAttribute("aria-label", "Shape 2 · Cut out");
  await expect(dlg.locator(".shapepop-note")).toHaveText("Not inside a shape — cuts nothing.");
  const after = await changedFrom(page, both.stats);
  // It sews nothing: the count drops by Shape 2's stitches...
  expect(count(after.stats)).toBeLessThan(count(both.stats));
  // ...but nothing else moves (the hoop's re-fit rule covers the switch). Until
  // the fix wave the element re-fitted to Shape 1 alone and it jumped from
  // 81×39 to 81×91 mm — the one-shape size. The height is Shape 1's, held.
  expect(sizeOf(after.stats)).not.toEqual(sizeOf(one.stats));
  expect(Math.abs(sizeOf(after.stats)[1] - sizeOf(both.stats)[1])).toBeLessThanOrEqual(1);
  const s1After = await darkBBoxLeftOf(page, gapX);
  expect(s1After).not.toBeNull();
  for (const k of ["x0", "y0", "x1", "y1"]) expect(Math.abs(s1After[k] - s1Before[k]), k).toBeLessThanOrEqual(2);
});
