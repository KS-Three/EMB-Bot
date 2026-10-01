// End-to-end for the click-to-edit popover (2026-09-29 spec §7). Three
// tests: the hand-drawn lane needs no service; the digitized lane drives the
// real digitizer through the real field; the third proves a drag is still a
// drag. Service bootstrap and fixture copied from field-border-menu.spec.js,
// per this directory's convention of self-contained specs.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");

async function healthy() {
  try { const r = await fetch(SERVICE_URL + "/health"); if (!r.ok) return false; const h = await r.json(); return !!h && h.status === "ok"; }
  catch (e) { return false; }
}
function venvPythonCandidates() {
  const roots = [path.resolve(__dirname, "../..")];
  try {
    const stat = readFileSync(path.join(roots[0], ".git"), "utf8");
    const m = stat.match(/^gitdir:\s*(.+)$/m);
    if (m) { const mainRoot = path.resolve(m[1].trim(), "../../.."); if (mainRoot !== roots[0]) roots.push(mainRoot); }
  } catch (e) { /* .git is a directory */ }
  const out = [];
  for (const root of roots) {
    out.push(path.join(root, "digitizer", ".venv", "bin", "python"));
    out.push(path.join(root, "digitizer", ".venv", "Scripts", "python.exe"));
  }
  return out.filter(existsSync);
}
let serviceProc = null, serviceUp = false, skipReason = "";
test.beforeAll(async () => {
  if (await healthy()) { serviceUp = true; return; }
  const [python] = venvPythonCandidates();
  if (!python) { skipReason = "digitizer service not running and no venv python found"; return; }
  serviceProc = spawn(python, ["-m", "digitizer_service"], { cwd: path.resolve(__dirname, "../../digitizer"), stdio: "ignore" });
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) { if (await healthy()) { serviceUp = true; return; } await new Promise((r) => setTimeout(r, 500)); }
  skipReason = "digitizer service failed to answer /health within 30s";
});
test.afterAll(() => { if (serviceProc) serviceProc.kill("SIGTERM"); });

const STATS = "span.stats";

async function toContent(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
}

// Draw a rectangle on ManualPanel's canvas: four clicks at fractions of the
// canvas's displayed box, then Enter to finish (the panel's own key).
// `x0`/`x1` are the rectangle's left/right as fractions of the canvas width;
// `open: false` skips the field menu when the drawing panel is already up.
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

async function hoopCentre(page) {
  const box = await page.locator(".hoop canvas").boundingBox();
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

// First dark (stitch) pixel column on the hoop canvas, in canvas px; -1 if none.
// The canvas outside the hoop is a dark surround since 2026-09-30, so "dark"
// is thread only INSIDE the fabric: both samplers below find the fabric
// first (the bounding box of the pale pixels, pulled in 3% a side so the
// hoop's rounded corners stay out) and read within it. Same rule as
// field-chrome.spec.js's ink test.
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

async function firstDarkColumn(page) {
  return page.evaluate((boxSrc) => {
    const fabricBox = eval(boxSrc);
    const c2 = document.querySelector(".hoop canvas");
    const d = c2.getContext("2d").getImageData(0, 0, c2.width, c2.height).data;
    const f = fabricBox(d, c2.width, c2.height);
    if (!f) return -1;
    for (let x = f.x0; x <= f.x1; x++) for (let y = f.y0; y <= f.y1; y++) {
      const i = (y * c2.width + x) * 4;
      if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) return x;
    }
    return -1;
  }, FABRIC_BOX_SRC);
}

