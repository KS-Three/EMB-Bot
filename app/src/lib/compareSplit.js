// Compare view (2026-11-07): the uploaded artwork and its stitches laid over
// each other at the same scale and registration, with a vertical split the
// customer drags — artwork LEFT of it, stitches RIGHT.
//
// The pure half. `split` is a fraction of the field's width, 0..1 (0 = all
// stitches, 1 = all artwork). The split moves by CSS clip only: the artwork
// sits on its own canvas over the field canvas and is clipped, so dragging the
// handle repaints nothing. Repaints happen only when the VIEW changes (zoom,
// pan, resize), and those go through the field's repaintView() like every
// other view-only change.

export const SPLIT_DEFAULT = 0.5;
// Arrow keys move the handle 2% of the field (Shift 10%), Home / End go to
// the ends. A percentage rather than px so a key press means the same thing
// on a laptop and on a wide monitor.
export const SPLIT_STEP = 0.02;
export const SPLIT_STEP_COARSE = 0.1;

export function clampSplit(s) {
  const n = Number(s);
  if (!Number.isFinite(n)) return SPLIT_DEFAULT;
  return Math.min(1, Math.max(0, n));
}

// The split under a pointer at `clientX`, against the overlay's own box (a
// DOMRect-like { left, width }). A zero-width box (mid-layout) keeps the
// default rather than dividing by zero.
export function splitFromClientX(clientX, rect) {
  if (!rect || !(rect.width > 0) || !Number.isFinite(clientX)) return SPLIT_DEFAULT;
  return clampSplit((clientX - rect.left) / rect.width);
}

// The handle's keys. Returns the new split, or null for a key the handle
// does not own — so Tab, [ ], < > , . and everything else fall through to
// whoever listens for them. Rounded to a whole step so repeated presses never
// drift off the grid by float error.
export function splitKey(split, key, shift = false) {
  const s = clampSplit(split);
  const step = shift ? SPLIT_STEP_COARSE : SPLIT_STEP;
  let next;
  if (key === "ArrowLeft" || key === "ArrowDown") next = s - step;
  else if (key === "ArrowRight" || key === "ArrowUp") next = s + step;
  else if (key === "Home") next = 0;
  else if (key === "End") next = 1;
  else return null;
  return clampSplit(Math.round(next * 1000) / 1000);
}

// CSS clip-path keeping the artwork LEFT of the split: inset from the right
// by the rest of the width.
export function clipForSplit(split) {
  const right = (1 - clampSplit(split)) * 100;
  return `inset(0 ${+right.toFixed(3)}% 0 0)`;
}

export function splitPercent(split) {
  return Math.round(clampSplit(split) * 100);
}

// What a screen reader says for the handle's value: both sides, since the
// number alone does not say which side it measures.
export function splitValueText(split) {
  const p = splitPercent(split);
  return `Artwork ${p}%, stitches ${100 - p}%`;
}
