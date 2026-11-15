// The hat front's clamp box is its PLACEMENTS box, 113.5 x 64.0 (Kent's ruling
// 2026-11-14, "Hat front only"). The field's clamps (placementBoxOf), the
// preview's drawn box (hoopTransform), the worksheet's garment box
// (exportWorksheetPDF), the node-edit prediction (predictedFit) and the engine
// (buildImportedDesign) must all say the same box, or the customer sees one
// size on the canvas and another on the sheet. Left chest and beanie stay split
// on purpose and are pinned here too (test/placement-box-paths.test.js has the
// engine-side pins; docs/placement-box-paths-2026-11-14.md the reasons).
import { test, expect, beforeAll, vi } from "vitest";
import { createRequire } from "node:module";

vi.mock("jspdf", () => ({ jsPDF: class FakeJsPDF {} }));
// Real hoopTransform; renderRealistic needs a canvas, which node does not have.
vi.mock("./preview.js", async (orig) => ({ ...(await orig()), renderRealistic: vi.fn() }));

let EMB;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "pes", "svgexport", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  ({ EMB } = await import("./emb.js"));
});

const HAT = { w: 113.5, h: 64 };

test("hat front: field clamp, preview box, worksheet box and node-edit prediction are one box", async () => {
  const { placementBoxOf, garmentOf } = await import("./placement.js");
  const { hoopTransform } = await import("./preview.js");
  const { exportWorksheetPDF } = await import("./exporters.js");
  const { predictedFit } = await import("./fieldNodeEdit.js");
  const project = { garmentId: "hat_front", placementId: null };
  const garment = garmentOf(project);

  // the field's clamp (SizePanel, EmbroideryField, App)
  expect(placementBoxOf(project)).toEqual(HAT);
  // the preview's drawn box
  const t = hoopTransform(garment, 640, 420, 20);
  expect(t.boxWmm).toBeCloseTo(HAT.w, 9);
  expect(t.boxHmm).toBeCloseTo(HAT.h, 9);
  // the worksheet's garment box
  delete globalThis.window.jspdf;
  const original = EMB.buildWorksheetPDF;
  const spy = vi.fn();
  EMB.buildWorksheetPDF = spy;
  try {
    await exportWorksheetPDF({ stitches: [], colors: [] }, garment);
    const meta = spy.mock.calls[0][1];
    expect(meta.garmentBox.widthMM).toBeCloseTo(HAT.w, 9);
    expect(meta.garmentBox.heightMM).toBeCloseTo(HAT.h, 9);
  } finally {
    EMB.buildWorksheetPDF = original;
  }
  // node-edit's typed-size prediction clamps on the same box: a tall shape typed
  // far too wide is stopped by the 64 mm height, not the old 57.15
  const shapes = [{ id: "s1", points: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 100 }, { x: 0, y: 100 }], curves: {}, stitchType: "fill", colorRgb: [0, 0, 0], angleDeg: null }];
  const fit = predictedFit({ id: 1, type: "manual", shapes, sizeMm: 500 }, shapes, garment);
  expect(fit.mmPerPx * 100).toBeCloseTo(HAT.h, 6); // the shape's 100 px height, drawn in mm
  // the engine's clamp
  const built = EMB.buildImportedDesign({
    stitches: [{ x: -10, y: -2000, type: "stitch" }, { x: 10, y: 2000, type: "stitch" }],
    widthMM: 2, heightMM: 400, colorCount: 1, stitchCount: 2, jumpCount: 0, trimCount: 0,
  }, { garment });
  expect(built.heightMM).toBeCloseTo(HAT.h, 1);
});

test("left chest and beanie stay split on purpose: the preview and sheet draw their inch pair, the field clamps to the PLACEMENTS box (Kent 2026-11-14)", async () => {
  const { placementBoxOf, garmentOf } = await import("./placement.js");
  const { hoopTransform } = await import("./preview.js");
  const split = {
    left_chest: { clamp: { w: 101.6, h: 101.6 }, field: { w: 96, h: 76.5 } },
    beanie: { clamp: { w: 114.3, h: 63.5 }, field: { w: 94.5, h: 56 } },
  };
  for (const [id, want] of Object.entries(split)) {
    const project = { garmentId: id, placementId: null };
    const t = hoopTransform(garmentOf(project), 640, 420, 20);
    expect(t.boxWmm, id).toBeCloseTo(want.clamp.w, 6);
    expect(t.boxHmm, id).toBeCloseTo(want.clamp.h, 6);
    expect(placementBoxOf(project), id).toEqual(want.field);
  }
});
