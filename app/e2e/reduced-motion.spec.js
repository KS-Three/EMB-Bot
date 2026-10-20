// prefers-reduced-motion: no autoplay in the stitch simulator, no CSS
// transitions, and the same Studio otherwise. Emulated via Playwright's
// `reducedMotion` context option.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate } from "./helpers.js";

async function reachDesign(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
}

test.describe("reduced motion", () => {
  test.use({ contextOptions: { reducedMotion: "reduce" } });

  test("simulator opens finished and paused instead of autoplaying", async ({ page }) => {
    await reachDesign(page);
    expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(true);
    await page.locator('.zoomctl button[aria-label="Stitch simulator"]').click();
    await expect(page.locator(".simbar")).toBeVisible();
    await expect(page.locator('.simbar button[aria-label="Play"]')).toBeVisible();
    const scrub = page.locator(".simscrub");
    await expect(scrub).toHaveValue(await scrub.getAttribute("max"));
    // Play still works on request.
    await page.locator('.simbar button[aria-label="Play"]').click();
    await expect(page.locator('.simbar button[aria-label="Pause"], .simbar button[aria-label="Play"]')).toBeVisible();
  });

  test("no element animates a transition", async ({ page }) => {
    await reachDesign(page);
    const animated = await page.evaluate(() =>
      [...document.querySelectorAll("button, .tcard, .gpill")].filter((el) => {
        const d = getComputedStyle(el).transitionDuration;
        return d.split(",").some((x) => parseFloat(x) > 0);
      }).length,
    );
    expect(animated).toBe(0);
  });
});

test.describe("no preference", () => {
  test.use({ contextOptions: { reducedMotion: "no-preference" } });

  test("simulator still autoplays", async ({ page }) => {
    await reachDesign(page);
    await page.locator('.zoomctl button[aria-label="Stitch simulator"]').click();
    await expect(page.locator(".simbar")).toBeVisible();
    await expect(page.locator('.simbar button[aria-label="Pause"]')).toBeVisible();
  });
});
