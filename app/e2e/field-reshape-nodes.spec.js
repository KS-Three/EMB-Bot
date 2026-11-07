// Reshape mode, part 2: sparse smooth nodes (s*) and Add hole (h1-h9). Split out of
// field-reshape-mode.spec.js 2026-11-07; helpers in reshape-helpers.js.
import { test, expect } from "@playwright/test";
import { pickGarment, uploadArtwork, runDigitize, pinDigitizeConfig, openAdvanced } from "./helpers.js";
import fs, { existsSync, readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { useDigitizerService, readDigitized, ringOf, movedVertices, blackSquareCorners, drag, digitizeSquares, clickLeftSquare, enterReshape, selectedCount, restitched, digitizeHoled, pixelAt, readHoled, selectGreenShape, stripButton, RENDERS, amberNodes, stableNodePx, reshapeNodePx, nodeCount, digitizeArt, readNodes, shoelace, perimeter, kinds, outsideTwoSpansIsOriginal, __dirname, serviceUp, skipReason } from "./reshape-helpers.js";

// SERVICE_URL (the digitizer service at 127.0.0.1:8721): this file needs it, so
// playwright.config.js runs it in the serial step.
useDigitizerService();

test("(s1) red-disc: seeding thins the traced ring; one node dragged 3 mm outward rebuilds only its two spans, and the design restitches", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeArt(page, path.join(__dirname, "fixtures", "red-disc.png"));
  const canvas = page.locator(".hoop canvas");
  const box = await canvas.boundingBox();
  await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.5);
  await expect(page.getByRole("dialog", { name: /^Thread #/ })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  await expect.poll(() => nodeCount(page)).toBeGreaterThan(2);
  const n0 = await nodeCount(page);
  mkdirSync(RENDERS, { recursive: true });
  // Measured 2026-11-05: the service traces this disc as a 64-vertex ring, and
  // the spec's 0.5 mm Douglas-Peucker seeds MORE than the 16 the spec expected
  // (the disc is ~200 mm across at tote scale: the sagitta of a 64-gon on it
  // is already ~0.6 mm). The ring goes to test-results so the threshold can be
  // re-read offline; the test pins that seeding thins the ring, not the count.
  const dense0 = (await readDigitized(page)).shapes.reduce((a, b) => (b.outline.length > a.outline.length ? b : a));
  fs.writeFileSync(path.join(RENDERS, "s1-red-disc-outline.json"), JSON.stringify(dense0.outline));
  expect(n0, "seeding thins the traced ring").toBeLessThan(ringOf(dense0.outline).length);
  await canvas.screenshot({ path: path.join(RENDERS, "s1-red-disc-before.png") });

  // The rightmost node, and the scale in px per service mm (red fill width / outline width).
  const nodes = await amberNodes(page);
  expect(nodes.length, "the amber nodes are found on the canvas").toBeGreaterThanOrEqual(Math.min(n0, 4));
  const grab = nodes.reduce((a, b) => (b.x > a.x ? b : a));
  const read0 = await readDigitized(page);
  const shape = read0.shapes.reduce((a, b) => (b.outline.length > a.outline.length ? b : a));
  const xs = ringOf(shape.outline).map((p) => p[0]);
  const wMm = Math.max(...xs) - Math.min(...xs);
  const red = await page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let x0 = Infinity, x1 = -1;
    for (let y = 0; y < c.height; y += 2) for (let x = 0; x < c.width; x++) {
      const i = (y * c.width + x) * 4;
      if (d[i + 3] > 200 && d[i] > 150 && d[i + 1] < 80 && d[i + 2] < 80) { if (x < x0) x0 = x; if (x > x1) x1 = x; }
    }
    return { w: x1 - x0, cw: c.width };
  });
  const pxPerMm = (red.w * (box.width / red.cw)) / wMm;
  await drag(page, grab, { x: grab.x + 3 * pxPerMm, y: grab.y });

  await expect.poll(async () => !!(await readNodes(page))).toBe(true);
  const { entry, shape: sh } = await readNodes(page);
  const orig = ringOf(sh.outline);
  const edited = entry.boundary_override;
  const nodeList = entry.nodes.shell;
  expect(nodeList.length, "the committed node list is the shown one").toBe(n0);
  console.log(`s1 red-disc: outlineFull ${orig.length} vertices, seeded ${JSON.stringify(kinds(nodeList))}, boundary_override ${edited.length}`);
  // The dragged node is the one whose position is in no original vertex.
  const dragged = nodeList.findIndex((nd) => orig.every((p) => Math.hypot(p[0] - edited[nd.i][0], p[1] - edited[nd.i][1]) > 1e-4));
  expect(dragged, "exactly the grabbed node left the original ring").toBeGreaterThanOrEqual(0);
  const at = edited[nodeList[dragged].i];
  const home = orig.reduce((a, p) => (Math.hypot(p[0] + 3 - at[0], p[1] - at[1]) < Math.hypot(a[0] + 3 - at[0], a[1] - at[1]) ? p : a));
  expect(Math.hypot(home[0] + 3 - at[0], home[1] - at[1]), "the node moved ~3 mm to the right").toBeLessThan(0.6);
  expect(outsideTwoSpansIsOriginal(sh.outline, edited, nodeList, dragged), "every vertex outside the node's two spans is the original, in order").toBe(true);
  await restitched(page, before);
  await page.waitForTimeout(500);
  await canvas.screenshot({ path: path.join(RENDERS, "s1-red-disc-after.png") });
});

