import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
});

function letteringDesign(text, garment, overrides = {}) {
  const { EMB } = globalThis.window;
  const fontData = EMB.SATIN_FONTS.medium_font;
  return EMB.buildLetteringDesign(fontData, text, {
    garment, pxPerMm: 8, densityMm: 0.4, underlay: true, rgb: [20, 20, 20], ...overrides,
  });
}

test("combining two real text designs sums stitches, splices exactly one trim+color, and concatenates colors", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("AB", garment, { rgb: [200, 20, 20] });
  const d2 = letteringDesign("CD", garment, { rgb: [20, 20, 200], offsetYMm: -15 });

  const combined = combineDesigns([d1, d2]);

  expect(combined.stitchCount).toBe(d1.stitchCount + d2.stitchCount);
  expect(combined.colors.length).toBe(2);
  expect(combined.colorCount).toBe(2);

  // d1's own real (non-"end") stitches, unchanged, come first...
  const d1Own = d1.stitches.filter((s) => s.type !== "end");
  expect(combined.stitches.slice(0, d1Own.length)).toEqual(d1Own);
  // ...then exactly one trim, then exactly one color record...
  expect(combined.stitches[d1Own.length].type).toBe("trim");
  expect(combined.stitches[d1Own.length + 1].type).toBe("color");
  // ...then d2's own real stitches start right after.
  const afterSplice = combined.stitches.slice(d1Own.length + 2);
  const d2Own = d2.stitches.filter((s) => s.type !== "end");
  expect(afterSplice).toEqual(d2Own);

  // exactly one trim and one color record were ADDED (not present in either input)
  const trimsIn = (s) => s.filter((st) => st.type === "trim").length;
  const colorsIn = (s) => s.filter((st) => st.type === "color").length;
  expect(trimsIn(combined.stitches)).toBe(trimsIn(d1.stitches) + trimsIn(d2.stitches) + 1);
  expect(colorsIn(combined.stitches)).toBe(colorsIn(d1.stitches) + colorsIn(d2.stitches) + 1);

  // no "end" records survive combination
  expect(combined.stitches.some((s) => s.type === "end")).toBe(false);

  // decodes fine and is bigger than either input alone
  const bytesCombined = EMB.encodeDST(combined);
  const bytes1 = EMB.encodeDST(d1);
  const bytes2 = EMB.encodeDST(d2);
  expect(bytesCombined.length).toBeGreaterThan(bytes1.length);
  expect(bytesCombined.length).toBeGreaterThan(bytes2.length);
});

test("a single design in is returned structurally unchanged", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = letteringDesign("AB", garment);
  const out = combineDesigns([d]);
  expect(out).toBe(d);
  expect(out.stitches).toEqual(d.stitches);
});

test("_debug counters are summed across inputs when present", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("AB", garment);
  const d2 = letteringDesign("CD", garment, { offsetYMm: -15 });
  const combined = combineDesigns([d1, d2]);
  expect(combined._debug.nSatin).toBe((d1._debug.nSatin || 0) + (d2._debug.nSatin || 0));
  expect(combined._debug.nTrims).toBe((d1._debug.nTrims || 0) + (d2._debug.nTrims || 0));
});

// ---- two elements in one thread are one block ----------------------------
//
// A colour change is a machine stop, and on a single-needle home machine it
// is a full pause with a prompt to rethread — to the colour already loaded.
// combineDesigns spliced one between EVERY pair whatever colour they were, so
// the commonest real design there is (a two-line name in one thread) cost a
// stop it could not use, and the review's thread list and the PDF worksheet
// each listed the same cone twice.

test("two designs in the same thread merge into one block", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("TOP", garment, { rgb: [20, 20, 20] });
  const d2 = letteringDesign("BOTTOM", garment, { rgb: [20, 20, 20], offsetYMm: -15 });

  const combined = combineDesigns([d1, d2]);

  expect(combined.colors.length).toBe(1);
  expect(combined.colorCount).toBe(1);
  expect(combined.stitches.filter((s) => s.type === "color")).toHaveLength(0);
  // Every stitch still sews, and the needle still travels between the two —
  // the merge removes a machine STOP, not the trim that keeps thread off the
  // garment.
  expect(combined.stitchCount).toBe(d1.stitchCount + d2.stitchCount);
  const d1Own = d1.stitches.filter((s) => s.type !== "end");
  expect(combined.stitches[d1Own.length].type).toBe("trim");
  expect(combined.stitches[d1Own.length + 1].type).not.toBe("color");
});

