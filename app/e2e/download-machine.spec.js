// "Your machine" on the Download step (2026-09-30): pick the brand, get the
// file that machine reads. Driven end to end on the lettering lane (no
// service needed): Brother -> one filled button -> a real .pes lands, and the
// choice survives a reload. The Left-chest template fits its suggested hoop,
// so no oversize confirm stands between the click and the download.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate, openDownload } from "./helpers.js";
import { statSync } from "node:fs";

async function reachDownload(page) {
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
  await openDownload(page);
}

test("choosing Brother gives one PES button that downloads a real file, and the choice is remembered", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reachDownload(page);

  const select = page.getByLabel("Your machine");
  await expect(select).toHaveValue("");
  await expect(page.getByTestId("machine-download")).toHaveCount(0);
  // DST is the filled button until a machine is chosen.
  await expect(page.locator(".formats button.primary")).toHaveText("DST");

  await select.selectOption("brother");
  const btn = page.getByTestId("machine-download");
  await expect(btn).toHaveText("Download PES for Brother / Baby Lock");
  // One filled download on the step: the machine's; DST in the grid is not.
  // (StepNav's Next is also `.primary`, so the count is scoped to the two
  // download blocks.)
  await expect(page.locator(".machinepick button.primary, .formats button.primary")).toHaveCount(1);
  await expect(page.locator(".formats button.primary")).toHaveCount(0);

  const downloadPromise = page.waitForEvent("download");
  await btn.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("design.pes");
  const p = await download.path();
  expect(statSync(p).size).toBeGreaterThan(200);

  // Remembered: the next visit starts with the machine already chosen. A
  // reload lands on the design again; the summary bar's Download is the
  // route back once the design has regenerated.
  await page.reload();
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await openDownload(page);
  await expect(page.getByLabel("Your machine")).toHaveValue("brother");
  await expect(page.getByTestId("machine-download")).toHaveText("Download PES for Brother / Baby Lock");
});

test("the view segments: Stitches, Realistic and Simulate are one choice", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");

  const flat = page.locator('.zoomctl button[aria-label="Stitches view"]');
  const real = page.locator('.zoomctl button[aria-label="Realistic view"]');
  const sim = page.locator('.zoomctl button[aria-label="Stitch simulator"]');
  // Realistic is the default; the words are on the segments.
  await expect(real).toHaveAttribute("aria-pressed", "true");
  await expect(real).toHaveText("Realistic");
  await expect(flat).toHaveAttribute("aria-pressed", "false");

  await flat.click();
  await expect(flat).toHaveAttribute("aria-pressed", "true");
  await expect(real).toHaveAttribute("aria-pressed", "false");
  // Clicking the lit segment again changes nothing — a segment is a pick,
  // not a toggle.
  await flat.click();
  await expect(flat).toHaveAttribute("aria-pressed", "true");

  await sim.click();
  await expect(sim).toHaveAttribute("aria-pressed", "true");
  await expect(flat).toHaveAttribute("aria-pressed", "false");
  // The simulator bar covers the zoom bar while it runs (by design — see
  // .fieldbars in theme.css), so the way out by mouse is its own close
  // button; the segments are then the flat view the simulator left from.
  await expect(page.locator(".simbar")).toHaveCount(1);
  await page.locator('.simbar button[aria-label="Close simulator"]').click();
  await expect(page.locator(".simbar")).toHaveCount(0);
  await expect(sim).toHaveAttribute("aria-pressed", "false");
  await expect(flat).toHaveAttribute("aria-pressed", "true");
  await real.click();
  await expect(real).toHaveAttribute("aria-pressed", "true");
  await expect(flat).toHaveAttribute("aria-pressed", "false");

  // The overlay toggles carry their names now.
  await expect(page.locator('.zoomctl button[aria-label="Show shape outlines"]')).toHaveText("Outlines");
});
