// Sparse smooth nodes on a digitized ring (spec 2026-11-04-sparse-smooth-nodes-
// design.md, PR 1: the pure library; the Studio wiring is PR 2).
//
// A ring is `[[x, y], ...]` in mm, closed implicitly, winding kept. A NODE is a
// polygon vertex that the editor shows and drags: `{ i, kind }`, `i` an index
// into the ring (strictly ascending), kind "smooth" | "corner". Between two
// consecutive nodes the edge is a Catmull-Rom curve; a SPAN is the polygon's
// vertices from node k to node k+1 inclusive, wrapping. A span's interior is
// either the original trace (untouched) or a flattening of its curve (rebuilt).
//
// Everything is pure: nothing here mutates its arguments. This module works on
// ONE ring plus its node list; the shell/holes container is the Studio's.
//
// Spec ruling worth restating: a span whose curve is FLAT (deviates from its
// chord by no more than FLATTEN_ERR_MM) keeps no interior vertices at all,
// however long the chord. Without that a corner-to-corner edge of a logo's
// square would gain a vertex every millimetre when a neighbour moved, and
// invariant I5 (a dragged square stays a 4-vertex quadrilateral) would be false.

import { BOUNDARY_MAX_POINTS } from "./digitizer.js";

export const SEED_TOL_MM = 0.5;
export const CORNER_DEG = 35;
export const FLATTEN_ERR_MM = 0.05;
export const FLATTEN_MIN_MM = 0.3;
export const FLATTEN_MAX_MM = 1.0;
export const MIN_NODES = 3;

const SAME_POINT_MM = 1e-6;
const KINDS = new Set(["smooth", "corner"]);

const copyRing = (ring) => ring.map(([x, y]) => [x, y]);
const copyNodes = (nodes) => nodes.map((n) => ({ i: n.i, kind: n.kind }));

function distToSegment(px, py, ax, ay, bx, by) {
  const vx = bx - ax;
  const vy = by - ay;
  const len2 = vx * vx + vy * vy;
  const t = len2 <= 1e-12 ? 0 : Math.max(0, Math.min(1, ((px - ax) * vx + (py - ay) * vy) / len2));
  const cx = ax + t * vx;
  const cy = ay + t * vy;
  return { dist: Math.hypot(px - cx, py - cy), t, x: cx, y: cy };
}

// Open-polyline Douglas-Peucker over pts[lo..hi] (both kept) -> Set of kept
// indices. Same scheme as shapeOverlay's private `dpKeep`/`simplifyRing`; that
// one returns points and is not exported, so the ~15 lines are duplicated here
// (returning INDICES is the whole point) rather than coupling the two.
function dpKeepIndices(pts, lo, hi, tol) {
  const keep = new Set([lo, hi]);
  const stack = [[lo, hi]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let worst = -1, at = -1;
    for (let i = a + 1; i < b; i++) {
      const d = distToSegment(pts[i][0], pts[i][1], pts[a][0], pts[a][1], pts[b][0], pts[b][1]).dist;
      if (d > worst) { worst = d; at = i; }
    }
    if (at >= 0 && worst > tol) {
      keep.add(at);
      stack.push([a, at], [at, b]);
    }
  }
  return keep;
}

// Turn angle (degrees, unsigned) at `p` between the chords prev->p and p->next.
function turnDeg(prev, p, next) {
  const ax = p[0] - prev[0], ay = p[1] - prev[1];
  const bx = next[0] - p[0], by = next[1] - p[1];
  if (Math.hypot(ax, ay) < 1e-12 || Math.hypot(bx, by) < 1e-12) return 0;
  return Math.abs((Math.atan2(ax * by - ay * bx, ax * bx + ay * by) * 180) / Math.PI);
}

function kindsFor(ring, idx) {
  const m = idx.length;
  return idx.map((i, k) => ({
    i,
    kind: turnDeg(ring[idx[(k - 1 + m) % m]], ring[i], ring[idx[(k + 1) % m]]) > CORNER_DEG ? "corner" : "smooth",
  }));
}

/**
 * Seed the node list of a ring: closed-ring Douglas-Peucker at SEED_TOL_MM
 * (split at the two farthest vertices, as `simplifyRing` does), kept INDICES
 * become nodes; a node is a corner when the turn between its two chords
 * exceeds CORNER_DEG. A ring of 3 or fewer vertices makes every vertex a node.
 * Pure function of the ring, so re-deriving gives the same seeds.
 */
