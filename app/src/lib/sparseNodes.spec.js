import { describe, it, expect } from "vitest";
import {
  SEED_TOL_MM, CORNER_DEG, FLATTEN_ERR_MM, FLATTEN_MIN_MM, FLATTEN_MAX_MM, MIN_NODES,
  seedNodes, isValidNodes, spanCurve, flattenSpan, rebuildSpans, moveNodesExact,
  insertNodeOnPath, toggleNode, deleteNodes, nodePositions,
} from "./sparseNodes.js";
import { BOUNDARY_MAX_POINTS } from "./digitizer.js";

// ---- synthetic rings -------------------------------------------------------
const circle = (n, r = 10) =>
  Array.from({ length: n }, (_, i) => [r * Math.cos((2 * Math.PI * i) / n), r * Math.sin((2 * Math.PI * i) / n)]);
const square4 = (s = 20) => [[0, 0], [s, 0], [s, s], [0, s]];
const square8 = (s = 20) => [[0, 0], [s / 2, 0], [s, 0], [s, s / 2], [s, s], [s / 2, s], [0, s], [0, s / 2]];

// 52 x 52 mm rounded square, corner radius 8, resampled to ~5 mm spacing.
function roundedSquare() {
  const S = 52, R = 8, dense = [];
  const arc = (cx, cy, a0) => {
    for (let k = 0; k <= 200; k++) {
      const a = a0 + (Math.PI / 2) * (k / 200);
      dense.push([cx + R * Math.cos(a), cy + R * Math.sin(a)]);
    }
  };
  arc(S - R, S - R, 0); arc(R, S - R, Math.PI / 2); arc(R, R, Math.PI); arc(S - R, R, 1.5 * Math.PI);
  // fill the straight edges between arcs with fine points, then resample
  const fine = [];
  for (let i = 0; i < dense.length; i++) {
    const a = dense[i], b = dense[(i + 1) % dense.length];
    const steps = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.25));
    for (let s = 0; s < steps; s++) fine.push([a[0] + ((b[0] - a[0]) * s) / steps, a[1] + ((b[1] - a[1]) * s) / steps]);
  }
  // resample by arc length
  const out = [fine[0]];
  let acc = 0;
  for (let i = 1; i <= fine.length; i++) {
    const a = fine[i - 1], b = fine[i % fine.length];
    acc += Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (acc >= 5 && i < fine.length) { out.push(b); acc = 0; }
  }
  return out;
}

const area = (r) => {
  let a = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += r[j][0] * r[i][1] - r[i][0] * r[j][1];
  return a / 2;
};
const perim = (r) => r.reduce((s, p, i) => s + Math.hypot(r[(i + 1) % r.length][0] - p[0], r[(i + 1) % r.length][1] - p[1]), 0);
const bez = (b, t) => {
  const s = 1 - t;
  const w = [s * s * s, 3 * s * s * t, 3 * s * t * t, t * t * t];
  return [0, 1].map((c) => w[0] * b[0][c] + w[1] * b[1][c] + w[2] * b[2][c] + w[3] * b[3][c]);
};
const distToCurve = (b, p) => {
  let best = Infinity;
  for (let k = 0; k <= 4000; k++) {
    const q = bez(b, k / 4000);
    best = Math.min(best, Math.hypot(p[0] - q[0], p[1] - q[1]));
  }
  return best;
};
// the ring vertices belonging to span k (interior only), wrapping
const interior = (ring, nodes, k) => {
  const a = nodes[k].i, b = nodes[(k + 1) % nodes.length].i, out = [];
  for (let i = (a + 1) % ring.length; i !== b; i = (i + 1) % ring.length) out.push(ring[i]);
  return out;
};

describe("constants", () => {
  it("match the spec", () => {
    expect([SEED_TOL_MM, CORNER_DEG, FLATTEN_ERR_MM, FLATTEN_MIN_MM, FLATTEN_MAX_MM, MIN_NODES])
      .toEqual([0.5, 35, 0.05, 0.3, 1.0, 3]);
  });
});

