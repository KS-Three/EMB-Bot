// simTimeline and its lookups (lib/simulate.js): the machine's events — thread
// blocks, trims, travel — laid out in strand units for the simulator.
import { test, expect } from "vitest";
import { simTimeline, blockAt, colorStopBetween, stepBlock, travelAt, countAt, blockThreadNames } from "./simulate.js";
import { designToStrands, strandStitchOrdinals } from "./strands.js";

// Three threads, a trim inside the first, a travel jump inside the second.
//   block 0: strands 0..2 (run A: 2 strands, trim, run B: 1 strand)
//   block 1: strands 3..4 (jump to 100,100 then 2 strands)
//   block 2: strand 5
const S = (x, y, type = "stitch") => ({ x, y, type });
const three = {
  colors: [{ r: 200, g: 0, b: 0, name: "Red" }, { r: 0, g: 0, b: 200, name: "Blue" }, { r: 0, g: 150, b: 0, name: "Green" }],
  stitches: [
    S(0, 0), S(10, 0), S(20, 0),
    S(20, 0, "trim"),
    S(30, 10, "jump"), S(30, 10), S(40, 10),
    S(40, 10, "trim"), S(40, 10, "color"),
    S(100, 100, "jump"), S(100, 100), S(110, 100), S(120, 100),
    S(120, 100, "trim"), S(120, 100, "color"),
    S(0, 50), S(5, 50),
    S(5, 50, "end"),
  ],
};
const leadingColor = { colors: [{ r: 1, g: 2, b: 3 }, { r: 4, g: 5, b: 6 }], stitches: [S(0, 0, "color"), S(0, 0), S(5, 5)] };
const trailingColor = { colors: [{ r: 1, g: 2, b: 3 }, { r: 4, g: 5, b: 6 }], stitches: [S(0, 0), S(5, 5), S(5, 5, "trim"), S(5, 5, "color"), S(5, 5, "end")] };

test("simTimeline counts exactly the strands designToStrands draws, on every fixture", () => {
  const empty = { colors: [], stitches: [] };
  for (const d of [three, empty, leadingColor, trailingColor]) {
    const tl = simTimeline(d);
    expect(tl.total).toBe(designToStrands(d).length);
    expect(tl.total).toBe(strandStitchOrdinals(d).length);
    // Blocks tile [0, total) in order, with no gap and no overlap.
    let at = 0;
    for (const b of tl.blocks) { expect(b.start).toBe(at); expect(b.end).toBeGreaterThanOrEqual(b.start); at = b.end; }
    expect(at).toBe(tl.total);
  }
});

test("one block per thread: the PDF sequence's rows, named by colors[k], coloured like the canvas", () => {
  const tl = simTimeline(three);
  expect(tl.blocks.map((b) => [b.start, b.end])).toEqual([[0, 3], [3, 5], [5, 6]]);
  expect(tl.blocks.map((b) => b.color.name)).toEqual(["Red", "Blue", "Green"]);
  // The block count IS the review's "thread changes" + 1 (estimate.js
  // sewFacts counts the `color` records) and the PDF's colors.length row
  // count — the three must say the same thing.
  expect(tl.blocks.length).toBe(three.stitches.filter((s) => s.type === "color").length + 1);
  expect(tl.blocks.length).toBe(three.colors.length);
  // Each block's rgb is the rgb its strands are painted with.
  const strands = designToStrands(three);
  for (const b of tl.blocks) for (let i = b.start; i < b.end; i++) expect(strands[i].rgb).toEqual(b.rgb);
});

test("trims and travel sit at the strand count when they happen, at the positions they name", () => {
  const tl = simTimeline(three);
  expect(tl.trims).toEqual([
    { at: 2, x: 20, y: 0 }, { at: 3, x: 40, y: 10 }, { at: 5, x: 120, y: 100 },
  ]);
  // Every break between strands, end-of-last to start-of-next; the trim at
  // (20,0) then the jump to (30,10) is ONE travel, not two.
  expect(tl.travels).toEqual([
    { at: 2, x0: 20, y0: 0, x1: 30, y1: 10 },
    { at: 3, x0: 40, y0: 10, x1: 100, y1: 100 },
    { at: 5, x0: 120, y0: 100, x1: 0, y1: 50 },
  ]);
  expect(countAt(tl.trims, 0)).toBe(0);
  expect(countAt(tl.trims, 2)).toBe(1);
  expect(countAt(tl.trims, 6)).toBe(3);
});

test("a break that lands where it left is not travel in flight", () => {
  const d = { colors: [{ r: 0, g: 0, b: 0 }], stitches: [S(0, 0), S(10, 0), S(10, 0, "trim"), S(10, 0), S(20, 0)] };
  const tl = simTimeline(d);
  expect(tl.travels).toEqual([{ at: 1, x0: 10, y0: 0, x1: 10, y1: 0 }]);
  expect(travelAt(tl, 1)).toBe(null);
  expect(travelAt(tl, 2)).toBe(null);
});

