// The stitch simulator reads like watching the machine sew (2026-11-07): the
// bar names the thread on the needle ("Thread K of B" and its chart name),
// playback STOPS at each thread change as the machine does, the skip buttons
// and `<` / `>` step from change to change, `,` / `.` step one stitch, and the
// counters keep agreeing with the field caption.
//
// The fixture is two-colour lettering on the browser lane (no digitizer
// service): "Fritschs Stitches" with "Stitches" in Scarlet — two thread
// blocks, an OFL font, nothing third-party.
import { test, expect } from "@playwright/test";
import { typeText } from "./helpers.js";

async function selectInTextarea(page, start, end) {
  const ta = page.getByPlaceholder("Type a name or word");
  await ta.evaluate((el, [s, e]) => {
    el.focus();
    el.setSelectionRange(s, e);
    el.dispatchEvent(new Event("select"));
  }, [start, end]);
}

async function twoColourLettering(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await typeText(page, "Fritschs Stitches");
  await selectInTextarea(page, 9, 17); // "Stitches"
  const offer = page.locator(".cr-pending");
  await offer.getByRole("button", { name: /^Thread color/ }).click();
  await offer.getByRole("option", { name: "Scarlet", exact: true }).click();
  await expect(page.locator(".cr-text")).toHaveText('"Stitches"');
  await page.waitForTimeout(400);
  const caption = await page.locator("span.stats").innerText();
  return caption.match(/([\d,]+) stitches/)[1];
}

const count = (page) => page.locator(".simcount");
const thread = (page) => page.getByTestId("sim-thread");
const shown = async (page) => Number((await count(page).innerText()).split("/")[0].replace(/[^\d]/g, ""));

async function openSim(page) {
  await page.locator('.zoomctl button[aria-label="Stitch simulator"]').click();
  await expect(page.locator(".simbar")).toBeVisible();
}

async function pause(page) {
  const btn = page.locator('.simbar button[aria-label="Pause"]');
  if (await btn.count()) await btn.click();
  await expect(page.locator('.simbar button[aria-label="Play"]')).toBeVisible();
}

test("playback stops at the thread change and names the thread to load next", async ({ page }) => {
  const total = await twoColourLettering(page);
  await openSim(page);
  await expect(thread(page)).toContainText("Thread 1 of 2");
  const stops = page.getByRole("button", { name: "Stop at thread changes" });
  await expect(stops).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Playback speed" }).click(); // 2x

  // The machine stops at the change: Play is offered again, the count is
  // short of the total, and the bar names thread 2 as the one to load.
  await expect(page.locator('.simbar button[aria-label="Play"]')).toBeVisible({ timeout: 30_000 });
  await expect(thread(page)).toContainText("Next: Thread 2 of 2");
  const atStop = await shown(page);
  expect(atStop).toBeGreaterThan(0);
  expect(atStop).toBeLessThan(Number(total.replace(/,/g, "")));
  await expect(page.locator(".fieldlive")).toContainText("thread 2 of 2");

  // Play carries on from the change to the end, on thread 2, and the count
  // finishes on the caption's number.
  await page.locator('.simbar button[aria-label="Play"]').click();
  await expect(count(page)).toHaveText(`${total} / ${total} stitches`, { timeout: 30_000 });
  await expect(thread(page)).toContainText("Thread 2 of 2");
  await expect(thread(page)).not.toContainText("Next");
});

test("with Stops off it plays straight through", async ({ page }) => {
  const total = await twoColourLettering(page);
  await openSim(page);
  const stops = page.getByRole("button", { name: "Stop at thread changes" });
  await stops.click();
  await expect(stops).toHaveAttribute("aria-pressed", "false");
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: "Playback speed" }).click(); // 8x
  await expect(count(page)).toHaveText(`${total} / ${total} stitches`, { timeout: 30_000 });
});

test("step keys and buttons: , . one stitch, < > and the skip buttons thread to thread", async ({ page }) => {
  const total = await twoColourLettering(page);
  await openSim(page);
  await pause(page);
  const canvas = page.locator(".hoop canvas");

  // Back to the start, then forward a stitch at a time from the field.
  const back = page.getByRole("button", { name: "Previous thread change" });
  for (let i = 0; i < 3 && (await back.isEnabled()); i++) await back.click();
  await expect(count(page)).toHaveText(`0 / ${total} stitches`);
  await expect(back).toBeDisabled();
  await canvas.focus();
  await page.keyboard.press(".");
  await page.keyboard.press(".");
  const two = await shown(page);
  expect(two).toBeGreaterThanOrEqual(2);
  await page.keyboard.press(",");
  expect(await shown(page)).toBeLessThan(two);

  // ">" lands ON the change (the bar names the next thread), "<" goes back.
  await page.keyboard.press(">");
  await expect(thread(page)).toContainText("Next: Thread 2 of 2");
  const change = await shown(page);
  await page.keyboard.press(".");
  await expect(thread(page)).toContainText("Thread 2 of 2");
  await expect(thread(page)).not.toContainText("Next");
  await page.keyboard.press("<");
  expect(await shown(page)).toBe(change);
  await page.keyboard.press("<");
  await expect(count(page)).toHaveText(`0 / ${total} stitches`);

  // The skip-forward button does what ">" does, and past the last change
  // goes to the end.
  await page.getByRole("button", { name: "Next thread change" }).click();
  expect(await shown(page)).toBe(change);
  await page.getByRole("button", { name: "Next thread change" }).click();
  await expect(count(page)).toHaveText(`${total} / ${total} stitches`);
  await expect(page.getByRole("button", { name: "Next thread change" })).toBeDisabled();

  // None of it moved the design: the caption still reads the same.
  await expect(page.locator("span.stats")).toContainText(`${total} stitches`);
});

test("the step keys stay out of the text box", async ({ page }) => {
  await twoColourLettering(page);
  await openSim(page);
  await pause(page);
  const before = await count(page).innerText();
  const ta = page.getByPlaceholder("Type a name or word");
  // Typing a full stop in the text regenerates the design, which closes the
  // simulator (any regeneration does) -- what must NOT happen is the key
  // stepping the simulator first.
  await ta.evaluate((el) => { el.focus(); el.setSelectionRange(el.value.length, el.value.length); });
  await page.keyboard.press(",");
  await expect(ta).toHaveValue("Fritschs Stitches,");
  await expect(page.locator(".simbar")).toHaveCount(0);
  expect(before).toMatch(/stitches$/);
});

test("the simulator's keys are listed in the shortcuts overlay", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Font credits" }).focus();
  await page.keyboard.press("Shift+?");
  const dlg = page.getByRole("dialog", { name: "Keyboard shortcuts" });
  await expect(dlg.getByText("Previous or next thread change")).toBeVisible();
  await expect(dlg.getByText("One stitch back or forward")).toBeVisible();
});
