// "Rotate to fit" keeps the design's size (Kent 2026-11-12: one click turns
// the design, one undo step, nothing unprompted).
//
// The button's first build (#1414) turned the elements and left each one's
// width alone. A width is the width AFTER the turn, so the engine rescaled
// the turned design to keep it: ROTATE ME at 150 x 15 mm came back 31 x 305 mm
// with 3,636 stitches (it doubled), and the football starter 150 x 100 mm came
// back 150 x 225 mm (build walkthrough 2026-11-13, section 3). The unit spec
// (src/lib/rotateToFit.spec.js) pins the sizes per element kind; this one
// presses the real button in the real Studio and reads what the customer reads:
// the caption, the Width and Height boxes, the hoop warning, and Undo.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, typeText } from "./helpers.js";

const caption = (page) => page.locator("span.stats").locator("xpath=..");
const exceeds = (page) => caption(page).locator(".warn", { hasText: "Exceeds" });
const rotateBtn = (page) => page.getByTestId("rotate-to-fit");
const undo = (page) => page.getByRole("button", { name: "Undo" });

// The caption reads "1,899 stitches · 150×15 mm · 5×7 in hoop ..."
async function readStats(page) {
  const text = await page.locator("span.stats").innerText();
  const m = text.match(/^([\d,]+) stitches · (\d+)×(\d+) mm/);
  expect(m, "caption: " + text).not.toBeNull();
  return { stitches: m[1], w: Number(m[2]), h: Number(m[3]) };
}
async function readBoxes(page) {
  return {
    w: await page.getByLabel("Width").inputValue(),
    h: await page.getByLabel("Height").inputValue(),
  };
}

// A 5x7 hoop is 130 x 180 mm, and a Full Back (304.8 mm box) can hold more
// than that, so a 5.9 in (150 mm) wide design exceeds it upright and fits it
// turned. Wait for the warning (and the button) before reading anything.
async function oversizeIn5x7(page) {
  await pickGarment(page, "Full Back");
  await page.getByRole("group", { name: "Hoop size" }).getByRole("button", { name: /5×7 in/ }).click();
}
async function setWidthIn(page, inches) {
  const w = page.getByLabel("Width");
  expect(await page.locator("select.unitselect").inputValue()).toBe("in");
  await w.fill(String(inches));
  await w.dispatchEvent("change");
}

test("lettering 150 x 15 mm turns to 15 x 150 mm: same stitches, swapped size boxes, warning gone, one Undo", async ({ page }) => {
  await startStudio(page);
  await oversizeIn5x7(page);
  await typeText(page, "ROTATE ME");
  await setWidthIn(page, 5.9);
  await expect(exceeds(page)).toContainText("rotate the design 90° and it fits");
  await expect(rotateBtn(page)).toBeVisible();
  const before = await readStats(page);
  const boxesBefore = await readBoxes(page);
  expect([before.w, before.h]).toEqual([150, 15]);

  await rotateBtn(page).click();

  await expect(exceeds(page)).toHaveCount(0);
  await expect(rotateBtn(page)).toHaveCount(0);
  await expect.poll(async () => (await readStats(page)).w).toBe(15);
  const after = await readStats(page);
  expect(after.h).toBe(150);
  expect(after.stitches).toBe(before.stitches); // turned, not rescaled
  // the size boxes read the new width and height: the old ones, swapped
  const boxesAfter = await readBoxes(page);
  expect(boxesAfter).toEqual({ w: boxesBefore.h, h: boxesBefore.w });

  // one Undo puts the design back exactly: size, size boxes and the button
  await undo(page).click();
  await expect.poll(async () => (await readStats(page)).w).toBe(150);
  expect(await readStats(page)).toEqual(before);
  expect(await readBoxes(page)).toEqual(boxesBefore);
  await expect(rotateBtn(page)).toBeVisible();
  await expect(exceeds(page)).toContainText("rotate the design 90° and it fits");
});

test("the football starter 150 x 100 mm turns to 100 x 150 mm, not 150 x 225", async ({ page }) => {
  await startStudio(page);
  await oversizeIn5x7(page);
  await page.getByRole("group", { name: "Start with" }).getByRole("button", { name: "Starter designs" }).click();
  await page.getByRole("dialog", { name: "Starter designs" }).getByRole("button", { name: /^Add American football/ }).click();
  await expect(page.getByRole("dialog", { name: "Starter designs" })).toHaveCount(0);
  await setWidthIn(page, 5.9);
  await expect(rotateBtn(page)).toBeVisible({ timeout: 30_000 });
  const before = await readStats(page);
  const boxesBefore = await readBoxes(page);
  expect([before.w, before.h]).toEqual([150, 100]);

  await rotateBtn(page).click();

  await expect(exceeds(page)).toHaveCount(0);
  await expect.poll(async () => (await readStats(page)).w).toBe(100);
  const after = await readStats(page);
  expect(after.h).toBe(150);
  expect(after.stitches).toBe(before.stitches);
  expect(await readBoxes(page)).toEqual({ w: boxesBefore.h, h: boxesBefore.w });

  await undo(page).click();
  await expect.poll(async () => (await readStats(page)).w).toBe(150);
  expect(await readStats(page)).toEqual(before);
  expect(await readBoxes(page)).toEqual(boxesBefore);
});
