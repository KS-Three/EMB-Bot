// The thin-outline prompt (Kent, 2026-11-13: "When it gets digitized can you
// have items like this throb/pulse and glow (ask user to keep or remove)").
//
// The digitizer marks the shapes it read as a HAIRLINE OUTLINE — a thin line
// the art draws round its shapes, sewn as one bean line (review row
// `hairlineOutline`, wire `hairline_outline`, contract v1.10; never a letter).
// On a light garment that line adds little and costs a colour stop; on a dark
// one it is what makes the design read. The tool cannot know which, so it
// asks: the marked shapes glow on the design until the customer says Keep or
// Remove.
//
// This is a question the CUSTOMER can answer about THEIR design, which is the
// kind of thing the 2026-10-02 no-warnings ruling leaves room for; it is not
// the tool reporting a flaw of its own.
//
// Three states per marked shape, all derived (nothing here is a second source
// of truth):
//   removed   — in the element's `deletedShapeIds` (the ordinary, restorable
//               hide: undo works, the Layers list can bring it back, and the
//               canvas drops its stitches at once — lib/digitizer.js
//               displayResult);
//   kept      — in the element's `keptOutlineIds`. Not a shape edit: it is not
//               in canonicalShapeEdits, so saying Keep never makes the design
//               stale (nothing about the stitches changes);
//   undecided — neither, and still sewn. These glow.

const ids = (list) => (Array.isArray(list) ? list : []);

/** The review rows the digitizer marked as a hairline outline. */
export function outlineRows(element) {
  const rows = element && element.review && element.review.shapes;
  return ids(rows).filter((r) => r && r.hairlineOutline === true);
}

function sewn(row, element) {
  // A shape the customer (or the enclosed-background default) left unsewn is
  // not on the design, so there is nothing to keep or remove.
  const ov = element && element.shapeOverrides && element.shapeOverrides[row.id];
  if (ov && typeof ov.stitched === "boolean") return ov.stitched;
  return row.stitched !== false;
}

/** Marked, still sewn, and not yet answered: the shapes that glow. */
export function undecidedOutlineIds(element) {
  const removed = new Set(ids(element && element.deletedShapeIds));
  const kept = new Set(ids(element && element.keptOutlineIds));
  return outlineRows(element)
    .filter((r) => !removed.has(r.id) && !kept.has(r.id) && sewn(r, element))
    .map((r) => r.id);
}

/** Marked shapes the customer removed: what "Put back" restores. */
export function removedOutlineIds(element) {
  const removed = new Set(ids(element && element.deletedShapeIds));
  return outlineRows(element).filter((r) => removed.has(r.id)).map((r) => r.id);
}

/** The element patch for Keep: remember the answer, change no stitch. */
export function keepPatch(element) {
  const kept = new Set(ids(element && element.keptOutlineIds));
  for (const id of undecidedOutlineIds(element)) kept.add(id);
  return { keptOutlineIds: [...kept] };
}

/** The element patch for Remove: every undecided outline hidden, in one step. */
export function removePatch(element) {
  const deleted = new Set(ids(element && element.deletedShapeIds));
  for (const id of undecidedOutlineIds(element)) deleted.add(id);
  return { deletedShapeIds: [...deleted] };
}

/** The element patch for Put back: un-hide them, and count that as "Keep". */
export function putBackPatch(element) {
  const back = new Set(removedOutlineIds(element));
  const kept = new Set(ids(element && element.keptOutlineIds));
  for (const id of back) kept.add(id);
  return {
    deletedShapeIds: ids(element && element.deletedShapeIds).filter((id) => !back.has(id)),
    keptOutlineIds: [...kept],
  };
}

// One slow breath every THROB_MS: 0 at rest, 1 at the peak. Unlike the
// new-result pulse (shapeOverlay.pulseAt, three beats then done) this one does
// not end by itself — it is waiting on an answer.
export const THROB_MS = 1400;

export function throbAt(nowMs) {
  const t = Number.isFinite(nowMs) ? nowMs : 0;
  return 0.5 - 0.5 * Math.cos((2 * Math.PI * t) / THROB_MS);
}

// Under prefers-reduced-motion the glow holds still at this level.
export const STILL_GLOW = 0.6;
