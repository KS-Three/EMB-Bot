// The stitch inspector's lookup (lib/stitchInspect.js): grid index, nearest
// strand within the radius, and the numbers the tooltip shows.
import { test, expect } from "vitest";
import { buildStitchIndex, nearestStrand, strandInfo, inspectAt, kindLabel, canvasPxToMm, INSPECT_RADIUS_MM } from "./stitchInspect.js";
import { designToStrands, strandStitchOrdinals } from "./strands.js";
import { simTimeline, blockAt } from "./simulate.js";

const S = (x, y, type = "stitch") => ({ x, y, type });

// Three threads, a trim, a jump, and run spans that tag satin / fill / bean /
// underlay / a border, so every label and the block walk are exercised.
const tagged = {
  colors: [{ r: 200, g: 0, b: 0, name: "Red" }, { r: 0, g: 0, b: 200, name: "Blue" }, { r: 0, g: 150, b: 0, name: "Green" }],
  stitches: [
    S(0, 0), S(2, 0), S(4, 0),            // 0..2  underlay
    S(4, 0, "trim"),
    S(10, 0, "jump"), S(10, 0), S(10, 4), S(11, 0), // 5..7 satin
    S(11, 0, "trim"), S(11, 0, "color"),
    S(20, 20, "jump"), S(20, 20), S(23, 20), S(26, 20), // 11..13 fill
    S(26, 20, "color"),
    S(0, 30), S(1, 30), S(2, 30),         // 15..17 bean border
    S(2, 30, "end"),
  ],
  runs: [
    { i0: 0, i1: 2, kind: "underlay", shape: "a", role: "" },
    { i0: 5, i1: 7, kind: "satin", shape: "a", role: "" },
    { i0: 11, i1: 13, kind: "fill", shape: "b", role: "" },
    { i0: 15, i1: 17, kind: "bean", shape: "b", role: "border" },
  ],
};

// A seeded random walk: many short stitches, some long ones, trims and colour
// changes, so the grid holds strands spanning several cells.
function randomDesign(n, seed) {
  let s = seed >>> 0;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const stitches = [];
  let x = 0, y = 0;
  for (let i = 0; i < n; i++) {
    const r = rnd();
    if (r < 0.01) { stitches.push(S(x, y, "trim")); x = rnd() * 80 - 40; y = rnd() * 60 - 30; stitches.push(S(x, y, "jump")); }
    else if (r < 0.012) stitches.push(S(x, y, "color"));
    const step = rnd() < 0.1 ? 4 + rnd() * 8 : 0.3 + rnd() * 2.5;
    const a = rnd() * Math.PI * 2;
    x += Math.cos(a) * step; y += Math.sin(a) * step;
    stitches.push(S(x, y));
  }
  return { colors: [{ r: 1, g: 2, b: 3 }, { r: 4, g: 5, b: 6 }, { r: 7, g: 8, b: 9 }], stitches };
}

// The reference: every strand measured, same tie rule (later wins).
function bruteNearest(strands, x, y, r) {
  let best = -1, bestD = r * r;
  strands.forEach((s, j) => {
    const dx = s.x1 - s.x0, dy = s.y1 - s.y0, l2 = dx * dx + dy * dy;
    let t = l2 > 0 ? ((x - s.x0) * dx + (y - s.y0) * dy) / l2 : 0;
    t = Math.max(0, Math.min(1, t));
    const ex = s.x0 + t * dx - x, ey = s.y0 + t * dy - y, d = ex * ex + ey * ey;
    if (d < bestD || (d === bestD && j > best)) { bestD = d; best = j; }
  });
  return best;
}

test("the grid finds exactly the strand a scan of every strand finds", () => {
  for (const seed of [1, 7, 42]) {
    const d = randomDesign(3000, seed);
    const ix = buildStitchIndex(d);
    const strands = designToStrands(d);
    let s = seed * 97;
    const rnd = () => ((s = (s * 1103515245 + 12345) >>> 0) / 4294967296);
    let hits = 0;
    for (let q = 0; q < 2000; q++) {
      const x = rnd() * 120 - 60, y = rnd() * 100 - 50;
      const want = bruteNearest(strands, x, y, INSPECT_RADIUS_MM);
      expect(nearestStrand(ix, x, y), `seed ${seed} at ${x},${y}`).toBe(want);
      if (want >= 0) hits++;
    }
    // Both outcomes were exercised, not just misses.
    expect(hits).toBeGreaterThan(200);
  }
});

test("only within 1.5 mm, measured to the segment, not its ends", () => {
  const d = { colors: [{ r: 0, g: 0, b: 0 }], stitches: [S(0, 0), S(10, 0)] };
  const ix = buildStitchIndex(d);
  expect(nearestStrand(ix, 5, 1.4)).toBe(0);
  expect(nearestStrand(ix, 5, -1.5)).toBe(0);
  expect(nearestStrand(ix, 5, 1.6)).toBe(-1);
  expect(nearestStrand(ix, 11.4, 0)).toBe(0);
  expect(nearestStrand(ix, 11.6, 0)).toBe(-1);
  expect(nearestStrand(ix, 500, 500)).toBe(-1);
  expect(nearestStrand(ix, NaN, 0)).toBe(-1);
});

