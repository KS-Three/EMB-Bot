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

// The caption groups thousands (`toLocaleString`) since 2026-09-07 — it was
// the one stitch count in the app printing a bare 1289 where QualityReport,
// DigitizePanel, DesignPanel and the review summary all say 1,289. Every
// `[\d,]+` in this file's caption matchers is that, not a loosened assertion.
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
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
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
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
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
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
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

// The review step on an EMPTY project, which nothing had ever driven: every
// test above types text or uploads art before advancing, so the summary was
// only ever seen full. A brand-new project holds one empty text element, and
// the stepper lets you jump straight to Review from the garment step.
//
// Until 2026-09-07 that screen read "**Ready to stitch** — Looks good? The
// live field is your stitch-out." over a summary saying `Text — ""` and a
// canvas saying "Your embroidery appears here as you add content." The only
// contradiction was a disabled Next button with no reason attached.
//
// `flow.js`'s `canAdvance("create", …)` already computed the right answer and
// only the button consulted it; the headline now does too. This drives the
// state transition in both directions, because a headline that is merely
// pessimistic would be its own bug.
test("the review step does not claim readiness for a design with nothing in it", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Left Chest", exact: true }).click();

  // Jump the stepper straight to Review, skipping Content entirely — the
  // badge carries the step number, so the accessible name is "3 Review".
  await page.getByRole("button", { name: "3 Review" }).click();

  await expect(page.getByRole("heading", { name: "Nothing to stitch yet" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toHaveCount(0);
  // The summary says it in words, not as two quote marks.
  await expect(page.locator("dl.summary")).toContainText("nothing typed yet");
  await expect(page.locator("dl.summary")).not.toContainText('Text — ""');
  // And Next stays shut, which is the behaviour the headline now agrees with.
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeDisabled();

  // Now give it something to sew and watch the same screen change its mind.
  await page.getByRole("button", { name: "Content" }).click();
  const textInput = page.locator("textarea").first();
  await textInput.fill("HELLO");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();

  await page.getByRole("button", { name: "3 Review" }).click();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nothing to stitch yet" })).toHaveCount(0);
  await expect(page.locator("dl.summary")).toContainText('Text — "HELLO"');
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeEnabled();
});

// Artwork must survive a refresh — the case that was silently losing work.
//
// An `image` element (the browser flatten lane) is created only when the
// digitizer service is DOWN: App.onAddElement routes "artwork" through
// resolveArtworkType(digitizerHealth), and the Content step tells the user
// outright that art will be "placed but not auto-digitized". So this is an
// explicitly supported state — and until 2026-09-07 it was the one where a
// page refresh destroyed the user's work. Measured on the shipped build:
// 2739 stitches before, no stitch caption after, and no message either way,
// because the pixels lived only in App's `runtime` (not persisted) while
// `_hasImage: true` was written to localStorage.
//
// Aborting /health is what makes the app believe the service is down; it is
// the only lever, and it is the real code path rather than a stubbed one.
test("artwork uploaded with the digitizer offline survives a page refresh", async ({ page }) => {
  await page.route("**/health", (r) => r.abort());
  await page.goto("/");

  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator("input[type=file]").first().setInputFiles(ART_PNG);

  const caption = page.locator("span.stats");
  await expect(caption).toBeVisible({ timeout: 60_000 });
  const before = await caption.innerText();
  expect(before).toMatch(/[\d,]+ stitches/);

  // The pixels must be ON the element, not only in runtime — that is what
  // makes the reload below possible at all.
  const saved = await page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const el = JSON.parse(localStorage.getItem("embstudio:p:" + id)).elements
      .find((e) => e.type === "image");
    return { name: el.name, hasPng: typeof el.sourcePng === "string" && el.sourcePng.length > 100 };
  });
  expect(saved.hasPng).toBe(true);
  expect(saved.name).toBe("two-squares.png");

  await page.reload();

  // On the step the reload LANDS on, not after navigating to Content: the
  // embroidery field is visible beside every step, so restoring in the panel
  // would leave this empty and read as lost work.
  await expect(caption).toHaveText(before, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();

  // Opening a project is a RESTORE, not an edit. The rehydrate publishes
  // `_hasImage` through the same path an upload does, and letting that record
  // an undo step meant one press of Undo returned `_hasImage` to false while
  // `runtime.flats` still held the flat — the design stayed on screen while
  // the review step called it empty and Next went disabled (measured
  // 2026-09-07: 1473 stitches visible under "Nothing to stitch yet"). Undo
  // must have nothing to undo here, because the user did nothing.
  await expect(page.getByRole("button", { name: "Undo", exact: true })).toBeDisabled();

  // And the design is really there, not just a stale caption: the review
  // step's own gate has to agree.
  await page.getByRole("button", { name: "3 Review" }).click();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nothing to stitch yet" })).toHaveCount(0);
  await expect(page.locator("dl.summary")).toContainText("Logo / image");
});

// A name PLUS a logo — the commonest real job, and the one the review recap
// described only half of. It keyed off the selected element, so a design with
// lettering under an uploaded logo reached the last screen before Download
// saying "Auto-digitized artwork" and nothing about the words also sewing.
// Measured 2026-09-07: left chest, 3542 stitches, three cones, one element
// named. This is the browser flatten lane (service left alone) so the test
// needs no digitizer.
test("the review recap names every element, not just the selected one", async ({ page }) => {
  await page.route("**/health", (r) => r.abort());   // browser lane: `image`
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await page.locator("textarea").first().fill("FRITSCH'S");
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator("input[type=file]").first().setInputFiles(ART_PNG);
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "3 Review" }).click();
  const summary = page.locator("dl.summary");
  await expect(summary).toContainText('Text — "FRITSCH\'S"');
  await expect(summary).toContainText("Logo / image");
  // Numbered, so two "Content" rows are tellable apart.
  await expect(summary.locator("dt", { hasText: /^Content 1$/ })).toBeVisible();
  await expect(summary.locator("dt", { hasText: /^Content 2$/ })).toBeVisible();
});

