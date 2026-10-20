// The artwork a customer uploaded, for the field's Original view (spec §4).
// `element.sourcePng` is bare base64 — the 1,200-px preview both the image
// and the digitized lanes keep on the element (lib/project.js).
export function originalDataUrl(sourcePng) {
  return typeof sourcePng === "string" && sourcePng.length > 0 ? "data:image/png;base64," + sourcePng : null;
}

export function hasOriginal(el) {
  return !!el && (el.type === "image" || el.type === "digitized") && !!originalDataUrl(el.sourcePng);
}

// Aspect-preserving fit of the WHOLE image frame inside `rect`, centred. The
// Original view uses it only as a fallback: for the digitized lane, fitted
// into the placement box (no exact source-to-design mapping exists there),
// and for an image element with no flat to take a content box from. It does
// not register the art on its stitches — placeByContent does that.
export function fitRect(imgW, imgH, rect) {
  if (!rect || !(imgW > 0) || !(imgH > 0) || !(rect.w > 0) || !(rect.h > 0)) return null;
  const s = Math.min(rect.w / imgW, rect.h / imgH);
  const w = imgW * s;
  const h = imgH * s;
  return { x: rect.x + (rect.w - w) / 2, y: rect.y + (rect.h - h) / 2, w, h };
}

// Where to draw the WHOLE image so that its CONTENT box (`content`, in source
// px) lands centred in `rect` at a uniform scale. The stitches cover only the
// content, not the frame (the background was knocked out), so fitting the
// frame into the stitch rect shrinks and shifts the art; this registers it.
// Content equal to the whole frame reduces exactly to fitRect.
export function placeByContent(imgW, imgH, content, rect) {
  if (!(imgW > 0) || !(imgH > 0) || !content || !rect) return null;
  if (!(content.w > 0) || !(content.h > 0) || !(rect.w > 0) || !(rect.h > 0)) return null;
  const s = Math.min(rect.w / content.w, rect.h / content.h);
  const cx = rect.x + (rect.w - content.w * s) / 2;
  const cy = rect.y + (rect.h - content.h * s) / 2;
  return { x: cx - content.x * s, y: cy - content.y * s, w: imgW * s, h: imgH * s };
}

// The digitized lane's content box, in the 1,200-px preview's own px. The
// service reports where the sewn art sits as fractions of the image it was
// handed — the customer's crop of the upload — so the crop (fractions of the
// whole frame, or absent) maps it back to the whole frame. Null when the
// review carries no box (a saved element from before the service sent one).
export function digitizedContentBox(imgW, imgH, artBox, crop) {
  if (!(imgW > 0) || !(imgH > 0) || !Array.isArray(artBox) || artBox.length !== 4) return null;
  const [a0, b0, a1, b1] = artBox;
  const c = crop && crop.x1 > crop.x0 && crop.y1 > crop.y0 ? crop : { x0: 0, y0: 0, x1: 1, y1: 1 };
  const cw = c.x1 - c.x0, ch = c.y1 - c.y0;
  const w = (a1 - a0) * cw * imgW, h = (b1 - b0) * ch * imgH;
  if (!(w > 0) || !(h > 0)) return null;
  return { x: (c.x0 + a0 * cw) * imgW, y: (c.y0 + b0 * ch) * imgH, w, h };
}

// The browser lane's content box: the bbox of every flattened pixel that is
// NOT the engine's transparent index (quantize.js TRANSPARENT_INDEX, 255 —
// knocked-out background and alpha-cut pixels). These are the pixels
// `flatToRegions` traces, so the box comes from the same data as the
// stitches, not from a colour guess. It is not quite what is stitched:
// flatToRegions then drops specks and caps shapes per colour, so on noisy art
// this box can be slightly LARGER than the sewn extent. In the flat's own px
// grid; null when nothing is kept.
export const TRANSPARENT_INDEX = 255;
export function flatContentBox(indices, w, h) {
  if (!indices || !(w > 0) || !(h > 0)) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) {
    const row = y * w;
    for (let x = 0; x < w; x++) {
      if (indices[row + x] === TRANSPARENT_INDEX) continue;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  }
  if (x1 < 0) return null;
  return { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
}

// Decoded originals, keyed by the (large) source string. Bounded: every distinct
// upload used to stay here -- decoded bitmap plus its base64 key -- for the
// whole session, and removing the element never evicted it. Map order is
// insertion order, so re-inserting on a hit makes the first key the LRU one.
export const ORIGINAL_CACHE_MAX = 8;
const cache = new Map();
export function loadOriginal(sourcePng) {
  const url = originalDataUrl(sourcePng);
  if (!url) return Promise.reject(new Error("no original"));
  if (cache.has(sourcePng)) {
    const hit = cache.get(sourcePng);
    cache.delete(sourcePng);
    cache.set(sourcePng, hit);
    return hit;
  }
  const p = new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => resolve(im);
    im.onerror = () => { cache.delete(sourcePng); reject(new Error("original failed to decode")); };
    im.src = url;
  });
  cache.set(sourcePng, p);
  while (cache.size > ORIGINAL_CACHE_MAX) cache.delete(cache.keys().next().value);
  return p;
}
