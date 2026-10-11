// A hand-drawn satin column's rails, derived from its spine and drawn width.
// The engine cannot tell good rails from bad ones — opposite-direction rails
// sew a bow-tie, coincident rails sew nothing — so the correspondence is
// pinned HERE: rail A's i-th point and rail B's i-th point are the two ends
// of the cross at the spine's i-th point.
import { describe, expect, test } from "vitest";
import { railsFromSpine } from "./spineRails.js";
import { flattenShape } from "./manualShapes.js";

const area = (ring) => {
  let a = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += ring[j].x * ring[i].y - ring[i].x * ring[j].y;
  return Math.abs(a) / 2;
};
const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);

// The guard the engine does not have. Midpoint: exact everywhere, clamped
// miters included — a clamp shortens BOTH offsets equally, so the cross stays
// centred on the spine. Side: the cross of the local tangent (the chord
// through the neighbouring spine points) with (railA[i] - spine[i]) keeps one
// sign from end to end.
function expectCorresponding(spine, rails) {
  expect(rails.railA).toHaveLength(spine.length);
  expect(rails.railB).toHaveLength(spine.length);
  let sign = 0;
  for (let i = 0; i < spine.length; i++) {
    const a = rails.railA[i], b = rails.railB[i], s = spine[i];
    expect(Math.abs((a.x + b.x) / 2 - s.x)).toBeLessThan(1e-9);
    expect(Math.abs((a.y + b.y) / 2 - s.y)).toBeLessThan(1e-9);
    const prev = spine[Math.max(0, i - 1)], next = spine[Math.min(spine.length - 1, i + 1)];
    const cross = (next.x - prev.x) * (a.y - s.y) - (next.y - prev.y) * (a.x - s.x);
    expect(Math.abs(cross)).toBeGreaterThan(1e-9);
    if (sign === 0) sign = Math.sign(cross);
    expect(Math.sign(cross)).toBe(sign);
  }
}

describe("railsFromSpine", () => {
  test("a straight spine: rails exactly the width apart, two points each, same direction, ring area = length x width", () => {
    const spine = [{ x: 50, y: 100 }, { x: 350, y: 100 }];
    const r = railsFromSpine(spine, 24);
    expect(r.railA).toHaveLength(2);
    expect(r.railB).toHaveLength(2);
    expect(dist(r.railA[0], r.railB[0])).toBeCloseTo(24, 9);
    expect(dist(r.railA[1], r.railB[1])).toBeCloseTo(24, 9);
    // same direction: both rails run +x, like the spine
    expect(r.railA[1].x - r.railA[0].x).toBeCloseTo(300, 9);
    expect(r.railB[1].x - r.railB[0].x).toBeCloseTo(300, 9);
    expect(r.railA[0].y).toBeCloseTo(r.railA[1].y, 9);
    expect(r.ring).toHaveLength(4);
    expect(area(r.ring)).toBeCloseTo(7200, 6);
    expect(r.ring).toEqual(r.railA.concat(r.railB.slice().reverse()));
    expectCorresponding(spine, r);
  });

  test("a right-angle spine: the corner is a true miter (h x sqrt 2), inside the 2x clamp", () => {
    const spine = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }];
    const r = railsFromSpine(spine, 24);
    expect(dist(r.railA[1], spine[1])).toBeCloseTo(12 * Math.SQRT2, 9);
    for (let i = 0; i < spine.length; i++) {
      expect(dist(r.railA[i], spine[i])).toBeLessThanOrEqual(24 + 1e-9);
      expect(dist(r.railB[i], spine[i])).toBeLessThanOrEqual(24 + 1e-9);
    }
    expectCorresponding(spine, r);
  });

  test("a sharp corner: the miter is clamped to 2x the half-width, and the cross stays centred on the spine", () => {
    // 160 degree turn: an unclamped miter would be 12 / cos(80 deg) = 69 px
    const back = { x: 100 - 100 * Math.cos(Math.PI / 9), y: 100 * Math.sin(Math.PI / 9) };
    const spine = [{ x: 0, y: 0 }, { x: 100, y: 0 }, back];
    const r = railsFromSpine(spine, 24);
    expect(dist(r.railA[1], spine[1])).toBeCloseTo(24, 9);
    expect(dist(r.railB[1], spine[1])).toBeCloseTo(24, 9);
    expectCorresponding(spine, r);
  });

  test("a curved (flattened quadratic) spine: rails carry the spine's point count, in its order", () => {
    const spine = flattenShape([{ x: 100, y: 300 }, { x: 300, y: 300 }, { x: 500, y: 300 }], { 0: { x: 200, y: 180 } }, false);
    expect(spine.length).toBeGreaterThan(5);
    const r = railsFromSpine(spine, 24);
    expectCorresponding(spine, r);
    expect(r.ring).toHaveLength(spine.length * 2);
  });

  test("a full reversal (the spine doubles straight back) still emits finite, centred rails", () => {
    const spine = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 0, y: 0.0000001 }];
    const r = railsFromSpine([{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 20, y: 0 }], 24);
    for (const p of r.ring) { expect(Number.isFinite(p.x)).toBe(true); expect(Number.isFinite(p.y)).toBe(true); }
    expect(railsFromSpine(spine, 24).railA).toHaveLength(3);
  });

  test("coincident consecutive points are dropped, not turned into a zero-length cross", () => {
    const r = railsFromSpine([{ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 0 }], 24);
    expect(r.railA).toHaveLength(2);
    expect(r.railB).toHaveLength(2);
  });

  test("null when there is nothing to offset", () => {
    expect(railsFromSpine([{ x: 0, y: 0 }, { x: 100, y: 0 }], 0)).toBeNull();
    expect(railsFromSpine([{ x: 0, y: 0 }, { x: 100, y: 0 }], -3)).toBeNull();
    expect(railsFromSpine([{ x: 0, y: 0 }, { x: 100, y: 0 }], NaN)).toBeNull();
    expect(railsFromSpine([{ x: 0, y: 0 }, { x: 100, y: 0 }], undefined)).toBeNull();
    expect(railsFromSpine([{ x: 5, y: 5 }], 24)).toBeNull();
    expect(railsFromSpine([{ x: 5, y: 5 }, { x: 5, y: 5 }], 24)).toBeNull();
    expect(railsFromSpine([], 24)).toBeNull();
    expect(railsFromSpine(null, 24)).toBeNull();
  });
});
