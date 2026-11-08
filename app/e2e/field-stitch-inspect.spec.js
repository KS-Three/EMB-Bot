// The field's stitch inspector (2026-11-08): with Inspect on, hovering the
// stitches shows a tooltip for the nearest stitch, and the number it gives is
// the number the simulator's counter shows for that stitch.
//
// Also pinned here, because the tooltip is the first thing that updates on
// EVERY hover move: it never repaints the field (the fillRect spy from
// field-hover-repaint.spec.js), it is not inside `.hoop`, and it takes no
// layout space (the canvas keeps its box while it shows).
//
// Browser lane only (a lettering template), so no digitizer service.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate } from "./helpers.js";

const FIELD = ".hoop canvas";
const TIP = "[data-testid=stitch-inspect]";

test.use({ contextOptions: { reducedMotion: "reduce" } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__fieldRenders = 0;
    const fill = CanvasRenderingContext2D.prototype.fillRect;
    CanvasRenderingContext2D.prototype.fillRect = function (x, y, w, h) {
      const c = this.canvas;
      if (x === 0 && y === 0 && c && c.closest && c.closest(".hoop") && w >= c.clientWidth - 1 && h >= c.clientHeight - 1) {
        window.__fieldRenders++;
      }
      return fill.apply(this, arguments);
    };
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
});

const settle = (page) => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 300)))));

// The first point of a grid over the canvas where the tooltip shows.
async function findStitch(page) {
  const box = await page.locator(FIELD).boundingBox();
  for (let j = 8; j < 56; j++) {
    for (let i = 8; i < 72; i++) {
      const pt = { x: box.x + (box.width * i) / 80, y: box.y + (box.height * j) / 64 };
      await page.mouse.move(pt.x, pt.y);
      if (await page.locator(TIP).count()) return pt;
    }
  }
  throw new Error("no stitch under any grid point");
}

test("Inspect: off by default, a tooltip on a stitch, nothing off the design, Escape turns it off", async ({ page }) => {
  const btn = page.getByRole("button", { name: "Inspect stitches" });
  await expect(btn).toHaveAttribute("aria-pressed", "false");
  const box = await page.locator(FIELD).boundingBox();
  // Off: hovering the middle of the design shows nothing.
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page.locator(TIP)).toHaveCount(0);

  await btn.click();
  await expect(btn).toHaveAttribute("aria-pressed", "true");
  const pt = await findStitch(page);
  const tip = page.locator(TIP);
  await expect(tip).toBeVisible();
  await expect(tip).toContainText(/Stitch [\d,]+ of [\d,]+/);
  await expect(tip).toContainText(/(Satin|Tatami|Run|Bean|Underlay|Stitch|Travel|Tie)( \([a-z ]+\))? · \d+\.\d mm/);
  await expect(tip).toContainText(/Thread \d+ of \d+/);

  // Outside `.hoop`, which still holds the canvas alone; and at the pointer.
  expect(await page.locator(".hoop > *").count()).toBe(1);
  expect(await page.locator(`.hoop ${TIP}`).count()).toBe(0);
  const tb = await tip.boundingBox();
  expect(Math.abs(tb.x - (pt.x + 14))).toBeLessThan(3);
  expect(Math.abs(tb.y - (pt.y + 14))).toBeLessThan(3);
  // No layout space: the canvas has the box it had before the tooltip.
  const after = await page.locator(FIELD).boundingBox();
  expect(after).toEqual(box);

  // The field's corner is far from any stitch: no tooltip there.
  await page.mouse.move(box.x + 4, box.y + 4);
  await expect(page.locator(TIP)).toHaveCount(0);
  // Back on the stitch, then leaving the canvas hides it.
  await page.mouse.move(pt.x, pt.y);
  await expect(page.locator(TIP)).toHaveCount(1);
  await page.mouse.move(box.x + box.width / 2, box.y - 40);
  await expect(page.locator(TIP)).toHaveCount(0);

  // Escape from the field turns Inspect off.
  await page.mouse.move(pt.x, pt.y);
  await expect(page.locator(TIP)).toHaveCount(1);
  await page.locator(FIELD).focus();
  await page.keyboard.press("Escape");
  await expect(btn).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator(TIP)).toHaveCount(0);
  await page.mouse.move(pt.x + 1, pt.y);
  await expect(page.locator(TIP)).toHaveCount(0);
});

test("Inspect: hovering never repaints the field, and the arrows still nudge", async ({ page }) => {
  await page.getByRole("button", { name: "Inspect stitches" }).click();
  const pt = await findStitch(page);
  await settle(page);
  await page.evaluate(() => { window.__fieldRenders = 0; });
  // Sixteen moves along the stitches, the tooltip updating on each.
  const seen = new Set();
  for (let i = 0; i < 16; i++) {
    await page.mouse.move(pt.x + (i % 4) * 2, pt.y + Math.floor(i / 4));
    if (await page.locator(TIP).count()) seen.add(await page.locator(TIP).getAttribute("data-strand"));
  }
  await settle(page);
  expect(seen.size).toBeGreaterThan(0);
  expect(await page.evaluate(() => window.__fieldRenders)).toBe(0);

  // The arrow nudge is the field's, Inspect or not: it moves the design
  // (one render) and the tooltip goes until the pointer moves again.
  await page.locator(FIELD).focus();
  await page.evaluate(() => { window.__fieldRenders = 0; });
  await page.keyboard.press("ArrowRight");
  await settle(page);
  expect(await page.evaluate(() => window.__fieldRenders)).toBeGreaterThan(0);
  await expect(page.locator(TIP)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Inspect stitches" })).toHaveAttribute("aria-pressed", "true");
});

test("Inspect: the stitch number agrees with the simulator's counter at that stitch", async ({ page }) => {
  await page.getByRole("button", { name: "Inspect stitches" }).click();
  const tip = page.locator(TIP);
  const box = await page.locator(FIELD).boundingBox();
  // Three different stitches: the first one found, then the first found
  // after skipping ahead along the grid.
  const reads = [];
  const rows = [16, 28, 40];
  for (const j of rows) {
    for (let i = 8; i < 72; i++) {
      await page.mouse.move(box.x + (box.width * i) / 80, box.y + (box.height * j) / 64);
      if (await tip.count()) {
        const text = (await tip.textContent()).replace(/\s+/g, " ");
        const m = text.match(/Stitch ([\d,]+) of ([\d,]+)/);
        const th = text.match(/Thread (\d+) of (\d+)/);
        reads.push({ strand: Number(await tip.getAttribute("data-strand")), n: m[1], total: m[2], thread: th[0] });
        break;
      }
    }
  }
  expect(reads.length).toBeGreaterThanOrEqual(2);

  await page.getByRole("button", { name: "Stitch simulator" }).click();
  const scrub = page.getByRole("slider", { name: "Stitch progress" });
  await expect(scrub).toBeVisible();
  for (const r of reads) {
    // Strand j is drawn once the bar shows j + 1 strands.
    await scrub.fill(String(r.strand + 1));
    await expect(page.locator(".simcount")).toHaveText(`${r.n} / ${r.total} stitches`);
    await expect(page.getByTestId("sim-thread")).toContainText(r.thread);
  }
});
