// A customer typing a Russian name opens the font browser to find a font that
// can sew it. Before this, the browser knew nothing about their text: all 85
// tiles looked equally good and most of them could not stitch a single
// Cyrillic letter ("This font can't stitch ...", then click blind).
import { test, expect } from "@playwright/test";

test("the font browser can narrow to fonts that stitch the typed text", async ({ page }) => {
  await page.goto("/");
  await page.locator("textarea").first().fill("Привет");
  await page.locator(".fs-trigger").click();
  const dialog = page.getByRole("dialog", { name: "Choose a font" });
  await expect(dialog).toBeVisible();

  const tiles = dialog.locator(".fb-tile");
  await expect(tiles.first()).toBeVisible();
  const all = await tiles.count();
  expect(all).toBeGreaterThan(20);

  const chip = dialog.getByRole("button", { name: /^Fits your text/ });
  await expect(chip).toBeVisible();
  await chip.click();
  await expect(chip).toHaveAttribute("aria-pressed", "true");

  const fit = await tiles.count();
  expect(fit).toBeGreaterThan(0);
  expect(fit).toBeLessThan(10); // three shipped fonts cover Cyrillic
  await expect(chip).toContainText(`(${fit})`);

  // Unfiltered, the others are flagged rather than left looking usable.
  await chip.click();
  await expect(tiles).toHaveCount(all);
  await expect(dialog.getByText("Can’t stitch all your text").first()).toBeVisible();
});

test("plain Latin text flags only the few fonts that cannot sew it", async ({ page }) => {
  await page.goto("/");
  await page.locator("textarea").first().fill("FRITSCH");
  await page.locator(".fs-trigger").click();
  const dialog = page.getByRole("dialog", { name: "Choose a font" });
  await expect(dialog.locator(".fb-tile").first()).toBeVisible();
  await expect(dialog.getByRole("button", { name: /^Fits your text/ })).toBeVisible();
  expect(await dialog.locator(".fb-tile.misfit").count()).toBeLessThan(6);
});
