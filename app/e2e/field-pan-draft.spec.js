// A pan drag shifts the last finished render instead of re-stroking every
// strand, then settles on one exact render (2026-11-08).
//
// Counted on the `.hoop` canvas: every stroke() call. A full render draws
// each thread as strokes, so the count of one ordinary render (the zoom click)
// is the yardstick; a pan DRAFT frame strokes only the ground (hoop, grid).
// Pixels: a drag out and back lands on the exact view the zoom click made
// (zoom z, pan 0,0); its resting frame must equal that ordinary render
// byte for byte.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate } from "./helpers.js";

const FIELD = ".hoop canvas";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__strokes = 0;
    const stroke = CanvasRenderingContext2D.prototype.stroke;
    CanvasRenderingContext2D.prototype.stroke = function () {
      const c = this.canvas;
      if (c && c.closest && c.closest(".hoop")) window.__strokes++;
      return stroke.apply(this, arguments);
    };
  });
});

const strokes = (page) => page.evaluate(() => window.__strokes);
const zero = (page) => page.evaluate(() => { window.__strokes = 0; });
const settle = (page, ms = 600) => page.evaluate((t) => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, t)))), ms);
const frameHash = (page) => page.locator(FIELD).evaluate(async (c) => {
  const buf = new TextEncoder().encode(c.toDataURL("image/png"));
  const d = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(d), (b) => b.toString(16).padStart(2, "0")).join("");
});

test("pan drag: drag frames do not re-stroke the design; the resting frame is the exact render", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
  await settle(page);

  // The yardstick: one ordinary render (a zoom click is never a draft).
  await zero(page);
  await page.getByRole("button", { name: "Zoom in" }).click();
  await settle(page);
  const full = await strokes(page);
  expect(full).toBeGreaterThan(200);

  // Press on empty field (a corner, off the design) and drag out and back.
  const box = await page.locator(FIELD).boundingBox();
  const x0 = box.x + 12;
  const y0 = box.y + 12;
  await page.mouse.click(x0, y0);
  await settle(page);
  const reference = await frameHash(page);

  // One drag of (dx, dy): a burst of moves with no round trip between them
  // (the 120 ms rest timer must not fire inside it), then one short wait for
  // the rAF repaints and the count read while the pointer is still held.
  async function drag(dx, dy) {
    await page.mouse.move(x0, y0);
    await page.mouse.down();
    await settle(page, 300); // a press may repaint once (selection); not a pan frame
    await zero(page);
    for (let i = 1; i <= 8; i++) await page.mouse.move(x0 + (dx * i) / 8, y0 + (dy * i) / 8);
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 30)))));
    const during = await strokes(page);
    await zero(page);
    await page.mouse.up();
    await settle(page);
    return { during, after: await strokes(page) };
  }

  // Out: 8 moves, each at most one repaint. If any re-stroked the design this
  // is >= one full render; a draft frame strokes only the ground (hoop, grid).
  const out = await drag(48, 32);
  expect(out.during, `strokes during the drag vs ${full} for ONE full render`).toBeLessThan(full / 2);
  expect(out.during).toBeGreaterThan(0); // the ground WAS redrawn at the new view
  // Release owes ONE exact render of the new view (not cached: a full one).
  expect(out.after).toBe(full);

  // Back to where it began: another uncached view, so another full render,
  // and its pixels must be the ordinary render taken before any drag.
  const back = await drag(-48, -32);
  expect(back.during).toBeLessThan(full / 2);
  expect(back.after).toBe(full);
  expect(await frameHash(page)).toBe(reference);
});
