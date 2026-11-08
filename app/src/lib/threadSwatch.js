// threadSwatch.js -- how a thread chip is DRAWN, so a customer sees how the
// colour sews (strands, crown, sheen) instead of a flat rgb square.
//
// One model, three consumers: `swatchStyle(rgb)` is the inline style a chip
// carries (a handful of custom properties), `SWATCH_BACKGROUND` is the one
// shared CSS gradient stack that theme.css pastes onto `.tp-thread` (a spec
// pins the two byte-for-byte), and `swatchMean`/`swatchPixel` evaluate the
// SAME stops in JS so a spec can measure what the chip averages to.
//
// The look is borrowed from the preview, not re-invented: the rim/shoulder
// tones and the sheen strength come out of `threadLayers` (preview.js) at the
// strand's own angle. A chip is long satin strands on a 4 px pitch, each
// shaded rim -> shoulder -> bright crown -> shoulder -> rim, and the strand
// ends dip into shade (the needle holes) the way CROWN_INSET does on the
// canvas.
//
// MEAN COLOUR: unbalanced shading makes a chip read darker than the thread it
// stands for, which is exactly what a colour picker must not do. So the shade
// is solved per thread: `tb` (the strand's base) is scaled so the chip's
// average comes back to the thread's rgb. Bright threads have no headroom to
// brighten into, so their shading depth `k` shrinks until the base fits
// (white is a flat white square; it has no shadow to show).
//
// Support: color-mix() (all current browsers). Without it the gradient
// declaration is dropped as invalid and the inline flat background-color is
// what shows -- the old chip, not a broken one.
import { threadLayers } from "./preview.js";
import { rgbToLab, ciede2000 } from "./colorMatch.js";

// Strands run up and to the right at 60 degrees clockwise from "up" (CSS
// angle), i.e. 30 degrees above horizontal. The cross-section gradient runs
// perpendicular to them; the end-shade gradient runs along them.
export const STRAND_ANGLE_DEG = 60;
export const CROSS_ANGLE_DEG = STRAND_ANGLE_DEG + 90;
export const PITCH_PX = 4; // one strand's width
export const END_FRAC = 0.22; // each strand end gives up this fraction to shade