test("the size field and the field caption report one width, and the field is not in an invalid state", async ({ page }) => {
  // The two numbers a customer sees for the size of their design come from
  // different places: the field caption reads the design's own widthMM, the
  // Size panel reads the stitch bbox. Until 2026-09-07 those were different
  // measurements, and the very first screen of the most common quick start
  // showed it: caption "127×13 mm" next to a W field reading 5.05 in
  // (= 128.3 mm) whose own max was 5.00 — so the browser had the input at
  // `rangeOverflow: true, valid: false` on a design with nothing wrong with it.
  //
  // Both halves are asserted here because they failed together and the fix is
  // in two places: the engine now reports the sewn extent (digitize.js
  // designExtentMm), and SizePanel no longer puts a REQUEST bound on a field
  // that displays a SEWN size (the clamp lives in onWidthChange, unchanged).
  await page.goto("/");
  await page.getByRole("button", { name: /^Name on a hat/ }).click();
  await page.getByRole("button", { name: "2 Content", exact: true }).click();

  const stats = page.locator("span.stats");
  await expect(stats).toBeVisible({ timeout: 60_000 });
  const caption = await stats.innerText();
  const capW = Number(caption.match(/(\d+)×\d+ mm/)[1]);

  const w = page.getByLabel("Width");
  const unit = await page.locator("select.unitselect").inputValue();
  expect(unit).toBe("in");
  const fieldMm = Number(await w.inputValue()) * 25.4;

  // The caption rounds to whole mm; agreement to within that rounding is the
  // strongest claim the two displays can make, and it is the one that broke
  // (127 vs 128.3 is 1.3 mm apart, not a rounding step).
  expect(Math.abs(fieldMm - capW)).toBeLessThanOrEqual(0.5);

  // …and the honest number is not fighting a constraint on its own input.
  expect(await w.evaluate((el) => el.validity.valid)).toBe(true);
  expect(await w.evaluate((el) => el.checkValidity())).toBe(true);
});

test("a font that can't set the text names the fonts that can — or says none can", async ({ page }) => {
  // "This font can’t stitch «Р», «у», «с». Try a different font, or different
  // text." was true and unactionable: three shipped fonts cover Cyrillic,
  // three cover Greek, two cover Hebrew, and NONE covers Japanese, Korean or
  // Arabic. Finding that out meant opening up to 85 fonts by hand, or looking
  // for something that is not there.
  //
  // The suggestion is async (a lazily fetched 16 KB index) and lands after the
  // paint that shows the generic sentence, so both assertions wait rather than
  // reading once.
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await page.locator("textarea").first().fill("Иван");
  await expect(page.getByText(/Switch fonts and it will stitch/)).toBeVisible({ timeout: 60_000 });
  // Named, not just promised — the point is that the customer can act on it.
  await expect(page.getByText(/can\. Switch fonts/)).toBeVisible();

  // And the other answer, which is a different one on purpose: no font in the
  // library covers Japanese, so "try a different font" would be bad advice.
  await page.locator("textarea").first().fill("日本語");
  await expect(page.getByText(/No font in this library can stitch/)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/Switch fonts/)).toHaveCount(0);
});

// Playwright's ARIA snapshot renders each control as `- role "accessible
// name"`. A control with no name renders without the quoted part, which is
// what this looks for — the same thing a screen reader would announce as a
// bare "slider" or "combobox".
async function unnamedControls(page) {
  const snap = await page.locator("body").ariaSnapshot();
  return [...new Set(snap.split("\n").map((l) => l.trim())
    .filter((l) => /^- (button|slider|spinbutton|textbox|combobox|checkbox|radio|link)\b/.test(l))
    .filter((l) => !l.includes('"')))];
}

