// The Review step and the printed worksheet, on the same design, at the same
// moment — they must not disagree about what it costs to sew.
//
// estimate.js calls these "the four facts an operator needs before loading a
// machine": size, stitches, trims, thread. The Review step has stated all
// four since 2026-09-07; the worksheet printed the first two and dropped the
// other two. Measured that day on a lettering design: the screen read
// "Size 102 x 15 mm / Stitches 1,336 / Trims 6 / Thread 2.5 m (estimate)"
// and the sheet said only the size and the count. The screen stays at the
// desk. The sheet is what goes to the machine.
//
// This is an e2e rather than a unit test because the disagreement was
// between two SEPARATE renderings of one design — pdfsheet.spec.js can prove
// the sheet prints what it is given, and estimate.spec.js can prove the walk,
// but only a real download proves the app hands the sheet the same numbers it
// just put on the screen.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import zlib from "node:zlib";

// Same extractor pdfsheet.realpdf.spec.js uses: every `(...) Tj` string out
// of the content streams, un-escaping the parens PDF requires. jsPDF may or
// may not compress a stream, so try inflate and fall back to the raw bytes.
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

test("the printed worksheet states the same trims and thread the review does", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("FRITSCH");
  await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 20000 });

  // ---- what the screen says -----------------------------------------------
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const review = (await page.locator("body").innerText()).replace(/\s+/g, " ");
  const trims = review.match(/Trims (\d[\d,]*)/);
  const thread = review.match(/Thread ([\d.]+) m \(estimate\)/);
  const stitches = review.match(/Stitches (\d[\d,]*)/);
  // The premise: the review really does state all three. If it stops, the
  // agreement below would hold vacuously.
  expect(trims, "review step states a trim count").not.toBeNull();
  expect(thread, "review step states a thread estimate").not.toBeNull();
  expect(stitches, "review step states a stitch count").not.toBeNull();
  expect(Number(thread[1])).toBeGreaterThan(0);

  // ---- what the sheet says ------------------------------------------------
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const dl = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /PDF worksheet/i }).click(),
  ]).then(([d]) => d);
  expect(dl.suggestedFilename()).toBe("embbot-worksheet.pdf");
  const texts = pdfText(readFileSync(await dl.path()));

  // Not "contains a number that looks right" — the SAME numbers, verbatim.
  expect(texts).toContain(`Trims: ${trims[1]}`);
  expect(texts).toContain(`Thread: ${thread[1]} m (estimate)`);
  expect(texts).toContain(`Stitch count: ${stitches[1]}`);
});
