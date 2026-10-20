// Quote settings -> the quote on screen AND the numbers on the PDF worksheet.
//
// The operator's machine, running speed, cone price/length and hourly rate
// live in QuoteSettings (Download step). The screen rows come from App's
// `sewSummary(design, quote)`; the sheet's come from exporters.js reading
// the same stored record at download time. Unit tests prove each side; only
// a real edit followed by a real download proves a changed setting reaches
// BOTH, and that they say the same thing.
import { test, expect } from "@playwright/test";
import { startStudio, openDownload } from "./helpers.js";
import { readFileSync } from "node:fs";
import zlib from "node:zlib";

// Same extractor worksheet-numbers.spec.js uses.
function pdfText(bytes) {
  const out = [];
  const raw = bytes.toString("latin1");
  const streams = [raw];
  for (const m of raw.matchAll(/stream\r?\n([\s\S]*?)endstream/g)) {
    try {
      streams.push(zlib.inflateSync(Buffer.from(m[1], "latin1")).toString("latin1"));
    } catch {
      /* not deflated — the raw pass above already covers it */
    }
  }
  for (const s of streams) {
    for (const m of s.matchAll(/\(((?:\\.|[^\\()])*)\)\s*Tj/g)) {
      out.push(m[1].replace(/\\([()\\])/g, "$1"));
    }
  }
  return out;
}

async function screenRow(sheet, label) {
  // `has` is matched relative to each row, so it must be a page-level locator.
  const row = sheet.locator("dl.summary > div", {
    has: sheet.page().locator("dt", { hasText: new RegExp(`^${label}$`) }),
  });
  return (await row.locator("dd").innerText()).trim();
}

async function setField(sheet, label, value) {
  const f = sheet.getByLabel(label);
  await f.fill(String(value));
  await f.blur(); // the component dispatches on `change`
}

async function worksheet(page) {
  const dl = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /PDF worksheet/i }).click(),
  ]).then(([d]) => d);
  return pdfText(readFileSync(await dl.path()));
}

test("quote settings change the quote on screen and the same numbers on the worksheet", async ({ page }) => {
  await startStudio(page);
  await page.locator("textarea").first().fill("FRITSCH");
  await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 20000 });
  const sheet = await openDownload(page);

  // Nothing entered: no dollar rows anywhere.
  await expect(sheet.locator("dt", { hasText: /^Thread cost$/ })).toHaveCount(0);
  await expect(sheet.locator("dt", { hasText: /^Machine time$/ })).toHaveCount(0);
  const planRun = await screenRow(sheet, "Run time");
  expect(planRun).toMatch(/at 650 spm$/);
  let texts = await worksheet(page);
  expect(texts.some((t) => t.startsWith("Thread cost:"))).toBe(false);
  expect(texts.some((t) => t.startsWith("Machine time:"))).toBe(false);
  expect(texts.some((t) => t.startsWith("Run time: ") && t.includes(" at 650 spm"))).toBe(true);

  // Fill the settings in.
  await sheet.locator("summary", { hasText: "Quote settings" }).click();
  await sheet.getByLabel("Machine model").selectOption("smartstitch_s1501");
  await setField(sheet, "Speed I run at (spm)", 900);
  await setField(sheet, "Thread cone price ($)", 7.5);
  await setField(sheet, "Thread on that cone (m)", 5000);
  await setField(sheet, "Machine rate ($ per hour)", 30);

  const run = await screenRow(sheet, "Run time");
  const threadCost = await screenRow(sheet, "Thread cost");
  const machineTime = await screenRow(sheet, "Machine time");
  expect(run).toMatch(/on your SmartStitch S-1501 at 900 spm$/);
  expect(threadCost).toContain("$7.50");
  expect(machineTime).toContain("$30.00/hr");

  texts = await worksheet(page);
  // The sheet appends " (incl. trims)" to the run time; the rest is verbatim.
  expect(texts).toContain(`Run time: ${run} (incl. trims)`);
  expect(texts).toContain(`Thread cost: ${threadCost}`);
  expect(texts).toContain(`Machine time: ${machineTime}`);

  // Change one setting: both renderings follow it.
  await setField(sheet, "Machine rate ($ per hour)", 45);
  const machineTime2 = await screenRow(sheet, "Machine time");
  expect(machineTime2).toContain("$45.00/hr");
  expect(machineTime2).not.toBe(machineTime);
  texts = await worksheet(page);
  expect(texts).toContain(`Machine time: ${machineTime2}`);

  // A speed above the S-1501's rating is capped, on both.
  await setField(sheet, "Speed I run at (spm)", 1500);
  expect(await screenRow(sheet, "Run time")).toMatch(/at 1,200 spm$/);
  texts = await worksheet(page);
  expect(texts.some((t) => t.startsWith("Run time: ") && t.includes(" at 1,200 spm"))).toBe(true);
});
