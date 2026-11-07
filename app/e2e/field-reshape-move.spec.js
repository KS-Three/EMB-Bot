// Reshape mode, part 3: Move shape (m1-m10). Split out of field-reshape-mode.spec.js
// 2026-11-07; helpers in reshape-helpers.js.
import { test, expect } from "@playwright/test";
import { pickGarment, uploadArtwork, runDigitize, pinDigitizeConfig, openAdvanced } from "./helpers.js";
import fs, { existsSync, readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { useDigitizerService, readDigitized, ringOf, movedVertices, blackSquareCorners, drag, digitizeSquares, clickLeftSquare, enterReshape, selectedCount, restitched, settle, digitizeHoled, readHoled, selectGreenShape, __dirname, serviceUp, skipReason } from "./reshape-helpers.js";

// SERVICE_URL (the digitizer service at 127.0.0.1:8721): this file needs it, so
// playwright.config.js runs it in the serial step.
useDigitizerService();
// ---- Move shape (2026-11-05 spec) -----------------------------------------
// One shape (shell, holes, nodes) translates as a unit; its stitches regenerate
// at the new place through the normal restitch after the commit. Fill pixels are
// read with strict thresholds (the outline's casing is a translucent grey that a
// loose "dark" test would count, and it moves LIVE, long before any restitch).

const TWO_BLACK_PNG = path.join(__dirname, "fixtures", "two-black-squares.png");

// Bounding box (page CSS px) of solid fill pixels: `kind` "black" or "red", rows and
// columns with at least 12 hits only, optionally limited to canvas x in [xa, xb].
async function fillBBox(page, kind, xa = 0, xb = Infinity) {
  const r = await page.evaluate(([kind, xa, xb]) => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const hit = kind === "black"
      ? (i) => d[i] < 14 && d[i + 1] < 14 && d[i + 2] < 14
      : (i) => d[i] > 150 && d[i + 1] < 40 && d[i + 2] < 40;
    const rows = new Uint32Array(c.height), cols = new Uint32Array(c.width);
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) {
      if (x < xa || x > xb) continue;
      const i = (y * c.width + x) * 4;
      if (d[i + 3] > 200 && hit(i)) { rows[y]++; cols[x]++; }
    }
    let x0 = -1, x1 = -1, y0 = -1, y1 = -1;
    for (let x = 0; x < c.width; x++) if (cols[x] >= 12) { if (x0 < 0) x0 = x; x1 = x; }
    for (let y = 0; y < c.height; y++) if (rows[y] >= 12) { if (y0 < 0) y0 = y; y1 = y; }
    return x0 < 0 || y0 < 0 ? null : { x0, y0, x1, y1, cw: c.width };
  }, [kind, xa, xb]);
  if (!r) return null;
  const hb = await page.locator(".hoop canvas").boundingBox();
  const k = hb.width / r.cw;
  return { x0: r.x0 * k, y0: r.y0 * k, x1: r.x1 * k, y1: r.y1 * k, cw: r.cw };
}
const canvasWidthPx = (page) => page.evaluate(() => document.querySelector(".hoop canvas").width);

// Two reads 150 ms apart that agree (the page re-lays out once the popover is gone).
async function settledFill(page, kind, xa = 0, xb = Infinity) {
  let prev = null, cur = await fillBBox(page, kind, xa, xb);
  await expect.poll(async () => {
    prev = cur;
    await page.waitForTimeout(150);
    cur = await fillBBox(page, kind, xa, xb);
    return !!cur && JSON.stringify(prev) === JSON.stringify(cur);
  }, { timeout: 10_000 }).toBe(true);
  return cur;
}

async function moveDelta(page) {
  const t = await page.locator(".hoop canvas").getAttribute("data-shape-move-delta");
  const [dx, dy] = (t || "0,0").split(",").map(Number);
  return { dx, dy };
}

