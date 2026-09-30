// Node editing of hand-drawn shapes on the hoop canvas (2026-09-29 spec).
//
// A hand-drawn shape is AUTHORED geometry — anchors in a fixed 600x400
// canvas-px space plus one optional quadratic control per segment
// (manualShapes.js) — and the engine fits the bbox of all of an element's
// shapes to the hoop. The field only ever saw the flattened ring. This module
// maps the authored anchors and controls through the engine's own fit
// (`design.fit`, exported by buildQualityDesign) so the field can draw and
// edit them, and it owns the one rule that makes editing usable: an edit
// never moves what was not edited (editedElementPatch). Pure: no DOM, no
// Svelte. Points in field mm are [x, y] arrays (the field's convention);
// shape records keep {x, y} canvas px.
import {
  flattenShape, shapeIssues, curveHandlePoint, curveControlOrNull,
  insertVertexAtSegment, nearestSegmentIndex,
} from "./manualShapes.js";

// shapeOverlay.js's grab radii, so a hand-drawn node feels like a digitized one.
export const ANCHOR_GRAB_PX = 9;
export const HANDLE_GRAB_PX = 8;
export const EDGE_GRAB_PX = 6;

// T() without the rounding: canvas px -> field mm (+y up).
export function pxToFieldMm(fit, q) {
  return [(q.x - fit.cxPx) * fit.mmPerPx + fit.offsetXMm, (fit.cyPx - q.y) * fit.mmPerPx + fit.offsetYMm];
}
export function fieldMmToPx(fit, [xMm, yMm]) {
  return { x: fit.cxPx + (xMm - fit.offsetXMm) / fit.mmPerPx, y: fit.cyPx - (yMm - fit.offsetYMm) / fit.mmPerPx };
}

// Kent's ruling (2026-09-29): a dragged node stops at the garment PLACEMENT
// BOX. The engine clamps the whole design's scale to that box, so a point
// dragged past it would rescale everything else; editedElementPatch keeps
// every unedited point still, so keeping the dragged point inside keeps the
// bbox inside and the clamp never fires. Box is centred on the field origin.
export function clampMmToBox([xMm, yMm], box) {
  const hw = Math.max(0, (box.wMm || 0) / 2), hh = Math.max(0, (box.hMm || 0) / 2);
  return [Math.min(hw, Math.max(-hw, xMm)) + 0, Math.min(hh, Math.max(-hh, yMm)) + 0]; // + 0: no -0
}

// Anchors, controls and the per-segment handle (B(0.5) of the curve, or the
// chord midpoint when straight) in field mm. The control point is mapped
// directly: the map is affine, so a quadratic drawn through mapped
// anchors/control is the same curve the engine flattened.
export function authoredInFieldMm(shape, fit) {
  const pts = shape.points || [];
  const curves = shape.curves || {};
  const n = pts.length;
  const anchors = pts.map((p) => pxToFieldMm(fit, p));
  const controls = {};
  const handles = [];
  for (let i = 0; i < n; i++) {
    const a = pts[i], c = pts[(i + 1) % n];
    if (curves[i]) controls[i] = pxToFieldMm(fit, curves[i]);
    handles.push(pxToFieldMm(fit, curveHandlePoint(a, c, curves[i])));
  }
  return { anchors, controls, handles };
}

// What a point is on, in ONE px space (the caller maps the authored geometry
// to canvas px first). Anchors beat handles beat edges: an anchor sits on two
// edges and a handle sits on its edge, so distance alone would hand a
// dead-centre hit to whichever rounds smaller. The edge distance is measured
// against the FLATTENED curve chain, so a bowed segment is hit on its bow.
export function hitAuthored(authoredPx, px, py) {
  const { anchors, controls, handles } = authoredPx;
  for (let i = 0; i < anchors.length; i++) {
    if (Math.hypot(px - anchors[i][0], py - anchors[i][1]) <= ANCHOR_GRAB_PX) return { kind: "anchor", index: i, atPx: anchors[i] };
  }
  for (let i = 0; i < handles.length; i++) {
    if (Math.hypot(px - handles[i][0], py - handles[i][1]) <= HANDLE_GRAB_PX) return { kind: "handle", index: i, atPx: handles[i] };
  }
  const pts = anchors.map(([x, y]) => ({ x, y }));
  const cv = {};
  for (const k of Object.keys(controls)) cv[k] = { x: controls[k][0], y: controls[k][1] };
  const near = nearestSegmentIndex(pts, cv, px, py, true);
  if (near && near.index >= 0 && near.dist <= EDGE_GRAB_PX) return { kind: "edge", index: near.index, atPx: [px, py] };
  return null;
}

