// GUARDS for the Studio's core customer flows (foreman's ask, 2026-10-08,
// after Kent found two features gone that no test noticed: the digitizing
// busy indicator and zooming to 800%).
//
// Each test here pins ONE thing a customer does, at the level of "is it
// still there and does it still do something" — not the fine behaviour,
// which the feature's own spec owns. They are the tripwire: when one goes
// red, a feature vanished. Kept fast for the studio-e2e job: everything but
// the digitize test runs on the browser lettering lane (no service), off the
// "Left-chest name" template, which fits its hoop so no oversize confirm
// stands between a click and a download.
//
// A test marked `test.fail()` pins a feature that is broken on main TODAY.
// It passes while the regression stands and turns RED the moment someone
// fixes it — on purpose: whoever fixes it deletes the `test.fail()` line in
// the same PR, and the guard then holds the fix.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate, openDownload, uploadArtwork, runDigitize } from "./helpers.js";
import { readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
const SERVICE_URL = "http://127.0.0.1:8721";

async function lettering(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
  // The "Drag the design to move it" hint sits ABOVE the field and goes on
  // the first field interaction, moving the canvas up ~76 px mid-gesture —
  // a drag measured against the old box lands on empty field. Dismiss it
  // first so every canvas coordinate below is read off the final layout.
  const hint = page.getByRole("button", { name: "Dismiss hint" }).first();
  if (await hint.isVisible().catch(() => false)) await hint.click();
  await expect(page.locator(".hoop canvas")).toBeVisible();
}

const zoomPct = (page) => page.locator(".zoompct");
const zoomIn = (page) => page.getByRole("button", { name: "Zoom in" });
const zoomOut = (page) => page.getByRole("button", { name: "Zoom out" });

// The selected element of the saved project — the only place a move's
// offsets are readable (the caption reports size and stitch count, not
// position). Saves are asynchronous, so callers poll.
async function savedElement(page) {
  return page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const raw = id && localStorage.getItem("embstudio:p:" + id);
    if (!raw) return null;
    const p = JSON.parse(raw);
    const el = (p.elements || []).find((e) => e.id === p.selectedId) || (p.elements || [])[0];
    return el ? { offsetXMm: el.offsetXMm || 0, offsetYMm: el.offsetYMm || 0, sizeMm: el.sizeMm ?? null } : null;
  });
}

// Mean x of thread-black pixels on the field canvas (thread core reads under
// 28 on every channel; the dark surround sits at ~35, the hoop at ~125).
async function inkCentroidX(page) {
  return page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let sx = 0, n = 0;
    for (let i = 0, px = 0; i < d.length; i += 4, px++) {
      if (d[i] < 28 && d[i + 1] < 28 && d[i + 2] < 28) { sx += px % c.width; n++; }
    }
    return n ? sx / n / (c.width / c.getBoundingClientRect().width) : null;
  });
}

// ---- upload + auto-digitize ------------------------------------------------