// Select the left square, press "Move shape" in its popover, wait for the layout.
async function startMove(page, { similar = false } = {}) {
  await clickLeftSquare(page);
  if (similar) await page.getByRole("dialog").getByRole("checkbox", { name: /Apply to all similar shapes/ }).check();
  await page.getByRole("dialog").getByRole("button", { name: "Move shape" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "on");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.locator(".hoop canvas").focus();
}

// A drag by (dx, dy) CSS px from a point low in the canvas (anywhere starts the drag).
async function moveDrag(page, dxPx, dyPx = 0) {
  const box = await page.locator(".hoop canvas").boundingBox();
  const from = { x: box.x + box.width * 0.5, y: box.y + box.height * 0.9 };
  await drag(page, from, { x: from.x + dxPx, y: from.y + dyPx });
}

// Drag so the live delta reads `mm` to the right; returns px per mm.
async function moveRightMm(page, mm) {
  await moveDrag(page, 100);
  const first = await moveDelta(page);
  expect(first.dx, "the first drag moved the outline").toBeGreaterThan(1);
  const k = 100 / first.dx;
  await moveDrag(page, (mm - first.dx) * k);
  return k;
}

// The drawn Done / Discard buttons, from the canvas' own attribute.
async function moveButton(page, which) {
  const hb = await page.locator(".hoop canvas").boundingBox();
  const btns = JSON.parse(await page.locator(".hoop canvas").getAttribute("data-shape-move-btns"));
  return { x: hb.x + btns[which][0], y: hb.y + btns[which][1] };
}

const boundaryEntries = async (page) => Object.entries((await readDigitized(page)).overrides).filter(([, v]) => v.boundary_override);

async function waitMoved(page, kind, was, dxPx, xa = 0, xb = Infinity) {
  // The stitches follow after the commit's idle pause; kick the run if it doesn't start.
  const moved = async () => { const b = await fillBBox(page, kind, xa, xb); return !!b && Math.abs(b.x0 - was.x0) > dxPx * 0.5; };
  const ok = await expect.poll(moved, { timeout: 10_000 }).toBe(true).then(() => true, () => false);
  if (!ok) { await runDigitize(page); await expect.poll(moved, { timeout: 120_000 }).toBe(true); }
  return settledFill(page, kind, xa, xb);
}

test("(m1) Move shape: drag the black square 10 mm right, Done -> its stitches land +10 mm, the red square stays, one restitch", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await startMove(page);
  const black0 = await settledFill(page, "black");
  const red0 = await settledFill(page, "red");
  const k = await moveRightMm(page, 10);
  const d = await moveDelta(page);
  expect(d.dx).toBeCloseTo(10, 0);
  expect(Math.abs(d.dy)).toBeLessThan(0.1);
  expect(await boundaryEntries(page), "nothing is committed mid-move").toHaveLength(0);
  const b = await moveButton(page, "done");
  await page.mouse.click(b.x, b.y);
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "off");
  expect(await boundaryEntries(page), "ONE shape carries a boundary_override").toHaveLength(1);
  const black1 = await waitMoved(page, "black", black0, 10 * k);
  const red1 = await settledFill(page, "red");
  // The move grew the element's bbox, and the restitched design keeps the frame
  // it was centred on, so ABSOLUTE positions hold: black +10 mm, red unmoved.
  const blackDx = (black1.x0 - black0.x0) / k, redDx = (red1.x0 - red0.x0) / k;
  console.log(`m1 on-screen shift mm: black dx=${blackDx.toFixed(2)} dy=${((black1.y0 - black0.y0) / k).toFixed(2)}, red dx=${redDx.toFixed(2)} dy=${((red1.y0 - red0.y0) / k).toFixed(2)}`);
  expect(Math.abs((black1.x1 - black1.x0) - (black0.x1 - black0.x0)) / k, "same scale").toBeLessThan(0.6);
  expect(Math.abs(blackDx - 10), "black moved +10 mm on screen").toBeLessThan(0.3);
  expect(Math.abs(redDx), "the red square did not move").toBeLessThan(0.3);
  expect(Math.abs((black1.y0 - black0.y0) / k), "black: no vertical drift").toBeLessThan(0.3);
  expect(Math.abs((red1.y0 - red0.y0) / k), "red: no vertical drift").toBeLessThan(0.3);
});

test("(m2) Esc after a drag: nothing is patched, nothing restitches, the outline is back", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  await startMove(page);
  const black0 = await settledFill(page, "black");
  await moveDrag(page, 120);
  expect((await moveDelta(page)).dx).toBeGreaterThan(1);
  await page.keyboard.press("Escape");
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "off");
  await page.waitForTimeout(2500);                                   // longer than the restitch pause
  expect(await boundaryEntries(page)).toHaveLength(0);
  expect(await page.locator(".dgp-stats").innerText()).toBe(before);
  const black1 = await settledFill(page, "black");
  expect(black1).toEqual(black0);
});

