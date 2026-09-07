// Fritsch's Stitches, typed two ways, must be one design.
//
// A customer types an apostrophe; their phone, Word, Notes and every paste
// buffer substitute U+2019 for it. 26 of the 85 shipped fonts have no glyph
// for that codepoint, so the character was dropped SILENTLY — measured
// 2026-09-07 in the shipped app, "Fritsch's Stitches" gave 1,354 stitches
// straight and 1,326 curly, and the note explaining it named a character
// indistinguishable from the one they typed, inside quotation marks made of
// the same mark, then advised switching fonts.
//
// Driven end to end rather than left to the engine tests because the whole
// point is what the CUSTOMER sees: the same caption, and no note.
import { test, expect } from "@playwright/test";

async function type(page, text) {
  await page.locator("textarea").first().fill(text);
  await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 20000 });
  // Settle: the caption is repainted on every generate.
  await page.waitForTimeout(600);
  return (await page.locator("span.stats").first().innerText()).replace(/\s+/g, " ").trim();
}

test("a curly apostrophe sews the same design as a straight one, and says nothing", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();

  const straight = await type(page, "Fritsch's Stitches");
  await expect(page.getByText(/can.t stitch/i)).toHaveCount(0);

  const curly = await type(page, "Fritsch’s Stitches");
  expect(curly).toBe(straight);
  // The note is the tell: before the fold it named "’" and told the
  // customer to switch fonts.
  await expect(page.getByText(/can.t stitch/i)).toHaveCount(0);
});

test("an em dash sews as a hyphen rather than vanishing", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const hyphen = await type(page, "Mom - 2026");
  const emdash = await type(page, "Mom — 2026");
  expect(emdash).toBe(hyphen);
  await expect(page.getByText(/can.t stitch/i)).toHaveCount(0);
});

test("a character with no ASCII twin still gets its message", async ({ page }) => {
  // The fold must not have swallowed the explanation it replaced. Japanese
  // folds to nothing and no shipped font covers it, so this takes
  // unsupportedMessage's third variant — which deliberately does NOT say
  // "this font can't stitch", because the current font is not the problem.
  // (A first draft looked for that phrase and failed, correctly.)
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("Emb 日本");
  await expect(page.getByText(/No font in this library can stitch/i)).toBeVisible({ timeout: 20000 });
});

test("a font that cannot set the text still names the fonts that can", async ({ page }) => {
  // The other surviving variant: Cyrillic IS covered, by three fonts. The
  // fold must not have made this message unreachable either.
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("Русский");
  await expect(page.getByText(/Switch fonts and it will stitch/i)).toBeVisible({ timeout: 20000 });
});
