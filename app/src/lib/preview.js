import { designToStrands } from "./strands.js";
export function fitTransform(design, cw, ch, pad) {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const s of design.stitches) { if (s.type === "color" || s.type === "end") continue; if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x; if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y; }
  const w = Math.max(1, maxX - minX), h = Math.max(1, maxY - minY);
  const scale = Math.min((cw - 2 * pad) / w, (ch - 2 * pad) / h);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  return { scale, ox: cw / 2 - cx * scale, oy: ch / 2 - cy * scale };
}
export function renderRealistic(canvas, design, opts) {
  const o = opts || {};
  const ctx = canvas.getContext("2d");
  const cw = canvas.width, ch = canvas.height;
  ctx.fillStyle = o.fabric || "#e9e6df";
  ctx.fillRect(0, 0, cw, ch);
  const t = fitTransform(design, cw, ch, o.pad || 24);
  const TX = (x) => t.ox + x * t.scale, TY = (y) => t.oy + y * t.scale;
  const strands = designToStrands(design, { colorOverride: o.colorOverride });
  const lw = Math.max(1.5, 2.2 * t.scale); // thread thickness in px (DST units ~0.1mm)
  ctx.lineCap = "round";
  // shadow pass
  ctx.strokeStyle = "rgba(0,0,0,0.28)";
  ctx.lineWidth = lw;
  for (const s of strands) { ctx.beginPath(); ctx.moveTo(TX(s.x0) + 1, TY(s.y0) + 1.5); ctx.lineTo(TX(s.x1) + 1, TY(s.y1) + 1.5); ctx.stroke(); }
  // color pass
  ctx.lineWidth = lw;
  for (const s of strands) { ctx.strokeStyle = `rgb(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]})`; ctx.beginPath(); ctx.moveTo(TX(s.x0), TY(s.y0)); ctx.lineTo(TX(s.x1), TY(s.y1)); ctx.stroke(); }
  // highlight pass (sheen)
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = Math.max(0.6, lw * 0.35);
  for (const s of strands) { ctx.beginPath(); ctx.moveTo(TX(s.x0) - 0.6, TY(s.y0) - 0.9); ctx.lineTo(TX(s.x1) - 0.6, TY(s.y1) - 0.9); ctx.stroke(); }
}
