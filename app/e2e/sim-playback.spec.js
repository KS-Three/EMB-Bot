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
import { typeText, openDownload, closeDownload } from "./helpers.js";

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

// ---- Round 2 (2026-11-07): the strip is clickable, Isolate, underlay ------

// A cheap fingerprint of the field's pixels, to tell "changed" from "the
// same picture" without a screenshot diff.
async function canvasSum(page) {
  return page.locator(".hoop canvas").evaluate((c) => {
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let s = 0, h = 0;
    for (let i = 0; i < d.length; i += 4) { s += d[i] + d[i + 1] + d[i + 2]; h = (h * 31 + d[i] + 7 * d[i + 1] + 13 * d[i + 2]) >>> 0; }
    return { s, h };
  });
}

test("a click on a thread's band in the strip goes to the start of that thread", async ({ page }) => {
  const total = await twoColourLettering(page);
  await openSim(page);
  await pause(page);
  const strip = page.getByTestId("sim-strip");
  const bands = strip.locator("button");
  await expect(bands).toHaveCount(2);
  // The band is where `>` lands: on the change, naming thread 2 next.
  await page.getByRole("button", { name: "Next thread change" }).click();
  const change = await shown(page);
  await page.getByRole("button", { name: "Previous thread change" }).click();
  await expect(count(page)).toHaveText(`0 / ${total} stitches`);
  await strip.getByRole("button", { name: /^Go to thread 2 of 2/ }).click();
  expect(await shown(page)).toBe(change);
  await expect(thread(page)).toContainText("Next: Thread 2 of 2");
  await expect(page.locator(".fieldlive")).toContainText("thread 2 of 2");
  // Thread 1's band goes back to the design's start.
  await strip.getByRole("button", { name: /^Go to thread 1 of 2/ }).click();
  await expect(count(page)).toHaveText(`0 / ${total} stitches`);
  await expect(thread(page)).toContainText("Thread 1 of 2");
  // Out of the Tab order: Tab from Play never lands on a band.
  for (const b of await bands.all()) await expect(b).toHaveAttribute("tabindex", "-1");
  // The bands are mouse targets of their own, not painted over the slider:
  // a click mid-slider still scrubs.
  const box = await page.locator(".simscrub").boundingBox();
  await page.mouse.click(box.x + box.width * 0.75, box.y + box.height / 2);
  const scrubbed = await shown(page);
  expect(scrubbed).toBeGreaterThan(change);
  expect(scrubbed).toBeLessThan(Number(total.replace(/,/g, "")));
});

test("Isolate dims everything but the thread on the needle, and off is the same picture", async ({ page }) => {
  const total = await twoColourLettering(page);
  await openSim(page);
  await pause(page);
  // Into thread 2 by a few stitches: thread 1 is all sewn behind it.
  await page.getByRole("button", { name: "Next thread change" }).click();
  const canvas = page.locator(".hoop canvas");
  await canvas.focus();
  for (let i = 0; i < 20; i++) await page.keyboard.press(".");
  await expect(thread(page)).toContainText("Thread 2 of 2");
  const at = await count(page).innerText();
  const iso = page.getByRole("button", { name: "Isolate the thread on the needle" });
  await expect(iso).toHaveAttribute("aria-pressed", "false");
  await page.waitForTimeout(150);
  const plain = await canvasSum(page);
  await iso.click();
  await expect(iso).toHaveAttribute("aria-pressed", "true");
  await page.waitForTimeout(150);
  const dimmed = await canvasSum(page);
  expect(dimmed.h).not.toBe(plain.h);
  // The wash lifts thread 1 toward the bed (a mid grey), so the picture moves.
  expect(Math.abs(dimmed.s - plain.s)).toBeGreaterThan(0);
  // Nothing about the playback moved.
  await expect(count(page)).toHaveText(at);
  await iso.click();
  await expect(iso).toHaveAttribute("aria-pressed", "false");
  await page.waitForTimeout(150);
  expect((await canvasSum(page)).h).toBe(plain.h);
  // And it keeps its state through playback to the end.
  await iso.click();
  await page.locator('.simbar button[aria-label="Play"]').click();
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: "Playback speed" }).click();
  await expect(count(page)).toHaveText(`${total} / ${total} stitches`, { timeout: 30_000 });
  await expect(iso).toHaveAttribute("aria-pressed", "true");
});