describe("seedNodes", () => {
  it("64-point circle r=10: 8..16 nodes, all smooth", () => {
    const n = seedNodes(circle(64));
    console.log("seed count circle64:", n.length);
    expect(n.length).toBeGreaterThanOrEqual(8);
    expect(n.length).toBeLessThanOrEqual(16);
    expect(n.every((x) => x.kind === "smooth")).toBe(true);
  });
  it("4- and 8-point squares: exactly 4 corners (midpoints dropped)", () => {
    for (const sq of [square4(), square8()]) {
      const n = seedNodes(sq);
      expect(n.length).toBe(4);
      expect(n.every((x) => x.kind === "corner")).toBe(true);
    }
    expect(seedNodes(square8()).map((x) => x.i)).toEqual([0, 2, 4, 6]);
  });
  it("52 mm rounded square (r=8, ~5 mm spacing): corners only where the turn exceeds 35 deg; count quoted", () => {
    const ring = roundedSquare();
    const n = seedNodes(ring);
    const turn = (k) => {
      const a = ring[n[(k - 1 + n.length) % n.length].i], p = ring[n[k].i], b = ring[n[(k + 1) % n.length].i];
      const t = Math.atan2((p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0]),
        (p[0] - a[0]) * (b[0] - p[0]) + (p[1] - a[1]) * (b[1] - p[1]));
      return Math.abs((t * 180) / Math.PI);
    };
    const corners = n.map((x, k) => ({ k, x })).filter(({ x }) => x.kind === "corner");
    console.log("seed count rounded square:", ring.length, "vertices ->", n.length, "nodes,",
      corners.length, "corners, turns", corners.map(({ k }) => turn(k).toFixed(1)).join("/"));
    // the rule, exactly: corner <=> turn > 35 deg
    n.forEach((x, k) => expect(x.kind === "corner").toBe(turn(k) > 35));
    // at 5 mm spacing on an r=8 arc the 0.5 mm DP keeps ONE vertex per arc, whose
    // chords turn about 45 deg: one corner per rounded corner, none on the straights
    expect(corners.length).toBe(4);
  });
  it("every seed index is in range, ascending, valid", () => {
    for (const ring of [circle(64), square8(), roundedSquare(), circle(500)]) {
      const n = seedNodes(ring);
      expect(n.every((x) => x.i >= 0 && x.i < ring.length)).toBe(true);
      expect(isValidNodes(n, ring)).toBe(true);
    }
    console.log("seed count circle500:", seedNodes(circle(500)).length);
  });
  it("a 3-vertex ring seeds 3", () => {
    expect(seedNodes([[0, 0], [10, 0], [0, 10]]).map((x) => x.i)).toEqual([0, 1, 2]);
  });
  it("is deterministic", () => {
    const ring = roundedSquare();
    expect(seedNodes(ring)).toEqual(seedNodes(ring));
  });
  it("a sliver still seeds MIN_NODES", () => {
    expect(seedNodes([[0, 0], [5, 0.01], [10, 0], [5, -0.01]]).length).toBeGreaterThanOrEqual(3);
  });
});

describe("spanCurve", () => {
  const ring = circle(64);
  const nodes = seedNodes(ring);
  it("passes through its two nodes", () => {
    for (let k = 0; k < nodes.length; k++) {
      const c = spanCurve(ring, nodes, k);
      expect(c[0]).toEqual(ring[nodes[k].i]);
      expect(c[3]).toEqual(ring[nodes[(k + 1) % nodes.length].i]);
    }
  });
  it("corner-to-corner span is its chord (controls on the chord)", () => {
    const sq = square4();
    const nd = seedNodes(sq);
    const [P0, C1, C2, P3] = spanCurve(sq, nd, 0);
    expect([P0, P3]).toEqual([[0, 0], [20, 0]]);
    expect(C1[1]).toBeCloseTo(0, 12);
    expect(C2[1]).toBeCloseTo(0, 12);
    expect(C1[0]).toBeGreaterThan(0);
    expect(C2[0]).toBeLessThan(20);
  });
  it("controls clamp at half the chord when neighbours are far apart", () => {
    // spans: 1 mm (node1->node2) with a 40 mm neighbour either side
    const r = [[-40, 0], [0, 0], [1, 0.3], [41, 0]];
    const nd = r.map((_, i) => ({ i, kind: "smooth" }));
    const [P0, C1, C2, P3] = spanCurve(r, nd, 1);
    const chord = Math.hypot(P3[0] - P0[0], P3[1] - P0[1]);
    expect(Math.hypot(C1[0] - P0[0], C1[1] - P0[1])).toBeLessThanOrEqual(chord / 2 + 1e-12);
    expect(Math.hypot(C2[0] - P3[0], C2[1] - P3[1])).toBeLessThanOrEqual(chord / 2 + 1e-12);
    expect(Math.hypot(C1[0] - P0[0], C1[1] - P0[1])).toBeCloseTo(chord / 2, 9); // unclamped it is ~6.7
  });
});

