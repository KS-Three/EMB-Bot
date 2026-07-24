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

// Translates the design's offset (from hoop center, mm, +y UP) by a canvas
// pixel-space drag delta already converted to mm. Canvas dy is DOWN, but
// offset-space y is UP, so a positive canvas dyMm SUBTRACTS from offsetYMm.
// Clamped so the design's mm bbox stays fully inside the hoop; if the
// design is larger than the hoop on an axis, the clamp range collapses to
// 0 (centered) on that axis rather than going negative.
export function dragMove(startOffXMm, startOffYMm, dxMm, dyMm, designWmm, designHmm, hoopWmm, hoopHmm) {
  let offsetXMm = startOffXMm + dxMm;
  let offsetYMm = startOffYMm - dyMm;
  const maxOffX = Math.max(0, (hoopWmm - designWmm) / 2);
  const maxOffY = Math.max(0, (hoopHmm - designHmm) / 2);
  offsetXMm = Math.min(maxOffX, Math.max(-maxOffX, offsetXMm));
  offsetYMm = Math.min(maxOffY, Math.max(-maxOffY, offsetYMm));
  // Normalize -0 (e.g. clamping a large negative delta to a 0-width range)
  // to +0 so callers doing strict equality checks don't trip on the sign bit.
  return { offsetXMm: offsetXMm + 0, offsetYMm: offsetYMm + 0 };
}