test("different threads still get their colour change", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const combined = combineDesigns([
    letteringDesign("A", garment, { rgb: [200, 20, 20] }),
    letteringDesign("B", garment, { rgb: [20, 20, 200], offsetYMm: -15 }),
  ]);
  expect(combined.colors.length).toBe(2);
  expect(combined.stitches.filter((s) => s.type === "color")).toHaveLength(1);
});

test("only ADJACENT blocks merge — black/red/black stays three", async () => {
  // Merging the two blacks would mean reordering the sew, which changes what
  // lands on top of what. That is a different question and not a free one.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const combined = combineDesigns([
    letteringDesign("A", garment, { rgb: [20, 20, 20] }),
    letteringDesign("B", garment, { rgb: [200, 20, 20], offsetYMm: -12 }),
    letteringDesign("C", garment, { rgb: [20, 20, 20], offsetYMm: -24 }),
  ]);
  expect(combined.colors.length).toBe(3);
  expect(combined.stitches.filter((s) => s.type === "color")).toHaveLength(2);
});

test("the merge compares thread, not the label", async () => {
  // Every lettering block is named "Color 1" and the import builder numbers
  // its own per element, so `name` cannot decide this — and two entries that
  // sew identically must merge whatever they are called.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("A", garment, { rgb: [20, 20, 20] });
  const d2 = letteringDesign("B", garment, { rgb: [20, 20, 20], offsetYMm: -15 });
  d1.colors = [{ ...d1.colors[0], name: "Isacord 0020" }];
  d2.colors = [{ ...d2.colors[0], name: "Block 2" }];

  const combined = combineDesigns([d1, d2]);
  expect(combined.colors).toHaveLength(1);
  expect(combined.colors[0].name).toBe("Isacord 0020"); // the first block keeps its name
});

test("a merged first block does not swallow the rest of that design's blocks", async () => {
  // A two-colour design whose FIRST block matches the previous one loses only
  // that entry; its second block still needs its own colour and its own stop.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("A", garment, { rgb: [20, 20, 20] });
  const d2 = letteringDesign("B", garment, { rgb: [20, 20, 20], offsetYMm: -15 });
  d2.colors = [{ r: 20, g: 20, b: 20 }, { r: 200, g: 20, b: 20 }];

  const combined = combineDesigns([d1, d2]);
  expect(combined.colors).toEqual([{ r: 20, g: 20, b: 20, name: "Color 1" }, { r: 200, g: 20, b: 20 }]);
});

// ---- the run-span index across a combine --------------------------------
//
// `runs` is a second description of the record array (see combine.js's note),
// and the failure mode of a second description is that it drifts quietly. The
// check below is therefore the PARTITION identity the Python adapter pins:
// every stitch record claimed by exactly one span, none twice, no span
// reaching past the array. Index arithmetic that is off anywhere fails it,
// and arithmetic that is off by a constant fails it too.
//
// The spans are the builder's OWN — `buildLetteringDesign` emits them now —
// over real output, because what moves the indices here is the real
// interleaving: the jumps and trims the lettering path puts between glyph
// runs, the trailing `end` a digitized design carries, and the trim/color the
// splice adds.

// Every stitch record is claimed exactly once and no span runs off the end.
// Deliberately NOT "a span holds only stitch records": the browser lane's
// spans cover a run's travel jumps too, and the shared contract is about
// which run a STITCH belongs to.
function expectPartition(design) {
  const claimed = new Set();
  for (const s of design.runs) {
    expect(s.i1).toBeGreaterThanOrEqual(s.i0);
    expect(s.i0).toBeGreaterThanOrEqual(0);
    expect(s.i1).toBeLessThan(design.stitches.length);
    for (let i = s.i0; i <= s.i1; i++) {
      expect(claimed.has(i)).toBe(false);          // never claimed twice
      claimed.add(i);
    }
    expect(s.block).toBeGreaterThanOrEqual(0);
    expect(s.block).toBeLessThan(design.colors.length);
  }
  const stitchIdx = design.stitches
    .map((s, i) => (s.type === "stitch" ? i : -1))
    .filter((i) => i >= 0);
  const claimedStitches = [...claimed]
    .filter((i) => design.stitches[i].type === "stitch")
    .sort((a, b) => a - b);
  expect(claimedStitches).toEqual(stitchIdx);      // nothing left out
  expect(design.stitches.some((s, i) => s.type === "end" && claimed.has(i))).toBe(false);
}

