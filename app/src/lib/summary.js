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

import { isSewable } from "./flow.js";

const NOT_YET = "not uploaded yet";

export function contentSummary(element, sewnCount) {
  const el = element || {};
  switch (el.type) {
    case "image": {
      // The slider is a CEILING the customer asked for, not a count of what
      // sews: median-cut returns only as many entries as the art needs (two
      // on a two-colour image at every setting from 2 to 8 — flatten.spec.js).
      // This row printed `nColors` verbatim until 2026-09-08, so the shipped
      // Logo-patch starter reached the review card reading
      //
      //     Colors          4 · background removed
      //     Thread changes  1
      //
      // — two rows apart and disagreeing, because `Thread changes` is counted
      // from the design's own {type:"color"} records (estimate.js) while this
      // one never looked at the design at all. Every other row on that card is
      // measured; this is the one that was asserted. Colours are cones to buy
      // and re-threads on a single-needle machine, so four against a real two
      // is money.
      //
      // Falls back to the slider only when nothing has been flattened yet —
      // an image element with no image, which `designSummary` reaches solely
      // through its "nothing sewable" branch. There the ceiling is genuinely
      // all that is known.
      //
      // A number in (`sewnCount`), not the flat itself: `sewnColorCount` lives in
      // flatten.js, which imports the engine and throws at module load when it
      // is absent. This module is deliberately dependency-light — importing it
      // here made every summary test require the whole engine preloaded, for
      // one integer.
      const n = typeof sewnCount === "number" ? sewnCount : el.nColors;
      return [
        { label: "Content", value: "Logo / image" },
        { label: "Colors", value: `${n}${el.removeBg ? " · background removed" : ""}` },
      ];
    }
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


// Every element's rows, for the review step's recap.
//
// The recap keyed off `selectedElement` alone, which is right for the SIZE
// panel below it (that edits one element) and wrong for a summary sitting
// under "Ready to stitch": a name plus a logo — the commonest real job there
// is — reached the last screen before Download described only as
// "Auto-digitized artwork", with no mention of the lettering also sewing.
// Measured 2026-09-07: two elements, 3542 stitches, one of them named.
//
// The rows are numbered ONLY when there is more than one element, so a
// single-element project renders exactly as before (and the e2e assertions
// on "Content" keep meaning what they meant).
//
// `sewnColors` maps element id -> the number of colours that element's
// flattened palette will actually sew (App derives it from `runtime.flats` via
// flatten.js's `sewnColorCount`). Derived from the same object ImagePanel is
// rendering, rather than recomputed here — computing it twice is how the
// swatch strip and this card came to disagree in the first place. Optional, so
// a caller with no runtime still gets every row, with the image row falling
// back to the slider as documented above.
export function designSummary(project, sewnColors) {
  const all = (project && project.elements) || [];
  const sewnFor = (el) => (sewnColors && el ? sewnColors[el.id] : undefined);
  // Only what will actually SEW, by flow.js's rule rather than a second one.
  // A brand-new project always carries an empty text element, so listing
  // every element verbatim recapped a digitized logo as
  // "Content 1: Text — nothing typed yet / Content 2: Auto-digitized
  // artwork" — numbering the real content second behind a placeholder that
  // sews nothing. Caught by an assertion written for a different defect.
  const els = all.filter(isSewable);
  // Nothing sewable is its own honest state: describe the first element as
  // it is, which is what the "Nothing to stitch yet" headline sits above.
  if (!els.length) return contentSummary(all[0], sewnFor(all[0]));
  if (els.length === 1) return contentSummary(els[0], sewnFor(els[0]));
  return els.flatMap((el, i) => {
    const rows = contentSummary(el, sewnFor(el));
    return [{ ...rows[0], label: `${rows[0].label} ${i + 1}` }, ...rows.slice(1)];
  });
}
