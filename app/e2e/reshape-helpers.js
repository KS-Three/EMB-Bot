// Shared helpers for the three field-reshape-*.spec.js files (split from one
// 1,700-line file 2026-11-07 so the two studio-e2e shards balance). Not a spec:
// the name does not end in .spec.js, so Playwright never collects it.
import { test, expect } from "@playwright/test";
import { pickGarment, uploadArtwork, runDigitize, pinDigitizeConfig, openAdvanced } from "./helpers.js";
import { spawn } from "node:child_process";
import fs, { existsSync, readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const SERVICE_URL = "http://127.0.0.1:8721";
export const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
export const STATS = "span.stats";

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
export let serviceUp = false;
export let skipReason = "";

// Registers the per-file beforeAll/afterAll that bring the digitizer service
// up (or reuse a healthy one) and kill what this file started. Every spec file
// calls it once at its top level: the three reshape files each run on one
// worker and one machine, and a module's state is shared by the files a worker
// loads, so afterAll resets it.
export function useDigitizerService() {
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
    serviceProc = null;
    serviceUp = false;
    skipReason = "";
  });
}

// ---- reading the app -------------------------------------------------------

// The saved project's digitized element: { overrides, shapes } — the committed
// shapeOverrides and the review rows (outlineFull = the service's outline).
export async function readDigitized(page) {
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
export function ringOf(points) {
  const n = points.length;
  if (n >= 2 && Math.abs(points[0][0] - points[n - 1][0]) < 1e-6 && Math.abs(points[0][1] - points[n - 1][1]) < 1e-6) return points.slice(0, n - 1);
  return points;
}

// Vertices that differ between the ring the service sent and the committed
// override: [{ i, dx, dy }] in the service's mm (y-down).
export function movedVertices(original, edited, eps = 1e-6) {
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
export async function blackSquareCorners(page) {
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

export async function statsText(page) {
  return (await page.locator(STATS).count()) ? page.locator(STATS).innerText() : null;
}

// A drag in stages (the 4 px dead zone needs real moves).
export async function drag(page, from, to, { alt = false } = {}) {
  await page.mouse.move(from.x, from.y);
  if (alt) await page.keyboard.down("Alt");
  await page.mouse.down();
  await page.mouse.move(to.x, to.y, { steps: 10 });
  await page.mouse.up();
  if (alt) await page.keyboard.up("Alt");
}

// Upload two-squares.png, digitize, and wait for the result to settle.
export async function digitizeSquares(page) {
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
export async function clickLeftSquare(page) {
  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + box.width * 0.4, box.y + box.height * 0.5);
  await expect(page.getByRole("dialog", { name: /^Thread #/ })).toBeVisible();
}

export async function enterReshape(page) {
  await clickLeftSquare(page);
  await page.getByRole("dialog").getByRole("button", { name: "Edit points" }).click();
  await expect(page.locator(".hoop canvas")).toHaveAttribute("data-reshape", "on");
  await expect(page.getByRole("dialog")).toHaveCount(0);
}

export const selectedCount = (page) => page.locator(".hoop canvas").getAttribute("data-reshape-points").then(Number);

// Wait for the Studio's restitch of a committed edit to land: the caption moves.
export async function restitched(page, before) {
  const moved = () => page.locator(".dgp-stats").innerText().then((t) => t !== before);
  const ok = await expect.poll(moved, { timeout: 8_000 }).toBe(true).then(() => true, () => false);
  if (ok) return;
  await runDigitize(page);
  await expect.poll(moved, { timeout: 120_000 }).toBe(true);
}

// ---- digitized lane -------------------------------------------------------

// ---- hand-drawn lane -----------------------------------------------------

export async function drawRectangle(page, { x0 = 0.25, x1 = 0.75, open = true } = {}) {
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

export async function readManual(page) {
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
export const MIN_RUN = 12;
export const FABRIC_BOX_SRC = `(function (d, w, h) {
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
export async function darkBBox(page, xa = 0, xb = Infinity) {
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
export async function settle(page, xa = 0, xb = Infinity) {
  let out = null;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) { reads.push({ stats: await statsText(page), bb: await darkBBox(page, xa, xb).then((b) => b && [b.x0, b.y0, b.x1, b.y1]) }); await page.waitForTimeout(250); }
    out = reads[0];
    return out.stats !== null && out.bb !== null && reads.every((r) => JSON.stringify(r) === JSON.stringify(reads[0]));
  }, { timeout: 30_000 }).toBe(true);
  return out;
}


// ---- holes (contract v1.9, spec section 7 (e)) -------------------------------
//
// trace-holes-and-colors.png digitizes to a green square with ONE square hole
// (4 corners). The hole is its own ring on the canvas: a node of it drags on its
// own, the commit carries `holes_override` (and no `boundary_override`: the
// shell did not move), and the restitch shows the moved inner edge.
export const HOLES_PNG = path.join(__dirname, "fixtures", "trace-holes-and-colors.png");

export async function digitizeHoled(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await pinDigitizeConfig(page, { border_by_size: false });
  await uploadArtwork(page, HOLES_PNG);
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

// The green square and its hole, in page CSS px, found the way a person finds
// them: green fill (the overlay's casing is translucent and cyan/amber), and
// the non-green stretch through its middle.
export async function greenSquareAndHole(page) {
  const f = await page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const w = c.width, h = c.height;
    const d = c.getContext("2d").getImageData(0, 0, w, h).data;
    const green = (x, y) => { const i = (y * w + x) * 4; return d[i + 3] > 200 && d[i + 1] > 90 && d[i] < 70 && d[i + 2] < 70 && d[i + 1] > d[i] + 40; };
    let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (green(x, y)) {
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    if (x1 < 0) return null;
    const cx = Math.round((x0 + x1) / 2), cy = Math.round((y0 + y1) / 2);
    let hx0 = cx, hx1 = cx, hy0 = cy, hy1 = cy;
    while (hx0 > x0 && !green(hx0 - 1, cy)) hx0--;
    while (hx1 < x1 && !green(hx1 + 1, cy)) hx1++;
    while (hy0 > y0 && !green(cx, hy0 - 1)) hy0--;
    while (hy1 < y1 && !green(cx, hy1 + 1)) hy1++;
    const i = (cy * w + cx) * 4;
    return { x0, y0, x1, y1, hx0, hy0, hx1, hy1, cw: w, garment: [d[i], d[i + 1], d[i + 2]] };
  });
  expect(f, "a green square is on the canvas").not.toBeNull();
  const hb = await page.locator(".hoop canvas").boundingBox();
  const k = hb.width / f.cw;
  const at = (x, y) => ({ x: hb.x + x * k, y: hb.y + y * k });
  return { f, k, at, shell: { tl: at(f.x0, f.y0), tr: at(f.x1, f.y0) }, hole: { tl: at(f.hx0, f.hy0), tr: at(f.hx1, f.hy0), bl: at(f.hx0, f.hy1), br: at(f.hx1, f.hy1) } };
}

// The canvas pixel at a page point.
export function pixelAt(page, pt) {
  return page.evaluate(({ x, y }) => {
    const c = document.querySelector(".hoop canvas");
    const r = c.getBoundingClientRect();
    const px = Math.round((x - r.left) * (c.width / r.width)), py = Math.round((y - r.top) * (c.height / r.height));
    const d = c.getContext("2d").getImageData(px, py, 1, 1).data;
    return [d[0], d[1], d[2]];
  }, pt);
}

export async function readHoled(page) {
  return page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const parsed = JSON.parse(localStorage.getItem("embstudio:p:" + id));
    const proj = parsed.project || parsed;
    const el = (proj.elements || []).find((e) => e.type === "digitized");
    return {
      overrides: el.shapeOverrides || {},
      shapes: ((el.review && el.review.shapes) || []).map((s) => ({ id: s.id, outline: s.outlineFull || [], holes: s.holesFull || [] })),
    };
  });
}

export async function selectGreenShape(page) {
  const g = await greenSquareAndHole(page);
  // The ring's body, a few px inside the left edge: selects the shape, opens the popover.
  await page.mouse.click(g.shell.tl.x + 4 * g.k + 3, (g.shell.tl.y + g.hole.bl.y) / 2);
  await expect(page.getByRole("dialog", { name: /^Thread #/ })).toBeVisible();
  await expect(page.getByTestId("shapepop-holes")).toContainText("Holes: 1");
  await page.keyboard.press("Escape");
  // The page re-lays out once the popover is gone: measure again, aim at that.
  await page.waitForTimeout(400);
  return greenSquareAndHole(page);
}

// The strip's tick (Done) and cross (Discard) sit right of the label, centred
// on the canvas: 30-48 px and 52-70 px right of centre, 7-25 px from the top.
export async function stripButton(page, which) {
  const hb = await page.locator(".hoop canvas").boundingBox();
  return { x: hb.x + hb.width / 2 + (which === "done" ? 39 : 61), y: hb.y + 16 };
}

// ---- sparse smooth nodes (2026-11-05 spec, PR 2) ---------------------------
// The overlay draws a shape's NODES, not its dense vertices: a node is a filled
// amber disc (smooth) or square (corner), 3 x 3 px of solid amber at least; the
// outline itself is a 2 px line. These helpers find nodes the way a person does.

export const RENDERS = path.join(__dirname, "..", "test-results", "sparse-nodes");

// Centres of the amber nodes on the canvas, in page CSS px.
export async function amberNodes(page) {
  const f = await page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const w = c.width, h = c.height;
    const d = c.getContext("2d").getImageData(0, 0, w, h).data;
    const amber = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      if (d[i + 3] > 200 && d[i] > 225 && d[i + 1] > 185 && d[i + 1] < 235 && d[i + 2] < 120) amber[y * w + x] = 1;
    }
    // integral image: a 3 x 3 window all amber
    const S = new Uint32Array((w + 1) * (h + 1));
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      S[(y + 1) * (w + 1) + x + 1] = amber[y * w + x] + S[y * (w + 1) + x + 1] + S[(y + 1) * (w + 1) + x] - S[y * (w + 1) + x];
    }
    const hits = [];
    for (let y = 0; y + 3 <= h; y++) for (let x = 0; x + 3 <= w; x++) {
      const sum = S[(y + 3) * (w + 1) + x + 3] - S[y * (w + 1) + x + 3] - S[(y + 3) * (w + 1) + x] + S[y * (w + 1) + x];
      if (sum === 9) hits.push([x + 1.5, y + 1.5]);
    }
    const clusters = [];
    for (const [x, y] of hits) {
      const c0 = clusters.find((k) => Math.hypot(k.x - x, k.y - y) < 7);
      if (c0) { c0.sx += x; c0.sy += y; c0.n++; c0.x = c0.sx / c0.n; c0.y = c0.sy / c0.n; }
      else clusters.push({ x, y, sx: x, sy: y, n: 1 });
    }
    return { clusters: clusters.map((k) => [k.x, k.y]), cw: w };
  });
  const hb = await page.locator(".hoop canvas").boundingBox();
  const k = hb.width / f.cw;
  return f.clusters.map(([x, y]) => ({ x: hb.x + x * k, y: hb.y + y * k }));
}

// The selected shape's nodes as the canvas reports where it drew them, in page px
// (Reshape mode only): [{ ni, ring (-1 = shell), x, y, corner }].
// The node report is the same on two reads 200 ms apart (a late re-render moves the pixels).
export async function stableNodePx(page) {
  const read = () => page.locator(".hoop canvas").getAttribute("data-reshape-node-px");
  await expect.poll(async () => {
    const a = await read();
    await page.waitForTimeout(200);
    const b = await read();
    return !!a && a === b;
  }, { timeout: 20_000 }).toBe(true);
}

export async function reshapeNodePx(page) {
  const raw = await page.locator(".hoop canvas").getAttribute("data-reshape-node-px");
  const hb = await page.locator(".hoop canvas").boundingBox();
  const cssW = await page.evaluate(() => document.querySelector(".hoop canvas").clientWidth);
  const k = hb.width / cssW;
  return JSON.parse(raw || "[]").map(([ni, ring, x, y, corner]) => ({ ni, ring, x: hb.x + x * k, y: hb.y + y * k, corner: !!corner }));
}

export const nodeCount = (page) => page.locator(".hoop canvas").getAttribute("data-reshape-nodes").then(Number);

export async function digitizeArt(page, png) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await pinDigitizeConfig(page, { border_by_size: false });
  await uploadArtwork(page, png);
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

export async function readNodes(page) {
  const r = await readDigitized(page);
  const e = Object.entries(r.overrides).find(([, v]) => v.nodes);
  return e ? { sid: e[0], entry: e[1], shape: r.shapes.find((s) => s.id === e[0]) } : null;
}

export const shoelace = (ring) => {
  let a = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
  return a / 2;
};
export const perimeter = (ring) => ring.reduce((s, p, i) => s + Math.hypot(ring[(i + 1) % ring.length][0] - p[0], ring[(i + 1) % ring.length][1] - p[1]), 0);
export const kinds = (list) => ({ n: list.length, corner: list.filter((x) => x.kind === "corner").length, smooth: list.filter((x) => x.kind === "smooth").length });

// The vertices of `edited` outside the two spans at node `k` (an index into
// `nodes`, the NEW ring's list) form one contiguous run of `original`, in order.
export function outsideTwoSpansIsOriginal(original, edited, nodes, k) {
  const N = nodes.length;
  const start = nodes[(k + 1) % N].i, end = nodes[(k - 1 + N) % N].i;
  const run = [];
  for (let i = start; ; i = (i + 1) % edited.length) { run.push(edited[i]); if (i === end) break; }
  const orig = ringOf(original);
  const near = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-4;
  const at = orig.findIndex((p) => near(p, run[0]));
  if (at < 0) return false;
  return run.every((p, m) => near(p, orig[(at + m) % orig.length]));
}
