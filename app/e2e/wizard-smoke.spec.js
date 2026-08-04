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
import { test, expect } from "@playwright/test";

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
