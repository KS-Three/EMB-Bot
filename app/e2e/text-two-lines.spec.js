// A first-time customer types a two-word name. Auto-fit makes it as wide as
// the left-chest placement, so a long single line sews 7 mm tall with most
// strokes under 1 mm — and the text box reads as a one-line field, so the fix
// that keeps every word (a line break) is the one nobody tries. The field
// offers it as one click beside the thin-lettering note.
import { test, expect } from "@playwright/test";
import { startStudio, typeText } from "./helpers.js";

test("a thin one-line name gets a one-click 'Put on two lines' that clears the note", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await typeText(page, "Fritsch's Stitches");

  const meta = page.locator(".fieldmeta");
  await expect(meta).toContainText(/% of this lettering is under/);
  const before = (await meta.textContent()).match(/(\d+)×(\d+) mm/);
  expect(Number(before[2])).toBeLessThan(10);

  await meta.getByRole("button", { name: "Put on two lines" }).click();

  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue("Fritsch's\nStitches");
  await expect(meta).not.toContainText(/% of this lettering is under/);
  await expect(meta.getByRole("button", { name: "Put on two lines" })).toHaveCount(0);
  const after = (await meta.textContent()).match(/(\d+)×(\d+) mm/);
  expect(Number(after[2])).toBeGreaterThan(3 * Number(before[2]));
});

test("no line-break offer on a single word, which has no space to break at", async ({ page }) => {
  await startStudio(page);
  await typeText(page, "Fritsch");
  await expect(page.locator(".fieldmeta").getByRole("button", { name: "Put on two lines" })).toHaveCount(0);
});
