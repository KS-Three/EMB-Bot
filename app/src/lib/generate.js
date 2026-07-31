import { EMB } from "./emb.js";
import { flatToRegions } from "./imageRegions.js";
import { combineDesigns, bboxMmFromStitches } from "./combine.js";
import { decodedFromDesignCached, digitizedBlockColors } from "./digitizer.js";

// Generates a single element's Design, or null if the element isn't ready
// to sew yet (empty text / no flattened image state). Throws only on real
// errors — e.g. an element referencing a font key the engine doesn't have.
//
// `garment` is the resolved garment object (EMB.getGarment(project.garmentId)),
// shared across every element in a project so callers only look it up once.
// `runtime` carries per-project state that doesn't belong on the persisted
// project itself: `runtime.flats[element.id]` is the flattened palette/index
// image (from flattenRGBA) for an image element, keyed by element id so each
// image element in a multi-element project keeps its own working image.
// Decoded-DST cache. Drag/resize regenerate every element per frame (the
// deliberate "one cheap full regen path" choice in EmbroideryField), so the
// base64 -> bytes -> record-walk decode must not re-run 60x/s for a design
// that never changes. Keyed by the base64 string itself: a re-import is a
// new string = new entry, and the tiny cap just stops a long session from
// pinning every file ever uploaded.
const dstCache = new Map();
const DST_CACHE_MAX = 8;