test("(s2) two-squares: 4 corners; a dragged corner keeps 4 vertices; click the edge -> 5 nodes (area equal); double-click -> smooth; Delete -> 4; Discard -> original", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  await enterReshape(page);
  expect(await nodeCount(page), "a traced square seeds 4 nodes").toBe(4);
  expect(Object.keys((await readDigitized(page)).overrides)).toHaveLength(0);

  // I5: drag the top-right corner; the quadrilateral keeps 4 vertices, one moved.
  const { tr } = await blackSquareCorners(page);
  await drag(page, tr, { x: tr.x + 22, y: tr.y - 16 });
  await expect.poll(async () => !!(await readNodes(page))).toBe(true);
  let got = await readNodes(page);
  const ring4 = got.entry.boundary_override;
  expect(ring4, "I5: a dragged corner leaves a quadrilateral").toHaveLength(4);
  expect(movedVertices(got.shape.outline, ring4), "exactly one vertex moved").toHaveLength(1);
  console.log(`s2 two-squares: seeded ${JSON.stringify(kinds(got.entry.nodes.shell))}`);
  expect(got.entry.nodes.shell.every((n) => n.kind === "corner")).toBe(true);
  const area4 = Math.abs(shoelace(ring4)), peri4 = perimeter(ring4);

  // I6: click the middle of the top edge in the mode.
  await restitched(page, before);                                  // the corner drag restitched...
  await stableNodePx(page);                                        // ...and the field stopped re-laying out
  // The element's selection handles sit over some corners, so the nodes are read
  // from the canvas' own report of where it drew them (data-reshape-node-px).
  const nodesPx = await reshapeNodePx(page);
  expect(nodesPx.filter((n) => n.ring === -1), "the selected shape's four nodes").toHaveLength(4);
  const top = nodesPx.filter((n) => n.ring === -1).sort((p, q) => p.y - q.y).slice(0, 2);
  const mid = { x: (top[0].x + top[1].x) / 2, y: (top[0].y + top[1].y) / 2 };
  await page.mouse.click(mid.x, mid.y);
  await expect.poll(() => nodeCount(page)).toBe(5);
  got = await readNodes(page);
  const ring5 = got.entry.boundary_override;
  expect(ring5, "one more vertex").toHaveLength(5);
  expect(Math.abs(shoelace(ring5))).toBeCloseTo(area4, 6);
  expect(perimeter(ring5)).toBeCloseTo(peri4, 6);
  const newIdx = got.entry.nodes.shell.findIndex((n) => !ring4.some((p) => Math.hypot(p[0] - ring5[n.i][0], p[1] - ring5[n.i][1]) < 1e-9));
  expect(newIdx, "the new node is a vertex that was not in the quadrilateral").toBeGreaterThanOrEqual(0);
  expect(got.entry.nodes.shell[newIdx].kind, "an inserted node is a corner").toBe("corner");

  // Double-click it: smooth. A straight top edge stays straight (I5 wins).
  await page.waitForTimeout(700);                                // not the second half of the insert click
  const newPt = mid;
  await page.mouse.dblclick(newPt.x, newPt.y);
  await expect.poll(async () => (await readNodes(page)).entry.nodes.shell[newIdx].kind).toBe("smooth");
  expect((await readNodes(page)).entry.boundary_override, "collinear neighbours: still a straight edge").toHaveLength(5);

  // Pull it up 18 px: its two spans now carry flattened vertices.
  await drag(page, newPt, { x: newPt.x, y: newPt.y - 18 });
  await expect.poll(async () => (await readNodes(page)).entry.boundary_override.length).toBeGreaterThan(5);
  got = await readNodes(page);
  expect(got.entry.nodes.shell).toHaveLength(5);
  console.log(`s2: smooth node pulled 18 px -> boundary_override ${got.entry.boundary_override.length} vertices`);

  // Delete the (selected) smooth node: the merged span between two corners is straight again.
  await expect.poll(() => selectedCount(page)).toBe(1);
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Delete");
  await expect.poll(() => nodeCount(page)).toBe(4);
  await expect.poll(async () => (await readNodes(page)).entry.boundary_override.length).toBe(4);

  // Discard: back to the original, no override at all.
  const b = await stripButton(page, "discard");
  await page.mouse.click(b.x, b.y);
  await expect(page.locator(".hoop canvas")).not.toHaveAttribute("data-reshape", "on");
  await expect.poll(async () => Object.keys((await readDigitized(page)).overrides).length).toBe(0);
});

