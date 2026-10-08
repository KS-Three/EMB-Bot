// colorMatch.js — perceptual thread matching for the "match from a photo"
// tool: sample a patch of an image, rank a chart's threads by CIEDE2000.
//
// threads.js's nearestInList is a Euclidean scan in RGB. That is fine for
// naming a colour the design already carries, and it is NOT what this module
// uses: digitizer_core/threads.py records plain distance sending a dark navy
// to a grey thread, and snaps with CIEDE2000 instead. A tool whose whole job
// is "which cone is this colour" has to rank the way the digitizer does, so
// the maths below is a port of the same two skimage functions
// (rgb2lab, deltaE_ciede2000) and colorMatch.spec.js pins it to numbers
// generated from them — 48 pairs and 48 top-five rankings on three charts.
//
// Nothing here knows about the DOM. ThreadFromPhoto.svelte owns the canvas.

// sRGB (0-255) -> CIELAB, D65 / 2 degree observer: skimage's rgb2lab,
// constant for constant, so the two lanes agree to the last decimals.
const WHITE = [0.95047, 1.0, 1.08883];

function toLinear(v) {
  const c = v / 255;
  return c > 0.04045 ? Math.pow((c + 0.055) / 1.055, 2.4) : c / 12.92;
}

function fromLinear(l) {
  const c = l > 0.0031308 ? 1.055 * Math.pow(l, 1 / 2.4) - 0.055 : 12.92 * l;
  return Math.max(0, Math.min(255, Math.round(c * 255)));
}

function labF(t) {
  return t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116;
}

