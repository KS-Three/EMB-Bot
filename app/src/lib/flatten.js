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
export function mergeFlat(flat, idxList) {
  const m = EMB.mergeColors(flat.palette, flat.indices, idxList);
  return { palette: m.palette, indices: m.indices, w: flat.w, h: flat.h };
}
