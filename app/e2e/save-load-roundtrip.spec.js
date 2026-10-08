// Save/load round-trip in the real Studio: edit -> reload (registry restore)
// -> export .embproj -> wipe the browser ("another machine") -> import.
// The lib specs (src/lib/saveLoad.roundtrip.spec.js) pin every element type
// against the serializers; this proves the wired path, and that the undo
// stack — in-memory by design — starts empty after a reload.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { startStudio, typeText, pickGarment } from "./helpers.js";

const NAME = "Round Trip 42";

async function openDrawer(page) {
  if (await page.locator(".drawer").count()) return;
  await page.getByRole("button", { name: /My designs/ }).first().click();
  await expect(page.locator(".drawer")).toBeVisible();
}

test("an edited design survives a reload, an export and an import elsewhere; undo history does not", async ({ page }) => {
  await startStudio(page);
  await pickGarment(page, "Tote");
  await typeText(page, NAME);
  await expect(page.getByRole("button", { name: "Undo" })).toBeEnabled();

  // 1. Reload: the registry record restores the text and garment; the undo
  //    stack is session-only, so nothing is left to undo.
  await page.reload();
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue(NAME);
  await expect(page.locator(".cfg-sub")).toContainText("Tote");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("button", { name: "Undo" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Redo" })).toBeDisabled();

  // 2. Export the current design.
  await openDrawer(page);
  const [dl] = await Promise.all([
    page.waitForEvent("download"),
    page.locator(".drawer-row.current").getByRole("button", { name: "Export" }).click(),
  ]);
  const text = readFileSync(await dl.path(), "utf8");
  const file = JSON.parse(text);
  expect(file.format).toBe("embproj");
  expect(file.project.garmentId).toBe("tote");
  expect(file.project.elements[0].text).toBe(NAME);
  expect(JSON.stringify(file)).not.toMatch(/undo|redo/i);

  // 3. "Another machine": no registry at all, then import the file.
  await page.evaluate(() => localStorage.clear());
  await page.goto("/");
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue("");
  await openDrawer(page);
  await page
    .getByLabel("Import design file")
    .setInputFiles({ name: dl.suggestedFilename(), mimeType: "application/json", buffer: Buffer.from(text, "utf8") });
  await expect(page.locator(".drawer")).toHaveCount(0);
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue(NAME);
  await expect(page.locator(".cfg-sub")).toContainText("Tote");
  await expect(page.getByRole("button", { name: "Undo" })).toBeDisabled();
});
