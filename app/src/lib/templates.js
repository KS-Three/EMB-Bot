// One-click starter templates for the first screen. Each template's `patch`
// is a v2 project patch — { garmentId, selectedId, elements } — that gives a
// beginner a fully-configured, ready-to-stitch starting point.
import { defaultProject, defaultTextElement, defaultImageElement } from "./project.js";

export const TEMPLATES = [
  {
    id: "hat-name",
    label: "Name on a hat",
    hint: "Bold block letters, hat front",
    patch: {
      garmentId: "hat_front",
      selectedId: "e1",
      elements: [{ ...defaultTextElement("e1"), fontKey: "manga_impact", text: "YOUR NAME" }],
    },
  },
  {
    id: "chest-name",
    label: "Left-chest name",
    hint: "Clean sans, business look",
    patch: {
      garmentId: "left_chest",
      selectedId: "e1",
      elements: [{ ...defaultTextElement("e1"), fontKey: "medium_font", text: "Your Name", sizeMm: 76.2 }],
    },
  },
  {
    id: "script-name",
    label: "Script monogram",
    hint: "Flowing cursive",
    patch: {
      garmentId: "left_chest",
      selectedId: "e1",
      elements: [{ ...defaultTextElement("e1"), fontKey: "mam_script", text: "Yours" }],
    },
  },
  {
    id: "logo-patch",
    label: "Logo patch",
    hint: "Upload your logo next",
    patch: {
      garmentId: "patch",
      selectedId: "e1",
      elements: [defaultImageElement("e1")],
    },
  },
];

// Applies a template to a project. A template REPLACES the design entirely —
// that's the semantics of "start from template" — so this is just fresh
// defaults overlaid with the template's patch, not a merge onto whatever the
// user had going before.
//
// template.patch's `elements` array (and the element objects inside it) are
// the MODULE-LEVEL TEMPLATES constants -- a shallow spread would hand the
// resulting project's caller a live reference into those constants. Any code
// that later mutates a returned element in place (e.g. TextStep previously
// two-way-bound its text input directly to the selected element) would
// corrupt the shared TEMPLATES entry for the rest of the session (see
// final-review-s5.md Important #2). `patch` is plain JSON-serializable data
// (strings/numbers/plain objects), so a JSON round-trip is a cheap, safe deep
// clone that keeps TEMPLATES pristine regardless of what callers do with the
// project this returns.
export function applyTemplate(project, template) {
  return { ...defaultProject(), ...JSON.parse(JSON.stringify(template.patch)) };
}
