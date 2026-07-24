import { designToStrands } from "./strands.js";
// Design stitches are in DST units, whose Y axis points UP; canvas Y points
// DOWN. fitTransform therefore returns a transform whose TY NEGATES y
// (canvasY = oy - y*scale) — without that flip every glyph renders vertically
// mirrored (upside-down letters).
export function fitTransform(design, cw, ch, pad) {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const s of design.stitches) { if (s.type === "color" || s.type === "end") continue; if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x; if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y; }
  const w = Math.max(1, maxX - minX), h = Math.max(1, maxY - minY);
  const scale = Math.min((cw - 2 * pad) / w, (ch - 2 * pad) / h);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  return { scale, ox: cw / 2 - cx * scale, oy: ch / 2 + cy * scale };
}

const MM_PER_INCH = 25.4; // inlined (no dependency on the engine global here)

// Maps HOOP mm-space (origin = hoop CENTER, +y UP — same convention as
// fitTransform, for the same DST-y-up reason) onto the canvas. Unlike
// fitTransform, this fits the full embroiderable hoop area — not just the
// design's bbox — into cw x ch, so the design renders at its true size and
// position within the garment/hoop frame instead of being stretched to fill
// the canvas.
export function hoopTransform(garment, cw, ch, pad) {
  const hoopWmm = garment.widthIn * MM_PER_INCH;
  const hoopHmm = garment.heightIn * MM_PER_INCH;
  const scale = Math.min((cw - 2 * pad) / hoopWmm, (ch - 2 * pad) / hoopHmm);
  return { scale, ox: cw / 2, oy: ch / 2, hoopWmm, hoopHmm };
}

function roundRectPath(ctx, x, y, w, h, r) {
  const rr = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

// Draws the hoop ring as a rounded-rect outline, plus a dashed inset
// (~3mm) suggesting the safe stitching margin inside the hoop's clamp.
export function drawHoopOutline(ctx, t) {
  const wPx = t.hoopWmm * t.scale, hPx = t.hoopHmm * t.scale;
  const x = t.ox - wPx / 2, y = t.oy - hPx / 2;
  const r = Math.min(16, wPx * 0.08, hPx * 0.08);
  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "rgba(60,50,40,0.35)";
  roundRectPath(ctx, x, y, wPx, hPx, r);
  ctx.stroke();
  const insetPx = 3 * t.scale; // ~3mm stitch-limit margin
  const iw = wPx - 2 * insetPx, ih = hPx - 2 * insetPx;
  if (iw > 0 && ih > 0) {
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(60,50,40,0.28)";
    roundRectPath(ctx, x + insetPx, y + insetPx, iw, ih, Math.max(0, r - insetPx));
    ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.restore();
}

export function renderRealistic(canvas, design, opts) {
  const o = opts || {};
  const ctx = canvas.getContext("2d");
  const cw = canvas.width, ch = canvas.height;
  ctx.fillStyle = o.fabric || "#e9e6df";
  ctx.fillRect(0, 0, cw, ch);

  const hooped = !!(o.hoop && o.hoop.garment);
  let t, TX, TY, pxPerMm;

  if (hooped) {
    t = hoopTransform(o.hoop.garment, cw, ch, o.pad || 24);
    TX = (xMm) => t.ox + xMm * t.scale;
    TY = (yMm) => t.oy - yMm * t.scale; // Y-flip: hoop mm y-up -> canvas y-down
    pxPerMm = t.scale;
    drawHoopOutline(ctx, t);
  } else {
    t = fitTransform(design, cw, ch, o.pad || 24);
    TX = (x) => t.ox + x * t.scale;
    TY = (y) => t.oy - y * t.scale; // Y-flip: DST y-up -> canvas y-down
    pxPerMm = t.scale * 10; // design-fit's scale is px per DST unit (0.1mm)
  }
  // Strand coordinates come straight from design.stitches, i.e. DST units
  // (0.1mm each). fitTransform's scale already absorbs that (it's computed
  // from the same raw units), so the design-fit path can feed them to TX/TY
  // untouched. hoopTransform's scale is px-per-mm though, so in hoop mode we
  // must convert DST units -> mm (/10) before applying it.
  const SX = hooped ? (x) => TX(x / 10) : TX;
  const SY = hooped ? (y) => TY(y / 10) : TY;

  const strands = designToStrands(design, { colorOverride: o.colorOverride });
  const lw = Math.max(1.5, 0.22 * pxPerMm); // thread thickness in px
  ctx.lineCap = "round";
  // shadow pass
  ctx.strokeStyle = "rgba(0,0,0,0.28)";
  ctx.lineWidth = lw;
  for (const s of strands) { ctx.beginPath(); ctx.moveTo(SX(s.x0) + 1, SY(s.y0) + 1.5); ctx.lineTo(SX(s.x1) + 1, SY(s.y1) + 1.5); ctx.stroke(); }
  // color pass
  ctx.lineWidth = lw;
  for (const s of strands) { ctx.strokeStyle = `rgb(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]})`; ctx.beginPath(); ctx.moveTo(SX(s.x0), SY(s.y0)); ctx.lineTo(SX(s.x1), SY(s.y1)); ctx.stroke(); }
  // highlight pass (sheen)
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = Math.max(0.6, lw * 0.35);
  for (const s of strands) { ctx.beginPath(); ctx.moveTo(SX(s.x0) - 0.6, SY(s.y0) - 0.9); ctx.lineTo(SX(s.x1) - 0.6, SY(s.y1) - 0.9); ctx.stroke(); }

  if (!hooped) return undefined;

  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9, any = false;
  for (const s of design.stitches) {
    if (s.type === "color" || s.type === "end") continue;
    any = true;
    if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x;
    if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y;
  }
  const designBBoxMm = any ? { x0: minX / 10, y0: minY / 10, x1: maxX / 10, y1: maxY / 10 } : null;
  return {
    toCanvas: (xMm, yMm) => ({ x: TX(xMm), y: TY(yMm) }),
    scale: t.scale,
    designBBoxMm,
  };
}
