// The "?" keyboard-shortcuts overlay: opens on "?", never while typing,
// closes on Esc / Close / backdrop and hands focus back.
import { test, expect } from "@playwright/test";
import { startStudio } from "./helpers.js";

test("? opens the shortcuts list; Esc closes it and restores focus", async ({ page }) => {
  await startStudio(page);
  const dlg = page.getByRole("dialog", { name: "Keyboard shortcuts" });
  await expect(dlg).toHaveCount(0);

  await page.getByRole("button", { name: "Font credits" }).focus();
  await page.keyboard.press("Shift+?");
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText("Redo", { exact: true })).toBeVisible();
  await expect(dlg.getByText("Nudge the selected design 1 mm")).toBeVisible();
  await expect(dlg.getByText("Finish the shape")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(dlg).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Font credits" })).toBeFocused();
});

test("? typed into a text field does not open the overlay", async ({ page }) => {
  await startStudio(page);
  const input = page.getByPlaceholder("Type a name or word");
  await input.click();
  await input.pressSequentially("Hi?");
  await expect(input).toHaveValue("Hi?");
  await expect(page.getByRole("dialog", { name: "Keyboard shortcuts" })).toHaveCount(0);
});

test("Close button and backdrop dismiss it; ? does not stack on another dialog", async ({ page }) => {
  await startStudio(page);
  const dlg = page.getByRole("dialog", { name: "Keyboard shortcuts" });
  await page.locator("body").press("Shift+?");
  await expect(dlg).toBeVisible();
  await dlg.getByRole("button", { name: "Close" }).click();
  await expect(dlg).toHaveCount(0);

  await page.locator("body").press("Shift+?");
  await expect(dlg).toBeVisible();
  await page.mouse.click(5, 5);
  await expect(dlg).toHaveCount(0);

  await page.getByRole("button", { name: "Font credits" }).click();
  await expect(page.getByRole("dialog", { name: "Font licenses & credits" })).toBeVisible();
  await page.keyboard.press("Shift+?");
  await expect(dlg).toHaveCount(0);
});
