import { test, expect } from "vitest";
import { designToStrands } from "./strands.js";

const design = { colors: [{ r: 10, g: 20, b: 30 }], stitches: [
  { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" },
  { x: 10, y: 0, type: "stitch" }, { x: 10, y: 5, type: "stitch" },
  { x: 40, y: 5, type: "trim" }, { x: 40, y: 5, type: "end" },
]};

test("one strand per consecutive sewn segment, colored by block", () => {
  const s = designToStrands(design, {});
  expect(s.length).toBe(2); // (0,0)->(10,0) and (10,0)->(10,5)
  expect(s[0]).toMatchObject({ x0: 0, y0: 0, x1: 10, y1: 0, rgb: [10, 20, 30] });
});

test("no strand spans a jump/trim boundary", () => {
  const s = designToStrands(design, {});
  expect(s.some(v => v.x1 === 40)).toBe(false);
});

test("colorOverride recolors all strands", () => {
  const s = designToStrands(design, { colorOverride: [200, 0, 0] });
  expect(s[0].rgb).toEqual([200, 0, 0]);
});

// --- jumpTrimMarks (field diagnostic overlays) --------------------------

import { jumpTrimMarks } from "./strands.js";

test("jumpTrimMarks: jump/trim moves become dashed segments, trims get markers, stitches do not", () => {
  const design = { stitches: [
    { x: 0, y: 0, type: "stitch" },
    { x: 10, y: 0, type: "stitch" },
    { x: 50, y: 50, type: "jump" },     // travel -> one jump segment
    { x: 60, y: 50, type: "stitch" },
    { x: 90, y: 90, type: "trim" },     // trim with a move -> marker + segment
    { x: 91, y: 90, type: "stitch" },
    { x: 91, y: 90, type: "end" },
  ] };
  const m = jumpTrimMarks(design);
  expect(m.jumps).toEqual([
    { x0: 10, y0: 0, x1: 50, y1: 50 },
    { x0: 60, y0: 50, x1: 90, y1: 90 },
  ]);
  expect(m.trims).toEqual([{ x: 90, y: 90 }]);
});

test("jumpTrimMarks: zero-length jump moves draw nothing; color/end break the chain", () => {
  const design = { stitches: [
    { x: 0, y: 0, type: "stitch" },
    { x: 0, y: 0, type: "trim" },       // in-place trim: marker, no segment
    { x: 0, y: 0, type: "color" },
    { x: 40, y: 0, type: "stitch" },    // first stitch after color: no segment (chain broken)
  ] };
  const m = jumpTrimMarks(design);
  expect(m.jumps).toEqual([]);
  expect(m.trims).toEqual([{ x: 0, y: 0 }]);
});

// --- strandStitchOrdinals (the simulator's counter) ------------------------
//
// A strand is a SEGMENT BETWEEN two consecutive stitches, so N stitches in K
// runs make N − K strands. That put two numbers on screen together saying
// different things — "1289 stitches · 102×12 mm" under the canvas and
// "1280 / 1280" in the simulator bar, on a design with nine runs. Both were
// correct measurements of different things and only one was labelled.
import { strandStitchOrdinals } from "./strands.js";

test("each strand reports the stitch number it ends at", () => {
  // `design` above: jump, stitch#1, stitch#2, stitch#3, trim, end.
  // Two strands: #1->#2 ends at 2, #2->#3 ends at 3.
  expect(strandStitchOrdinals(design)).toEqual([2, 3]);
  // One entry per strand — the arrays index together, which is the whole
  // contract the simulator relies on.
  expect(strandStitchOrdinals(design).length).toBe(designToStrands(design, {}).length);
});

test("ordinals keep counting across a break, and the run that starts it paints nothing", () => {
  const d = { colors: [{ r: 0, g: 0, b: 0 }], stitches: [
    { x: 0, y: 0, type: "stitch" },   // 1
    { x: 1, y: 0, type: "stitch" },   // 2  <- strand ends here
    { x: 9, y: 9, type: "trim" },
    { x: 9, y: 9, type: "jump" },
    { x: 9, y: 9, type: "stitch" },   // 3  <- first of a new run: no strand
    { x: 9, y: 8, type: "stitch" },   // 4  <- strand ends here
  ]};
  expect(strandStitchOrdinals(d)).toEqual([2, 4]);
  expect(strandStitchOrdinals(d).length).toBe(designToStrands(d, {}).length);
});

test("a single-stitch run paints no segment, so its ordinal never appears", () => {
  // This is why the simulator's total is the LAST ORDINAL and not
  // design.stitchCount: it must never claim to have drawn a stitch it cannot.
  const d = { colors: [{ r: 0, g: 0, b: 0 }], stitches: [
    { x: 0, y: 0, type: "stitch" },   // 1
    { x: 1, y: 0, type: "stitch" },   // 2
    { x: 5, y: 5, type: "trim" },
    { x: 5, y: 5, type: "stitch" },   // 3 — alone between two breaks
    { x: 8, y: 8, type: "trim" },
    { x: 8, y: 8, type: "stitch" },   // 4
    { x: 8, y: 9, type: "stitch" },   // 5
  ]};
  expect(strandStitchOrdinals(d)).toEqual([2, 5]);
  expect(strandStitchOrdinals(d).length).toBe(designToStrands(d, {}).length);
});

test("a colour change breaks the chain for both, identically", () => {
  const d = { colors: [{ r: 0, g: 0, b: 0 }, { r: 9, g: 9, b: 9 }], stitches: [
    { x: 0, y: 0, type: "stitch" },   // 1
    { x: 1, y: 0, type: "stitch" },   // 2
    { x: 1, y: 0, type: "color" },
    { x: 1, y: 0, type: "stitch" },   // 3
    { x: 2, y: 0, type: "stitch" },   // 4
  ]};
  expect(strandStitchOrdinals(d)).toEqual([2, 4]);
  expect(strandStitchOrdinals(d).length).toBe(designToStrands(d, {}).length);
});

test("an empty or absent design answers nothing rather than throwing", () => {
  expect(strandStitchOrdinals({ stitches: [] })).toEqual([]);
  expect(strandStitchOrdinals({})).toEqual([]);
  expect(strandStitchOrdinals(null)).toEqual([]);
});

// --- run spans: what each strand IS ---------------------------------------
//
// `design.runs` is the browser's only source of stitch KIND: the design model
// is otherwise a flat {x,y,type} stream in which satin, tatami, bean runs,
// underlay and travel are indistinguishable. It is OPTIONAL and permanently
// so — every .embproj saved before 2026-09-15, every imported .dst, and the
// browser's own lettering/manual/shape lanes produce designs without it — so
// half of what these tests pin is that its ABSENCE changes nothing.

// jump, #1, #2, #3, trim, end (indices 0..5) — the fixture at the top of this
// file, now with spans over it.
const spanned = {
  colors: [{ r: 10, g: 20, b: 30 }],
  stitches: design.stitches,
  runs: [
    { i0: 0, i1: 2, kind: "underlay", shape: "s1", role: "", block: 0 },
    { i0: 3, i1: 5, kind: "satin", shape: "s1", role: "border", block: 0 },
  ],
};

test("with no runs, a strand is exactly what it always was — kind 'stitch' and NOTHING else", () => {
  const s = designToStrands(design, {});
  // The key SET is the assertion, not just the values: a stray role:"" or
  // shape:"" would be a new field on every strand of every legacy design.
  expect(Object.keys(s[0])).toEqual(["x0", "y0", "x1", "y1", "rgb", "kind"]);
  for (const v of s) expect(v.kind).toBe("stitch");
  // An empty or malformed runs array is the same as no runs at all.
  for (const runs of [[], null, undefined, "nonsense", [null], [{ kind: "satin" }]]) {
    expect(designToStrands({ ...design, runs }, {})).toEqual(s);
  }
});

test("a strand takes the kind/role/shape of the stitch it ends at", () => {
  const s = designToStrands(spanned, {});
  expect(s.length).toBe(2);
  // Strand 0 ends at stitch index 2, inside the underlay span; strand 1 ends
  // at index 3, the first stitch of the satin border span. The thread crossing
  // from one run into the next belongs to the run the needle is now sewing.
  expect(s[0]).toMatchObject({ kind: "underlay", role: "", shape: "s1" });
  expect(s[1]).toMatchObject({ kind: "satin", role: "border", shape: "s1" });
  // Geometry and colour are untouched by any of this.
  expect(s[0]).toMatchObject({ x0: 0, y0: 0, x1: 10, y1: 0, rgb: [10, 20, 30] });
});

test("colorOverride still recolours every strand when spans are present", () => {
  const s = designToStrands(spanned, { colorOverride: [200, 0, 0] });
  for (const v of s) expect(v.rgb).toEqual([200, 0, 0]);
  expect(s[1].kind).toBe("satin");
});

test("a stitch covered by no span falls back to the kindless 'stitch'", () => {
  const partial = { ...spanned, runs: [{ i0: 3, i1: 5, kind: "satin", shape: "s1", role: "", block: 0 }] };
  const s = designToStrands(partial, {});
  expect(s[0].kind).toBe("stitch"); // ends at index 2 — before the only span
  expect(s[1].kind).toBe("satin");
});

test("spans arriving out of order still resolve (the walk is a pointer, and a pointer needs them sorted)", () => {
  const scrambled = { ...spanned, runs: [spanned.runs[1], spanned.runs[0]] };
  expect(designToStrands(scrambled, {}).map((v) => v.kind)).toEqual(["underlay", "satin"]);
  // and the caller's array is not mutated out from under it
  expect(scrambled.runs[0].kind).toBe("satin");
});

test("one corrupt span does not un-kind the rest of the design", () => {
  // The walk advances a single monotonic pointer, so an entry with an
  // undefined i1 would wedge it and silently strip the kind off every stitch
  // after that point — a whole design rendered as if it had no runs, with
  // nothing on screen saying why. Corrupt entries are dropped instead.
  const corrupt = {
    ...spanned,
    runs: [{ i0: 0, i1: undefined, kind: "fill", shape: "x", role: "", block: 0 }, ...spanned.runs],
  };
  expect(designToStrands(corrupt, {}).map((v) => v.kind)).toEqual(["underlay", "satin"]);
  // Every entry corrupt -> the no-runs fallback, not a throw and not a blank.
  const allBad = { ...spanned, runs: [{ i0: "a", i1: 3 }, { i0: 1 }] };
  expect(designToStrands(allBad, {})).toEqual(designToStrands(design, {}));
});

test("spans do not change WHICH strands exist — the simulator's index mapping still holds", () => {
  // strandStitchOrdinals indexes together with designToStrands, and the
  // simulator relies on that. Adding kinds must not add, drop or reorder a
  // single strand.
  const plain = designToStrands(design, {});
  const kinded = designToStrands(spanned, {});
  expect(kinded.length).toBe(plain.length);
  expect(kinded.length).toBe(strandStitchOrdinals(spanned).length);
  for (let i = 0; i < plain.length; i++) {
    const { x0, y0, x1, y1, rgb } = kinded[i];
    expect({ x0, y0, x1, y1, rgb }).toEqual({ x0: plain[i].x0, y0: plain[i].y0, x1: plain[i].x1, y1: plain[i].y1, rgb: plain[i].rgb });
  }
});

test("a colour change inside a span keeps both the colour walk and the span walk correct", () => {
  const d = {
    colors: [{ r: 0, g: 0, b: 0 }, { r: 9, g: 9, b: 9 }],
    stitches: [
      { x: 0, y: 0, type: "stitch" },   // 0
      { x: 1, y: 0, type: "stitch" },   // 1
      { x: 1, y: 0, type: "color" },    // 2
      { x: 1, y: 0, type: "stitch" },   // 3
      { x: 2, y: 0, type: "stitch" },   // 4
    ],
    runs: [
      { i0: 0, i1: 1, kind: "fill", shape: "a", role: "", block: 0 },
      { i0: 3, i1: 4, kind: "satin", shape: "b", role: "edge_cap", block: 1 },
    ],
  };
  const s = designToStrands(d, {});
  expect(s.map((v) => v.kind)).toEqual(["fill", "satin"]);
  expect(s.map((v) => v.rgb)).toEqual([[0, 0, 0], [9, 9, 9]]);
  expect(s[1].role).toBe("edge_cap");
});