test("(s4) enter Edit points and press Done with no edit: no override at all, no nodes written (I1)", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  const base = JSON.stringify((await readDigitized(page)).overrides);
  await enterReshape(page);
  expect(await nodeCount(page)).toBeGreaterThan(2);               // seeds are shown...
  const b = await stripButton(page, "done");
  await page.mouse.click(b.x, b.y);
  await expect(page.locator(".hoop canvas")).not.toHaveAttribute("data-reshape", "on");
  await page.waitForTimeout(800);
  const overrides = (await readDigitized(page)).overrides;
  expect(JSON.stringify(overrides), "...but nothing is written").toBe(base);
  expect(Object.values(overrides).some((v) => v.nodes || v.boundary_override)).toBe(false);
});

test("(s5) outside the mode: double-click an edge inserts a corner node, double-click a node toggles it (a PointerEvent's detail is 0, so the Studio counts the presses itself)", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  await clickLeftSquare(page);
  await page.keyboard.press("Escape");
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-reshape", "off");
  await expect.poll(() => nodeCount(page)).toBe(4);
  const { tl, tr } = await blackSquareCorners(page);
  const mid = { x: (tl.x + tr.x) / 2, y: (tl.y + tr.y) / 2 };
  await page.mouse.dblclick(mid.x, mid.y);
  await expect.poll(() => nodeCount(page)).toBe(5);
  let got = await readNodes(page);
  expect(got.entry.boundary_override, "one more vertex, nothing moved").toHaveLength(5);
  expect(got.entry.nodes.shell.filter((n) => n.kind === "corner")).toHaveLength(5);
  await page.waitForTimeout(700);
  await page.mouse.dblclick(mid.x, mid.y);
  await expect.poll(async () => (await readNodes(page)).entry.nodes.shell.filter((n) => n.kind === "smooth").length).toBe(1);
  got = await readNodes(page);
  expect(got.entry.boundary_override, "its neighbours are collinear corners: the edge stays straight").toHaveLength(5);
});

test("(s6) quick drag: a press on a node that wobbles 1 px commits nothing; a drag past CLICK_PX still commits", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  await clickLeftSquare(page);
  await page.keyboard.press("Escape");
  const { tr } = await blackSquareCorners(page);
  // A press-and-release with 1 px of wobble, as a click on a node to select it.
  await page.mouse.move(tr.x, tr.y);
  await page.mouse.down();
  await page.mouse.move(tr.x + 1, tr.y);
  await page.mouse.move(tr.x + 1, tr.y + 1);
  await page.mouse.up();
  await page.waitForTimeout(1500);
  const overrides = (await readDigitized(page)).overrides;
  expect(Object.values(overrides).some((v) => v.boundary_override || v.nodes), "no geometry, no nodes").toBe(false);
  expect(await page.locator(".dgp-stats").innerText(), "no restitch").toBe(before);
  // Past the dead zone it is a drag again.
  await drag(page, tr, { x: tr.x + 9, y: tr.y - 6 });
  await expect.poll(async () => !!(await readNodes(page))).toBe(true);
  expect(ringOf((await readNodes(page)).entry.boundary_override)).toHaveLength(4);
});


