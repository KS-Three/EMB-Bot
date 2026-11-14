// End-to-end for Reshape mode (2026-11-03 node-reshape spec, sections 4 and 7):
// "Edit points" in the shape popover turns on a mode where a bare drag is a
// marquee over the points of EVERY shape of the element, a drag on a selected
// point moves them all, the arrows nudge them 0.1 mm, and Delete removes them —
// each gesture one patch and one undo step. Both lanes:
//
//   digitized  (a) one node drag outside the mode moves that node only and the
//                  stitches follow; (b) marquee two neighbouring vertices of
//                  one square, ArrowRight x3: both moved 0.3 mm, three undo
//                  steps; (c) Delete removes a selected point and refuses at
//                  three; (f) outside the mode a bare drag inside the shape
//                  still moves the element.
//   hand-drawn (g) marquee two anchors of a drawn rectangle, drag: the caption
//                  changes and a neighbour's stitches stay.
//
// The digitized tests run against the REAL digitizer service (same bootstrap
// as digitize-boundary-edit.spec.js) and read what was committed out of the
// project the Studio saves to localStorage, so a number here is the number on
// the wire. Where the canvas has to be aimed at, the points are found the way a
// person finds them: the amber dots the overlay draws (a node is a filled dot,
// a line is two pixels wide, so a 5 x 5 all-amber window is a node).
// (Split 2026-11-07: sparse-node + add-hole tests are in field-reshape-nodes.spec.js, move-shape tests in field-reshape-move.spec.js; shared helpers in reshape-helpers.js.)
import { test, expect } from "@playwright/test";
import { pickGarment, uploadArtwork, runDigitize, pinDigitizeConfig, openAdvanced } from "./helpers.js";
import fs, { existsSync, readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { useDigitizerService, readDigitized, ringOf, movedVertices, blackSquareCorners, statsText, drag, digitizeSquares, clickLeftSquare, enterReshape, selectedCount, restitched, drawRectangle, readManual, darkBBox, settle, digitizeHoled, greenSquareAndHole, pixelAt, readHoled, selectGreenShape, stripButton, amberNodes, kinds, outsideTwoSpansIsOriginal, __dirname, serviceUp, skipReason, ART_PNG } from "./reshape-helpers.js";

// SERVICE_URL (the digitizer service at 127.0.0.1:8721): this file needs it, so
// playwright.config.js runs it in the serial step.
useDigitizerService();

test("(a) one node drag moves that node only, and the stitches follow", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  await clickLeftSquare(page);
  await page.keyboard.press("Escape");                       // selected, popover out of the way
  // The square's top-right corner (the left corners sit under the selection box's handles).
  const { tr } = await blackSquareCorners(page);
  await drag(page, tr, { x: tr.x + 22, y: tr.y - 16 });
  const read = await readDigitized(page);
  const edited = Object.entries(read.overrides).filter(([, v]) => v.boundary_override);
  expect(edited, "exactly one shape carries a boundary edit").toHaveLength(1);
  const [sid, entry] = edited[0];
  const orig = read.shapes.find((s) => s.id === sid).outline;
  const moved = movedVertices(orig, entry.boundary_override);
  expect(moved, "same point count").not.toBeNull();
  expect(moved, "exactly one vertex moved").toHaveLength(1);
  // Sparse nodes (I5): the square's four corners are nodes, a corner-to-corner
  // span is its chord, so the dragged quadrilateral keeps its 4 vertices; the
  // seeds ride in the same entry.
  expect(ringOf(entry.boundary_override), "I5: still a 4-vertex quadrilateral").toHaveLength(4);
  expect(entry.nodes && entry.nodes.shell.map((n) => n.kind)).toEqual(["corner", "corner", "corner", "corner"]);
  await restitched(page, before);
});

