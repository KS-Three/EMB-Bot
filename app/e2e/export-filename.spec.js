// A downloaded machine file is named after the design, not "design.*".
// Three DST/PES/EXP files for three designs used to land in Downloads as
// design.dst, design (1).dst, ... and the customer could not tell them apart.
// Only the real app puts the name field, the Download step and the browser's
// suggested filename in one place; the slug rule itself is pinned in
// src/lib/exporters.spec.js.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, typeText, openDownload } from "./helpers.js";

async function confirmOversize(page, label) {
  const anyway = page.getByRole("button", { name: `Download ${label} anyway`, exact: true });
  if (await anyway.isVisible().catch(() => false)) await anyway.click();
}

test("DST, PES and EXP downloads are named after the design, sanitised", async ({ page }) => {
  await startStudio(page);
  await pickGarment(page, "Tote");
  await typeText(page, "EMB TEST");
  await openDownload(page);

  for (const [label, ext] of [["DST", "dst"], ["PES", "pes"], ["EXP", "exp"]]) {
    const dl = page.waitForEvent("download");
    await page.getByRole("button", { name: label, exact: true }).click();
    await confirmOversize(page, label);
    expect((await dl).suggestedFilename()).toBe(`emb-test.${ext}`);
  }
});

test("a name full of odd characters becomes a safe filename", async ({ page }) => {
  await startStudio(page);
  await pickGarment(page, "Tote");
  await typeText(page, "Fritsch's Stitches: Hat #2");
  await openDownload(page);

  const dl = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  await confirmOversize(page, "DST");
  expect((await dl).suggestedFilename()).toBe("fritsch-s-stitches-hat-2.dst");
});