export function seedNodes(ring) {
  const n = ring.length;
  if (n <= MIN_NODES) return kindsFor(ring, ring.map((_, i) => i));
  let ia = 0, ib = 1, far = -1;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const d = Math.hypot(ring[j][0] - ring[i][0], ring[j][1] - ring[i][1]);
      if (d > far) { far = d; ia = i; ib = j; }
    }
  }
  // half one: ia -> ib; half two: ib -> ia round the wrap (ring indices kept)
  const half = (from, to) => {
    const seq = [];
    for (let i = from; ; i = (i + 1) % n) { seq.push(i); if (i === to) break; }
    return seq;
  };
  const keep = new Set();
  for (const seq of [half(ia, ib), half(ib, ia)]) {
    const pts = seq.map((i) => ring[i]);
    for (const k of dpKeepIndices(pts, 0, pts.length - 1, SEED_TOL_MM)) keep.add(seq[k]);
  }
  // A sliver can DP down to two points; a node list needs MIN_NODES. Add the
  // vertices farthest from the existing polygon until it has three.
  while (keep.size < MIN_NODES) {
    const cur = [...keep].sort((a, b) => a - b);
    let best = -1, bd = -1;
    for (let i = 0; i < n; i++) {
      if (keep.has(i)) continue;
      let d = Infinity;
      for (let k = 0; k < cur.length; k++) {
        const a = ring[cur[k]], b = ring[cur[(k + 1) % cur.length]];
        d = Math.min(d, distToSegment(ring[i][0], ring[i][1], a[0], a[1], b[0], b[1]).dist);
      }
      if (d > bd) { bd = d; best = i; }
    }
    keep.add(best);
  }
  return kindsFor(ring, [...keep].sort((a, b) => a - b));
}

/** In range, strictly ascending, >= MIN_NODES, kinds valid. */
export function isValidNodes(nodes, ring) {
  if (!Array.isArray(nodes) || !Array.isArray(ring) || nodes.length < MIN_NODES) return false;
  let prev = -1;
  for (const nd of nodes) {
    if (!nd || !Number.isInteger(nd.i) || nd.i < 0 || nd.i >= ring.length) return false;
    if (nd.i <= prev) return false;
    if (!KINDS.has(nd.kind)) return false;
    prev = nd.i;
  }
  return true;
}

function clampOffset(vx, vy, limit) {
  const len = Math.hypot(vx, vy);
  if (len <= limit || len === 0) return [vx, vy];
  const s = limit / len;
  return [vx * s, vy * s];
}

/**
 * Span k (node k -> node k+1, wrapping) as a cubic Bezier [P0, C1, C2, P3].
 * Uniform Catmull-Rom: C1 = P_i + (P_{i+1} - P_{i-1}) / 6, C2 = P_{i+1} -
 * (P_{i+2} - P_i) / 6, each control offset clamped to half the chord. At a
 * CORNER node the tangent on each side is that side's chord, so corner-to-corner
 * spans are straight lines.
 */
export function spanCurve(ring, nodes, k) {
  const N = nodes.length;
  const a = nodes[k], b = nodes[(k + 1) % N];
  const prev = nodes[(k - 1 + N) % N], next = nodes[(k + 2) % N];
  const P0 = ring[a.i], P3 = ring[b.i];
  const Pm = ring[prev.i], Pn = ring[next.i];
  const cx = P3[0] - P0[0], cy = P3[1] - P0[1];
  const half = Math.hypot(cx, cy) / 2;
  const o1 = a.kind === "corner" ? [cx / 3, cy / 3] : [(P3[0] - Pm[0]) / 6, (P3[1] - Pm[1]) / 6];
  const o2 = b.kind === "corner" ? [cx / 3, cy / 3] : [(Pn[0] - P0[0]) / 6, (Pn[1] - P0[1]) / 6];
  const [u1, v1] = clampOffset(o1[0], o1[1], half);
  const [u2, v2] = clampOffset(o2[0], o2[1], half);
  return [
    [P0[0], P0[1]],
    [P0[0] + u1, P0[1] + v1],
    [P3[0] - u2, P3[1] - v2],
    [P3[0], P3[1]],
  ];
}

function bezierAt(b, t) {
  const s = 1 - t;
  const w0 = s * s * s, w1 = 3 * s * s * t, w2 = 3 * s * t * t, w3 = t * t * t;
  return [
    w0 * b[0][0] + w1 * b[1][0] + w2 * b[2][0] + w3 * b[3][0],
    w0 * b[0][1] + w1 * b[1][1] + w2 * b[2][1] + w3 * b[3][1],
  ];
}

// Largest distance of the curve (sampled) over [t0, t1] from the chord A->Z.
function sagitta(b, t0, t1, A, Z) {
  let worst = 0;
  for (const f of [0.25, 0.5, 0.75]) {
    const p = bezierAt(b, t0 + (t1 - t0) * f);
    worst = Math.max(worst, distToSegment(p[0], p[1], A[0], A[1], Z[0], Z[1]).dist);
  }
  return worst;
}

