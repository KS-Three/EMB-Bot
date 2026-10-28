// "Apply to all similar shapes" (Kent 2026-10-28: ~50 stars on a digitized
// flag, each needing the same Fill, one select at a time).
//
// WHAT "SIMILAR" MEANS. Shape B is similar to the selected shape A when ALL
// of these hold:
//   1. it is a live shape of the same digitized design — not deleted, not
//      switched off (stitched === false);
//   2. it has the same colour as A as it SEWS today (a recolour override
//      counts, so a star Kent already changed is not swept up by its old
//      colour);
//   3. its area is within a factor of `areaRatio` of A's — scale tolerant on
//      purpose (a flag's stars shrink toward the edge of the canton), but not
//      so loose that a speck matches a field;
//   4. its outline has the same FORM, read from four numbers that do not
//      change under turning or scaling: Hu's first two moment invariants,
//      compactness (perimeter² / 4π·area) and solidity (area / convex-hull
//      area). Solidity and compactness are what tell a star from a stripe of
//      the same colour; the moments catch an elongated bar from a blob.
// Position never matters. Stitch type never matters (B may already be Fill).
//
// Pure: rings in, ids out. The popover's patch for each shape is the
// popover's own (shapePopover.popoverPatch), so a group edit and N single
// edits are the same bytes in shapeOverrides — and ONE patch, so one undo.
import { popoverPatch, overridePatch } from "./shapePopover.js";
import { outlineOf } from "./shapeOverlay.js";

// The numbers behind the definition. Measured on the flag fixture
// (similarShapes.spec.js) and on Kent's Flag.webp through the live service
// (see the PR); loosen only with a case that needs it.
export const SIMILAR_TOLERANCE = {
  areaRatio: 2,          // either way: 0.5x .. 2x A's area
  phi1Rel: 0.15,         // relative, Hu phi1
  phi2Abs: 0.012,        // absolute, Hu phi2 (≈0 for any symmetric form)
  compactnessRel: 0.2,   // relative
  solidityAbs: 0.1,      // absolute, 0..1
  colorChannel: 3,       // per-channel rgb slack: threads are exact, this is rounding
};

// Polygon area, centroid and second moments by Green's theorem, then Hu
// phi1/phi2, compactness and solidity. Null for a ring with no area.
export function shapeSignature(ring) {
  const p = ring && ring.length >= 3 ? ring : null;
  if (!p) return null;
  const n = p.length;
  let a2 = 0, sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0, perim = 0;
  for (let i = 0; i < n; i++) {
    const [x0, y0] = p[i];
    const [x1, y1] = p[(i + 1) % n];
    const c = x0 * y1 - x1 * y0;
    a2 += c;
    sx += (x0 + x1) * c;
    sy += (y0 + y1) * c;
    sxx += (x0 * x0 + x0 * x1 + x1 * x1) * c;
    sxy += (x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0) * c;
    syy += (y0 * y0 + y0 * y1 + y1 * y1) * c;
    perim += Math.hypot(x1 - x0, y1 - y0);
  }
  const area = Math.abs(a2) / 2;
  if (!(area > 1e-9)) return null;
  // Signed formulas assume counter-clockwise; fold the winding in.
  const sgn = a2 < 0 ? -1 : 1;
  const A = a2 / 2;                      // signed area
  // Σ(x0+x1)c = 6·A·Cx with A the signed area → Cx = sx / (6A); same for y.
  const Cx = sx / (6 * A), Cy = sy / (6 * A);
  // Raw second moments: m20 = Σ(x0²+x0x1+x1²)c / 12, m02 likewise, m11 / 24.
  const m20 = (sxx / 12) * sgn, m02 = (syy / 12) * sgn, m11 = (sxy / 24) * sgn;
  const mu20 = m20 - area * Cx * Cx;
  const mu02 = m02 - area * Cy * Cy;
  const mu11 = m11 - area * Cx * Cy;
  const norm = area * area;              // η_pq = μ_pq / μ00^(1+(p+q)/2), μ00 = area, p+q = 2
  const e20 = mu20 / norm, e02 = mu02 / norm, e11 = mu11 / norm;
  const phi1 = e20 + e02;
  const phi2 = (e20 - e02) * (e20 - e02) + 4 * e11 * e11;
  const hull = hullArea(p);
  return {
    area,
    perimeter: perim,
    phi1,
    phi2,
    compactness: (perim * perim) / (4 * Math.PI * area),
    solidity: hull > 1e-9 ? Math.min(1, area / hull) : 1,
  };
}

