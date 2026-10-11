// End-to-end guard for the upload crop: the Studio PROPOSES a crop box on an
// uploaded logo, and the customer can accept it, adjust it, or reset it.
//
// Component tests (CropBox.spec.js, cropProposal.spec.js) cover the box and the
// algorithm apart; neither sees the real wiring -- a real file through the real
// canvas into proposeCrop, a real pointer drag on the rendered box, and the
// reset button. Needs NO digitizer service: the crop box shows as soon as the
// file loads (upload is not a run). Existing fixtures only.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { startStudio, uploadArtwork } from "./helpers.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Stand-in for the digitizer service: the Studio routes an upload to the
// digitized element (the one with the crop box) only when /health answers, and
// an upload runs nothing, so a bare /health is all this spec needs.
const SERVICE = "http://127.0.0.1:8721";
const CORS = { "access-control-allow-origin": "*", "access-control-allow-headers": "*" };
async function mockHealth(page) {
  await page.route(SERVICE + "/**", (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });
    if (new URL(route.request().url()).pathname === "/health")
      return route.fulfill({ status: 200, headers: { ...CORS, "content-type": "application/json" }, body: JSON.stringify({ status: "ok" }) });
    return route.fulfill({ status: 404, headers: CORS, body: "{}" });
  });
}

const ART = path.join(__dirname, "fixtures", "two-squares.png");

const fractions = (page) =>
  page.getByRole("group", { name: "Crop area" }).evaluate((el) => {
    const f = (v) => parseFloat(v) / 100;
    const s = el.style;
    return { x0: f(s.left), y0: f(s.top), x1: f(s.left) + f(s.width), y1: f(s.top) + f(s.height) };
  });

test("an uploaded logo gets a crop proposal that can be adjusted and reset", async ({ page }) => {
  await mockHealth(page);
  await startStudio(page);
  await uploadArtwork(page, ART, { run: false });

  const box = page.getByRole("group", { name: "Crop area" });
  const reset = page.getByRole("button", { name: "Use whole image" });
  await expect(box).toBeVisible();

  // Accept: two-squares (two equal inks, so the box of ALL ink) is proposed as
  // a tight rectangle -- ink spans x 0.05-0.95, y 0.1-0.9 plus the 2 mm margin
  // the algorithm adds -- and left untouched it is what the box shows, with the
  // reset on offer.
  const proposed = await fractions(page);
  expect(proposed.x0).toBeGreaterThan(0.02);
  expect(proposed.y0).toBeGreaterThan(0.05);
  expect(proposed.x1).toBeLessThan(0.98);
  expect(proposed.y1).toBeLessThan(0.95);
  await expect(reset).toBeEnabled();

  // Adjust: drag the right edge handle 40 px left; only that edge moves.
  const handle = page.getByRole("button", { name: "Drag right edge" });
  const hb = await handle.boundingBox();
  const host = await page.locator(".crop-host").boundingBox();
  const x = hb.x + hb.width / 2, y = hb.y + hb.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x - 40, y, { steps: 5 });
  await page.mouse.up();
  const adjusted = await fractions(page);
  expect(adjusted.x1).toBeCloseTo(proposed.x1 - 40 / host.width, 2);
  expect(adjusted.x0).toBeCloseTo(proposed.x0, 3);
  expect(adjusted.y0).toBeCloseTo(proposed.y0, 3);
  expect(adjusted.y1).toBeCloseTo(proposed.y1, 3);
  await expect(reset).toBeEnabled();

  // Reset: the whole image again, and the button has nothing left to do.
  await reset.click();
  const whole = await fractions(page);
  expect(whole).toEqual({ x0: 0, y0: 0, x1: 1, y1: 1 });
  await expect(reset).toBeDisabled();
});
