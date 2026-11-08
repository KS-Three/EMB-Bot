// Stitched font samples in the font browser (lib/fontSample.js, 2026-11-07).
//
// Each tile now sews "Abc 123" through the browser lettering engine, which
// needs the font's binary. The grid was rebuilt once already because opening
// the old dropdown fetched every binary (~30 MB), so the first test is the
// guard on that: opening the browser may fetch binaries for the visible rows
// and ONE look-ahead page below them, never anything further down, and never
// a binary over the sample's byte cap. It also pins that the stitched sample
// does not change the tile's (and so the row's) height.
//
// The second measures what one sample costs on the main thread: build +
// draw + encode, median over 20 fonts.
import { test, expect } from "@playwright/test";

const BIN = /\/fonts\/bin\/([^/?#]+)\.embf/;

// FontBrowser mirrors its sample queue onto .fb-body: data-samples-seen counts
// the tiles its IntersectionObserver reported in the window, data-samples is
// "idle" once every sample it asked for has finished. Waiting on these, not on
// networkidle plus a timer: the queue sews between fetches, and under four
// workers' CPU load a render gap outlasted networkidle's 500 ms, so the spec
// snapshotted its fetch count while two window samples were still queued and
// the reopen fetched them (CI run 42445397701: expected 16, received 18).
const sampleState = (dialog) => dialog.locator(".fb-body").evaluate((b) => ({
  seen: Number(b.dataset.samplesSeen || 0),
  idle: b.dataset.samples === "idle",
}));

test("opening the browser fetches only visible rows plus one look-ahead page, and rows keep their height", async ({ page }) => {
  await page.goto("/");
  // Let start-up finish first: FontSelect's own trigger preview ensures the
  // CURRENT font on load, and that fetch is not the browser's.
  await page.waitForLoadState("networkidle");

  const fetched = [];
  let release;
  const gate = new Promise((r) => { release = r; });
  await page.route(BIN, async (route) => {
    fetched.push(BIN.exec(route.request().url())[1]);
    await gate; // hold every binary until the tiles' plain height is measured
    await route.continue();
  });

  await page.locator(".fs-trigger").click();
  const dialog = page.getByRole("dialog", { name: "Choose a font" });
  const tiles = dialog.locator(".fb-tile");
  await expect(tiles.first()).toBeVisible();
  expect(await tiles.count()).toBeGreaterThan(40);
  // The observer fires on the next frame and asks for the whole window at
  // once; the gate holds every binary it starts, so nothing is sewn yet.
  await expect.poll(() => fetched.length).toBeGreaterThan(0);

  // Which tiles a browser counts as "visible rows + one page": anything that
  // starts above the body's bottom edge plus one body height.
  const layout = () => dialog.evaluate((d) => {
    const body = d.querySelector(".fb-body").getBoundingClientRect();
    const limit = body.bottom + body.height;
    const all = [...d.querySelectorAll(".fb-tile")];
    return {
      window: all.filter((t) => t.getBoundingClientRect().top < limit).map((t) => t.dataset.key),
      visible: all.filter((t) => t.getBoundingClientRect().top < body.bottom).length,
      heights: all.slice(0, 12).map((t) => t.getBoundingClientRect().height),
      imgBox: all.slice(0, 12).map((t) => t.querySelector(".fb-tile-img").getBoundingClientRect().height),
    };
  });
  const before = await layout();
  const total = await tiles.count();
  release();

  // Samples land: stitched images replace static PNGs in the window.
  await expect.poll(() => dialog.locator("img.fb-stitched").count(), { timeout: 30_000 }).toBeGreaterThan(4);
  // ...and every sample the window asked for has finished, so the fetch count
  // below is the first opening's whole bill.
  await expect.poll(async () => (await sampleState(dialog)).idle, { timeout: 30_000 }).toBe(true);
  const after = await layout();

  const manifest = await page.evaluate(() => fetch("fonts/manifest.json").then((r) => r.json()));
  const bytes = Object.fromEntries(manifest.fonts.map((f) => [f.key, f.bytes]));
  const inWindow = new Set(before.window);
  console.log(`font-browser samples: ${total} tiles, ${before.visible} visible, window ${before.window.length}, fetched ${fetched.length} binaries, ${(fetched.reduce((s, k) => s + (bytes[k] || 0), 0) / 1e6).toFixed(1)} MB`);

  expect(fetched.length).toBeLessThanOrEqual(before.window.length);
  expect(fetched.length).toBeLessThan(total / 2);
  for (const k of fetched) {
    expect(inWindow.has(k), `${k} was fetched but lies below the look-ahead page`).toBe(true);
    expect(bytes[k], `${k} is over the sample byte cap`).toBeLessThanOrEqual(1_000_000);
  }
  expect(new Set(fetched).size).toBe(fetched.length); // no font fetched twice

  // Row height: the image box is fixed, so a stitched sample changes nothing.
  expect(after.heights).toEqual(before.heights);
  expect(after.imgBox).toEqual(before.imgBox);

  // Reopening shows the samples it already sewed, with no fetch at all.
  const sewn = await dialog.locator("img.fb-stitched").count();
  const n = fetched.length;
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await page.locator(".fs-trigger").click();
  await expect(dialog.locator(".fb-tile").first()).toBeVisible();
  await expect.poll(() => dialog.locator("img.fb-stitched").count()).toBeGreaterThanOrEqual(sewn);
  // The new observer has reported the window and its queue has drained: any
  // fetch it was going to make has started, and the route counted it.
  await expect.poll(async () => {
    const s = await sampleState(dialog);
    return s.seen > 0 && s.idle;
  }).toBe(true);
  expect(fetched.length).toBe(n);
});

// The clock: each font is timed once per PASS, over PASSES passes spread in
// time, and a font's cost is the BEST of its passes; the figure is the median
// of those over the 20 fonts. A wall clock on a shared CI runner reads the
// runner's other work as well as ours: this file shares four workers on four
// cores, and one single pass of the 20 fonts read a median of 11.3-47.9 ms on
// CI (13 attempts on 11 runs, 2026-11-07/08: 11.3, 13.4, 17.1, 17.5, 17.7,
// 19.6, 21.5, 22.0, 30.5, 32.3, 33.8, 41.3, 47.9; the 41.3 turned main red on
// run 42453083807 and its retry read 13.4, the 47.9 on PR run 42456795255
// retried at 11.3). Interference only ever ADDS time, so the best of several
// passes is the cost with the least of it in: a real slowdown in the code
// still raises every pass. The 40 ms ceiling is unchanged: 3.5x the two
// retries (11.3, 13.4) and 1.8x the median single pass (22.0). The
// single-pass median is still logged beside it.
const PASSES = 5;

test("a stitched sample costs at most 40 ms to sew and draw (median of 20 fonts, best of 5 passes each)", async ({ page }) => {
  await page.goto("/");
  const r = await page.evaluate(async (PASSES) => {
    const S = await import("/src/lib/fontSample.js");
    const L = await import("/src/lib/fontLoader.js");
    const man = await L.loadManifest();
    const keys = man.fonts.filter((f) => S.sampleEligible(f)).slice(0, 20).map((f) => f.key);
    const fonts = await Promise.all(keys.map((k) => L.ensureFont(k)));
    S.renderSampleUrl(window.EMB, fonts[0]); // warm the JIT once, untimed
    const best = fonts.map(() => Infinity);
    let first = null;
    let empty = 0;
    for (let p = 0; p < PASSES; p++) {
      const ms = [];
      fonts.forEach((f, i) => {
        const t0 = performance.now();
        const url = S.renderSampleUrl(window.EMB, f, { dpr: 2 });
        const dt = performance.now() - t0;
        ms.push(dt);
        if (dt < best[i]) best[i] = dt;
        if (!url && p === 0) empty++;
      });
      if (p === 0) first = ms;
      // Let the page breathe between passes, so they sample different moments.
      await new Promise((res) => setTimeout(res, 50));
    }
    const med = (a) => { const s = [...a].sort((x, y) => x - y); return (s[9] + s[10]) / 2; };
    return { n: best.length, median: med(best), firstPassMedian: med(first), max: Math.max(...best), empty };
  }, PASSES);
  console.log(`stitched sample: n ${r.n}, median ${r.median.toFixed(1)} ms (best of ${PASSES} passes), single-pass median ${r.firstPassMedian.toFixed(1)} ms, max ${r.max.toFixed(1)} ms`);
  expect(r.n).toBe(20);
  expect(r.empty).toBe(0);
  expect(r.median).toBeLessThanOrEqual(40);
});