test("(b) Edit points: a marquee over two neighbouring vertices, ArrowRight x3 -> both moved 0.3 mm, three undo steps", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await enterReshape(page);
  // The square's top two corners: a marquee 14 px round both.
  const { tl: p, tr: q } = await blackSquareCorners(page);
  const pad = 14;
  await drag(page, { x: p.x - pad, y: p.y - pad }, { x: q.x + pad, y: q.y + pad });
  await expect.poll(() => selectedCount(page)).toBe(2);

  const read0 = await readDigitized(page);
  const baseOverrides = JSON.stringify(read0.overrides);
  const canvas = page.locator(".hoop canvas");
  await canvas.focus();
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press("ArrowRight");
    await expect.poll(async () => JSON.stringify((await readDigitized(page)).overrides)).not.toBe(i === 0 ? baseOverrides : "");
  }
  const read = await readDigitized(page);
  const edited = Object.entries(read.overrides).filter(([, v]) => v.boundary_override);
  expect(edited).toHaveLength(1);
  const [sid, entry] = edited[0];
  const moved = movedVertices(read.shapes.find((s) => s.id === sid).outline, entry.boundary_override);
  expect(moved, "exactly the two selected vertices differ").toHaveLength(2);
  for (const m of moved) {
    expect(m.dx).toBeCloseTo(0.3, 2);       // 3 x 0.1 mm, along +x
    expect(m.dy).toBeCloseTo(0, 6);
  }

  // Three presses are three undo steps: each Undo takes 0.1 mm back.
  const undo = page.getByRole("button", { name: "Undo", exact: true });
  const xOf = async () => {
    const r = await readDigitized(page);
    const e = Object.entries(r.overrides).find(([, v]) => v.boundary_override);
    if (!e) return 0;
    const mv = movedVertices(r.shapes.find((s) => s.id === e[0]).outline, e[1].boundary_override);
    return mv && mv.length ? mv[0].dx : 0;
  };
  for (const want of [0.2, 0.1, 0]) {
    await undo.click();
    await expect.poll(xOf).toBeCloseTo(want, 2);
  }
});

test("(c) Delete removes a selected point; at three points it refuses and removes nothing", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await enterReshape(page);
  const { tl, tr } = await blackSquareCorners(page);
  // Click the top-right corner: selects that point.
  await page.mouse.click(tr.x, tr.y);
  await expect.poll(() => selectedCount(page)).toBe(1);
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Delete");
  await expect.poll(async () => {
    const r = await readDigitized(page);
    const e = Object.entries(r.overrides).find(([, v]) => v.boundary_override);
    return e ? ringOf(e[1].boundary_override).length : null;
  }).toBe(3);                                                   // a square minus a corner: a triangle
  await expect.poll(() => selectedCount(page)).toBe(0);

  // Now at three: select one vertex of the triangle and Delete -> refused.
  await page.mouse.click(tl.x, tl.y);
  await expect.poll(() => selectedCount(page)).toBe(1);
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Delete");
  await expect(page.getByTestId("shape-edit-error")).toHaveText("A shape needs at least 3 points.");
  const r = await readDigitized(page);
  const e = Object.entries(r.overrides).find(([, v]) => v.boundary_override);
  expect(ringOf(e[1].boundary_override)).toHaveLength(3);        // nothing removed
});

test("(f) outside the mode a bare drag inside the shape still moves the element", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await clickLeftSquare(page);
  await page.keyboard.press("Escape");
  const canvas = page.locator(".hoop canvas");
  await expect(canvas).toHaveAttribute("data-reshape", "off");
  const box = await canvas.boundingBox();
  const readOffset = () => page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const parsed = JSON.parse(localStorage.getItem("embstudio:p:" + id));
    const proj = parsed.project || parsed;
    const el = (proj.elements || []).find((e) => e.type === "digitized");
    return { x: el.offsetXMm || 0, y: el.offsetYMm || 0 };
  });
  const o0 = await readOffset();
  // A drag from inside the shape, away from every node.
  await drag(page, { x: box.x + box.width * 0.4, y: box.y + box.height * 0.5 }, { x: box.x + box.width * 0.4 + 40, y: box.y + box.height * 0.5 + 30 });
  await expect.poll(async () => (await readOffset()).x).not.toBe(o0.x);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const read = await readDigitized(page);
  expect(Object.values(read.overrides).filter((v) => v.boundary_override), "no point was edited").toHaveLength(0);
});


