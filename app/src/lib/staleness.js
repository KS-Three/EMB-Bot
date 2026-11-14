// "Are these stitches behind their settings?" — ONE answer for everything that
// asks it: the Digitize panel's run button, the field's hatch over the stitches,
// and the Download step.
//
// Why one rule. The question used to live in two places that disagreed.
// DigitizePanel answered it for the SELECTED element only, off its own mount
// key, and nobody else could: the Download step checked the hoop and the
// quality report and handed over whatever was on the canvas. The field's hatch
// answered a narrower question — shape edits only. So a shop could be handed a
// file at 1.66x density, or on the wrong fabric preset, without a word
// (area-3 doc, 2026-10-08):
//
//   * corner-drag a digitized logo from 80 to 62 mm: generate.js hands
//     `sizeMm` to buildImportedDesign, which SCALES the baked stitches, so all
//     8,764 stayed on 0.6x the area, 1.66x the thread per mm²;
//   * switch the garment after digitizing (a tee to a hat): the file still
//     carries the first garment's request (`garment_id` in the POSTed
//     config), so its pull compensation, underlay and density.
//
// Kent's rulings these sit under: nothing re-runs on its own (2026-10-05) — a
// run is the customer's click on "Auto Digitize Image"; no warning text
// (2026-10-02); and, 2026-10-25, Download stays disabled while the stitches
// are behind (`blocksDownload`), with the run button highlighted.
//
// What "behind" means is what the panel has meant since 2026-10-05, unchanged:
// the config this element would send NOW differs from the one its result was
// digitized with (`appliedConfig`, stamped by runDigitize), or its shape edits
// are not the ones it was digitized with (`appliedEdits`), or the field has
// resized it (resizedTargetWidth). The config covers params, crop, garment,
// fabric colour, calibration profile and the thread chart — everything
// buildDigitizeConfig puts on the wire.
import {
  buildDigitizeConfig,
  canonicalShapeEdits,
  editsKey,
  configKey,
  resizedTargetWidth,
  decodedFromDesignCached,
} from "./digitizer.js";
import { isOutlineKey, outlineStale } from "./outlineFonts.js";

// The width a design is DRAWN at: the result's native width in the frame the
// element's rotation puts it in — the frame `sizeMm` is measured in.
//
// Off the quarter turns this is the width of the TURNED STITCHES, the way
// buildImportedDesign measures it (2026-11-13). It used to be the turned
// bounding RECTANGLE, |w cos| + |h sin|, which is the engine's rule for
// lettering, not for a stitch file: a round logo at 45 degrees read 41% wider
// than it sews, so a pure rotation read as a resize and marked the design
// behind. The rotation controls now keep sizeMm in this same frame
// (hoop.js rotationPatch), so turning a digitized design leaves it current.
export function rotatedWidth(dec, deg) {
  if (!dec) return 0.1;
  const rot = ((deg % 360) + 360) % 360;
  if (rot === 0 || rot === 180) return dec.widthMM;
  if (rot === 90 || rot === 270) return dec.heightMM;
  const rad = (rot * Math.PI) / 180;
  if (!dec.stitches) return Math.abs(dec.widthMM * Math.cos(rad)) + Math.abs(dec.heightMM * Math.sin(rad));
  const cos = Math.cos(rad), sin = Math.sin(rad);
  let x0 = Infinity, x1 = -Infinity;
  for (const s of dec.stitches) {
    if (s.type !== "stitch") continue;
    const x = s.x * cos - s.y * sin;
    if (x < x0) x0 = x;
    if (x > x1) x1 = x;
  }
  return x0 === Infinity ? 0.1 : Math.max(0.1, (x1 - x0) / 10);
}

// The same width for any element, not only the one on screen.
export function nativeWidthOf(el) {
  const dec = el && el.result ? decodedFromDesignCached(el.result) : null;
  return dec ? rotatedWidth(dec, el.rotationDeg || 0) : 0;
}

// The element as a run would send it when the field has resized it: the
// dragged width is the design width until the next run.
export function withTargetWidth(el, target) {
  return target == null ? el : { ...el, params: { ...el.params, target_width_mm: target } };
}

// Shape edits the current result was not digitized with. Canonical on both
// sides, so a toggled-then-untoggled edit reads as "nothing pending", exactly
// like the job cache. A design with no shape list has no edits to apply.
export function pendingEdits(el) {
  const shapes = (el && el.review && el.review.shapes) || [];
  return shapes.length > 0 && editsKey(canonicalShapeEdits(el)) !== (el.appliedEdits || editsKey({}));
}

// `baselineKey` is for a design saved before `appliedConfig` existed (null in
// project.js): there is nothing stored to compare its config with, so the
// panel passes the key it computed when it opened and reads the design as
// current as loaded. Without it (the field, Download) such a design is seen
// only through a resize or pending edits — a legacy design whose garment was
// switched while no panel was open is invisible to the config comparison, and
// ships as it always did.
export function isElementStale(element, project, { baselineKey = null } = {}) {
  // A text element in an outline font carries a service result too
  // (lib/outlineFonts.js): behind when the request it would send now —
  // text, font, width, spacing, colour, garment, fabric, chart — is not the
  // one it was digitized with.
  if (isOutlineText(element)) return outlineStale(element, project, { baselineKey });
  if (!element || element.type !== "digitized" || !element.result) return false;
  // Cheapest first: the field asks this for every element on every redraw.
  const target = resizedTargetWidth(element, nativeWidthOf(element));
  if (target != null) return true;
  if (pendingEdits(element)) return true;
  const applied = element.appliedConfig || baselineKey;
  if (!applied) return false;
  return configKey(buildDigitizeConfig(element, project)) !== applied;
}

// ART UPLOADED BUT NEVER DIGITIZED (Kent 2026-11-13). Such an element sews
// nothing (flow.js isSewable), so beside a typed text the design read as
// ready and Download handed over a file with the logo silently left out --
// the image twin of outlineStale's "text typed but never digitized". No art
// is behind nothing: an empty image element has nothing to press or sew.
//
// Kept OUT of isElementStale on purpose. That question is "are these
// STITCHES behind their settings", and two of its readers would say the
// wrong thing to art with no stitches: the panel would turn its run button
// transparent ("out of date") and say "Changed since the last run" before
// any run, and the field would hatch stitches that do not exist. So it joins
// only what Download waits for, below. The catch, accepted: Download stays
// locked until the art is digitized or removed.
export function isUndigitizedArt(element) {
  return !!element && element.type === "digitized" && !!element.sourcePng && !element.result;
}

// Every element Download waits for: stitches behind their settings, and art
// not digitized at all.
export function staleElements(project) {
  return ((project && project.elements) || []).filter(
    (el) => isElementStale(el, project) || isUndigitizedArt(el),
  );
}

// A run needs the stored art and the service — the same two things
// DigitizePanel's runDigitize and its button need.
export function canRedigitize(element, health) {
  if (isOutlineText(element)) return !!health;   // the text IS the source
  return !!(element && element.sourcePng && health);
}

export function isOutlineText(element) {
  return !!element && element.type === "text" && isOutlineKey(element.fontKey);
}

// Download is disabled while this is true. It counts only what the customer
// can act on: with the service down, or the art gone from a saved project,
// the highlighted button cannot run and a locked Download would have no way
// out — and DigitizePanel's offline note already promises that "your stitched
// result is saved with the design and still sews and exports". Kent's
// no-warnings ruling allows a customer-facing item for what they can act on.
export function blocksDownload(project, health) {
  return staleElements(project).some((el) => canRedigitize(el, health));
}
