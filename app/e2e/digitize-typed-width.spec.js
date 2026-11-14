// Kent's 2026-11-13 walkthrough, items 4 and 5, against the REAL digitizer
// service (reused from a developer's own instance; SKIPPED, never failed, when
// none answers on 8721 -- the same posture as digitize-restitch-trigger.spec.js).
//
//   A. A width typed in the Size panel BEFORE the first digitize is the width
//      that run digitizes at: one POST /digitize at the typed width, no
//      "Resized to N mm ... restitch" cue after it, and the mm box shows a
//      tenth of a millimetre (90.5, not "91").
//   B. A resize under the 2% tolerance, then Auto Digitize Image: the stitches
//      come back the same, and one line in the status area says why nothing
//      was restitched ("No restitch needed: size changed by under 2%."); the
//      panel's size line follows the canvas caption instead of keeping the
//      digitized width beside it.
//
// Optional: SHOT_DIR keeps a screenshot of each state for a PR body.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, uploadArtwork, runDigitize } from "./helpers.js";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
const SHOT_DIR = process.env.SHOT_DIR || "";
if (SHOT_DIR) mkdirSync(SHOT_DIR, { recursive: true });
async function shot(page, name, locator = null) {
  if (!SHOT_DIR) return;
  await (locator || page).screenshot({ path: path.join(SHOT_DIR, name + ".png") });
}

let serviceUp = false;
test.beforeAll(async () => {
  try {
    const r = await fetch(SERVICE_URL + "/health");
    serviceUp = r.ok && (await r.json()).status === "ok";
  } catch (e) {
    serviceUp = false;
  }
});

// Every POST /digitize, with the Design width its config carried.
function watchDigitize(page) {
  const sent = [];
  // A route, not a "request" listener: the multipart body of a Blob upload is
  // only readable from the route's request (helpers.js pinDigitizeConfig).
  page.route("**/digitize", async (route) => {
    const req = route.request();
    const buf = req.method() === "POST" ? req.postDataBuffer() : null;
    const m = buf && /name="config"\r\n\r\n(\{[^\r\n]*\})/.exec(buf.toString("latin1"));
    if (req.method() === "POST") sent.push(m ? JSON.parse(m[1]).target_width_mm : null);
    return route.continue();
  });
  return sent;
}

const dims = (text) => {
  const m = /(\d+)×(\d+) mm/.exec(text);
  return m ? [Number(m[1]), Number(m[2])] : null;
};

test("A: a width typed before the first digitize is that run's width, and costs one run", async ({ page }) => {
  test.skip(!serviceUp, "digitizer service is not running on 8721");
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sent = watchDigitize(page);
  await startStudio(page);
  await pickGarment(page, "Tote");
  await uploadArtwork(page, ART_PNG, { run: false });

  const unit = page.locator("select.unitselect");
  await expect(unit).toBeVisible({ timeout: 30_000 });
  await unit.selectOption("mm");
  const width = page.getByLabel("Width", { exact: true });
  // Not empty any more: the box shows the width the first run would use.
  await expect(width).not.toHaveValue("");
  await width.scrollIntoViewIfNeeded();
  await page.mouse.move(5, 5);
  await shot(page, "a1-before-typing", page.locator(".sizepanel").first());
  await width.fill("90.5");
  await width.dispatchEvent("change");
  await expect(width).toHaveValue("90.5");
  await page.mouse.move(5, 5);
  await shot(page, "a2-typed-90.5", page.locator(".sizepanel").first());

  await runDigitize(page);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  expect(sent).toEqual([90.5]);
  await expect(page.getByTestId("digitize-stale")).toHaveCount(0);
  await width.scrollIntoViewIfNeeded();
  await shot(page, "a3-after-first-run");
  await shot(page, "a3-size-row-after-first-run", page.locator(".sizepanel").first());
  // Still one run after a pause: nothing started a second.
  await page.waitForTimeout(3000);
  expect(sent).toHaveLength(1);
});

test("B: a resize under 2% then Auto Digitize says nothing needed restitching, and the size line follows the canvas", async ({ page }) => {
  test.skip(!serviceUp, "digitizer service is not running on 8721");
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sent = watchDigitize(page);
  await startStudio(page);
  await pickGarment(page, "Tote");
  await uploadArtwork(page, ART_PNG, { run: false });
  const unit = page.locator("select.unitselect");
  await expect(unit).toBeVisible({ timeout: 30_000 });
  await unit.selectOption("mm");
  const width = page.getByLabel("Width", { exact: true });
  await width.fill("120");
  await width.dispatchEvent("change");
  await runDigitize(page);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  const canvas = () => page.locator("span.stats").innerText();
  const stitches = async () => /([\d,]+) stitches/.exec(await canvas())[1];
  const before = await stitches();
  expect(sent).toHaveLength(1);

  // +1.1%: the Size panel's box, the same hand a customer uses.
  const sewn = parseFloat(await width.inputValue());
  await width.fill((Math.round(sewn * 1.011 * 10) / 10).toString());
  await width.dispatchEvent("change");
  await expect(page.getByTestId("digitize-stale")).toHaveCount(0);   // under 2%: not stale
  await runDigitize(page);
  await expect(page.getByTestId("digitize-no-restitch")).toHaveText("No restitch needed: size changed by under 2%.", { timeout: 120_000 });
  await expect(page.locator(".dgp-run")).toBeEnabled();
  expect(await stitches()).toBe(before);                              // same stitches
  // The panel's size line is the canvas's.
  const panel = dims(await page.locator(".dgp-stats").innerText());
  const caption = dims(await canvas());
  expect(panel).toEqual(caption);
  await shot(page, "b1-no-restitch-needed");
});
