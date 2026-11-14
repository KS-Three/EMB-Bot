// A group resize keeps the group inside the placement box and its layout
// intact (Kent's approval 2026-11-13). Drives the field's group-resize maths
// (EmbroideryField onPointerMove "gresize": dragResize, then
// groupResizeInBox) and its per-element reclamp (reclampAll's clampOffsets)
// against the real engine. Before the fix, "AB" and "CD" 8.4 mm apart on a
// left chest, dragged past the size cap, overlapped by 9.6 mm once the
// reclamp had pushed one of them back inside on its own.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";

let EMB, generateElement, bboxMmFromStitches, dragResize, unionBBox, groupResizeInBox, clampOffsets, placementBoxOf;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
  ({ EMB } = await import("./emb.js"));
  ({ generateElement } = await import("./generate.js"));
  ({ bboxMmFromStitches } = await import("./combine.js"));
  ({ dragResize, unionBBox, groupResizeInBox, clampOffsets } = await import("./interact.js"));
  ({ placementBoxOf } = await import("./placement.js"));
});

const T = (id, text, o) => ({ id, type: "text", text, fontKey: "medium_font", colorRgb: [20, 20, 20], colorRanges: [], weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, underlay: true, sizeMm: 20, offsetXMm: 0, offsetYMm: 0, ...o });

test("an off-centre group dragged past the cap stays inside the box, and the reclamp moves no member", () => {
  const g = EMB.getGarment("left_chest");
  const box = placementBoxOf({ garmentId: "left_chest" });
  let els = [T("a", "AB", { offsetXMm: -30 }), T("b", "CD", { offsetXMm: -6 })];
  const bb = (el) => bboxMmFromStitches(generateElement(el, g, {}).stitches);
  const start = els.map(bb);
  const members = els.map((el, i) => ({ id: el.id, offsetXMm: el.offsetXMm, offsetYMm: el.offsetYMm, widthMm: start[i].x1 - start[i].x0, targetMm: el.sizeMm }));
  const G = unionBBox(start);
  const gW = G.x1 - G.x0, gH = G.y1 - G.y0;
  const gap0 = start[1].x0 - start[0].x1;
  for (const dragMm of [10, 40, 200]) {
    const newW = dragResize(gW, gH, "se", dragMm, 0, 5, box.w);
    const r = groupResizeInBox(members, newW / gW, G, box.w, box.h, 5);
    const resized = els.map((el) => ({ ...el, ...r.patches[el.id] }));
    const after = resized.map(bb);
    const U = unionBBox(after);
    expect(U.x0, `${dragMm}: left edge`).toBeGreaterThanOrEqual(-box.w / 2 - 0.2);
    expect(U.x1, `${dragMm}: right edge`).toBeLessThanOrEqual(box.w / 2 + 0.2);
    // the layout scaled as one: the gap grew with the factor, never closed
    expect(after[1].x0 - after[0].x1, `${dragMm}: gap`).toBeGreaterThan(gap0);
    // reclampAll (per element) finds nothing to correct
    for (let i = 0; i < resized.length; i++) {
      const b = after[i];
      const c = clampOffsets(resized[i].offsetXMm, resized[i].offsetYMm, b.x1 - b.x0, b.y1 - b.y0, box.w, box.h);
      expect(Math.abs(c.offsetXMm - resized[i].offsetXMm), `${dragMm}: member ${i} reclamped`).toBeLessThanOrEqual(0.01);
      expect(Math.abs(c.offsetYMm - resized[i].offsetYMm)).toBeLessThanOrEqual(0.01);
    }
  }
});
