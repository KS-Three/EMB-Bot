// The embroidery field is shown persistently on the right, so "preview" is no
// longer a screen of its own — the guided steps are just the left-panel flow.
import { isValidShape } from "./manualShapes.js";

export const STEPS = ["garment", "content", "create", "download"];

export function canAdvance(step, project) {
  if (step === "garment") return !!project.garmentId;
  if (step === "content") return true;
  if (step === "create") {
    // "Something is ready to sew": each element type has its own notion of
    // having real content. design/digitized carry their stitches ON the
    // element (dstBase64 / the baked service result); image content lives in
    // runtime state, tracked by the _hasImage flag (see App.svelte); manual
    // content lives right on the element too (element.shapes), same as
    // design/digitized — ready once at least one COMPLETED shape traces to
    // real geometry (same isValidShape check generate.js's shapesToRegions
    // uses to decide what's sewable, so this gate can never pass on a shape
    // that generation would then silently skip).
    return project.elements.some((el) =>
      el.type === "text" ? el.text.trim().length > 0 :
      el.type === "design" ? !!el.dstBase64 :
      el.type === "digitized" ? !!el.result :
      el.type === "manual" ? (el.shapes || []).some((s) => isValidShape(s.points)) :
      el._hasImage === true
    );
  }
  return true;
}

export function nextStep(step) {
  const i = STEPS.indexOf(step);
  return i >= 0 && i < STEPS.length - 1 ? STEPS[i + 1] : null;
}

export function prevStep(step) {
  const i = STEPS.indexOf(step);
  return i > 0 ? STEPS[i - 1] : null;
}