test("upload a logo, Auto Digitize shows it is busy while it runs, and stitches land", async ({ page }) => {
  test.setTimeout(180_000);
  let up = false;
  for (let i = 0; i < 30 && !up; i++) {
    up = await fetch(SERVICE_URL + "/health").then((r) => r.ok).catch(() => false);
    if (!up) await new Promise((r) => setTimeout(r, 1000));
  }
  test.skip(!up, "digitizer service not reachable on 8721 (npm run dev starts it when digitizer/.venv exists)");

  // Hold the submit for 1.5 s so the in-flight state is observable even when
  // the service answers from its job cache (another spec may have sent the
  // same fixture first).
  await page.route(SERVICE_URL + "/digitize", async (route) => {
    await new Promise((r) => setTimeout(r, 1500));
    await route.continue();
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await uploadArtwork(page, ART_PNG, { run: false });
  await expect(page.locator(".dgp-run")).toBeEnabled({ timeout: 30_000 });
  await runDigitize(page);

  // Busy while running: the button says so and cannot be pressed twice, and
  // a live status line says what is happening.
  const run = page.locator(".dgp-run");
  await expect(run).toHaveText("Digitizing…");
  await expect(run).toBeDisabled();
  await expect(page.locator(".dgp-status[role=status]").first()).toBeVisible();

  await expect(page.locator("span.stats")).toHaveText(/[\d,]+ stitches · [\d.]+×[\d.]+ mm/, { timeout: 120_000 });
  await expect(run).toHaveText("Auto Digitize Image");
  await expect(run).toBeEnabled();
});

// ---- zoom + pan -----------------------------------------------------------

test("zoom in and out across the whole range; the buttons stop at each end", async ({ page }) => {
  await lettering(page);
  await expect(zoomPct(page)).toHaveText("100%");
  await expect(zoomOut(page)).toBeDisabled();
  let last = 100;
  for (let i = 0; i < 20 && (await zoomIn(page).isEnabled()); i++) {
    await zoomIn(page).click();
    const now = parseInt(await zoomPct(page).innerText(), 10);
    expect(now).toBeGreaterThan(last);
    last = now;
  }
  await expect(zoomIn(page)).toBeDisabled();
  expect(last).toBeGreaterThanOrEqual(400);
  for (let i = 0; i < 20 && (await zoomOut(page).isEnabled()); i++) await zoomOut(page).click();
  await expect(zoomPct(page)).toHaveText("100%");
  await expect(zoomOut(page)).toBeDisabled();
  // Fit to hoop is the one-click way home from any zoom.
  await zoomIn(page).click();
  await page.getByRole("button", { name: "Fit to hoop" }).click();
  await expect(zoomPct(page)).toHaveText("100%");
});

test("zoom reaches 800%", async ({ page }) => {
  // REGRESSION reported by Kent 2026-10-08: "can't zoom to 800%" — the field
  // stopped at 400%. Fixed by PR #676 (MAX_ZOOM back to 8); now a plain guard.
  await lettering(page);
  for (let i = 0; i < 20 && (await zoomIn(page).isEnabled()); i++) await zoomIn(page).click();
  expect(parseInt(await zoomPct(page).innerText(), 10)).toBeGreaterThanOrEqual(800);
});

test("zoomed in, dragging empty field pans the view", async ({ page }) => {
  await lettering(page);
  await zoomIn(page).click();
  await zoomIn(page).click();
  await expect(zoomPct(page)).not.toHaveText("100%");
  let before = null;
  await expect.poll(async () => {
    const a = await inkCentroidX(page);
    await page.waitForTimeout(250);
    const b = await inkCentroidX(page);
    before = b;
    return a != null && Math.abs(a - b) < 0.5;
  }, { timeout: 15_000 }).toBe(true);
  // Empty field well clear of the centred lettering: its top-left corner.
  const box = await page.locator(".hoop canvas").boundingBox();
  const x = box.x + 60, y = box.y + 60;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 120, y + 20, { steps: 8 });
  await page.mouse.up();
  await expect.poll(() => inkCentroidX(page), { timeout: 10_000 }).toBeGreaterThan(before + 60);
  // Panning is a VIEW change: the zoom held, and the design did not move.
  await expect(zoomPct(page)).not.toHaveText("100%");
});

// ---- select / move / resize ------------------------------------------------

test("drag the design to move it, and a corner to resize it", async ({ page }) => {
  await lettering(page);
  await expect.poll(() => savedElement(page), { timeout: 10_000 }).not.toBeNull();
  const start = await savedElement(page);
  const caption = page.locator("span.stats");
  const sizeBefore = (await caption.innerText()).match(/([\d.]+)×([\d.]+) mm/)[1];

  // Click the lettering at the canvas centre (the template centres it), then
  // drag it right. The element trails the pointer by a small dead zone
  // (field-shape-popover.spec.js), so +80 px clears any threshold.
  const box = await page.locator(".hoop canvas").boundingBox();
  const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
  await page.mouse.click(cx, cy);
  await page.mouse.move(cx, cy);
  await page.mouse.down();
  await page.mouse.move(cx + 80, cy, { steps: 8 });
  await page.mouse.up();
  await expect.poll(async () => (await savedElement(page)).offsetXMm, { timeout: 10_000 })
    .toBeGreaterThan(start.offsetXMm + 1);   // the 92 mm name is hoop-clamped to ~4.7 mm of travel

  // Resize: the selection's bottom-right handle, read off the overlay the
  // field draws (lettering's box is wide and short; aim just inside the
  // corner the move left it at).
  const handle = await page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const overlay = [...document.querySelectorAll(".hoop canvas")].pop();
    const r = c.getBoundingClientRect();
    const d = overlay.getContext("2d").getImageData(0, 0, overlay.width, overlay.height).data;
    const k = overlay.width / r.width;
    // Selection handles are filled indigo squares (#6366f1-ish): blue high,
    // red/green mid. The lowest-rightmost such pixel is the BR handle.
    let best = null;
    for (let i = 0, px = 0; i < d.length; i += 4, px++) {
      if (d[i + 2] > 200 && d[i] > 70 && d[i] < 130 && d[i + 1] > 70 && d[i + 1] < 130) {
        const x = px % overlay.width, y = Math.floor(px / overlay.width);
        if (!best || x + y > best.x + best.y) best = { x, y };
      }
    }
    return best && { x: r.x + best.x / k - 2, y: r.y + best.y / k - 2 };
  });
  expect(handle).not.toBeNull();
  await page.mouse.move(handle.x, handle.y);
  await page.mouse.down();
  await page.mouse.move(handle.x - 60, handle.y - 6, { steps: 8 });
  await page.mouse.up();
  await expect.poll(async () => (await caption.innerText()).match(/([\d.]+)×([\d.]+) mm/)[1], { timeout: 15_000 })
    .not.toBe(sizeBefore);
  const w = parseFloat((await caption.innerText()).match(/([\d.]+)×([\d.]+) mm/)[1]);
  expect(w).toBeLessThan(parseFloat(sizeBefore));
});

