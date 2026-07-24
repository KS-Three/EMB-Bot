import { EMB } from "./emb.js";

// Ported verbatim from the old tool's imageToRegions (src/app.js:318-358).
// Studio doesn't have per-swatch angle overrides yet, so that part is
// skipped — every shape uses the engine's per-shape auto angle.
const SIMPLIFY_TOL = 1.6; // Douglas-Peucker tolerance (px)
const DESPECKLE_SHARE = 0.0004; // drop traced shapes below w*h*this (px^2)
const MAX_SHAPES_PER_COLOR = 60; // cap shapes per color (largest kept first)
const NOMINAL_LONG_MM = 50; // pre-fit physical size of the source art long side

// Absolute polygon area (px^2); thin wrapper so region/hole filtering reads
// cleanly, matching src/app.js's area() helper.
function area(poly) {
  return EMB.polygonArea(poly);
}

// Build per-color masks from a flattened image (palette + indices) and trace
// them into ColorRegion[], so the generated stitches match the flatten
// preview exactly. flat: { palette, indices, w, h } from flattenRGBA().
export function flatToRegions(flat) {
  const w = flat.w, h = flat.h;
  const palette = flat.palette, indices = flat.indices;

  const despeckleMin = w * h * DESPECKLE_SHARE; // area-relative per-shape despeckle
  const holeMin = Math.max(6, despeckleMin * 0.3); // keep smaller holes (counters)

  const regions = [];
  for (let ci = 0; ci < palette.length; ci++) {
    const mask = new Uint8Array(w * h);
    for (let p = 0; p < indices.length; p++) {
      if (indices[p] === ci) mask[p] = 1; // 255 = transparent -> skipped (ci never reaches it)
    }
    // Hole-aware tracing: each blob -> { outer, holes[] }. Simplify every
    // ring, drop specks (outer) and pinholes (holes), then keep the largest
    // shapes up to the per-color cap.
    let shapes = EMB.traceRegions(mask, w, h)
      .map((s) => ({
        outer: EMB.simplify(s.outer, SIMPLIFY_TOL),
        holes: s.holes
          .map((hh) => EMB.simplify(hh, SIMPLIFY_TOL))
          .filter((hh) => hh.length >= 4 && area(hh) > holeMin),
      }))
      .filter((s) => s.outer.length >= 4 && area(s.outer) > despeckleMin);
    shapes.sort((a, b) => area(b.outer) - area(a.outer));
    if (shapes.length > MAX_SHAPES_PER_COLOR) shapes = shapes.slice(0, MAX_SHAPES_PER_COLOR);
    if (shapes.length === 0) continue; // no geometry for this color
    regions.push({ rgb: palette[ci], shapes });
  }

  // Map the working image long side to NOMINAL_LONG_MM; fit handles final size.
  const pxPerMm = Math.max(w, h) / NOMINAL_LONG_MM;
  return { regions, pxPerMm };
}
