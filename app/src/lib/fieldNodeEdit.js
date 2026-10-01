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
  flattenShape, curveHandlePoint, curveControlOrNull,
  insertVertexAtSegment, nearestSegmentIndex, resolveCutOuts,
  isColumn, shapeRing, shapeProblems, columnRails,
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

export const CUTOUT_HOLD_HINT = "A cut-out has to stay inside its shape.";

// Ruling 3 (spec 2026-09-30 §5): an edit may not take a cut-out out of the
// shape it cuts, nor pull that shape across it. Compared before -> after, so
// a cut-out that already cut nothing is free to move.
export function breaksContainment(shapesBefore, shapesAfter) {
  const before = resolveCutOuts(shapesBefore).parentOf;
  const ids = Object.keys(before).filter((id) => before[id] != null);
  if (!ids.length) return false;
  const after = resolveCutOuts(shapesAfter).parentOf;
  return ids.some((id) => after[id] !== before[id]);
}

// The placement box, tested on the FLATTENED ring. A handle's through point
// (the curve at t = 0.5) can sit on the box edge while the curve bulges past
// it — a quadratic's extreme along an axis is not at t = 0.5 — and a ring
// past the box trips the engine's scale clamp, which rescales the design.
// The ring is the one the ENGINE sees (shapeRing): for a column that is the
// rail ring, which stands half a width outside the spine. This runs on every
// frame of a drag, so it builds rails (linear) and never asks shapeProblems.
export function ringInsideBox(shape, fit, box, epsMm = 0.01) {
  if (!(box && box.wMm > 0 && box.hMm > 0)) return true;
  const hw = box.wMm / 2 + epsMm, hh = box.hMm / 2 + epsMm;
  for (const p of shapeRing(shape)) {
    const [x, y] = pxToFieldMm(fit, p);
    if (Math.abs(x) > hw || Math.abs(y) > hh) return false;
  }
  return true;
}

