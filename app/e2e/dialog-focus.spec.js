// Every Studio dialog: focus moves in on open, Tab stays inside, Escape
// closes, focus returns to the opener (Kent 2026-10-08).
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate } from "./helpers.js";

const insideDialog = (page, name) =>
  page.evaluate((n) => {
    const d = [...document.querySelectorAll('[role="dialog"]')].find((x) => x.getAttribute("aria-label") === n);
    return !!d && d.contains(document.activeElement);
  }, name);

async function tabsStayInside(page, name) {
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press("Tab");
    expect(await insideDialog(page, name), `Tab ${i} stays in "${name}"`).toBe(true);
  }
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press("Shift+Tab");
    expect(await insideDialog(page, name), `Shift+Tab ${i} stays in "${name}"`).toBe(true);
  }
}

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
});

test("My designs: focus in, Tab trapped, Escape closes, focus returns", async ({ page }) => {
  const opener = page.getByRole("button", { name: /^My designs/ });
  await opener.click();
  await expect(page.getByRole("dialog", { name: "My designs" })).toBeVisible();
  expect(await insideDialog(page, "My designs")).toBe(true);
  await tabsStayInside(page, "My designs");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "My designs" })).toHaveCount(0);
  await expect(opener).toBeFocused();
});

test("Download sheet: focus in, Tab trapped, Escape closes, focus returns", async ({ page }) => {
  const opener = page.getByRole("button", { name: "Download", exact: true });
  await opener.click();
  await expect(page.getByRole("dialog", { name: "Download" })).toBeVisible();
  expect(await insideDialog(page, "Download")).toBe(true);
  await tabsStayInside(page, "Download");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Download" })).toHaveCount(0);
  await expect(opener).toBeFocused();
});

test("Font browser: focus in, Tab trapped, Escape closes, focus returns", async ({ page }) => {
  const opener = page.locator(".fs-trigger").first();
  await opener.click();
  const dlg = page.locator('[role="dialog"][aria-modal="true"]').last();
  await expect(dlg).toBeVisible();
  const name = await dlg.getAttribute("aria-label");
  expect(await insideDialog(page, name)).toBe(true);
  await tabsStayInside(page, name);
  await page.keyboard.press("Escape");
  await expect(dlg).toHaveCount(0);
  await expect(opener).toBeFocused();
});
