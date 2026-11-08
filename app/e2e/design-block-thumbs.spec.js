// Block thumbnails in the Design panel, measured on a real 22k-stitch design.
//
// The fixture is the repo's own synthetic contrast-palette.png, run through the
// browser engine (service down) and exported as a DST, then imported through
// the "Design file" lane -- so the panel reads exactly what a customer's file
// gives it, with no encoder or decoder stubbed.
//
// Three claims, each measured in the page:
//   1. one thumbnail per colour block, with the block's own stitch count;
//   2. each thumbnail draws ink only inside its block's bbox + 1 mm
//      (blockThumbs.js read with the silhouette and tile OFF, so what is left
//      is the block layer alone);
//   3. building all of them takes <= 150 ms (median of 9), and the row is
//      exactly as tall with a thumbnail as without.
import { test, expect } from "@playwright/test";
import { startStudio, openAdvanced, openDownload, uploadArtwork, pickGarment } from "./helpers.js";

// Towel (152 mm box) auto-fits this fixture to ~30.8k stitches: the 22,533-stitch
// class the brief names and then some, so the 150 ms bar is met with room for the
// bigger file, not just the smaller one.
const GARMENT = "Towel";
const MIN_STITCHES = 22_533;

async function exportDst(browser) {
  const ctx = await browser.newContext({ baseURL: test.info().project.use.baseURL, viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.route("**/health", (r) => r.abort());
  await startStudio(page);
  await pickGarment(page, GARMENT);
  await uploadArtwork(page, "e2e/fixtures/contrast-palette.png", { run: false, engine: "browser" });
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 90_000 });
  await page.waitForTimeout(4000);
  console.log("field caption:", await page.getByText(/^[\d,]+ stitches/).textContent());
  await openDownload(page);
  const dl = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const buf = await (await dl).createReadStream().then(
    (s) => new Promise((res, rej) => { const c = []; s.on("data", (d) => c.push(d)); s.on("end", () => res(Buffer.concat(c))); s.on("error", rej); }),
  );
  await ctx.close();
  return buf;
}

test("every colour block gets a thumbnail inside its bbox, fast, without changing the row", async ({ browser, page }) => {
  test.setTimeout(240_000);
  const dst = await exportDst(browser);

  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await openAdvanced(page);
  await page.getByRole("button", { name: "Design file" }).click();
  await page.locator(".dp-upload input[type=file]").setInputFiles({ name: "contrast-palette.dst", mimeType: "application/octet-stream", buffer: dst });
  await expect(page.locator(".dp-stats")).toBeVisible({ timeout: 60_000 });

  const rows = page.locator(".dp-block");
  const n = await rows.count();
  expect(n).toBeGreaterThan(1);
  // 1. one canvas per block; counts add up to the design's.
  await expect(page.locator(".dp-thumb canvas")).toHaveCount(n, { timeout: 30_000 });
  const counts = await page.locator(".dp-block-st").allTextContents();
  const total = counts.reduce((a, t) => a + parseInt(t.replace(/[^\d]/g, ""), 10), 0);
  const statText = await page.locator(".dp-stats").textContent();
  expect(statText).toContain(total.toLocaleString("en-US"));
  console.log("blocks", n, "stitches", total);
  expect(total).toBeGreaterThanOrEqual(MIN_STITCHES);

  // 3b. row height: with the thumbnail vs the thumbnail taken out of flow.
  const heights = await page.evaluate(() => {
    const rows = [...document.querySelectorAll(".dp-block")];
    const withThumb = rows.map((r) => r.getBoundingClientRect().height);
    for (const r of rows) r.querySelector(".dp-thumb").style.display = "none";
    const without = rows.map((r) => r.getBoundingClientRect().height);
    for (const r of rows) r.querySelector(".dp-thumb").style.display = "";
    return { withThumb, without };
  });
  console.log("row heights", JSON.stringify(heights));
  expect(heights.withThumb).toEqual(heights.without);

  // 2 + 3a. ink inside bbox + 1 mm, and the build time, on the decoded design.
  const res = await page.evaluate(async (b64) => {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const design = window.EMB.decodeDSTStandard(bytes);
    const mod = await import("/src/lib/blockThumbs.js");
    const colors = [];
    for (let i = 0; i < design.colorCount; i++) colors.push(window.EMB.IMPORT_BLOCK_COLORS[i % window.EMB.IMPORT_BLOCK_COLORS.length]);
    const W = 56, H = 28, dpr = 2;

    const times = [];
    for (let k = 0; k < 9; k++) {
      const t0 = performance.now();
      const th = mod.buildBlockThumbs(design, { colors, width: W, height: H, dpr });
      // A canvas queues its drawing until something reads it; the clock must
      // include the rasterizing, so every thumbnail is read back before it stops.
      for (const t of th) t.canvas.getContext("2d").getImageData(0, 0, 1, 1);
      times.push(performance.now() - t0);
      if (k === 8) var last = th;
    }
    times.sort((a, b) => a - b);

    // Block layer alone -> alpha > 0 is ink. Geometry replays the lib's fit.
    const bare = mod.buildBlockThumbs(design, { colors, width: W, height: H, dpr, silhouette: false, background: false });
    const blocks = mod.splitBlocks(design);
    let ext = { x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9 };
    for (const b of blocks) if (b.bbox) { ext.x0 = Math.min(ext.x0, b.bbox.x0); ext.x1 = Math.max(ext.x1, b.bbox.x1); ext.y0 = Math.min(ext.y0, b.bbox.y0); ext.y1 = Math.max(ext.y1, b.bbox.y1); }
    const bw = W * dpr, bh = H * dpr, pad = 3 * dpr;
    const s = Math.min((bw - 2 * pad) / Math.max(1, ext.x1 - ext.x0), (bh - 2 * pad) / Math.max(1, ext.y1 - ext.y0));
    const cx = (ext.x0 + ext.x1) / 2, cy = (ext.y0 + ext.y1) / 2;
    const SX = (x) => bw / 2 + (x - cx) * s, SY = (y) => bh / 2 - (y - cy) * s;
    const out = [];
    for (let i = 0; i < bare.length; i++) {
      const b = blocks[i], t = bare[i];
      if (!b.bbox) { out.push({ i, ink: 0, outside: 0 }); continue; }
      const data = t.canvas.getContext("2d").getImageData(0, 0, bw, bh).data;
      const m = 10; // 1 mm in DST units
      const rx0 = Math.floor(SX(b.bbox.x0 - m)), rx1 = Math.ceil(SX(b.bbox.x1 + m));
      const ry0 = Math.floor(SY(b.bbox.y1 + m)), ry1 = Math.ceil(SY(b.bbox.y0 - m));
      let ink = 0, outside = 0;
      for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
        if (data[(y * bw + x) * 4 + 3] === 0) continue;
        ink++;
        if (x < rx0 || x >= rx1 || y < ry0 || y >= ry1) outside++;
      }
      out.push({ i, ink, outside, bboxMm: t.bboxMm });
    }
    return { median: times[4], times, out, count: last.length, decodedBlocks: design.colorCount };
  }, dst.toString("base64"));
  console.log("build ms median", res.median.toFixed(1), "all", res.times.map((t) => t.toFixed(0)).join(","));
  console.log(JSON.stringify(res.out));
  expect(res.count).toBe(res.decodedBlocks);
  for (const r of res.out) { expect(r.ink, `block ${r.i} has ink`).toBeGreaterThan(0); expect(r.outside, `block ${r.i} ink outside bbox+1mm`).toBe(0); }
  expect(res.median).toBeLessThanOrEqual(150);
});