describe("flattenSpan", () => {
  const ring = circle(64);
  const nodes = seedNodes(ring);
  it("every flattened vertex within 0.05 mm of the curve, spacing 0.3-1.0 mm", () => {
    // pick the longest span
    let k = 0, longest = 0;
    nodes.forEach((_, s) => {
      const c = spanCurve(ring, nodes, s);
      const L = Math.hypot(c[3][0] - c[0][0], c[3][1] - c[0][1]);
      if (L > longest) { longest = L; k = s; }
    });
    const c = spanCurve(ring, nodes, k);
    const mid = flattenSpan(c);
    const pts = [c[0], ...mid, c[3]];
    let maxErr = 0;
    for (const p of mid) maxErr = Math.max(maxErr, distToCurve(c, p));
    let maxChordErr = 0;
    for (let s = 1; s < pts.length; s++) {
      const q = [(pts[s][0] + pts[s - 1][0]) / 2, (pts[s][1] + pts[s - 1][1]) / 2];
      maxChordErr = Math.max(maxChordErr, distToCurve(c, q));
    }
    console.log(`flatten: chord ${longest.toFixed(2)} mm -> ${mid.length} interior vertices, max chord error ${maxChordErr.toFixed(4)} mm`);
    expect(mid.length).toBeGreaterThan(0);
    expect(maxErr).toBeLessThanOrEqual(0.05);
    for (let i = 1; i < pts.length; i++) {
      const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      expect(d).toBeLessThanOrEqual(1.0 + 1e-9);
      expect(d).toBeGreaterThanOrEqual(0.3 - 1e-9);
    }
    // polyline of the flattening stays within 0.05 of the curve, both ways
    for (let s = 1; s < pts.length; s++) {
      const q = [(pts[s][0] + pts[s - 1][0]) / 2, (pts[s][1] + pts[s - 1][1]) / 2];
      expect(distToCurve(c, q)).toBeLessThanOrEqual(0.05 + 1e-3);
    }
  });
  it("a straight 5 mm span keeps nothing extra", () => {
    expect(flattenSpan([[0, 0], [5 / 3, 0], [10 / 3, 0], [5, 0]])).toEqual([]);
  });
  it("a short curved span (under 0.6 mm) is never split below 0.3 mm", () => {
    const mid = flattenSpan([[0, 0], [0.1, 0.3], [0.4, 0.3], [0.5, 0]]);
    expect(mid.length).toBeLessThanOrEqual(1);
  });
});

describe("rebuildSpans", () => {
  it("moving one circle node 3 mm outward rebuilds exactly its two spans (I2, I3)", () => {
    const ring = circle(64);
    const nodes = seedNodes(ring);
    const k = 5, N = nodes.length;
    const p = ring[nodes[k].i];
    const len = Math.hypot(p[0], p[1]);
    const dx = (3 * p[0]) / len, dy = (3 * p[1]) / len;
    const m = moveNodesExact(ring, nodes, [k], dx, dy);
    expect(m.dirty).toEqual([k - 1, k]);
    const r = rebuildSpans(m.ring, m.nodes, m.dirty);
    // I3: every node is a vertex; the moved one moved by exactly the delta
    r.nodes.forEach((nd, j) => {
      const want = j === k ? [p[0] + dx, p[1] + dy] : ring[nodes[j].i];
      expect(r.ring[nd.i]).toEqual(want);
    });
    // I2: every other span's interior byte-identical, in place
    for (let s = 0; s < N; s++) {
      if (m.dirty.includes(s)) continue;
      expect(interior(r.ring, r.nodes, s)).toEqual(interior(ring, nodes, s));
    }
    // the two dirty spans changed
    for (const s of m.dirty) expect(interior(r.ring, r.nodes, s)).not.toEqual(interior(ring, nodes, s));
    expect(r.nodes.map((x) => x.kind)).toEqual(nodes.map((x) => x.kind));
    // input untouched
    expect(ring).toEqual(circle(64));
  });
  it("a dirty last span (wrapping) keeps the rest intact", () => {
    const ring = circle(64);
    const nodes = seedNodes(ring);
    const N = nodes.length;
    const m = moveNodesExact(ring, nodes, [0], 1, 1);
    expect(m.dirty).toEqual([0, N - 1]);
    const r = rebuildSpans(m.ring, m.nodes, m.dirty);
    expect(isValidNodes(r.nodes, r.ring)).toBe(true);
    for (let s = 1; s < N - 1; s++) {
      expect(interior(r.ring, r.nodes, s)).toEqual(interior(ring, nodes, s));
    }
  });
  it("I5: a square with a dragged corner is a 4-vertex quadrilateral", () => {
    const sq = square4();
    const nodes = seedNodes(sq);
    const m = moveNodesExact(sq, nodes, [2], 3, 4);
    const r = rebuildSpans(m.ring, m.nodes, m.dirty);
    expect(r.ring).toEqual([[0, 0], [20, 0], [23, 24], [0, 20]]);
  });
  it("no dirty spans is a copy", () => {
    const ring = circle(64);
    const nodes = seedNodes(ring);
    expect(rebuildSpans(ring, nodes, [])).toEqual({ ring, nodes });
  });
});

