// Pure hit-test / drag math for direct manipulation of the design on the
// embroidery field. Kept free of DOM/canvas APIs so it's cheap to unit-test;
// EmbroideryField.svelte supplies the pointer events and canvas coordinates.

// Converts a design's mm-space bounding box (hoop mm-space, +y UP — see
// preview.js's designBBoxMm / hoopTransform) into a canvas-pixel rect, via
// the `toCanvas(xMm, yMm) -> {x,y}` transform returned by renderRealistic.
// Because +y is UP in mm-space but canvas y grows DOWN, the mm bbox's "top"
// (y1, the larger mm y) lands at the SMALLER canvas y. Rather than assume
// which corner ends up top-left, we project both mm corners through
// toCanvas and take min/max — correct regardless of transform sign.
export function designRectPx(bboxMm, toCanvas) {
  if (!bboxMm) return null;
  const p0 = toCanvas(bboxMm.x0, bboxMm.y0);
  const p1 = toCanvas(bboxMm.x1, bboxMm.y1);
  const x = Math.min(p0.x, p1.x);
  const y = Math.min(p0.y, p1.y);
  return { x, y, w: Math.abs(p1.x - p0.x), h: Math.abs(p1.y - p0.y) };
}

// Hit-tests a canvas point against a design rect's corner handles first
// (a circular hit area of radius handleR around each corner — handles are
// allowed to stick out past the rect edge, which is why they're checked
// before the body test), then the rect body, else "none".
export function hitTest(rect, px, py, handleR = 8) {
  if (!rect) return "none";
  const corners = {
    nw: { x: rect.x, y: rect.y },
    ne: { x: rect.x + rect.w, y: rect.y },
    sw: { x: rect.x, y: rect.y + rect.h },
    se: { x: rect.x + rect.w, y: rect.y + rect.h },
  };
  for (const name of ["nw", "ne", "sw", "se"]) {
    const c = corners[name];
    const dx = px - c.x, dy = py - c.y;
    if (Math.sqrt(dx * dx + dy * dy) <= handleR) return name;
  }
  if (px >= rect.x && px <= rect.x + rect.w && py >= rect.y && py <= rect.y + rect.h) return "body";
  return "none";
}

// Sign of dx/dy that means "grow" for each dragged corner (canvas-pixel
// convention: +x right, +y down). E.g. dragging the "se" handle right or
// down grows the design; dragging "nw" left or up grows it.
const GROWTH_SIGN = {
  se: { sx: 1, sy: 1 },
  ne: { sx: 1, sy: -1 },
  sw: { sx: -1, sy: 1 },
  nw: { sx: -1, sy: -1 },
};

// Aspect-locked resize from a dragged corner. Rule (documented, predictable):
// project both the raw dx and dy onto "growth" using the dragged corner's
// sign convention, convert the dy contribution into a width-equivalent delta
// via the design's aspect ratio (w/h), then average the two estimates:
//   widthDelta = (growthDx + growthDy * (w/h)) / 2
// For a corner drag straight along one axis this reduces to using just that
// axis's delta; for a diagonal drag it blends both, which is what keeps the
// result feeling proportional regardless of drag angle. Result is clamped to
// [minWmm, maxWmm].
export function dragResize(startWidthMm, startHeightMm, handle, dxMm, dyMm, minWmm, maxWmm) {
  const w = startWidthMm;
  const h = startHeightMm || startWidthMm || 1;
  const aspect = h > 0 ? w / h : 1;
  const sign = GROWTH_SIGN[handle] || GROWTH_SIGN.se;
  const growthDx = sign.sx * dxMm;
  const growthDy = sign.sy * dyMm;
  const widthDelta = (growthDx + growthDy * aspect) / 2;
  let newW = startWidthMm + widthDelta;
  if (newW < minWmm) newW = minWmm;
  if (newW > maxWmm) newW = maxWmm;
  return newW;
}

