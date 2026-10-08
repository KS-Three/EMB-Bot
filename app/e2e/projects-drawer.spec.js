// ProjectsDrawer lifecycle across a reload: create, rename, reopen, delete.
// The drawer is presentational and App owns the registry, so the guard that
// matters is the whole loop in the real app with localStorage surviving page.reload().
import { test, expect } from "@playwright/test";
import { typeText } from "./helpers.js";

const nameField = (page) => page.getByLabel("Project name");
const rows = (page) => page.locator(".drawer-row-name");
const row = (page, name) => page.locator(".drawer-row", { has: page.locator(".drawer-row-name", { hasText: name }) });

async function openDrawer(page) {
  if (await page.locator(".drawer").count()) return;
  await page.getByRole("button", { name: /My designs/ }).first().click();
  await expect(page.locator(".drawer")).toBeVisible();
}

test("create, rename, reopen and delete projects survive a reload", async ({ page }) => {
  await page.goto("/");
  await typeText(page, "ALPHA");
  await openDrawer(page);
  await page.getByRole("button", { name: "+ New design" }).click();
  await typeText(page, "BRAVO");

  // Rename the non-current row (ALPHA) by hand; a hand name is sticky.
  await openDrawer(page);
  await expect(rows(page)).toHaveText(["BRAVO", "ALPHA"]);
  await row(page, "ALPHA").getByRole("button", { name: "Rename" }).click();
  const input = page.getByLabel("Rename project");
  await input.fill("Charlie Cap");
  await input.press("Enter");
  await expect(rows(page)).toHaveText(["BRAVO", "Charlie Cap"]);

  // Reload: both rows and the open design persist.
  await page.reload();
  await expect(nameField(page)).toHaveValue("BRAVO");
  await openDrawer(page);
  await expect(rows(page)).toHaveText(["BRAVO", "Charlie Cap"]);

  // Reopen the renamed one; it becomes current, and that survives a reload too.
  await row(page, "Charlie Cap").getByRole("button", { name: "Open" }).click();
  await expect(page.locator(".drawer")).toHaveCount(0);
  await expect(nameField(page)).toHaveValue("Charlie Cap");
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue("ALPHA");
  await page.reload();
  await expect(nameField(page)).toHaveValue("Charlie Cap");

  // Delete is two-tap; the other design survives a reload.
  await openDrawer(page);
  const bravo = row(page, "BRAVO");
  await bravo.getByRole("button", { name: "Delete" }).click();
  await expect(rows(page)).toHaveCount(2);
  await page.waitForTimeout(350); // past the double-click guard
  await bravo.getByRole("button", { name: "Really delete?" }).click();
  await expect(rows(page)).toHaveText(["Charlie Cap"]);
  await page.reload();
  await openDrawer(page);
  await expect(rows(page)).toHaveText(["Charlie Cap"]);
  await expect(nameField(page)).toHaveValue("Charlie Cap");
});