/**
 * Interior vertices of a Bezier (ends excluded), by adaptive subdivision: split
 * while the chord error is over `errMm` or the spacing over `maxMm`, never when
 * the piece is under twice `minMm`. A FLAT curve (every sample within `errMm`
 * of the whole chord) keeps nothing, however long: a 5 mm straight edge stays
 * two vertices.
 */
export function flattenSpan(bezier, opts = {}) {
  const errMm = opts.errMm ?? FLATTEN_ERR_MM;
  const minMm = opts.minMm ?? FLATTEN_MIN_MM;
  const maxMm = opts.maxMm ?? FLATTEN_MAX_MM;
  const A0 = bezier[0], Z0 = bezier[3];
  let flat = true;
  for (let s = 1; s < 16 && flat; s++) {
    const p = bezierAt(bezier, s / 16);
    if (distToSegment(p[0], p[1], A0[0], A0[1], Z0[0], Z0[1]).dist > errMm) flat = false;
  }
  if (flat) return [];
  const out = [];
  // Depth-first, left to right, so the output is in curve order.
  const rec = (t0, t1, A, Z, depth) => {
    const L = Math.hypot(Z[0] - A[0], Z[1] - A[1]);
    const mustSplit = sagitta(bezier, t0, t1, A, Z) > errMm || L > maxMm;
    if (mustSplit && L >= 2 * minMm && depth < 40) {
      const tm = (t0 + t1) / 2;
      const M = bezierAt(bezier, tm);
      rec(t0, tm, A, M, depth + 1);
      out.push(M);
      rec(tm, t1, M, Z, depth + 1);
    }
  };
  rec(0, 1, [A0[0], A0[1]], [Z0[0], Z0[1]], 0);
  return out;
}

// One full layout of the ring with the given spacing factor. The ring's head
// (vertices before node 0) and tail (after the last node) are the two halves of
// the LAST span's interior; they stay where they are unless that span is dirty,
// in which case node 0 becomes index 0.
function layout(ring, nodes, dirty, factor, curves) {
  const N = nodes.length;
  const lastDirty = dirty.has(N - 1);
  const out = lastDirty ? [] : ring.slice(0, nodes[0].i).map(([x, y]) => [x, y]);
  const newNodes = [];
  const flat = (k) => flattenSpan(curves[k], {
    minMm: FLATTEN_MIN_MM * factor,
    maxMm: FLATTEN_MAX_MM * factor,
  });
  for (let k = 0; k < N; k++) {
    newNodes.push({ i: out.length, kind: nodes[k].kind });
    const p = ring[nodes[k].i];
    out.push([p[0], p[1]]);
    let interior;
    if (k < N - 1) {
      interior = dirty.has(k) ? flat(k) : ring.slice(nodes[k].i + 1, nodes[k + 1].i);
    } else {
      interior = dirty.has(k) ? flat(k) : ring.slice(nodes[k].i + 1);
    }
    for (const [x, y] of interior) out.push([x, y]);
  }
  return { ring: out, nodes: newNodes };
}

/**
 * Rebuild the dirty spans: replace each one's interior vertices with the
 * flattening of its curve (current node positions and kinds), keep every other
 * span's vertices byte-identical, re-index `nodes`. Then the cap: while the
 * ring exceeds BOUNDARY_MAX_POINTS, the DIRTY spans alone are re-flattened with
 * both spacing bounds doubled (0.6-2.0, 1.2-4.0, ...); original spans are never
 * thinned. `ring` must already hold the moved node positions.
 *
 * @returns { ring, nodes }
 */
export function rebuildSpans(ring, nodes, dirtySpanIndices, opts = {}) {
  const N = nodes.length;
  const max = opts.maxPoints ?? BOUNDARY_MAX_POINTS;
  const dirty = new Set([...(dirtySpanIndices || [])].filter((k) => Number.isInteger(k) && k >= 0 && k < N));
  if (!dirty.size) return { ring: copyRing(ring), nodes: copyNodes(nodes) };
  const curves = [];
  for (const k of dirty) curves[k] = spanCurve(ring, nodes, k);
  let res = layout(ring, nodes, dirty, 1, curves);
  for (let factor = 2; res.ring.length > max && factor <= 1024; factor *= 2) {
    res = layout(ring, nodes, dirty, factor, curves);
  }
  if (res.ring.length > max) {
    // Error-bound vertices alone still overflow (a huge, very curved span):
    // last resort, the dirty spans keep no interior at all.
    for (const k of dirty) curves[k] = [[0, 0], [0, 0], [0, 0], [0, 0]];
    res = layout(ring, nodes, dirty, 1, curves);
  }
  return res;
}

