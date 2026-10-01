// Shared drives for the configurator (spec §7). Every spec used to walk
// Next → Next → Next; the walk is gone, so the way to each place is stated
// once here. Assertions about WHAT is reached stay in each spec.
import { expect } from "@playwright/test";

export async function startStudio(page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your design" })).toBeVisible();
}

export async function typeText(page, text) {
  const input = page.getByPlaceholder("Type a name or word");
  await input.fill(text);
  await expect(input).toHaveValue(text);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
}

export async function pickGarment(page, label) {
  const tile = page.getByRole("button", { name: label, exact: true });
  await tile.click();
  await expect(tile).toHaveClass(/\bsel\b/);
}

export async function pickTemplate(page, name) {
  await page.getByRole("button", { name: /^My designs/ }).click();
  await page.locator(".tcard", { hasText: name }).click();
  await expect(page.getByRole("dialog", { name: "My designs" })).toHaveCount(0);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
}

export async function openDownload(page) {
  await page.getByRole("button", { name: "Download", exact: true }).click();
  const sheet = page.getByRole("dialog", { name: "Download" });
  await expect(sheet).toBeVisible();
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();
  return sheet;
}

export async function closeDownload(page) {
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Download" })).toHaveCount(0);
}
