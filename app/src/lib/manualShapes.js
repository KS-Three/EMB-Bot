// Manual digitizing mode (Studio's third content type, MVP slice): pure
// logic for a hand-drawn shape list. Zero image analysis anywhere in this
// file — every shape and its stitch assignment comes straight from what the
// user drew and picked. The one job here is turning that shape list into
// EXACTLY the colorRegions shape src/digitize.js's buildQualityDesign
// already accepts (the same shape imageRegions.js's flatToRegions produces
// for Image mode) so generation rides the identical pull-comp/underlay/
// sequencing pipeline — see digitize.js's shape.tierOverride /
// shape.angleOverride, both additive hooks this module is the first caller
// of on the Studio side.

// A nominal authoring-canvas size manual shapes are drawn against. Only the
// RELATIVE geometry between shapes matters — buildQualityDesign fits the
// combined bbox to the garment/hoop regardless of absolute px scale — so any
// fixed canvas size + pxPerMm pair produces the same final design. Mirrors
// imageRegions.js's own NOMINAL_LONG_MM approach.
export const CANVAS_W = 600;
export const CANVAS_H = 400;
export const NOMINAL_LONG_MM = 100;
export const PX_PER_MM = Math.max(CANVAS_W, CANVAS_H) / NOMINAL_LONG_MM;

// Canvas-pixel radius for "click near the shape's start point" (closing a
// shape by clicking back on its first point).
export const CLOSE_RADIUS_PX = 10;

const MIN_AREA_PX2 = 4; // degenerate/zero-area guard (a mis-click sliver)

function polygonArea(points) {
  let a = 0;
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    a += points[j].x * points[i].y - points[i].x * points[j].y;
  }
  return Math.abs(a) / 2;
}

// A shape is sewable once it has >= 3 points and real (non-degenerate)
// area — two points on top of each other, or three collinear points, can't
// trace to a real polygon.
export function isValidShape(points) {
  return Array.isArray(points) && points.length >= 3 && polygonArea(points) > MIN_AREA_PX2;
}

// Whether (x,y) is within closing distance of a shape's own first point —
// the "click the start point to close" gesture. Requires at least 2 points
// already placed (closing a 1-point "shape" is meaningless).
export function isNearStart(points, x, y) {
  if (!Array.isArray(points) || points.length < 2) return false;
  const p0 = points[0];
  return Math.hypot(x - p0.x, y - p0.y) <= CLOSE_RADIUS_PX;
}

// Convert an element's COMPLETED shapes into buildQualityDesign's
// colorRegions input. Each shape becomes its OWN region (a manual choice,
// not an auto-merge-by-color step: two shapes the user happens to color the
// same still sew as two independently-ordered pieces, matching how the
// canvas draws them one at a time). Invalid/degenerate shapes are silently
// skipped, mirroring flatToRegions dropping empty-geometry palette entries,
// rather than throwing — one bad shape shouldn't block generating the rest.
export function shapesToRegions(shapes) {
  const regions = [];
  for (const shape of shapes || []) {
    if (!shape || !isValidShape(shape.points)) continue;
    const angleOverride = (typeof shape.angleDeg === "number" && isFinite(shape.angleDeg)) ? shape.angleDeg : null;
    regions.push({
      rgb: Array.isArray(shape.colorRgb) ? shape.colorRgb : [20, 20, 20],
      shapes: [{
        outer: shape.points.map((p) => ({ x: p.x, y: p.y })),
        holes: [],
        tierOverride: shape.stitchType === "satin" ? "satin" : "fill",
        angleOverride,
      }],
    });
  }
  return { regions, pxPerMm: PX_PER_MM };
}
