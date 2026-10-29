// "Apply to all similar shapes" — which shapes of a digitized design count as
// SIMILAR to the selected one, and the one patch that edits them all.
// The fixture is a flag: a blue canton, 13 stripes (7 red, 6 white) and 50
// white stars, every star jittered, turned and scaled a little the way a
// raster trace leaves them. The point of the definition is that the stars
// match each other and nothing else — in particular not the WHITE stripes,
// which share the stars' colour, and not the canton.
import { describe, expect, test } from "vitest";
import {
  shapeSignature, similarShapeIds, similarOverridesPatch, SIMILAR_TOLERANCE,
} from "./similarShapes.js";
import { popoverModel } from "./shapePopover.js";

// Deterministic noise (mulberry32) so a failure is reproducible.
function rng(seed) {
  let a = seed;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function star(cx, cy, r, rotRad, rand, jitter = 0.03) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const rad = (i % 2 === 0 ? r : r * 0.382) * (1 + (rand() - 0.5) * 2 * jitter);
    const a = rotRad + (i * Math.PI) / 5;
    pts.push([cx + rad * Math.sin(a), cy - rad * Math.cos(a)]);
  }
  return pts;
}
const rect = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

const RED = [178, 34, 52];
const WHITE = [255, 255, 255];
const BLUE = [60, 59, 110];

// 80 x 43 mm, service space (centre origin, y down).
function flagElement() {
  const rand = rng(7);
  const shapes = [];
  const add = (id, ring, rgb, threadNumber) =>
    shapes.push({ id, outlineFull: ring, rgb, threadNumber, areaMm2: 1, tier: "fill", stitched: true });
  const stripeH = 43 / 13;
  for (let i = 0; i < 13; i++) {
    const y0 = -21.5 + i * stripeH;
    add("stripe" + i, rect(-40, y0, 40, y0 + stripeH), i % 2 ? WHITE : RED, i % 2 ? "1002" : "1921");
  }
  add("canton", rect(-40, -21.5, -8, -21.5 + 7 * stripeH), BLUE, "3544");
  let n = 0;
  for (let row = 0; row < 9; row++) {
    const cols = row % 2 ? 5 : 6;
    for (let c = 0; c < cols; c++) {
      const cx = -37 + (row % 2 ? 2.7 : 0) + c * 5.4;
      const cy = -19 + row * 3.1;
      add("star" + n++, star(cx, cy, 1.3 * (1 + (rand() - 0.5) * 0.12), rand() * 0.6 - 0.3, rand), WHITE, "1002");
    }
  }
  return { id: 1, type: "digitized", params: { border: null }, review: { brandId: "isacord", shapes }, shapeOverrides: {}, deletedShapeIds: [] };
}
const starIds = (el) => el.review.shapes.filter((s) => s.id.startsWith("star")).map((s) => s.id);

describe("shapeSignature", () => {
  test("is the same for a shape, the same shape scaled, and the same shape turned", () => {
    const base = star(0, 0, 2, 0, () => 0.5);
    const big = star(10, 10, 4, 0, () => 0.5);
    const turned = star(0, 0, 2, 0.7, () => 0.5);
    const a = shapeSignature(base), b = shapeSignature(big), c = shapeSignature(turned);
    for (const k of ["phi1", "phi2", "compactness", "solidity"]) {
      expect(b[k]).toBeCloseTo(a[k], 6);
      expect(c[k]).toBeCloseTo(a[k], 6);
    }
    expect(b.area / a.area).toBeCloseTo(4, 6);
  });

  test("a star is not compact and not convex; a square is both", () => {
    const s = shapeSignature(star(0, 0, 2, 0, () => 0.5));
    const q = shapeSignature(rect(0, 0, 4, 4));
    expect(q.solidity).toBeCloseTo(1, 6);
    expect(s.solidity).toBeLessThan(0.7);
    expect(s.compactness).toBeGreaterThan(q.compactness);
  });

  test("winding does not matter, and a degenerate ring has no signature", () => {
    const ring = star(0, 0, 2, 0, () => 0.5);
    expect(shapeSignature([...ring].reverse()).area).toBeCloseTo(shapeSignature(ring).area, 9);
    expect(shapeSignature([[0, 0], [1, 1]])).toBeNull();
    expect(shapeSignature([[0, 0], [1, 1], [2, 2]])).toBeNull();
  });
});