test("(m3) ten ArrowRight presses then Done = 1.0 mm; one Shift+ArrowRight = 1 mm", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await startMove(page);
  for (let i = 0; i < 10; i++) await page.keyboard.press("ArrowRight");
  await expect.poll(async () => (await moveDelta(page)).dx).toBeCloseTo(1.0, 1);
  expect(await boundaryEntries(page), "arrows commit nothing by themselves").toHaveLength(0);
  const b = await moveButton(page, "done");
  await page.mouse.click(b.x, b.y);
  await expect.poll(async () => (await boundaryEntries(page)).length).toBe(1);
  const [[sid, entry]] = await boundaryEntries(page);
  const r = await readDigitized(page);
  const was = r.shapes.find((s) => s.id === sid).outline;
  const mv = movedVertices(was, entry.boundary_override, 1e-9);
  expect(mv.length, "every vertex moved").toBe(ringOf(was).length);
  for (const v of mv) expect(Math.abs(Math.hypot(v.dx, v.dy) - 1.0)).toBeLessThan(0.05);
  // Shift+Arrow is 1 mm: committed this time, read after the stitches have followed.
  const first = entry.boundary_override;
  await settledFill(page, "black");
  await startMove(page);
  await page.keyboard.press("Shift+ArrowRight");
  await expect.poll(async () => (await moveDelta(page)).dx).toBeCloseTo(1.0, 1);
  const b2 = await moveButton(page, "done");
  await page.mouse.click(b2.x, b2.y);
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "off");
  await settledFill(page, "black");
  await expect.poll(async () => {
    const e2 = (await readDigitized(page)).overrides[sid];
    const m = e2 && e2.boundary_override ? movedVertices(first, e2.boundary_override, 1e-9) : null;
    return !!m && m.length === ringOf(first).length && m.every((v) => Math.abs(Math.hypot(v.dx, v.dy) - 1.0) < 0.05);
  }, { timeout: 15_000 }).toBe(true);
});

test("(m4) holed fixture: shell and hole move together, the hole keeps its place in the shell", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeHoled(page);
  const g = await selectGreenShape(page);
  await page.mouse.click(g.shell.tl.x + 4 * g.k + 3, (g.shell.tl.y + g.hole.bl.y) / 2);
  await expect(page.getByRole("dialog", { name: /^Thread #/ })).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Move shape" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "on");
  await page.locator(".hoop canvas").focus();
  await moveDrag(page, 80, 30);
  await page.keyboard.press("Enter");
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "off");
  const after = await readHoled(page);
  const [sid, entry] = Object.entries(after.overrides).find(([, v]) => v.boundary_override);
  expect(entry.holes_override, "the hole travels with the shell").toHaveLength(1);
  const was = after.shapes.find((s) => s.id === sid);
  const centre = (ring) => {
    const pts = ringOf(ring);
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
  };
  const [sx0, sy0] = centre(was.outline), [hx0, hy0] = centre(was.holes[0]);
  const [sx1, sy1] = centre(entry.boundary_override), [hx1, hy1] = centre(entry.holes_override[0]);
  expect(Math.hypot(sx1 - sx0, sy1 - sy0), "the shell moved").toBeGreaterThan(1);
  expect(Math.abs((hx1 - sx1) - (hx0 - sx0))).toBeLessThan(0.1);
  expect(Math.abs((hy1 - sy1) - (hy0 - sy0))).toBeLessThan(0.1);
});

test("(m5) 'edit all similar shapes' ticked: only the grabbed square moves", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await pinDigitizeConfig(page, { border_by_size: false });
  await uploadArtwork(page, TWO_BLACK_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await settle(page);
  await startMove(page, { similar: true });
  const cw = await canvasWidthPx(page);
  const hb = await page.locator(".hoop canvas").boundingBox();
  const mid = cw / 2;
  const left0 = await settledFill(page, "black", 0, mid);
  const right0 = await settledFill(page, "black", mid, Infinity);
  const k = await moveRightMm(page, 4);
  await page.keyboard.press("Enter");
  expect(await boundaryEntries(page), "only the grabbed shape is overridden").toHaveLength(1);
  const gap = 4 * k * (cw / hb.width);
  await waitMoved(page, "black", left0, 4 * k, 0, mid + gap);
  const right1 = await settledFill(page, "black", mid + gap, Infinity);
  // Re-centring shifts both; if the tick had moved the look-alike too, the gap would not change.
  const left1 = await settledFill(page, "black", 0, mid);
  const gapChange = ((right1.x0 - left1.x0) - (right0.x0 - left0.x0)) / k;
  expect(gapChange, "the gap closed by the grabbed square's 4 mm only").toBeGreaterThan(-4.3);
  expect(gapChange).toBeLessThan(-3.7);
});

test("(m6) Done with no drag: no patch, the stats do not move", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  await startMove(page);
  const b = await moveButton(page, "done");
  await page.mouse.click(b.x, b.y);
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "off");
  for (let i = 0; i < 3; i++) { expect(await page.locator(".dgp-stats").innerText()).toBe(before); await page.waitForTimeout(900); }
  expect(await boundaryEntries(page)).toHaveLength(0);
});

