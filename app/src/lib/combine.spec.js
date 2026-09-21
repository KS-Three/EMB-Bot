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