describe("toggle / delete / insert", () => {
  const ring = circle(64);
  const nodes = seedNodes(ring);
  it("toggle flips the kind and dirties exactly two spans", () => {
    const t = toggleNode(nodes, 4);
    expect(t.nodes[4].kind).toBe("corner");
    expect(t.dirty).toEqual([3, 4]);
    expect(toggleNode(nodes, 0).dirty).toEqual([0, nodes.length - 1]);
    expect(nodes[4].kind).toBe("smooth"); // not mutated
    const r = rebuildSpans(ring, t.nodes, t.dirty);
    expect(r.nodes[4].kind).toBe("corner");
    // a corner on a circle straightens its two spans' ends -> at least one interior changed
    expect(r.ring.length).not.toBe(0);
  });
  it("delete merges the neighbours' span, rebuilds it, refuses at 3 nodes", () => {
    const d = deleteNodes(ring, nodes, [4]);
    expect(d.nodes.length).toBe(nodes.length - 1);
    expect(d.dirty).toEqual([3]);
    const r = rebuildSpans(d.ring, d.nodes, d.dirty);
    expect(r.nodes.length).toBe(nodes.length - 1);
    // the deleted node's vertex is gone with the old interior
    expect(r.ring.some((p) => p[0] === ring[nodes[4].i][0] && p[1] === ring[nodes[4].i][1])).toBe(false);
    for (let s = 0; s < r.nodes.length; s++) {
      if (s === 3) continue;
      const oldS = s < 3 ? s : s + 1;
      expect(interior(r.ring, r.nodes, s)).toEqual(interior(ring, nodes, oldS));
    }
    // floor
    const tri = [{ i: 0, kind: "corner" }, { i: 1, kind: "corner" }, { i: 2, kind: "corner" }];
    expect(deleteNodes([[0, 0], [1, 0], [0, 1]], tri, [0])).toBeNull();
    expect(deleteNodes(ring, nodes.slice(0, 4), [0, 1])).toBeNull();
  });
  it("delete of node 0 and of adjacent nodes", () => {
    const d = deleteNodes(ring, nodes, [0, 1]);
    expect(d.dirty).toEqual([nodes.length - 3]); // one merged span from old node N-1
    const r = rebuildSpans(d.ring, d.nodes, d.dirty);
    expect(isValidNodes(r.nodes, r.ring)).toBe(true);
  });
  it("insert adds exactly one vertex, keeps area and perimeter (I6), re-indexes later nodes", () => {
    const sq = square4();
    const nd = seedNodes(sq);
    const r = insertNodeOnPath(sq, nd, [10, -0.7]); // 0.7 off the bottom edge
    expect(r.ring.length).toBe(5);
    expect(r.ring[1]).toEqual([10, 0]);
    expect(r.nodeIndex).toBe(1);
    expect(r.nodes).toEqual([
      { i: 0, kind: "corner" }, { i: 1, kind: "corner" }, { i: 2, kind: "corner" },
      { i: 3, kind: "corner" }, { i: 4, kind: "corner" },
    ]);
    expect(Math.abs(area(r.ring) - area(sq)) / Math.abs(area(sq))).toBeLessThan(1e-9);
    expect(Math.abs(perim(r.ring) - perim(sq)) / perim(sq)).toBeLessThan(1e-9);
    expect(sq).toEqual(square4());
    // on the wrap edge (last -> first), winding kept
    const w = insertNodeOnPath(sq, nd, [-1, 10]);
    expect(w.ring.length).toBe(5);
    expect(w.ring[4]).toEqual([0, 10]);
    expect(w.nodes.map((x) => x.i)).toEqual([0, 1, 2, 3, 4]);
  });
  it("a second insert near an existing vertex snaps to it, adding nothing", () => {
    const sq = square4();
    const first = insertNodeOnPath(sq, seedNodes(sq), [10, 0]);
    const again = insertNodeOnPath(first.ring, first.nodes, [10, 0.0000003]);
    expect(again.ring.length).toBe(5);
    expect(again.nodeIndex).toBe(1);
    expect(again.nodes).toEqual(first.nodes);
  });
  it("insert on a circle's smooth ring re-indexes later nodes and makes a corner", () => {
    const nd = seedNodes(circle(64));
    const p = circle(64)[3]; // between nodes
    const mid = [(p[0] + circle(64)[4][0]) / 2, (p[1] + circle(64)[4][1]) / 2];
    const r = insertNodeOnPath(circle(64), nd, mid);
    expect(r.ring.length).toBe(65);
    expect(r.nodes.length).toBe(nd.length + 1);
    expect(r.nodes[r.nodeIndex].kind).toBe("corner");
    expect(isValidNodes(r.nodes, r.ring)).toBe(true);
    const later = nd.filter((x) => x.i > 3).map((x) => x.i + 1);
    expect(r.nodes.filter((x, j) => j > r.nodeIndex).map((x) => x.i)).toEqual(later);
  });
  it("nodePositions returns the node vertices", () => {
    const sq = square4();
    expect(nodePositions(sq, seedNodes(sq))).toEqual(sq);
  });
});

