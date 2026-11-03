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
import { test, expect } from "@playwright/test";
import { pickGarment, uploadArtwork, runDigitize, pinDigitizeConfig, openAdvanced } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
const STATS = "span.stats";

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
    skipReason = "digitizer service is not running and no venv python was found. Start it: `python -m digitizer_service` in digitizer/.";
    return;
  }
  serviceProc = spawn(python, ["-m", "digitizer_service"], { cwd: path.resolve(__dirname, "../../digitizer"), stdio: "ignore" });
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (await healthy()) { serviceUp = true; return; }
    await new Promise((r) => setTimeout(r, 500));
  }
  skipReason = "digitizer service failed to answer /health within 30s of being started.";
});

test.afterAll(() => {
  if (serviceProc) serviceProc.kill("SIGTERM");
});

// ---- reading the app -------------------------------------------------------

// The saved project's digitized element: { overrides, shapes } — the committed
// shapeOverrides and the review rows (outlineFull = the service's outline).
async function readDigitized(page) {
  return page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const raw = id && localStorage.getItem("embstudio:p:" + id);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const proj = parsed.project || parsed;
    const el = (proj.elements || []).find((e) => e.type === "digitized");
    if (!el) return null;
    return {
      overrides: el.shapeOverrides || {},
      shapes: ((el.review && el.review.shapes) || []).map((s) => ({ id: s.id, outline: s.outlineFull || s.outline || [], rgb: s.rgb })),
    };
  });
}

// The ring without its explicit closing duplicate, as outlineOf does.
function ringOf(points) {
  const n = points.length;
  if (n >= 2 && Math.abs(points[0][0] - points[n - 1][0]) < 1e-6 && Math.abs(points[0][1] - points[n - 1][1]) < 1e-6) return points.slice(0, n - 1);
  return points;
}

// Vertices that differ between the ring the service sent and the committed
// override: [{ i, dx, dy }] in the service's mm (y-down).
function movedVertices(original, edited, eps = 1e-6) {
  const a = ringOf(original), b = ringOf(edited);
  if (a.length !== b.length) return null;
  const out = [];
  for (let i = 0; i < a.length; i++) {
    const dx = b[i][0] - a[i][0], dy = b[i][1] - a[i][1];
    if (Math.abs(dx) > eps || Math.abs(dy) > eps) out.push({ i, dx, dy });
  }
  return out;
}

// Where the nodes are. two-squares.png digitizes to a black square (left) and a
// red one, each with four vertices, and the black fill is the only near-black
// thing on the canvas (the surround is a lighter slate, the overlay's casing is
// translucent), so the bounding box of near-black pixels IS the black square:
// its corners are its vertices, to a pixel or two (a node's grab radius is 9).
// Returns the four corners in page CSS px.
async function blackSquareCorners(page) {
  const f = await page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const w = c.width, h = c.height;
    const d = c.getContext("2d").getImageData(0, 0, w, h).data;
    let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      if (d[i + 3] > 200 && d[i] < 14 && d[i + 1] < 14 && d[i + 2] < 14) {
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
    }
    return { x0, y0, x1, y1, cw: w };
  });
  expect(f.x1, "a black square is on the canvas").toBeGreaterThan(0);
  const hb = await page.locator(".hoop canvas").boundingBox();
  const k = hb.width / f.cw;
  const at = (x, y) => ({ x: hb.x + x * k, y: hb.y + y * k });
  return { tl: at(f.x0, f.y0), tr: at(f.x1, f.y0), br: at(f.x1, f.y1), bl: at(f.x0, f.y1) };
}

async function statsText(page) {
  return (await page.locator(STATS).count()) ? page.locator(STATS).innerText() : null;
}

// A drag in stages (the 4 px dead zone needs real moves).
async function drag(page, from, to, { alt = false } = {}) {
  await page.mouse.move(from.x, from.y);
  if (alt) await page.keyboard.down("Alt");
  await page.mouse.down();
  await page.mouse.move(to.x, to.y, { steps: 10 });
  await page.mouse.up();
  if (alt) await page.keyboard.up("Alt");
}

