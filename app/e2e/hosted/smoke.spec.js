// The hosted build, in a real browser, with no digitizer service running.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { statSync } from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// The same flat two-squares fixture wizard-smoke.spec.js's own image-content
// path test uses -- reused rather than adding a new fixture. Flat art, no
// digitizer service involved, so it exercises exactly the browser
// flatten-and-sew lane a hosted build falls back to.
const ART_PNG = path.join(__dirname, "..", "fixtures", "two-squares.png");

// Nothing may reach for the localhost service from a hosted build. This is the
// assertion Task 1's unit test makes, re-made against the shipped bundle —
// where an accidental static import or a second call site would still fire it.
test("no request is made to the digitizer service", async ({ page }) => {
  const attempts = [];
  page.on("request", (r) => {
    if (r.url().includes("8721")) attempts.push(r.url());
  });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  expect(attempts).toEqual([]);
});

// The app has to actually boot from a relative-base build served at root.
//
// The brief's original version of this test checked for the "Text" button
// right after `page.goto("/")`, but that button lives on the CONTENT step
// (ContentStep.svelte's "+ Text" tile, App.svelte's addelement("text")) — the
// first screen is the garment step ("What are you putting this on?"). Reached
// wizard-smoke.spec.js's happy path (garment -> Next) to get there for real,
// same as every other e2e spec in this repo does.
test("the Studio loads and reaches the content step", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Text", exact: true })).toBeVisible({ timeout: 15_000 });
  expect(errors).toEqual([]);
});

// The whole point: a hosted build, with no service anywhere, still hands a
// customer a real stitch file. Navigation and download interception are
// lifted verbatim from e2e/wizard-smoke.spec.js's original happy path
// ("guided wizard: garment -> content -> review -> download") — Tote is the
// garment that test uses, and a Tote's auto-fit text design exceeds its own
// 8x8 in hoop by construction (placement box 203.2 mm vs hoop 200 mm), so the
// DST export requires the same one-click "Download DST anyway" confirm that
// test's confirmOversizeExport() helper handles. If that spec's navigation
// changes, change this with it.
test("text lane reaches a downloadable DST", async ({ page }) => {
  await page.goto("/");

  // ---- Garment -----------------------------------------------------------
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  const toteTile = page.getByRole("button", { name: "Tote", exact: true });
  await toteTile.click();
  await expect(toteTile).toHaveClass(/\bsel\b/);
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Content (text) ------------------------------------------------------
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  const textInput = page.getByPlaceholder("Type a name or word");
  await textInput.fill("EMB TEST");
  await expect(textInput).toHaveValue("EMB TEST");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await expect(page.locator(".topbar-download")).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Review --------------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Download --------------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();

  // Tote's oversize confirm — see confirmOversizeExport() in wizard-smoke.spec.js.
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Exceeds your 8×8 in hoop");
  await page.getByRole("button", { name: "Download DST anyway", exact: true }).click();

  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.dst$/i);
  // The filename check alone would pass on a zero-byte or corrupt download --
  // this is the test the plan itself calls the proof a customer gets a real
  // file, so it needs to check the file, not just its name. Same threshold
  // wizard-smoke.spec.js's own DST download check uses.
  const dstPath = await download.path();
  expect(dstPath).toBeTruthy();
  expect(statSync(dstPath).size).toBeGreaterThan(512);
});

// On a hosted build the service can never appear, so "start it" is advice
// nobody can follow and the recheck button is a dead affordance. The note has
// to describe what the web app actually does.
test("the digitize note describes the browser lane, not a missing service", async ({ page }) => {
  await page.goto("/");

  // Navigate to the content step
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // Verify the digitize note
  const note = page.locator(".digitize-offline");
  await expect(note).toBeVisible({ timeout: 15_000 });
  await expect(note).toContainText("in your browser");
  await expect(note).not.toContainText("Start it");
  await expect(page.locator(".digitize-recheck")).toHaveCount(0);
});

// JEF/XXX/VP3 are service-only (exporters.js:97) and no browser encoder
// exists, so a hosted build can never write them. Kent's ruling: keep the
// buttons visible and disabled, but stop telling people to start something
// they cannot start.
test("service-only formats are disabled with a reason a hosted user can act on", async ({ page }) => {
  await page.goto("/");

  // Walk to the download step the same way wizard-smoke.spec.js does; if that
  // navigation differs, copy it from there rather than weakening this test.
  // ---- Garment -----------------------------------------------------------
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  const toteTile = page.getByRole("button", { name: "Tote", exact: true });
  await toteTile.click();
  await expect(toteTile).toHaveClass(/\bsel\b/);
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Content (text) ------------------------------------------------------
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  const textInput = page.getByPlaceholder("Type a name or word");
  await textInput.fill("EMB TEST");
  await expect(textInput).toHaveValue("EMB TEST");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await expect(page.locator(".topbar-download")).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Review --------------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Download --------------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();

  for (const label of ["JEF", "XXX", "VP3"]) {
    const btn = page.getByRole("button", { name: new RegExp(label) });
    await expect(btn).toBeVisible();
    await expect(btn).toBeDisabled();
    const title = await btn.getAttribute("title");
    expect(title).toContain("desktop version");
    expect(title).not.toContain("digitizer service running");
  }
});

// The text lane above proves the wizard works on a hosted build, but text is
// not the lane VITE_HOSTED actually changes -- the ARTWORK/image lane is.
// "+ Artwork" routes through resolveArtworkType (project.js), and on a
// hosted build digitizerHealth is always null (fetchHealth never fetches --
// see hosted.js and digitizer.js's own hosted-gate tests), so it always
// resolves to an "image" element: the browser's own flatten-and-sew lane
// (ImagePanel.svelte), never the "digitized" service lane. That fallback was
// never proven to reach a file on a hosted build before this test.
//
// Navigation and the upload fixture are lifted from wizard-smoke.spec.js's
// own image-content-path test ("guided wizard: image content path -> review
// reflects it -> download") -- same fixture, same selectors, same "no
// oversize confirm" expectation (the imported PNG does not fill the
// placement box the way auto-fit lettering does, so it fits Tote's 8x8 hoop
// and downloads in one click, unlike the text lane above).
test("artwork/image lane reaches a downloadable stitch file", async ({ page }) => {
  await page.goto("/");

  // ---- Garment -----------------------------------------------------------
  await expect(page.getByRole("heading", { name: "What are you putting this on?" })).toBeVisible();
  const toteTile = page.getByRole("button", { name: "Tote", exact: true });
  await toteTile.click();
  await expect(toteTile).toHaveClass(/\bsel\b/);
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Content (artwork -> image, no service to route to) -----------------
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork", exact: true }).click();

  await page.locator(".uploadbox input[type=file]").setInputFiles(ART_PNG);
  // Real processed state, not just "the input accepted a file": the panel's
  // flatten pipeline ran client-side and produced stitchable content.
  await expect(page.locator(".uploadbox .filename")).toHaveText("two-squares.png");
  await expect(page.locator(".flatprev")).not.toHaveClass(/hidden/);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await expect(page.locator(".topbar-download")).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Review --------------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await expect(page.locator("dl.summary")).toContainText("Logo / image");
  await page.getByRole("button", { name: "Next", exact: true }).click();

  // ---- Download --------------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toMatch(/\.dst$/i);
  const dstPath = await download.path();
  expect(dstPath).toBeTruthy();
  expect(statSync(dstPath).size).toBeGreaterThan(512);
});
