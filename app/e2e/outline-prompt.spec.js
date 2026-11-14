// The thin-outline prompt, in the real app against the real service.
//
// Kent, 2026-11-13: "When it gets digitized can you have items like this
// throb/pulse and glow (ask user to keep or remove)". "Items like this" are
// the hairline outline a logo draws round its shapes: the digitizer sews it as
// one fine line and marks the shapes (`review.shapes[].hairline_outline`,
// contract v1.10), and the Studio glows them on the design and asks.
//
// What this pins, end to end, on the logo he showed
// (digitizer/testdata/art/commons_lettering/hed_p_e_logo.png, Left Chest):
//   - the question is on the panel's FIRST screen, not inside Advanced (the
//     first build put it beside the attention warnings, where the real app
//     never showed it);
//   - the marked shapes glow on the canvas (`data-outline-glow` counts rings);
//   - Remove drops their stitches at once, stops the glow, and leaves the
//     design waiting on Auto Digitize (nothing re-runs by itself);
//   - Put back undoes that, and does not ask again.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { uploadArtwork, watchConsole } from "./helpers.js";
import { useDigitizerService, __dirname, STATS } from "./reshape-helpers.js";

const LOGO = path.resolve(__dirname, "../../digitizer/testdata/art/commons_lettering/hed_p_e_logo.png");
const ASK = '[data-testid="outline-ask"]';
const GONE = '[data-testid="outline-removed"]';
const CANVAS = ".hoop canvas";

// A dev seam for running this spec beside another session's service: the
// app's own `embstudio:digitizerUrl` override, set before the page loads.
const OTHER_SERVICE = process.env.EMB_E2E_DIGITIZER_URL || null;

useDigitizerService();

const stitches = async (page) => {
  const m = (await page.locator(STATS).innerText()).match(/([\d,]+) stitches/);
  return m ? parseInt(m[1].replace(/,/g, ""), 10) : null;
};

test("a logo's thin outline glows, and Keep / Remove / Put back do what they say", async ({ page }) => {
  test.setTimeout(240_000);
  // Remove and Put back each change the design, and the Studio ABORTS the
  // size recount already in flight (`POST /recount`): a cancelled request the
  // browser reports as failed. Its own doing, not a fault.
  const seen = watchConsole(page, { ignore: [/\/recount$/] });
  if (OTHER_SERVICE) {
    await page.addInitScript((url) => localStorage.setItem("embstudio:digitizerUrl", url), OTHER_SERVICE);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await uploadArtwork(page, LOGO);

  // The question, on the first screen.
  const ask = page.locator(ASK);
  await expect(ask).toBeVisible({ timeout: 180_000 });
  await expect(ask).toContainText(/thin outline \(\d+ shapes?, glowing on the design\)/);
  const sewn = await stitches(page);
  expect(sewn).toBeGreaterThan(0);

  // The shapes it is about glow.
  await expect.poll(async () => Number(await page.locator(CANVAS).getAttribute("data-outline-glow"))).toBeGreaterThan(0);
  await expect(page.locator(".dgp-run")).toHaveAttribute("data-stale", "false");

  // Remove: their stitches go at once, the glow stops, the design waits.
  await ask.getByRole("button", { name: "Remove" }).click();
  await expect(page.locator(GONE)).toBeVisible();
  await expect(ask).toHaveCount(0);
  await expect(page.locator(CANVAS)).toHaveAttribute("data-outline-glow", "0");
  await expect.poll(() => stitches(page)).toBeLessThan(sewn);
  await expect(page.locator(".dgp-run")).toHaveAttribute("data-stale", "true");

  // Put back: as it was, and it does not ask again.
  await page.locator(GONE).getByRole("button", { name: "Put back" }).click();
  await expect(page.locator(GONE)).toHaveCount(0);
  await expect(ask).toHaveCount(0);
  await expect.poll(() => stitches(page)).toBe(sewn);
  await expect(page.locator(".dgp-run")).toHaveAttribute("data-stale", "false");
  await expect(page.locator(CANVAS)).toHaveAttribute("data-outline-glow", "0");

  seen.expectClean();
});
