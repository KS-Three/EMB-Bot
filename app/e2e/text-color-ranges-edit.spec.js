// Per-letter colour has to survive the customer fixing a typo.
//
// Colour ranges are stored as character indices into the text. Before
// lib/colorRanges.js they were never moved when the text changed, so a
// customer who coloured "Stitches" red and then added the missing apostrophe
// in "Fritschs" got red on " Stitche" and a navy final "s" — in the preview
// AND in the downloaded file, which reads the same indices. Found 2026-10-08
// by driving the text tool as a customer would; the before/after pictures
// are in docs/renders/text-color-ranges-2026-10-08/.
import { test, expect } from "@playwright/test";
import { typeText } from "./helpers.js";

async function selectInTextarea(page, start, end) {
  const ta = page.getByPlaceholder("Type a name or word");
  await ta.evaluate((el, [s, e]) => {
    el.focus();
    el.setSelectionRange(s, e);
    el.dispatchEvent(new Event("select"));
  }, [start, end]);
}

async function colourSelection(page, threadName) {
  const offer = page.locator(".cr-pending");
  await offer.getByRole("button", { name: /^Thread color/ }).click();
  await offer.getByRole("option", { name: threadName, exact: true }).click();
}

test("a coloured word keeps its colour when an earlier typo is fixed", async ({ page }, testInfo) => {
  await page.goto("/");
  await typeText(page, "Fritschs Stitches");

  await selectInTextarea(page, 9, 17); // "Stitches"
  await expect(page.locator(".cr-pending")).toContainText('"Stitches"');
  await colourSelection(page, "Scarlet");
  await expect(page.locator(".cr-text")).toHaveText('"Stitches"');
  await page.screenshot({ path: testInfo.outputPath("1-stitches-red.png") });

  // Fix the typo: put the caret after "Fritsch" and type the apostrophe.
  await selectInTextarea(page, 7, 7);
  await page.keyboard.type("'");
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue("Fritsch's Stitches");

  await page.waitForTimeout(600); // let the preview repaint before the picture
  await page.screenshot({ path: testInfo.outputPath("2-after-typo-fix.png") });
  await expect(page.locator(".cr-text")).toHaveText('"Stitches"');
});

test("typing over a selection does not leave a stale 'Color …' offer behind", async ({ page }) => {
  await page.goto("/");
  await typeText(page, "Fritsch");
  await selectInTextarea(page, 0, 7);
  await expect(page.locator(".cr-pending")).toContainText('"Fritsch"');

  // Replace the selected text without a key-up (paste, autocorrect, dictation).
  await page.getByPlaceholder("Type a name or word").fill("Fritsch's Stitches");
  await expect(page.locator(".cr-pending")).toHaveCount(0);
});
