// End-to-end for node editing of a hand-drawn shape ON THE FIELD (2026-09-29
// field-node-edit spec §7). EmbroideryField has no component spec, so this file
// carries the gestures: drag an anchor, bow a segment with its handle, click an
// edge to insert an anchor, focus an anchor and Delete it (down to the
// three-point floor), the invariance of a neighbouring shape, that a drag
// starting on an edge does nothing, and that the shape popover can be dragged
// out of the way. No digitizer service is involved -- the hand-drawn lane
// stitches in the browser.
//
// How the pixels are read. The design's stitches are black thread (the default
// colour), so the shape's box is the bounding box of the DARK pixels on the
// hoop canvas (every channel < 80). The overlay's amber anchor dots
// (255,214,64) and green handle dots (64,200,120) are never dark, but their
// 1 px casing is drawn in near-black at 0.75 alpha, so a bare "any dark pixel"
// box would carry a ring around each dot. A row or column therefore only counts
// when it holds MIN_RUN dark pixels: a dot's ring puts at most a handful in one
// row, a filled shape hundreds.
//
// Selecting a shape re-fits the hoop's view slightly (measured 2026-09-29, see
// manual-trace-import.spec.js), so every pixel box that a gesture aims at is
// read AFTER select + Escape and only once three consecutive reads agree.
import { test, expect } from "@playwright/test";
import { pickGarment } from "./helpers.js";

const STATS = "span.stats";
const MIN_RUN = 12;

// The canvas outside the hoop is a dark surround since 2026-09-30 (every
// channel < 80, so it would read as one giant stitch box), so "dark" is thread
// only INSIDE the fabric: both samplers below find the fabric first (the
// bounding box of the pale pixels, pulled in 3% a side so the hoop's rounded
// corners stay out) and read within it. Same rule as field-chrome.spec.js's
// ink test and field-shape-popover.spec.js's samplers.
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

async function toContent(page) {
  await page.goto("/");
  await pickGarment(page, "Tote");
}

// Draw a rectangle on ManualPanel's canvas: four clicks at fractions of the
// canvas's displayed box, then Enter. `x0`/`x1` are the left/right as fractions
// of the canvas width; `open: false` skips the field menu when the drawing panel
// is already up. (Same helper as field-shape-popover.spec.js, which keeps its
// own copy by this directory's convention.)
async function drawRectangle(page, { x0 = 0.25, x1 = 0.75, open = true } = {}) {
  if (open) {
    await page.locator(".hoop canvas").click({ button: "right" });
    await page.locator(".fieldmenu button").filter({ hasText: "Draw shapes" }).click();
  }
  const mp = page.locator(".mp-canvas");
  await expect(mp).toBeVisible();
  const box = await mp.boundingBox();
  for (const [fx, fy] of [[x0, 0.25], [x1, 0.25], [x1, 0.75], [x0, 0.75]]) {
    await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
  }
  await mp.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
}

// The dark (stitch) bounding box on the hoop canvas, in canvas px, optionally
// restricted to the columns [xa, xb]; null when nothing qualifies.
async function darkBBox(page, xa = 0, xb = Infinity) {
  return page.evaluate(([xa, xb, MIN_RUN, boxSrc]) => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const f = eval(boxSrc)(d, c.width, c.height);
    if (!f) return null;
    const rows = new Uint32Array(c.height), cols = new Uint32Array(c.width);
    for (let y = f.y0; y <= f.y1; y++) for (let x = f.x0; x <= f.x1; x++) {
      if (x < xa || x > xb) continue;
      const i = (y * c.width + x) * 4;
      if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) { rows[y]++; cols[x]++; }
    }
    let x0 = -1, x1 = -1, y0 = -1, y1 = -1;
    for (let x = 0; x < c.width; x++) if (cols[x] >= MIN_RUN) { if (x0 < 0) x0 = x; x1 = x; }
    for (let y = 0; y < c.height; y++) if (rows[y] >= MIN_RUN) { if (y0 < 0) y0 = y; y1 = y; }
    return x0 < 0 || y0 < 0 ? null : { x0, y0, x1, y1 };
  }, [xa, xb, MIN_RUN, FABRIC_BOX_SRC]);
}

