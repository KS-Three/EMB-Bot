// The empty canvas is the only place in EMB-Bot that says the drawing tools
// exist. Two of PRODUCT.md's four launch-scope items live behind them —
// "Basic shapes tool" and the manual draw lane — and the way in is a
// right-click on the canvas (Kent's placement call, 2026-08-13: a tool, not
// an upload button).
//
// That sentence used to name the gesture to everyone. Measured 2026-09-07
// against the production build:
//
//   - a phone context reports `(any-pointer: fine)` FALSE, so the app can
//     tell no mouse is attached, and said "Right-click" anyway;
//   - a real 1.4-second long-press on the canvas, dispatched through CDP
//     rather than as a synthetic event, produced ZERO contextmenu events and
//     never opened the menu, while a real right-click on a desktop context
//     opened it every time;
//   - no button anywhere in the app reaches those two tools — the
//     contextmenu handler is the only route in the code.
//
// So this file drives both device shapes and asserts the sentence matches
// the device. It is an e2e rather than a unit test because the thing under
// test is a browser capability: `emptyFieldHint`'s own branches are covered
// in generate.spec.js, and what could still break here is the wiring — the
// media query being read too late to reach the first paint, which is exactly
// how a phone would have kept the desktop sentence.
import { test, expect } from "@playwright/test";

const HINT = "p.fieldhint";   // the empty-canvas line, and nothing else

test.describe("a device with a mouse", () => {
  test.use({ viewport: { width: 1440, height: 960 } });

  test("is told about the right-click tool menu, and it opens", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.locator(HINT)).toContainText(/right-click the canvas for drawing tools/i);

    // Not just the advice — the lever it names. Both launch-scope tools.
    const canvas = page.locator("canvas").first();
    await canvas.click({ button: "right" });
    const menu = page.locator(".fieldmenu");
    await expect(menu).toBeVisible();
    await expect(menu).toContainText("Draw shapes");
    await expect(menu).toContainText("Basic shape");
  });
});

test.describe("a device with no mouse", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

  test("is never told to right-click, and is pointed at a lane it has", async ({ page }) => {
    await page.goto("/");
    // The premise. If this fails the emulation stopped being a phone, and the
    // assertions below would pass for the wrong reason.
    expect(await page.evaluate(() => matchMedia("(any-pointer: fine)").matches)).toBe(false);

    await page.getByRole("button", { name: "Next", exact: true }).tap();
    const hint = page.locator(HINT);
    await expect(hint).toBeVisible();
    await expect(hint).not.toContainText(/right-click/i);
    await expect(hint).toContainText(/mouse/i);
    await expect(hint).toContainText(/text/i);
    await expect(hint).toContainText(/artwork/i);
  });

  test("the lane it is pointed at actually works there", async ({ page }) => {
    // The sentence is only honest if typing really does produce a design on
    // this device. Driven with taps and no mouse events at all.
    await page.goto("/");
    await page.getByRole("button", { name: "Next", exact: true }).tap();
    const ta = page.locator("textarea").first();
    await ta.tap();
    await ta.fill("Fritsch");
    await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 20000 });
    // And the hint is gone, because there is a design now.
    await expect(page.locator(HINT)).toHaveCount(0);
  });
});
