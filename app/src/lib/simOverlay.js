// simOverlay.js — what the simulator draws ON TOP of the sewn-so-far thread:
// the needle, the travel in flight, and the trims (and, with the Jumps toggle
// on, the travel) that have HAPPENED. The thread itself is preview.js's
// (renderRealistic with `limitStrands`); this file never draws thread, so
// the two can change independently.
//
// Everything here is O(events so far) per frame at worst and O(1) for the
// needle — no walk of the stitches. The timeline (lib/simulate.js
// simTimeline) is built once when the simulator opens.
//
// Coordinates: strands and timeline events are in DST units (0.1 mm);
// `toCanvas` is renderRealistic's post-view mm -> CSS-px transform, so the
// overlay lands on the thread at any zoom or pan. The context arrives with
// renderRealistic's dpr transform still applied, so CSS px are what we draw in.

import { countAt, travelAt, pendingUnderlay } from "./simulate.js";
// Imported, never edited here: preview.js belongs to the appearance work.
// Isolate redraws the thread on the needle through its own drawThreads so
// the redrawn thread is the same picture, not a second renderer.
import { drawThreads, threadLodLayers, THREAD_WIDTH_MM } from "./preview.js";
import { shrinkSatinStrands } from "./strands.js";

// The same blue and red the field's Jumps/Trims overlays use (preview.js),
// so a mark means the same thing in both views.
const TRAVEL_RGB = "37,99,235";
const TRIM_RGB = "220,38,38";

// Where the needle is with `idx` strands drawn: the end of the last one, or
// the start of the first before anything is sewn. null for no strands.
export function needleAt(strands, idx) {
  if (!strands || !strands.length) return null;
  if (idx <= 0) return { x: strands[0].x0, y: strands[0].y0 };
  const s = strands[Math.min(idx, strands.length) - 1];
  return { x: s.x1, y: s.y1 };
}

function pt(toCanvas, x, y) {
  return toCanvas(x / 10, y / 10);
}

function trimMark(ctx, p, r) {
  ctx.moveTo(p.x - r, p.y - r);
  ctx.lineTo(p.x + r, p.y + r);
  ctx.moveTo(p.x - r, p.y + r);
  ctx.lineTo(p.x + r, p.y - r);
}

// The drawn thread width in CSS px at `pxPerMm`: renderRealistic's own rule
// (THREAD_WIDTH_MM with a 1.2 px floor), so a mark sits on the thread.
export function threadPx(pxPerMm) {
  return Math.max(1.2, THREAD_WIDTH_MM * (pxPerMm > 0 ? pxPerMm : 0));
}

// renderRealistic's strand transform, recovered from its post-view toCanvas
// (mm -> CSS px; separable and affine: zoom, pan, y-flip) as the SX/SY pair
// drawThreads takes, in DST units (0.1 mm).
export function strandTransform(toCanvas) {
  const o = toCanvas(0, 0), ux = toCanvas(1, 0), uy = toCanvas(0, 1);
  const ax = o.x, bx = ux.x - o.x, ay = o.y, by = uy.y - o.y;
  return { SX: (x) => ax + bx * (x / 10), SY: (y) => ay + by * (y / 10) };
}

function tint(rgb, f) {
  return "rgb(" + Math.round(rgb[0] + (255 - rgb[0]) * f) + "," + Math.round(rgb[1] + (255 - rgb[1]) * f) + "," + Math.round(rgb[2] + (255 - rgb[2]) * f) + ")";
}

// Underlay that is sewn and not yet covered (lib/simulate.js underlayRuns and
// pendingUnderlay), drawn LIGHTER and THINNER over what renderRealistic laid
// for it: a pale casing the width of the underlay's own stroke, with a thin
// core of the true thread colour. It reads as the layer beneath, not as an
// open version of the top stitching. Only pending runs are marked: once the
// top begins, the underlay is renderRealistic's again, drawn under it.
// O(pending underlay strands), which is one shape's underlay in practice.
// Returns how many strands it marked.
export function drawPendingUnderlay(ctx, o) {
  if (!ctx || !o || !o.underlay || !o.toCanvas || !o.strands) return 0;
  const runs = pendingUnderlay(o.underlay, o.idx);
  if (!runs.length) return 0;
  const { SX, SY } = strandTransform(o.toCanvas);
  const lw = o.lw > 0 ? o.lw : 1.2;
  // preview.js draws underlay at 0.66 of the thread (kindStyle), floored at
  // 0.6 px; the casing covers that and its anti-aliased edge.
  const casing = Math.max(0.6, lw * 0.66) + 0.75;
  const core = Math.max(0.5, lw * 0.28);
  let n = 0;
  ctx.save();
  ctx.setLineDash([]);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const [w, f] of [[casing, 0.62], [core, 0]]) {
    ctx.lineWidth = w;
    for (const r of runs) {
      ctx.strokeStyle = tint(r.rgb, f);
      ctx.beginPath();
      for (let i = r.start; i < r.end; i++) {
        const s = o.strands[i];
        ctx.moveTo(SX(s.x0), SY(s.y0));
        ctx.lineTo(SX(s.x1), SY(s.y1));
      }
      ctx.stroke();
      if (f) n += r.end - r.start;
    }
  }
  ctx.restore();
  return n;
}

