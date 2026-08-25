import { designToStrands, jumpTrimMarks } from "./strands.js";

// ---- Fabric contrast helpers (Slice 8 Task 2, B7) --------------------------
// Perceived brightness (ITU-R BT.709 relative-luminance weights), normalized
// to 0 (black) .. 1 (white). Pure + cheap on purpose: every render-path
// decision that needs to stay legible against an arbitrary fabric color
// (hoop outline, its dashed inset, the selection box + corner handles) reuses
// this SAME helper, so "what counts as dark" can never drift between them.
export function luminance(rgb) {
  const [r, g, b] = rgb;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

// Below 0.5 the fabric reads as "dark" -- callers should switch whatever
// chrome they're drawing to a light variant to stay legible on top of it.
export function isDark(rgb) {
  return luminance(rgb) < 0.5;
}

const DEFAULT_FABRIC_RGB = [235, 232, 223]; // matches project.js's defaultProject() fabricRgb

function rgbCss(rgb, alpha) {
  return alpha == null
    ? `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`
    : `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;
}

// ---- The lit filament -----------------------------------------------------
// Thread is a cylinder lying on cloth, not a coloured line. Two consequences,
// and this renderer had neither until 2026-08-25, when Kent said of a fill
// sheet: *"It feels like i'm looking at an image made up of vectors and not
// stitches."*
//
//   1. HOW MUCH light a filament catches depends on its angle to the source,
//      so a field of parallel rows stops being one flat tone.
//   2. WHERE its highlight sits is off-centre, toward the light, with the far
//      side in shadow. That shadow is what separates one row from the next.
//
// This is the SAME model as `digitizer_core/stitchviz.py`'s `_draw_filament`,
// deliberately: what Kent rules on in an acceptance sheet and what a customer
// sees on the canvas have to agree. Change one, change both.
//
// The light is in CANVAS coordinates, where y increases downward -- 225 deg is
// up and to the left, which is what the old fixed offsets (+1/+1.5 shadow,
// -0.6/-0.9 sheen) were approximating.
const THREAD_MM = 0.4; // 40wt polyester filament diameter; was 0.22 here, i.e.
                       // 55% of real width, which is why thread read as line art
const LIGHT_DEG = 225;
const LX = Math.cos((LIGHT_DEG * Math.PI) / 180);
const LY = Math.sin((LIGHT_DEG * Math.PI) / 180);
const AMBIENT = 0.8;
const DIFFUSE = 0.42;
// [width, offset toward light, tone], as fractions of the nominal width.
// Every band is clamped inside that width by drawFilament, so shading never
// widens the drawn thread -- the Python side measures coverage by rendering,
// and the two models are kept identical.
const BANDS = [
  [1.0, 0.0, 0.62],   // shadowed body -- defines the footprint
  [0.66, 0.14, 1.0],  // lit body
  [0.28, 0.26, 1.22], // specular
];

export function drawFilament(ctx, x0, y0, x1, y1, rgb, lw) {
  const dx = x1 - x0;
  const dy = y1 - y0;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;

  // Lambert on a cylinder: the axis-to-light cross product. Absolute value
  // because a filament is symmetric -- signing it would make sew DIRECTION
  // show up as tone, so the same row sewn back the other way would differ.
  const tone = AMBIENT + DIFFUSE * Math.abs(ux * LY - uy * LX);

  // Perpendicular, resolved to point at the light.
  let nx = -uy;
  let ny = ux;
  if (nx * LX + ny * LY < 0) { nx = -nx; ny = -ny; }

  for (const [wFrac, offFrac, shade] of BANDS) {
    const w = Math.max(0.5, wFrac * lw);
    const off = Math.max(0, Math.min(offFrac * lw, (lw - w) / 2));
    const k = tone * shade;
    ctx.strokeStyle = `rgb(${Math.min(255, Math.round(rgb[0] * k))},${Math.min(255, Math.round(rgb[1] * k))},${Math.min(255, Math.round(rgb[2] * k))})`;
    ctx.lineWidth = w;
    ctx.beginPath();
    ctx.moveTo(x0 + nx * off, y0 + ny * off);
    ctx.lineTo(x1 + nx * off, y1 + ny * off);
    ctx.stroke();
  }
}

// A cheap procedural weave: a low-alpha crosshatch (both directions, every
// ~3px) in a tone darkened off the fabric color, drawn AFTER the bg fill but
// BEFORE strands. Skipped when the view is zoomed out enough that the lines
// would just read as noise (< 1.5 px/mm) rather than texture. Kept as a pure,
// spy-testable helper -- it only calls ctx methods, no state of its own.
export function weavePattern(ctx, w, h, rgb, pxPerMm) {
  if (pxPerMm < 1.5) return;
  const step = 3;
  const dr = Math.max(0, rgb[0] - 30);
  const dg = Math.max(0, rgb[1] - 30);
  const db = Math.max(0, rgb[2] - 30);
  ctx.save();
  ctx.strokeStyle = rgbCss([dr, dg, db], 0.08);
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0; x <= w; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
  for (let y = 0; y <= h; y += step) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
  ctx.stroke();
  ctx.restore();
}

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
// `fabricRgb` (B7) picks the outline/inset tone: the original dark-on-light
// chrome when the fabric is light (or unspecified -- back-compat), a light
// variant when the fabric is dark enough that the dark chrome would wash out.
export function drawHoopOutline(ctx, t, fabricRgb) {
  const dark = isDark(fabricRgb || DEFAULT_FABRIC_RGB);
  const outlineColor = dark ? "rgba(255,255,255,0.45)" : "rgba(60,50,40,0.35)";
  const insetColor = dark ? "rgba(255,255,255,0.35)" : "rgba(60,50,40,0.28)";
  const wPx = t.hoopWmm * t.scale, hPx = t.hoopHmm * t.scale;
  const x = t.ox - wPx / 2, y = t.oy - hPx / 2;
  const r = Math.min(16, wPx * 0.08, hPx * 0.08);
  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = outlineColor;
  roundRectPath(ctx, x, y, wPx, hPx, r);
  ctx.stroke();
  const insetPx = 3 * t.scale; // ~3mm stitch-limit margin
  const iw = wPx - 2 * insetPx, ih = hPx - 2 * insetPx;
  if (iw > 0 && ih > 0) {
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = insetColor;
    roundRectPath(ctx, x + insetPx, y + insetPx, iw, ih, Math.max(0, r - insetPx));
    ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.restore();
}

// opts:
//   fabric        CSS color string bg fill (FontSelect/exportPNG's existing
//                  contract -- stays working, B5).
//   fabricRgb      [r,g,b] bg fill; WINS over `fabric` when both given (B5).
//   colorOverride  existing strand-recolor contract -- unchanged.
//   weave          true -> draw weavePattern() over the bg fill (needs
//                  fabricRgb; a no-op without it).
//   view           { zoom, panX, panY } -- defaults to identity, so callers
//                  that never pass one (FontSelect thumbnails, exportPNG) get
//                  back exactly the pre-Slice-8 transform. B1 (BLOCKING): the
//                  returned contract is POST-VIEW -- scale = base.scale *
//                  view.zoom, and toCanvas already has pan baked in. zoom is
//                  applied about the CANVAS CENTER (so plain zoom-in-place
//                  keeps the hoop centered) and pan is then added in canvas
//                  px -- wheel-zoom-around-cursor is the caller's job (solve
//                  for the panX/panY that keep the cursor's mm-point fixed;
//                  see EmbroideryField's zoomBy()), not this function's.
export function renderRealistic(canvas, design, opts) {
  const o = opts || {};
  const ctx = canvas.getContext("2d");
  const cw = canvas.width, ch = canvas.height;
  const view = o.view || { zoom: 1, panX: 0, panY: 0 };
  const zoom = view.zoom || 1;
  const panX = view.panX || 0;
  const panY = view.panY || 0;

  ctx.fillStyle = o.fabricRgb ? rgbCss(o.fabricRgb) : (o.fabric || "#e9e6df");
  ctx.fillRect(0, 0, cw, ch);

  const hooped = !!(o.hoop && o.hoop.garment);
  let t, TX0, TY0, pxPerMm0;

  if (hooped) {
    t = hoopTransform(o.hoop.garment, cw, ch, o.pad || 24);
    TX0 = (xMm) => t.ox + xMm * t.scale;
    TY0 = (yMm) => t.oy - yMm * t.scale; // Y-flip: hoop mm y-up -> canvas y-down
    pxPerMm0 = t.scale;
  } else {
    t = fitTransform(design, cw, ch, o.pad || 24);
    TX0 = (x) => t.ox + x * t.scale;
    TY0 = (y) => t.oy - y * t.scale; // Y-flip: DST y-up -> canvas y-down
    pxPerMm0 = t.scale * 10; // design-fit's scale is px per DST unit (0.1mm)
  }

  // Post-view transform (B1): zoom about the canvas center, then translate by
  // pan (both in canvas-px). With the default identity view (zoom=1,
  // panX=panY=0) this reduces to exactly TX0/TY0 -- unchanged behavior for
  // every caller that doesn't pass `view`.
  const ccx = cw / 2, ccy = ch / 2;
  const TX = (v) => ccx + (TX0(v) - ccx) * zoom + panX;
  const TY = (v) => ccy + (TY0(v) - ccy) * zoom + panY;
  const pxPerMm = pxPerMm0 * zoom;

  if (o.weave && o.fabricRgb) weavePattern(ctx, cw, ch, o.fabricRgb, pxPerMm);
  if (hooped) {
    // t.ox/t.oy run through the SAME TX/TY used for strands below, so the
    // outline is always drawn at the current view's scale/position -- one
    // shared transform, not a second parallel calculation (B4).
    const viewedT = { scale: pxPerMm, ox: TX(0), oy: TY(0), hoopWmm: t.hoopWmm, hoopHmm: t.hoopHmm };
    drawHoopOutline(ctx, viewedT, o.fabricRgb);
  }

  // Strand coordinates come straight from design.stitches, i.e. DST units
  // (0.1mm each). fitTransform's scale already absorbs that (it's computed
  // from the same raw units), so the design-fit path can feed them to TX/TY
  // untouched. hoopTransform's scale is px-per-mm though, so in hoop mode we
  // must convert DST units -> mm (/10) before applying it.
  const SX = hooped ? (x) => TX(x / 10) : TX;
  const SY = hooped ? (y) => TY(y / 10) : TY;

  let strands = designToStrands(design, { colorOverride: o.colorOverride });
  // Simulator support: draw only the first `limitStrands` segments (sew
  // order IS strand order — designToStrands walks design.stitches start to
  // finish), so scrubbing/playing renders the design exactly as the machine
  // would sew it. undefined/null = draw everything (every existing caller).
  if (o.limitStrands != null) strands = strands.slice(0, Math.max(0, o.limitStrands));
  const lw = Math.max(1.5, THREAD_MM * pxPerMm); // thread thickness in px
  ctx.lineCap = "round";
  // FLAT view (`threadStyle: "flat"`): the same filament footprint with the
  // lighting taken away — one solid stroke per strand, still in sew order and
  // still at THREAD_MM, so coverage reads identically in both views.
  //
  // It is not a cheaper approximation of the lit view but a different
  // question. With the shading gone, coverage and stitch structure read as
  // flat areas of colour, which is what you want while judging whether a shape
  // is actually FILLED; the lit view is what you want for how it will look
  // sewn. Ember ships the same toggle. Keeping the WIDTH identical between the
  // two is the part that matters: if they disagreed on width they would
  // disagree on coverage, and the flat view exists to answer coverage.
  if (o.threadStyle === "flat") {
    for (const s of strands) {
      ctx.strokeStyle = `rgb(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]})`;
      ctx.lineWidth = lw;
      ctx.beginPath();
      ctx.moveTo(SX(s.x0), SY(s.y0));
      ctx.lineTo(SX(s.x1), SY(s.y1));
      ctx.stroke();
    }
  } else {
    // One lit filament per strand, in sew order, so a later stitch's shadow
    // falls ON an earlier stitch the way it physically does. This used to be
    // three GLOBAL passes -- every shadow, then every colour, then every
    // sheen -- which put an early stitch's highlight on top of a late
    // stitch's body, and gave every strand the same fixed 1px/1.5px offset
    // regardless of zoom or of which way the stitch ran.
    for (const s of strands) drawFilament(ctx, SX(s.x0), SY(s.y0), SX(s.x1), SY(s.y1), s.rgb, lw);
  }

  // Diagnostic overlays (drawn ON TOP of thread so they're never buried):
  // showJumps -> dashed travel lines; showTrims -> an X marker per trim.
  if (o.showJumps || o.showTrims) {
    const marks = jumpTrimMarks(design);
    ctx.save();
    if (o.showJumps) {
      ctx.strokeStyle = "rgba(37,99,235,0.8)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      for (const j of marks.jumps) {
        ctx.beginPath();
        ctx.moveTo(SX(j.x0), SY(j.y0));
        ctx.lineTo(SX(j.x1), SY(j.y1));
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    if (o.showTrims) {
      ctx.strokeStyle = "rgba(220,38,38,0.9)";
      ctx.lineWidth = 1.5;
      const r = 4;
      for (const t of marks.trims) {
        const cx2 = SX(t.x), cy2 = SY(t.y);
        ctx.beginPath();
        ctx.moveTo(cx2 - r, cy2 - r);
        ctx.lineTo(cx2 + r, cy2 + r);
        ctx.moveTo(cx2 - r, cy2 + r);
        ctx.lineTo(cx2 + r, cy2 - r);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

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
    // POST-VIEW contract (B1): toCanvas already bakes in pan; scale already
    // has view.zoom multiplied in (pxPerMm === t.scale * zoom for the hoop
    // path) -- interact.js's px<->mm math (designRectPx/hitTest/dragResize/
    // dragMove/clampOffsets) consumes this as-is, with ZERO changes needed.
    toCanvas: (xMm, yMm) => ({ x: TX(xMm), y: TY(yMm) }),
    scale: pxPerMm,
    designBBoxMm,
  };
}
