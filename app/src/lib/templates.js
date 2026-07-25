// One-click starter templates for the first screen. Each template's `patch`
// is a plain project patch (same shape update() expects) that gives a
// beginner a fully-configured, ready-to-stitch starting point.
import { update } from "./project.js";

export const TEMPLATES = [
  {
    id: "hat-name",
    label: "Name on a hat",
    hint: "Bold block letters, hat front",
    patch: { garmentId: "hat_front", mode: "text", fontKey: "manga_impact", text: "YOUR NAME", sizeMm: null, offsetXMm: 0, offsetYMm: 0 },
  },
  {
    id: "chest-name",
    label: "Left-chest name",
    hint: "Clean sans, business look",
    patch: { garmentId: "left_chest", mode: "text", fontKey: "geneva_simple", text: "Your Name", sizeMm: 76.2 },
  },
  {
    id: "script-name",
    label: "Script monogram",
    hint: "Flowing cursive",
    patch: { garmentId: "left_chest", mode: "text", fontKey: "aventurina", text: "Yours", sizeMm: null },
  },
  {
    id: "logo-patch",
    label: "Logo patch",
    hint: "Upload your logo next",
    patch: { garmentId: "patch", mode: "image" },
  },
];

// Applies a template's patch to a project, immutably (like update()). Unlike
// a plain update(), this always resets offsetXMm/offsetYMm to 0 and sizeMm
// to null — a starter template should never inherit stale positioning/sizing
// left over from whatever the user was doing before — unless the template's
// own patch explicitly sets those fields.
export function applyTemplate(project, template) {
  const patch = template.patch;
  return update(project, {
    ...patch,
    offsetXMm: patch.offsetXMm !== undefined ? patch.offsetXMm : 0,
    offsetYMm: patch.offsetYMm !== undefined ? patch.offsetYMm : 0,
    sizeMm: patch.sizeMm !== undefined ? patch.sizeMm : null,
    letterSpacingMm: patch.letterSpacingMm !== undefined ? patch.letterSpacingMm : 0,
  });
}
