import { EMB } from "./emb.js";
import { flatToRegions } from "./imageRegions.js";
import { shapesToRegions } from "./manualShapes.js";
import { shapePresetPoints, DEFAULT_SHAPE_SIZE_MM } from "./shapePresets.js";
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

  if (element.type === "manual") {
    // Manual digitizing mode: the user drew every shape and picked its
    // stitch type/color/angle by hand — zero auto-analysis. shapesToRegions
    // turns element.shapes into the SAME colorRegions shape Image mode
    // feeds buildQualityDesign, riding the identical pull-comp/underlay/
    // trims/sequencing pipeline (digitize.js's shape.tierOverride is what
    // makes the manual satin/fill CHOICE stick instead of being
    // re-classified by width/branch-guard heuristics).
    const { regions, pxPerMm } = shapesToRegions(element.shapes);
    if (!regions.length) return null;
    const fabric = EMB.getFabric(EMB.fabricForGarment(garment.id));
    return EMB.buildQualityDesign(regions, {
      garment, fabric, pxPerMm, densityMm: 0.4,
      // DRAW ORDER IS SEW ORDER here, so the brightness sort must not run.
      //
      // digitize.js sequences light-to-dark by default (`darkOnTop`), which is
      // right for IMAGE mode: nothing in a raster says which colour the artist
      // meant on top, and dark-last is the professional default. It is wrong
      // here. In manual mode the user drew these shapes in an order they can
      // see -- ManualPanel paints `for (const s of shapeList)`, later over
      // earlier, and hit-tests back-to-front to match -- and shapesToRegions
      // preserves that order deliberately, one region per shape.
      //
      // Without this, a navy rectangle drawn first and a cream circle drawn on
      // top of it sew cream-then-navy: the navy covers the circle the user put
      // above it. Measured against the real engine 2026-08-26 -- input order
      // [navy, cream] came back as colors [cream, navy], exactly reversed --
      // and there is no reorder control in ManualPanel, so the stacking the
      // user drew was simply unreachable.
      //
      // Kent's call, 2026-08-26. Image mode keeps the heuristic (see the
      // artwork branch above); this changes what already-saved manual designs
      // sew, which is the point.
      darkOnTop: false,
      underlay: element.underlay,
      targetWidthMm: element.sizeMm || undefined,
      offsetXMm: element.offsetXMm || 0,
      offsetYMm: element.offsetYMm || 0,
    });
  }

  if (element.type === "shape") {
    // Preset basic shapes (circle/rect/heart/star): the generator emits a
    // point ring in EXACTLY the model manual draw uses, so this branch is
    // the manual branch with the ring computed instead of hand-drawn —
    // same shapesToRegions, same buildQualityDesign, no parallel pipeline.
    // stitchType "auto" means shapesToRegions sends no tierOverride:
    // satin-vs-fill is the engine classifier's call here, unlike manual
    // mode where that choice is explicitly the user's.
    const points = shapePresetPoints(
      element.kind,
      element.params,
      element.sizeMm || DEFAULT_SHAPE_SIZE_MM
    );
    const { regions, pxPerMm } = shapesToRegions([
      { points, curves: {}, stitchType: "auto", colorRgb: element.colorRgb, angleDeg: null },
    ]);
    if (!regions.length) return null;
    const fabric = EMB.getFabric(EMB.fabricForGarment(garment.id));
    return EMB.buildQualityDesign(regions, {
      garment, fabric, pxPerMm, densityMm: 0.4,
      // Same rule as the manual branch above. A no-op today -- this branch
      // always emits exactly one region, and a sort of one element cannot
      // reorder anything -- but it is the same code path the moment presets
      // can be stacked, and the two branches drifting apart is precisely how
      // the manual one ended up wrong.
      darkOnTop: false,
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
// Formats an `unsupported` array for a person: quoted, comma-separated, and
// capped so a paragraph of unrenderable text does not become a paragraph of
// error. Exported (and tested) rather than inlined in the component, matching
// hoopFitNote — message wording is logic, and logic in a .svelte file is logic
// nobody unit-tests.
// The width-guard note for a text element, from buildLetteringDesign's
// `lettering` report (see satinfont.layoutText). One line, the most useful
// fact first: a cap under the 4 mm floor is the CAUSE of everything below it,
// so it wins; then a font that is mostly hairline at this size (below its own
// band — the fix is size or font, not a tweak); then what the engine did about
// the odd hairline (sewn as running stitch, not dropped); then lettering that
// is mostly under the needle minimum. Empty string when there is nothing to
// say, so callers can `{#if}` on it like the hoop and unsupported notes.
//
// The two SHARE thresholds are UI policy, not physics: "mostly" means half
// the stroke length, and the thin note stays quiet under a quarter because
// nearly every authored column tapers through 1 mm at its tips, so a lower
// bar would print on almost every design and mean nothing. Every mm figure
// quoted comes from the report itself, so the note can never drift from the
// constant the engine actually applied. Exported and tested for the same
// reason charList is: wording is logic.
export function letteringNote(l) {
  if (!l || !(l.strokeMm > 0)) return "";
  const share = (mm) => mm / l.strokeMm;
  const pct = (mm) => Math.round(100 * share(mm));
  if (l.capMm > 0 && l.capMm < l.capFloorMm) {
    return `Letters ${l.capMm.toFixed(1)} mm tall — under the ${l.capFloorMm} mm floor, thin strokes will shred`;
  }
  if (share(l.hairlineMm) >= 0.5) {
    return `${pct(l.hairlineMm)}% of this lettering is under ${l.crossFloorMm} mm wide at this size and sews as running stitch — size up or pick a bolder font`;
  }
  if (l.hairlineSpans > 0) {
    const n = l.hairlineSpans;
    return `${n} hairline stroke${n === 1 ? "" : "s"} under ${l.crossFloorMm} mm sewn as running stitch`;
  }
  if (share(l.thinMm) >= 0.25) {
    return `${pct(l.thinMm)}% of this lettering is under ${l.columnFloorMm} mm wide — size up for crisp letters`;
  }
  return "";
}

export function charList(chars, max = 6) {
  const list = (chars || []).filter((c) => typeof c === "string" && c.length);
  if (!list.length) return "";
  const shown = list.slice(0, max).map((c) => `\u201c${c}\u201d`);
  const rest = list.length - shown.length;
  const joined = shown.length === 1 ? shown[0]
    : shown.slice(0, -1).join(", ") + " and " + shown[shown.length - 1];
  return rest > 0 ? `${shown.join(", ")} and ${rest} more` : joined;
}

// Elements that aren't ready (see generateElement) are silently skipped —
// not an error, just nothing to contribute yet. Returns
// { combined: null, perElement: [] } when nothing in the project is ready.
export function generateAll(project, runtime) {
  const garment = EMB.getGarment(project.garmentId);
  const perElement = [];
  for (const element of project.elements || []) {
    const design = generateElement(element, garment, runtime);
    if (!design) continue;
    // `unsupported`: characters the element's font has no glyph for. Carried
    // per element rather than merged, because the fix is per element — it is
    // THAT element's font that cannot set THAT text. A Hebrew font with Latin
    // text produces a valid-looking 0-stitch element and, before this, no
    // explanation anywhere in the UI.
    perElement.push({
      id: element.id, design, bboxMm: bboxMmFromStitches(design.stitches),
      unsupported: design.unsupported || [],
    });
  }
  if (!perElement.length) return { combined: null, perElement: [], unsupported: [] };
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
  // `unsupported` is also surfaced at the top level, deduplicated across
  // elements, so a caller that only wants "is there anything to tell the user"
  // does not have to walk perElement.
  const unsupported = [...new Set(ordered.flatMap((pe) => pe.unsupported))];
  return { combined: combineDesigns(ordered.map((pe) => pe.design)), perElement: ordered, unsupported };
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
