export const STEPS = ["garment", "text", "preview", "download"];

export function canAdvance(step, project) {
  if (step === "garment") return !!project.garmentId;
  if (step === "text") return project.text.trim().length > 0 && !!project.fontKey;
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
