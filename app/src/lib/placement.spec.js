// The default Design width comes from the PLACEMENT (2026-10-27): the
// engine's fitScale of the artwork's aspect into the placement's box, hoop
// cap and the pro's left-chest area cap included — not the flat 80 mm
// project.js used to hand every garment. Run against the REAL engine table,
// so a changed box here is a changed default there.
import { beforeAll, expect, test } from "vitest";
import { createRequire } from "node:module";

let placement;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  // lib/emb.js refuses to load without EMB.buildLetteringDesign; stub it.
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  placement = await import("./placement.js");
});

const hat = { garmentId: "hat_front", placementId: null };

test("garmentOf: the default placement IS the garment; another placement carries its box", () => {
  const EMB = globalThis.EMB;
  expect(placement.garmentOf(hat)).toBe(EMB.getGarment("hat_front"));
  expect(placement.garmentOf({ garmentId: "hat_front", placementId: "hat_front" })).toBe(EMB.getGarment("hat_front"));
  const rear = placement.garmentOf({ garmentId: "hat_front", placementId: "hat_rear" });
  expect(rear.id).toBe("hat_front");
  expect(rear.placementId).toBe("hat_rear");
  expect(placement.garmentOf({ garmentId: "no_such" })).toBeUndefined();
  expect(placement.garmentOf(null)).toBeUndefined();
});

test("placementBoxOf is the clamp box: the pro's where measured, the placement's otherwise, null unknown", () => {
  // the two stale clamps (SizePanel, the field) read the hat's 127 x 57.15 inch pair until today
  expect(placement.placementBoxOf(hat)).toEqual({ w: 113.5, h: 64 });
  expect(placement.placementBoxOf({ garmentId: "hat_front", placementId: "hat_rear" })).toEqual({ w: 88.9, h: 38.1 });
  expect(placement.placementBoxOf({ garmentId: "left_chest" })).toEqual({ w: 96, h: 76.5 });
  expect(placement.placementBoxOf({ garmentId: "full_back", placementId: "left_chest" })).toEqual({ w: 96, h: 76.5 });
  expect(placement.placementBoxOf({ garmentId: "no_such" })).toBeNull();
});

test("hat front: a wide logo is width-bound at 113.5, a tall one height-bound at 64, by its aspect", () => {
  // 1400 x 316 px (the DigitizePanel spec's image): 113.5 wide would be 25.6 tall — width-bound
  expect(placement.fitTargetWidthMm({ w: 1400, h: 316 }, null, hat)).toBe(113.5);
  // a square logo on a hat: 64 tall caps it at 64 wide
  expect(placement.fitTargetWidthMm({ w: 500, h: 500 }, null, hat)).toBe(64);
  // 2:1 is height-bound too: 64 * 2 = 128 > 113.5, so width wins at 113.5
  expect(placement.fitTargetWidthMm({ w: 1000, h: 500 }, null, hat)).toBe(113.5);
  // 1.5:1 is height-bound: 64 * 1.5 = 96
  expect(placement.fitTargetWidthMm({ w: 1500, h: 1000 }, null, hat)).toBe(96);
});

test("left chest honours the 5,800 mm2 area cap: a square logo lands at sqrt(5800), under both edges", () => {
  const lc = { garmentId: "left_chest" };
  expect(placement.fitTargetWidthMm({ w: 800, h: 800 }, null, lc)).toBe(Math.round(Math.sqrt(5800) * 10) / 10); // 76.2
  // a wide one is width-bound at 96 (96 x 48 = 4,608 mm2, under the cap)
  expect(placement.fitTargetWidthMm({ w: 1000, h: 500 }, null, lc)).toBe(96);
  // 1.385:1 (Machine's LC) is area-bound: sqrt(5800 * 1.385) = 89.6, not 96
  expect(placement.fitTargetWidthMm({ w: 1385, h: 1000 }, null, lc)).toBe(89.6);
  // the right chest mirrors it, cap included
  expect(placement.fitTargetWidthMm({ w: 800, h: 800 }, null, { garmentId: "left_chest", placementId: "right_chest" })).toBe(76.2);
});

test("the crop's aspect is what is fitted, and the hoop cap holds on an over-hoop placement", () => {
  // a 1000 x 1000 image cropped to its wide middle band is 2:1 on a hat -> 113.5
  expect(placement.fitTargetWidthMm({ w: 1000, h: 1000 }, { x0: 0, y0: 0.25, x1: 1, y1: 0.75 }, hat)).toBe(113.5);
  // full back is 304.8 square but auto-fit caps to the 8x8 hoop minus a mm a side: 198
  expect(placement.fitTargetWidthMm({ w: 500, h: 500 }, null, { garmentId: "full_back" })).toBe(198);
  // the tee's upper back is 254 x 76.2: a 4:1 banner is height-bound at 304.8, hoop-capped to 198
  expect(placement.fitTargetWidthMm({ w: 4000, h: 1000 }, null, { garmentId: "full_back", placementId: "upper_back" })).toBe(198);
  // nothing to fit
  expect(placement.fitTargetWidthMm(null, null, hat)).toBeNull();
  expect(placement.fitTargetWidthMm({ w: 0, h: 10 }, null, hat)).toBeNull();
  expect(placement.fitTargetWidthMm({ w: 10, h: 10 }, null, { garmentId: "no_such" })).toBeNull();
});

test("refitDigitized moves un-typed digitized widths to the new placement and leaves the rest", () => {
  const el = (id, extra) => ({ id, type: "digitized", sourcePx: { w: 1400, h: 316 }, crop: null, params: { target_width_mm: 80 }, ...extra });
  const project = {
    garmentId: "hat_front", placementId: "hat_rear",
    elements: [
      el("fit"),
      el("typed", { widthTyped: true }),
      el("legacy", { sourcePx: null }),
      { id: "text", type: "text", text: "hi" },
    ],
  };
  const out = placement.refitDigitized(project);
  const by = Object.fromEntries(out.elements.map((e) => [e.id, e]));
  expect(by.fit.params.target_width_mm).toBe(88.9); // the rear's width, the banner is width-bound
  expect(by.typed.params.target_width_mm).toBe(80);
  expect(by.legacy.params.target_width_mm).toBe(80);
  expect(by.text).toBe(project.elements[3]);
  // nothing to change returns the same object (no spurious persist/stale)
  expect(placement.refitDigitized(out)).toBe(out);
  expect(placement.refitDigitized(null)).toBeNull();
});
