// End-to-end smoke test for the Studio's guided wizard: garment -> content
// -> review -> download, walked as a real user would, asserting real state
// at each step (not just "the page didn't crash"). Per MASTER_SCOPE.md
// capability area 3's "Next step" -- this is meant to catch regressions
// "like the rotation/hoop-fit bug class": something that renders fine but
// silently produces wrong geometry or a broken handoff between steps.
//
// This is a code-based @playwright/test spec, run via `npx playwright test`
// (or `npm run test:e2e`) -- NOT the interactive `playwright` MCP server
// (.mcp.json / tools/mcp-playwright.mjs) used for human-in-the-loop
// exploration. Both point at the same sandboxed Chromium (see
// playwright.config.js), but this file is the automated, repeatable check.
//
// Broadening pass (see MASTER_SCOPE.md capability area 3's "Next step"):
// the original single happy path below (Tote, text content, DST export) is
// unchanged; the tests after it extend coverage along the three named axes
// -- other garment types, the image-content path, and multiple export
// formats -- without multiplying this into a full combinatorial matrix. Each
// axis is varied independently against an otherwise-fixed baseline (Tote +
// "EMB TEST" text), matching how a regression in one axis would actually
// surface.
//
// The image-content path below (ContentStep's "+ Image" -- ImagePanel) is
// entirely client-side (canvas flatten, no network call), unlike the
// separate "+ Auto-digitize" path (DigitizePanel) that digitize-stale-edits
// .spec.js drives against the real Python service -- so this file has no
// service-bootstrap needs to share with that spec.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { statSync } from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Same fixture digitize-stale-edits.spec.js uses (see that file's own
// comment for why it's a checked-in real PNG, not an inlined base64 copy).
// It's just raster art to ImagePanel -- no digitizer service involved here.
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");

// ---- shared helpers -------------------------------------------------------

// Drives garment -> content(text) -> review, asserting the same real-state
// checks the original happy path does, and returns having landed on the
// "Ready to stitch" review step. Callers vary garmentLabel/text; assertions
// on what the review step reflects are left to each caller since that's the
// point being tested.
// Every stitch-format export in this file runs on a TOTE, and a tote design
// exceeds its hoop by construction: the placement box is 8 in = 203.2 mm, the
// largest hoop the app offers is "8x8 in" = 200 mm, and the design is auto-fit
// to the BOX. So the field caption has always read "Exceeds your 8x8 in hoop"
// here, and since 2026-09-02 exporting one costs a deliberate confirm.
//
// Asserted rather than tolerated: the dialog is deterministic for this garment,
// so a conditional dismiss would hide it the day it stops appearing. PNG and
// the PDF worksheet are not gated and must NOT call this.
async function confirmOversizeExport(page, fmt) {
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Exceeds your 8×8 in hoop");
  await page.getByRole("button", { name: `Download ${fmt} anyway`, exact: true }).click();
}

async function reachReviewWithText(page, garmentLabel, text) {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  const tile = page.getByRole("button", { name: garmentLabel, exact: true });
  await tile.click();
  await expect(tile).toHaveClass(/\bsel\b/);
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  const textInput = page.getByPlaceholder("Type a name or word");
  await textInput.fill(text);
  await expect(textInput).toHaveValue(text);
  await expect(page.getByText(/^\d+ stitches/)).toBeVisible();
  await expect(page.locator(".topbar-download")).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
}

test("guided wizard: garment -> content -> review -> download", async ({ page }) => {
  await page.goto("/");

  // ---- Step 1: Garment ------------------------------------------------
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();

  const toteTile = page.getByRole("button", { name: "Tote", exact: true });
  await toteTile.click();
  // Real state, not just "didn't crash": the tile picked is the one marked
  // selected (the app's own ".sel" affordance), and picking a garment is
  // what unlocks moving past this step.
  await expect(toteTile).toHaveClass(/\bsel\b/);
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeEnabled();

  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Step 2: Content --------------------------------------------------
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();

  const textInput = page.getByPlaceholder("Type a name or word");
  await textInput.fill("EMB TEST");
  await expect(textInput).toHaveValue("EMB TEST");

  // Real content produced real stitches on the field -- the topbar Download
  // shortcut and the Download step in the stepper both gate on hasStitches
  // (App.svelte), and the field's own stats readout reports a nonzero count.
  await expect(page.getByText(/^\d+ stitches/)).toBeVisible();
  await expect(page.locator(".topbar-download")).toBeEnabled();

  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Step 3: Review ("create" step, labeled "Review" in the stepper) --
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  // The recap must reflect what was actually picked/typed in the prior two
  // steps, not just render a static template -- this is exactly the kind of
  // cross-step state handoff a regression could silently break.
  await expect(page.locator("dl.summary")).toContainText("Tote");
  await expect(page.locator("dl.summary")).toContainText('Text — "EMB TEST"');

  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Step 4: Download ---------------------------------------------------
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();
  // A thread block was actually planned for the design (not an empty/failed
  // generate) -- the shopping-list summary the Download step exists for.
  await expect(page.locator(".threadlist .threadrow")).toHaveCount(1);

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  await confirmOversizeExport(page, "DST");
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe("design.dst");
  const dstPath = await download.path();
  expect(dstPath).toBeTruthy();
  const { statSync } = await import("node:fs");
  // A real stitch file, not an empty/failed export -- DST's fixed 512-byte
  // header alone means a genuine export is comfortably larger than this.
  expect(statSync(dstPath).size).toBeGreaterThan(512);

  await expect(page.getByText("Downloaded DST")).toBeVisible();
});