// Pull the preview's own numbers once, off a mid grey so they are pure ratios.
const GREY = 128;
const rad = (STRAND_ANGLE_DEG * Math.PI) / 180;
// CSS angle -> canvas direction: CSS 0 = up, clockwise; canvas angle from +x, y down.
const canvasAngle = Math.atan2(-Math.cos(rad), Math.sin(rad));
const probe = threadLayers([GREY, GREY, GREY], canvasAngle, PITCH_PX);
const chan = (css) => Number(/rgb\((\d+)/.exec(css)[1]);
export const RIM = chan(probe[0].color) / GREY; // ~0.66
export const SHOULDER = chan(probe[1].color) / GREY; // ~0.85
// How far toward white the specular goes. threadLayers' own sheen term for
// this angle; the chip uses most of it, capped, because 4 px is too small for
// a full specular to read as anything but noise.
const SHEEN_FULL = (chan(probe[4].color) - GREY) / (255 - GREY);
export const SHEEN = Math.min(0.34, SHEEN_FULL * 0.9);
// Where the crown sits across the strand in px. The light is top-left, so it
// sits off-centre toward the lit edge, never on it.
const CROWN_POS = Math.max(1.4, Math.min(2.6, PITCH_PX / 2 + probe[4].offset));
const RIM_DROP = 1 - RIM;
const SHOULDER_DROP = 1 - SHOULDER;
const END_ALPHA = 0.2;

// Stops across one pitch. kind: rim | shoulder | crown.
export const CROSS_STOPS = [
  { pos: 0, kind: "rim" },
  { pos: CROWN_POS * 0.55, kind: "shoulder" },
  { pos: CROWN_POS, kind: "crown" },
  { pos: CROWN_POS + (PITCH_PX - CROWN_POS) * 0.45, kind: "shoulder" },
  { pos: PITCH_PX, kind: "rim" },
];

const KIND_VAR = { rim: "var(--tr)", shoulder: "var(--ts)" };
function stopCss(s) {
  const px = `${+s.pos.toFixed(2)}px`;
  if (s.kind === "crown") return `color-mix(in srgb, var(--tb), white var(--tw)) ${px}`;
  return `color-mix(in srgb, var(--tb) ${KIND_VAR[s.kind]}, black) ${px}`;
}

// The shared gradient stack: end shade on top, strands underneath.
export const SWATCH_BACKGROUND =
  `linear-gradient(${STRAND_ANGLE_DEG}deg, color-mix(in srgb, black var(--te), transparent) 0, transparent ${END_FRAC * 100}%, transparent ${(1 - END_FRAC) * 100}%, color-mix(in srgb, black var(--te), transparent) 100%), ` +
  `repeating-linear-gradient(${CROSS_ANGLE_DEG}deg, ${CROSS_STOPS.map(stopCss).join(", ")})`;

// ---- the model, as three scalar fields over the chip ----
// A pixel is   (tb * (1 - k*D - w*C) + 255 * w*C) * (1 - end*E)
//   D  how far this point on the strand has dropped toward shade (0 at the
//      crown, 1 - RIM at the rim; the cross-section, scaled by k),
//   C  the crown's sheen weight (1 at the crown stop, 0 at the others),
//   E  the strand-end shade (1 at a strand end, 0 END_FRAC in).
// None of them depends on the thread, so their means over a chip are computed
// ONCE per chip size and every thread's base is then solved in closed form.
const KIND_D = { rim: RIM_DROP, shoulder: SHOULDER_DROP, crown: 0 };
const KIND_C = { rim: 0, shoulder: 0, crown: 1 };

function along(deg, x, y, w, h) {
  const r = (deg * Math.PI) / 180;
  const dx = Math.sin(r), dy = -Math.cos(r);
  const len = Math.abs(w * dx) + Math.abs(h * dy);
  return { t: (x - w / 2) * dx + (y - h / 2) * dy + len / 2, len };
}

// D and C at (x, y), plus E.
function fields(x, y, w, h) {
  const p = (((along(CROSS_ANGLE_DEG, x, y, w, h).t % PITCH_PX) + PITCH_PX) % PITCH_PX);
  let D = 0, C = 0;
  for (let i = 0; i < CROSS_STOPS.length - 1; i++) {
    const a = CROSS_STOPS[i], b = CROSS_STOPS[i + 1];
    if (p >= a.pos && p <= b.pos) {
      const f = b.pos === a.pos ? 0 : (p - a.pos) / (b.pos - a.pos);
      D = KIND_D[a.kind] + (KIND_D[b.kind] - KIND_D[a.kind]) * f;
      C = KIND_C[a.kind] + (KIND_C[b.kind] - KIND_C[a.kind]) * f;
      break;
    }
  }
  const en = along(STRAND_ANGLE_DEG, x, y, w, h);
  const u = en.t / en.len;
  const E = Math.max(0, END_FRAC - Math.min(u, 1 - u)) / END_FRAC;
  return { D, C, E };
}

const meansBySize = new Map();
// Mean of E, D, C, D*E and C*E over a size x size padding box (4x4 samples per
// pixel). Cached per size; ~1.6k evaluations the first time, none after.
function chipMeans(size) {
  let m = meansBySize.get(size);
  if (m) return m;
  m = { E: 0, D: 0, C: 0, DE: 0, CE: 0 };
  const sub = 4, n = size * sub;
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const f = fields((i + 0.5) / sub, (j + 0.5) / sub, size, size);
      m.E += f.E; m.D += f.D; m.C += f.C; m.DE += f.D * f.E; m.CE += f.C * f.E;
    }
  }
  for (const key of Object.keys(m)) m[key] /= n * n;
  meansBySize.set(size, m);
  return m;
}

const clamp255 = (v) => Math.max(0, Math.min(255, v));
// How far a clamped base may leave the thread's mean, in dE00. A channel
// already at 255 cannot be brightened to pay for shade, so bright threads
// trade depth for colour; this is the price they are allowed to pay.
export const MAX_MEAN_DE = 1.2;

// The two coefficients of the chip's mean: mean = tb * A + 255 * B.
function coeffs(k, w, end, m) {
  const A = 1 - k * m.D - w * m.C - end * (m.E - k * m.DE - w * m.CE);
  const B = w * m.C - end * w * m.CE;
  return { A, B };
}

