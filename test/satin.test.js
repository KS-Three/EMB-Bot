const assert = require("node:assert");
const { test } = require("node:test");
const satin = require("../src/satin.js");

// Long thin rectangle: 120 long, 12 wide. Closed ring (pixel coords).
const rect = [{ x: 0, y: 0 }, { x: 120, y: 0 }, { x: 120, y: 12 }, { x: 0, y: 12 }];

// ---- unchanged helper tests -------------------------------------------------

test("estimateWidthMm of a 120x12 rect ~1.1mm", () => {
  // area 1440, perimeter 264 -> 2*1440/264 = 10.909px -> /10 = 1.0909mm
  const w = satin.estimateWidthMm(rect, 10);
  assert.ok(Math.abs(w - 1.1) <= 0.4, `expected ~1.1mm, got ${w}`);
});

test("farthestBoundaryPair returns opposite ends of the rect", () => {
  const [i, j] = satin.farthestBoundaryPair(rect);
  const a = rect[i], b = rect[j];
  const d = Math.hypot(a.x - b.x, a.y - b.y); // ~sqrt(120^2+12^2)=120.6
  assert.ok(d > 118, `expected far pair distance > 118, got ${d}`);
});

test("chainLength sums euclidean segments", () => {
  const L = satin.chainLength([{ x: 0, y: 0 }, { x: 3, y: 4 }, { x: 3, y: 14 }]);
  assert.ok(Math.abs(L - 15) < 1e-9, `expected 15, got ${L}`); // 5 + 10
});

test("splitBoundary walks i->j and j->i sharing endpoints", () => {
  const [A, B] = satin.splitBoundary(rect, 0, 2);
  assert.deepStrictEqual(A, [{ x: 0, y: 0 }, { x: 120, y: 0 }, { x: 120, y: 12 }]);
  assert.deepStrictEqual(B, [{ x: 120, y: 12 }, { x: 0, y: 12 }, { x: 0, y: 0 }]);
});

test("resampleChain gives evenly arc-spaced points incl. endpoints", () => {
  const out = satin.resampleChain([{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }], 3);
  assert.strictEqual(out.length, 3);
  assert.ok(Math.abs(out[0].x - 0) < 1e-9 && Math.abs(out[0].y - 0) < 1e-9, "first endpoint");
  assert.ok(Math.abs(out[2].x - 10) < 1e-9 && Math.abs(out[2].y - 10) < 1e-9, "last endpoint");
  // total length 20 -> midpoint at arc-length 10 sits exactly on the corner (10,0)
  assert.ok(Math.abs(out[1].x - 10) <= 0.5 && Math.abs(out[1].y - 0) <= 0.5,
    `middle should be ~(10,0), got (${out[1].x},${out[1].y})`);
});

// ---- new perpendicular-satin geometry --------------------------------------
//
// satinColumn now emits a zig-zag whose consecutive point pairs are the
// cross-stitches. The crosses come in pairs but the leading edge alternates
// (even station: A->B, odd station: B->A) so a cross is NOT always pts[2k]->
// pts[2k+1]. To test geometry robustly we reconstruct crosses as the pairs
// that span the width: for a zig-zag path emitted as
//   a0,b0, b1,a1, a2,b2, b3,a3, ...
// the width-spanning segments are (a0,b0),(b1,a1),(a2,b2),... i.e. pairs
// (pts[2k], pts[2k+1]). The connectors are pts[2k+1]->pts[2k+2] (same side,
// short). So crosses = even-indexed pairs.
function crosses(pts) {
  const out = [];
  for (let k = 0; k + 1 < pts.length; k += 2) {
    out.push([pts[k], pts[k + 1]]);
  }
  return out;
}