// Upload two-squares.png, digitize, and wait for the result to settle.
async function digitizeSquares(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await pinDigitizeConfig(page, { border_by_size: false });
  await uploadArtwork(page, ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  let before = null;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) { reads.push(await page.locator(".dgp-stats").innerText()); await page.waitForTimeout(300); }
    before = reads[0];
    return reads.every((r) => r === reads[0]);
  }, { timeout: 30_000 }).toBe(true);
  return before;
}

// Click inside the left square: selects the shape and opens its popover.
async function clickLeftSquare(page) {
  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + box.width * 0.4, box.y + box.height * 0.5);
  await expect(page.getByRole("dialog", { name: /^Thread #/ })).toBeVisible();
}

async function enterReshape(page) {
  await clickLeftSquare(page);
  await page.getByRole("dialog").getByRole("button", { name: "Edit points" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-reshape", "on");
  await expect(page.getByRole("dialog")).toHaveCount(0);
}

const selectedCount = (page) => page.locator(".hoop canvas").getAttribute("data-reshape-points").then(Number);

// Wait for the Studio's restitch of a committed edit to land: the caption moves.
async function restitched(page, before) {
  const moved = () => page.locator(".dgp-stats").innerText().then((t) => t !== before);
  const ok = await expect.poll(moved, { timeout: 8_000 }).toBe(true).then(() => true, () => false);
  if (ok) return;
  await runDigitize(page);
  await expect.poll(moved, { timeout: 120_000 }).toBe(true);
}

// ---- digitized lane -------------------------------------------------------

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

// ---- hand-drawn lane -----------------------------------------------------

async function drawRectangle(page, { x0 = 0.25, x1 = 0.75, open = true } = {}) {
  if (open) {
    await page.locator(".hoop canvas").click({ button: "right" });
    await page.locator(".fieldmenu button").filter({ hasText: "Draw shapes" }).click();
  }
  await openAdvanced(page);
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

async function readManual(page) {
  return page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const parsed = JSON.parse(localStorage.getItem("embstudio:p:" + id));
    const proj = parsed.project || parsed;
    const el = (proj.elements || []).find((e) => e.type === "manual");
    return el ? { shapes: el.shapes, sizeMm: el.sizeMm } : null;
  });
}

// The dark (stitch) bounding box inside the fabric, in canvas px, optionally
// restricted to columns [xa, xb]; a row or column only counts with MIN_RUN dark
// pixels, so a dot's casing ring is not a box. Same rule as field-node-edit.spec.js.
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
async function darkBBox(page, xa = 0, xb = Infinity) {
  const r = await page.evaluate(([xa, xb, MIN_RUN, boxSrc]) => {
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
    return x0 < 0 || y0 < 0 ? null : { x0, y0, x1, y1, cw: c.width };
  }, [xa, xb, MIN_RUN, FABRIC_BOX_SRC]);
  if (!r) return null;
  const hb = await page.locator(".hoop canvas").boundingBox();
  const k = hb.width / r.cw;
  return { ...r, css: (x, y) => ({ x: hb.x + x * k, y: hb.y + y * k }), k };
}
// Three reads of the caption and the box that all agree: the repo's baseline rule.
async function settle(page, xa = 0, xb = Infinity) {
  let out = null;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) { reads.push({ stats: await statsText(page), bb: await darkBBox(page, xa, xb).then((b) => b && [b.x0, b.y0, b.x1, b.y1]) }); await page.waitForTimeout(250); }
    out = reads[0];
    return out.stats !== null && out.bb !== null && reads.every((r) => JSON.stringify(r) === JSON.stringify(reads[0]));
  }, { timeout: 30_000 }).toBe(true);
  return out;
}

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