/**
 * Move the named nodes (indices into the NODE LIST) by (dx, dy), exactly. The
 * span indices to rebuild are both spans at each moved node. Compose with
 * `rebuildSpans`.
 */
export function moveNodesExact(ring, nodes, nodeIndices, dx, dy) {
  const N = nodes.length;
  const out = copyRing(ring);
  const dirty = new Set();
  for (const k of nodeIndices) {
    if (!Number.isInteger(k) || k < 0 || k >= N) continue;
    const i = nodes[k].i;
    out[i] = [out[i][0] + dx, out[i][1] + dy];
    dirty.add(k);
    dirty.add((k - 1 + N) % N);
  }
  return { ring: out, nodes: copyNodes(nodes), dirty: [...dirty].sort((a, b) => a - b) };
}

/**
 * Insert a CORNER node where `point` projects onto the nearest polygon edge.
 * The node is a new collinear vertex placed after the edge's start index
 * (`insertNode` semantics, winding kept); later nodes re-index; no span
 * rebuilds, so geometry is unchanged. A projection within 1e-6 mm of an
 * existing vertex makes that vertex the node (a no-op if it already is one).
 */
export function insertNodeOnPath(ring, nodes, point) {
  const n = ring.length;
  let best = null;
  for (let j = 0; j < n; j++) {
    const a = ring[j], b = ring[(j + 1) % n];
    const s = distToSegment(point[0], point[1], a[0], a[1], b[0], b[1]);
    if (!best || s.dist < best.dist) best = { ...s, j };
  }
  const near = (v) => Math.hypot(best.x - v[0], best.y - v[1]) <= SAME_POINT_MM;
  let at = -1;
  if (near(ring[best.j])) at = best.j;
  else if (near(ring[(best.j + 1) % n])) at = (best.j + 1) % n;

  const newNodes = copyNodes(nodes);
  if (at >= 0) {
    const existing = newNodes.findIndex((nd) => nd.i === at);
    if (existing >= 0) return { ring: copyRing(ring), nodes: newNodes, nodeIndex: existing };
    const pos = newNodes.findIndex((nd) => nd.i > at);
    const slot = pos < 0 ? newNodes.length : pos;
    newNodes.splice(slot, 0, { i: at, kind: "corner" });
    return { ring: copyRing(ring), nodes: newNodes, nodeIndex: slot };
  }
  const out = copyRing(ring);
  out.splice(best.j + 1, 0, [best.x, best.y]);
  for (const nd of newNodes) if (nd.i > best.j) nd.i += 1;
  const pos = newNodes.findIndex((nd) => nd.i > best.j + 1);
  const slot = pos < 0 ? newNodes.length : pos;
  newNodes.splice(slot, 0, { i: best.j + 1, kind: "corner" });
  return { ring: out, nodes: newNodes, nodeIndex: slot };
}

/** Flip a node's kind; the two spans at it are dirty. */
export function toggleNode(nodes, nodeIndex) {
  const N = nodes.length;
  const out = copyNodes(nodes);
  if (!Number.isInteger(nodeIndex) || nodeIndex < 0 || nodeIndex >= N) return { nodes: out, dirty: [] };
  out[nodeIndex].kind = out[nodeIndex].kind === "corner" ? "smooth" : "corner";
  const dirty = [...new Set([(nodeIndex - 1 + N) % N, nodeIndex])].sort((a, b) => a - b);
  return { nodes: out, dirty };
}

/**
 * Remove nodes (indices into the node list). null when fewer than MIN_NODES
 * would remain (nothing removed). The removed nodes' vertices STAY in the ring
 * until the merged span is rebuilt, which drops them with the rest of the old
 * interior: the caller ALWAYS follows with `rebuildSpans(ring, nodes, dirty)`.
 * `dirty` indexes the NEW node list (each merged span).
 */
export function deleteNodes(ring, nodes, nodeIndices) {
  const N = nodes.length;
  const drop = new Set([...nodeIndices].filter((k) => Number.isInteger(k) && k >= 0 && k < N));
  if (!drop.size) return { ring: copyRing(ring), nodes: copyNodes(nodes), dirty: [] };
  if (N - drop.size < MIN_NODES) return null;
  const kept = [];
  const dirty = [];
  for (let k = 0; k < N; k++) {
    if (drop.has(k)) continue;
    if (drop.has((k + 1) % N)) dirty.push(kept.length);
    kept.push({ i: nodes[k].i, kind: nodes[k].kind });
  }
  return { ring: copyRing(ring), nodes: kept, dirty };
}

/** The nodes' positions, for drawing. */
export function nodePositions(ring, nodes) {
  return nodes.map((nd) => [ring[nd.i][0], ring[nd.i][1]]);
}
