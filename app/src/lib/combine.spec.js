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