test("combining carries the run-span index onto the combined record array", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("AB", garment, { rgb: [200, 20, 20] });
  const d2 = letteringDesign("CD", garment, { rgb: [20, 20, 200], offsetYMm: -15 });
  // The fixture is only worth anything if the builder really emitted spans.
  expect(d1.runs.length).toBeGreaterThan(1);
  expectPartition(d1);
  // One mark the browser lane never sets, so role is shown to survive too.
  d1.runs[0] = { ...d1.runs[0], role: "border" };

  const combined = combineDesigns([d1, d2]);
  expect(combined.runs).toHaveLength(d1.runs.length + d2.runs.length);
  expectPartition(combined);

  // The tiers survive the move, in sew order, and so does the border mark.
  expect(combined.runs.map((s) => s.kind))
    .toEqual([...d1.runs, ...d2.runs].map((s) => s.kind));
  expect(combined.runs.filter((s) => s.role === "border")).toHaveLength(1);

  // The second element's spans landed on its own colour, not the first's.
  const d1Own = d1.stitches.filter((s) => s.type !== "end").length;
  const second = combined.runs.filter((s) => s.i0 >= d1Own);
  expect(second).toHaveLength(d2.runs.length);
  expect(second.every((s) => s.block === 1)).toBe(true);
});

test("a merged block shifts the second element's spans onto the shared colour", async () => {
  // Same thread on both elements: no `color` record is spliced and the
  // colours array loses the duplicate, so block 0 of the second design has to
  // become block 0 of the combined one, not block 1.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("TOP", garment, { rgb: [20, 20, 20] });
  const d2 = letteringDesign("BOTTOM", garment, { rgb: [20, 20, 20], offsetYMm: -15 });

  const combined = combineDesigns([d1, d2]);
  expect(combined.colors).toHaveLength(1);
  expect(combined.runs.every((s) => s.block === 0)).toBe(true);
  expectPartition(combined);
});

test("three elements still partition, with the splice records counted each time", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const combined = combineDesigns([
    letteringDesign("A", garment, { rgb: [20, 20, 20] }),
    letteringDesign("B", garment, { rgb: [200, 20, 20], offsetYMm: -12 }),
    letteringDesign("C", garment, { rgb: [20, 20, 20], offsetYMm: -24 }),
  ]);
  expect(combined.colors).toHaveLength(3);
  expectPartition(combined);
  expect(new Set(combined.runs.map((s) => s.block))).toEqual(new Set([0, 1, 2]));
});

test("an interior end record shifts the spans after it, not just a trailing one", async () => {
  // `buildLetteringDesign` emits no `end` at all and `buildQualityDesign`
  // appends one at the very end, so neither on its own would catch a fixed
  // offset. A design assembled from parts can carry one MID-STREAM, and
  // combine strips those too — this is the case that fails if someone writes
  // `i0 + off` instead of tracking the running delta.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("AB", garment, { rgb: [200, 20, 20] });
  const d2 = letteringDesign("CD", garment, { rgb: [20, 20, 200], offsetYMm: -15 });

  // Between two spans, so no span is broken by it — insert after the first
  // span ends, and shift every later index by one to match.
  const cut = d1.runs[0].i1 + 1;
  d1.stitches.splice(cut, 0, { x: 0, y: 0, type: "end" });
  d1.runs = d1.runs.map((s, i) => (i === 0 ? s : { ...s, i0: s.i0 + 1, i1: s.i1 + 1 }));
  expect(d1.stitches.filter((s) => s.type === "end")).toHaveLength(1);
  expectPartition(d1);

  const combined = combineDesigns([d1, d2]);
  expect(combined.stitches.some((s) => s.type === "end")).toBe(false);
  expectPartition(combined);
  // The spans after the stripped record moved DOWN by one relative to a naive
  // splice-only offset — the whole point of the running delta.
  expect(combined.runs[1].i0).toBe(d1.runs[1].i0 - 1);
});

test("one element without an index means the combined design carries none", async () => {
  // Half an index looks exactly like a whole one to a reader: it would leave
  // the other element's stitches unclaimed and a renderer keying off the
  // partition would draw nothing for them. The honest answer is no index.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("AB", garment, { rgb: [200, 20, 20] });
  const d2 = letteringDesign("CD", garment, { rgb: [20, 20, 200], offsetYMm: -15 });
  delete d2.runs;                       // e.g. a design from an older service
  expect("runs" in combineDesigns([d1, d2])).toBe(false);

  // ...and the other way round, so it is the ANY rule and not an order quirk.
  const d3 = letteringDesign("EF", garment, { rgb: [20, 200, 20], offsetYMm: -30 });
  const d4 = letteringDesign("GH", garment, { rgb: [20, 20, 20] });
  delete d4.runs;
  expect("runs" in combineDesigns([d4, d3])).toBe(false);
});