test("straight uniform bar: every cross is ~vertical, length ~= width", () => {
  const bar = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 20 }, { x: 0, y: 20 }];
  const pts = satin.satinColumn(bar, { spacingMm: 2, pxPerMm: 4 });
  assert.ok(pts.length >= 12, `expected several crosses, got ${pts.length} pts`);
  const cs = crosses(pts);
  for (const [a, b] of cs) {
    const dx = Math.abs(b.x - a.x), dy = Math.abs(b.y - a.y);
    assert.ok(dx < 0.25 * dy + 1e-6, `cross should be ~vertical, got dx=${dx} dy=${dy}`);
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    assert.ok(Math.abs(len - 20) <= 2, `cross length ~=20, got ${len}`);
  }
});

test("satin slantDeg leans the crosses off perpendicular", () => {
  const bar = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 20 }, { x: 0, y: 20 }];
  const meanAngleFromVertical = (pts) => {
    const cs = crosses(pts);
    let s = 0, n = 0;
    for (const [a, b] of cs) { s += Math.atan2(Math.abs(b.x - a.x), Math.abs(b.y - a.y)); n++; }
    return n ? (s / n) * 180 / Math.PI : 0; // 0 == vertical (perpendicular to the bar)
  };
  const upright = meanAngleFromVertical(satin.satinColumn(bar, { spacingMm: 2, pxPerMm: 4 }));
  const slanted = meanAngleFromVertical(satin.satinColumn(bar, { spacingMm: 2, pxPerMm: 4, slantDeg: 30 }));
  assert.ok(upright < 8, `upright crosses ~vertical, got ${upright.toFixed(1)}deg`);
  assert.ok(slanted > 18 && slanted < 42, `slanted crosses ~30deg off vertical, got ${slanted.toFixed(1)}deg`);
});

test("tapered bar: crosses are perpendicular to the local centerline tangent", () => {
  const taper = [{ x: 40, y: 190 }, { x: 360, y: 150 }, { x: 362, y: 175 }, { x: 42, y: 215 }];
  const pts = satin.satinColumn(taper, { spacingMm: 2, pxPerMm: 4 });
  const cs = crosses(pts);
  assert.ok(cs.length >= 4, `expected crosses, got ${cs.length}`);
  // Local centerline tangent from consecutive cross MIDPOINTS.
  const mids = cs.map(([a, b]) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }));
  let good = 0, total = 0;
  for (let k = 0; k < cs.length; k++) {
    const prev = mids[Math.max(0, k - 1)];
    const next = mids[Math.min(mids.length - 1, k + 1)];
    const tx = next.x - prev.x, ty = next.y - prev.y;
    const tl = Math.hypot(tx, ty);
    if (tl < 1e-6) continue;
    const [a, b] = cs[k];
    const cx = b.x - a.x, cy = b.y - a.y;
    const cl = Math.hypot(cx, cy);
    if (cl < 1e-6) continue;
    total++;
    const cosang = Math.abs((cx * tx + cy * ty) / (cl * tl));
    if (cosang < 0.2) good++; // within ~11.5deg of perpendicular
  }
  assert.ok(good >= 0.9 * total, `>=90% crosses perpendicular, got ${good}/${total}`);
});

test("arc C band: crosses are ~radial (within ~15deg) including the ends", () => {
  const cx = 200, cy = 200, r0 = 120, r1 = 150, a0 = Math.PI * 0.35, a1 = Math.PI * 1.65, steps = 60;
  const ring = [];
  for (let k = 0; k <= steps; k++) { const a = a0 + (a1 - a0) * k / steps; ring.push({ x: cx + r1 * Math.cos(a), y: cy + r1 * Math.sin(a) }); }
  for (let k = 0; k <= steps; k++) { const a = a1 + (a0 - a1) * k / steps; ring.push({ x: cx + r0 * Math.cos(a), y: cy + r0 * Math.sin(a) }); }
  const pts = satin.satinColumn(ring, { spacingMm: 2.2, pxPerMm: 4 });
  const cs = crosses(pts);
  assert.ok(cs.length >= 8, `expected many crosses, got ${cs.length}`);
  let good = 0;
  for (const [a, b] of cs) {
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const rx = mx - cx, ry = my - cy;            // radial direction at the station
    const rl = Math.hypot(rx, ry);
    const dx = b.x - a.x, dy = b.y - a.y;         // cross direction
    const dl = Math.hypot(dx, dy);
    if (rl < 1e-6 || dl < 1e-6) continue;
    const cosang = Math.abs((rx * dx + ry * dy) / (rl * dl));
    if (cosang > Math.cos(15 * Math.PI / 180)) good++; // within 15deg of radial
  }
  assert.ok(good >= 0.85 * cs.length, `>=85% crosses radial, got ${good}/${cs.length}`);
});

