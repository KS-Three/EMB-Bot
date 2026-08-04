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