test("an element that sews nothing does not cost the others their index", async () => {
  // `buildLetteringDesign` returns a stitchless design (and no `runs`) when a
  // font cannot sew any of the characters it was given. It claims no records,
  // so it can leave none unclaimed — dropping the whole index over it would
  // punish every other element for one unsupported character.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("AB", garment, { rgb: [200, 20, 20] });
  const d2 = letteringDesign("CD", garment, { rgb: [20, 20, 200], offsetYMm: -15 });
  const empty = { stitches: [{ x: 0, y: 0, type: "end" }], colors: [], stitchCount: 0, colorCount: 0 };

  const combined = combineDesigns([d1, empty, d2]);
  expect(combined.runs).toHaveLength(d1.runs.length + d2.runs.length);
  expectPartition(combined);
});

test("an element that sews nothing adds no trim and no colour stop", async () => {
  // Before the fix the empty element still got its own trim+color splice and
  // brought no colour with it: [red, empty, blue] came out as 3 blocks over 2
  // colours, so the PES table gave the EMPTY block blue and the real blue
  // stitches a padding thread, and the DST stopped for a block that sews
  // nothing. Blocks and `colors` must stay one-to-one.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d1 = letteringDesign("AB", garment, { rgb: [200, 20, 20] });
  const d2 = letteringDesign("CD", garment, { rgb: [20, 20, 200], offsetYMm: -15 });
  const empty = () => ({ stitches: [{ x: 0, y: 0, type: "end" }], colors: [], stitchCount: 0, colorCount: 0 });
  const blocks = (d) => 1 + d.stitches.filter((s) => s.type === "color").length;

  const mid = combineDesigns([d1, empty(), d2]);
  expect(mid.colors).toHaveLength(2);
  expect(blocks(mid)).toBe(mid.colors.length);
  expect(mid.stitches.filter((s) => s.type === "trim")).toHaveLength(
    d1.stitches.filter((s) => s.type === "trim").length + d2.stitches.filter((s) => s.type === "trim").length + 1);
  expect(mid.stitches).toEqual(combineDesigns([d1, d2]).stitches);

  // Leading empty: the stream must not open with a trim/colour before any stitch.
  const lead = combineDesigns([empty(), d1, d2]);
  expect(["trim", "color"]).not.toContain(lead.stitches[0].type);
  expect(lead.stitches).toEqual(combineDesigns([d1, d2]).stitches);
  expect(blocks(lead)).toBe(lead.colors.length);

  // Only one element sews: it passes through untouched, as a lone design does.
  expect(combineDesigns([empty(), d1, empty()])).toBe(d1);
});

test("a single design keeps its own index untouched", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = letteringDesign("AB", garment);
  const out = combineDesigns([d]);
  expect(out).toBe(d);
  expect(out.runs).toBe(d.runs);
});

test("a span that does not describe its own design abandons the whole index", async () => {
  // The guard that keeps a plausible-looking lie out of the combined design.
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const mk = () => [
    letteringDesign("AB", garment, { rgb: [200, 20, 20] }),
    letteringDesign("CD", garment, { rgb: [20, 20, 200], offsetYMm: -15 }),
  ];

  let [a, b] = mk();
  b.runs = [{ ...b.runs[0], i1: b.stitches.length + 50 }];        // off the end
  expect("runs" in combineDesigns([a, b])).toBe(false);

  [a, b] = mk();
  b.runs = [{ ...b.runs[0], block: 7 }];                          // no such colour
  expect("runs" in combineDesigns([a, b])).toBe(false);

  [a, b] = mk();
  b.runs = [{ ...b.runs[0], i0: -1 }];                            // before the start
  expect("runs" in combineDesigns([a, b])).toBe(false);
});

// ---- operator steps across a combine (R15) --------------------------------
//
// A digitized puff design carries `steps` (one per colour row) and its puff
// blocks are operator stops. Combining must carry the steps, never fold a
// same-thread neighbour into or out of a stepped block, and keep every span's
// `block` naming the row it sews in, so `steps[run.block].code` finds puff.

