// The artwork a customer uploaded, for the field's Original view (spec §4).
// `element.sourcePng` is bare base64 — the 1,200-px preview both the image
// and the digitized lanes keep on the element (lib/project.js).
export function originalDataUrl(sourcePng) {
  return typeof sourcePng === "string" && sourcePng.length > 0 ? "data:image/png;base64," + sourcePng : null;
}

export function hasOriginal(el) {
  return !!el && (el.type === "image" || el.type === "digitized") && !!originalDataUrl(el.sourcePng);
}

// Aspect-preserving fit of an image inside `rect`, centred. The rect is the
// one the element's own stitches occupy, so flipping Original <-> Stitches
// compares like with like at the same place and size.
export function fitRect(imgW, imgH, rect) {
  if (!rect || !(imgW > 0) || !(imgH > 0) || !(rect.w > 0) || !(rect.h > 0)) return null;
  const s = Math.min(rect.w / imgW, rect.h / imgH);
  const w = imgW * s;
  const h = imgH * s;
  return { x: rect.x + (rect.w - w) / 2, y: rect.y + (rect.h - h) / 2, w, h };
}

const cache = new Map();
export function loadOriginal(sourcePng) {
  const url = originalDataUrl(sourcePng);
  if (!url) return Promise.reject(new Error("no original"));
  if (cache.has(sourcePng)) return cache.get(sourcePng);
  const p = new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => resolve(im);
    im.onerror = () => { cache.delete(sourcePng); reject(new Error("original failed to decode")); };
    im.src = url;
  });
  cache.set(sourcePng, p);
  return p;
}
