// Compare view (2026-11-07): the uploaded artwork and its realistic stitches
// laid over each other at the same scale and registration, with a vertical
// split — artwork LEFT, stitches RIGHT — dragged by pointer or moved by keys.
//
// What this pins, on the browser lane (no service) with two synthetic
// fixtures:
//  - registration: the artwork's red box vs the red thread's box, in canvas
//    px at fit and again after a zoom (the zoom repaints through
//    repaintView, so the two canvases must stay locked together). Two
//    numbers, because they mean different things: the CENTRE offset is the
//    registration (one transform for both canvases: <= 1.5 px), and the
//    per-EDGE gap is mostly the thread itself — a sewn edge stands proud of
//    the drawn one by the thread's width and the fill's pull allowance, so
//    the stitched box is a few px bigger all round (<= 6 px at fit, 1440x900);
//  - overlay only: lighting Compare moves nothing in `.fieldwrap`;
//  - the split moves by CSS clip alone: dragging and keying it repaint
//    nothing (data-paint-seq is unchanged);
//  - the handle's keys are its own — arrows / Shift / Home / End — and Tab
//    still leaves it.
//
// COMPARE_SHOTS=1 also writes the screenshots the PR quotes into
// docs/compare-view-2026-11-07/ (synthetic fixtures only).
import { test, expect } from "@playwright/test";
import path from "node:path";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { startStudio, uploadArtwork } from "./helpers.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = process.env.COMPARE_SHOTS ? path.resolve(__dirname, "../../docs/compare-view-2026-11-07") : null;

// The field alone, without the view button's tooltip over it. Leaves focus
// where it was (the handle test reads it next).
async function shot(page, name) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  await page.mouse.move(2, 2);
  await page.evaluate(() => document.querySelectorAll(".tipbubble, [role=tooltip]").forEach((t) => (t.style.display = "none")));
  await page.locator(".hoop").screenshot({ path: path.join(SHOTS, name) });
}

const FIXTURES = [
  // White ground, one black and one (204, 0, 0) red square.
  { name: "two-squares", file: "two-squares.png", red: 204 },
  // A (200, 0, 0) disc on a transparent ground: the content box is the disc.
  { name: "red-disc", file: "red-disc.png", red: 200 },
];