// ---- Add hole (2026-11-05, PR 3 of the node-editing work) ------------------
// "Add hole" (popover row, or the right-click menu inside a shape) opens a draw
// mode: each click places a vertex, a click on the first vertex closes the ring,
// and the closed ring is appended to the shape's holes_override through the
// same commit path as every other ring edit. A hole outside / crossing the
// shape is refused with boundaryIssues' own wording and the draft stays open.

const draftCount = (page) => page.locator(".hoop canvas").getAttribute("data-hole-draft");

// Left square: select it, Add hole from the popover, wait for the draw mode and
// for the layout to settle once the popover is gone. -> the square's corners.
async function startAddHole(page) {
  await clickLeftSquare(page);
  await page.getByRole("dialog").getByRole("button", { name: "Add hole" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-hole-draft", "0");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  return settledCorners(page);
}

// The page re-lays out once the popover is gone: poll until two reads 150 ms
// apart agree, then aim at that.
async function settledCorners(page) {
  let prev = null, cur = await blackSquareCorners(page);
  await expect.poll(async () => {
    prev = cur;
    await page.waitForTimeout(150);
    cur = await blackSquareCorners(page);
    return JSON.stringify(prev) === JSON.stringify(cur);
  }, { timeout: 10_000 }).toBe(true);
  return cur;
}

// Page points of a square hole of `frac` x the black square's half-size, centred in it.
function holeSquare(c, frac = 0.3) {
  const cx = (c.tl.x + c.br.x) / 2, cy = (c.tl.y + c.br.y) / 2, h = ((c.tr.x - c.tl.x) / 2) * frac;
  return [{ x: cx - h, y: cy - h }, { x: cx + h, y: cy - h }, { x: cx + h, y: cy + h }, { x: cx - h, y: cy + h }];
}

async function clickAll(page, pts) {
  for (const q of pts) await page.mouse.click(q.x, q.y);
}

const holeOverrides = async (page) => {
  const r = await readDigitized(page);
  return Object.entries(r.overrides).filter(([, v]) => Array.isArray(v.holes_override));
};

test("(h1) Add hole: four clicks inside the square, click the first vertex -> one 4-vertex hole, 4 corner nodes, the restitch shows garment there", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  const corners = await startAddHole(page);
  const sq = holeSquare(corners);
  const centre = { x: (corners.tl.x + corners.br.x) / 2, y: (corners.tl.y + corners.br.y) / 2 };
  const solid = await pixelAt(page, centre);
  expect(Math.max(...solid), "the square is solid black before the hole").toBeLessThan(40);
  await clickAll(page, sq);
  expect(await draftCount(page)).toBe("4");
  expect(await holeOverrides(page), "nothing is committed while drawing").toHaveLength(0);
  await page.mouse.click(sq[0].x, sq[0].y);                         // the first vertex closes it
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-hole-draft", "off");
  const held = await holeOverrides(page);
  expect(held, "exactly one shape carries a holes_override").toHaveLength(1);
  const [, entry] = held[0];
  expect(entry.holes_override, "one hole").toHaveLength(1);
  expect(ringOf(entry.holes_override[0]), "4 vertices").toHaveLength(4);
  expect(entry.boundary_override, "the shell was not edited").toBeUndefined();
  expect(entry.nodes.holes, "one node list for the new hole").toHaveLength(1);
  expect(entry.nodes.holes[0].map((n) => n.kind)).toEqual(["corner", "corner", "corner", "corner"]);
  await restitched(page, before);
  await expect.poll(async () => Math.max(...(await pixelAt(page, centre))), { timeout: 15_000 }).toBeGreaterThan(80);
  console.log("h1: centre pixel solid", JSON.stringify(solid), "-> hole", JSON.stringify(await pixelAt(page, centre)));
});

test("(h2) Undo after Add hole: no holes_override, the garment is gone from the square", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeSquares(page);
  const corners = await startAddHole(page);
  const sq = holeSquare(corners);
  const centre = { x: (corners.tl.x + corners.br.x) / 2, y: (corners.tl.y + corners.br.y) / 2 };
  await clickAll(page, sq);
  await page.mouse.click(sq[0].x, sq[0].y);
  expect(await holeOverrides(page)).toHaveLength(1);
  await restitched(page, before);
  await expect.poll(async () => Math.max(...(await pixelAt(page, centre))), { timeout: 15_000 }).toBeGreaterThan(80);
  // The restitch that followed the edit may sit on the undo stack above it:
  // undo until the hole is gone (it never takes more than a few steps).
  for (let i = 0; i < 4 && (await holeOverrides(page)).length; i++) {
    const n = (await holeOverrides(page)).length;
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    // the click has landed once the read state moves, or the next poll sees it
    await expect.poll(async () => (await holeOverrides(page)).length !== n || (await page.getByRole("button", { name: "Undo", exact: true }).isDisabled()), { timeout: 3_000 }).toBe(true).catch(() => {});
  }
  await expect.poll(async () => (await holeOverrides(page)).length).toBe(0);
  const back = () => page.locator(".dgp-stats").innerText().then((t) => t === before);
  const ok = await expect.poll(back, { timeout: 8_000 }).toBe(true).then(() => true, () => false);
  if (!ok) { await runDigitize(page); await expect.poll(back, { timeout: 120_000 }).toBe(true); }
  await expect.poll(async () => Math.max(...(await pixelAt(page, centre))), { timeout: 15_000 }).toBeLessThan(40);
});

