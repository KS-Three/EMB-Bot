// The embroidery field is shown persistently on the right, so "preview" is no
// longer a screen of its own — the guided steps are just the left-panel flow.
import { isValidShape } from "./manualShapes.js";

export const STEPS = ["garment", "content", "create", "download"];

// "This element is ready to sew": each type has its own notion of having real
// content. design/digitized carry their stitches ON the element (dstBase64 /
// the baked service result); image content lives in runtime state, tracked by
// the _hasImage flag (see App.svelte); manual content lives right on the
// element too (element.shapes), ready once at least one COMPLETED shape
// traces to real geometry (the same isValidShape check generate.js's
// shapesToRegions uses to decide what's sewable, so this can never pass on a
// shape that generation would then silently skip).
//
// Exported 2026-09-07 because it had acquired a second and third consumer —
// the review step's headline and its content recap — and each had been
// answering the same question its own way. The recap's version was a
// `{:else}` that assumed text; the headline had none at all and simply said
// "Ready to stitch". One rule, three readers.
export function isSewable(el) {
  if (!el) return false;
  return el.type === "text" ? (el.text || "").trim().length > 0 :
    el.type === "design" ? !!el.dstBase64 :
    el.type === "digitized" ? !!el.result :
    el.type === "manual" ? (el.shapes || []).some((s) => isValidShape(s.points)) :
    // A preset shape element is born sewable: its geometry is generated from
    // kind + params, and shapePresets' generators clamp every input into a
    // range that always yields a valid ring (pinned by shapePresets.spec.js),
    // so there is no "empty" state to gate on.
    el.type === "shape" ? true :
    el._hasImage === true;
}

export function canAdvance(step, project) {
  if (step === "garment") return !!project.garmentId;
  if (step === "content") return true;
  if (step === "create") return project.elements.some(isSewable);
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