// Andrew's monotone chain, area of the hull.
function hullArea(points) {
  const pts = points.map((q) => [q[0], q[1]]).sort((u, v) => u[0] - v[0] || u[1] - v[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const build = (list) => {
    const h = [];
    for (const q of list) {
      while (h.length >= 2 && cross(h[h.length - 2], h[h.length - 1], q) <= 0) h.pop();
      h.push(q);
    }
    h.pop();
    return h;
  };
  const hull = build(pts).concat(build(pts.slice().reverse()));
  let a = 0;
  for (let i = 0; i < hull.length; i++) {
    const [x0, y0] = hull[i];
    const [x1, y1] = hull[(i + 1) % hull.length];
    a += x0 * y1 - x1 * y0;
  }
  return Math.abs(a) / 2;
}

// The colour a shape sews in right now: a recolour override, else the row's.
function effectiveRgb(row, entry) {
  return Array.isArray(entry && entry.rgb) ? entry.rgb : row.rgb;
}

function sameColour(a, b, tol) {
  if (a.rgb && b.rgb) return a.rgb.every((v, i) => Math.abs(v - b.rgb[i]) <= tol);
  return a.rgb == null && b.rgb == null && a.thread != null && a.thread === b.thread;
}

function formMatches(a, b, t) {
  const hi = Math.max(a.area, b.area), lo = Math.min(a.area, b.area);
  if (hi / lo > t.areaRatio) return false;
  const rel = (u, v) => Math.abs(u - v) / Math.max(Math.abs(u), Math.abs(v), 1e-9);
  return (
    rel(a.phi1, b.phi1) <= t.phi1Rel &&
    Math.abs(a.phi2 - b.phi2) <= t.phi2Abs &&
    rel(a.compactness, b.compactness) <= t.compactnessRel &&
    Math.abs(a.solidity - b.solidity) <= t.solidityAbs
  );
}

// -> ids of every shape similar to `shapeId` in `element`, the selected one
// first and the rest in review order; [] when `shapeId` is not a live shape.
export function similarShapeIds(element, shapeId, tolerance = SIMILAR_TOLERANCE) {
  const rows = (element && element.review && element.review.shapes) || [];
  const overrides = element.shapeOverrides || {};
  const gone = new Set(element.deletedShapeIds || []);
  const live = (r) => r && r.stitched !== false && !gone.has(r.id);
  const read = (r) => {
    const ring = outlineOf(r);
    const sig = ring && shapeSignature(ring);
    if (!sig) return null;
    return { ...sig, rgb: effectiveRgb(r, overrides[r.id]), thread: r.threadNumber };
  };
  const self = rows.find((r) => live(r) && r.id === shapeId);
  const me = self && read(self);
  if (!me) return [];
  const out = [shapeId];
  for (const r of rows) {
    if (!live(r) || r.id === shapeId) continue;
    const you = read(r);
    if (you && sameColour(me, you, tolerance.colorChannel) && formMatches(me, you, tolerance)) out.push(r.id);
  }
  return out;
}

// -> ONE `elupdate` patch that makes the popover edit `key`/`value` on every
// id, or null when the key is not a per-shape override that makes sense for a
// group (delete and the actions never are). `recolor` takes the resolved
// override fields { thread_index, rgb } — the thread-chart lookup is async and
// lives in the caller.
export function similarOverridesPatch(element, ids, key, value) {
  let cur = element;
  for (const id of ids) {
    const patch = key === "recolor"
      ? overridePatch(cur, id, value)
      : key === "delete" ? null : popoverPatch({ element: cur, shapeId: id }, key, value);
    if (key !== "recolor" && !patch) return null;
    cur = { ...cur, ...patch };
  }
  return { shapeOverrides: cur.shapeOverrides };
}
