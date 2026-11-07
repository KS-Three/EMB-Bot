// Underlay vs top stitching on the simulator's strand timeline
// (lib/simulate.js underlayRuns / pendingUnderlay / phaseAt) and the strip's
// click target (blockStart). The tags are the strands' own, from the
// design's run spans; nothing here classifies a stitch.
import { test, expect } from "vitest";
import { simTimeline, underlayRuns, pendingUnderlay, phaseAt, blockStart, blockAt } from "./simulate.js";
import { designToStrands } from "./strands.js";

const S = (x, y, type = "stitch") => ({ x, y, type });
// Block 0: shape a = underlay (strands 0-1) then fill (2-3); shape b =
//          underlay (4-5), a needle-down travel (6), then satin (7).
// Block 1: shape c = underlay (8) then fill (9).
const layered = {
  colors: [{ r: 200, g: 0, b: 0 }, { r: 0, g: 0, b: 200 }],
  stitches: [
    S(0, 0), S(10, 0), S(20, 0), S(20, 10), S(10, 10),
    S(30, 0), S(40, 0), S(40, 5), S(40, 10),
    S(40, 10, "trim"), S(40, 10, "color"),
    S(0, 50, "jump"), S(0, 50), S(5, 50), S(10, 50),
  ],
  runs: [
    { i0: 0, i1: 2, kind: "underlay", shape: "a", role: "", block: 0 },
    { i0: 3, i1: 4, kind: "fill", shape: "a", role: "", block: 0 },
    { i0: 5, i1: 6, kind: "underlay", shape: "b", role: "", block: 0 },
    { i0: 7, i1: 7, kind: "travel", shape: "b", role: "", block: 0 },
    { i0: 8, i1: 8, kind: "satin", shape: "b", role: "", block: 0 },
    { i0: 12, i1: 13, kind: "underlay", shape: "c", role: "", block: 1 },
    { i0: 14, i1: 14, kind: "fill", shape: "c", role: "", block: 1 },
  ],
};

const strands = designToStrands(layered);
const tl = simTimeline(layered);

test("the fixture's strands carry the tags the spans give them", () => {
  expect(strands.map((s) => s.kind)).toEqual(["underlay", "underlay", "fill", "fill", "underlay", "underlay", "travel", "satin", "underlay", "fill"]);
  expect(tl.blocks.map((b) => [b.start, b.end])).toEqual([[0, 8], [8, 10]]);
});

test("underlayRuns: each run is covered by its own shape's first top strand, past travel", () => {
  const ul = underlayRuns(strands, tl);
  expect(ul.runs.map((r) => [r.start, r.end, r.coverAt])).toEqual([[0, 2, 2], [4, 6, 7], [8, 9, 9]]);
  expect(ul.runs.map((r) => r.rgb)).toEqual([[200, 0, 0], [200, 0, 0], [0, 0, 200]]);
  expect(ul.maxCover).toEqual([2, 7, 9]);
});

test("pending underlay: sewn, and its top not begun; never once the top is on", () => {
  const ul = underlayRuns(strands, tl);
  const at = (idx) => pendingUnderlay(ul, idx).map((r) => [r.start, r.end]);
  expect(at(0)).toEqual([]);
  expect(at(1)).toEqual([[0, 1]]);       // half of a's underlay sewn
  expect(at(2)).toEqual([[0, 2]]);       // all of it; the fill is next
  expect(at(3)).toEqual([]);             // a's fill has begun
  expect(at(5)).toEqual([[4, 5]]);
  expect(at(7)).toEqual([[4, 6]]);       // the travel does not cover it
  expect(at(8)).toEqual([]);             // b's satin has
  expect(at(9)).toEqual([[8, 9]]);       // the next thread's underlay
  expect(at(10)).toEqual([]);
});

test("a shape whose top is in no later strand of its block stays pending to the block's end only", () => {
  const d = { ...layered, runs: layered.runs.map((r) => (r.shape === "b" && r.kind !== "underlay" ? { ...r, shape: "z" } : r)) };
  const st = designToStrands(d);
  const ul = underlayRuns(st, simTimeline(d));
  expect(ul.runs[1].coverAt).toBe(8);
  expect(pendingUnderlay(ul, 8).map((r) => [r.start, r.end])).toEqual([[4, 6]]);
  expect(pendingUnderlay(ul, 9).map((r) => r.start)).toEqual([8]);
});

test("an underlay with no shape is covered by the next top strand of any shape", () => {
  const d = { ...layered, runs: layered.runs.map((r) => ({ ...r, shape: r.kind === "underlay" ? "" : r.shape })) };
  const ul = underlayRuns(designToStrands(d), simTimeline(d));
  expect(ul.runs.map((r) => r.coverAt)).toEqual([2, 7, 9]);
});

test("a design without runs has no underlay: nothing pending, no phase", () => {
  const plain = { colors: layered.colors, stitches: layered.stitches };
  const st = designToStrands(plain);
  const ul = underlayRuns(st, simTimeline(plain));
  expect(ul.runs).toEqual([]);
  expect(pendingUnderlay(ul, 5)).toEqual([]);
  expect(underlayRuns([], null).runs).toEqual([]);
  expect(pendingUnderlay(null, 3)).toEqual([]);
});

test("phaseAt names what the last strand drawn is, and nothing at the ends", () => {
  expect(phaseAt(strands, 0, tl.total)).toBe(null);
  expect(phaseAt(strands, 1, tl.total)).toBe("underlay");
  expect(phaseAt(strands, 3, tl.total)).toBe("top");
  expect(phaseAt(strands, 7, tl.total)).toBe("top");   // travel is not underlay
  expect(phaseAt(strands, 9, tl.total)).toBe("underlay");
  expect(phaseAt(strands, tl.total, tl.total)).toBe(null);
});

test("blockStart: a band's click lands on that thread's start, where the machine stops", () => {
  expect(blockStart(tl, 0)).toBe(0);
  expect(blockStart(tl, 1)).toBe(8);
  // Landing there, the bar names the band's thread as the one to load next
  // (SimBar reads blockAt(index + 1) while stopped).
  expect(blockAt(tl, blockStart(tl, 1) + 1)).toBe(1);
  expect(blockStart(tl, 9)).toBe(0);
  expect(blockStart(null, 1)).toBe(0);
});

test("pendingUnderlay stays cheap: it stops scanning once no earlier run can be pending", () => {
  // 2,000 shapes of underlay-then-fill; at the end only the last can pend.
  const stitches = [], runs = [];
  for (let k = 0; k < 2000; k++) {
    const i0 = stitches.length;
    for (let j = 0; j < 4; j++) stitches.push(S(k * 10 + j, 0));
    runs.push({ i0, i1: i0 + 1, kind: "underlay", shape: "s" + k, role: "", block: 0 });
    runs.push({ i0: i0 + 2, i1: i0 + 3, kind: "fill", shape: "s" + k, role: "", block: 0 });
  }
  const d = { colors: [{ r: 1, g: 2, b: 3 }], stitches, runs };
  const st = designToStrands(d);
  const ul = underlayRuns(st, simTimeline(d));
  expect(ul.runs.length).toBe(2000);
  let reads = 0;
  const spy = { runs: new Proxy(ul.runs, { get(t, p) { if (/^\d+$/.test(String(p))) reads++; return t[p]; } }), maxCover: ul.maxCover };
  const last = ul.runs[1999];
  expect(pendingUnderlay(spy, last.start + 1).map((r) => r.start)).toEqual([last.start]);
  expect(reads).toBeLessThan(40); // a binary search and one step back, not 2,000
});
