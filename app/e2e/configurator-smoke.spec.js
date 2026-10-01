// End-to-end smoke test for the Studio configurator: one panel, the summary
// bar, the Download sheet — walked as a customer would, asserting real state,
// not just "the page didn't crash". Per MASTER_SCOPE.md
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
import { startStudio, typeText, pickGarment, pickTemplate, openDownload, closeDownload } from "./helpers.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Same fixture digitize-stale-edits.spec.js uses (see that file's own
// comment for why it's a checked-in real PNG, not an inlined base64 copy).
// It's just raster art to ImagePanel -- no digitizer service involved here.
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");

// ---- shared helpers -------------------------------------------------------

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
  // The Download sheet is itself a dialog and stays open beneath the confirm,
  // so the confirm is picked out by its own title, not as "the" dialog.
  const dialog = page.getByRole("dialog", { name: /This design is bigger than/ });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Exceeds your 8×8 in hoop");
  await page.getByRole("button", { name: `Download ${fmt} anyway`, exact: true }).click();
}

// The caption groups thousands (`toLocaleString`) since 2026-09-07 — it was
// the one stitch count in the app printing a bare 1289 where QualityReport,
// DigitizePanel, DesignPanel and the review summary all say 1,289. Every
// `[\d,]+` in this file's caption matchers is that, not a loosened assertion.
//
// Picks the garment, types the text, opens the Download sheet. Callers vary
// garmentLabel/text; what the sheet reflects is asserted by each caller since
// that's the point being tested.
async function reachDownloadWithText(page, garmentLabel, text) {
  await startStudio(page);
  await pickGarment(page, garmentLabel);
  await typeText(page, text);
  await openDownload(page);
}

test("configurator: text -> download sheet -> DST", async ({ page }) => {
  await startStudio(page);

  // ---- Garment ----------------------------------------------------------
  await pickGarment(page, "Tote");

  // ---- Content ----------------------------------------------------------
  // Real content produced real stitches on the field -- typeText asserts the
  // input took the value and the field's stats readout reports a count.
  await typeText(page, "EMB TEST");

  // ---- Download sheet -----------------------------------------------------
  await openDownload(page);
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  // The recap must reflect what was actually picked/typed, not just render a
  // static template -- this is exactly the kind of state handoff a regression
  // could silently break.
  const summary = page.locator(".sheet dl.summary");
  await expect(summary).toContainText("Tote");
  await expect(summary).toContainText('Text — "EMB TEST"');
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

  await expect(page.getByText("Saved DST")).toBeVisible();
});