// ---- Axis 1: other garment types ------------------------------------------
// The original happy path only ever picks Tote. Two more garments (a small
// non-square one and the largest one in the list) confirm the garment tile
// -> review-step handoff generalizes, not just for the one size the happy
// path exercises. "Flow completes" here means reaching the Download step
// with a real thread list -- the actual download-and-verify-bytes work is
// axis 3's job, so these don't re-click a format button.
for (const garmentLabel of ["Hat Front", "Full Back"]) {
  test(`guided wizard: garment=${garmentLabel} completes and review reflects it`, async ({ page }) => {
    await reachReviewWithText(page, garmentLabel, "EMB TEST");

    // Real cross-step handoff, not a static template: the review recap names
    // THIS garment and THIS text, not whatever the last-tested garment was.
    await expect(page.locator("dl.summary")).toContainText(garmentLabel);
    await expect(page.locator("dl.summary")).toContainText('Text — "EMB TEST"');

    await page.getByRole("button", { name: "Next", exact: true }).click();

    await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();
    // The flow actually completes with something real to sew/buy thread
    // for, for this garment -- not stuck on an empty/failed generate.
    await expect(page.locator(".threadlist .threadrow").first()).toBeVisible();
  });
}

// ---- Axis 2: the image-content path ----------------------------------------
// Everything above only ever drives TextStep. ImagePanel ("+ Image" in
// ContentStep) is the other content path the review step has its own branch
// for (selectedElement.type === "image" -> "Logo / image" + color count,
// App.svelte). This is the client-side flatten path (canvas + median-cut, no
// network) -- distinct from "+ Auto-digitize" (DigitizePanel), which needs
// the real Python digitizer service the way digitize-stale-edits.spec.js
// drives it; nothing here needs that service.
test("guided wizard: image content path -> review reflects it -> download", async ({ page }) => {
  // Force the no-digitizer case: this spec is about the browser flatten lane,
  // which "+ Artwork" only routes to when the service is unreachable.
  await page.route("**/health", (r) => r.abort());
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  const toteTile = page.getByRole("button", { name: "Tote", exact: true });
  await toteTile.click();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  // "+ Artwork" is one tile that routes on service health (App.onAddElement):
  // digitizer up -> a digitized element, digitizer down -> an image element
  // and the browser's own flatten lane, which is what THIS test covers. The
  // health probe is blocked above so that routing is deterministic — without
  // it this spec's result would depend on whether a sibling spec's service
  // happened to be running, since Playwright runs the files in parallel.
  await page.getByRole("button", { name: "Artwork", exact: true }).click();

  await page.locator(".uploadbox input[type=file]").setInputFiles(ART_PNG);
  // Real processed state, not just "the input accepted a file": the panel's
  // flatten pipeline ran and produced a palette preview, and that flowed all
  // the way up into stitchable content (same hasStitches gates the original
  // text-path test checks).
  await expect(page.locator(".uploadbox .filename")).toHaveText("two-squares.png");
  await expect(page.locator(".flatprev")).not.toHaveClass(/hidden/);
  await expect(page.getByText(/^\d+ stitches/)).toBeVisible();
  await expect(page.locator(".topbar-download")).toBeEnabled();

  await page.getByRole("button", { name: "Next", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  // The recap's image branch (App.svelte), not the text branch -- and the
  // real default settings (4 colors, background removed), not a static
  // placeholder.
  await expect(page.locator("dl.summary")).toContainText("Logo / image");
  await expect(page.locator("dl.summary")).toContainText("background removed");

  await page.getByRole("button", { name: "Next", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();
  await expect(page.locator(".threadlist .threadrow").first()).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  // NO confirm here, deliberately: the imported PNG does not fill the
  // placement box the way auto-fit lettering does, so this design fits the
  // 8x8 hoop and downloads in one click. The contrast with the text path
  // above is the gate working -- it fires on the design, not on the garment.
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe("design.dst");
  const dstPath = await download.path();
  expect(dstPath).toBeTruthy();
  expect(statSync(dstPath).size).toBeGreaterThan(512);
});

// ---- Axis 3: multiple export formats ---------------------------------------
// The original happy path only downloads DST. PES and EXP are the other two
// binary machine formats DownloadStep offers (SVG/PNG are vector/raster
// previews, not stitch files a machine reads), plus the PDF worksheet (a
// different code path entirely -- jsPDF, not exportDesign). One wizard run
// through to the Download step, three format clicks against it: each is a
// real download, verified on disk, not just "a click handler ran".
test("guided wizard: PES, EXP, and PDF worksheet exports produce real files", async ({ page }) => {
  await reachReviewWithText(page, "Tote", "EMB TEST");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();

  // ---- PES: has a real, checkable magic header ("#PES0001") -------------
  const pesDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "PES", exact: true }).click();
  await confirmOversizeExport(page, "PES");
  const pesDownload = await pesDownloadPromise;
  expect(pesDownload.suggestedFilename()).toBe("design.pes");
  const pesPath = await pesDownload.path();
  expect(pesPath).toBeTruthy();
  const { readFileSync } = await import("node:fs");
  const pesBytes = readFileSync(pesPath);
  expect(pesBytes.length).toBeGreaterThan(64);
  expect(pesBytes.subarray(0, 8).toString("ascii")).toBe("#PES0001");
  await expect(page.getByText("Downloaded PES")).toBeVisible();

  // ---- EXP: no fixed magic header, so pin real stitch-record content ----
  // instead (a genuine "EMB TEST" export is comfortably more than a
  // handful of bytes; an empty/failed export would be near-zero).
  const expDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "EXP", exact: true }).click();
  await confirmOversizeExport(page, "EXP");
  const expDownload = await expDownloadPromise;
  expect(expDownload.suggestedFilename()).toBe("design.exp");
  const expPath = await expDownload.path();
  expect(expPath).toBeTruthy();
  expect(statSync(expPath).size).toBeGreaterThan(64);
  await expect(page.getByText("Downloaded EXP")).toBeVisible();

  // ---- PDF worksheet: a distinct export path (jsPDF, not exportDesign) --
  // real PDF magic header, not just a nonzero byte count.
  const pdfDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "PDF worksheet", exact: true }).click();
  const pdfDownload = await pdfDownloadPromise;
  expect(pdfDownload.suggestedFilename()).toBe("embbot-worksheet.pdf");
  const pdfPath = await pdfDownload.path();
  expect(pdfPath).toBeTruthy();
  const pdfBytes = readFileSync(pdfPath);
  expect(pdfBytes.length).toBeGreaterThan(64);
  expect(pdfBytes.subarray(0, 5).toString("ascii")).toBe("%PDF-");
  await expect(page.getByText("Worksheet saved.")).toBeVisible();
});