export function rgbToLab(rgb) {
  const r = toLinear(rgb[0]);
  const g = toLinear(rgb[1]);
  const b = toLinear(rgb[2]);
  const fx = labF((0.412453 * r + 0.35758 * g + 0.180423 * b) / WHITE[0]);
  const fy = labF((0.212671 * r + 0.71516 * g + 0.072169 * b) / WHITE[1]);
  const fz = labF((0.019334 * r + 0.119193 * g + 0.950227 * b) / WHITE[2]);
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

const TWO_PI = 2 * Math.PI;
const POW25_7 = Math.pow(25, 7);
const rad = (deg) => (deg * Math.PI) / 180;

// CIEDE2000 between two Lab triples, kL = kC = kH = 1.
export function ciede2000(lab1, lab2) {
  const [L1, a1, b1] = lab1;
  const [L2, a2, b2] = lab2;

  const cbar = 0.5 * (Math.hypot(a1, b1) + Math.hypot(a2, b2));
  const c7 = Math.pow(cbar, 7);
  const scale = 1 + 0.5 * (1 - Math.sqrt(c7 / (c7 + POW25_7)));
  const ap1 = a1 * scale;
  const ap2 = a2 * scale;
  const C1 = Math.hypot(ap1, b1);
  const C2 = Math.hypot(ap2, b2);
  let h1 = Math.atan2(b1, ap1);
  let h2 = Math.atan2(b2, ap2);
  if (h1 < 0) h1 += TWO_PI;
  if (h2 < 0) h2 += TWO_PI;

  // Lightness
  const Lbar = 0.5 * (L1 + L2);
  const lt = (Lbar - 50) * (Lbar - 50);
  const SL = 1 + (0.015 * lt) / Math.sqrt(20 + lt);
  const Lterm = (L2 - L1) / SL;

  // Chroma
  const Cbar = 0.5 * (C1 + C2);
  const SC = 1 + 0.045 * Cbar;
  const Cterm = (C2 - C1) / SC;

  // Hue. A grey has no hue, so when either chroma is zero the hue
  // difference is zero and the mean hue is the other colour's.
  const hDiff = h2 - h1;
  const hSum = h1 + h2;
  const CC = C1 * C2;
  let dH = hDiff;
  if (hDiff > Math.PI) dH -= TWO_PI;
  else if (hDiff < -Math.PI) dH += TWO_PI;
  if (CC === 0) dH = 0;
  const dHterm = 2 * Math.sqrt(CC) * Math.sin(dH / 2);

  let Hbar = hSum;
  if (CC !== 0 && Math.abs(hDiff) > Math.PI) Hbar += hSum < TWO_PI ? TWO_PI : -TWO_PI;
  if (CC === 0) Hbar *= 2;
  Hbar *= 0.5;

  const T =
    1 -
    0.17 * Math.cos(Hbar - rad(30)) +
    0.24 * Math.cos(2 * Hbar) +
    0.32 * Math.cos(3 * Hbar + rad(6)) -
    0.2 * Math.cos(4 * Hbar - rad(63));
  const SH = 1 + 0.015 * Cbar * T;
  const Hterm = dHterm / SH;

  // The blue-region rotation term.
  const cb7 = Math.pow(Cbar, 7);
  const Rc = 2 * Math.sqrt(cb7 / (cb7 + POW25_7));
  const hbarDeg = (Hbar * 180) / Math.PI;
  const dTheta = rad(30) * Math.exp(-Math.pow((hbarDeg - 275) / 25, 2));
  const Rterm = -Math.sin(2 * dTheta) * Rc * Cterm * Hterm;

  return Math.sqrt(Math.max(0, Lterm * Lterm + Cterm * Cterm + Hterm * Hterm + Rterm));
}

// The `n` threads in `list` nearest to `rgb`, nearest first, each with its
// colour difference: [{ name, code, rgb, index, deltaE }]. Ties keep chart
// order, as the Python chart's argmin does. A chart is at most ~1,700
// threads, so a full scan and sort is a few milliseconds per click.
export function rankThreads(list, rgb, n = 5) {
  if (!list || !list.length || !rgb) return [];
  const ref = rgbToLab(rgb);
  const scored = list.map((t, index) => ({
    name: t.name,
    code: t.code || "",
    rgb: t.rgb,
    index,
    deltaE: ciede2000(ref, rgbToLab(t.rgb)),
  }));
  scored.sort((p, q) => p.deltaE - q.deltaE || p.index - q.index);
  return scored.slice(0, n);
}

// Mean colour of the square patch of half-width `radius` centred on (x, y)
// in an ImageData-shaped { data, width, height }: { rgb, count } or null
// when the patch holds no opaque pixel. A patch rather than one pixel
// because a photo's single pixel is sensor noise, JPEG ringing or one fibre's
// highlight. The mean is taken in linear light — averaging sRGB numbers
// darkens a mix (half black, half white comes out 128, where the light that
// reached the lens is 188).
export function samplePatch(img, x, y, radius = 4) {
  if (!img || !img.data) return null;
  const { data, width, height } = img;
  const cx = Math.round(x);
  const cy = Math.round(y);
  const x0 = Math.max(0, cx - radius);
  const x1 = Math.min(width - 1, cx + radius);
  const y0 = Math.max(0, cy - radius);
  const y1 = Math.min(height - 1, cy + radius);
  let r = 0;
  let g = 0;
  let b = 0;
  let count = 0;
  for (let py = y0; py <= y1; py++) {
    for (let px = x0; px <= x1; px++) {
      const i = (py * width + px) * 4;
      if (data[i + 3] < 128) continue;
      r += toLinear(data[i]);
      g += toLinear(data[i + 1]);
      b += toLinear(data[i + 2]);
      count++;
    }
  }
  if (!count) return null;
  return { rgb: [fromLinear(r / count), fromLinear(g / count), fromLinear(b / count)], count };
}

// A colour difference in plain words, on the bands preflight.DELTA_E_VISIBLE
// already cites (Mokrzycki & Tatol 2011): 1 is a just-noticeable difference,
// 2-3.5 visible to an attentive eye, 3.5-5 clear, above 5 two colours.
export function matchWord(deltaE) {
  if (!Number.isFinite(deltaE)) return "";
  if (deltaE < 1) return "very close";
  if (deltaE < 2) return "close";
  if (deltaE < 3.5) return "noticeable";
  if (deltaE < 5) return "clearly different";
  return "a different colour";
}

// Below this CIEDE2000 distance a thread reads as the same colour as the
// garment at arm's length. UI policy, not physics, set on the Studio's own
// swatches: Black thread on Black (0), on Navy (13), White on Natural (6) and
// Natural on Sand (10) all fall under it; Royal on Navy (16) and White on
// Sand (16) are the nearest pairs that clear it.
export const FABRIC_CONTRAST_MIN = 15;

// The field stopped painting the garment colour in #648 (it shows a neutral
// work bed), so black thread on a black cap looked exactly like black thread
// on a white polo: nothing on screen said the design would vanish. This is
// that warning. It speaks only when EVERY colour in the design sits under
// FABRIC_CONTRAST_MIN — one garment-coloured region in a logo is often
// deliberate (the auto-digitizer leaves those holes unsewn on purpose), but a
// design with no colour that stands out sews as an invisible patch. `colors`
// is the combined design's [{ r, g, b }]; empty string when there is nothing
// to say, so callers can `{#if}` on it like the other caption notes.
export function fabricContrastNote(colors, fabricRgb) {
  if (!Array.isArray(colors) || !colors.length || !Array.isArray(fabricRgb)) return "";
  const fab = rgbToLab(fabricRgb);
  const close = colors.every((c) => c && ciede2000(rgbToLab([c.r, c.g, c.b]), fab) < FABRIC_CONTRAST_MIN);
  if (!close) return "";
  const what = colors.length === 1 ? "Thread color is" : "Every thread color is";
  return `${what} too close to the fabric color — the design will barely show; pick a contrasting thread or fabric`;
}