test("(g) hand-drawn: marquee two anchors of a drawn rectangle, drag -> the caption changes and the neighbour's stitches stay", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await drawRectangle(page, { x0: 0.15, x1: 0.45 });
  await drawRectangle(page, { x0: 0.55, x1: 0.85, open: false });
  await expect(page.locator(".mp-shaperow")).toHaveCount(2);
  await expect.poll(async () => (await readManual(page)).shapes.length).toBe(2);

  // The rectangles are symmetric about the middle of their joint box.
  const both = await settle(page);
  const mid = (both.bb[0] + both.bb[2]) / 2;
  const left0 = await darkBBox(page, 0, mid);
  const c0 = left0.css((left0.x0 + left0.x1) / 2, (left0.y0 + left0.y1) / 2);
  // Click inside the LEFT rectangle: popover -> Edit points.
  await page.mouse.click(c0.x, c0.y);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Edit points" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-reshape", "on");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Selecting re-fits the view a little: read the boxes AFTER, settled.
  const leftBefore = await settle(page, 0, mid);
  const rightBefore = await settle(page, mid + 1);
  const lb = await darkBBox(page, 0, mid);
  const p = lb.css(lb.x0, lb.y0), q = lb.css(lb.x1, lb.y0);         // the left rectangle's top two corners
  const pad = 14;
  const before = await readManual(page);
  await drag(page, { x: p.x - pad, y: p.y - pad }, { x: q.x + pad, y: q.y + pad });
  await expect.poll(() => selectedCount(page)).toBe(2);
  // Drag the pair outward (up and left) by 40 px: both anchors move together.
  await drag(page, p, { x: p.x - 40, y: p.y - 30 });
  await expect.poll(() => statsText(page), { timeout: 20_000 }).not.toBe(leftBefore.stats);

  const after = await readManual(page);
  const moved = (sid) => {
    const a = before.shapes.find((s) => s.id === sid).points, b = after.shapes.find((s) => s.id === sid).points;
    return a.map((pt, i) => Math.hypot(b[i].x - pt.x, b[i].y - pt.y)).map((d) => d > 1e-6);
  };
  const ids = before.shapes.map((s) => s.id);
  expect(moved(ids[0]).filter(Boolean), "exactly the two marqueed anchors of the left rectangle moved").toHaveLength(2);
  expect(moved(ids[1]).filter(Boolean), "the neighbour's anchors did not move").toHaveLength(0);
  // And the neighbour's STITCHES stayed where they were, to a pixel (the re-fit rule).
  const rightAfter = await settle(page, mid + 1);
  for (let i = 0; i < 4; i++) expect(Math.abs(rightAfter.bb[i] - rightBefore.bb[i]), "right box " + i).toBeLessThanOrEqual(1);
  const leftAfter = await settle(page, 0, mid);
  expect(leftBefore.bb[0] - leftAfter.bb[0], "the edited rectangle grew leftward").toBeGreaterThan(10);
});

test("(d) Simplify points 0.5 mm drops the point count, shows Points: N -> M, and the design restitches", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  // two-squares' squares are 4 points; a disc digitizes to a dense ring.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await pinDigitizeConfig(page, { border_by_size: false });
  await uploadArtwork(page, path.join(__dirname, "fixtures", "red-disc.png"));
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  let before = null;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) { reads.push(await page.locator(".dgp-stats").innerText()); await page.waitForTimeout(300); }
    before = reads[0];
    return reads.every((r) => r === reads[0]);
  }, { timeout: 30_000 }).toBe(true);

  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.5);
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const pointsText = await dialog.getByTestId("shapepop-points").innerText();
  const n0 = Number(pointsText.replace(/\D+/g, ""));
  expect(n0, "a disc digitizes to a dense ring").toBeGreaterThan(20);
  if (process.env.SIMPLIFY_SHOT) await page.screenshot({ path: process.env.SIMPLIFY_SHOT + "-before.png" });

  await dialog.getByTestId("shapepop-simplify-0.5").click();
  await expect(dialog.getByTestId("shapepop-points")).toHaveText(/^Points: \d+ -> \d+$/);
  const n1 = Number((await dialog.getByTestId("shapepop-points").innerText()).split("->")[1]);
  expect(await dialog.getByTestId("shapepop-points").innerText()).toContain(`Points: ${n0} ->`);
  expect(n1).toBeLessThan(n0);
  expect(n1).toBeGreaterThanOrEqual(3);
  if (process.env.SIMPLIFY_SHOT) await page.screenshot({ path: process.env.SIMPLIFY_SHOT + "-after.png" });

  const read = await readDigitized(page);
  const edited = Object.entries(read.overrides).filter(([, v]) => v.boundary_override);
  expect(edited, "exactly one shape carries a boundary edit").toHaveLength(1);
  const [sid, entry] = edited[0];
  const orig = ringOf(read.shapes.find((s) => s.id === sid).outline);
  const out = ringOf(entry.boundary_override);
  console.log(`simplify 0.5 mm: outlineFull ${orig.length} -> boundary_override ${out.length}`);
  expect(out.length).toBeLessThan(orig.length);
  expect(out.length).toBeGreaterThanOrEqual(3);
  expect(out.length).toBe(n1);
  await restitched(page, before);
});


