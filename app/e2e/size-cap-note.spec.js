// A typed size the placement cannot take must say so. Height is aspect-locked
// to width, so on a left-chest name a typed 1-inch height is solved to a width
// past the 4-inch placement and capped — and until 2026-10-08 the field just
// went back to "0.29" with no word of why or what would make it bigger.
import { test, expect } from "@playwright/test";
import { startStudio, typeText } from "./helpers.js";

test("a typed height past the placement explains the cap", async ({ page }) => {
  await startStudio(page);
  await typeText(page, "Fritsch's Stitches");

  const height = page.getByRole("spinbutton", { name: "Height" });
  await expect(height).toBeEnabled();
  await height.fill("1");
  await height.press("Enter");

  const note = page.locator(".capnote");
  await expect(note).toBeVisible();
  await expect(note).toContainText("Capped at 4.00 in wide");
  await expect(note).toContainText("Left Chest");
  await expect(height).not.toHaveValue("1");

  // A request that fits clears it.
  const width = page.getByRole("spinbutton", { name: "Width" });
  await width.fill("3");
  await width.press("Enter");
  await expect(note).toHaveCount(0);
});
