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

test("hoopFitNote names the hoop when the design exceeds it outright", () => {
  expect(hoopFitNote(120, 110, EMB.getHoop("4x4"))).toBe("Exceeds your 4×4 in hoop");
});

test("hoopFitNote tolerates a missing hoop or dims (no note rather than a throw)", () => {
  expect(hoopFitNote(90, 90, null)).toBeNull();
  expect(hoopFitNote(NaN, 90, EMB.getHoop("4x4"))).toBeNull();
});