// Isolate: everything sewn so far is dimmed toward the cloth, then the thread
// on the needle is drawn again on top at full strength, through preview.js's
// own drawThreads with renderRealistic's width, level of detail, sewn-width
// pull and view style, so it looks as it did before the wash. Only the
// CURRENT block's strands are redrawn, and they are the last thing sewn, so
// nothing they cover can be lost.
//   o: { strands, idx, from, toCanvas, lw, flat, sewnPullMm, wash, bboxMm, cw, ch }
//   from: the current block's first strand.
//   wash: the CSS colour the thread sits on (the field's work bed), laid at
//     ISOLATE_WASH over the design's box (bboxMm, renderRealistic's
//     designBBoxMm) and 2 mm round it, so the dark surround and the hoop
//     ring outside it keep their colour. No box: the whole canvas.
export const ISOLATE_WASH = 0.72;
export function drawIsolate(ctx, o) {
  if (!ctx || !o || !o.toCanvas || !o.strands) return 0;
  const cw = o.cw || 0, ch = o.ch || 0;
  ctx.save();
  ctx.setLineDash([]);
  ctx.globalAlpha = ISOLATE_WASH;
  ctx.fillStyle = o.wash || "#7b8190";
  const b = o.bboxMm;
  if (b) {
    const p = o.toCanvas(b.x0 - 2, b.y0 - 2), q = o.toCanvas(b.x1 + 2, b.y1 + 2);
    ctx.fillRect(Math.min(p.x, q.x), Math.min(p.y, q.y), Math.abs(q.x - p.x), Math.abs(q.y - p.y));
  } else {
    ctx.fillRect(0, 0, cw, ch);
  }
  ctx.restore();
  const from = Math.max(0, o.from | 0), to = Math.min(o.strands.length, o.idx | 0);
  if (to <= from) return 0;
  let mine = o.strands.slice(from, to);
  if (o.sewnPullMm > 0) mine = shrinkSatinStrands(mine, o.sewnPullMm);
  const { SX, SY } = strandTransform(o.toCanvas);
  const lw = o.lw > 0 ? o.lw : 1.2;
  ctx.save();
  // The level of detail is the whole prefix's, as renderRealistic chose it,
  // so the redrawn thread carries the same layers as the dimmed copy.
  drawThreads(ctx, mine, SX, SY, lw, { layers: threadLodLayers(lw, to), flat: !!o.flat, clip: { x0: 0, y0: 0, x1: cw, y1: ch } });
  ctx.restore();
  return to - from;
}

// o: { strands, timeline, idx, toCanvas, showJumps, rgb, underlay, lw }
//   rgb: the thread on the needle, for the marker's core.
//   underlay: underlayRuns(strands, timeline); omitted, none is marked.
//   lw: threadPx(renderResult.scale), the drawn thread width.
export function drawSimOverlay(ctx, o) {
  if (!ctx || !o || !o.toCanvas || !o.timeline) return;
  const { strands, timeline: tl, idx, toCanvas } = o;
  if (o.underlay) drawPendingUnderlay(ctx, o);
  ctx.save();
  ctx.setLineDash([]);

  // Travel that has happened (Jumps toggle on): faint, so the sewn thread
  // still reads through it. Only the past — the field's own Jumps overlay
  // draws the whole design, which during playback showed the future.
  const nTravel = countAt(tl.travels, idx);
  if (o.showJumps && nTravel) {
    ctx.strokeStyle = `rgba(${TRAVEL_RGB},0.45)`;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    for (let i = 0; i < nTravel; i++) {
      const t = tl.travels[i];
      if (t.x0 === t.x1 && t.y0 === t.y1) continue;
      const a = pt(toCanvas, t.x0, t.y0), b = pt(toCanvas, t.x1, t.y1);
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // The travel in flight: the frame's last move with the needle up, kept
  // while the needle sews the run it led into. Always on — it is the one
  // piece of travel that says where the needle just came from.
  const tr = travelAt(tl, idx);
  if (tr && idx < tl.total) {
    const a = pt(toCanvas, tr.x0, tr.y0), b = pt(toCanvas, tr.x1, tr.y1);
    ctx.strokeStyle = `rgba(${TRAVEL_RGB},0.7)`;
    ctx.lineWidth = 1.25;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Trims, as they happen. Always on in the simulator: a trim is an event the
  // operator hears, not clutter.
  const nTrim = countAt(tl.trims, idx);
  if (nTrim) {
    ctx.strokeStyle = `rgba(${TRIM_RGB},0.9)`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < nTrim; i++) trimMark(ctx, pt(toCanvas, tl.trims[i].x, tl.trims[i].y), 3.5);
    ctx.stroke();
  }

  // The needle: a ring with a crosshair, dark core on a white casing so it
  // reads on any fabric and any thread, centred on the last stitch sewn. Not
  // drawn once the design is finished — the machine has stopped.
  const p = idx < tl.total ? needleAt(strands, idx) : null;
  if (p) {
    const c = pt(toCanvas, p.x, p.y);
    const r = 7;
    ctx.lineCap = "round";
    for (const [w, col] of [[4, "rgba(255,255,255,0.95)"], [1.6, "rgba(17,17,17,0.95)"]]) {
      ctx.lineWidth = w;
      ctx.strokeStyle = col;
      ctx.beginPath();
      ctx.arc(c.x, c.y, r, 0, Math.PI * 2);
      ctx.moveTo(c.x - r - 4, c.y);
      ctx.lineTo(c.x - r + 3, c.y);
      ctx.moveTo(c.x + r - 3, c.y);
      ctx.lineTo(c.x + r + 4, c.y);
      ctx.moveTo(c.x, c.y - r - 4);
      ctx.lineTo(c.x, c.y - r + 3);
      ctx.moveTo(c.x, c.y + r - 3);
      ctx.lineTo(c.x, c.y + r + 4);
      ctx.stroke();
    }
    if (o.rgb) {
      ctx.fillStyle = `rgb(${o.rgb[0]},${o.rgb[1]},${o.rgb[2]})`;
      ctx.strokeStyle = "rgba(255,255,255,0.95)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(c.x, c.y, 2.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }
  ctx.restore();
}