// Solve one thread for a chip of `size` px (padding box): the base `tb`, the
// depth `k`, the sheen weight `w`. Largest k in 0.1 steps whose chip mean stays
// within MAX_MEAN_DE of the thread (an exact fit while the base is in 0..255).
export function solveSwatch(rgb, size = 20) {
  const m = chipMeans(size);
  const lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255;
  const lab = rgbToLab(rgb);
  for (let step = 10; step >= 1; step--) {
    const k = step / 10;
    const w = SHEEN * k * Math.min(1, lum * 3);
    const end = END_ALPHA * k;
    const { A, B } = coeffs(k, w, end, m);
    const tb = [0, 0, 0];
    let clamped = false;
    for (let c = 0; c < 3; c++) {
      const v = (rgb[c] - 255 * B) / A;
      if (v < -0.25 || v > 255.25) clamped = true;
      tb[c] = clamp255(v);
    }
    if (clamped) {
      const mean = tb.map((v) => v * A + 255 * B);
      if (ciede2000(lab, rgbToLab(mean)) > MAX_MEAN_DE) continue;
    }
    return { k, w, tb, rim: 1 - RIM_DROP * k, shoulder: 1 - SHOULDER_DROP * k, end };
  }
  return { k: 0, w: 0, tb: rgb.slice(), rim: 1, shoulder: 1, end: 0 };
}

const pct = (x) => `${+(x * 100).toFixed(1)}%`;
// The inline style of one chip. background-color is the FLAT thread colour: the
// fallback if the gradient stack is not understood. `size` is the chip's
// padding box in px (24 for the trigger swatch, 20 for compact and grid cells).
export function swatchStyle(rgb, size = 20) {
  const s = solveSwatch(rgb, size);
  return (
    `background-color: rgb(${rgb[0]},${rgb[1]},${rgb[2]}); ` +
    `--tb: rgb(${Math.round(s.tb[0])},${Math.round(s.tb[1])},${Math.round(s.tb[2])}); ` +
    `--tr: ${pct(s.rim)}; --ts: ${pct(s.shoulder)}; --tw: ${pct(s.w)}; --te: ${pct(s.end)}`
  );
}

// ---- JS twin of the CSS, for measuring ----
// The parameters exactly as the inline style carries them (rounded).
function renderedParams(rgb, size) {
  const s = solveSwatch(rgb, size);
  const q = (v) => +pct(v).slice(0, -1) / 100;
  return { tb: s.tb.map(Math.round), rim: q(s.rim), shoulder: q(s.shoulder), w: q(s.w), end: q(s.end) };
}

// Colour of the pixel at (x, y) in a w x h padding box, interpolating the stops
// directly (not through the D/C fields the solver uses), so a spec comparing
// its mean with the thread also checks the solver.
function pixelOf(P, x, y, w, h) {
  const stopCol = (st) =>
    P.tb.map((v) => (st.kind === "crown" ? v * (1 - P.w) + 255 * P.w : v * (st.kind === "rim" ? P.rim : P.shoulder)));
  const p = (((along(CROSS_ANGLE_DEG, x, y, w, h).t % PITCH_PX) + PITCH_PX) % PITCH_PX);
  let col = P.tb;
  for (let i = 0; i < CROSS_STOPS.length - 1; i++) {
    const a = CROSS_STOPS[i], b = CROSS_STOPS[i + 1];
    if (p >= a.pos && p <= b.pos) {
      const f = b.pos === a.pos ? 0 : (p - a.pos) / (b.pos - a.pos);
      const ca = stopCol(a), cb = stopCol(b);
      col = ca.map((v, c) => v + (cb[c] - v) * f);
      break;
    }
  }
  const { E } = fields(x, y, w, h);
  return col.map((v) => v * (1 - P.end * E));
}

export function swatchPixel(rgb, x, y, size = 20) {
  return pixelOf(renderedParams(rgb, size), x, y, size, size);
}

// Mean colour over a size x size chip, `sub` x `sub` samples per pixel.
export function swatchMean(rgb, size = 20, sub = 4) {
  const P = renderedParams(rgb, size);
  const sum = [0, 0, 0];
  let n = 0;
  for (let j = 0; j < size * sub; j++) {
    for (let i = 0; i < size * sub; i++) {
      const px = pixelOf(P, (i + 0.5) / sub, (j + 0.5) / sub, size, size);
      sum[0] += px[0];
      sum[1] += px[1];
      sum[2] += px[2];
      n++;
    }
  }
  return sum.map((v) => v / n);
}