test("hand-drawn lane: click inside the shape opens its popover; Satin restitches; Escape closes", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  // Two rectangles, so the panel's selection (finishShape selects the shape it
  // just finished) sits on Shape 2 before the field is touched: the click on
  // Shape 1 then has to MOVE the selection, not merely find it already there.
  await drawRectangle(page, { x0: 0.15, x1: 0.45 });
  await drawRectangle(page, { x0: 0.55, x1: 0.85, open: false });
  await expect(page.locator(".mp-shaperow")).toHaveCount(2);
  await expect(page.locator(".mp-shaperow").nth(1)).toHaveClass(/sel/);
  const before = await page.locator(STATS).innerText();

  // The element is a small block centred in the hoop (not the whole canvas), so
  // find Shape 1 from the pixels: its left edge is the first dark column, and
  // 30 CSS px in (the shape is ~100 wide) is well inside it.
  const hb = await page.locator(".hoop canvas").boundingBox();
  const cw = await page.evaluate(() => document.querySelector(".hoop canvas").width);
  const left = await firstDarkColumn(page);
  expect(left).toBeGreaterThan(0);
  await page.mouse.click(hb.x + left / (cw / hb.width) + 30, hb.y + hb.height / 2);
  const dlg = page.getByRole("dialog", { name: "Shape 1 · Fill" });
  await expect(dlg).toBeVisible();
  // The side panel's row followed the field's selection: Shape 2 -> Shape 1.
  await expect(page.locator(".mp-shaperow").first()).toHaveClass(/sel/);
  await expect(page.locator(".mp-shaperow.sel")).toHaveCount(1);

  await dlg.getByRole("combobox", { name: "Stitch type" }).selectOption("satin");
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 20_000 }).not.toBe(before);
  // The panel's own control agrees.
  await expect(page.locator(".mp-assign .mp-btn.active")).toHaveText("Satin");
  // ...and so does the dialog's name, re-derived from the shape.
  await expect(page.getByRole("dialog", { name: "Shape 1 · Satin" })).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Empty fabric: click well outside the rectangle — no dialog.
  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + 12, box.y + 12);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("a drag that starts inside a shape moves the element and opens nothing", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await drawRectangle(page);
  // Settle: the baseline is the first column that three consecutive reads,
  // 200 ms apart, agree on (a fixed sleep could sample mid-render).
  let beforeCol = -2;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) { reads.push(await firstDarkColumn(page)); await page.waitForTimeout(200); }
    beforeCol = reads[0];
    return reads[0] > 0 && reads.every((r) => r === reads[0]);
  }, { timeout: 15_000 }).toBe(true);
  const hb = await page.locator(".hoop canvas").boundingBox();
  const scale = await page.evaluate(() => document.querySelector(".hoop canvas").width) / hb.width;
  const c = await hoopCentre(page);
  await page.mouse.move(c.x, c.y);
  await page.mouse.down();
  await page.mouse.move(c.x + 60, c.y + 10, { steps: 8 });
  await page.mouse.up();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  // The drag is +60 CSS px in x; the column is read in canvas px. MEASURED
  // 2026-09-29: the element trails the pointer by a constant ~15 px dead zone
  // (drags of 20/40/60 px moved it 5/25/45), so a +40 drag would only just clear
  // a 30 px bar; +60 moves it ~45 and leaves margin either way.
  await expect.poll(() => firstDarkColumn(page), { timeout: 10_000 }).toBeGreaterThanOrEqual(beforeCol + 30 * scale);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

// Column runs (gap > 10 canvas px splits a run) of the pixels matching `kind`
// on the hoop canvas: "amber" is the selected outline's core stroke,
// rgba(255, 214, 64, 0.95) in drawShapeOutlines; "dark" is black thread.
async function columnRuns(page, kind) {
  return page.evaluate(([kind, boxSrc]) => {
    const fabricBox = eval(boxSrc);
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    const f = fabricBox(d, c.width, c.height) || { x0: 0, x1: c.width - 1, y0: 0, y1: c.height - 1 };
    const on = new Uint8Array(c.width);
    for (let y = f.y0; y <= f.y1; y++) for (let x = f.x0; x <= f.x1; x++) {
      const i = (y * c.width + x) * 4;
      const hit = kind === "amber"
        ? d[i] > 230 && d[i + 1] > 190 && d[i + 1] < 235 && d[i + 2] < 110
        : d[i] < 60 && d[i + 1] < 60 && d[i + 2] < 60;
      if (hit) on[x] = 1;
    }
    const out = [];
    let start = -1, last = -100;
    for (let x = 0; x < c.width; x++) {
      if (!on[x]) continue;
      if (x - last > 10) { if (start >= 0) out.push([start, last]); start = x; }
      last = x;
    }
    if (start >= 0) out.push([start, last]);
    return out;
  }, [kind, FABRIC_BOX_SRC]);
}

