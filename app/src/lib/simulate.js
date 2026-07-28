// simulate.js — pure playback math for the stitch simulator (no canvas, no
// timers here; EmbroideryField owns the rAF loop and rendering).
//
// Progress is measured in STRANDS (drawable segments from designToStrands),
// not raw stitch records — strands are what actually paint, so "N of total"
// maps 1:1 onto what the user sees appear.

// Playback rates. BASE_SPS is strands-per-second at 1x — slow enough to watch
// individual letters form, fast enough that a 5k-stitch name finishes in
// ~20s. The speed multipliers are the user-facing options.
export const BASE_SPS = 250;
export const SPEEDS = [1, 2, 4, 8];

// One playback tick: advance `index` (a float — fractional progress carries
// across frames so slow speeds still move on every frame) by dtMs at `speed`,
// clamped to [0, total]. Returns the new index; callers floor it for display
// and drawing.
export function advanceIndex(index, dtMs, speed, total) {
  if (!Number.isFinite(dtMs) || dtMs < 0) dtMs = 0;
  const next = index + (dtMs / 1000) * BASE_SPS * speed;
  return Math.max(0, Math.min(total, next));
}

// Scrub-slider input → clamped integer index.
export function clampIndex(value, total) {
  const n = Math.floor(Number(value) || 0);
  return Math.max(0, Math.min(total, n));
}

// The next speed option after `speed`, cycling back to the first — the
// simulator bar's speed button cycles instead of using a dropdown.
export function nextSpeed(speed) {
  const i = SPEEDS.indexOf(speed);
  return SPEEDS[(i + 1) % SPEEDS.length];
}