// Clamps an absolute design offset (from hoop center, mm, +y UP) so the
// design's mm bbox stays fully inside the hoop. If the design is larger
// than the hoop on an axis, the clamp range collapses to 0 (centered) on
// that axis rather than going negative.
//
// Standalone (not just via dragMove) so callers that already have an
// absolute offset in hand -- e.g. EmbroideryField re-validating a
// persisted/stale offset after a garment or size change, rather than a
// live pointer drag -- can re-clamp without synthesizing a fake drag delta.
export function clampOffsets(offXMm, offYMm, designWmm, designHmm, hoopWmm, hoopHmm) {
  const maxOffX = Math.max(0, (hoopWmm - designWmm) / 2);
  const maxOffY = Math.max(0, (hoopHmm - designHmm) / 2);
  const offsetXMm = Math.min(maxOffX, Math.max(-maxOffX, offXMm));
  const offsetYMm = Math.min(maxOffY, Math.max(-maxOffY, offYMm));
  // Normalize -0 (e.g. clamping a large negative delta to a 0-width range)
  // to +0 so callers doing strict equality checks don't trip on the sign bit.
  return { offsetXMm: offsetXMm + 0, offsetYMm: offsetYMm + 0 };
}

// One-axis "flush align": the offset that puts the design's edge against the
// hoop's edge, or 0 for centered. The extreme offset on an axis IS
// (hoop - design)/2 — the very bound clampOffsets clamps to — so aligning is
// just picking -max / 0 / +max, and an aligned offset is always already
// in-range (clampOffsets is a no-op on it).
//
// Modes cover BOTH axes because the math is identical: x uses left/right,
// y uses bottom/top. +y is UP in offset-space (see clampOffsets), so "top"
// is +max, not -max. A design larger than the hoop has no slack at all, so
// every mode collapses to 0 (centered) — the same degenerate case
// clampOffsets already handles by collapsing its range.
// The trailing "+ 0" normalizes -0 (negating a zero-width slack range) to +0,
// exactly as clampOffsets does, so a no-slack align can't hand callers a
// sign-bit that fails Object.is/strict-equality checks.
export function alignOffset(mode, designMm, hoopMm) {
  const max = Math.max(0, (hoopMm - designMm) / 2);
  if (mode === "left" || mode === "bottom") return -max + 0;
  if (mode === "right" || mode === "top") return max;
  return 0;
}

// Clamps a view pan offset so a pan/zoom can never push the hoop entirely
// off canvas -- the reachable travel grows with zoom (more zoomed in => more
// slack to pan around), plus a flat 40px of slack so even at zoom===MIN_ZOOM
// there's a little play. Shared by EmbroideryField's zoomBy() (wheel/button
// zoom, which solves for a new pan to keep the zoom anchor fixed) AND the
// pan-drag branch of onPointerMove -- pointer capture lets a pan drag travel
// across the whole screen, well past the canvas edge, so the drag branch
// needs the SAME clamp zoomBy already applied, not an unclamped assignment.
export function clampPan(panX, panY, zoom, cw, ch) {
  const maxPanX = (cw * (zoom - 1)) / 2 + 40;
  const maxPanY = (ch * (zoom - 1)) / 2 + 40;
  return {
    panX: Math.min(maxPanX, Math.max(-maxPanX, panX)),
    panY: Math.min(maxPanY, Math.max(-maxPanY, panY)),
  };
}

// Picks which element (by id) a canvas point falls in, for click-to-select
// on a multi-element field. `rects` is an array of { id, x, y, w, h } canvas
// rects (see designRectPx), one per ready element, in the SAME order as
// project.elements -- i.e. paint order, later entries drawn on top of
// earlier ones. Overlap resolution therefore means "topmost wins": we scan
// every rect and keep overwriting the hit on each match, so the LAST
// matching rect in array order is what's returned. No match anywhere ->
// null (a miss, e.g. an empty-space click, which callers should treat as
// "leave the current selection alone").
export function pickElement(rects, px, py) {
  let hit = null;
  for (const r of rects || []) {
    if (px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h) hit = r.id;
  }
  return hit;
}

