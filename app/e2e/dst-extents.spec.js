// The size the app shows is the size the machine sews (2026-10-08). Type a
// name, pick a font, set the width, download the DST, decode its bytes HERE
// (an independent standard-DST reader, not the app's decoder) and compare the
// extents with the Width/Height the Size panel reports. The existing specs
// check the file is non-empty with the right magic and that the caption and
// field agree with each other (configurator-smoke); none reads the stitches.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { startStudio, pickTemplate, openDownload } from "./helpers.js";

// Standard DST: 512-byte header, then 3-byte records of 0.1 mm units. X is
// the LOW bit of each pair (byte0 bits 0-3, byte1 bits 0-3, byte2 bits 2-3),
// Y the HIGH one (byte0 bits 4-7, ...); the opposite assignment reads the
// design a quarter turn round, which is the 2026-09-08 bug this guards.
function dstExtentsMm(buf) {
  let x = 0, y = 0, minX = 0, maxX = 0, minY = 0, maxY = 0;
  for (let i = 512; i + 2 < buf.length; i += 3) {
    const [b0, b1, b2] = [buf[i], buf[i + 1], buf[i + 2]];
    if ((b2 & 0xf3) === 0xf3) break;          // END
    const bit = (b, n) => (b >> n) & 1;
    y += bit(b0, 7) - bit(b0, 6) + 9 * (bit(b0, 5) - bit(b0, 4))
       + 3 * (bit(b1, 7) - bit(b1, 6)) + 27 * (bit(b1, 5) - bit(b1, 4))
       + 81 * (bit(b2, 5) - bit(b2, 4));
    x += bit(b0, 0) - bit(b0, 1) + 9 * (bit(b0, 2) - bit(b0, 3))
       + 3 * (bit(b1, 0) - bit(b1, 1)) + 27 * (bit(b1, 2) - bit(b1, 3))
       + 81 * (bit(b2, 2) - bit(b2, 3));
    minX = Math.min(minX, x); maxX = Math.max(maxX, x);
    minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  }
  return { w: (maxX - minX) / 10, h: (maxY - minY) / 10 };
}

test("a downloaded DST measures the size the Size panel shows (±0.5 mm)", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");

  // Type a name and pick a font (second tile, so it is not the default).
  const input = page.getByPlaceholder("Type a name or word");
  await input.fill("Kent");
  await page.locator(".fs-trigger").click();
  const fontDialog = page.getByRole("dialog", { name: "Choose a font" });
  await expect(fontDialog).toBeVisible();
  await fontDialog.locator(".fb-tile").nth(1).click();
  await expect(fontDialog).toBeHidden();
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });

  // Set the size in mm.
  await page.locator("select.unitselect").selectOption("mm");
  const w = page.getByLabel("Width");
  await w.fill("60");
  await w.blur();
  await expect.poll(async () => Number(await w.inputValue()), { timeout: 30_000 })
    .toBeGreaterThan(55);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
  const shownW = Number(await w.inputValue());
  const shownH = Number(await page.getByLabel("Height").inputValue());
  expect(shownW).toBeGreaterThan(0);
  expect(shownH).toBeGreaterThan(0);

  await openDownload(page);
  const dl = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const file = await dl;
  const { w: dstW, h: dstH } = dstExtentsMm(readFileSync(await file.path()));

  expect(Math.abs(dstW - shownW), `DST width ${dstW} vs shown ${shownW}`).toBeLessThanOrEqual(0.5);
  expect(Math.abs(dstH - shownH), `DST height ${dstH} vs shown ${shownH}`).toBeLessThanOrEqual(0.5);
});
