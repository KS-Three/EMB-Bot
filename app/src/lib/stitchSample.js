// The click-to-edit popover's stitch sample (2026-11-07).
//
// Changing a shape's stitch type, angle or colour in the popover showed
// nothing until the design was sewn again: the choice was a word in a select.
// This draws a small patch of the chosen stitching -- satin, tatami, brick, a
// single run or a bean -- at the chosen angle and thread colour, through the
// SAME `drawThreads` the field's realistic view uses, so the sample's thread
// is the field's thread (same sheen, same crown, same per-kind style) and not
// a second idea of what stitching looks like.
//
// A LOOK, not a sew-out: nothing here is a sewing number. Row and cross
// spacing are the engine's own (EMB.FILL_ROW_MM / EMB.SATIN_SPACING_MM, read
// off the engine global, never re-declared -- the shapePopover.runDefaults
// rule), and the patch is clipped to a 12 x 8 mm rectangle that is not the
// shape. With no engine loaded (a unit test) `sampleDensities()` is null and
// the popover draws nothing; the strand builder itself takes every number as
// an argument so a spec can drive it directly.
//
// Coordinates: mm, Y DOWN (canvas space). An angle is degrees in that space,
// clockwise on screen from +X -- the frame both engines rotate their fill rows
// in (fill.js and stage6_scanline rotate the shape by -angle, scan
// horizontal rows, rotate back), before any DST Y flip.
import { drawThreads, isDark, THREAD_WIDTH_MM } from "./preview.js";

export const SAMPLE_W_MM = 12;
export const SAMPLE_H_MM = 8;
// CSS px per mm of the sample canvas: 120 x 80 CSS px, which fits the
// popover's 260 px width with its padding. A display scale only.
export const SAMPLE_PX_PER_MM = 10;
// The stitch length a tatami/brick row is cut into when the caller gives
// none: the digitized lane's `machine.FILL_STITCH_MM` (3.0), quoted for the
// picture only -- the browser lane's own is 4 (digitize.js maxStitchMm). It
// sets where the sample's row breaks fall, nothing that sews.
const FILL_STITCH_FALLBACK_MM = 3;
// A run/bean sample's line spacing: parallel lines across the patch, so
// a single line reads as a LINE and not as a lone scratch. A layout choice.
const RUN_LINE_GAP_MM = 2;
// Where the angle row says "auto", the sample is drawn at this angle and the
// caption says so -- the shape's own auto angle is the digitizer's to pick.
export const AUTO_SAMPLE_ANGLE = 45;
// A satin with no angle row (the digitized lane offers none for satin; a
// hand-drawn column follows its own spine): vertical crosses, i.e. a column
// running across the patch.
const SATIN_DEFAULT_ANGLE = 90;

export const SAMPLE_TYPES = ["satin", "tatami", "brick", "run", "bean"];

// The engine's spacings, or null before the engine has loaded.
export function sampleDensities(eng = globalThis.EMB) {
  if (!eng || !(eng.FILL_ROW_MM > 0) || !(eng.SATIN_SPACING_MM > 0)) return null;
  const g = eng.LETTERING_GUARDS;
  return {
    rowMm: eng.FILL_ROW_MM,
    satinMm: eng.SATIN_SPACING_MM,
    runStitchMm: g && g.BEAN_STITCH_MM > 0 ? g.BEAN_STITCH_MM : null,
  };
}

// The tier word a model's stitch-type value names, as a sample type. "auto"
// reads the effective tier out of the Auto option's own label ("Auto (fill)").
function typeFromTier(v, row) {
  let t = v;
  if (t === "auto" && row && Array.isArray(row.options)) {
    const auto = row.options.find((o) => o.value === "auto");
    const m = auto && /\(([a-z_]+)\)/i.exec(auto.label || "");
    t = m ? m[1].toLowerCase() : null;
  }
  if (t === "satin" || t === "border") return "satin";
  if (t === "fill" || t === "tatami") return "tatami";
  if (t === "brick") return "brick";
  if (t === "run") return "run";
  if (t === "bean") return "bean";
  return null;
}

