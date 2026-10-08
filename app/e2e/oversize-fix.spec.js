// Garment picker -> placement -> oversize warning -> the fix the warning names.
//
// hoopFitNote (lib/hoop.js) is written to "name the fix, not just the problem",
// and the unit spec checks the sentence. Nothing checked that doing what the
// sentence says actually clears it in the real Studio, which is the only claim
// that matters to a customer. Two fixes are named in practice:
//
//   "a <bigger> hoop fits it"   -> pick that hoop in the hoop row
//   "make it smaller under Size" -> type a smaller width in the Size panel
//
// Each test follows the warning's own instruction and asserts the caption
// stops warning. Auto-fit is deliberately NOT asserted here: it fits the
// garment's placement box, not the hoop, so on a tote or back it brings the
// warning straight back (MASTER_SCOPE area 3 carries that open question).
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, typeText } from "./helpers.js";

const caption = (page) => page.locator("span.stats").locator("xpath=..");

test("oversize on a smaller hoop names a bigger hoop, and picking it clears the warning", async ({ page }) => {
  await startStudio(page);
  await pickGarment(page, "Left Chest");
  await typeText(page, "EMB TEST");

  // Left chest suggests a hoop it fits; pick the smallest one by hand so the
  // placement-box-sized design (101.6 mm) exceeds it (100 mm).
  const hoops = page.getByRole("group", { name: "Hoop size" });
  await hoops.getByRole("button", { name: /4×4 in/ }).click();

  const warn = caption(page).locator(".warn", { hasText: /^\s*·\s*Exceeds your 4×4 in hoop/ });
  await expect(warn).toBeVisible();
  const m = (await warn.innerText()).match(/a (\S+ in) hoop fits it/);
  expect(m, "the warning should name a bigger hoop").not.toBeNull();

  await hoops.getByRole("button", { name: new RegExp(m[1]) }).click();
  await expect(caption(page).locator(".warn", { hasText: "Exceeds" })).toHaveCount(0);
});

test("oversize on a garment past every hoop says make it smaller, and a smaller width clears it", async ({ page }) => {
  await startStudio(page);
  await pickGarment(page, "Full Back");
  await typeText(page, "EMB TEST");

  const warn = caption(page).locator(".warn", { hasText: "Exceeds" });
  await expect(warn).toBeVisible();
  await expect(warn).toContainText("every hoop this app offers — make it smaller under Size");

  // Do what it says: 6 in (152 mm) is inside the largest, 200 mm, hoop.
  const w = page.getByLabel("Width");
  expect(await page.locator("select.unitselect").inputValue()).toBe("in");
  await w.fill("6");
  await w.dispatchEvent("change");
  await expect(caption(page).locator(".warn", { hasText: "Exceeds" })).toHaveCount(0);
});