// A cut-out emits no region, so the engine has no outline for it. The field
// draws and hit-tests this one instead — the authored ring through the same
// fit the engine's outlines use. Unresolved cut-outs are included: one that
// cuts nothing still has to be clickable, to be fixed or deleted.
export function cutOutOutlinesInFieldMm(shapes, fit) {
  const out = [];
  for (const sh of shapes || []) {
    if (!sh || !sh.cutOut || sh.id == null) continue;
    const ring = flattenShape(sh.points, sh.curves, true);
    if (ring.length < 3) continue;
    out.push({ id: String(sh.id), points: ring.map((p) => pxToFieldMm(fit, p)), cutOut: true });
  }
  return out;
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
//
// A column is an OPEN spine: n - 1 segments, so n - 1 handles and no control
// for a closing segment that does not exist (a stale curves[n - 1] is ignored,
// as flattenShape ignores it). It also carries `rails: { a, b }` — the two
// rails the engine sews between, in field mm — so the field can draw the width
// the spine alone does not show. Empty when the column has no usable width.
export function authoredInFieldMm(shape, fit) {
  const pts = shape.points || [];
  const curves = shape.curves || {};
  const n = pts.length;
  const open = isColumn(shape);
  const segCount = open ? Math.max(0, n - 1) : n;
  const anchors = pts.map((p) => pxToFieldMm(fit, p));
  const controls = {};
  const handles = [];
  for (let i = 0; i < segCount; i++) {
    const a = pts[i], c = pts[(i + 1) % n];
    if (curves[i]) controls[i] = pxToFieldMm(fit, curves[i]);
    handles.push(pxToFieldMm(fit, curveHandlePoint(a, c, curves[i])));
  }
  if (!open) return { anchors, controls, handles };
  const r = columnRails(shape);
  const rails = r
    ? { a: r.railA.map((p) => pxToFieldMm(fit, p)), b: r.railB.map((p) => pxToFieldMm(fit, p)) }
    : { a: [], b: [] };
  return { anchors, controls, handles, rails };
}

// What a point is on, in ONE px space (the caller maps the authored geometry
// to canvas px first). Anchors beat handles beat edges: an anchor sits on two
// edges and a handle sits on its edge, so distance alone would hand a
// dead-centre hit to whichever rounds smaller. The edge distance is measured
// against the FLATTENED curve chain, so a bowed segment is hit on its bow.
// `closed === false` is a column's open spine: segment n - 1 (last anchor back
// to the first) does not exist, so no handle and no edge is ever answered for it.
export function hitAuthored(authoredPx, px, py, closed = true) {
  const { anchors, controls, handles } = authoredPx;
  for (let i = 0; i < anchors.length; i++) {
    if (Math.hypot(px - anchors[i][0], py - anchors[i][1]) <= ANCHOR_GRAB_PX) return { kind: "anchor", index: i, atPx: anchors[i] };
  }
  const segCount = closed ? anchors.length : anchors.length - 1;
  for (let i = 0; i < Math.min(handles.length, segCount); i++) {
    if (Math.hypot(px - handles[i][0], py - handles[i][1]) <= HANDLE_GRAB_PX) return { kind: "handle", index: i, atPx: handles[i] };
  }
  const pts = anchors.map(([x, y]) => ({ x, y }));
  const cv = {};
  for (const k of Object.keys(controls)) cv[k] = { x: controls[k][0], y: controls[k][1] };
  const near = nearestSegmentIndex(pts, cv, px, py, closed);
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
//
// A column's floor is two, and its spine does not wrap: an END anchor touches
// only its own segment (anchor 0 -> curves[0]; the last -> curves[n - 2]), so
// only that curve goes. `prev` is -1 at the first anchor rather than n - 1, and
// a stale curves[n - 1] (the closing segment an open spine does not have) is
// dropped instead of being shifted down into a real segment.
export function removeAnchor(shape, index) {
  const pts = shape.points || [];
  const n = pts.length;
  const open = isColumn(shape);
  if (n <= (open ? 2 : 3)) return null;
  const points = pts.filter((_, i) => i !== index);
  const old = shape.curves || {};
  const curves = {};
  const prev = open ? index - 1 : (index - 1 + n) % n;
  for (const k of Object.keys(old)) {
    const s = Number(k);
    if (s === index || s === prev) continue;
    if (open && s >= n - 1) continue;
    curves[s > index ? s - 1 : s] = old[k];
  }
  return { ...shape, points, curves };
}

// The re-fit rule (spec §4). The engine fits the bbox of ALL shapes, so a
// node dragged outward would re-centre and rescale everything on the next
// generate. Hold the scale (sizeMm' = new width * mmPerPx — this also seeds
// sizeMm when it was null, the field's resize convention) and shift the
// offsets by the bbox-centre delta, so T() of every unedited point is
// unchanged. Refuses an invalid shape with the first shapeProblems string
// (a closed shape's ring issues, or a column's). Commit time only: a column's
// check is O(n^2) in its rail ring and must not run per pointer-move frame.
// The engine rounds the applied offsets to the 0.1 mm DST grid, so an
// unedited point can land up to half a unit from where it was — the machine's
// own resolution, and the tests pin that the movement is exactly that rounding
// residual and nothing else (mmPerPx is held to 1e-12).
export function editedElementPatch(element, fit, shapeId, edited) {
  const issues = shapeProblems(edited);
  if (issues.length) return { error: issues[0] };
  const shapes = (element.shapes || []).map((s) => (s && s.id === shapeId ? edited : s));
  if (breaksContainment(element.shapes || [], shapes)) return { error: CUTOUT_HOLD_HINT };
  if (!flatBBox(element.shapes || []) || !flatBBox(shapes)) return { error: "Nothing to fit." };
  return refitShapesPatch(element, fit, shapes);
}

// The re-fit arithmetic on its own: `element` re-sized and re-offset so that
// `shapes` (its new list) sews every unchanged point where it sewed before.
// editedElementPatch uses it for a node edit; the hoop's Cut out switch uses it
// directly, because a cut-out emits no region and so switching one on or off
// can change the bbox the engine fits. When nothing is sewn before, or nothing
// would be after, there is nothing to hold still: the plain { shapes } patch.
export function refitShapesPatch(element, fit, shapes) {
  const b0 = flatBBox(element.shapes || []);
  const b1 = flatBBox(shapes || []);
  if (!b0 || !b1) return { shapes };
  if (!(fit && fit.mmPerPx > 0)) return { error: "Nothing to fit." };
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

// The engine's bbox: every VALID shape's ring as the engine is handed it
// (shapesToRegions skips invalid ones, and buildQualityDesign fits what it is
// given) — a closed shape's flattened outer ring, a column's RAIL ring, which
// is wider than its spine by the drawn width. A cut-out is skipped too: the
// engine never sees it (it emits no region), so the bbox must not either. A
// column is never a cut-out, so a stray flag on one does not hide it.
function flatBBox(shapes) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const sh of shapes) {
    if (!sh || (sh.cutOut && !isColumn(sh))) continue;
    if (shapeProblems(sh).length) continue;
    const ring = shapeRing(sh);
    for (const p of ring) { if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x; if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y; }
  }
  return isFinite(minX) ? { minX, minY, maxX, maxY } : null;
}

// ---- A column's width, in millimetres -------------------------------------
// Kent's ruling 12 (spec 2026-09-30 §6, amended 2026-10-01): a column stores
// its width as geometry — `widthPx`, authored canvas px — so a resize scales it
// with everything else. Millimetres are a VIEW through the element's fit, and
// nothing here stores one.

// The floor a typed width is held to. Not a sewing limit (the engine clamps
// nothing, ruling 5) — only what keeps `widthPx` positive, so the column keeps
// its rails and stays selectable to be fixed.
const COLUMN_MIN_TYPED_MM = 0.1;

// The DRAWN width at this fit.
export function columnWidthMm(shape, fit) {
  return (shape.widthPx || 0) * fit.mmPerPx;
}

// A copy of the column whose drawn width is `mm` at this fit. The caller
// commits it through refitShapesPatch: the rail ring is the engine's bbox, so
// a new width can move the fit unless the re-fit rule holds it.
export function withColumnWidthMm(shape, fit, mm) {
  const want = typeof mm === "number" && isFinite(mm) ? Math.max(COLUMN_MIN_TYPED_MM, mm) : COLUMN_MIN_TYPED_MM;
  return { ...shape, widthPx: want / fit.mmPerPx };
}

// The SEWN width: satin pushes each rail out by half the fabric's pull
// compensation, a fixed amount on top of the drawn width at any size.
export function columnSewnMm(shape, fit, pullCompMm) {
  return columnWidthMm(shape, fit) + (pullCompMm || 0);
}