test("coverage: cross endpoints land on the two rails", () => {
  const taper = [{ x: 40, y: 190 }, { x: 360, y: 150 }, { x: 362, y: 175 }, { x: 42, y: 215 }];
  const [i, j] = satin.farthestBoundaryPair(taper);
  const [A, B] = satin.splitBoundary(taper, i, j);
  const distToChain = (p, chain) => {
    let bd = Infinity;
    for (let k = 0; k + 1 < chain.length; k++) {
      const a = chain[k], b = chain[k + 1];
      const ex = b.x - a.x, ey = b.y - a.y;
      const L2 = ex * ex + ey * ey;
      let u = L2 > 1e-12 ? ((p.x - a.x) * ex + (p.y - a.y) * ey) / L2 : 0;
      u = Math.max(0, Math.min(1, u));
      const qx = a.x + ex * u, qy = a.y + ey * u;
      bd = Math.min(bd, Math.hypot(p.x - qx, p.y - qy));
    }
    return bd;
  };
  const pts = satin.satinColumn(taper, { spacingMm: 2, pxPerMm: 4 });
  const cs = crosses(pts);
  for (const [a, b] of cs) {
    // each cross endpoint lies on one rail or the other (within ~2px)
    const aOnA = distToChain(a, A), aOnB = distToChain(a, B);
    const bOnA = distToChain(b, A), bOnB = distToChain(b, B);
    assert.ok(Math.min(aOnA, aOnB) <= 2, `cross start off rails: ${Math.min(aOnA, aOnB)}`);
    assert.ok(Math.min(bOnA, bOnB) <= 2, `cross end off rails: ${Math.min(bOnA, bOnB)}`);
  }
});

test("pull compensation widens the crosses", () => {
  const bar = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 20 }, { x: 0, y: 20 }];
  const meanLen = (pts) => {
    const cs = crosses(pts);
    let s = 0;
    for (const [a, b] of cs) s += Math.hypot(b.x - a.x, b.y - a.y);
    return cs.length ? s / cs.length : 0;
  };
  const base = satin.satinColumn(bar, { spacingMm: 2, pxPerMm: 4, pullCompMm: 0 });
  const comp = satin.satinColumn(bar, { spacingMm: 2, pxPerMm: 4, pullCompMm: 1 });
  assert.ok(meanLen(comp) > meanLen(base) + 1,
    `expected wider crosses with pull comp, base=${meanLen(base)} comp=${meanLen(comp)}`);
});

test("degenerate rings (n<3) return [] without crashing", () => {
  assert.deepStrictEqual(satin.satinColumn([], { spacingMm: 2, pxPerMm: 10 }), []);
  assert.deepStrictEqual(satin.satinColumn([{ x: 0, y: 0 }, { x: 1, y: 1 }], { spacingMm: 2, pxPerMm: 10 }), []);
});

test("a nearly-square ring still produces a valid finite column", () => {
  const nearSquare = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 98 }, { x: 0, y: 98 }];
  const pts = satin.satinColumn(nearSquare, { spacingMm: 3, pxPerMm: 10 });
  assert.ok(pts.length >= 4, `expected some stitches, got ${pts.length}`);
  assert.ok(pts.every(p => Number.isFinite(p.x) && Number.isFinite(p.y)), "all finite");
});
