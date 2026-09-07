// The "Design file" lane, end to end — the third tile on the Content step and
// the one with no e2e coverage at all until now.
//
// What it guards is a defect that shipped: EMB-Bot's DST codec disagrees with
// the Tajima standard, and the import lane used to read third-party files with
// the EMB-Bot-convention reader. That was measured as a width/height swap and
// then written down as "a quarter turn" — the Studio told customers to use
// Rotate. Looking at the canvas on 2026-09-07 showed it was a MIRROR: the
// letters came in backwards, and no rotation repairs that. PES, EXP and JEF
// then exported the mirrored design faithfully.
//
// A unit test cannot catch that class of thing. The bytes were right, the
// counts were right, the bbox was "right" up to a swap, and every test passed.
// So this spec drives the real upload and asserts the SIZE the panel and the
// canvas report — the one number that differs between the two conventions.
//
// Fixture: test/fixtures/standard-tajima.dst, 40 x 10 mm, written by pystitch
// (digitizer/tools/make_standard_dst_fixture.py) so no EMB-Bot encoder is in
// the loop. Referenced across the repo rather than copied into e2e/fixtures:
// one file, one regeneration path, no chance of the two drifting.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STANDARD_DST = path.resolve(__dirname, "../../test/fixtures/standard-tajima.dst");

async function importFixture(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Design file" }).click();
  await page.locator(".dp-upload input[type=file]").setInputFiles(STANDARD_DST);
  await expect(page.locator(".dp-stats")).toBeVisible({ timeout: 60_000 });
}

test("an imported .dst reports the size its own writer meant", async ({ page }) => {
  await importFixture(page);

  // 40x10, not 10x40. Landscape stays landscape.
  await expect(page.locator(".dp-stats")).toContainText("40×10 mm");
  // And the canvas caption agrees. `.stats` specifically, not the first
  // element on the page matching the string: the panel decodes for DISPLAY
  // (DesignPanel's decodeSafe) while generate.js decodes for STITCHES, two
  // separate reads of one file, and a loose locator would match the panel
  // line twice and never look at the canvas at all. It did, in the first
  // draft of this test — the mutation that reverts generate.js to decodeDST
  // passed it.
  await expect(page.locator("span.stats")).toContainText("40×10 mm");
});

test("the panel does not tell anyone to rotate an import straight", async ({ page }) => {
  // Rotation cannot undo a mirror. The old advice sent a customer away
  // believing a backwards design was fixed, which is worse than silence.
  await importFixture(page);

  await expect(page.getByTestId("dst-import-orientation-note")).toHaveCount(0);
  await expect(page.getByText(/stand it up/i)).toHaveCount(0);
});

test("the case that is still wrong — EMB-Bot's own .dst — is named", async ({ page }) => {
  await importFixture(page);

  const note = page.getByTestId("dst-own-file-note");
  await expect(note).toBeVisible();
  await expect(note).toContainText(/mirrored/i);
  await expect(note).toContainText("My designs");
});

test("an imported design reaches Download and exports", async ({ page }) => {
  // The lane end to end. DST is what the browser encoder writes for a project
  // like this; that it is the encoder with the known axis bug is the subject
  // of DownloadStep's own note, not of this assertion — here the point is only
  // that an imported file becomes a real machine file at all.
  await importFixture(page);
  await page.getByRole("button", { name: "4 Download", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();

  const dl = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const anyway = page.getByRole("button", { name: "Download DST anyway", exact: true });
  if (await anyway.isVisible().catch(() => false)) await anyway.click();
  const d = await dl;
  expect(d.suggestedFilename()).toBe("design.dst");
});

test("the DST note's premise fits a project with no lettering in it", async ({ page }) => {
  // It read "this project includes lettering or hand-drawn shapes" while
  // firing on the gate !isPurelyDigitized — which an import-only project also
  // trips. The note opened on a claim about the customer's own project that
  // was not true.
  await importFixture(page);
  await page.getByRole("button", { name: "4 Download", exact: true }).click();

  const note = page.getByTestId("dst-browser-encoder-note");
  await expect(note).toBeVisible();
  await expect(note).toContainText("imported design file");
});