// Translates the design's offset (from hoop center, mm, +y UP) by a canvas
// pixel-space drag delta already converted to mm, then delegates to
// clampOffsets. Canvas dy is DOWN, but offset-space y is UP, so a positive
// canvas dyMm SUBTRACTS from offsetYMm.
export function dragMove(startOffXMm, startOffYMm, dxMm, dyMm, designWmm, designHmm, hoopWmm, hoopHmm) {
  const offsetXMm = startOffXMm + dxMm;
  const offsetYMm = startOffYMm - dyMm;
  return clampOffsets(offsetXMm, offsetYMm, designWmm, designHmm, hoopWmm, hoopHmm);
}

// ---- auto-snap (move / resize) ---------------------------------------------

// Collects the alignment lines a dragged element can snap to: every other
// element's edges and center (per axis), plus the hoop's centerlines (x=0,
// y=0 in hoop mm-space — offsets are measured from hoop center, so the
// centerlines are the origin axes). `otherBBoxes` is [{x0,y0,x1,y1}] in
// absolute hoop mm-space (+y UP), i.e. exactly perElement bboxMm shapes.
export function buildSnapLines(otherBBoxes, opts = {}) {
  const xs = [];
  const ys = [];
  if (opts.hoopCenter !== false) {
    xs.push(0);
    ys.push(0);
  }
  for (const b of otherBBoxes || []) {
    xs.push(b.x0, (b.x0 + b.x1) / 2, b.x1);
    ys.push(b.y0, (b.y0 + b.y1) / 2, b.y1);
  }
  return { xs, ys };
}

// Snaps a proposed bbox (absolute hoop mm-space) against buildSnapLines'
// candidates. Each axis snaps independently: the bbox's own three lines
// (low edge, center, high edge) are compared against every candidate, and
// the smallest |candidate - own| at or under thresholdMm wins. Returns the
// mm adjustment to apply to the element's offset plus the mm position of
// the line it snapped to (null = no snap on that axis) so the caller can
// draw a guide there.
export function snapMove(bbox, lines, thresholdMm) {
  const own = (lo, hi) => [lo, (lo + hi) / 2, hi];
  const best = (ownLines, candidates) => {
    let diff = null;
    let line = null;
    for (const o of ownLines) {
      for (const c of candidates || []) {
        const d = c - o;
        if (Math.abs(d) <= thresholdMm && (diff === null || Math.abs(d) < Math.abs(diff))) {
          diff = d;
          line = c;
        }
      }
    }
    return { diff: diff === null ? 0 : diff, line };
  };
  const bx = best(own(bbox.x0, bbox.x1), lines.xs);
  const by = best(own(bbox.y0, bbox.y1), lines.ys);
  return { dx: bx.diff, dy: by.diff, guideXMm: bx.line, guideYMm: by.line };
}

// Size-match snapping for an aspect-locked resize: if the proposed width is
// within thresholdMm of another element's width — or of the width that would
// make the dragged element's HEIGHT equal another element's height (via the
// dragged element's aspect = w/h) — snap to exact equality. Nearest
// candidate wins. Returns { widthMm, match: "width"|"height"|null }.
export function snapResizeWidth(widthMm, aspect, otherDims, thresholdMm) {
  let bestW = widthMm;
  let bestD = null;
  let match = null;
  for (const o of otherDims || []) {
    const cands = [
      { target: o.w, kind: "width" },
      { target: o.h * aspect, kind: "height" },
    ];
    for (const c of cands) {
      const d = Math.abs(widthMm - c.target);
      if (d <= thresholdMm && (bestD === null || d < bestD)) {
        bestD = d;
        bestW = c.target;
        match = c.kind;
      }
    }
  }
  return { widthMm: bestW, match };
}

// ---- multi-select group geometry -------------------------------------------

// Union of member mm bboxes — the "group box" a multi-selection drags,
// snaps, and resizes as. Null for an empty list.
export function unionBBox(bboxes) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const b of bboxes || []) {
    if (b.x0 < x0) x0 = b.x0;
    if (b.y0 < y0) y0 = b.y0;
    if (b.x1 > x1) x1 = b.x1;
    if (b.y1 > y1) y1 = b.y1;
  }
  return x0 === Infinity ? null : { x0, y0, x1, y1 };
}

