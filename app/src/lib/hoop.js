// hoop.js — which hoop preset a project is using, and how the fit check
// reads to the user. The presets themselves (sizes, the per-garment
// suggestion rule, and the orientation-aware fit math) live in the engine
// (src/garments.js: HOOPS / getHoop / suggestHoop / hoopFit) so the same
// hoop the Studio shows also drives any engine-side ceiling check; this
// module only resolves a project's pick and phrases the result.
//
// IMPORTANT: the hoop is a CEILING check, never a clamp. The scale-to-fit
// math everywhere (fitScale, SizePanel's typed-width bound, the field's
// drag clamps) keys off the garment PLACEMENT box, unchanged — a design can
// legitimately fit its placement and still exceed the picked hoop, and the
// answer is a warning, not a silent resize.
import { EMB } from "./emb.js";

// The hoop in effect for a project: the manual pick when project.hoopId
// names a real preset, else the per-garment suggestion. `suggested` tells
// the UI whether it's showing the suggestion or the user's own choice. An
// unknown hoopId (corrupt save, renamed preset) falls back to the
// suggestion rather than to nothing.
export function effectiveHoop(project) {
  const manual = project && project.hoopId ? EMB.getHoop(project.hoopId) : null;
  if (manual) return { hoop: manual, suggested: false };
  const garment = project ? EMB.getGarment(project.garmentId) : null;
  return { hoop: EMB.suggestHoop(garment), suggested: true };
}

// User-facing fit line for a generated design against the chosen hoop.
// Returns null when the design fits — nothing to say. The rotated case
// names the fix, not just the problem (the engine's hoopFit is
// orientation-aware); actually auto-rotating the design for the user is a
// noted follow-up, today the message just points at it.
export function hoopFitNote(widthMM, heightMM, hoop) {
  if (!hoop || !isFinite(widthMM) || !isFinite(heightMM)) return null;
  const fit = EMB.hoopFit(widthMM, heightMM, hoop);
  if (fit === "fits") return null;
  if (fit === "rotated") return `Exceeds your ${hoop.label} hoop — rotate the design 90° and it fits`;
  return `Exceeds your ${hoop.label} hoop`;
}