describe("similarShapeIds — the flag", () => {
  const el = flagElement();

  test("a star matches all 50 stars and nothing else", () => {
    const ids = similarShapeIds(el, "star0");
    expect(ids).toHaveLength(50);
    expect(new Set(ids)).toEqual(new Set(starIds(el)));
  });

  test("the answer is the same whichever star is selected", () => {
    for (const id of ["star7", "star23", "star49"]) {
      expect(new Set(similarShapeIds(el, id))).toEqual(new Set(starIds(el)));
    }
  });

  test("a white stripe matches the other white stripes — not the stars of the same colour", () => {
    const ids = similarShapeIds(el, "stripe1");
    expect(ids.sort()).toEqual(["stripe1", "stripe11", "stripe3", "stripe5", "stripe7", "stripe9"].sort());
  });

  test("the red stripes are 7, and the canton stands alone", () => {
    expect(similarShapeIds(el, "stripe0")).toHaveLength(7);
    expect(similarShapeIds(el, "canton")).toEqual(["canton"]);
  });

  test("the selected shape is always in its own answer, first", () => {
    expect(similarShapeIds(el, "star9")[0]).toBe("star9");
    expect(similarShapeIds(el, "nope")).toEqual([]);
  });

  test("a star that was recoloured, deleted or switched off is not swept up", () => {
    const e2 = {
      ...el,
      shapeOverrides: { star3: { rgb: [10, 10, 10], thread_index: 4 } },
      deletedShapeIds: ["star4"],
      review: { ...el.review, shapes: el.review.shapes.map((s) => (s.id === "star5" ? { ...s, stitched: false } : s)) },
    };
    const ids = similarShapeIds(e2, "star0");
    expect(ids).toHaveLength(47);
    for (const gone of ["star3", "star4", "star5"]) expect(ids).not.toContain(gone);
  });

  test("a star twice the area still matches (scale tolerant); five times does not", () => {
    const rand = () => 0.5;
    const mk = (id, r) => ({ id, outlineFull: star(0, 0, r, 0, rand), rgb: WHITE, threadNumber: "1002", stitched: true });
    const e2 = { ...el, review: { ...el.review, shapes: [mk("a", 1.3), mk("b", 1.3 * Math.SQRT2 * 0.9), mk("c", 1.3 * 2.3)] } };
    expect(similarShapeIds(e2, "a")).toEqual(["a", "b"]);
  });

  test("tolerance is exported so the claim in the docs is the number in the code", () => {
    expect(SIMILAR_TOLERANCE.areaRatio).toBeGreaterThan(1);
  });
});

describe("similarOverridesPatch — one patch for the lot", () => {
  const el = flagElement();
  const ids = similarShapeIds(el, "star0");

  test("Fill on every star is ONE shapeOverrides patch touching only the stars", () => {
    const patch = similarOverridesPatch(el, ids, "stitchType", "fill");
    const keys = Object.keys(patch.shapeOverrides);
    expect(new Set(keys)).toEqual(new Set(starIds(el)));
    for (const k of keys) expect(patch.shapeOverrides[k]).toEqual({ tier: "fill" });
    expect(Object.keys(patch)).toEqual(["shapeOverrides"]);
  });

  test("it keeps what a star already had, and Auto clears just that field", () => {
    const withBorder = { ...el, shapeOverrides: { star1: { border: "bean", tier: "satin" }, canton: { tier: "run" } } };
    const filled = similarOverridesPatch(withBorder, ids, "stitchType", "fill");
    expect(filled.shapeOverrides.star1).toEqual({ border: "bean", tier: "fill" });
    expect(filled.shapeOverrides.canton).toEqual({ tier: "run" });
    const auto = similarOverridesPatch(withBorder, ids, "stitchType", "auto");
    expect(auto.shapeOverrides.star1).toEqual({ border: "bean" });
    expect(auto.shapeOverrides.star2).toBeUndefined();
  });

  test("border goes through the same path, as the popover's own patch for each shape", () => {
    const patch = similarOverridesPatch(el, ids, "border", "off");
    expect(patch.shapeOverrides.star8).toEqual({ border: "off" });
    expect(similarOverridesPatch(el, ids, "border", "default").shapeOverrides.star8).toBeUndefined();
  });

  test("Delete is never applied to a group", () => {
    expect(similarOverridesPatch(el, ids, "delete")).toBeNull();
    expect(similarOverridesPatch(el, ids, "editPoints")).toBeNull();
  });

  test("a colour pick is a per-shape thread override applied to every id", () => {
    const patch = similarOverridesPatch(el, ids, "recolor", { thread_index: 12, rgb: [1, 2, 3] });
    expect(patch.shapeOverrides.star2).toEqual({ thread_index: 12, rgb: [1, 2, 3] });
    expect(patch.shapeOverrides.canton).toBeUndefined();
  });
});

describe("the popover model offers the choice only when there is something to apply to", () => {
  const el = flagElement();
  test("carries the match count and ids on a digitized shape with company", () => {
    const m = popoverModel({ element: el, shapeId: "star0", similar: similarShapeIds(el, "star0") });
    expect(m.similar.count).toBe(50);
    expect(m.similar.ids).toHaveLength(50);
  });
  test("is absent for a shape that stands alone, and for the other lanes", () => {
    expect(popoverModel({ element: el, shapeId: "canton", similar: ["canton"] }).similar).toBeNull();
    expect(popoverModel({ element: el, shapeId: "canton" }).similar).toBeNull();
  });
});