// Is there a dark pixel within `r` canvas px of (x, y)? A window rather than one
// pixel: stitch rows leave sub-pixel gaps.
async function darkNear(page, x, y, r = 2) {
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

// Canvas px -> page CSS px: {hb, k, css(x, y)}.
async function geom(page) {
  const hb = await page.locator(".hoop canvas").boundingBox();
  const cw = await page.evaluate(() => document.querySelector(".hoop canvas").width);
  const k = hb.width / cw;
  return { hb, k, css: (x, y) => ({ x: hb.x + x * k, y: hb.y + y * k }) };
}

// Three reads, 250 ms apart, of the caption and the dark box (the whole canvas,
// or [xa, xb]) that all agree -- the repo's rule for a baseline. Returns the
// agreed {stats, bb}.
async function settle(page, xa = 0, xb = Infinity) {
  let out = null;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) {
      const stats = (await page.locator(STATS).count()) ? await page.locator(STATS).innerText() : null;
      reads.push({ stats, bb: await darkBBox(page, xa, xb) });
      await page.waitForTimeout(250);
    }
    out = reads[0];
    const j = JSON.stringify(reads[0]);
    return out.stats !== null && out.bb !== null && reads.every((r) => JSON.stringify(r) === j);
  }, { timeout: 30_000 }).toBe(true);
  return out;
}

// Click inside a shape (CSS px), then close the popover it opens: the shape is
// left SELECTED, which is what arms its anchors and handles.
async function selectAt(page, x, y) {
  await page.mouse.click(x, y);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
}

// A press at (x0,y0), a move to (x1,y1) in 8 steps, a release. Steps, because
// the drag has a 4 px dead zone and a single jump is not a drag the field's
// pointermove would see in stages.
async function drag(page, from, to) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(to.x, to.y, { steps: 8 });
  await page.mouse.up();
}

// Draw one rectangle, select it, and return its settled state. Everything the
// gestures aim at is derived from this box, read AFTER the re-fit.
async function drawAndSelect(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await drawRectangle(page);
  const first = await settle(page);
  const g0 = await geom(page);
  const c = g0.css((first.bb.x0 + first.bb.x1) / 2, (first.bb.y0 + first.bb.y1) / 2);
  await selectAt(page, c.x, c.y);
  return settle(page);
}

// Does a right-click at (x, y) offer "Remove point"? The item exists only when
// the pointer is on an ANCHOR of the selected hand-drawn shape, so it is the
// field's own statement of "there is an anchor here". The menu is closed again.
async function offersRemovePoint(page, x, y) {
  await page.mouse.click(x, y, { button: "right" });
  await expect(page.locator(".fieldmenu")).toBeVisible();
  const has = (await page.locator(".fieldmenu button").filter({ hasText: "Remove point" }).count()) > 0;
  await page.keyboard.press("Escape");
  await expect(page.locator(".fieldmenu")).toBeHidden();
  return has;
}

test("(a) dragging an anchor moves that corner only: the caption changes, the box grows toward the drag", async ({ page }) => {
  const before = await drawAndSelect(page);
  const g = await geom(page);
  const tl = g.css(before.bb.x0, before.bb.y0);
  await drag(page, tl, { x: tl.x - 40, y: tl.y - 30 });
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 20_000 }).not.toBe(before.stats);
  const after = await settle(page);
  const g2 = await geom(page);
  // The drag was (-40, -30) CSS px. Once past the 4 px dead zone the drag is
  // RELATIVE to the grab point, so the anchor takes the full delta — it does
  // not trail the pointer by the dead zone. 25 px each way is a loose floor
  // that says "the corner followed", not a measured lag.
  expect((before.bb.x0 - after.bb.x0) * g2.k).toBeGreaterThanOrEqual(25);
  expect((before.bb.y0 - after.bb.y0) * g2.k).toBeGreaterThanOrEqual(25);
  // ...and only that corner moved: the opposite corner stays where it was.
  expect(Math.abs(after.bb.x1 - before.bb.x1)).toBeLessThanOrEqual(2);
  expect(Math.abs(after.bb.y1 - before.bb.y1)).toBeLessThanOrEqual(2);
});

