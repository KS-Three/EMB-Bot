// A garment switch auto-fits a stitch file without touching its sizeMm. The
// design panel read sizeMm alone, so on Hat the monarch starter was drawn at
// 66% of native under "Pre-digitized file: it sews exactly as digitized", and
// its size line kept the native size beside a smaller canvas (Kent's build
// walkthrough, 2026-11-13). The panel now reads the DRAWN width, so the note
// a typed size shows appears here too, and one Undo of the switch takes it away.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, openAdvanced } from "./helpers.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MONARCH = path.resolve(__dirname, "../public/starter/monarch-butterflies.dst");

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