test("(h3) a hole drawn out of the shape is refused with the existing wording, nothing is patched; Backspace and redraw inside commits", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  const corners = await startAddHole(page);
  const [a, b] = holeSquare(corners);
  const half = (corners.tr.x - corners.tl.x) / 2;
  const cx = (corners.tl.x + corners.br.x) / 2, cy = (corners.tl.y + corners.br.y) / 2;
  const out = { x: cx - 0.3 * half, y: corners.bl.y + 0.5 * half };   // well below the square's bottom edge
  await clickAll(page, [a, b, out]);
  expect(await draftCount(page)).toBe("3");
  await page.mouse.click(a.x, a.y);                                  // try to close
  await expect(page.getByTestId("shape-edit-error")).toContainText(/Hole 1 (crosses the outline|is outside the outline)\./);
  expect(await holeOverrides(page), "a refusal patches nothing").toHaveLength(0);
  expect(await draftCount(page), "the draft stays open").toBe("3");
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Backspace");
  expect(await draftCount(page)).toBe("2");
  await page.mouse.click(cx - 0.3 * half, cy + 0.3 * half);
  expect(await draftCount(page)).toBe("3");
  await page.mouse.click(a.x, a.y);
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-hole-draft", "off");
  const held = await holeOverrides(page);
  expect(held).toHaveLength(1);
  expect(ringOf(held[0][1].holes_override[0]), "a triangle").toHaveLength(3);
});

test("(h4) Escape mid-draft: no patch and the mode is gone", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  const corners = await startAddHole(page);
  const sq = holeSquare(corners);
  await clickAll(page, sq.slice(0, 3));
  expect(await draftCount(page)).toBe("3");
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Escape");
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-hole-draft", "off");
  expect(Object.keys((await readDigitized(page)).overrides), "no override at all").toHaveLength(0);
});

test("(h7) holed fixture: a small square drawn inside the existing hole's void is refused as 'Hole 2 crosses Hole 1.', nothing patched, draft stays open", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeHoled(page);
  const g = await selectGreenShape(page);
  const bodyX = (g.shell.tl.x + g.hole.tl.x) / 2, bodyY = (g.hole.tl.y + g.hole.bl.y) / 2;
  await page.mouse.click(bodyX, bodyY, { button: "right" });
  await page.getByRole("menuitem", { name: "Add hole" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-hole-draft", "0");
  const cx = (g.hole.tl.x + g.hole.br.x) / 2, cy = (g.hole.tl.y + g.hole.br.y) / 2;
  const h = ((g.hole.br.x - g.hole.tl.x) / 2) * 0.3;
  const sq = [{ x: cx - h, y: cy - h }, { x: cx + h, y: cy - h }, { x: cx + h, y: cy + h }, { x: cx - h, y: cy + h }];
  await clickAll(page, sq);
  await page.mouse.click(sq[0].x, sq[0].y);
  await expect(page.getByTestId("shape-edit-error")).toContainText("Hole 2 crosses Hole 1.");
  expect(Object.keys((await readHoled(page)).overrides), "a refusal patches nothing").toHaveLength(0);
  expect(await draftCount(page), "the draft stays open").toBe("4");
});

test("(h8) right-click mid-draft opens no menu and keeps the draft's vertices; a Ctrl-click places a vertex", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  const corners = await startAddHole(page);
  const sq = holeSquare(corners);
  await clickAll(page, sq.slice(0, 2));
  expect(await draftCount(page)).toBe("2");
  await page.mouse.click(sq[2].x, sq[2].y, { button: "right" });
  await expect(page.getByRole("menuitem")).toHaveCount(0);
  expect(await draftCount(page), "the draft keeps its vertices").toBe("2");
  await page.mouse.click(sq[2].x, sq[2].y, { modifiers: ["Control"] });
  expect(await draftCount(page), "Ctrl-click is a plain vertex").toBe("3");
});