test("(b) dragging a segment's handle bows the edge: the caption changes and stitches cover ground the straight edge did not", async ({ page }) => {
  const before = await drawAndSelect(page);
  const g = await geom(page);
  const midX = (before.bb.x0 + before.bb.x1) / 2;
  // 20 CSS px above the old top edge, at mid-x: bare fabric until the edge bows.
  const probe = { x: midX, y: before.bb.y0 - 20 / g.k };
  expect(await darkNear(page, probe.x, probe.y, 3)).toBe(false);
  const handle = g.css(midX, before.bb.y0);
  await drag(page, handle, { x: handle.x, y: handle.y - 40 });
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 20_000 }).not.toBe(before.stats);
  const after = await settle(page);
  const g2 = await geom(page);
  // The probe is a fixed canvas pixel: the view did not move under it.
  expect(Math.abs(g2.k - g.k)).toBeLessThan(1e-9);
  expect(await darkNear(page, probe.x, probe.y, 3)).toBe(true);
  // The bow is upward only: the sides and the bottom stay put.
  expect(after.bb.y0).toBeLessThan(before.bb.y0 - 20 / g.k);
  expect(Math.abs(after.bb.x0 - before.bb.x0)).toBeLessThanOrEqual(2);
  expect(Math.abs(after.bb.y1 - before.bb.y1)).toBeLessThanOrEqual(2);
});

test("(c) clicking an edge inserts an anchor there: Remove point is offered on the spot afterwards, not before", async ({ page }) => {
  const before = await drawAndSelect(page);
  const g = await geom(page);
  const midX = (before.bb.x0 + before.bb.x1) / 2;
  // 30 CSS px left of the top edge's midpoint (whose own dot is the handle), on
  // the edge.
  const spot = g.css(midX - 30 / g.k, before.bb.y0);
  // Control: nothing there yet.
  expect(await offersRemovePoint(page, spot.x, spot.y)).toBe(false);
  await page.mouse.click(spot.x, spot.y);
  // The insert commits at release; poll until the anchor is there (a value that
  // CHANGES from false), never a fixed sleep.
  await expect.poll(() => offersRemovePoint(page, spot.x, spot.y), { timeout: 20_000 }).toBe(true);
  // An edge click opens no popover and does not move the shape.
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const after = await settle(page);
  expect(Math.abs(after.bb.x0 - before.bb.x0)).toBeLessThanOrEqual(2);
  expect(Math.abs(after.bb.x1 - before.bb.x1)).toBeLessThanOrEqual(2);
  expect(Math.abs(after.bb.y1 - before.bb.y1)).toBeLessThanOrEqual(2);
});

test("(d) a focused anchor is removed by Delete; at three anchors Delete refuses and says why", async ({ page }) => {
  const before = await drawAndSelect(page);
  const g = await geom(page);
  const { x0, y0, x1, y1 } = before.bb;
  // The corner region just inside the top-right anchor is stitched now...
  const inside = { x: x1 - 8, y: y0 + 8 };
  expect(await darkNear(page, inside.x, inside.y, 2)).toBe(true);

  // Press the top-right anchor and release without moving: that FOCUSES it.
  const tr = g.css(x1, y0);
  await page.mouse.click(tr.x, tr.y);
  await page.keyboard.press("Delete");
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 20_000 }).not.toBe(before.stats);
  const tri = await settle(page);
  // ...and after Delete the corner is cut off by a diagonal from the top-left
  // to the bottom-right anchor: the same pixel is bare fabric while the far
  // side of the diagonal (near the bottom-left anchor) is still stitched.
  expect(await darkNear(page, inside.x, inside.y, 2)).toBe(false);
  expect(await darkNear(page, x0 + 8, y1 - 8, 2)).toBe(true);
  // The bottom-left corner is a full right angle, so its column and row read
  // exactly; the other two corners are now acute tips, which the run threshold
  // in darkBBox trims by a few tens of canvas px (a tip is thinner than
  // MIN_RUN pixels for its last stretch) -- they may not move, only shrink.
  expect(Math.abs(tri.bb.x0 - x0)).toBeLessThanOrEqual(2);
  expect(Math.abs(tri.bb.y1 - y1)).toBeLessThanOrEqual(2);
  expect(tri.bb.x1).toBeLessThanOrEqual(x1 + 2);
  expect(tri.bb.x1).toBeGreaterThanOrEqual(x1 - 40);
  expect(tri.bb.y0).toBeGreaterThanOrEqual(y0 - 2);
  expect(tri.bb.y0).toBeLessThanOrEqual(y0 + 40);
  // The shape survived the point (one row, one selection), no popover.
  await expect(page.locator(".mp-shaperow")).toHaveCount(1);
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Three anchors left: focus the bottom-right one (at its original corner), Delete once more.
  const br = g.css(x1, y1); // the anchors did not move; the tip of the triangle reads short
  await page.mouse.click(br.x, br.y);
  await page.keyboard.press("Delete");
  const err = page.getByTestId("shape-edit-error");
  await expect(err).toHaveText("A shape needs at least 3 points.");
  // Nothing was removed: pressing the anchor again clears the message (it
  // replaces the caption while it shows) and the caption is the triangle's.
  await page.mouse.click(br.x, br.y);
  await expect(err).toHaveCount(0);
  const kept = await settle(page);
  expect(kept.stats).toBe(tri.stats);
  expect(kept.bb).toEqual(tri.bb);
  await expect(page.locator(".mp-shaperow")).toHaveCount(1);
});