test("the bar says when the needle is laying underlay and when it is on the top stitching", async ({ page }) => {
  await twoColourLettering(page);
  await openSim(page);
  await pause(page);
  const phase = page.getByTestId("sim-phase");
  await expect(phase).toBeVisible();
  const canvas = page.locator(".hoop canvas");
  await canvas.focus();
  // Lettering lays an underlay under each satin letter before the satin, so
  // stepping forward from the start passes through both. (What the canvas
  // draws for pending underlay is pinned in simOverlay.round2.spec.js.)
  let seen = { underlay: false, top: false };
  for (let i = 0; i < 400 && !(seen.underlay && seen.top); i++) {
    await page.keyboard.press(".");
    const t = (await phase.innerText()).trim();
    if (t === "Underlay") seen.underlay = true;
    if (t === "Top") seen.top = true;
  }
  expect(seen.underlay).toBe(true);
  expect(seen.top).toBe(true);
});

test("the mouse over the field and a wheel zoom leave the simulator open where it was", async ({ page }) => {
  // Before 2026-11-07 the first pointer move over the canvas closed it: the
  // cursor write invalidated `canvas`, which re-ran paint(), which stops the
  // simulator. A customer's mouse is over the field all the time.
  const total = await twoColourLettering(page);
  await openSim(page);
  await pause(page);
  await page.getByRole("button", { name: "Next thread change" }).click();
  const at = await count(page).innerText();
  const h = await page.locator(".hoop").boundingBox();
  await page.mouse.move(h.x + h.width / 2, h.y + h.height / 2, { steps: 4 });
  await page.mouse.move(h.x + 20, h.y + 20, { steps: 4 });
  for (let i = 0; i < 4; i++) await page.mouse.wheel(0, -100);
  await page.waitForTimeout(300);
  await expect(page.locator(".simbar")).toBeVisible();
  await expect(count(page)).toHaveText(at);
  await expect(thread(page)).toContainText("Next: Thread 2 of 2");
  // And it still plays to the end from there.
  await page.locator('.simbar button[aria-label="Play"]').click();
  await page.mouse.move(h.x + h.width / 2, h.y + h.height / 3, { steps: 4 });
  await expect(count(page)).toHaveText(`${total} / ${total} stitches`, { timeout: 30_000 });
});

test("the bar estimates the sew time left, on the Run time's own figure and rate", async ({ page }) => {
  // Kent 2026-11-07, "Show it": the same sewTimeMin at the same 650 spm
  // planning rate as the Download step's "Run time" row, so the bar's total
  // IS that row's minutes. Labelled as an estimate, its basis in the tooltip.
  const total = await twoColourLettering(page);
  const sheet = await openDownload(page);
  const row = sheet.locator("dl.summary > div", { has: page.locator("dt", { hasText: /^Run time$/ }) });
  const run = (await row.locator("dd").innerText()).trim(); // "~3 min at 650 spm"
  const m = run.match(/^~(\d+) min.* at 650 spm$/);
  expect(m, `Run time row: ${run}`).not.toBeNull();
  const minutes = m[1];
  await closeDownload(page);

  await openSim(page);
  await pause(page);
  const back = page.getByRole("button", { name: "Previous thread change" });
  for (let i = 0; i < 3 && (await back.isEnabled()); i++) await back.click();
  await expect(count(page)).toHaveText(`0 / ${total} stitches`);
  const time = page.getByTestId("sim-time");
  await expect(time).toHaveText(`about ${minutes} min left of ${minutes}`);
  await expect(time).toHaveAttribute("title", /650 stitches per minute.*planning rate.*Trims and thread changes are included/);

  // Mid-design it counts down and never above the total; at the end it is
  // the whole run.
  await page.getByRole("button", { name: "Next thread change" }).click();
  const mid = (await time.innerText()).match(/^about (\d+) min left of (\d+)$/);
  expect(mid).not.toBeNull();
  expect(mid[2]).toBe(minutes);
  expect(Number(mid[1])).toBeLessThanOrEqual(Number(minutes));
  await page.getByRole("button", { name: "Next thread change" }).click();
  await expect(count(page)).toHaveText(`${total} / ${total} stitches`);
  await expect(time).toHaveText(`about ${minutes} min in all`);
});