export function applyAnchorDrag(shape, index, newPx) {
  const points = shape.points.map((p, i) => (i === index ? { x: newPx.x, y: newPx.y } : p));
  return { ...shape, points };
}

// Drag a segment's handle to `throughPx`: store the control that puts the
// curve through it, or delete the key when it is back on the chord
// (manualShapes.curveControlOrNull — the same 2 px rule the side canvas had).
export function applyHandleDrag(shape, seg, throughPx) {
  const n = shape.points.length;
  const a = shape.points[seg], c = shape.points[(seg + 1) % n];
  const control = curveControlOrNull(a, c, throughPx);
  const curves = { ...(shape.curves || {}) };
  if (control) curves[seg] = control; else delete curves[seg];
  return { ...shape, curves };
}

export function insertAnchor(shape, seg, atPx) {
  return insertVertexAtSegment(shape, seg, atPx);
}

// Remove one anchor. The two segments that touched it (seg index-1 and seg
// index) become one straight segment; curves on later segments shift down.
// null at the floor: a shape needs three anchors to be a shape.
export function removeAnchor(shape, index) {
  const pts = shape.points || [];
  const n = pts.length;
  if (n <= 3) return null;
  const points = pts.filter((_, i) => i !== index);
  const old = shape.curves || {};
  const curves = {};
  const prev = (index - 1 + n) % n;
  for (const k of Object.keys(old)) {
    const s = Number(k);
    if (s === index || s === prev) continue;
    curves[s > index ? s - 1 : s] = old[k];
  }
  return { ...shape, points, curves };
}

// The re-fit rule (spec §4). The engine fits the bbox of ALL shapes, so a
// node dragged outward would re-centre and rescale everything on the next
// generate. Hold the scale (sizeMm' = new width * mmPerPx — this also seeds
// sizeMm when it was null, the field's resize convention) and shift the
// offsets by the bbox-centre delta, so T() of every unedited point is
// unchanged. Refuses an invalid shape with the first shapeIssues string.
// The engine rounds the applied offsets to the 0.1 mm DST grid, so an
// unedited point can land up to half a unit from where it was — the machine's
// own resolution, and the tests pin that the movement is exactly that rounding
// residual and nothing else (mmPerPx is held to 1e-12).
export function editedElementPatch(element, fit, shapeId, edited) {
  const issues = shapeIssues(flattenShape(edited.points, edited.curves, true));
  if (issues.length) return { error: issues[0] };
  const shapes = (element.shapes || []).map((s) => (s && s.id === shapeId ? edited : s));
  const b0 = flatBBox(element.shapes || []);
  const b1 = flatBBox(shapes);
  if (!b0 || !b1) return { error: "Nothing to fit." };
  const s = fit.mmPerPx;
  const cx0 = (b0.minX + b0.maxX) / 2, cy0 = (b0.minY + b0.maxY) / 2;
  const cx1 = (b1.minX + b1.maxX) / 2, cy1 = (b1.minY + b1.maxY) / 2;
  // Offsets shift from the REQUEST (the element's own offsets), not from
  // `fit.offsetXMm/YMm`: those are the offsets AS APPLIED, already rounded to
  // the 0.1 mm grid, and basing on them fed each edit's rounding into the
  // next — the residual compounded across edits (an unedited point's worst
  // drift over 60 random edits measured 0.097 mm, against 0.065 with the
  // request as the base — final review, drift.mjs). From the request, an
  // unedited point is off by at most ONE rounding (0.05 mm/axis) however
  // many edits came before.
  const patch = {
    shapes,
    sizeMm: (b1.maxX - b1.minX) * s,
    offsetXMm: (element.offsetXMm || 0) + (cx1 - cx0) * s,
    offsetYMm: (element.offsetYMm || 0) + (cy0 - cy1) * s,
  };
  return patch;
}

// The engine's bbox: every VALID shape's flattened outer ring (shapesToRegions
// skips invalid ones, and buildQualityDesign fits what it is given).
function flatBBox(shapes) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const sh of shapes) {
    if (!sh) continue;
    const ring = flattenShape(sh.points, sh.curves, true);
    if (shapeIssues(ring).length) continue;
    for (const p of ring) { if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x; if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y; }
  }
  return isFinite(minX) ? { minX, minY, maxX, maxY } : null;
}