test("(e) a hole's node drags on its own: holes_override carries the grabbed vertex moved, the shell is untouched, the restitch opens the garment", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeHoled(page);
  const g0 = await greenSquareAndHole(page);
  const garment = g0.f.garment;                                 // the pixel in the middle of the hole
  const g = await selectGreenShape(page);
  const read0 = await readHoled(page);
  const holed = read0.shapes.find((s) => s.holes.length === 1);
  expect(holed, "the service sent one shape with one hole").toBeTruthy();
  // Pull the hole's top-left NODE out into the green by ~3 mm. The hole's own
  // width in mm and px gives the scale; the node is found where it is drawn.
  const hs = holed.holes[0];
  const wMm = Math.max(...hs.map((p) => p[0])) - Math.min(...hs.map((p) => p[0]));
  const pxPerServiceMm = (g.f.hx1 - g.f.hx0) * g.k / wMm;
  const dragPx = 3 * pxPerServiceMm;                            // 3 mm of service mm, in px
  const holeNodes = (await amberNodes(page)).filter((n) => n.x >= g.hole.tl.x - 14 && n.x <= g.hole.br.x + 14 && n.y >= g.hole.tl.y - 14 && n.y <= g.hole.br.y + 14);
  expect(holeNodes.length, "the hole's seeded nodes are drawn").toBeGreaterThanOrEqual(3);
  const grab = holeNodes.reduce((p, q) => (Math.hypot(q.x - g.hole.tl.x, q.y - g.hole.tl.y) < Math.hypot(p.x - g.hole.tl.x, p.y - g.hole.tl.y) ? q : p));
  await drag(page, grab, { x: grab.x - dragPx, y: grab.y - dragPx });   // diagonal: out into the green, up and left

  const read = await readHoled(page);
  const entry = read.overrides[holed.id];
  expect(entry, "the holed shape carries an override").toBeTruthy();
  expect(entry.holes_override, "holes_override is on the wire").toHaveLength(1);
  expect(entry.boundary_override, "the shell was not edited").toBeUndefined();
  // Sparse nodes: the grabbed NODE moved the whole drag; only its two spans were
  // rebuilt, so every hole vertex outside them is the original, in order.
  const kinds = (list) => `${list.length} nodes (${list.filter((x) => x.kind === "corner").length} corner, ${list.filter((x) => x.kind === "smooth").length} smooth)`;
  expect(entry.nodes.holes, "one node list per hole").toHaveLength(1);
  const holeList = entry.nodes.holes[0];
  const newHole = entry.holes_override[0];
  const ring0 = ringOf(holed.holes[0]);
  const draggedAt = holeList.findIndex((nd) => ring0.every((p) => Math.hypot(p[0] - newHole[nd.i][0], p[1] - newHole[nd.i][1]) > 1e-4));
  expect(draggedAt, "exactly the grabbed node left the original ring").toBeGreaterThanOrEqual(0);
  expect(outsideTwoSpansIsOriginal(holed.holes[0], newHole, holeList, draggedAt), "the hole outside the node's two spans is the original").toBe(true);
  const pos = newHole[holeList[draggedAt].i];
  const homeIdx = ring0.reduce((best, p, i) => (Math.hypot(p[0] - 3 - pos[0], p[1] - 3 - pos[1]) < Math.hypot(ring0[best][0] - 3 - pos[0], ring0[best][1] - 3 - pos[1]) ? i : best), 0);
  const lead = { i: homeIdx, dx: pos[0] - ring0[homeIdx][0], dy: pos[1] - ring0[homeIdx][1] };
  expect(lead.dx, "the grabbed node took the whole drag, out into the green").toBeCloseTo(-3, 0);
  expect(lead.dy, "and up by as much").toBeCloseTo(-3, 0);
  console.log("holes_override vertices:", newHole.length, "of", ring0.length, "- dragged node", JSON.stringify(lead));
  console.log("holed fixture seeded: shell", kinds(entry.nodes.shell), "| hole", kinds(holeList), "| shell vertices", ringOf(holed.outline).length, "hole vertices", ring0.length);

  await restitched(page, before);
  // The ground the move opened: halfway from the midpoint of the grabbed vertex's
  // two ring neighbours (the chord) out to its new position. It is inside the
  // triangle (prev, new, next) and beyond the old corner, so it was green and is
  // garment now. (The bbox corner is not a vertex on a chamfered square.)
  const minX = Math.min(...ring0.map((p) => p[0])), minY = Math.min(...ring0.map((p) => p[1]));
  const toPx = (p) => ({ x: g.hole.tl.x + (p[0] - minX) * pxPerServiceMm, y: g.hole.tl.y + (p[1] - minY) * pxPerServiceMm });
  const n0 = ring0.length;
  const prev = toPx(ring0[(lead.i + n0 - 1) % n0]), next = toPx(ring0[(lead.i + 1) % n0]);
  const mid = { x: (prev.x + next.x) / 2, y: (prev.y + next.y) / 2 };
  const vNew = { x: toPx(ring0[lead.i]).x + lead.dx * pxPerServiceMm, y: toPx(ring0[lead.i]).y + lead.dy * pxPerServiceMm };
  const wedge = { x: (mid.x + vNew.x) / 2, y: (mid.y + vNew.y) / 2 };
  // The wedge is bare garment, but it sits down-right of the green it was cut
  // from, so the realistic view's drop shadow falls on it. Measured 2026-11-07
  // on Kent's laptop: 39 levels off the garment on main (passing the old < 40
  // by one), 41 with the thread-appearance crown, the wedge itself moving ~3 px
  // run to run with where the drag lands. The question is garment-or-thread:
  // green thread is 90+ off the garment on its red channel even at its
  // darkest rim, and the deepest shadow the renderer casts (a raised border,
  // alpha 0.42) is under 75, so 80 separates the two with room either side.
  await expect.poll(async () => {
    const px = await pixelAt(page, wedge);
    return Math.max(...px.map((v, i) => Math.abs(v - garment[i])));
  }, { timeout: 15_000 }).toBeLessThan(80);
});