test("with a Quote speed set, the bar and the Run time row use it, and the tooltip says so", async ({ page }) => {
  // #1334's Decision 1, Kent's pick (b): one rate for both figures on the
  // screen (estimate.js runSpm). The speed is the operator's own Quote
  // setting, stored where QuoteSettings saves it.
  await page.addInitScript(() => {
    localStorage.setItem("embstudio:quote", JSON.stringify({ spm: 1000 }));
  });
  const total = await twoColourLettering(page);
  const sheet = await openDownload(page);
  const row = sheet.locator("dl.summary > div", { has: page.locator("dt", { hasText: /^Run time$/ }) });
  const run = (await row.locator("dd").innerText()).trim();
  const m = run.match(/^~(\d+) min.* at 1,000 spm$/);
  expect(m, `Run time row: ${run}`).not.toBeNull();
  const minutes = m[1];
  await closeDownload(page);

  await openSim(page);
  await pause(page);
  const back = page.getByRole("button", { name: "Previous thread change" });
  for (let i = 0; i < 3 && (await back.isEnabled()); i++) await back.click();
  await expect(count(page)).toHaveText(`0 / ${total} stitches`);
  const time = page.getByTestId("sim-time");
  await expect(time).toHaveText(`about ${minutes} min left of ${minutes}`);
  await expect(time).toHaveAttribute("title", /^Estimated sew time at 1,000 stitches per minute, your speed from Quote settings\./);
  await expect(time).not.toHaveAttribute("title", /planning rate/);
});

test("resizing the window leaves the simulator open where it was, and repaints the field once", async ({ page }) => {
  // #1334's Decision 2: fitCanvasToPane's canvas.width/height writes
  // invalidated `canvas`, so every resize re-ran paint() (the regenerate,
  // which opens with stopSim()). A field render is counted the way
  // field-hover-repaint.spec.js counts it: renderRealistic opens every one
  // with fillRect(0, 0, cw, ch) on the `.hoop` canvas.
  await page.addInitScript(() => {
    window.__fieldRenders = 0;
    const fill = CanvasRenderingContext2D.prototype.fillRect;
    CanvasRenderingContext2D.prototype.fillRect = function (x, y, w, h) {
      const c = this.canvas;
      if (x === 0 && y === 0 && c && c.closest && c.closest(".hoop") && w >= c.clientWidth - 1 && h >= c.clientHeight - 1) {
        window.__fieldRenders++;
      }
      return fill.apply(this, arguments);
    };
  });
  const settle = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 600)))));
  await twoColourLettering(page);
  await openSim(page);
  await pause(page);
  await page.getByRole("button", { name: "Next thread change" }).click();
  const at = await count(page).innerText();
  await settle();
  const sizes = [{ width: 1200, height: 820 }, { width: 1440, height: 900 }, { width: 1320, height: 760 }];
  const perResize = [];
  for (const s of sizes) {
    const before = await page.evaluate(() => window.__fieldRenders);
    const w0 = await page.locator(".hoop canvas").evaluate((c) => c.width);
    await page.setViewportSize(s);
    await settle();
    const w1 = await page.locator(".hoop canvas").evaluate((c) => c.width);
    expect(w1, `bitmap resized at ${s.width}x${s.height}`).not.toBe(w0);
    perResize.push((await page.evaluate(() => window.__fieldRenders)) - before);
    console.log(`[sim-resize] ${s.width}x${s.height}: ${perResize[perResize.length - 1]} field render(s)`);
    await expect(page.locator(".simbar")).toBeVisible();
    await expect(count(page)).toHaveText(at);
    await expect(thread(page)).toContainText("Next: Thread 2 of 2");
  }
  // repaintView() only: one render per resize, no regenerate on top.
  for (const n of perResize) expect(n).toBe(1);
});