// --- the step panel starts at the top -------------------------------------

// The panel scrolls, and its offset used to survive a step change. That lands
// on the path EVERY user takes, because the fabric picker sits below the fold:
// measured on the shipped build at 1440x900, the garment step was 1320px of
// content in a 741px viewport with "Fabric color" 529px down, so choosing a
// fabric REQUIRED scrolling — and pressing Next then opened the content step
// already 493px down, with "what do you want to say?" off-screen above it and
// no visible way forward.
test("the step panel is scrolled to the top after every step change", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const panel = page.locator(".panel-body");
  const scrollTop = () => panel.evaluate((el) => el.scrollTop);

  // The garment step really is taller than its viewport — if it ever stops
  // being, this test would pass without exercising anything.
  const overflow = await panel.evaluate((el) => el.scrollHeight - el.clientHeight);
  expect(overflow).toBeGreaterThan(100);

  await page.getByRole("button", { name: "Tote", exact: true }).click();

  // Scroll the way someone picking a fabric colour has to.
  await panel.evaluate((el) => { el.scrollTop = el.scrollHeight; });
  expect(await scrollTop()).toBeGreaterThan(100);

  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await expect.poll(scrollTop).toBe(0);

  // And on the way back, which is the same defect in the other direction.
  await panel.evaluate((el) => { el.scrollTop = el.scrollHeight; });
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  await expect.poll(scrollTop).toBe(0);
});
