// Black thread on a black garment, and nothing said.
//
// The field paints a neutral work bed, not the garment (#648), so the default
// black lettering on the Black swatch looks exactly like it does on White: a
// first-time customer picks their cap colour, downloads, and sews a name that
// disappears into the fabric. The caption note is the one place that says so.
import { test, expect } from "@playwright/test";
import { startStudio, typeText } from "./helpers.js";

test("a thread the same colour as the fabric is flagged on the caption, and clears on a contrasting fabric", async ({ page }) => {
  await startStudio(page);
  await typeText(page, "Fritsch");
  const meta = page.locator(".fieldmeta");
  const note = page.getByTestId("contrast-note");

  // Default fabric (Natural) under the default black thread: quiet.
  await expect(note).toHaveCount(0);

  await page.locator(".fabricrow").getByRole("button", { name: "Black", exact: true }).click();
  await expect(note).toBeVisible();
  await expect(meta).toContainText("Thread color is too close to the fabric color");
  if (process.env.EMB_SHOTS) await page.screenshot({ path: `${process.env.EMB_SHOTS}/after-black-on-black.png` });

  await page.locator(".fabricrow").getByRole("button", { name: "White", exact: true }).click();
  await expect(note).toHaveCount(0);
});