// ---- colour + undo/redo ----------------------------------------------------

test("change the thread colour, then Undo and Redo it", async ({ page }) => {
  await lettering(page);
  const swatch = page.getByRole("button", { name: /^Thread color — / }).first();
  await expect(swatch).toBeVisible();
  const before = await swatch.getAttribute("aria-label");
  await swatch.click();
  // The first cell whose name is not the current colour.
  const current = before.replace(/^Thread color — /, "");
  const pick = page.locator(`button.tp-cell:not([aria-label="${current}"])`).first();
  await expect(pick).toBeVisible();
  const picked = await pick.getAttribute("aria-label");
  await pick.click();
  await page.keyboard.press("Escape");
  await expect(swatch).toHaveAttribute("aria-label", `Thread color — ${picked}`);

  const undo = page.getByRole("button", { name: "Undo" });
  const redo = page.getByRole("button", { name: "Redo" });
  await expect(undo).toBeEnabled();
  await undo.click();
  await expect(swatch).toHaveAttribute("aria-label", before);
  await expect(redo).toBeEnabled();
  await redo.click();
  await expect(swatch).toHaveAttribute("aria-label", `Thread color — ${picked}`);
});

// ---- export ----------------------------------------------------------------

for (const [fmt, magic] of [["DST", "LA:"], ["PES", "#PES"], ["EXP", null]]) {
  test(`export ${fmt} downloads a real, non-empty file`, async ({ page }) => {
    await lettering(page);
    await openDownload(page);
    const btn = page.locator(".formats button", { hasText: new RegExp(`^${fmt}$`) });
    await expect(btn).toBeEnabled();
    const dl = page.waitForEvent("download");
    await btn.click();
    const file = await dl;
    expect(file.suggestedFilename().toLowerCase()).toMatch(new RegExp(`\\.${fmt.toLowerCase()}$`));
    const p = await file.path();
    expect(statSync(p).size).toBeGreaterThan(200);
    if (magic) expect(readFileSync(p).subarray(0, magic.length).toString("latin1")).toBe(magic);
  });
}