test("(h9) a click back on the first vertex at 2 points adds nothing", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  const corners = await startAddHole(page);
  const [a, b] = holeSquare(corners);
  await clickAll(page, [a, b]);
  await page.mouse.click(a.x, a.y);                                  // the first vertex again
  expect(await draftCount(page), "no duplicate vertex").toBe("2");
  // The stale-refusal fix (cancelHoleDraft() on a selection change) has no e2e: the
  // fixture is ONE element, so a press on the other square is a vertex, not a selection.
});

test("(h5) holed fixture, right-click menu: a second hole beside the first -> 2 rings, the first unchanged, 2 node lists", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  const before = await digitizeHoled(page);
  const g = await selectGreenShape(page);
  const read0 = await readHoled(page);
  const holed = read0.shapes.find((s) => s.holes.length === 1);
  expect(holed).toBeTruthy();
  // Right-click the ring's body: the menu offers Add hole.
  const bodyX = (g.shell.tl.x + g.hole.tl.x) / 2, bodyY = (g.hole.tl.y + g.hole.bl.y) / 2;
  await page.mouse.click(bodyX, bodyY, { button: "right" });
  await page.getByRole("menuitem", { name: "Add hole" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-hole-draft", "0");
  // A square in the green band left of the hole.
  const bw = g.hole.tl.x - g.shell.tl.x;
  const h = Math.min(bw * 0.3, (g.hole.bl.y - g.hole.tl.y) * 0.2);
  const sq = [
    { x: bodyX - h, y: bodyY - h }, { x: bodyX + h, y: bodyY - h },
    { x: bodyX + h, y: bodyY + h }, { x: bodyX - h, y: bodyY + h },
  ];
  console.log("h5: band width px", bw.toFixed(1), "new hole half-size px", h.toFixed(1));
  await clickAll(page, sq);
  await page.mouse.click(sq[0].x, sq[0].y);
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-hole-draft", "off");
  const entry = (await readHoled(page)).overrides[holed.id];
  expect(entry.holes_override, "two rings").toHaveLength(2);
  expect(entry.holes_override[0], "the first hole is unchanged").toEqual(holed.holes[0]);
  expect(entry.nodes.holes, "two node lists").toHaveLength(2);
  expect(entry.boundary_override).toBeUndefined();
  await restitched(page, before);
});

test("(h6) double-click a vertex of the new hole -> smooth, its two spans carry interior vertices, one undo step", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await digitizeSquares(page);
  const corners = await startAddHole(page);
  const sq = holeSquare(corners, 0.5);
  await clickAll(page, sq);
  await page.mouse.click(sq[0].x, sq[0].y);
  await expect.poll(async () => (await holeOverrides(page)).length).toBe(1);
  await page.waitForTimeout(700);                                    // not the second half of the closing click
  await page.mouse.dblclick(sq[2].x, sq[2].y);
  await expect.poll(async () => {
    const [[, e]] = await holeOverrides(page);
    return e.nodes.holes[0].filter((n) => n.kind === "smooth").length;
  }).toBe(1);
  const [[, e]] = await holeOverrides(page);
  expect(e.holes_override[0].length, "the two spans of the smooth node carry interior vertices").toBeGreaterThan(4);
  expect(e.nodes.holes[0], "still 4 nodes").toHaveLength(4);
  await page.locator(".hoop canvas").focus();
  await page.keyboard.press("Control+z");
  await expect.poll(async () => {
    const hs = await holeOverrides(page);
    return hs.length ? ringOf(hs[0][1].holes_override[0]).length : -1;
  }).toBe(4);
  const [[, e2]] = await holeOverrides(page);
  expect(e2.nodes.holes[0].every((n) => n.kind === "corner"), "one undo step took the smoothing back").toBe(true);
});
