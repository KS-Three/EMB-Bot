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

import { countAt, travelAt } from "./simulate.js";

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

// o: { strands, timeline, idx, toCanvas, showJumps, rgb }
//   rgb — the thread on the needle, for the marker's core.
export function drawSimOverlay(ctx, o) {
  if (!ctx || !o || !o.toCanvas || !o.timeline) return;
  const { strands, timeline: tl, idx, toCanvas } = o;
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