test("every control in the wizard has an accessible name", async ({ page }) => {
  // Swept 2026-09-07 across all four steps: exactly ONE control in the app was
  // unnamed (SizePanel's in/cm/mm select). Most are named implicitly by a
  // wrapping <label> — the four TextStep sliders read "Letter spacing 0.0 mm",
  // "Curve 0°", "Rotation 0°", "Slant 0°" — which is easy to break by moving
  // an input out of its label while everything still LOOKS right.
  await page.goto("/");
  expect(await unnamedControls(page), "garment step").toEqual([]);

  await page.getByRole("button", { name: /^Name on a hat/ }).click();
  await page.getByRole("button", { name: "2 Content", exact: true }).click();
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  expect(await unnamedControls(page), "content step, text").toEqual([]);

  await page.getByRole("button", { name: "Artwork", exact: true }).click();
  expect(await unnamedControls(page), "content step, artwork").toEqual([]);

  await page.getByRole("button", { name: "3 Review", exact: true }).click();
  expect(await unnamedControls(page), "review step").toEqual([]);

  await page.getByRole("button", { name: "4 Download", exact: true }).click();
  expect(await unnamedControls(page), "download step").toEqual([]);
});

test("a page load produces no console errors and no failed requests", async ({ page }) => {
  // The only one there has ever been is the /favicon.ico 404 every browser
  // makes when a page declares no icon — which is also why a customer's
  // bookmark showed a blank tab. `app/public/favicon.svg` (the topbar's own
  // accent tile, with a stitch zigzag instead of the word "EMB", which is
  // illegible at 16 px) settles both.
  const problems = [];
  page.on("console", (m) => { if (m.type() === "error") problems.push("[console] " + m.text().slice(0, 160)); });
  page.on("pageerror", (e) => problems.push("[pageerror] " + e.message.slice(0, 160)));
  page.on("requestfailed", (r) => problems.push("[requestfailed] " + r.url()));

  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  expect(problems).toEqual([]);
});

test("the empty canvas says how to reach the drawing tools", async ({ page }) => {
  // Two of PRODUCT.md's four launch-scope items — the basic shapes tool and
  // the manual draw lane — live on the canvas's right-click menu (Kent's
  // placement call, 2026-08-13: a tool, not an upload button). Nothing in the
  // UI said so, and right-click on a canvas is a power-user idiom a first-time
  // customer has no reason to try.
  //
  // The drag hint would be the obvious place and is the wrong one: hints.js
  // gates it on `stitchCount > 0`, so it appears only once there is already a
  // design — after the question has stopped being asked.
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".fieldhint")).toContainText("Right-click the canvas for drawing tools");

  // …and the gesture it names actually reaches both tools, on the real canvas.
  await page.locator("canvas").first().click({ button: "right", position: { x: 200, y: 120 } });
  const menu = page.getByRole("menu", { name: "Canvas tools" });
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("menuitem")).toHaveText(["Draw shapes", "Basic shape"]);

  // The shape lane produces real stitches — the launch-scope item, end to end.
  await menu.getByRole("menuitem", { name: "Basic shape" }).click();
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  for (const kind of ["Circle", "Rectangle", "Heart", "Star"]) {
    await expect(page.getByRole("button", { name: kind, exact: true })).toBeVisible();
  }
});

test("the simulator counts in the same unit the caption does", async ({ page }) => {
  // The animation is driven by STRANDS — the segments between consecutive
  // stitches — so N stitches in K runs make N − K strands. The counter showed
  // that raw number: "1289 stitches · 102×12 mm" under the canvas and
  // "1280 / 1280" in the simulator bar, nine apart on a design with nine runs.
  // Both correct, measuring different things, only one of them labelled.
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("FRITSCH'S");
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  const captionCount = Number((await page.locator("span.stats").innerText()).match(/([\d,]+) stitches/)[1].replace(/,/g, ""));
  expect(captionCount).toBeGreaterThan(100);

  await page.getByRole("button", { name: "Stitch simulator" }).click();
  const counter = page.locator(".simcount");
  await expect(counter).toBeVisible();
  // The total is asserted immediately; the running number is left alone,
  // because it is mid-animation and racing it would be the flaky assertion.
  await expect(counter).toContainText(new RegExp(`/ ${captionCount} stitches$`));
  // …and it gets there. The design is short, so the default 1x run finishes
  // well inside this budget.
  await expect(counter).toHaveText(`${captionCount} / ${captionCount} stitches`, { timeout: 60_000 });
});

test("the review names what it costs to sew — on the lane the service never sees", async ({ page }) => {
  // An auto-digitized design gets these from the service (QualityReport). A
  // lettering, hand-drawn, shape or imported-DST design never reaches it, and
  // this screen showed the garment, the hoop, the content, the font — and not
  // one number about the sew-out.
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("FRITSCH'S");
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  const caption = await page.locator("span.stats").innerText();
  const stitches = caption.match(/([\d,]+) stitches/)[1];
  const size = caption.match(/(\d+)×(\d+) mm/);

  await page.getByRole("button", { name: "3 Review", exact: true }).click();
  const summary = page.locator("dl.summary");
  // The same design, so the same numbers as the caption — this is the
  // assertion that catches the two drifting apart.
  await expect(summary).toContainText(`${size[1]} × ${size[2]} mm`);
  await expect(summary).toContainText(stitches);
  await expect(summary).toContainText("Trims");
  await expect(summary).toContainText(/\d+\.\d m \(estimate\)/);
  // No service report on this lane, so nothing can contradict it.
  await expect(page.locator("section.quality")).toHaveCount(0);
});
