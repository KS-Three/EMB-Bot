// A first-time customer opens the Studio and uploads their logo. A fresh
// design opens on one empty text box, and the upload used to be seeded as a
// SECOND element beside it: 40% of the hoop's width (42 x 8 mm in the 5x7,
// where typed text fits the left-chest placement at ~102 mm) and staggered
// up, with a "Text · empty" row left in the list that sews nothing. A logo
// that small loses its lettering. The art now replaces the untouched text
// box and sizes like the first element it is.
//
// Browser lane (`/health` aborted) so the upload sews on its own and the
// size is readable without the service.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { startStudio, uploadArtwork, typeText } from "./helpers.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LOGO = path.join(__dirname, "fixtures", "enthusiast_logo.png");

const caption = (page) => page.getByText(/^[\d,]+ stitches · \d+×\d+ mm/);
async function sewnWidthMm(page) {
  await expect(caption(page)).toBeVisible({ timeout: 60_000 });
  return Number(/· (\d+)×\d+ mm/.exec(await caption(page).innerText())[1]);
}

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.route("**/health", (r) => r.abort());
  await startStudio(page);
});

test("artwork uploaded onto a fresh design fills the placement and leaves no empty text row", async ({ page }) => {
  await uploadArtwork(page, LOGO, { run: false });
  await expect(page.locator(".elrow")).toHaveCount(1);
  await expect(page.locator(".elrow", { hasText: "Text · empty" })).toHaveCount(0);
  // The same placement typed text auto-fits to (~102 mm); 42 mm before the fix.
  expect(await sewnWidthMm(page)).toBeGreaterThan(80);
});

test("artwork added after typed text still lands as a second element", async ({ page }) => {
  await typeText(page, "Ann");
  await uploadArtwork(page, LOGO, { run: false });
  await expect(page.locator(".elrow")).toHaveCount(2);
  await expect(page.locator(".elrow", { hasText: "Ann" })).toHaveCount(1);
});
