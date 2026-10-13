// hoop.js — which hoop preset a project is using, and how the fit check
// reads to the user. The presets themselves (sizes, the per-garment
// suggestion rule, and the orientation-aware fit math) live in the engine
// (src/garments.js: HOOPS / getHoop / suggestHoop / hoopFit) so the same
// hoop the Studio shows also drives any engine-side ceiling check; this
// module only resolves a project's pick and phrases the result.
//
// IMPORTANT: the hoop is a CEILING check, never a clamp on what the user
// asks for. SizePanel's typed-width bound and the field's drag clamps key off
// the garment PLACEMENT box, unchanged — a design can legitimately fit its
// placement and still exceed the picked hoop, and the answer is a warning,
// not a silent resize. The one exception is AUTO-fit (Kent's ruling
// 2026-10-13, "cap to hoop"): fitScale sizes to the placement box capped to
// the largest hoop's usable field (EMB.autoFitBoxMm), so auto-fit alone never
// produces an oversize design.
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
// Returns null when the design fits — nothing to say. Every other case names
// the fix, not just the problem, which is this repo's standing convention for
// a finding (THREAD_MATCH_POOR names a loaded better spool, COLOR_STOPS_HEAVY
// the cheapest merge, and so on).
//
// The three fixes are genuinely different, and "Exceeds your 8×8 in hoop" —
// the whole message until 2026-09-07 — implied the wrong one for the case that
// fires most:
//
//   rotated       -> turn it; the engine's hoopFit is orientation-aware.
//                    (Auto-rotating for the user is a noted follow-up.)
//   a bigger hoop -> name it. The customer may own it, and if not they now
//                    know what to buy.
//   nothing fits  -> say so. Suggesting "a bigger hoop" when the design is
//                    already past the largest one this app offers is advice to
//                    go shopping for something that will not help.
//
// The last case is not an edge case. Measured 2026-09-07 over the shipped
// garment table: FOUR of the ten placement boxes — full_back 304.8×304.8,
// jacket_back 304.8×254.0, blanket 254.0×203.2 and tote 203.2×203.2 mm — are
// larger than the biggest hoop offered (8×8 in = 200 mm), and auto-fit targets
// the placement box. So every design on 40% of the garment picker is oversize
// by construction, on every run, and got told to try a bigger hoop.
//
// Auto-fit now caps to the largest hoop (2026-10-13), so this last case is
// reached only by a width the user typed (or dragged) past the hoop; the
// auto-fit design says it was capped via `autoCapNote` instead.
export function hoopFitNote(widthMM, heightMM, hoop) {
  if (!hoop || !isFinite(widthMM) || !isFinite(heightMM)) return null;
  const fit = EMB.hoopFit(widthMM, heightMM, hoop);
  if (fit === "fits") return null;
  if (fit === "rotated") return `Exceeds your ${hoop.label} hoop — rotate the design 90° and it fits`;
  const bigger = (EMB.HOOPS || []).find((h) => EMB.hoopFit(widthMM, heightMM, h) !== "exceeds");
  return bigger
    ? `Exceeds your ${hoop.label} hoop — a ${bigger.label} hoop fits it`
    : `Exceeds your ${hoop.label} hoop, and every hoop this app offers — make it smaller under Size`;
}

// Said beside the Size controls while a design is auto-fit on a garment whose
// placement box is bigger than the largest hoop: the design is smaller than
// the placement area by choice, not by accident. "" when auto-fit is not
// capped (every other garment), so the line only appears where it is true.
export function autoCapNote(garment) {
  if (!garment || !EMB.autoFitBoxMm || !EMB.HOOPS) return "";
  const hoop = EMB.HOOPS[EMB.HOOPS.length - 1];
  const box = EMB.autoFitBoxMm(garment);
  const capped = box.w < garment.widthIn * 25.4 - 1e-9 || box.h < garment.heightIn * 25.4 - 1e-9;
  return capped
    ? `Auto-fit sizes this to the ${hoop.label} hoop, the largest this app offers — the ${garment.label} area is bigger. Type a width to go larger.`
    : "";
}
