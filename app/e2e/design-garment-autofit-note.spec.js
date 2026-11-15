// A garment switch auto-fits a stitch file without touching its sizeMm. The
// design panel read sizeMm alone, so on Hat the monarch starter was drawn at
// 66% of native under "Pre-digitized file: it sews exactly as digitized", and
// its size line kept the native size beside a smaller canvas (Kent's build
// walkthrough, 2026-11-13). The panel now reads the DRAWN width, so the note
// a typed size shows appears here too, and one Undo of the switch takes it away.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, openAdvanced, openDownload } from "./helpers.js";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MONARCH = path.resolve(__dirname, "../public/starter/monarch-butterflies.dst");
const { decodeDSTStandard } = createRequire(import.meta.url)(path.resolve(__dirname, "../../src/dstimport.js"));

test("switching to Hat shrinks a stitch file and the panel says so; Undo restores", async ({ page }) => {
  await startStudio(page);
  await openAdvanced(page);
  await page.getByRole("button", { name: "Design file" }).click();
  await page.locator(".dp-upload input[type=file]").setInputFiles(MONARCH);
  await expect(page.locator(".dp-stats")).toBeVisible({ timeout: 60_000 });

  const note = page.locator(".dp-note").filter({ hasText: /Pre-digitized file|Resized to/ });
  await expect(note).toContainText("sews exactly as digitized");
  await expect(note).not.toContainText("Resized to");

  await pickGarment(page, "Hat Front");

  // Kent 2026-11-14 ("Stop at 75%, say so"): auto-fit stops at the range edge,
  // 91x86 -> 68x64, and the note says the file does not fit the placement.
  await expect(note).toContainText("Resized to 75%", { timeout: 30_000 });
  await expect(note).toContainText("Auto-fit stopped at the 75% limit");
  await expect(note).toContainText("does not fit the placement");
  await expect(note).not.toContainText("well outside");
  await expect(page.locator("span.stats").first()).toContainText("68×64 mm");
  await expect(note).not.toContainText("sews exactly as digitized");
  // the file's size line names the size on the canvas, and the native size
  const canvas = (await page.locator("span.stats").first().textContent()) || "";
  const m = canvas.match(/(\d+)×(\d+) mm/);
  expect(m).not.toBeNull();
  await expect(page.locator(".dp-stats")).toContainText(`${m[1]}×${m[2]} mm (file:`);

  await page.keyboard.press("Control+z");
  await expect(note).toContainText("sews exactly as digitized", { timeout: 30_000 });
  await expect(page.locator(".dp-stats")).not.toContainText("(file:");
});

// The starter picker on a placement a starter overflows (the Bur oak leaf is
// 67.9 mm tall at 75% on the hat front, whose box is 64 since Kent's ruling
// 2026-11-14, "Hat front only"; the Shamrock used to overflow the old 57.2 mm
// box and now fits): it lands at the 75% limit with the does-not-fit line, and
// still exports a complete file.
test("a starter that overflows the hat front sits at 75%, says so, and still downloads", async ({ page }) => {
  await startStudio(page);
  await pickGarment(page, "Hat Front");
  await page.getByRole("group", { name: "Start with" }).getByRole("button", { name: "Starter designs" }).click();
  await page.getByRole("dialog", { name: "Starter designs" }).getByRole("button", { name: "Add Bur oak leaf", exact: true }).click();
  await expect(page.locator(".dp-stats")).toBeVisible({ timeout: 60_000 });
  await openAdvanced(page);
  const note = page.locator(".dp-note").filter({ hasText: "Resized to" });
  await expect(note).toContainText("Resized to 75%", { timeout: 30_000 });
  await expect(note).toContainText("does not fit the placement");
  await expect(page.locator("span.stats").first()).toContainText("41×68 mm");

  await openDownload(page);
  const dl = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const anyway = page.getByRole("button", { name: "Download DST anyway", exact: true });
  if (await anyway.isVisible().catch(() => false)) await anyway.click();
  const file = await dl;
  expect(file.suggestedFilename()).toBe("bur-oak-leaf.dst");
  const out = decodeDSTStandard(new Uint8Array(readFileSync(await file.path())));
  expect(out.stitchCount).toBe(12357);
  expect(Math.abs(out.widthMM - 41.3)).toBeLessThanOrEqual(0.3);
  expect(Math.abs(out.heightMM - 67.9)).toBeLessThanOrEqual(0.3);
});
