// The starter design pack in the real Studio (PRODUCT.md launch item 3):
// browse the twelve designs, add one to the open design, and take it all the
// way to a machine file.
//
// EVERY request to the digitizer service is refused here, on purpose. The
// pack is static files and DST import is browser-side, so a customer whose
// service is not running must still be able to start from a starter design --
// this file is the standing proof, and it runs the same on a machine that has
// the service up.
import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { startStudio, typeText, openDownload } from "./helpers.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PACK = path.resolve(__dirname, "../public/starter");
const manifest = JSON.parse(readFileSync(path.join(PACK, "manifest.json"), "utf8"));
// The engine's own standard-DST reader, for reading an exported file back.
const { decodeDSTStandard } = createRequire(import.meta.url)(path.resolve(__dirname, "../../src/dstimport.js"));

const HEART = manifest.designs.find((d) => d.id === "heart");
const heartStats = `${HEART.stitches.toLocaleString("en-US")} stitches`;

const picker = (page) => page.getByRole("dialog", { name: "Starter designs" });
const opener = (page) => page.getByRole("group", { name: "Start with" }).getByRole("button", { name: "Starter designs" });
const rows = (page) => page.locator(".elrow");
const undo = (page) => page.getByRole("button", { name: "Undo" });
const redo = (page) => page.getByRole("button", { name: "Redo" });

// Requests the page made to the digitizer service; all of them are aborted.
async function serviceDown(page) {
  const asked = [];
  await page.route("http://127.0.0.1:8721/**", (route) => {
    asked.push(new URL(route.request().url()).pathname);
    return route.abort();
  });
  return asked;
}

async function addStarter(page, title) {
  await opener(page).click();
  await expect(picker(page)).toBeVisible();
  await picker(page).getByRole("button", { name: "Add " + title, exact: true }).click();
  await expect(picker(page)).toHaveCount(0);
}

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
});

test("the picker lists all twelve designs with their art, name and provenance, and no grades", async ({ page }) => {
  await serviceDown(page);
  await startStudio(page);
  await opener(page).click();
  const dlg = picker(page);
  await expect(dlg.locator(".sp-card")).toHaveCount(12);

  for (const d of manifest.designs) {
    const card = dlg.locator(`[data-starter="${d.id}"]`);
    await expect(card.locator(".sp-title")).toHaveText(d.title);
    await expect(card.locator(".sp-credit")).toContainText(`Art by ${d.author} · ${d.license}`);
    await expect(card.getByRole("link", { name: "Source of " + d.title })).toHaveAttribute("href", d.source_page_url);
    // The thumbnail is the pack's own art, and it really drew.
    const img = card.locator("img");
    await img.scrollIntoViewIfNeeded();
    await expect(img).toHaveAttribute("src", "starter/" + d.art);
    await expect.poll(() => img.evaluate((el) => el.complete && el.naturalWidth > 0)).toBe(true);
  }
  // Nothing about the pack reads as a verdict or a warning.
  await expect(dlg).not.toContainText(/preflight|grade|score|warning/i);
  await expect(dlg.locator(".warn, [role=alert]")).toHaveCount(0);
});

test("a starter design goes from the picker to an exported DST with the service down", async ({ page }) => {
  const asked = await serviceDown(page);
  await startStudio(page);
  await addStarter(page, "Heart");

  // It replaced the untouched blank text box, and it is the pack's file: the
  // manifest's stitch count, size and colour count, on the panel AND the canvas.
  await expect(rows(page)).toHaveCount(1);
  await expect(rows(page)).toContainText("File · Heart");
  const size = `${Math.round(HEART.width_mm)}×${Math.round(HEART.height_mm)} mm`;
  await expect(page.locator(".dp-stats")).toContainText(`Heart — ${heartStats} · ${size} · ${HEART.colors} colors`, { timeout: 60_000 });
  await expect(page.locator("span.stats")).toContainText(`${heartStats} · ${size}`);
  await expect(page.getByLabel("Project name")).toHaveValue("Heart");

  // Thread colours came with it (a DST has none): block 1 is the heart's red,
  // not the import lane's placeholder dark grey.
  await expect(page.locator(".dp-block")).toHaveCount(HEART.colors);
  await expect(page.locator(".dp-block").first().locator(".tp-swatch")).toHaveCSS("background-color", "rgb(230, 0, 0)");

  // No warning on the canvas caption or the panel.
  await expect(page.locator(".warn:visible")).toHaveCount(0);

  // Export it. The browser encoder writes the DST; read it back with the
  // engine's standard reader and compare with the pack's own file.
  await openDownload(page);
  const dl = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const anyway = page.getByRole("button", { name: "Download DST anyway", exact: true });
  if (await anyway.isVisible().catch(() => false)) await anyway.click();
  const file = await dl;
  expect(file.suggestedFilename()).toBe("heart.dst");
  const out = decodeDSTStandard(new Uint8Array(readFileSync(await file.path())));
  const src = decodeDSTStandard(new Uint8Array(readFileSync(path.join(PACK, HEART.dst))));
  expect(out.colorCount).toBe(src.colorCount);
  expect(out.stitchCount).toBe(src.stitchCount);
  expect(Math.abs(out.widthMM - src.widthMM)).toBeLessThanOrEqual(0.2);
  expect(Math.abs(out.heightMM - src.heightMM)).toBeLessThanOrEqual(0.2);

  // The service was never needed: the only things the page asked it were its
  // standing "are you there" probes, and every one was refused.
  expect(asked.filter((p) => p !== "/health" && p !== "/fonts/outline")).toEqual([]);
});