test("(e) invariance: dragging one shape's anchor outward leaves its neighbour's stitches where they were", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await drawRectangle(page, { x0: 0.15, x1: 0.45 });
  await drawRectangle(page, { x0: 0.55, x1: 0.85, open: false });
  await expect(page.locator(".mp-shaperow")).toHaveCount(2);
  const both = await settle(page);
  // The two rectangles are symmetric about the canvas's middle, so the middle
  // of their joint box lies in the gap between them.
  const mid = (both.bb.x0 + both.bb.x1) / 2;
  const g0 = await geom(page);
  const left0 = await darkBBox(page, 0, mid);
  const cLeft = g0.css((left0.x0 + left0.x1) / 2, (left0.y0 + left0.y1) / 2);
  await selectAt(page, cLeft.x, cLeft.y);
  await expect(page.locator(".mp-shaperow").first()).toHaveClass(/sel/);

  // Re-read after the re-fit, both halves, settled.
  const leftBefore = await settle(page, 0, mid);
  const rightBefore = await settle(page, mid + 1);
  const g = await geom(page);
  const tl = g.css(leftBefore.bb.x0, leftBefore.bb.y0);
  await drag(page, tl, { x: tl.x - 40, y: tl.y });
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 20_000 }).not.toBe(rightBefore.stats);

  const leftAfter = await settle(page, 0, mid);
  const rightAfter = await settle(page, mid + 1);
  const g2 = await geom(page);
  // The edited shape really grew leftward (so this is not a test of nothing)...
  expect((leftBefore.bb.x0 - leftAfter.bb.x0) * g2.k).toBeGreaterThanOrEqual(25);
  // ...and the other one did not move: same box to within a pixel.
  for (const key of ["x0", "y0", "x1", "y1"]) {
    expect(Math.abs(rightAfter.bb[key] - rightBefore.bb[key]), "right shape " + key).toBeLessThanOrEqual(1);
  }
});

test("(f) a drag that starts on an edge does nothing: no edit, no move, no popover", async ({ page }) => {
  const before = await drawAndSelect(page);
  const g = await geom(page);
  const midX = (before.bb.x0 + before.bb.x1) / 2;
  const onEdge = g.css(midX + 30 / g.k, before.bb.y0);
  await drag(page, onEdge, { x: onEdge.x, y: onEdge.y - 40 });
  await expect(page.getByRole("dialog")).toHaveCount(0);
  // Three equal reads AFTER the release: any late restitch has landed.
  const after = await settle(page);
  expect(after.stats).toBe(before.stats);
  expect(after.bb).toEqual(before.bb);
  // Guard against a press that simply missed the outline (which would drag the
  // whole element and fail the box check above, but would also pass if it
  // landed on nothing): the same spot, clicked, DOES insert an anchor -- so it
  // is an edge hit.
  expect(await offersRemovePoint(page, onEdge.x, onEdge.y)).toBe(false);
  await page.mouse.click(onEdge.x, onEdge.y);
  await expect.poll(() => offersRemovePoint(page, onEdge.x, onEdge.y), { timeout: 20_000 }).toBe(true);
});

