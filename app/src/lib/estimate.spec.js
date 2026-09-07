// The four facts an operator needs before loading a machine, for the lane that
// had none. An auto-digitized design gets them from the service
// (QualityReport: "N stitches · N thread changes · N trims · N m of thread");
// a lettering, hand-drawn, shape or imported-DST design never reaches the
// service, and its review screen showed the garment, the hoop, the content,
// the font — and not one number.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin",
                   "satinplay", "satinfont", "fontbin", "dst", "fonts", "digitize"])
    require("../../../src/" + f + ".js");
});

// 0.1 mm design units. A 10 mm leg is 100.
const D = {
  widthMM: 30, heightMM: 10,
  stitches: [
    { x: 0, y: 0, type: "jump" },
    { x: 0, y: 0, type: "stitch" },     // 1
    { x: 100, y: 0, type: "stitch" },   // 2   10 mm
    { x: 100, y: 100, type: "stitch" }, // 3   10 mm
    { x: 200, y: 100, type: "trim" },
    { x: 200, y: 100, type: "stitch" }, // 4   (new run: no length)
    { x: 300, y: 100, type: "stitch" }, // 5   10 mm
    { x: 300, y: 100, type: "color" },
    { x: 300, y: 100, type: "stitch" }, // 6   (new run)
    { x: 300, y: 200, type: "stitch" }, // 7   10 mm
    { x: 0, y: 0, type: "end" },
  ],
};

test("one walk, four facts — and the chain breaks exactly where a strand's does", async () => {
  const { sewFacts } = await import("./estimate.js");
  const f = sewFacts(D);
  expect(f.stitches).toBe(7);
  expect(f.trims).toBe(1);
  expect(f.threadChanges).toBe(1);
  // 4 sewn segments of 10 mm each. The jump, the trim and the colour change
  // each start a new run and contribute NO length — which is the same rule
  // designToStrands applies, and the same one Python's StitchRun.length_mm
  // sums under.
  expect(f.pathMm).toBeCloseTo(40, 6);
});

test("metres are the path times the engine's own factor, not a number invented here", async () => {
  const { sewFacts } = await import("./estimate.js");
  const { EMB } = await import("./emb.js");
  const f = sewFacts(D);
  // machine.py's THREAD_LENGTH_FACTOR, hand-ported and guarded against drift
  // by test/digitize.test.js. Asserted through EMB rather than as a literal so
  // this test cannot be the thing that pins a stale copy.
  expect(EMB.THREAD_LENGTH_FACTOR).toBe(1.35);
  expect(f.threadM).toBeCloseTo((40 * EMB.THREAD_LENGTH_FACTOR) / 1000, 9);
});

test("a design with nothing sewn states no facts at all", async () => {
  const { sewFacts, sewSummary } = await import("./estimate.js");
  // "0 stitches · 0 m of thread" under "Nothing to stitch yet" is noise, not
  // information.
  expect(sewSummary({ widthMM: 0, heightMM: 0, stitches: [{ x: 0, y: 0, type: "end" }] })).toEqual([]);
  expect(sewSummary({ stitches: [] })).toEqual([]);
  expect(sewSummary(null)).toEqual([]);
  expect(sewFacts(null)).toEqual({ stitches: 0, threadChanges: 0, trims: 0, pathMm: 0, threadM: null });
});

test("without the engine's factor there is NO metres row, not a wrong one", async () => {
  // A missing THREAD_LENGTH_FACTOR means a stale app/public/engine/ copy, and
  // `|| 1` would turn that into a plausible number: measured against a stale
  // copy on 2026-09-07 the review read "1.5 m (estimate)" for a design that
  // needs 2.1 — the path length quoted as thread.
  const { EMB } = await import("./emb.js");
  const { sewFacts, sewSummary } = await import("./estimate.js");
  const real = EMB.THREAD_LENGTH_FACTOR;
  try {
    delete EMB.THREAD_LENGTH_FACTOR;
    expect(sewFacts(D).threadM).toBeNull();
    expect(sewSummary(D).map((r) => r.label)).not.toContain("Thread");
    // Everything countable is still counted — only the estimate is withheld.
    expect(sewSummary(D).map((r) => r.label)).toEqual(["Size", "Stitches", "Thread changes", "Trims"]);
  } finally {
    EMB.THREAD_LENGTH_FACTOR = real;
  }
});

test("the rows read in the order an operator uses them", async () => {
  const { sewSummary } = await import("./estimate.js");
  expect(sewSummary(D).map((r) => r.label)).toEqual(["Size", "Stitches", "Thread changes", "Trims", "Thread"]);
  expect(sewSummary(D).map((r) => r.value)).toEqual(["30 × 10 mm", "7", "1", "1", "0.1 m (estimate)"]);
});

test("a single-colour design reports no thread change, and zero trims IS reported", async () => {
  const { sewSummary } = await import("./estimate.js");
  const one = { widthMM: 10, heightMM: 0, stitches: [
    { x: 0, y: 0, type: "stitch" }, { x: 100, y: 0, type: "stitch" },
  ]};
  const labels = sewSummary(one).map((r) => r.label);
  // Printing "0 thread changes" invites the reader to look for the control
  // that sets it; "0 trims" says there is nothing to clip, which is the same
  // reason QualityReport prints it.
  expect(labels).not.toContain("Thread changes");
  expect(labels).toContain("Trims");
  expect(sewSummary(one).find((r) => r.label === "Trims").value).toBe("0");
});

test("a real lettering design's facts agree with what the field caption says", async () => {
  // The end-to-end property: the review screen and the canvas caption are
  // reading the same design, so their stitch count and size must match. This
  // is the assertion that would have caught the numbers drifting apart the way
  // the width and the simulator counter both did.
  const { EMB } = await import("./emb.js");
  const { sewFacts } = await import("./estimate.js");
  const { readFileSync } = await import("node:fs");
  const { createRequire } = await import("node:module");
  const fb = createRequire(import.meta.url)("../../../src/fontbin.js");
  const font = fb.decodeFontBin(readFileSync(new URL("../../../src/fonts/bin/medium_font.embf", import.meta.url)));
  const d = EMB.buildLetteringDesign(font, "FRITSCH'S", { garment: EMB.getGarment("left_chest") });
  const f = sewFacts(d);
  expect(f.stitches).toBe(d.stitchCount);
  expect(f.pathMm).toBeGreaterThan(0);
  // Sanity on the estimate's magnitude: a ~100 mm design of 1.3k stitches is
  // metres of thread, not centimetres and not kilometres.
  expect(f.threadM).toBeGreaterThan(0.3);
  expect(f.threadM).toBeLessThan(20);
});
