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

test("the worksheet names the chart its codes came out of", async ({ page }) => {
  // "1375 Dark Charcoal" is not a thread anyone can buy until the sheet says
  // whose 1375 it is. Measured 2026-09-07: picking Isacord in the Studio
  // re-labelled the design's black to that catalog's nearest cone, the
  // Download step showed "Chart: Isacord Polyester 40" beside it, and the
  // printed sheet gave the code alone. All 68 charts number independently.
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("FRITSCH");
  await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 20000 });

  await page.getByRole("button", { name: "Next", exact: true }).click();   // Review
  await page.getByRole("button", { name: "Next", exact: true }).click();   // Download

  // Pick a real manufacturer chart, the way a customer with a thread rack does.
  const chart = page.getByLabel("Thread chart");
  await chart.selectOption({ label: "Isacord Polyester 40" });
  // The codes only arrive once the lazy brand chunk lands.
  await expect(page.locator(".threadrow-name").first()).toContainText(/^\d{3,4}\s/, { timeout: 20000 });
  const cone = (await page.locator(".threadrow-name").first().innerText()).trim();
  const shownChart = await chart.locator("option:checked").innerText();

  const dl = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /PDF worksheet/i }).click(),
  ]).then(([d]) => d);
  const texts = pdfText(readFileSync(await dl.path()));

  // The sheet prints the code the screen printed...
  expect(texts).toContain(`1. ${cone}`);
  // ...and says whose numbering it is, matching the screen exactly.
  expect(texts).toContain(`Chart: ${shownChart}`);
});

test("a design that cannot be hooped says so on the sheet, not only in the export confirm", async ({ page }) => {
  // The Download step refuses a STITCH export for an oversize design until the
  // customer confirms ("the machine cannot stitch past the edge of the hoop"),
  // and rightly does not gate the worksheet — printing a reference sheet is
  // harmless. But the sheet carried no trace of it.
  //
  // Measured 2026-09-07 by rendering a real worksheet to an image and looking
  // at it: Full Back, a name auto-fitted to the placement area, "Hoop: 8x8 in
  // (200 mm x 200 mm)" printed above a 305.0 mm design — and the picture below
  // showed it comfortably inside the dashed box, because that box is the
  // GARMENT placement area, not the hoop. The one document that goes to the
  // machine was the one that never mentioned the design cannot be hooped.
  //
  // e2e rather than unit because the unit tier only proves pdfsheet.js prints
  // the sentence it is HANDED; this proves the Studio actually hands it over,
  // across DownloadStep -> exporters.js -> the engine copy.
  await page.goto("/");
  await page.getByRole("button", { name: "Full Back", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByPlaceholder("Type a name or word").fill("FRITSCH'S STITCHES");
  await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 20000 });

  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  const dl = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /PDF worksheet/i }).click(),
  ]).then(([d]) => d);
  const texts = pdfText(readFileSync(await dl.path()));

  // The premise: this design really does exceed every hoop the app offers. If
  // the garment or the auto-fit changes so it fits, the assertion below would
  // hold vacuously — so fail loudly instead.
  const exceeds = texts.find((t) => t.startsWith("Exceeds your "));
  expect(exceeds, "the sheet states the design exceeds its hoop").toBeTruthy();
  // Cause, consequence and a lever — the standard every other message here is
  // held to. It must not merely say "too big".
  expect(exceeds).toMatch(/hoop/);
  expect(exceeds).toMatch(/smaller|rotate|fits it/);
  // And it names the hoop the sheet itself printed two lines above.
  expect(texts.some((t) => t.startsWith("Hoop: "))).toBe(true);
});
