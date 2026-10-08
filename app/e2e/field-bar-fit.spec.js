// The control bar under the field must fit the field on a laptop.
//
// It held icons + words above 1280px and icons alone below, by a viewport
// media query written for a 400px panel. The panel widens to 460px from
// 1400px up and the bar gained the Original segment, so from 1281px to
// ~1500px the labelled bar ran wider than the field — measured 2026-10-08
// at 1366x768 (952px of bar in 918px) and 1440x900 (959px in 932px).
// Centred, it spilled off both ends: Zoom out half past the left edge,
// Auto-snap past the right, and the bar does not scroll. 1366 and 1440 are
// the two commonest laptop widths, so most first-time customers met it.
//
// The fix keys the labels to the bar's own width (a container query), so
// this asserts on what the customer sees — every button inside the pane —
// across the widths where it broke and the ones either side.
//
// Checked against the regression: with the old `@media (max-width: 1280px)`
// rule restored, 1300, 1366, 1400 and 1440 fail on Zoom out and Auto-snap.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate } from "./helpers.js";

for (const [width, height] of [[1280, 800], [1300, 800], [1366, 768], [1400, 900], [1440, 900], [1536, 864], [1920, 1080]]) {
  test(`every field control is on screen at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await startStudio(page);
    await pickTemplate(page, "Left-chest name");
    await expect(page.locator(".fieldbars")).toBeVisible();

    const clipped = await page.evaluate(() => {
      const bar = document.querySelector(".fieldbars");
      const pane = bar.parentElement.getBoundingClientRect();
      return [...bar.querySelectorAll("button")]
        .map((b) => ({ name: b.getAttribute("aria-label"), r: b.getBoundingClientRect() }))
        .filter(({ r }) => r.width > 0 && (r.left < pane.left - 0.5 || r.right > pane.right + 0.5))
        .map(({ name, r }) => `${name} [${Math.round(r.left)}..${Math.round(r.right)}] outside [${Math.round(pane.left)}..${Math.round(pane.right)}]`);
    });
    expect(clipped).toEqual([]);

    // And the ends are clickable, not merely inside the box.
    await expect(page.getByRole("button", { name: "Zoom in" })).toBeEnabled();
    await page.getByRole("button", { name: "Zoom in" }).click();
    await page.getByRole("button", { name: "Zoom out" }).click();
    await expect(page.locator(".zoompct")).toHaveText("100%");
  });
}

test("labels stay on where the bar has room for them", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
  await expect(page.locator(".zoomlabel").first()).toBeVisible();
});