// ---- Axis 1: other garment types ------------------------------------------
// The original happy path only ever picks Tote. Two more garments (a small
// non-square one and the largest one in the list) confirm the garment tile
// -> review-step handoff generalizes, not just for the one size the happy
// path exercises. "Flow completes" here means reaching the Download step
// with a real thread list -- the actual download-and-verify-bytes work is
// axis 3's job, so these don't re-click a format button.
for (const garmentLabel of ["Hat Front", "Full Back"]) {
  test(`configurator: garment=${garmentLabel} completes and the sheet reflects it`, async ({ page }) => {
    await reachDownloadWithText(page, garmentLabel, "EMB TEST");

    // Real state handoff, not a static template: the recap names THIS garment
    // and THIS text, not whatever the last-tested garment was.
    await expect(page.locator(".sheet dl.summary")).toContainText(garmentLabel);
    await expect(page.locator(".sheet dl.summary")).toContainText('Text — "EMB TEST"');

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
test("configurator: image content path -> sheet reflects it -> download", async ({ page }) => {
  // Force the no-digitizer case: this spec is about the browser flatten lane,
  // which "+ Artwork" only routes to when the service is unreachable.
  await page.route("**/health", (r) => r.abort());
  await startStudio(page);
  await pickGarment(page, "Tote");

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
  await expect(page.getByRole("button", { name: "Download", exact: true })).toBeEnabled();

  // The element chip and the swatch strip are on ONE screen, inches apart,
  // and disagreed until 2026-09-08: the chip read `element.nColors` (the
  // slider) and said "Image · 4 colors" above a strip rendering two. Same
  // defect as the review card below, one step earlier. The strip is the
  // honest one — it is drawn from the flattened palette — so the chip is
  // asserted against it rather than against a literal.
  const swatches = await page.locator(".swatchwrap").count();
  expect(swatches, "the swatch strip rendered nothing to compare against").toBeGreaterThan(0);
  await expect(page.locator(".elsummary").filter({ hasText: /^Image · / }))
    .toHaveText(`Image · ${swatches} color${swatches === 1 ? "" : "s"}`);

  await openDownload(page);

  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  // The recap's image branch (App.svelte), not the text branch -- and the
  // real default settings (4 colors, background removed), not a static
  // placeholder.
  await expect(page.locator(".sheet dl.summary")).toContainText("Logo / image");
  await expect(page.locator(".sheet dl.summary")).toContainText("background removed");

  // The two rows that used to contradict each other, on one card. `Colors`
  // was `element.nColors` — the slider, a CEILING the customer asked for —
  // while `Thread changes` two rows down is counted from the design's own
  // {type:"color"} records. Measured 2026-09-08 on the shipped Logo-patch
  // starter: "Colors 4 · background removed" beside "Thread changes 1", i.e.
  // four colours claimed for a design that stops the machine once. Colours
  // are cones to buy and re-threads on a single-needle machine, so this is
  // the customer's money, not a tidiness point.
  //
  // Asserted as the RELATIONSHIP rather than as "2", so the guard survives a
  // change of fixture: N colour blocks means N-1 changes, whatever N is.
  //
  // SINGLE-ELEMENT only, and deliberately so — do not copy this line into a
  // mixed-design spec. `Colors` is scoped to ITS element while `Thread
  // changes` is the whole design, so a name beside this logo reads Colors 2
  // against Thread changes 2 (one text colour + two image colours = three
  // blocks) and both are right. Measured 2026-09-08. This project carries only
  // the artwork, because the starter's empty text element is not sewable and
  // `designSummary` lists only what sews.
  const summaryRow = async (label) => {
    const dd = page.locator(".sheet dl.summary div").filter({ has: page.locator(`dt:text-is("${label}")`) }).locator("dd");
    await expect(dd).toHaveCount(1);
    return (await dd.innerText()).trim();
  };
  const colors = parseInt(await summaryRow("Colors"), 10);
  const changes = parseInt(await summaryRow("Thread changes"), 10);
  expect(Number.isNaN(colors), "the Colors row is not a number").toBe(false);
  expect(Number.isNaN(changes), "the Thread changes row is not a number").toBe(false);
  expect(colors, `Colors ${colors} against ${changes} thread change(s) on the same card`)
    .toBe(changes + 1);

  await expect(page.locator(".threadlist .threadrow").first()).toBeVisible();

  // …and the same count further down the sheet, where the customer reads it as a
  // shopping list. `worksheet-digitized-lane.spec.js` guards this for the
  // DIGITIZED lane; the browser flatten lane had no equivalent, which is the
  // lane the Colors row was wrong on. One cone row per colour block.
  await expect(page.locator(".threadlist .threadrow"),
    `${colors} colours on the review card against the Download step's cone rows`)
    .toHaveCount(colors);

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
test("configurator: PES, EXP, and PDF worksheet exports produce real files", async ({ page }) => {
  await reachDownloadWithText(page, "Tote", "EMB TEST");

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
  await expect(page.getByText("Saved PES")).toBeVisible();

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
  await expect(page.getByText("Saved EXP")).toBeVisible();

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

// --- the panel starts at the top ------------------------------------------

// The panel scrolls, and its offset used to survive a change of scene: the
// customer scrolls down to pick a fabric colour (it sits below the fold), then
// opens another design and lands mid-panel with the top of the new design
// off-screen above them. There are no steps any more; opening a different
// design is the equivalent reset.
test("the panel scrolls to the top when a different design is opened", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");

  const panel = page.locator(".cfg-body");
  const scrollTop = () => panel.evaluate((el) => el.scrollTop);

  // The panel really is taller than its viewport — if it ever stops being,
  // this test would pass without exercising anything.
  const overflow = await panel.evaluate((el) => el.scrollHeight - el.clientHeight);
  expect(overflow).toBeGreaterThan(100);

  // Scroll the way someone picking a fabric colour has to.
  await panel.evaluate((el) => { el.scrollTop = el.scrollHeight; });
  expect(await scrollTop()).toBeGreaterThan(100);

  await page.getByRole("button", { name: /^My designs/ }).click();
  await page.getByRole("button", { name: "+ New design" }).click();
  await expect.poll(scrollTop).toBe(0);
});

// --- a template starts a NEW design ------------------------------------------

// Templates moved into My designs (2026-09-30), beside every saved design.
// Picking one there applied it IN PLACE, so the design the customer had open
// was silently overwritten. A template now starts a fresh design and the
// open one survives as its own row.
test("a template picked from My designs starts a new design and keeps the open one", async ({ page }) => {
  await startStudio(page);
  await typeText(page, "KEEP ME");

  const rows = page.locator(".drawer-row-name");
  await page.getByRole("button", { name: /^My designs/ }).click();
  await expect(rows).toHaveCount(1);

  await page.locator(".tcard", { hasText: "Left-chest name" }).click();
  await expect(page.getByRole("dialog", { name: "My designs" })).toHaveCount(0);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: /^My designs/ }).click();
  await expect(rows).toHaveCount(2);
  await expect(rows.filter({ hasText: /^KEEP ME$/ })).toHaveCount(1);
});

// --- the Download sheet and browser history ----------------------------------

// The sheet pushes one history entry so a phone's Back closes it (spec §2.4).
// Pinned here: Back closes it without leaving the Studio; Close pops the entry
// it pushed (no dead Back left behind); and a reload with the sheet open
// normalises the stale entry away so the next open still closes in one press.
test("the Download sheet's history entry: Back closes it, Close and reload leave none behind", async ({ page }) => {
  await startStudio(page);
  await typeText(page, "BACK TEST");

  await openDownload(page);
  await page.goBack();
  await expect(page.getByRole("dialog", { name: "Download" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Your design" })).toBeVisible();

  await openDownload(page);
  // Modal: the panel underneath is inert while the sheet covers it...
  await expect(page.locator(".panel-main")).toHaveAttribute("inert", "");
  await closeDownload(page);
  await expect.poll(() => page.evaluate(() => window.history.state)).toBeNull();
  // ...and on close focus returns to the control that opened it.
  await expect(page.locator(".panel-main")).not.toHaveAttribute("inert");
  await expect(page.locator(".summarybar-download")).toBeFocused();

  await openDownload(page);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Your design" })).toBeVisible();
  await expect(page.getByRole("dialog", { name: "Download" })).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.history.state)).toBeNull();

  // At phone width the sheet is full height below the topbar (spec §2.4),
  // not clipped to the short panel row it is mounted in.
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
  const phoneSheet = await openDownload(page);
  const box = await phoneSheet.boundingBox();
  const topbarH = await page.locator(".topbar").evaluate((el) => el.getBoundingClientRect().height);
  expect(Math.round(box.y)).toBe(Math.round(topbarH));
  expect(Math.round(box.y + box.height)).toBe(844);
  expect(Math.round(box.width)).toBe(390);
  await closeDownload(page);
  await page.setViewportSize({ width: 1280, height: 720 });

  // One Escape is enough after the reload: no second entry was stacked.
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
  await openDownload(page);
  await closeDownload(page);
  await expect.poll(() => page.evaluate(() => window.history.state)).toBeNull();
});

// The Download button on a design with nothing in it, which nothing had ever
// driven: every test above types text or uploads art first. A brand-new
// project holds one empty text element.
//
// Until 2026-09-07 the review screen read "Ready to stitch" over a summary
// saying `Text — ""`. The summary bar now refuses up front: the button is
// disabled, with its reason in the title. (The "Nothing to stitch yet" sheet
// branch is unit-tested and unreachable from the bar.) This drives the
// transition in both directions, because a button that is merely pessimistic
// would be its own bug.
test("the Download button does not claim readiness for a design with nothing in it", async ({ page }) => {
  await startStudio(page);

  const download = page.getByRole("button", { name: "Download", exact: true });
  await expect(download).toBeDisabled();
  await expect(download).toHaveAttribute("title", "Add text or a logo first");

  // Now give it something to sew and watch the same button change its mind.
  await typeText(page, "HELLO");
  await openDownload(page);
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nothing to stitch yet" })).toHaveCount(0);
  await expect(page.locator(".sheet dl.summary")).toContainText('Text — "HELLO"');
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
  await startStudio(page);

  await pickGarment(page, "Tote");
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

  // Straight after the reload, with nothing opened: the embroidery field is
  // visible beside the panel, so restoring only in a sheet would leave this
  // empty and read as lost work.
  await expect(caption).toHaveText(before, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Your design" })).toBeVisible();

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
  await openDownload(page);
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nothing to stitch yet" })).toHaveCount(0);
  await expect(page.locator(".sheet dl.summary")).toContainText("Logo / image");
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
  await startStudio(page);
  await pickGarment(page, "Left Chest");

  await typeText(page, "FRITSCH'S");

  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator("input[type=file]").first().setInputFiles(ART_PNG);
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });

  await openDownload(page);
  const summary = page.locator(".sheet dl.summary");
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
  await startStudio(page);
  await pickTemplate(page, "Name on a hat");

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
  await startStudio(page);
  await pickGarment(page, "Left Chest");

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

test("every control in the configurator has an accessible name", async ({ page }) => {
  // Swept 2026-09-07 across all four wizard steps (now the configurator and
  // its Download sheet): exactly ONE control in the app was
  // unnamed (SizePanel's in/cm/mm select). Most are named implicitly by a
  // wrapping <label> — the four TextStep sliders read "Letter spacing 0.0 mm",
  // "Curve 0°", "Rotation 0°", "Slant 0°" — which is easy to break by moving
  // an input out of its label while everything still LOOKS right.
  await startStudio(page);
  await pickTemplate(page, "Name on a hat");
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  expect(await unnamedControls(page), "configurator").toEqual([]);

  await page.getByRole("button", { name: "Artwork", exact: true }).click();
  expect(await unnamedControls(page), "configurator, artwork").toEqual([]);

  await openDownload(page);
  expect(await unnamedControls(page), "download sheet").toEqual([]);
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
  await expect(page.getByRole("heading", { name: "Your design" })).toBeVisible();
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
  await startStudio(page);
  await pickGarment(page, "Left Chest");
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
  await startStudio(page);
  await pickGarment(page, "Left Chest");
  await page.locator("textarea").first().fill("FRITSCH'S");
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  // Compared as the STRINGS on screen, not as numbers: "1,779" and "1779" are
  // the same count and were still two different things to read, side by side.
  // The unit was fixed 2026-09-07 and the grouping the same day, after this
  // very test passed on a screen showing both renderings at once.
  const captionText = (await page.locator("span.stats").innerText()).match(/([\d,]+) stitches/)[1];
  expect(Number(captionText.replace(/,/g, ""))).toBeGreaterThan(100);

  await page.getByRole("button", { name: "Stitch simulator" }).click();
  const counter = page.locator(".simcount");
  await expect(counter).toBeVisible();
  // The total is asserted immediately; the running number is left alone,
  // because it is mid-animation and racing it would be the flaky assertion.
  await expect(counter).toContainText(`/ ${captionText} stitches`);
  // …and it gets there. The design is short, so the default 1x run finishes
  // well inside this budget.
  await expect(counter).toHaveText(`${captionText} / ${captionText} stitches`, { timeout: 60_000 });
});

test("the review names what it costs to sew — on the lane the service never sees", async ({ page }) => {
  // An auto-digitized design gets these from the service (QualityReport). A
  // lettering, hand-drawn, shape or imported-DST design never reaches it, and
  // this screen showed the garment, the hoop, the content, the font — and not
  // one number about the sew-out.
  await startStudio(page);
  await pickGarment(page, "Left Chest");
  await page.locator("textarea").first().fill("FRITSCH'S");
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  const caption = await page.locator("span.stats").innerText();
  const stitches = caption.match(/([\d,]+) stitches/)[1];
  const size = caption.match(/(\d+)×(\d+) mm/);

  await openDownload(page);
  const summary = page.locator(".sheet dl.summary");
  // The same design, so the same numbers as the caption — this is the
  // assertion that catches the two drifting apart.
  await expect(summary).toContainText(`${size[1]} × ${size[2]} mm`);
  await expect(summary).toContainText(stitches);
  await expect(summary).toContainText("Trims");
  await expect(summary).toContainText(/\d+\.\d m \(estimate\)/);
  // No service report on this lane, so nothing can contradict it.
  await expect(page.locator("section.quality")).toHaveCount(0);
});

test("Original view swaps the thread for the uploaded artwork, and any edit swaps it back", async ({ page }) => {
  await page.route("**/health", (r) => r.abort());   // browser lane: an `image` element, no service
  await startStudio(page);
  const orig = page.getByRole("button", { name: "Original view" });
  // A text-only design has no artwork to show.
  await typeText(page, "ABC");
  await expect(orig).toBeDisabled();

  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator("input[type=file]").first().setInputFiles(ART_PNG);
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  await expect(orig).toBeEnabled();

  const shot = () => page.evaluate(() => document.querySelector(".hoop canvas").toDataURL());
  // The fixture is white, one black square and one (204, 0, 0) red square.
  // Shaded thread never lands on that exact red over a large area; the
  // uploaded PNG drawn back onto the canvas does. A bare "the canvas changed"
  // is not enough: hiding the selection chrome alone changes it.
  const artworkRed = () => page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let n = 0;
    for (let i = 0; i < d.length; i += 4) {
      if (Math.abs(d[i] - 204) <= 2 && d[i + 1] <= 2 && d[i + 2] <= 2) n++;
    }
    return n;
  });
  const stitched = await shot();
  const stitchedRed = await artworkRed();

  await orig.click();
  await expect(orig).toHaveAttribute("aria-pressed", "true");
  await expect.poll(shot).not.toBe(stitched);
  // Measured 2026-09-30: 0 such pixels stitched, 420 in Original view.
  await expect.poll(artworkRed).toBeGreaterThan(Math.max(100, stitchedRed * 5));
  // No chrome was added over the canvas to do it.
  expect(await page.locator(".hoop > *").count()).toBe(1);

  await page.getByRole("button", { name: "Realistic view" }).click();
  await expect(orig).toHaveAttribute("aria-pressed", "false");
  await expect.poll(shot).toBe(stitched);
});
