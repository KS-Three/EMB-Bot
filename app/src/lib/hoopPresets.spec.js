import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";

// Cross-checks the Studio's HOOPS presets against their labels and against the
// digitizer's hoop constants (digitizer_core/preflight.py FACE_MIN_HOOP_MM /
// FACE_BLOCK_HOOP_MM). Presets are NOMINAL embroidery fields (Brother/Janome
// naming), not the label's inches converted — so the check is a tolerance band,
// not equality. Whether a nominal field matches a given machine is a physical
// question and is NOT settled here.
const IN_MM = 25.4;
// preflight.py: FACE_MIN_HOOP_MM = (127.0, 178.0) (5x7"), FACE_BLOCK_HOOP_MM = 101.6 (4x4")
const DIGITIZER_5X7_MM = [127.0, 178.0];
const DIGITIZER_4X4_MM = 101.6;

let HOOPS;
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  require("../../../src/units.js");
  require("../../../src/garments.js");
  HOOPS = globalThis.EMB.HOOPS;
});

test("every preset's id and label name the same inch size", () => {
  for (const h of HOOPS) {
    const m = /^(\d+)×(\d+) in$/.exec(h.label);
    expect(m, h.label).not.toBeNull();
    expect(h.id).toBe(`${m[1]}x${m[2]}`);
  }
});

test("each field is within 10% of its label's inches (portrait w<=h, nominal field)", () => {
  for (const h of HOOPS) {
    const [a, b] = h.id.split("x").map(Number);
    const [lo, hi] = [Math.min(a, b) * IN_MM, Math.max(a, b) * IN_MM];
    expect(h.widthMm).toBeLessThanOrEqual(h.heightMm);
    expect(Math.abs(h.widthMm - lo) / lo, `${h.id} width`).toBeLessThan(0.1);
    expect(Math.abs(h.heightMm - hi) / hi, `${h.id} height`).toBeLessThan(0.1);
  }
});

test("presets are non-decreasing by area (suggestHoop takes the first fit) and unique by id", () => {
  // 6x10 (160x250) and 8x8 (200x200) tie at 40000 mm2 — order between them is
  // the preference order, so non-decreasing, not strict.
  const areas = HOOPS.map((h) => h.widthMm * h.heightMm);
  expect([...areas].sort((x, y) => x - y)).toEqual(areas);
  expect(new Set(HOOPS.map((h) => h.id)).size).toBe(HOOPS.length);
});

test("5x7 and 4x4 agree with the digitizer's face-guard hoops (within 3 mm, inclusive)", () => {
  const h57 = HOOPS.find((h) => h.id === "5x7");
  const h44 = HOOPS.find((h) => h.id === "4x4");
  expect(Math.abs(h57.widthMm - DIGITIZER_5X7_MM[0])).toBeLessThanOrEqual(3);
  expect(Math.abs(h57.heightMm - DIGITIZER_5X7_MM[1])).toBeLessThanOrEqual(3);
  expect(Math.abs(h44.widthMm - DIGITIZER_4X4_MM)).toBeLessThanOrEqual(3);
  expect(Math.abs(h44.heightMm - DIGITIZER_4X4_MM)).toBeLessThanOrEqual(3);
});

test("largest preset equals the engine's 200 mm typical-hoop ceiling", () => {
  const big = HOOPS[HOOPS.length - 1];
  expect([big.widthMm, big.heightMm]).toEqual([200, 200]);
  expect(globalThis.EMB.exceedsHoop(200, 200)).toBe(false);
  expect(globalThis.EMB.exceedsHoop(201, 200)).toBe(true);
});
