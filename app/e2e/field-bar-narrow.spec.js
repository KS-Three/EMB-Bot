// At 1024x768 the control bar under the field was wider than the field even
// icons-only, so it spilled off BOTH ends (Zoom out at x -59..-31, Auto-snap
// clipped) and the bar does not scroll. It now wraps onto a second row.
// Complements field-bar-fit.spec.js (1280+), which keys the labels to width.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate } from "./helpers.js";

for (const [width, height] of [[1024, 768], [1100, 800]]) {
  test(`every field control is on screen at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await startStudio(page);
    await pickTemplate(page, "Left-chest name");
    await expect(page.locator(".zoomctl")).toBeVisible();
    const clipped = await page.evaluate(() => {
      const pane = document.querySelector(".fieldbars").getBoundingClientRect();
      return [...document.querySelectorAll(".zoomctl button")]
        .map((b) => ({ n: b.getAttribute("aria-label") || b.textContent.trim(), r: b.getBoundingClientRect() }))
        .filter(({ r }) => r.width > 0 && (r.left < pane.left - 0.5 || r.right > pane.right + 0.5))
        .map(({ n, r }) => `${n} [${Math.round(r.left)}..${Math.round(r.right)}]`);
    });
    expect(clipped).toEqual([]);
    await page.getByRole("button", { name: "Zoom in" }).click();
    await page.getByRole("button", { name: "Zoom out" }).click();
    await expect(page.locator(".zoompct")).toHaveText("100%");
  });
}