test("(m7) Done, wait for the restitch, Undo (twice): the square is back where it was", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await startMove(page);
  const black0 = await settledFill(page, "black");
  const k = await moveRightMm(page, 8);
  await page.keyboard.press("Enter");
  expect(await boundaryEntries(page)).toHaveLength(1);
  await waitMoved(page, "black", black0, 8 * k);
  const undo = page.getByRole("button", { name: "Undo", exact: true });
  await undo.click();                                                // the restitch's own step
  await expect.poll(async () => (await boundaryEntries(page)).length, { timeout: 5_000 }).toBe(1);
  await undo.click();                                                // the move: ONE step
  await expect.poll(async () => (await boundaryEntries(page)).length, { timeout: 5_000 }).toBe(0);
  const back = async () => { const b = await fillBBox(page, "black"); return !!b && Math.abs(b.x0 - black0.x0) / k < 0.3; };
  const ok = await expect.poll(back, { timeout: 8_000 }).toBe(true).then(() => true, () => false);
  if (!ok) { await runDigitize(page); await expect.poll(back, { timeout: 120_000 }).toBe(true); }
});

test("(m8) Delete / Backspace mid-move delete nothing: Done commits ONE boundary_override, the shape stays, one Undo step takes it back", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await startMove(page);
  const black0 = await settledFill(page, "black");
  const k = await moveRightMm(page, 5);
  await page.keyboard.press("Delete");
  await page.keyboard.press("Backspace");
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "on");
  expect((await moveDelta(page)).dx, "the move is still pending").toBeGreaterThan(4.5);
  const b = await moveButton(page, "done");
  await page.mouse.click(b.x, b.y);
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "off");
  expect(await boundaryEntries(page), "exactly one boundary_override").toHaveLength(1);
  const deleted = await page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const parsed = JSON.parse(localStorage.getItem("embstudio:p:" + id));
    const proj = parsed.project || parsed;
    const el = (proj.elements || []).find((e) => e.type === "digitized");
    return (el.deletedShapeIds || []).length;
  });
  expect(deleted, "no shape was deleted").toBe(0);
  await waitMoved(page, "black", black0, 5 * k);
  const undo = page.getByRole("button", { name: "Undo", exact: true });
  await undo.click();                                                // the restitch's own step
  await expect.poll(async () => (await boundaryEntries(page)).length, { timeout: 5_000 }).toBe(1);
  await undo.click();                                                // the move: ONE step
  await expect.poll(async () => (await boundaryEntries(page)).length, { timeout: 5_000 }).toBe(0);
  const back = async () => { const bb = await fillBBox(page, "black"); return !!bb && Math.abs(bb.x0 - black0.x0) / k < 0.3; };
  const ok = await expect.poll(back, { timeout: 8_000 }).toBe(true).then(() => true, () => false);
  if (!ok) { await runDigitize(page); await expect.poll(back, { timeout: 120_000 }).toBe(true); }
});

// Wait for a committed edit's stitches to land: on their own, or by the run button once it says
// the edit is waiting (restitched() kicks too early and loses a second edit).
async function landed(page, caption) {
  await expect.poll(async () => {
    if ((await page.locator(".dgp-stats").innerText()) !== caption) return true;
    const run = page.locator(".dgp-run");
    if ((await run.isEnabled()) && /Changed since the last run/.test(await page.locator("body").innerText())) await run.click().catch(() => {});
    return false;
  }, { timeout: 120_000, intervals: [3000] }).toBe(true);
}