test("(g) the shape popover is dragged by its header, stays open, and follows the pointer", async ({ page }) => {
  const before = await drawAndSelect(page);
  const g = await geom(page);
  // Reopen the popover on the (still selected) shape: a click inside its body.
  const c = g.css(before.bb.x0 + 30 / g.k, before.bb.y0 + 30 / g.k);
  await page.mouse.click(c.x, c.y);
  const dlg = page.getByRole("dialog", { name: /^Shape 1/ });
  await expect(dlg).toBeVisible();
  const box0 = await dlg.boundingBox();
  const head = await dlg.locator(".shapepop-head").boundingBox();
  const from = { x: head.x + head.width / 2, y: head.y + head.height / 2 };
  await drag(page, from, { x: from.x + 150, y: from.y + 80 });
  // A press on the header is not an outside press: it stays open, same shape.
  await expect(dlg).toBeVisible();
  const box1 = await dlg.boundingBox();
  expect(box1.x - box0.x).toBeGreaterThanOrEqual(147);
  expect(box1.x - box0.x).toBeLessThanOrEqual(153);
  expect(box1.y - box0.y).toBeGreaterThanOrEqual(77);
  expect(box1.y - box0.y).toBeLessThanOrEqual(83);
  // Moving the popover edited nothing.
  const after = await settle(page);
  expect(after.stats).toBe(before.stats);
  expect(after.bb).toEqual(before.bb);
  // ...and a plain press-and-release on the header does not close it either.
  const head2 = await dlg.locator(".shapepop-head").boundingBox();
  await page.mouse.click(head2.x + head2.width / 2, head2.y + head2.height / 2);
  await expect(dlg).toBeVisible();
});

test("(h) a node dragged far past the placement box stops at it: nothing else rescales", async ({ page }) => {
  // Kent's ruling 2026-09-29. Tote's placement is 8 x 8 in = 203.2 mm, centred.
  // The engine clamps the WHOLE design's scale to that box, so a node let past
  // it would shrink every other point; the drag stops at the box edge instead.
  const before = await drawAndSelect(page);
  const g = await geom(page);
  const tr = g.css(before.bb.x1, before.bb.y0);
  await drag(page, tr, { x: tr.x + 400, y: tr.y - 400 });
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 20_000 }).not.toBe(before.stats);
  const after = await settle(page);
  const g2 = await geom(page);
  // On a failure the number alone says nothing about WHERE the box was, and
  // this test has failed on CI with geometry no local run reproduces — so
  // every assertion below carries both boxes, both captions and the canvas
  // box in its message.
  const where = `before=${JSON.stringify(before)} after=${JSON.stringify(after)} canvas=${JSON.stringify(g2.hb)} k=${g2.k}`;
  // The opposite (bottom-left) corner did not move: no rescale.
  //
  // Allowance 6 canvas px, not 2. The box is read with the shape SELECTED,
  // so its edge carries the selection ring's dark casing, whose width pulses
  // 3.4 -> 5.2 px; how many of its antialiased outer columns cross the
  // "dark" threshold differs by renderer. Measured 2026-09-30 on one head:
  // every number identical between CI (Chrome 151) and a local Chromium
  // except this edge -- 4 px on CI, 1 px locally, three runs each. The
  // rescale this guards against moved the untouched edge 10.2 mm (~35 px
  // here), so 6 px still catches it by a factor of six.
  expect(Math.abs(after.bb.x0 - before.bb.x0), `left edge moved: ${where}`).toBeLessThanOrEqual(6);
  expect(Math.abs(after.bb.y1 - before.bb.y1), `bottom edge moved: ${where}`).toBeLessThanOrEqual(6);
  // The dragged corner DID move (it stopped at the box, it did not refuse the drag)...
  expect(Math.hypot(after.bb.x1 - before.bb.x1, after.bb.y0 - before.bb.y0) * g2.k, `dragged corner: ${where}`).toBeGreaterThanOrEqual(40);
  // ...and the design still fits the 203.2 mm box (the caption rounds to whole mm).
  const m = after.stats.match(/(\d+)×(\d+) mm/);
  expect(m).not.toBeNull();
  expect(Number(m[1])).toBeLessThanOrEqual(203.7);
  expect(Number(m[2])).toBeLessThanOrEqual(203.7);
});
