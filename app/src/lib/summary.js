// The review step's content recap — one row per fact about what the customer
// actually put in.
//
// Extracted from App.svelte 2026-09-07 because the markup it replaces ended
// in a `{:else}` that assumed TEXT, and three of the six element types
// `addElement` can build are neither image nor manual. An auto-digitized
// design — the commonest path there is — has no `text` and no `fontKey`, so
// the review step recapped it as:
//
//     Content   Text — "undefined"
//     Font
//
// on the screen a customer reads immediately before Download. A `.dst` upload
// and a preset shape did the same. Nothing failed, nothing warned; the
// catch-all branch simply answered a question about the wrong element type,
// and the e2e that drives the digitized path asserted the grade and the
// thread bill without ever looking at the recap above them.
//
// A function rather than more `{:else if}` rungs, because the defect is that
// the last rung is silent about types it does not know. Here the fallback is
// reached only by `text` and by nothing else, and `summary.spec.js` proves
// that against project.js's OWN factory list rather than a copy of it — so a
// seventh element type fails a test instead of shipping "undefined".

const NOT_YET = "not uploaded yet";

export function contentSummary(element) {
  const el = element || {};
  switch (el.type) {
    case "image":
      return [
        { label: "Content", value: "Logo / image" },
        { label: "Colors", value: `${el.nColors}${el.removeBg ? " · background removed" : ""}` },
      ];
    case "manual":
      return [
        { label: "Content", value: "Hand-drawn shapes" },
        { label: "Shapes", value: String((el.shapes || []).length) },
      ];
    case "digitized":
      return [
        { label: "Content", value: "Auto-digitized artwork" },
        { label: "Artwork", value: el.name || NOT_YET },
      ];
    case "design":
      return [
        { label: "Content", value: "Imported design file" },
        { label: "File", value: el.name || NOT_YET },
      ];
    case "shape":
      return [
        { label: "Content", value: "Drawn shape" },
        { label: "Shape", value: titleCase(el.kind) || "Circle" },
      ];
    default:
      // Text, and only text — see the module comment. Empty quotes are how a
      // developer writes "nothing"; a customer reads them as a design
      // containing two quote marks.
      return [
        { label: "Content", value: (el.text || "").trim() ? `Text — "${el.text}"` : "Text — nothing typed yet" },
        { label: "Font", value: titleCase(el.fontKey) || "None chosen" },
      ];
  }
}

// Same shape as App.svelte's own `readable`, kept here so this module has no
// dependency on the component it was cut out of.
function titleCase(id) {
  return (id || "")
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