function parseAngle(v) {
  if (v == null || v === "" || v === "auto") return null;
  const n = typeof v === "number" ? v : parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

// What the popover's sample draws for this model, with `picks` (the values
// the person just chose, keyed like the rows: stitchType / angle / color /
// passes / stitchLenMm) taking precedence over the model's stored ones -- so
// the sample answers the pick at once, before the field's patch round-trip.
// null: nothing to sample (a cut-out, a preset shape, an unknown tier).
export function sampleSpecFromModel(model, picks = {}) {
  if (!model || !Array.isArray(model.rows)) return null;
  const row = (k) => model.rows.find((r) => r && r.key === k);
  const pick = (k, fallback) => (Object.prototype.hasOwnProperty.call(picks, k) ? picks[k] : fallback);
  const colorRow = model.rows.find((r) => r && r.kind === "thread");
  const rgb = pick("color", colorRow ? colorRow.rgb : null);
  if (!Array.isArray(rgb) || rgb.length < 3) return null;

  const typeRow = row("stitchType");
  const passesRow = row("passes");
  let type = null;
  if (typeRow) type = typeFromTier(pick("stitchType", typeRow.value), typeRow);
  else if (passesRow) type = String(pick("passes", passesRow.value)) === "1" ? "run" : "bean";
  else if (row("widthMm")) type = "satin"; // a hand-drawn column
  if (!type) return null;

  const angleRow = row("angle");
  const chosen = angleRow ? parseAngle(pick("angle", angleRow.value)) : null;
  const auto = chosen == null;
  const angleDeg = !auto ? chosen : (type === "satin" && !angleRow ? SATIN_DEFAULT_ANGLE : AUTO_SAMPLE_ANGLE);
  const lenRow = row("stitchLenMm");
  const len = lenRow ? parseFloat(pick("stitchLenMm", lenRow.value)) : NaN;
  return {
    type,
    angleDeg,
    autoAngle: auto && !!angleRow,
    rgb: [rgb[0], rgb[1], rgb[2]],
    stitchMm: Number.isFinite(len) && len > 0 ? len : null,
  };
}

// The sample's caption: what is drawn, in the popover's own words.
export function sampleCaption(spec) {
  if (!spec) return "";
  const word = { satin: "Satin", tatami: "Fill", brick: "Brick", run: "Run", bean: "Bean" }[spec.type] || spec.type;
  if (spec.type === "run" || spec.type === "bean") return word + " sample";
  return word + " sample, " + (spec.autoAngle ? "auto angle (shown " + spec.angleDeg + "°)" : spec.angleDeg + "°");
}

// Clip the infinite line p + s*d (|d| = 1) to the rectangle [0,w] x [0,h]:
// the [s0, s1] it spends inside, or null (Liang-Barsky).
function clipLine(px, py, dx, dy, w, h) {
  let s0 = -Infinity, s1 = Infinity;
  const edges = [[-dx, px], [dx, w - px], [-dy, py], [dy, h - py]];
  for (const [p, q] of edges) {
    if (Math.abs(p) < 1e-12) { if (q < 0) return null; continue; }
    const r = q / p;
    if (p < 0) { if (r > s1) return null; if (r > s0) s0 = r; }
    else { if (r < s0) return null; if (r < s1) s1 = r; }
  }
  return s1 - s0 > 1e-9 ? [s0, s1] : null;
}

// The lines at `angleDeg` that cross the patch, `gap` mm apart, centred: each
// as { px, py, dx, dy, s0, s1, i } (point on the line, unit direction, the
// clipped span, the row index).
// `half` shifts the set half a gap, so no line runs along the centre (a run
// sample's lines then sit clear of the patch edges at 0 and 90 degrees).
function rowsAcross(angleDeg, gap, w, h, half = false) {
  const a = (angleDeg * Math.PI) / 180;
  const dx = Math.cos(a), dy = Math.sin(a);
  const nx = -dy, ny = dx;
  const cx = w / 2, cy = h / 2;
  const R = Math.hypot(w, h) / 2;
  const n = Math.ceil(R / gap);
  const out = [];
  const o = half ? 0.5 : 0;
  for (let i = -n; i <= n; i++) {
    const px = cx + nx * (i + o) * gap, py = cy + ny * (i + o) * gap;
    const span = clipLine(px, py, dx, dy, w, h);
    if (span) out.push({ px, py, dx, dy, s0: span[0], s1: span[1], i });
  }
  return out;
}

// Cut one row into stitches `len` long, the holes on a grid shifted by
// `phase` (a fraction of `len`) -- the stagger that makes tatami read as a
// fabric instead of as stripes.
function cutRow(r, len, phase, rgb, kind, out) {
  const first = Math.floor(r.s0 / len - phase) + phase;
  let a = r.s0;
  for (let k = first + 1; ; k++) {
    const b = Math.min(r.s1, k * len);
    if (b - a > 1e-6) out.push({ x0: r.px + r.dx * a, y0: r.py + r.dy * a, x1: r.px + r.dx * b, y1: r.py + r.dy * b, rgb, kind });
    if (b >= r.s1) break;
    a = b;
  }
}

// The patch's strands, in mm (Y down), ready for drawThreads.
//   type: satin | tatami | brick | run | bean
//   rowMm: tatami/brick row spacing; satinMm: satin cross spacing
//   stitchMm: a fill row's stitch length (tatami/brick) or a run's
export function sampleStrands({ type, angleDeg = 0, rgb, rowMm, satinMm, stitchMm, wMm = SAMPLE_W_MM, hMm = SAMPLE_H_MM }) {
  const out = [];
  if (!Array.isArray(rgb)) return out;
  if (type === "satin") {
    if (!(satinMm > 0)) return out;
    // One cross per row, hole to hole across the patch; alternate crosses
    // run back the other way, as the needle does.
    for (const r of rowsAcross(angleDeg, satinMm, wMm, hMm)) {
      const [a, b] = (r.i & 1) ? [r.s1, r.s0] : [r.s0, r.s1];
      out.push({ x0: r.px + r.dx * a, y0: r.py + r.dy * a, x1: r.px + r.dx * b, y1: r.py + r.dy * b, rgb, kind: "satin" });
    }
    return out;
  }
  if (type === "tatami" || type === "brick") {
    if (!(rowMm > 0)) return out;
    const len = stitchMm > 0 ? stitchMm : FILL_STITCH_FALLBACK_MM;
    // Tatami steps its holes a third of a stitch per row; brick a half,
    // every other row.
    const cycle = type === "brick" ? 2 : 3;
    for (const r of rowsAcross(angleDeg, rowMm, wMm, hMm)) {
      const k = ((r.i % cycle) + cycle) % cycle;
      cutRow(r, len, k / cycle, rgb, "fill", out);
    }
    return out;
  }
  if (type === "run" || type === "bean") {
    const len = stitchMm > 0 ? stitchMm : FILL_STITCH_FALLBACK_MM;
    for (const r of rowsAcross(angleDeg, RUN_LINE_GAP_MM, wMm, hMm, true)) {
      const line = [];
      cutRow(r, len, 0, rgb, type, line);
      if (type === "run") { out.push(...line); continue; }
      // A bean sews each stitch forward, back, forward over the same holes.
      for (const s of line) {
        out.push(s);
        out.push({ x0: s.x1, y0: s.y1, x1: s.x0, y1: s.y0, rgb, kind: "bean" });
        out.push({ ...s });
      }
    }
    return out;
  }
  return out;
}

// Paint the sample into a 2D context. `ctx` may carry a dpr transform; this
// works in CSS px. The ground is a plain neutral that the thread reads
// against (light behind a dark thread, dark behind a light one) -- the
// popover does not know the garment, and a guessed fabric would lie.
export function paintSample(ctx, strands, rgb, { pxPerMm = SAMPLE_PX_PER_MM, wMm = SAMPLE_W_MM, hMm = SAMPLE_H_MM } = {}) {
  const w = wMm * pxPerMm, h = hMm * pxPerMm;
  ctx.fillStyle = rgb && isDark(rgb) ? "rgb(214,214,210)" : "rgb(58,58,62)";
  ctx.fillRect(0, 0, w, h);
  if (!strands.length) return;
  const lw = Math.max(1.2, THREAD_WIDTH_MM * pxPerMm);
  drawThreads(ctx, strands, (x) => x * pxPerMm, (y) => y * pxPerMm, lw);
}

// The popover's whole draw: size the canvas for `dpr`, build, paint. Returns
// the strand count (0 when there is nothing to draw).
export function drawStitchSample(canvas, spec, dens, { dpr = 1, pxPerMm = SAMPLE_PX_PER_MM } = {}) {
  if (!canvas || !spec || !dens) return 0;
  const W = Math.round(SAMPLE_W_MM * pxPerMm * dpr), H = Math.round(SAMPLE_H_MM * pxPerMm * dpr);
  if (canvas.width !== W) canvas.width = W;
  if (canvas.height !== H) canvas.height = H;
  const ctx = canvas.getContext && canvas.getContext("2d");
  if (!ctx) return 0;
  const strands = sampleStrands({
    type: spec.type, angleDeg: spec.angleDeg, rgb: spec.rgb,
    rowMm: dens.rowMm, satinMm: dens.satinMm,
    stitchMm: spec.stitchMm || ((spec.type === "run" || spec.type === "bean") ? dens.runStitchMm : null),
  });
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  paintSample(ctx, strands, spec.rgb, { pxPerMm });
  return strands.length;
}