// A node dragged outside the old bbox grows the element, and the restitch must
// not slide the OTHER shape: the same frame hold as a Move (2026-11-06).
test("(m9) Reshape: a corner dragged ~5 mm above the old bbox -> the red square stays put", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  await enterReshape(page);
  const black0 = await settledFill(page, "black");
  const red0 = await settledFill(page, "red");
  const { tr } = await blackSquareCorners(page);
  // No click-to-select first: the app counts two presses on one spot inside 450 ms (and 6 px)
  // as a double-click, and a double-click on a node toggles corner <-> smooth instead of
  // dragging it (countPress / isDoublePress, EmbroideryField.svelte). A click followed at once
  // by this drag's press was that pair whenever the click's own work finished fast: it left a
  // 232-vertex smoothed ring whose top rose 5.4999 mm, the same figure on every red run
  // (main 2026-11-06, runs 42270700421 / 42315302056). Pressing an unselected node makes it
  // THE selection, so the drag alone selects it, with no time window to race.
  const up = 40;                                                       // CSS px, well past the old top edge
  await drag(page, tr, { x: tr.x, y: tr.y - up });
  await expect.poll(() => selectedCount(page)).toBe(1);
  await expect.poll(async () => (await boundaryEntries(page)).length).toBe(1);
  // Fail fast on a drag that did not register: the committed shell's top must have risen.
  const widthMm = Number((/(\d+)×(\d+) mm/.exec(before) || [])[1]);
  expect(widthMm, "the caption names the design width").toBeGreaterThan(5);
  const pxPerMm = (red0.x1 - black0.x0) / widthMm;
  const [[sid, entry]] = await boundaryEntries(page);
  const orig = (await readDigitized(page)).shapes.find((s) => s.id === sid).outline;
  const minY = (ring) => Math.min(...ringOf(ring).map((p) => p[1]));
  const rose = minY(orig) - minY(entry.boundary_override);
  expect(ringOf(entry.boundary_override), "a corner drag keeps the 4 corners (a smoothed ring means the press was read as a double-click)").toHaveLength(4);
  expect(rose, "the dragged corner raised the shell top by about the drag (mm)").toBeGreaterThan(up * 0.7 / pxPerMm);
  await landed(page, before);
  await expect.poll(async () => { const b = await fillBBox(page, "black"); return !!b && b.y0 < black0.y0 - up * 0.5; }, { timeout: 120_000 }).toBe(true);
  const red1 = await settledFill(page, "red");
  const mm = (a, b) => Math.abs(a - b) / pxPerMm;
  expect(mm(red1.x0, red0.x0), "red left").toBeLessThan(0.5);
  // The service lays fill rows on a grid anchored to the art box, which grew: the first
  // row can sit up to one row off. The placement itself (x above, the bottom edge) is exact.
  expect(mm(red1.y0, red0.y0), "red top").toBeLessThan(1.0);
  expect(mm(red1.y1, red0.y1), "red bottom").toBeLessThan(0.5);
  const black1 = await settledFill(page, "black");
  expect(mm(black1.x0, black0.x0), "black left edge did not move").toBeLessThan(0.5);
  expect(mm(black1.y0, black0.y0), "black top grew upward").toBeGreaterThan(up * 0.5 / pxPerMm);
});

test("(m10) a second Move after the first: the red square still has not moved", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(400_000);
  await digitizeSquares(page);
  let red0 = null;
  let black = null;
  let k = 0;
  for (let n = 0; n < 2; n++) {
    const caption = await page.locator(".dgp-stats").innerText();
    await startMove(page);
    // Baselines are read in the move layout, as (m1) does: the page lays out differently before it.
    if (!red0) red0 = await settledFill(page, "red");
    const was = await settledFill(page, "black");
    k = await moveRightMm(page, 6);
    const b = await moveButton(page, "done");
    await page.mouse.click(b.x, b.y);
    await expect(page.locator(".hoop canvas")).toHaveAttribute("data-shape-move", "off");
    // The new stitches land: on their own, or by the run button once it says the edit is waiting.
    await expect.poll(async () => {
      if ((await page.locator(".dgp-stats").innerText()) !== caption) return true;
      const run = page.locator(".dgp-run");
      if ((await run.isEnabled()) && /Changed since the last run/.test(await page.locator("body").innerText())) await run.click().catch(() => {});
      return false;
    }, { timeout: 120_000, intervals: [3000] }).toBe(true);
    black = await settledFill(page, "black");
    expect((black.x0 - was.x0) / k, "this move: black went right by 6 mm").toBeGreaterThan(5.5);
    expect((black.x0 - was.x0) / k).toBeLessThan(6.5);
  }
  const red2 = await settledFill(page, "red");
  expect(Math.abs(red2.x0 - red0.x0) / k, "red x after two moves").toBeLessThan(0.3);
  expect(Math.abs(red2.y0 - red0.y0) / k, "red y after two moves").toBeLessThan(0.3);
});