test("(e2) an exterior-only drag on the same holed shape commits NO holes_override", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeHoled(page);
  const g = await selectGreenShape(page);
  await drag(page, g.shell.tr, { x: g.shell.tr.x + 14, y: g.shell.tr.y - 10 });
  const read = await readHoled(page);
  const edited = Object.entries(read.overrides).filter(([, v]) => v.boundary_override);
  expect(edited, "the shell was edited").toHaveLength(1);
  expect(edited[0][1].holes_override, "and no hole key rides with it").toBeUndefined();
});

test("(e3) Edit points: a hole's node selected and nudged Shift+Left x3 -> holes_override differs in exactly 1 vertex, 3 mm of field space", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeHoled(page);
  const g1 = await selectGreenShape(page);
  await page.getByRole("dialog").count();                       // popover is closed (Escape in selectGreenShape)
  // Re-open it from a click on the ring's body, then Edit points.
  await page.mouse.click(g1.shell.tl.x + 4 * g1.k + 3, (g1.shell.tl.y + g1.hole.bl.y) / 2);
  await page.getByRole("dialog").getByRole("button", { name: "Edit points" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-reshape", "on");
  const g = await greenSquareAndHole(page);
  const nodesHere = (await amberNodes(page)).filter((n) => n.x >= g.hole.tl.x - 14 && n.x <= g.hole.br.x + 14 && n.y >= g.hole.tl.y - 14 && n.y <= g.hole.br.y + 14);
  const pick = nodesHere.reduce((p, q) => (Math.hypot(q.x - g.hole.tr.x, q.y - g.hole.tr.y) < Math.hypot(p.x - g.hole.tr.x, p.y - g.hole.tr.y) ? q : p));
  await page.mouse.click(pick.x, pick.y);
  await expect.poll(() => selectedCount(page)).toBe(1);
  await page.locator(".hoop canvas").focus();
  for (let i = 0; i < 3; i++) await page.keyboard.press("Shift+ArrowLeft");
  const read = await readHoled(page);
  const holed = read.shapes.find((s) => s.holes.length === 1);
  const entry = read.overrides[holed.id];
  expect(entry.holes_override).toHaveLength(1);
  expect(entry.boundary_override, "the shell was not edited").toBeUndefined();
  // One NODE moved (3 x 1 mm); only its two spans can differ from the traced ring.
  const list = entry.nodes.holes[0];
  const ring0 = ringOf(holed.holes[0]);
  const at = list.findIndex((nd) => ring0.every((p) => Math.hypot(p[0] - entry.holes_override[0][nd.i][0], p[1] - entry.holes_override[0][nd.i][1]) > 1e-4));
  expect(at, "exactly one hole node left the traced ring").toBeGreaterThanOrEqual(0);
  expect(list.filter((nd) => ring0.every((p) => Math.hypot(p[0] - entry.holes_override[0][nd.i][0], p[1] - entry.holes_override[0][nd.i][1]) > 1e-4))).toHaveLength(1);
  expect(outsideTwoSpansIsOriginal(holed.holes[0], entry.holes_override[0], list, at), "everything outside its two spans is the traced ring").toBe(true);
  console.log("nudged node:", JSON.stringify(list[at]), "hole vertices", ring0.length, "->", entry.holes_override[0].length);
});

test("(e4) every point of the hole selected, Delete -> holes_override is [] (the shape goes solid) and the hole no longer shows garment", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeHoled(page);
  const garment = (await greenSquareAndHole(page)).f.garment;
  const g1 = await selectGreenShape(page);
  await page.mouse.click(g1.shell.tl.x + 4 * g1.k + 3, (g1.shell.tl.y + g1.hole.bl.y) / 2);
  await page.getByRole("dialog").getByRole("button", { name: "Edit points" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-reshape", "on");
  const g = await greenSquareAndHole(page);
  const pad = 12;
  await drag(page, { x: g.hole.tl.x - pad, y: g.hole.tl.y - pad }, { x: g.hole.br.x + pad, y: g.hole.br.y + pad });
  await expect.poll(() => selectedCount(page)).toBeGreaterThanOrEqual(3);   // every NODE of the hole, none of the shell's
  console.log("hole nodes selected by the marquee:", await selectedCount(page));
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Delete");
  await expect.poll(async () => {
    const r = await readHoled(page);
    const e = Object.values(r.overrides).find((v) => v.holes_override);
    return e ? e.holes_override.length : null;
  }).toBe(0);
  const read = await readHoled(page);
  expect(Object.values(read.overrides).some((v) => v.boundary_override), "the shell was not edited").toBe(false);
  await restitched(page, before);
  const centre = { x: (g.hole.tl.x + g.hole.br.x) / 2, y: (g.hole.tl.y + g.hole.br.y) / 2 };
  // The hole no longer shows garment. (What sews there instead is the service's
  // call: the white square the art holds in the hole stitches once nothing
  // leaves the hole open - it is its own shape, with its own thread and delete.)
  await expect.poll(async () => {
    const px = await pixelAt(page, centre);
    return Math.max(...px.map((v, i) => Math.abs(v - garment[i])));
  }, { timeout: 15_000 }).toBeGreaterThan(60);
});

// ---- Done / Discard (2026-11-04) -----------------------------------------


test("(h) drag a vertex, click Discard: the ring is back to the pre-edit ring and the mode is off", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await enterReshape(page);
  const { tr } = await blackSquareCorners(page);
  await drag(page, tr, { x: tr.x + 22, y: tr.y - 16 });
  await expect.poll(async () => Object.values((await readDigitized(page)).overrides).some((v) => v.boundary_override)).toBe(true);
  const b = await stripButton(page, "discard");
  await page.mouse.click(b.x, b.y);
  await expect(page.locator(".hoop canvas")).not.toHaveAttribute("data-reshape", "on");
  await expect.poll(async () => Object.values((await readDigitized(page)).overrides).some((v) => v.boundary_override)).toBe(false);
});

test("(i) drag a vertex, press Enter: the edit stays and the mode is off", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await enterReshape(page);
  const { tr } = await blackSquareCorners(page);
  await drag(page, tr, { x: tr.x + 22, y: tr.y - 16 });
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".hoop canvas")).not.toHaveAttribute("data-reshape", "on");
  const r = await readDigitized(page);
  expect(Object.values(r.overrides).filter((v) => v.boundary_override)).toHaveLength(1);
});