test("Delete in the side panel, or Backspace on its draft, never deletes the field's selected shape", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await drawRectangle(page, { x0: 0.15, x1: 0.45 });
  await drawRectangle(page, { x0: 0.55, x1: 0.85, open: false });
  const rows = page.locator(".mp-shaperow");
  await expect(rows).toHaveCount(2);

  // Select Shape 1 ON THE FIELD (its popover names it), then close the popover.
  const hb = await page.locator(".hoop canvas").boundingBox();
  const cw = await page.evaluate(() => document.querySelector(".hoop canvas").width);
  const left = await firstDarkColumn(page);
  expect(left).toBeGreaterThan(0);
  await page.mouse.click(hb.x + left / (cw / hb.width) + 30, hb.y + hb.height / 2);
  await expect(page.getByRole("dialog", { name: "Shape 1 · Fill" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Now work in the side panel: pick Shape 2 there and press Delete. The
  // panel deletes ITS selection; the field's window listener must not also
  // delete Shape 1 (it did: one keypress, both shapes gone).
  await rows.nth(1).click();
  await page.keyboard.press("Delete");
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("Shape 1");

  // Start a draft on the panel's canvas and take its node back with
  // Backspace (the panel's documented gesture): Shape 1, still selected on
  // the field, must survive.
  const mp = page.locator(".mp-canvas");
  const box = await mp.boundingBox();
  await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.9);
  await page.keyboard.press("Backspace");
  // Both handlers run on the one keydown and Svelte flushes once after it,
  // so a wrong deletion is already in the DOM here (it showed as 0 rows).
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("Shape 1");

  // ...and Delete aimed AT THE FIELD still works: select Shape 1 there,
  // Escape (which hands focus back to the canvas), Delete.
  const left2 = await firstDarkColumn(page);
  expect(left2).toBeGreaterThan(0);
  await page.mouse.click(hb.x + left2 / (cw / hb.width) + 30, hb.y + hb.height / 2);
  await expect(page.getByRole("dialog", { name: "Shape 1 · Fill" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".hoop canvas")).toBeFocused();
  await page.keyboard.press("Delete");
  await expect(rows).toHaveCount(0);
});

test("two preset circles: selecting one highlights only that one, and switching elements drops it", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  const cv = page.locator(".hoop canvas");
  const addCircle = async () => {
    const b = await cv.boundingBox(); // re-read: the drag hint shifts the canvas
    await page.mouse.click(b.x + 10, b.y + 10, { button: "right" });
    await page.locator(".fieldmenu button").filter({ hasText: "Basic shape" }).click();
  };
  // Circle A sits at the hoop's left edge, circle B at the centre: apart, so
  // each outline is its own run of columns. Both have the shape id "shape".
  await addCircle();
  await page.getByRole("button", { name: "Left", exact: true }).click();
  await addCircle();
  await expect(page.locator(".elrow", { hasText: "Circle" })).toHaveCount(2);
  const hint = page.getByRole("button", { name: "Dismiss hint" });
  if (await hint.count()) await hint.click();

  // Settle on two separate dark blobs: three consecutive reads agree.
  let dark = [];
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) { reads.push(JSON.stringify(await columnRuns(page, "dark"))); await page.waitForTimeout(300); }
    dark = JSON.parse(reads[0]);
    return dark.length === 2 && reads.every((r) => r === reads[0]);
  }, { timeout: 20_000 }).toBe(true);
  const [a, b] = dark;
  const hb = await cv.boundingBox();
  const cw = await page.evaluate(() => document.querySelector(".hoop canvas").width);
  const toPage = (x) => hb.x + x * (hb.width / cw);

  // Click inside B: its popover opens, and exactly ONE outline is amber —
  // B's. Before the selection was tagged by element, both were.
  await page.mouse.click(toPage((b[0] + b[1]) / 2), hb.y + hb.height / 2);
  await expect(page.getByRole("dialog", { name: "Circle" })).toHaveCount(1);
  await expect.poll(() => columnRuns(page, "amber")).toHaveLength(1);
  const [lit] = await columnRuns(page, "amber");
  expect(lit[0]).toBeGreaterThan(a[1]); // right of A: it is B's outline
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Switch to A from its element row. The shape selection belonged to B, so
  // it drops: nothing is amber, and a Delete on the canvas touches nothing.
  await page.locator(".elrow", { hasText: "Circle" }).first().click();
  await expect.poll(() => columnRuns(page, "amber")).toHaveLength(0);
  await cv.focus();
  await page.keyboard.press("Delete");
  await expect(page.locator(".elrow", { hasText: "Circle" })).toHaveCount(2);
  await expect.poll(() => columnRuns(page, "amber")).toHaveLength(0);
});

test("digitized lane: click inside a square opens the Layers row's controls; Border restitches at once", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  // Settle: the baseline is the stats text three consecutive reads, 300 ms
  // apart, agree on. A fixed sleep could take it before a late restitch
  // landed, and that restitch alone would then satisfy the "changed" poll.
  let before = null;
  await expect.poll(async () => {
    const reads = [];
    for (let i = 0; i < 3; i++) { reads.push(await page.locator(".dgp-stats").innerText()); await page.waitForTimeout(300); }
    before = reads[0];
    return reads.every((r) => r === reads[0]);
  }, { timeout: 30_000 }).toBe(true);

  // Inside the LEFT square: the fixture is two squares side by side, centred.
  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + box.width * 0.4, box.y + box.height * 0.5);
  const dlg = page.getByRole("dialog", { name: /^Thread #/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByRole("combobox", { name: "Stitch type" })).toBeVisible();
  await expect(dlg.getByRole("combobox", { name: "Border" })).toHaveValue("default");

  await dlg.getByRole("combobox", { name: "Border" }).selectOption("auto");
  await expect.poll(() => page.locator(".dgp-stats").innerText(), { timeout: 120_000 }).not.toBe(before);

  // The panel's own Border select reads the same value.
  await page.getByRole("tab", { name: "Shapes" }).click();
  const rows = page.getByRole("button", { name: /^Edit shapes/ });
  if ((await rows.getAttribute("aria-expanded")) !== "true") await rows.click();
  await expect.poll(() => page.locator('select[aria-label^="Border — "]').evaluateAll((els) => els.map((e) => e.value))).toContain("auto");
});