test("a tie goes to the stitch sewn later (the one on top)", () => {
  const d = { colors: [{ r: 0, g: 0, b: 0 }], stitches: [S(0, 0), S(5, 0), S(0, 0)] };
  const ix = buildStitchIndex(d);
  // Strand 1 runs back over strand 0.
  expect(nearestStrand(ix, 2, 0.5)).toBe(1);
});

test("an empty design has no index and every lookup misses", () => {
  expect(buildStitchIndex({ stitches: [], colors: [] })).toBe(null);
  expect(buildStitchIndex({ stitches: [S(1, 1)], colors: [] })).toBe(null);
  expect(inspectAt(null, 0, 0)).toBe(null);
  expect(strandInfo(null, 0)).toBe(null);
});

test("the info: ordinal and total from strandStitchOrdinals, block from blockAt, length, label", () => {
  const ix = buildStitchIndex(tagged);
  const ord = strandStitchOrdinals(tagged);
  const tl = simTimeline(tagged);
  const strands = designToStrands(tagged);
  expect(ix.n).toBe(strands.length);
  for (let j = 0; j < strands.length; j++) {
    const info = strandInfo(ix, j, ["1 Red", "2 Blue", "3 Green"]);
    expect(info.ordinal).toBe(ord[j]);
    expect(info.total).toBe(ord[ord.length - 1]);
    expect(info.block).toBe(blockAt(tl, j + 1) + 1);
    expect(info.blocks).toBe(3);
  }
  // Underlay 0 -> 2 mm along x: stitch 2, Red, thread 1.
  const u = inspectAt(ix, 1, 0.2, ["1 Red", "2 Blue", "3 Green"]);
  expect(u).toMatchObject({ strand: 0, ordinal: 2, total: 12, label: "Underlay", block: 1, thread: "1 Red" });
  expect(u.lengthMm).toBeCloseTo(2, 9);
  // The satin cross 10,0 -> 10,4: 4 mm.
  const sat = inspectAt(ix, 10.1, 2);
  expect(sat).toMatchObject({ label: "Satin", block: 1, thread: "Red" });
  expect(sat.lengthMm).toBeCloseTo(4, 9);
  // Fill in the second thread, a bean border in the third; without names the
  // block's own colour name is used.
  expect(inspectAt(ix, 21, 20)).toMatchObject({ label: "Tatami", block: 2, thread: "Blue" });
  const bean = inspectAt(ix, 1.5, 30);
  expect(bean).toMatchObject({ label: "Bean (border)", block: 3, thread: "Green", ordinal: 12 });
});

test("labels for every kind, with the border and edge-cap roles", () => {
  expect(kindLabel("satin", "")).toBe("Satin");
  expect(kindLabel("fill", "")).toBe("Tatami");
  expect(kindLabel("run", "")).toBe("Run");
  expect(kindLabel("bean", "")).toBe("Bean");
  expect(kindLabel("underlay", "")).toBe("Underlay");
  expect(kindLabel("travel", "")).toBe("Travel");
  expect(kindLabel("tie", "")).toBe("Tie");
  expect(kindLabel("stitch", "")).toBe("Stitch");
  expect(kindLabel("satin", "border")).toBe("Satin (border)");
  expect(kindLabel("satin", "edge_cap")).toBe("Satin (edge cap)");
  expect(kindLabel("something-new", "")).toBe("Stitch");
});

test("canvasPxToMm inverts toCanvas, y flip and pan included", () => {
  // preview.js's shape: scale s, +y up in mm, pan baked in.
  const s = 3.7, tx = 412.5, ty = 300.25;
  const toCanvas = (x, y) => ({ x: tx + x * s, y: ty - y * s });
  for (const [x, y] of [[0, 0], [12.3, -4.5], [-80, 61]]) {
    const p = toCanvas(x, y);
    const back = canvasPxToMm(toCanvas, p.x, p.y);
    expect(back.x).toBeCloseTo(x, 9);
    expect(back.y).toBeCloseTo(y, 9);
  }
  expect(canvasPxToMm(null, 1, 1)).toBe(null);
  expect(canvasPxToMm(() => ({ x: 0, y: 0 }), 1, 1)).toBe(null);
});

test("lookup cost on a 22,533-stitch design (reported, bounded loosely)", () => {
  const d = randomDesign(22533, 3);
  const t0 = performance.now();
  const ix = buildStitchIndex(d);
  const build = performance.now() - t0;
  const times = [];
  let s = 11;
  const rnd = () => ((s = (s * 1103515245 + 12345) >>> 0) / 4294967296);
  for (let q = 0; q < 5000; q++) {
    const x = rnd() * 120 - 60, y = rnd() * 100 - 50;
    const a = performance.now();
    inspectAt(ix, x, y);
    times.push(performance.now() - a);
  }
  times.sort((a, b) => a - b);
  const p95 = times[Math.floor(times.length * 0.95)];
  console.log(`[stitch inspect] build ${build.toFixed(1)} ms, lookup p95 ${p95.toFixed(4)} ms over ${times.length}`);
  // A frame is 16 ms; a lookup is far under it. Loose so a loaded runner passes.
  expect(p95).toBeLessThan(2);
});