test("(n) keyboard node cursor: ] and Tab step the points, Space selects, arrows move them, no pointer", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await enterReshape(page);
  const canvas = page.locator(".hoop canvas");
  const live = page.locator(".fieldlive");
  await canvas.focus();
  expect(await selectedCount(page), "nothing selected before the cursor starts").toBe(0);

  await page.keyboard.press("]");
  await expect(live).toHaveText(/^Point 1 of \d+, ring 1, not selected$/);
  await page.keyboard.press(" ");
  await expect(live).toHaveText(/^Point 1 of \d+, ring 1, selected$/);
  await expect.poll(() => selectedCount(page)).toBe(1);

  await page.keyboard.press("Tab");
  await expect(live).toHaveText(/^Point 2 of \d+, ring 1, not selected$/);
  await page.keyboard.press(" ");
  await expect.poll(() => selectedCount(page)).toBe(2);
  await page.keyboard.press("Space");
  await expect.poll(() => selectedCount(page)).toBe(1);
  await page.keyboard.press(" ");
  await expect.poll(() => selectedCount(page)).toBe(2);

  // The existing arrows-move-selection path works on the keyboard-built selection.
  await page.keyboard.press("ArrowRight");
  await expect.poll(async () => {
    const r = await readDigitized(page);
    const e = Object.entries(r.overrides).find(([, v]) => v.boundary_override);
    if (!e) return 0;
    return movedVertices(r.shapes.find((s) => s.id === e[0]).outline, e[1].boundary_override).length;
  }).toBe(2);

  // [ steps back, and wraps from the first point to the last.
  await page.keyboard.press("[");
  await expect(live).toHaveText(/^Point 1 of \d+, ring 1, selected$/);
  await page.keyboard.press("[");
  await expect(live).toHaveText(/^Point \d+ of \d+, ring \d+, /);
});

// (r2) 2026-11-13: Reshape belonged to an element ID, and ids repeat across
// designs, so the mode carried into the next design's same-id element and its
// Discard wrote this design's entry snapshot there. Opening another design
// now ends the mode.
test("(r2) opening another design ends Reshape, even on an element with the same id", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await enterReshape(page);
  const idOf = () => page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const p = id && JSON.parse(localStorage.getItem("embstudio:p:" + id) || "null");
    return p ? p.selectedId : null;
  });
  const idA = await idOf();

  await page.getByRole("button", { name: /My designs/ }).first().click();
  await expect(page.locator(".drawer")).toBeVisible();
  await page.getByRole("button", { name: "+ New design" }).click();
  await page.getByTestId("art-file").setInputFiles(ART_PNG); // same element id as A's, not digitized
  await expect.poll(idOf).toBe(idA);

  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-reshape", "off");
  await expect(page.getByRole("button", { name: "Discard" })).toHaveCount(0);
});