// Clamps a group-move delta so the group's union bbox stays inside the hoop
// (hoop spans ±hoop/2 about the origin). Per-axis; a group larger than the
// hoop on an axis can't move on that axis (delta collapses to 0) — the
// group analog of clampOffsets collapsing its range. "+ 0" normalizes -0.
export function clampGroupDelta(dxMm, dyMm, groupBBox, hoopWmm, hoopHmm) {
  const clamp1 = (d, lo, hi) => (lo > hi ? 0 : Math.min(hi, Math.max(lo, d)) + 0);
  return {
    dxMm: clamp1(dxMm, -hoopWmm / 2 - groupBBox.x0, hoopWmm / 2 - groupBBox.x1),
    dyMm: clamp1(dyMm, -hoopHmm / 2 - groupBBox.y0, hoopHmm / 2 - groupBBox.y1),
  };
}

// Group resize fan-out: scale every member's generation target AND its
// offset about the group center by one factor, so the layout scales as a
// unit (relative spacing preserved). members:
//   [{ id, widthMm (rendered), targetMm (sizeMm at drag start), offsetXMm, offsetYMm }]
// The factor is raised if any member's rendered width would fall below
// minWmm (the group can never shrink a member past the stitchable minimum),
// and callers should cap it beforehand so the scaled union fits the hoop.
// Returns { patches: { id: {sizeMm, offsetXMm, offsetYMm} }, factor }.
export function groupResizePatches(members, factor, groupCxMm, groupCyMm, minWmm) {
  let f = factor;
  for (const m of members || []) {
    if (m.widthMm * f < minWmm) f = minWmm / m.widthMm;
  }
  const patches = {};
  for (const m of members || []) {
    patches[m.id] = {
      sizeMm: m.targetMm * f,
      offsetXMm: groupCxMm + ((m.offsetXMm || 0) - groupCxMm) * f,
      offsetYMm: groupCyMm + ((m.offsetYMm || 0) - groupCyMm) * f,
    };
  }
  return { patches, factor: f };
}

// ---- rotate handle ----------------------------------------------------------

// Canvas-px position of the rotate handle's grip: a "lollipop" centered
// above the selection rect's top edge, stalkPx above it. opts.flip hangs it
// BELOW the bottom edge instead — the caller flips when the normal position
// would land above the canvas top (zoomed/panned views), where a grip would
// be undraggable because the pointer can't reach it.
export function rotateHandlePx(rect, stalkPx = 22, opts = {}) {
  return {
    x: rect.x + rect.w / 2,
    y: opts.flip ? rect.y + rect.h + stalkPx : rect.y - stalkPx,
  };
}

// Pointer angle about a canvas-px center, in the mm-space's y-UP convention
// (so it increases counterclockwise ON SCREEN, matching the stitch engine's
// positive-rotationDeg direction — see digitize.js's rotation transform).
function pointerAngleDeg(centerPx, p) {
  return (Math.atan2(centerPx.y - p.y, p.x - centerPx.x) * 180) / Math.PI;
}

// Rotation drag: delta-based (the element turns by however far the pointer
// has swept around the center since the grab — no jump on grab), rounded to
// whole degrees and normalized to [0, 360). Unless opts.free, angles within
// magnetDeg (default 3°) of a 45° multiple snap to it — same philosophy as
// position snapping: precise everywhere, magnetic at the angles that matter.
export function dragRotate(startDeg, centerPx, startPx, curPx, opts = {}) {
  const delta = pointerAngleDeg(centerPx, curPx) - pointerAngleDeg(centerPx, startPx);
  let deg = Math.round(startDeg + delta);
  deg = ((deg % 360) + 360) % 360;
  if (!opts.free) {
    const magnetDeg = opts.magnetDeg == null ? 3 : opts.magnetDeg;
    const nearest = Math.round(deg / 45) * 45;
    if (Math.abs(deg - nearest) <= magnetDeg) deg = nearest % 360;
  }
  return deg;
}
