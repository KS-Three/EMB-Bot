// One-click starter templates for the first screen. Each template's `patch`
// is a v2 project patch — { garmentId, selectedId, elements } — that gives a
// beginner a fully-configured, ready-to-stitch starting point.
import { defaultProject, defaultTextElement, defaultImageElement, defaultDigitizedElement, resolveArtworkType } from "./project.js";

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
      // 92 mm, not the 76.2 this shipped with until 2026-09-08. At 76.2 the
      // template's own default text sews 7.6 mm caps with 69% of the lettering
      // under the 1 mm column floor, so clicking the app's second advertised
      // starter produced a design the app immediately told you to size up —
      // the one screen where a beginner has no reason to doubt what it handed
      // them.
      //
      // Two constraints, and the second is why this is not simply "as wide as
      // it goes". Measured on this font and text:
      //
      //   sizeMm   sewn W   slack each side   cap     thin
      //     76.2     76.4        12.6 mm      7.6      69%   <- shipped
      //     85       85.2         8.2         8.4      14%
      //     88.9     89.0         6.3         8.8       8%
      //     92       92.2         4.7         9.1       0%   <- here
      //     95       95.2         3.2         9.4       0%
      //    101.6    101.8         0.0        10.1       0%
      //
      // 92 is the first width with NO thin lettering at all, and it still
      // leaves 4.7 mm of room on each side. That room is the second
      // constraint: `EmbroideryField.nudgeSelected` and pointer drags clamp
      // against the GARMENT PLACEMENT BOX (`hoopSizeMm` returns
      // garment.widthIn, 4 in = 101.6 mm here — the name says hoop, the value
      // is the placement), so a design sewing 101.8 mm has ZERO slack and
      // cannot be moved at all. An earlier version of this fix used 101.6 for
      // its cap height and broke `field-chrome.spec.js`'s keyboard-placement
      // test, which was right to fail: a starter you cannot nudge is worse
      // than one 10 mm narrower. The e2e caught a real cost, not a stale
      // assertion.
      //
      // Better on longer names too — measured on this font: "Alexandra
      // Fitzgerald" and "Christopher Wetherington" both sit UNDER THE 4 mm CAP
      // FLOOR at 76.2 (the verdict meaning "cannot be sewn at all") and clear
      // it here. No input tested got worse.
      elements: [{ ...defaultTextElement("e1"), fontKey: "medium_font", text: "Your Name", sizeMm: 92 }],
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
      // INTENT, not a concrete element: "the user is about to give us
      // artwork". applyTemplate resolves it against digitizer health so this
      // template makes the same lane decision "+ Artwork" makes -- baking
      // defaultImageElement here is what silently routed photos through the
      // browser engine (the PR #122 defect class, through the template door).
      elements: [{ id: "e1", type: "artwork" }],
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
export function applyTemplate(project, template, digitizerHealth = null) {
  const patch = JSON.parse(JSON.stringify(template.patch));
  // Resolve artwork INTENT into a concrete element by the same rule
  // App.onAddElement uses. Builders return fresh objects, so the no-shared-
  // references guarantee the JSON clone provides for literal patch elements
  // holds for resolved ones too.
  patch.elements = patch.elements.map((el) =>
    el.type === "artwork"
      ? (resolveArtworkType(digitizerHealth) === "digitized"
          ? defaultDigitizedElement(el.id)
          : defaultImageElement(el.id))
      : el
  );
  return { ...defaultProject(), ...patch };
}