test("adding a starter design is one undo step, and leaves existing work alone", async ({ page }) => {
  await serviceDown(page);
  await startStudio(page);

  // On a fresh design: one Undo brings the blank text box back, Redo the heart.
  await addStarter(page, "Heart");
  await expect(rows(page)).toContainText("File · Heart");
  await expect(undo(page)).toBeEnabled();
  await undo(page).click();
  await expect(rows(page)).toHaveCount(1);
  await expect(rows(page)).toContainText("Text · empty");
  await expect(undo(page)).toBeDisabled();
  await redo(page).click();
  await expect(rows(page)).toContainText("File · Heart");
  await undo(page).click();

  // Beside typed text: the design is added as a second element, and one Undo
  // removes it without touching the text.
  await typeText(page, "TEAM");
  await addStarter(page, "Baseball");
  await expect(rows(page)).toHaveCount(2);
  await expect(rows(page).nth(1)).toContainText("File · Baseball");
  await undo(page).click();
  await expect(rows(page)).toHaveCount(1);
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue("TEAM");
});

test("a starter design survives a reload, an .embproj export and an import elsewhere", async ({ page }) => {
  await serviceDown(page);
  await startStudio(page);
  await addStarter(page, "Heart");
  await expect(page.locator("span.stats")).toContainText(heartStats, { timeout: 60_000 });

  await page.reload();
  await expect(rows(page)).toContainText("File · Heart");
  await expect(page.locator("span.stats")).toContainText(heartStats, { timeout: 60_000 });

  await page.getByRole("button", { name: /^My designs/ }).click();
  const [dl] = await Promise.all([
    page.waitForEvent("download"),
    page.locator(".drawer-row.current").getByRole("button", { name: "Export" }).click(),
  ]);
  const text = readFileSync(await dl.path(), "utf8");
  const saved = JSON.parse(text).project.elements;
  expect(saved).toHaveLength(1);
  expect(saved[0].type).toBe("design");
  expect(saved[0].name).toBe("Heart");
  expect(Buffer.from(saved[0].dstBase64, "base64").equals(readFileSync(path.join(PACK, HEART.dst)))).toBe(true);

  // "Another machine": an empty browser, then the file.
  await page.evaluate(() => localStorage.clear());
  await page.goto("/");
  await expect(rows(page)).toContainText("Text · empty");
  await page.getByRole("button", { name: /^My designs/ }).click();
  await page
    .getByLabel("Import design file")
    .setInputFiles({ name: dl.suggestedFilename(), mimeType: "application/json", buffer: Buffer.from(text, "utf8") });
  await expect(page.locator(".drawer")).toHaveCount(0);
  await expect(rows(page)).toContainText("File · Heart");
  await expect(page.locator("span.stats")).toContainText(heartStats, { timeout: 60_000 });
  await expect(page.locator(".dp-block")).toHaveCount(HEART.colors);
});

test("the picker is a dialog: focus moves in, Escape closes it, focus returns to its button", async ({ page }) => {
  await serviceDown(page);
  await startStudio(page);
  await opener(page).click();
  await expect(picker(page)).toBeVisible();
  await expect(picker(page).locator(".sp-card")).toHaveCount(12);
  const inside = () => page.evaluate(() => !!document.activeElement.closest('[role="dialog"][aria-label="Starter designs"]'));
  expect(await inside()).toBe(true);
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press("Tab");
    expect(await inside(), `Tab ${i} stays in the picker`).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(picker(page)).toHaveCount(0);
  await expect(opener(page)).toBeFocused();
  // Closing without picking changed nothing.
  await expect(rows(page)).toContainText("Text · empty");
  await expect(undo(page)).toBeDisabled();
});