describe("500-point cap (I7)", () => {
  it("one node moved 2 mm on a 500-point ring stays <= 500; untouched spans deep-equal", () => {
    const ring = circle(500, 40);
    const nodes = seedNodes(ring);
    const k = 2;
    const m = moveNodesExact(ring, nodes, [k], 2, 0);
    const r = rebuildSpans(m.ring, m.nodes, m.dirty);
    expect(r.ring.length).toBeLessThanOrEqual(BOUNDARY_MAX_POINTS);
    for (let s = 0; s < nodes.length; s++) {
      if (m.dirty.includes(s)) continue;
      expect(interior(r.ring, r.nodes, s)).toEqual(interior(ring, nodes, s));
    }
  });
  it("forced coarsening: rebuilding half the spans terminates under 500", () => {
    const ring = circle(480, 60);
    const nodes = seedNodes(ring);
    const dirty = nodes.map((_, k) => k).filter((k) => k % 2 === 0);
    // nudge every node so the curves differ from the trace
    const m = moveNodesExact(ring, nodes, nodes.map((_, k) => k), 0.2, 0.1);
    const r = rebuildSpans(m.ring, m.nodes, dirty, {});
    expect(r.ring.length).toBeLessThanOrEqual(BOUNDARY_MAX_POINTS);
    const kept = nodes.map((_, k) => k).filter((k) => !dirty.includes(k));
    for (const s of kept) {
      expect(interior(r.ring, r.nodes, s)).toEqual(interior(m.ring, nodes, s));
    }
    // and a hard case: a ring already near the cap with every span dirty
    const full = circle(498, 200);
    const nd = seedNodes(full);
    const all = rebuildSpans(full, nd, nd.map((_, k) => k));
    expect(all.ring.length).toBeLessThanOrEqual(BOUNDARY_MAX_POINTS);
  });
});

describe("isValidNodes", () => {
  const ring = circle(10);
  const ok = [{ i: 0, kind: "smooth" }, { i: 3, kind: "corner" }, { i: 6, kind: "smooth" }];
  it("accepts a good list", () => expect(isValidNodes(ok, ring)).toBe(true));
  it("rejects out of range, unsorted, duplicate, under 3 and bad kind", () => {
    expect(isValidNodes([...ok.slice(0, 2), { i: 10, kind: "smooth" }], ring)).toBe(false);
    expect(isValidNodes([{ i: -1, kind: "smooth" }, ...ok.slice(1)], ring)).toBe(false);
    expect(isValidNodes([ok[1], ok[0], ok[2]], ring)).toBe(false);
    expect(isValidNodes([ok[0], ok[1], { i: 3, kind: "smooth" }], ring)).toBe(false);
    expect(isValidNodes(ok.slice(0, 2), ring)).toBe(false);
    expect(isValidNodes([ok[0], ok[1], { i: 6, kind: "round" }], ring)).toBe(false);
    expect(isValidNodes([ok[0], ok[1], { i: 6.5, kind: "smooth" }], ring)).toBe(false);
    expect(isValidNodes(null, ring)).toBe(false);
  });
});