function decodeCached(dstBase64) {
  let hit = dstCache.get(dstBase64);
  if (hit) return hit;
  const bin = atob(dstBase64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  hit = EMB.decodeDST(bytes);
  if (dstCache.size >= DST_CACHE_MAX) {
    dstCache.delete(dstCache.keys().next().value); // drop oldest insertion
  }
  dstCache.set(dstBase64, hit);
  return hit;
}

export function generateElement(element, garment, runtime) {
  if (!element) return null;

  if (element.type === "design") {
    if (!element.dstBase64) return null;
    const decoded = decodeCached(element.dstBase64);
    return EMB.buildImportedDesign(decoded, {
      garment,
      targetWidthMm: element.sizeMm || undefined,
      rotationDeg: element.rotationDeg || 0,
      offsetXMm: element.offsetXMm || 0,
      offsetYMm: element.offsetYMm || 0,
      blockColors: element.blockColors || {},
    });
  }

  if (element.type === "digitized") {
    // Auto-digitized artwork. The element carries the BAKED service result
    // (a Design in decodeDST's exact space: 0.1 mm ints, +y up), so
    // generation is fully offline and rides the SAME imported-design path a
    // .dst upload does — scale/hoop-clamp/rotate/offset in one place, no
    // second implementation to drift. digitizer.js adapts result -> the
    // decoded shape (strips the trailing "end", centers on the stitch bbox)
    // and supplies the service's real thread palette as block colors, with
    // the user's per-block overrides on top.
    if (!element.result) return null;
    const decoded = decodedFromDesignCached(element.result);
    if (!decoded) return null;
    return EMB.buildImportedDesign(decoded, {
      garment,
      targetWidthMm: element.sizeMm || undefined,
      rotationDeg: element.rotationDeg || 0,
      offsetXMm: element.offsetXMm || 0,
      offsetYMm: element.offsetYMm || 0,
      blockColors: digitizedBlockColors(element),
    });
  }

  if (element.type === "image") {
    const flats = (runtime && runtime.flats) || {};
    const flat = flats[element.id];
    if (!flat) return null;
    // { threadRgb: element.threadRgb } is forward-compatible: flatToRegions
    // doesn't read a second argument yet (Task 3 adds threadRgb overrides to
    // imageRegions.js) so this is simply ignored today.
    const { regions, pxPerMm } = flatToRegions(flat, { threadRgb: element.threadRgb });
    const fabric = EMB.getFabric(EMB.fabricForGarment(garment.id));
    return EMB.buildQualityDesign(regions, {
      garment, fabric, pxPerMm, densityMm: 0.4, satinMaxWidthMm: 3.0,
      underlay: element.underlay,
      targetWidthMm: element.sizeMm || undefined,
      offsetXMm: element.offsetXMm || 0,
      offsetYMm: element.offsetYMm || 0,
    });
  }

  // text
  const text = (element.text || "").trim();
  if (!text) return null;
  const fontData = (EMB.SATIN_FONTS || {})[element.fontKey];
  if (!fontData) throw new Error("Unknown font: " + element.fontKey);
  return EMB.buildLetteringDesign(fontData, text, {
    garment, pxPerMm: 8, densityMm: 0.4, underlay: element.underlay,
    rgb: element.colorRgb,
    colorRanges: element.colorRanges || [],
    weightPreset: element.weightPreset || "normal",
    slantDeg: element.slantDeg || 0,
    targetWidthMm: element.sizeMm || undefined,
    offsetXMm: element.offsetXMm || 0,
    offsetYMm: element.offsetYMm || 0,
    letterSpacingMm: element.letterSpacingMm || 0,
    arcDeg: element.arcDeg || 0,
    rotationDeg: element.rotationDeg || 0,
    align: element.align || "center",
  });
}

// Generates every ready element in a project (in array order), combines them
// into one sewable design, and reports each element's own bbox (mm) so the
// UI can draw a per-element selection overlay against the combined preview.
// Elements that aren't ready (see generateElement) are silently skipped —
// not an error, just nothing to contribute yet. Returns
// { combined: null, perElement: [] } when nothing in the project is ready.
export function generateAll(project, runtime) {
  const garment = EMB.getGarment(project.garmentId);
  const perElement = [];
  for (const element of project.elements || []) {
    const design = generateElement(element, garment, runtime);
    if (!design) continue;
    perElement.push({ id: element.id, design, bboxMm: bboxMmFromStitches(design.stitches) });
  }
  if (!perElement.length) return { combined: null, perElement: [] };
  // SEW order: on cap garments (same predicate as the engine's capMode)
  // elements sew bottom-up — lowest bbox first, bill toward crown — matching
  // the engine's per-element center-out rule, so a stacked cap design pushes
  // fabric up off the unstable crown seam. bboxMm is +y UP, so ascending
  // y0 = lowest first. Everywhere else the order stays element-list order,
  // unchanged. perElement is returned in the SAME (sew) order as the
  // combined stitches because sew order IS paint order: EmbroideryField's
  // topmost-wins hit-testing walks perElement-derived rects assuming later
  // entries are drawn on top, and later-sewn thread genuinely sits on top.
  // The element LIST rows key off project.elements directly, not this.
  const capMode = garment && (garment.id === "hat_front" || garment.id === "beanie");
  const ordered = capMode
    ? perElement.slice().sort((a, b) => a.bboxMm.y0 - b.bboxMm.y0)
    : perElement;
  return { combined: combineDesigns(ordered.map((pe) => pe.design)), perElement: ordered };
}

// Back-compat convenience for a SINGLE-text-element project: everything the
// pre-multi-element UI/specs need from "give me the one design for this
// project" without them having to know about generateAll's { combined,
// perElement } shape. Works for any project with >=1 ready element (not just
// text) since it's just generateAll's combined result — the "single text
// element" framing is the common case, not an enforced constraint.
export function generateDesign(project) {
  const { combined } = generateAll(project, {});
  if (!combined) throw new Error("Type some text first.");
  return combined;
}

// Deprecated: legacy shim for callers (pre-Task-4/5 UI) that still hand
// generate.js a flat, v1-ish object — element fields (nColors/removeBg/
// threadRgb/underlay/sizeMm/offsetXMm/offsetYMm) spread directly onto a
// `garmentId`-bearing object rather than nested under project.elements.
// Builds a throwaway image element from those fields, feeds it through the
// same generateElement() path a real project would use, and keeps the old
// "no shapes" error message existing callers' catch blocks expect. Prefer
// generateAll(project, runtime)/generateElement for anything new.
export function generateImageDesign(flat, projectLike) {
  const garment = EMB.getGarment(projectLike.garmentId);
  const element = {
    id: projectLike.id || "e1",
    type: "image",
    nColors: projectLike.nColors,
    removeBg: projectLike.removeBg,
    threadRgb: projectLike.threadRgb || {},
    underlay: projectLike.underlay,
    sizeMm: projectLike.sizeMm,
    offsetXMm: projectLike.offsetXMm,
    offsetYMm: projectLike.offsetYMm,
  };
  const design = generateElement(element, garment, { flats: { [element.id]: flat } });
  if (!design) throw new Error("Upload a logo or image first.");
  if (!design.stitchCount) throw new Error("No shapes found to stitch — try a simpler image or fewer colors.");
  return design;
}
