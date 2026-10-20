// GUARD for the named-thread colour picker (ThreadPicker.svelte): switch brand,
// search by code and by name, apply a thread to a layer, and see the Download
// sheet's shopping list name the new cone. Runs on the browser lettering lane
// (no service), off the "Left-chest name" template.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate, openDownload, closeDownload } from "./helpers.js";

test("ThreadPicker: brand switch, search by code/name, apply to a layer, shopping list follows", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // A saved brand preference would change which chart opens first.
  await page.addInitScript(() => {
    try { localStorage.clear(); } catch (e) { /* storage blocked */ }
  });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");

  const trigger = page.getByRole("button", { name: /^Thread color/ }).first();
  await expect(trigger).toBeVisible();
  const before = await trigger.getAttribute("aria-label");
  await trigger.click();

  const brand = page.getByRole("combobox", { name: "Thread brand" });
  await expect(brand).toBeVisible();

  // Brand switch: the chart changes and the search box appears (Studio basics has none).
  await brand.selectOption({ label: "Isacord Polyester 40" });
  const search = page.getByRole("searchbox", { name: "Search threads" });
  await expect(search).toBeVisible();
  const cells = page.locator(".tp-grid").getByRole("option");
  await expect(cells.first()).toBeVisible();
  const total = await cells.count();
  expect(total).toBeGreaterThan(50);

  // Search by code, then by name: both narrow the grid; nonsense matches nothing.
  const firstLabel = await cells.first().getAttribute("aria-label");
  const [code, ...nameWords] = firstLabel.split(" ");
  await search.fill(code);
  await expect(cells.first()).toHaveAttribute("aria-label", firstLabel);
  expect(await cells.count()).toBeLessThan(total);
  await search.fill(nameWords.join(" ").toUpperCase());
  await expect(page.locator(`.tp-grid [aria-label="${firstLabel}"]`)).toBeVisible();
  await search.fill("zzzz-no-such-thread");
  await expect(page.getByText(/No threads match/)).toBeVisible();

  // Apply a thread to the layer: pick one that differs from the current colour.
  await search.fill("");
  const pickLabel = await cells.nth(Math.min(40, total - 1)).getAttribute("aria-label");
  await page.locator(".tp-grid").getByRole("option", { name: pickLabel, exact: true }).click();
  await expect(page.locator(".tp-panel")).toHaveCount(0);
  await expect(trigger).toHaveAttribute("aria-label", new RegExp(pickLabel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$"));
  expect(await trigger.getAttribute("aria-label")).not.toBe(before);

  // The shopping list follows the layer's new thread.
  await openDownload(page);
  await expect(page.locator(".threadlist .threadrow")).toHaveCount(1);
  await expect(page.locator(".threadlist .threadrow-name")).toHaveText(pickLabel);
  await closeDownload(page);
});
