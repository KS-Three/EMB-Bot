// rasterize.js — turning an uploaded file into pixels, once, for both upload
// lanes (DigitizePanel's auto-digitize and ImagePanel's browser flatten).
//
// It exists because the two panels held byte-identical copies of `loadImage`
// and the same work-size rule, and the rule was wrong for the same reason in
// both: `Math.min(1, MAX / longestSide)` never scales UP, which is exactly
// right for a raster (you cannot invent pixels a camera did not record) and
// exactly wrong for a vector, which has no pixels to invent.
//
// Measured 2026-09-07 in the shipped app. An SVG logo with a `viewBox` and no
// `width`/`height` — the shape SVGO and most hand-written exports produce —
// loads at Chrome's default 300 px wide. The panel then kept that 300 px, and
// the customer got:
//
//   "The image gives 3.1 pixels per millimetre at this size and needs 4.
//    Enlarging it can't add detail that isn't in the file — about 1.3x wider,
//    or a smaller design, will sew sharper."
//
// Every clause of which is false for a vector file: the detail IS in the file,
// and the app is what threw it away. `INPUT_LOW_RESOLUTION` (live defect 32)
// fires on a format that cannot be low-resolution.
//
// Re-rendering at the work size costs nothing and needs no SVG parsing: Chrome
// re-rasterises an SVG at whatever destination size `drawImage` is given.
// Measured on a 0.25-unit stripe in a 200-unit viewBox — thinner than one
// source pixel at the default size — the darkest pixel it produces:
//
//   rasterised at the natural 300 px (what shipped)     160  (a grey smear)
//   drawImage(img, 0, 0, 1200, 480)                       0  (a black line)
//   img.width/height set before drawing                    0
//   width/height injected into the SVG source              0
//
// The first of the three is used here: it is the destination size the panels
// already pass, so nothing else about their drawing changes.

// SVG is the only vector format a browser will decode into an <img>, so it is
// the only one this can be true of. Checked on the MIME type first because
// that is what the browser assigns from a real file picker, and on the
// extension second because a drag-and-drop, a rename, or an OS with no MIME
// database can leave the type empty — measured: a File with `type: ""` and
// SVG bytes fails to decode at all, so the extension is also what makes the
// fallback path reachable at all.
export function isVectorFile(file) {
  if (!file) return false;
  const type = (file.type || "").toLowerCase();
  if (type.includes("svg")) return true;
  return /\.svgz?$/i.test(file.name || "");
}

// The pixel size to rasterise `img` at, given a longest-side budget.
//
// Raster sources are only ever scaled DOWN — upscaling a photo makes a bigger
// file and not one extra pixel of detail, and the service does its own capped
// Lanczos when it needs more. Vector sources are rendered AT the budget in
// either direction, because their "natural" size is a browser default rather
// than a property of the artwork.
export function rasterSize(img, maxPx, opts = {}) {
  const iw = (img && img.width) || 0;
  const ih = (img && img.height) || 0;
  const longest = Math.max(iw, ih) || 1;
  const fit = maxPx / longest;
  const scale = opts.vector ? fit : Math.min(1, fit);
  return { w: Math.max(1, Math.round(iw * scale)), h: Math.max(1, Math.round(ih * scale)) };
}

// Decode a File to something drawable. `createImageBitmap` is tried first
// (faster, and it is what handles most raster formats); it does NOT handle
// SVG, which is why the <img> + object-URL fallback is not dead code.
//
// The rejection message names the formats that DO work, measured in this
// browser rather than assumed: PNG, JPEG, WebP, GIF, BMP and SVG all decode;
// PDF does not, and neither does anything that is not an image. Naming them
// is the difference between "the app is broken" and "export a PNG" for a
// customer whose logo is a PDF or an AI file, which is most of them.
export function loadImage(file, deps = {}) {
  const createBitmap = deps.createImageBitmap
    || (typeof createImageBitmap === "function" ? createImageBitmap : null);
  const makeUrl = deps.createObjectURL
    || ((f) => URL.createObjectURL(f));
  const dropUrl = deps.revokeObjectURL
    || ((u) => URL.revokeObjectURL(u));
  const ImageCtor = deps.Image || (typeof Image === "function" ? Image : null);

  const viaImg = () => {
    if (!ImageCtor) return Promise.reject(new Error(UNREADABLE));
    const url = makeUrl(file);
    return new Promise((resolve, reject) => {
      const img = new ImageCtor();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(UNREADABLE));
      img.src = url;
    }).finally(() => dropUrl(url));
  };

  if (!createBitmap) return viaImg();
  return Promise.resolve()
    .then(() => createBitmap(file))
    .catch(() => viaImg());
}

export const UNREADABLE =
  "Couldn’t read that file as an image. PNG, JPEG, WebP, GIF, BMP and SVG all work — " +
  "a PDF, AI or EPS logo needs to be exported as one of those first.";
