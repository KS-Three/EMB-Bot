import { EMB } from "./emb.js";
export const WORK_MAX_PX = 480;
export const ALPHA_CUTOFF = 128;
const MODE_FILTER_ITERS = 2;
const ABSORB_SHARE = 0.0005;

export function flattenRGBA(rgba, w, h, opts) {
  const o = opts || {};
  let px = rgba;
  if (o.removeBg) px = EMB.knockoutBackground(px, w, h, {});
  const quant = EMB.medianCut(px, o.nColors || 4);
  let indices = EMB.modeFilter(quant.indices, w, h, { iterations: MODE_FILTER_ITERS });
  indices = EMB.absorbSmallRegions(indices, w, h, Math.round(w * h * ABSORB_SHARE));
  return { palette: quant.palette.map((c) => c.slice()), indices, w, h };
}
export function flatToRGBA(flat) { return EMB.indicesToRGBA(flat.indices, flat.palette, flat.w, flat.h); }
export function flatShares(flat) { return EMB.paletteShares(flat.indices, flat.palette.length); }

// A palette entry below this share is treated as empty. The threshold and the
// reason are ImagePanel's, moved here rather than invented: median-cut can
// return more entries than the art uses, and a 0.0% chip is noise to a
// beginner. That claim is left as its author's — what IS measured here is the
// weaker and sufficient one: `nColors` is a CEILING, not a count. Median-cut
// on a two-colour image returns two entries at every slider value from 2 to 8
// (flatten.spec.js), so the slider and the sewn colours part company with no
// empty slot needed.
//
// ONE rule, exported, because two customer-facing surfaces read it and they
// disagreed until 2026-09-08: ImagePanel's swatch strip hid the empty slots
// (this threshold, inline) while the review card two clicks later reported
// `element.nColors` — the slider — as the design's colour count. On the
// shipped Logo-patch starter that read "Colors 4" beside "Thread changes 1"
// on the same card. A colour is a cone to buy and, on a single-needle
// machine, a re-thread, so the inflated number costs real money.
export const MIN_SWATCH_SHARE = 0.0005;

// How many colours this flat will actually sew — the count of palette entries
// carrying pixels, which is what ImagePanel renders as swatches. Null (not 0)
// when there is no flat yet, so a caller can tell "nothing flattened" from
// "flattened to nothing" instead of printing a confident zero.
export function sewnColorCount(flat) {
  if (!flat || !flat.palette) return null;
  return flatShares(flat).filter((s) => s > MIN_SWATCH_SHARE).length;
}
export function mergeFlat(flat, idxList) {
  const m = EMB.mergeColors(flat.palette, flat.indices, idxList);
  return { palette: m.palette, indices: m.indices, w: flat.w, h: flat.h };
}