function puffDesign() {
  // Two black blocks, tack-down then puff, as `plan_to_design` shapes them.
  const sq = (x) => [
    { x, y: 0, type: "stitch" }, { x: x + 20, y: 0, type: "stitch" },
    { x: x + 20, y: 20, type: "stitch" }, { x, y: 20, type: "stitch" },
  ];
  const stitches = [...sq(0), { x: 0, y: 20, type: "trim" }, { x: 0, y: 20, type: "color" },
    ...sq(40), { x: 0, y: 0, type: "end" }];
  const base = { flags: [], material: "", piece: "", layers: [], spm: null, thread: "1801", rgb: [20, 20, 20] };
  return {
    stitches,
    colors: [{ r: 20, g: 20, b: 20, name: "1801 Black" }, { r: 20, g: 20, b: 20, name: "1801 Black" }],
    runs: [
      { i0: 0, i1: 3, kind: "run", shape: "S1", role: "", block: 0 },
      { i0: 6, i1: 9, kind: "satin", shape: "S1", role: "", block: 1 },
    ],
    steps: [
      { ...base, code: "PUFF_TACKDOWN", label: "Puff outline", index: 1, stitches: 4,
        action: "Stop: lay 3 mm puff foam over the outline, then continue", function: "color_change" },
      { ...base, code: "PUFF", label: "3D puff", index: 2, stitches: 4,
        action: "Tear away the excess foam. Design complete.", function: "end" },
    ],
  };
}

test("steps are carried, and a stepped block never merges with a same-thread neighbour", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const a = letteringDesign("A", garment, { rgb: [20, 20, 20] });
  const b = letteringDesign("B", garment, { rgb: [20, 20, 20], offsetYMm: -15 });
  const combined = combineDesigns([a, puffDesign(), b]);

  // Same thread throughout, yet no merge across either side of the puff.
  expect(combined.colors).toHaveLength(4);
  expect(combined.steps.map((s) => s.code)).toEqual(["COLOR", "PUFF_TACKDOWN", "PUFF", "COLOR"]);
  expect(combined.steps.map((s) => s.index)).toEqual([1, 2, 3, 4]);
  // The puff's own last row is mid-stream now: a stop, keeping its instruction.
  expect(combined.steps[2].function).toBe("color_change");
  expect(combined.steps[2].action).toBe("Tear away the excess foam");
  expect(combined.steps[3]).toMatchObject({ code: "COLOR", function: "end", action: "Design complete" });
  // A synthesized row has plan_steps' shape.
  expect(Object.keys(combined.steps[0]).sort()).toEqual(Object.keys(puffDesign().steps[0]).sort());
  // Stitch counts are per row, off the combined records.
  expect(combined.steps.reduce((n, s) => n + s.stitches, 0)).toBe(combined.stitchCount);
  expect(combined.steps[1].stitches).toBe(4);

  // Every span names its own row: the puff's two spans find their steps.
  expectPartition(combined);
  const puffSpans = combined.runs.filter((s) => s.shape === "S1");
  expect(puffSpans.map((s) => combined.steps[s.block].code)).toEqual(["PUFF_TACKDOWN", "PUFF"]);
  const aSpans = combined.runs.filter((s) => s.i1 < puffSpans[0].i0);
  expect(aSpans.length).toBeGreaterThan(0);
  expect(aSpans.every((s) => combined.steps[s.block].code === "COLOR")).toBe(true);
});

test("a puff design last keeps its tear-away ahead of Design complete", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const a = letteringDesign("A", garment, { rgb: [200, 20, 20] });
  const combined = combineDesigns([a, puffDesign()]);
  expect(combined.steps.map((s) => s.function)).toEqual(["color_change", "color_change", "end"]);
  expect(combined.steps[0].action).toBe("Change thread to Color 1");
  expect(combined.steps[2].action).toBe("Tear away the excess foam. Design complete.");
  expect(combined.runs.filter((s) => s.shape === "S1").map((s) => s.block)).toEqual([1, 2]);
});

test("same-thread COLOR rows still merge when steps are carried", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const a = letteringDesign("A", garment, { rgb: [20, 20, 20] });
  const b = letteringDesign("B", garment, { rgb: [20, 20, 20], offsetYMm: -15 });
  b.steps = [{ code: "COLOR", label: "Thread Color 1", action: "Design complete", function: "end",
    flags: [], material: "", piece: "", layers: [], spm: null, thread: "Color 1", rgb: [20, 20, 20] }];
  const combined = combineDesigns([a, b]);
  expect(combined.colors).toHaveLength(1);
  expect(combined.steps).toHaveLength(1);
  expect(combined.steps[0]).toMatchObject({ code: "COLOR", function: "end", action: "Design complete" });
  expect(combined.steps[0].stitches).toBe(combined.stitchCount);
});

test("no input with steps -> no steps key, output unchanged", async () => {
  const { combineDesigns } = await import("./combine.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const combined = combineDesigns([
    letteringDesign("A", garment, { rgb: [200, 20, 20] }),
    letteringDesign("B", garment, { rgb: [20, 20, 200], offsetYMm: -15 }),
  ]);
  expect("steps" in combined).toBe(false);
});