test("travelAt is the latest break reached, kept for the run it led into", () => {
  const tl = simTimeline(three);
  expect(travelAt(tl, 0)).toBe(null);
  expect(travelAt(tl, 1)).toBe(null);
  expect(travelAt(tl, 2)).toMatchObject({ at: 2, x1: 30 });
  expect(travelAt(tl, 3)).toMatchObject({ at: 3, x1: 100 });
  expect(travelAt(tl, 4)).toMatchObject({ at: 3 });
  expect(travelAt(tl, 5)).toMatchObject({ at: 5 });
});

test("blockAt: the thread of the last strand drawn; on a change, the one just finished", () => {
  const tl = simTimeline(three);
  expect([0, 1, 2, 3, 4, 5, 6].map((i) => blockAt(tl, i))).toEqual([0, 0, 0, 0, 1, 1, 2]);
  // Past the end clamps to the last block that sews.
  expect(blockAt(tl, 99)).toBe(2);
});

test("blockAt skips a block that sews nothing, and starts on the thread that sews first", () => {
  const d = { colors: [{ r: 1, g: 1, b: 1 }, { r: 2, g: 2, b: 2 }, { r: 3, g: 3, b: 3 }],
    stitches: [S(0, 0, "color"), S(0, 0), S(1, 0), S(2, 0), S(2, 0, "color"), S(2, 0, "color"), S(9, 9), S(9, 8)] };
  const tl = simTimeline(d);
  expect(tl.blocks.map((b) => [b.start, b.end])).toEqual([[0, 0], [0, 2], [2, 2], [2, 3]]);
  expect(blockAt(tl, 0)).toBe(1);
  expect(blockAt(tl, 2)).toBe(1);
  expect(blockAt(tl, 3)).toBe(3);
});

test("colorStopBetween: the first change strictly after `from`, at or before `to`", () => {
  const tl = simTimeline(three);
  expect(colorStopBetween(tl, 0, 2)).toBe(null);
  expect(colorStopBetween(tl, 0, 3)).toBe(3);
  expect(colorStopBetween(tl, 0, 6)).toBe(3);   // a big 8x step still stops at the first
  expect(colorStopBetween(tl, 3, 6)).toBe(5);   // resuming FROM a stop does not re-stop there
  expect(colorStopBetween(tl, 5, 6)).toBe(null);
  expect(colorStopBetween(null, 0, 6)).toBe(null);
});

test("colorStopBetween ignores a change at 0 and a trailing one with nothing after it", () => {
  expect(colorStopBetween(simTimeline(leadingColor), -1, 1)).toBe(null);
  expect(colorStopBetween(simTimeline(trailingColor), 0, 1)).toBe(null);
});

test("stepBlock walks the thread changes, then the ends", () => {
  const tl = simTimeline(three);
  expect(stepBlock(tl, 0, 1)).toBe(3);
  expect(stepBlock(tl, 3, 1)).toBe(5);
  expect(stepBlock(tl, 4, 1)).toBe(5);
  expect(stepBlock(tl, 5, 1)).toBe(6);  // past the last change: the end
  expect(stepBlock(tl, 6, -1)).toBe(5);
  expect(stepBlock(tl, 5, -1)).toBe(3); // ON a change, back goes to the one before
  expect(stepBlock(tl, 3, -1)).toBe(0);
  expect(stepBlock(tl, 0, -1)).toBe(0);
});

test("blockThreadNames labels each block from the chart the way the PDF does: code then name", () => {
  const tl = simTimeline(three);
  const chart = [
    { code: "1902", name: "Poinsettia", rgb: [210, 10, 10] },
    { name: "Navy", rgb: [0, 0, 180] },
    { code: "5513", name: "Emerald", rgb: [0, 140, 0] },
  ];
  expect(blockThreadNames(tl, chart)).toEqual(["1902 Poinsettia", "Navy", "5513 Emerald"]);
  expect(blockThreadNames(tl, [])).toEqual([]);
  expect(blockThreadNames(null, chart)).toEqual([]);
});

test("simTimeline of a 20k-stitch design is one pass, cheap enough to build on open", () => {
  const stitches = [];
  for (let i = 0; i < 20000; i++) {
    if (i % 2500 === 0 && i) stitches.push(S(i, 0, "trim"), S(i, 0, "color"));
    stitches.push(S(i % 200, Math.floor(i / 200)));
  }
  const d = { colors: Array.from({ length: 8 }, (_, k) => ({ r: k, g: k, b: k })), stitches };
  const t0 = performance.now();
  const tl = simTimeline(d);
  const ms = performance.now() - t0;
  expect(tl.blocks.length).toBe(8);
  expect(tl.total).toBe(designToStrands(d).length);
  expect(ms).toBeLessThan(200);
});
