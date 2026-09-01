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
      dpr: window.devicePixelRatio,
      leftGap: Math.round(C.left - F.left),
      rightGap: Math.round(F.right - C.right),
    };
  });

  // The bitmap covers its displayed size at the screen's own pixel density —
  // an UPSCALED bitmap renders a blurry stitch preview, which is the whole
  // reason this is sized in JS rather than just stretched with CSS. At this
  // context's dpr of 1 that is a plain 1:1; the dpr-2 test below pins the
  // other half, and the two together are what stops a regression to
  // "bitmap = CSS px" from passing here unnoticed.
  const ratio = Math.min(2, geom.dpr);
  expect(geom.intrinsicW).toBe(Math.round(geom.cssW * ratio));
  expect(geom.intrinsicH).toBe(Math.round(geom.cssH * ratio));

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

// --- HiDPI: the bitmap is cut at devicePixelRatio -------------------------

// The preview IS the product, and it was being drawn at half resolution on
// every Retina-class screen: the bitmap was sized in CSS px with no dpr
// multiplier anywhere in the codebase, so the browser upscaled it. A separate
// context because deviceScaleFactor is fixed when the context is created — it
// cannot be changed with setViewportSize the way the width can.
test.describe("on a HiDPI screen", () => {
  test.use({ deviceScaleFactor: 2 });

  test("the canvas bitmap is cut at 2x its CSS box, and pointer maths still lands", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await reachDesign(page);

    const geom = await page.evaluate(() => {
      const cv = document.querySelector(".hoop canvas");
      const C = cv.getBoundingClientRect();
      return { intrinsicW: cv.width, intrinsicH: cv.height, cssW: C.width, cssH: C.height, dpr: window.devicePixelRatio };
    });
    expect(geom.dpr).toBe(2);
    expect(geom.intrinsicW).toBe(Math.round(geom.cssW * 2));
    expect(geom.intrinsicH).toBe(Math.round(geom.cssH * 2));

    // The half a naive "just double the bitmap" gets wrong. Doubling the
    // bitmap WITHOUT scaling the context leaves every drawing coordinate
    // where it was, so the design collapses into the top-left quadrant — and
    // it still passes the size assertions above. Measuring where the ink
    // actually landed is what separates the two.
    //
    // Checked against the real break, per this file's standard, not just
    // written to pass: removing the context scaling measures 0.250 on both
    // axes here and fails the bounds below. (Removing it from ONLY ONE of the
    // two places that set it still passes — the context keeps a transform
    // between calls, so the other call covers for it. preview.spec.js pins
    // the library half directly for that reason.)
    const ink = await page.evaluate(() => {
      const cv = document.querySelector(".hoop canvas");
      const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height).data;
      // The design is near-black thread on pale fabric; anything dark is ink.
      // The alpha test is load-bearing, not defensive: an UNSCALED context
      // paints only the top-left quadrant and leaves the rest of the bitmap
      // transparent, and a transparent pixel is (0,0,0,0) — which passes a
      // colour-only "is it dark" test and drags the measured bbox back out to
      // the full canvas, hiding the exact bug this test exists to catch.
      let minX = Infinity, minY = Infinity, maxX = -1, maxY = -1;
      for (let y = 0; y < cv.height; y++) {
        for (let x = 0; x < cv.width; x++) {
          const i = (y * cv.width + x) * 4;
          if (d[i + 3] > 200 && d[i] < 90 && d[i + 1] < 90 && d[i + 2] < 90) {
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
          }
        }
      }
      if (maxX < 0) return null;
      // As a FRACTION of the bitmap, so the answer is dpr-independent.
      return { cx: (minX + maxX) / 2 / cv.width, cy: (minY + maxY) / 2 / cv.height };
    });
    expect(ink).not.toBeNull();
    // The hoop is centred in the canvas and the template's design is centred
    // in the hoop, so the ink is centred too. An unscaled context would put
    // this near 0.25 on both axes.
    expect(ink.cx).toBeGreaterThan(0.4);
    expect(ink.cx).toBeLessThan(0.6);
    expect(ink.cy).toBeGreaterThan(0.4);
    expect(ink.cy).toBeLessThan(0.6);
  });
});

// --- keyboard placement ---------------------------------------------------

// The field was mouse-only: no way to select, move or nudge a design without
// a pointer, and the canvas carried no accessible name at all.
test("the design can be placed from the keyboard alone", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reachDesign(page);

  const canvas = page.locator(".hoop canvas");

  // Focusable, and named — a screen reader reaching it now hears what is on
  // the field and that the arrows do something.
  await expect(canvas).toHaveAttribute("tabindex", "0");
  await expect(canvas).toHaveAttribute("aria-label", /Embroidery field.*Arrow keys/);

  await canvas.focus();
  expect(await page.evaluate(() => document.activeElement === document.querySelector(".hoop canvas"))).toBe(true);

  // A nudge has to CHANGE the rendered field, not just some state — compare
  // the pixels either side of it.
  const shot = () => page.evaluate(() => document.querySelector(".hoop canvas").toDataURL());
  const before = await shot();

  await page.keyboard.press("ArrowRight");
  await expect.poll(shot, { timeout: 10_000 }).not.toBe(before);

  // And it says where the design landed, for someone who cannot see it move.
  await expect(page.locator(".fieldlive")).toHaveText(/mm (right|left) from center/);

  // Shift is the coarse step, so it must move strictly further than a plain
  // press from the same starting point. Undo back to the origin between the
  // two so they are measured from the same place.
  const readOffset = () => page.evaluate(() => {
    const t = document.querySelector(".fieldlive").textContent || "";
    const m = t.match(/([\d.]+) mm (right|left)/);
    return m ? Number(m[1]) * (m[2] === "right" ? 1 : -1) : 0;
  });
  const afterOne = await readOffset();
  await page.keyboard.press("Shift+ArrowRight");
  await expect.poll(readOffset).toBeGreaterThan(afterOne);
});
