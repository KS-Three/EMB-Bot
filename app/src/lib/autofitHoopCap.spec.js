import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";

// Kent's ruling 2026-10-13, "cap to hoop": garment auto-fit shrinks the design
// to the largest hoop's usable field, so the export oversize check never fires
// from auto-fit alone. Real engine, real text, every preset.
let EMB, generateElement, hoopFitNote;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
  ({ EMB } = await import("./emb.js"));
  ({ generateElement } = await import("./generate.js"));
  ({ hoopFitNote } = await import("./hoop.js"));
});

const el = (text) => ({
  id: "e1", type: "text", text, fontKey: "medium_font", colorRgb: [20, 20, 20], colorRanges: [],
  weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, underlay: true,
  sizeMm: null, offsetXMm: 0, offsetYMm: 0,
});

test("every garment preset: auto-fit result fits the largest hoop, so no oversize note", () => {
  const biggest = EMB.HOOPS[EMB.HOOPS.length - 1];
  for (const g of EMB.GARMENTS) {
    // A wide one-liner and a tall three-liner, so both box dimensions bind.
    for (const text of ["EMB", "EMB\nBOT\nFIT"]) {
      const d = generateElement(el(text), EMB.getGarment(g.id), {});
      expect(d.widthMM, `${g.id} ${JSON.stringify(text)} width`).toBeLessThanOrEqual(biggest.widthMm);
      expect(d.heightMM, `${g.id} ${JSON.stringify(text)} height`).toBeLessThanOrEqual(biggest.heightMm);
      expect(EMB.hoopFit(d.widthMM, d.heightMM, biggest)).toBe("fits");
      expect(hoopFitNote(d.widthMM, d.heightMM, biggest)).toBeNull();
    }
  }
});

test("the cap bites only where the placement box is bigger than the hoop", () => {
  const capped = EMB.GARMENTS.filter((g) => {
    const b = EMB.autoFitBoxMm(g);
    return b.w < g.widthIn * 25.4 - 1e-9 || b.h < g.heightIn * 25.4 - 1e-9;
  }).map((g) => g.id).sort();
  expect(capped).toEqual(["blanket", "full_back", "jacket_back", "tote"]);
});
