import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";

// hoop.js imports emb.js at module scope, and emb.js throws synchronously
// unless globalThis.EMB already looks like the loaded engine — so the real
// engine hoop modules are loaded first (they're dual-mode IIFEs that assign
// onto globalThis.EMB) plus a stub for the buildLetteringDesign gate, and
// hoop.js itself is imported dynamically after. Same "stub before
// importing" ordering TextStep.spec.js documents.
let effectiveHoop, hoopFitNote, EMB;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  ({ effectiveHoop, hoopFitNote } = await import("./hoop.js"));
  ({ EMB } = await import("./emb.js"));
});

test("effectiveHoop defaults to the per-garment suggestion when hoopId is null", () => {
  // left_chest is a 4x4in (101.6mm) placement box — a hair over the 4x4
  // hoop's 100mm field, so the suggestion steps up to 5x7.
  const r = effectiveHoop({ garmentId: "left_chest", hoopId: null });
  expect(r.suggested).toBe(true);
  expect(r.hoop.id).toBe("5x7");

  // sleeve (3x3in) genuinely fits the smallest hoop.
  expect(effectiveHoop({ garmentId: "sleeve", hoopId: null }).hoop.id).toBe("4x4");
});

test("effectiveHoop honors a manual pick over the suggestion", () => {
  const r = effectiveHoop({ garmentId: "sleeve", hoopId: "8x8" });
  expect(r.suggested).toBe(false);
  expect(r.hoop.id).toBe("8x8");
});

test("effectiveHoop falls back to the suggestion for an unknown hoopId", () => {
  const r = effectiveHoop({ garmentId: "sleeve", hoopId: "not-a-hoop" });
  expect(r.suggested).toBe(true);
  expect(r.hoop.id).toBe("4x4");
});

test("hoopFitNote is silent when the design fits", () => {
  expect(hoopFitNote(90, 90, EMB.getHoop("4x4"))).toBeNull();
  // exact fit is a fit
  expect(hoopFitNote(100, 100, EMB.getHoop("4x4"))).toBeNull();
});

test("hoopFitNote suggests rotating when only the rotated orientation fits", () => {
  // 170x120 into a 130x180 (5x7) hoop — the orientation-aware case.
  const note = hoopFitNote(170, 120, EMB.getHoop("5x7"));
  expect(note).toMatch(/Exceeds your 5×7 in hoop/);
  expect(note).toMatch(/rotate/i);
});

test("hoopFitNote names the hoop that WOULD fit, when one does", () => {
  // 120x110 clears every 4x4 orientation and drops straight into a 5x7.
  // Saying only "Exceeds your 4×4 in hoop" left the customer to work out
  // which of the four presets to switch to — a fix the app already knows.
  expect(hoopFitNote(120, 110, EMB.getHoop("4x4"))).toBe("Exceeds your 4×4 in hoop — a 5×7 in hoop fits it");
});

test("hoopFitNote says so when NO hoop this app offers can hold it", () => {
  // Not an edge case. Measured 2026-09-07: four of the ten shipped placement
  // boxes are larger than the biggest hoop offered (8×8 in = 200 mm), and
  // auto-fit targets the placement box — so every design on 40% of the garment
  // picker lands here, on every run.
  const note = hoopFitNote(304.8, 304.8, EMB.getHoop("8x8"));   // full_back
  expect(note).toBe("Exceeds your 8×8 in hoop, and every hoop this app offers — make it smaller under Size");
  // The half that matters: it must NOT send them shopping for a bigger hoop.
  expect(note).not.toMatch(/a \S+ hoop fits it/);
  // Same answer from a smaller starting hoop — what is impossible does not
  // depend on which preset happens to be selected.
  expect(hoopFitNote(304.8, 304.8, EMB.getHoop("4x4"))).toMatch(/every hoop this app offers/);
});

test("hoopFitNote covers every shipped garment's own placement box", () => {
  // The four that cannot fit are exactly full_back, tote, jacket_back and
  // blanket. Asserted as a SET so adding a garment, or a bigger hoop preset,
  // shows up here rather than silently changing what 40% of the picker says.
  const impossible = EMB.GARMENTS.filter((g) => {
    const note = hoopFitNote(g.widthIn * 25.4, g.heightIn * 25.4, EMB.suggestHoop(g));
    return note && /every hoop this app offers/.test(note);
  }).map((g) => g.id).sort();
  expect(impossible).toEqual(["blanket", "full_back", "jacket_back", "tote"]);
});

test("hoopFitNote tolerates a missing hoop or dims (no note rather than a throw)", () => {
  expect(hoopFitNote(90, 90, null)).toBeNull();
  expect(hoopFitNote(NaN, 90, EMB.getHoop("4x4"))).toBeNull();
});
