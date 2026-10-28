// placement.js — the garment AS PLACED, for everything in the Studio that
// reads a box off the garment.
//
// Kent, 2026-10-27: the size a digitized image comes in at should be picked
// from where on the garment it sits (hat centred / left / right / side /
// rear, left chest / right chest / full back / upper back / sleeve) as the
// most that fits there, not a flat 80 mm, and not a "suggested" number that
// only ever meant the hoop. The table of placements and boxes is the
// engine's (src/garments.js PLACEMENTS / resolvePlacement); this module only
// resolves a PROJECT's pick and derives the default width from it.
//
// `project.placementId` is null for the garment's default placement, which
// carries the garment's own id — so a project saved before placements
// existed, and every spec that builds `{ garmentId }` alone, resolves to the
// very garment object `EMB.getGarment` returns, and nothing downstream moves.
import { EMB } from "./emb.js";

const MM_PER_INCH = 25.4;

// The garment object every box reader takes, with the placement's box on it
// when one other than the default is picked. Undefined when the garment id
// is unknown, like EMB.getGarment. Falls back to the plain garment where the
// engine predates placements (a spec's EMB stub).
export function garmentOf(project) {
  if (!project || !project.garmentId) return undefined;
  return EMB.resolvePlacement
    ? EMB.resolvePlacement(project.garmentId, project.placementId || null)
    : EMB.getGarment(project.garmentId);
}

// The placement box in mm, { w, h }, or null when the garment is unknown.
// This is the box a typed width and a drag clamp to (SizePanel, the field);
// it is NOT the hoop (lib/hoop.js: "a CEILING check, never a clamp"), and it
// is the pro's box where he measured one (garments.placementBoxMm), not the
// garment's round-inch pair — the two clamps read the inch pair until today.
export function placementBoxOf(project) {
  const g = garmentOf(project);
  if (!g) return null;
  if (EMB.placementBoxMm) return EMB.placementBoxMm(g);
  return { w: g.widthIn * MM_PER_INCH, h: g.heightIn * MM_PER_INCH };
}

// The Design width (target_width_mm) a digitized image starts at: the
// engine's auto-fit of the artwork's aspect into the placement's box —
// garments.fitScale, so the hoop cap (autoFitBoxMm) and the pro's left-chest
// area cap apply exactly as they do to lettering — in the 10-400 mm range the
// Design width field accepts, to a tenth. `px` is the uploaded image's pixel
// size and `crop` the element's crop box in fractions of it (null = whole
// image): the aspect that is fitted is the cropped image's. null when there
// is nothing to fit (no image size, unknown garment, or no engine fit).
export function fitTargetWidthMm(px, crop, project) {
  if (!px || !(px.w > 0) || !(px.h > 0)) return null;
  const g = garmentOf(project);
  if (!g || !EMB.fitScale) return null;
  const fx = crop ? Math.max(1e-6, (crop.x1 - crop.x0)) : 1;
  const fy = crop ? Math.max(1e-6, (crop.y1 - crop.y0)) : 1;
  const fit = EMB.fitScale(px.w * fx, px.h * fy, g);
  if (!fit || !(fit.targetWmm > 0) || !isFinite(fit.targetWmm)) return null;
  return Math.min(400, Math.max(10, Math.round(fit.targetWmm * 10) / 10));
}

// The project after a garment or placement change: every digitized image
// whose width the customer has not typed is re-fitted to the new placement
// (its default moved; a typed width is theirs and stays). Elements with no
// recorded image size — saved before `sourcePx` existed, or never given art —
// are left alone. The stitches of a re-fitted element go stale under the
// usual rule (lib/staleness.js): nothing re-runs on its own (Kent 2026-10-05)
// and Download waits for the re-digitize (Kent 2026-10-25).
export function refitDigitized(project) {
  if (!project || !Array.isArray(project.elements)) return project;
  let changed = false;
  const elements = project.elements.map((el) => {
    if (!el || el.type !== "digitized" || el.widthTyped || !el.sourcePx) return el;
    const w = fitTargetWidthMm(el.sourcePx, el.crop, project);
    if (w == null || (el.params && el.params.target_width_mm === w)) return el;
    changed = true;
    return { ...el, params: { ...(el.params || {}), target_width_mm: w } };
  });
  return changed ? { ...project, elements } : project;
}