// Bbox of red in one canvas's own bitmap px. `exact` = the source red the
// artwork is drawn in; otherwise red-ish thread (shaded, never that exact red
// over an area — configurator-smoke's Original-view test measured 0 px).
function redBox(page, selector, red, exact) {
  return page.evaluate(([selector, red, exact]) => {
    let c = document.querySelector(selector);
    if (!c) return null;
    // The artwork side is an <img> of an offscreen bitmap: read it back at
    // its own (device-px) size, the field canvas's bitmap size.
    if (c.tagName === "IMG") {
      if (!c.complete || !c.naturalWidth) return null;
      const t = document.createElement("canvas");
      t.width = c.naturalWidth;
      t.height = c.naturalHeight;
      t.getContext("2d").drawImage(c, 0, 0);
      c = t;
    }
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1, n = 0;
    for (let y = 0; y < c.height; y++) {
      for (let x = 0; x < c.width; x++) {
        const i = (y * c.width + x) * 4;
        const hit = exact
          ? Math.abs(d[i] - red) <= 2 && d[i + 1] <= 2 && d[i + 2] <= 2 && d[i + 3] === 255
          : d[i] > 120 && d[i + 1] < 70 && d[i + 2] < 70;
        if (!hit) continue;
        n++;
        if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
    }
    return x1 < 0 ? null : { x0, y0, x1, y1, n };
  }, [selector, red, exact]);
}

// The worst edge, in canvas px, between the artwork's red and the thread's.
async function registration(page, red) {
  const stitches = await redBox(page, ".hoop canvas", red, false);
  const art = await redBox(page, ".hoop img.cmp-art", red, true);
  expect(stitches, "no red thread on the field canvas").not.toBeNull();
  expect(art, "no artwork red on the compare canvas").not.toBeNull();
  const err = {};
  for (const k of ["x0", "y0", "x1", "y1"]) err[k] = Math.abs(art[k] - stitches[k]);
  const centre = {
    dx: Math.abs((art.x0 + art.x1) / 2 - (stitches.x0 + stitches.x1) / 2),
    dy: Math.abs((art.y0 + art.y1) / 2 - (stitches.y0 + stitches.y1) / 2),
  };
  return { stitches, art, err, max: Math.max(...Object.values(err)), centre: Math.max(centre.dx, centre.dy) };
}

const paintSeq = (page) => page.locator(".hoop canvas").getAttribute("data-paint-seq");
const box = (page, sel) => page.evaluate((sel) => {
  const r = document.querySelector(sel).getBoundingClientRect();
  return { x: r.x, y: r.y, w: r.width, h: r.height };
}, sel);

async function openCompare(page, fixture) {
  await page.route("**/health", (r) => r.abort()); // browser lane: an `image` element
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await uploadArtwork(page, path.join(__dirname, "fixtures", fixture.file), { run: false, engine: "browser" });
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  const compare = page.getByRole("button", { name: "Compare view" });
  await expect(compare).toBeEnabled();
  return compare;
}

for (const fx of FIXTURES) {
  test(`Compare view registers the artwork on its stitches: ${fx.name}`, async ({ page }, info) => {
    const compare = await openCompare(page, fx);
    const before = { wrap: await box(page, ".fieldwrap"), canvas: await box(page, ".hoop canvas") };
    await compare.click();
    await expect(compare).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: "Original view" })).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByTestId("compare-split")).toBeVisible();
    // The artwork lands on the compare canvas asynchronously (image decode).
    await expect.poll(async () => ((await redBox(page, ".hoop img.cmp-art", fx.red, true)) || { n: 0 }).n).toBeGreaterThan(100);

    // Overlay only: nothing in the field pane moved or resized.
    expect(await box(page, ".fieldwrap")).toEqual(before.wrap);
    expect(await box(page, ".hoop canvas")).toEqual(before.canvas);
    // Still exactly one <canvas> in .hoop; the artwork <img> is the field
    // canvas's bitmap size and lies exactly over it.
    expect(await page.locator(".hoop canvas").count()).toBe(1);
    const sizes = await page.evaluate(() => {
      const c = document.querySelector(".hoop canvas"), im = document.querySelector(".hoop img.cmp-art");
      const rc = c.getBoundingClientRect(), ri = im.getBoundingClientRect();
      return [[c.width, c.height, rc.x, rc.y, rc.width, rc.height], [im.naturalWidth, im.naturalHeight, ri.x, ri.y, ri.width, ri.height]];
    });
    expect(sizes[1]).toEqual(sizes[0]);

    const atFit = await registration(page, fx.red);
    info.annotations.push({ type: "registration-at-fit", description: `${fx.name}: centre ${atFit.centre} px, worst edge ${atFit.max} px ${JSON.stringify(atFit.err)} art ${JSON.stringify(atFit.art)} stitches ${JSON.stringify(atFit.stitches)}` });
    console.log(`[compare] ${fx.name} at fit: centre ${atFit.centre} px, worst edge ${atFit.max} px`, JSON.stringify(atFit));
    expect(atFit.centre, JSON.stringify(atFit)).toBeLessThanOrEqual(1.5);
    expect(atFit.max, JSON.stringify(atFit)).toBeLessThanOrEqual(6);
    await shot(page, `${fx.name}-split-50.png`);

    // A zoom is a view change: repaintView repaints both sides, which must
    // still register.
    await page.getByRole("button", { name: "Zoom in" }).click();
    await page.getByRole("button", { name: "Zoom in" }).click();
    await expect(page.locator(".zoompct")).not.toHaveText("100%");
    // Zoomed, a px is a smaller distance and the same sub-px rounding of the
    // two boxes reads a little larger (measured 1.0-1.5 px at 150%).
    // The artwork <img> follows a beat behind (its bitmap is re-encoded after
    // the repaint, one per zoom step), so wait until it shows the FINAL zoom:
    // a stale step reads as a big edge gap (measured 75 px mid-zoom).
    const fitW = atFit.art.x1 - atFit.art.x0;
    let zoomed = null;
    await expect.poll(async () => {
      zoomed = await registration(page, fx.red);
      return zoomed.art.x1 - zoomed.art.x0 > fitW && zoomed.centre <= 2.5 && zoomed.max <= 10;
    }).toBe(true);
    info.annotations.push({ type: "registration-zoomed", description: `${fx.name}: centre ${zoomed.centre} px, worst edge ${zoomed.max} px at ${await page.locator(".zoompct").innerText()}` });
    console.log(`[compare] ${fx.name} zoomed: centre ${zoomed.centre} px, worst edge ${zoomed.max} px`, JSON.stringify(zoomed));
    expect((zoomed.art.x1 - zoomed.art.x0)).toBeGreaterThan(atFit.art.x1 - atFit.art.x0);
  });
}

