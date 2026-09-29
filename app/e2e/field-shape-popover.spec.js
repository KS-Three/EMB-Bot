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
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
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
async function firstDarkColumn(page) {
  return page.evaluate(() => {
    const c2 = document.querySelector(".hoop canvas");
    const d = c2.getContext("2d").getImageData(0, 0, c2.width, c2.height).data;
    for (let x = 0; x < c2.width; x++) for (let y = 0; y < c2.height; y++) {
      const i = (y * c2.width + x) * 4;
      if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) return x;
    }
    return -1;
  });
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

test("digitized lane: click inside a square opens the Layers row's controls; Border restitches at once", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await page.waitForTimeout(1200);
  const before = await page.locator(".dgp-stats").innerText();

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
  const rows = page.getByRole("button", { name: /^Edit shapes/ });
  if ((await rows.getAttribute("aria-expanded")) !== "true") await rows.click();
  await expect.poll(() => page.locator('select[aria-label^="Border — "]').evaluateAll((els) => els.map((e) => e.value))).toContain("auto");
});
