// The tracing image's own controls in Draw shapes (ManualPanel's .mp-backdrop
// strip) must be readable. Found driving the panel as a customer 2026-10-08:
// the strip's "Remove" button set a white background but no text colour, so
// it inherited the dark theme's light button ink and rendered white on white
// (computed rgb(255,255,255) on rgb(255,255,255)) -- an empty white box, and
// the only way to take a tracing image away again.
//
// Contrast is read from computed styles (the WCAG relative-luminance formula,
// AA 4.5:1 for normal text), not from pixels: the button is a solid fill, so
// its colour pair IS what the customer sees.
import { test, expect } from "@playwright/test";
import { pickGarment } from "./helpers.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_PNG = path.join(__dirname, "fixtures", "trace-holes-and-colors.png");

function contrast(fg, bg) {
  const lum = (s) => {
    const [r, g, b] = s.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number).map((v) => {
      const c = v / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
  return (a + 0.05) / (b + 0.05);
}

test("the tracing image's Remove button is readable, and removes the image", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/");
  await pickGarment(page, "Tote");
  await page.locator(".hoop canvas").click({ button: "right" });
  await page.getByRole("menuitem", { name: "Draw shapes" }).click();

  await page.getByRole("button", { name: "Trace image…" }).click();
  await page.locator(".tip-upload input[type=file]").setInputFiles(FIXTURE_PNG);

  const strip = page.getByRole("group", { name: "Tracing image" });
  await expect(strip).toBeVisible({ timeout: 15_000 });
  const remove = strip.getByRole("button", { name: "Remove" });
  await expect(remove).toBeVisible();

  const { color, background } = await remove.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { color: cs.color, background: cs.backgroundColor };
  });
  const ratio = contrast(color, background);
  test.info().annotations.push({ type: "contrast", description: `${color} on ${background} = ${ratio.toFixed(2)}` });
  expect(ratio, `${color} on ${background}`).toBeGreaterThanOrEqual(4.5);

  await remove.click();
  await expect(strip).toHaveCount(0);
});
