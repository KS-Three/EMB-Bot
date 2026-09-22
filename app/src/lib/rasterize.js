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

// What the panel SENDS. Since 2026-09-20 a raster upload goes to /digitize as
// the file itself: the canvas re-encode the panel used to send resampled
// seven of the nine corpus logos at Chrome's default "low" smoothing and
// rewrote the RGB under transparency through the canvas's premultiplied
// alpha — 503 -> 609 trims on the nine, Becker 59 -> 175 on an image the
// canvas never even resized (DOCTRINE 2026-09-19/20, scope-history
// 2026-09-20 §E). The service's own decoder caps at 2,800 px with a proper
// area filter, so the panel's resample bought the engine nothing; the 1,200
// px canvas stays as the localStorage PREVIEW (`element.sourcePng`) and the
// original's bytes go to IndexedDB (lib/sourceStore.js).
//
// The canvas PNG is still what goes up when the service cannot decode the
// file — its decoder is cv2: PNG, JPEG, WebP, BMP; not GIF, not SVG, which
// only a browser rasterises — or the file is outside the service's limits
// (/health `limits`; the defaults below are the service's own constants and
// only apply before /health has answered).
export const SERVICE_DECODES = new Set(["image/png", "image/jpeg", "image/webp", "image/bmp"]);
const EXT_MIME = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", bmp: "image/bmp" };
const DEFAULT_LIMITS = { max_upload_bytes: 12 * 1024 * 1024, max_pixels: 40_000_000 };

// A JPEG's pixel size from its SOF marker, or null. A phone JPEG carries its
// rotation in EXIF: the browser applies it when decoding (createImageBitmap
// defaults to imageOrientation "from-image"), the service does NOT —
// `cv2.imdecode(..., IMREAD_UNCHANGED)` ignores EXIF orientation by
// definition — so a JPEG whose decoded bitmap is not the header's size would
// digitize on its side if sent as it is. Those keep the canvas path, which is
// the browser's upright pixels.
export function jpegDimensions(bytes) {
  if (!bytes || bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return null;
  let i = 2;
  while (i + 9 < bytes.length) {
    if (bytes[i] !== 0xff) { i++; continue; }
    const marker = bytes[i + 1];
    if (marker === 0xff) { i++; continue; }                                            // fill byte
    if (marker === 0x01 || marker === 0xd8 || (marker >= 0xd0 && marker <= 0xd7)) { i += 2; continue; }   // standalone
    if (marker === 0xd9 || marker === 0xda) return null;                               // EOI / scan data before any SOF
    const len = (bytes[i + 2] << 8) | bytes[i + 3];
    const sof = marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc;
    if (sof) return { height: (bytes[i + 5] << 8) | bytes[i + 6], width: (bytes[i + 7] << 8) | bytes[i + 8] };
    i += 2 + len;
  }
  return null;
}

/**
 * -> { asIs, reason, type }: send the file's own bytes (asIs) or the canvas
 * PNG. `bytes` is optional — with it, a JPEG the browser rotated on decode is
 * caught (reason "orientation"); without it the cheaper checks alone decide,
 * which is how the panel asks once before reading the file and once after.
 */
export function uploadPlan(file, img, limits, bytes = null) {
  const lim = { ...DEFAULT_LIMITS, ...(limits || {}) };
  if (isVectorFile(file)) return { asIs: false, reason: "vector", type: null };
  const type = ((file && file.type) || "").toLowerCase();
  const ext = /\.([a-z0-9]+)$/i.exec((file && file.name) || "");
  const mime = SERVICE_DECODES.has(type) ? type : (!type && ext && EXT_MIME[ext[1].toLowerCase()]) || null;
  if (!mime) return { asIs: false, reason: "format", type: null };
  if (((file && file.size) || 0) > lim.max_upload_bytes) return { asIs: false, reason: "bytes", type: mime };
  const w = (img && img.width) || 0;
  const h = (img && img.height) || 0;
  if (w * h > lim.max_pixels) return { asIs: false, reason: "pixels", type: mime };
  if (mime === "image/jpeg" && bytes) {
    const dim = jpegDimensions(bytes);
    if (dim && (dim.width !== w || dim.height !== h)) return { asIs: false, reason: "orientation", type: mime };
  }
  return { asIs: true, reason: "", type: mime };
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
