// The embroidery field's own chrome: the control bars, the canvas sizing, and
// the stitch simulator. Nothing covered these before — which is exactly how
// the regression this file's second test guards against got in.
//
// Background. The zoom bar, the simulator bar and the drag hint were all
// absolutely positioned INSIDE `.hoop`, i.e. painted on top of the canvas:
// measured at 1440x900 they covered 10,351px, and 18,188px respectively of
// sewable field, and the two bars shared `bottom: var(--space-3)` so they
// collided with each other whenever the simulator was open. Moving them out
// is what these tests pin.
//
// The trap that moving them opened, and why the simulator test exists: the
// paint effect's dependency set reaches `simActive`, because paint() opens
// with stopSim() and stopSim() reads it. So ANY layout change that resizes
// the canvas while the simulator is starting re-enters paint() and switches
// the simulator off in the same tick it was switched on. When the zoom bar
// and the simulator bar stacked vertically, mounting `.simbar` grew the row,
// shrank `.hoop`, fired the ResizeObserver — and the simulator became
// impossible to open at all. The rule that matters is that the control row's
// HEIGHT must not depend on `simActive`; `.fieldbars` keeps the bars in one
// row and `.simbar` out of flow on top of the zoom bar.
//
// This spec was checked against the real regression, not just written to
// pass: re-stacking the bars fails `simulator opens and stays open` on its
// aria-pressed assertion. Note that `.simbar` merely being in flow is NOT
// enough to reproduce it — side by side, the row height is unchanged and the
// simulator works — so a repro has to make them stack.
//
// Code-based @playwright/test spec (`npx playwright test`), not the
// interactive MCP server — same Chromium, but this is the repeatable check.
import { test, expect } from "@playwright/test";

// Lands on the content step with real stitches on the canvas. The quick-start
// template is the shortest route to a design that actually generates.
async function reachDesign(page) {
  await page.goto("/");
  await page.locator(".tcard", { hasText: "Left-chest name" }).click();
  await expect(page.getByText(/^\d+ stitches/)).toBeVisible();
}

// Area of the intersection of two elements' boxes, in CSS px. 0 = no overlap.
async function overlapArea(page, selA, selB) {
  return page.evaluate(([a, b]) => {
    const ea = document.querySelector(a);
    const eb = document.querySelector(b);
    if (!ea || !eb) return null;
    const A = ea.getBoundingClientRect();
    const B = eb.getBoundingClientRect();
    const ox = Math.max(0, Math.min(A.right, B.right) - Math.max(A.left, B.left));
    const oy = Math.max(0, Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top));
    return Math.round(ox * oy);
  }, [selA, selB]);
}

test("field chrome never covers the canvas, and the canvas fills its pane", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reachDesign(page);

  // The controls and the hint are siblings of the canvas, not overlays on it.
  expect(await overlapArea(page, ".zoomctl", ".hoop canvas")).toBe(0);
  expect(await overlapArea(page, ".hintbubble", ".hoop canvas")).toBe(0);

  // `.hoop` holds the canvas and nothing else that could paint over it. (The
  // right-click tool menu and the empty-state hint still live here, but both
  // are conditional and absent in this state.)
  const hoopChildren = await page.locator(".hoop > *").count();
  expect(hoopChildren).toBe(1);

  const geom = await page.evaluate(() => {
    const cv = document.querySelector(".hoop canvas");
    const field = document.querySelector(".field");
    const C = cv.getBoundingClientRect();
    const F = field.getBoundingClientRect();
    return {
      intrinsicW: cv.width,
      intrinsicH: cv.height,
      cssW: Math.round(C.width),
      cssH: Math.round(C.height),
      leftGap: Math.round(C.left - F.left),
      rightGap: Math.round(F.right - C.right),
    };
  });

  // The bitmap matches its displayed size — an upscaled bitmap would render a
  // blurry stitch preview, which is the whole reason this is sized in JS
  // rather than just stretched with CSS.
  expect(geom.intrinsicW).toBe(geom.cssW);
  expect(geom.intrinsicH).toBe(geom.cssH);

  // And it uses the pane rather than sitting in it at a fixed size. It was
  // hardcoded 760x560 in a 980px-wide pane; anything near that old width
  // means the sizing stopped working.
  expect(geom.cssW).toBeGreaterThan(850);
  expect(geom.leftGap).toBe(geom.rightGap); // centred

  // Resizing the window re-sizes the bitmap (the ResizeObserver path).
  await page.setViewportSize({ width: 1200, height: 900 });
  await expect
    .poll(async () => page.evaluate(() => document.querySelector(".hoop canvas").width))
    .toBeLessThan(geom.intrinsicW);
});

test("simulator opens and stays open, without covering the canvas", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reachDesign(page);

  const toggle = page.locator('.zoomctl button[aria-label="Stitch simulator"]');
  const canvasSizeBefore = await page.evaluate(() => {
    const cv = document.querySelector(".hoop canvas");
    return [cv.width, cv.height];
  });

  await toggle.click();

  // The regression this guards: the bar appeared and vanished in the same
  // tick, leaving aria-pressed="false". Assert on the toggle's own state, not
  // just the bar's presence, so a bar that renders but is immediately
  // switched off still fails.
  await expect(page.locator(".simbar")).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");

  // Opening it must not resize the canvas — that resize is what re-entered
  // paint() and called stopSim() on the simulator that had just started.
  expect(
    await page.evaluate(() => {
      const cv = document.querySelector(".hoop canvas");
      return [cv.width, cv.height];
    }),
  ).toEqual(canvasSizeBefore);

  // It covers the zoom bar it replaces, not the field being simulated.
  expect(await overlapArea(page, ".simbar", ".hoop canvas")).toBe(0);

  // Playback actually advances rather than sitting at zero.
  await expect
    .poll(async () => page.locator(".simcount").textContent(), { timeout: 15_000 })
    .toMatch(/^[1-9]\d*\s*\/\s*\d+$/);

  // And closing it hands the field back.
  await page.locator('.simbar button[aria-label="Close simulator"]').click();
  await expect(page.locator(".simbar")).toHaveCount(0);
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
});