test("Compare split: drag the handle, then move it from the keyboard; nothing repaints and the field keeps its keys", async ({ page }) => {
  const fx = FIXTURES[0];
  const compare = await openCompare(page, fx);
  await compare.click();
  const handle = page.getByRole("separator", { name: "Compare split" });
  await expect(handle).toBeVisible();
  await expect(handle).toHaveAttribute("aria-valuenow", "50");
  await expect.poll(async () => ((await redBox(page, ".hoop img.cmp-art", fx.red, true)) || { n: 0 }).n).toBeGreaterThan(100);
  const seq0 = await paintSeq(page);
  const caption = await page.locator("span.stats").innerText();

  // Drag from the grip to a quarter of the way across.
  const hoop = await box(page, ".hoop");
  const h = await handle.boundingBox();
  await page.mouse.move(h.x + h.width / 2, h.y + h.height / 2);
  await page.mouse.down();
  await page.mouse.move(hoop.x + hoop.w * 0.4, h.y + h.height / 2, { steps: 4 });
  await page.mouse.move(hoop.x + hoop.w * 0.25, h.y + h.height / 2, { steps: 4 });
  await page.mouse.up();
  await expect(handle).toHaveAttribute("aria-valuenow", "25");
  await expect(handle).toHaveAttribute("aria-valuetext", "Artwork 25%, stitches 75%");
  const clip = await page.locator(".hoop img.cmp-art").evaluate((c) => c.style.clipPath);
  expect(clip).toBe("inset(0px 75% 0px 0px)");
  const hb = await handle.boundingBox();
  expect(Math.abs(hb.x + hb.width / 2 - (hoop.x + hoop.w * 0.25))).toBeLessThanOrEqual(1.5);
  await shot(page, "two-squares-split-25.png");

  // The drag left the handle focused: the keys are its own.
  await expect(handle).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(handle).toHaveAttribute("aria-valuenow", "27");
  await page.keyboard.press("Shift+ArrowRight");
  await expect(handle).toHaveAttribute("aria-valuenow", "37");
  await page.keyboard.press("ArrowLeft");
  await expect(handle).toHaveAttribute("aria-valuenow", "35");
  await page.keyboard.press("End");
  await expect(handle).toHaveAttribute("aria-valuenow", "100");
  await page.keyboard.press("Home");
  await expect(handle).toHaveAttribute("aria-valuenow", "0");
  // The simulator / node-cursor keys are not the handle's: nothing moves.
  for (const k of ["[", "]", "<", ">", ",", "."]) await page.keyboard.press(k);
  await expect(handle).toHaveAttribute("aria-valuenow", "0");

  // No paint and no repaint: the split is a CSS clip. And the design did not
  // move (an arrow reaching the field would have nudged it).
  expect(await paintSeq(page)).toBe(seq0);
  expect(await page.locator("span.stats").innerText()).toBe(caption);
  await expect(compare).toHaveAttribute("aria-pressed", "true");

  // Tab leaves the handle (no trap).
  await page.keyboard.press("Tab");
  await expect(handle).not.toBeFocused();

  // Leaving Compare for another view removes the overlay: .hoop is back to
  // the canvas alone.
  await page.getByRole("button", { name: "Realistic view" }).click();
  await expect(compare).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByTestId("compare-split")).toHaveCount(0);
  expect(await page.locator(".hoop > *").count()).toBe(1);

  // Compare and the simulator are exclusive, like Original.
  await compare.click();
  await expect(page.getByTestId("compare-split")).toBeVisible();
  await page.getByRole("button", { name: "Stitch simulator" }).click();
  await expect(compare).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByTestId("compare-split")).toHaveCount(0);
  await page.getByRole("button", { name: "Close simulator" }).click();
});
