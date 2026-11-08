// Per-colour-block thumbnails for the Design panel (an imported .dst's block
// list): one small realistic picture per block showing ONLY that block's
// stitches, over a faint silhouette of the whole design so the eye can see
// where the block sits. The point is the thread picker -- "Block 3" tells a
// customer nothing, while a picture of the lettering sewn in that block does.
//
// Nothing here is a second renderer. Strands come from strands.js's
// designToStrands (one call per block, on that block's slice of the stitch
// stream) and are drawn by preview.js's drawThreads, both unchanged, so a
// thumbnail's thread looks like the canvas's thread.
//
// DST units are 0.1 mm and +y points UP (fitTransform's convention); the
// canvas flips it below.

import { designToStrands } from "./strands.js";
import { drawThreads, threadLodLayers, THREAD_WIDTH_MM, isDark } from "./preview.js";

// Ink never leaves the block's own bounding box by more than this. A round
// thread cap at thumbnail scale is wider than 1 mm, so without the clip a
// block's strokes bled over its neighbours' territory and the picture lied
// about where the block is.
export const BBOX_MARGIN_MM = 1;
const UNITS_PER_MM = 10;
// Dedupe grid for thinStrands, in CSS px (x dpr = backing px).
const THIN_PX = 0.75;

// Split the stitch stream at colour records. Block i is everything between
// colour record i and i+1; a stitch record is the only thing that counts
// toward the count and the bbox (jump/trim positions are travel, not ink --
// the same rule dstimport.js's centring uses).
export function splitBlocks(design) {
  const blocks = [];
  let cur = { stitches: [], count: 0, bbox: null };
  const push = () => { blocks.push(cur); cur = { stitches: [], count: 0, bbox: null }; };
  for (const st of (design && design.stitches) || []) {
    if (st.type === "color") { push(); continue; }
    cur.stitches.push(st);
    if (st.type !== "stitch") continue;
    cur.count++;
    const b = cur.bbox;
    if (!b) cur.bbox = { x0: st.x, y0: st.y, x1: st.x, y1: st.y };
    else {
      if (st.x < b.x0) b.x0 = st.x; if (st.x > b.x1) b.x1 = st.x;
      if (st.y < b.y0) b.y0 = st.y; if (st.y > b.y1) b.y1 = st.y;
    }
  }
  push();
  // A trailing colour record (or an "end" at the tail) leaves an empty block
  // the panel never lists; colorCount counts color records + 1, so the empty
  // tail is kept when the panel would list it and dropped by the caller's
  // length. Here: keep everything, index stays aligned with the panel's.
  return blocks;
}

// The whole design's extent over stitch records, in DST units.
function designExtent(blocks) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const b of blocks) {
    if (!b.bbox) continue;
    if (b.bbox.x0 < x0) x0 = b.bbox.x0; if (b.bbox.x1 > x1) x1 = b.bbox.x1;
    if (b.bbox.y0 < y0) y0 = b.bbox.y0; if (b.bbox.y1 > y1) y1 = b.bbox.y1;
  }
  return x0 === Infinity ? null : { x0, y0, x1, y1 };
}

function rgbOf(c) {
  if (!c) return [20, 20, 20];
  if (Array.isArray(c)) return [c[0], c[1], c[2]];
  return [c.r, c.g, c.b];
}

function defaultMakeCanvas(w, h) {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  return c;
}

// A thumbnail is ~1 px per mm, and a fill row is 0.15 mm from the next, so
// ~7 neighbouring rows land on the same pixels: stroking every one is the
// whole cost (measured 12 ms per 1,000 stitches, honest, with the canvas
// flushed) and none of it is visible. Strands that quantise to the same
// (start, end) pair on a grid of `q` backing px are drawn once, in their
// first position (sew order, and so z-order, is kept).
export function thinStrands(strands, SX, SY, q) {
  const seen = new Set();
  const out = [];
  const inv = 1 / q;
  for (const st of strands) {
    let a = Math.round(SX(st.x0) * inv) + 64, b = Math.round(SY(st.y0) * inv) + 64;
    let c = Math.round(SX(st.x1) * inv) + 64, d = Math.round(SY(st.y1) * inv) + 64;
    if (a > c || (a === c && b > d)) { const ta = a, tb = b; a = c; b = d; c = ta; d = tb; }
    const key = ((a * 1024 + b) * 1024 + c) * 1024 + d;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(st);
  }
  return out;
}

// buildBlockThumbs(design, opts) -> [{ index, count, canvas, bboxMm }]
//
//   design    { stitches } as decodeDST returns it (colour records split the
//             blocks). Its own `colors`, if any, are ignored: the panel owns
//             each block's thread.
//   opts.colors      [rgb] per block -- the panel's blockRgb(element, i).
//   opts.width/height  CSS px of each thumbnail (default 64 x 32).
//   opts.dpr         backing-store scale (default 2).
//   opts.makeCanvas  (w, h) -> canvas; defaults to document.createElement.
//   opts.silhouette  false -> skip the faint whole-design silhouette.
//   opts.background  false -> leave the canvas transparent where nothing is
//                    drawn (the done-test reads ink alone with both off).
//
// An empty block (no stitch records) yields a thumbnail with count 0 and no
// ink; a canvas that cannot give a 2d context (jsdom) yields canvas: null.
export function buildBlockThumbs(design, opts) {
  const o = opts || {};
  const W = o.width || 64, H = o.height || 32, dpr = o.dpr || 2;
  const make = o.makeCanvas || defaultMakeCanvas;
  const blocks = splitBlocks(design);
  const ext = designExtent(blocks);
  const bw = Math.round(W * dpr), bh = Math.round(H * dpr);

  // One fit for every thumbnail, so they share a scale and the same block
  // lands in the same place in each picture.
  const pad = 3 * dpr;
  const ew = ext ? Math.max(1, ext.x1 - ext.x0) : 1, eh = ext ? Math.max(1, ext.y1 - ext.y0) : 1;
  const s = ext ? Math.min((bw - 2 * pad) / ew, (bh - 2 * pad) / eh) : 1; // px per DST unit
  const cx = ext ? (ext.x0 + ext.x1) / 2 : 0, cy = ext ? (ext.y0 + ext.y1) / 2 : 0;
  const SX = (x) => bw / 2 + (x - cx) * s;
  const SY = (y) => bh / 2 - (y - cy) * s; // DST y-up -> canvas y-down
  const pxPerMm = s * UNITS_PER_MM;
  const lw = Math.max(1.2 * dpr, THREAD_WIDTH_MM * pxPerMm);

  const out = [];
  // Strands first (pure): one designToStrands pass per block's slice of the
  // stitch stream, so the cost is one pass over the stream in total.
  const perBlock = blocks.map((b, i) => {
    const rgb = rgbOf((o.colors || [])[i]);
    return designToStrands({ stitches: b.stitches, colors: [{ r: rgb[0], g: rgb[1], b: rgb[2] }] });
  });

  // Pass 1: each block's own layer, on a transparent canvas. This is the only
  // place a stitch is drawn. (The silhouette is NOT stroked from the whole
  // design: that was measured 5x dearer than every block layer together --
  // 63 of 74 ms on a 15k-stitch file -- because one path of 30k overlapping
  // round-capped strokes is what the rasterizer is worst at. It is the union
  // of these layers instead, which costs a few blits.)
  const layers = blocks.map((b, i) => {
    const canvas = make(bw, bh);
    const ctx = canvas && canvas.getContext && canvas.getContext("2d");
    const entry = { index: i, count: b.count, canvas: ctx ? canvas : null, bboxMm: null };
    if (b.bbox) entry.bboxMm = { x0: b.bbox.x0 / UNITS_PER_MM, y0: b.bbox.y0 / UNITS_PER_MM, x1: b.bbox.x1 / UNITS_PER_MM, y1: b.bbox.y1 / UNITS_PER_MM };
    out.push(entry);
    const strands = o.thin === 0 ? perBlock[i] : thinStrands(perBlock[i], SX, SY, o.thin || THIN_PX * dpr);
    if (!ctx || !strands.length || !b.bbox) return entry;
    ctx.save();
    // Clip to the block's bbox + 1 mm (see BBOX_MARGIN_MM).
    const m = BBOX_MARGIN_MM * UNITS_PER_MM;
    const rx0 = SX(b.bbox.x0 - m), rx1 = SX(b.bbox.x1 + m);
    const ry0 = SY(b.bbox.y1 + m), ry1 = SY(b.bbox.y0 - m);
    ctx.beginPath();
    ctx.rect(rx0, ry0, rx1 - rx0, ry1 - ry0);
    ctx.clip();
    drawThreads(ctx, strands, SX, SY, lw, {
      layers: threadLodLayers(lw / dpr, strands.length),
      clip: { x0: 0, y0: 0, x1: bw, y1: bh },
      ...(o.draw || {}),
    });
    ctx.restore();
    return entry;
  });

  const bare = o.silhouette === false && o.background === false;
  if (bare || !ext) return out;

  // Pass 2: the silhouette (union of the layers, flattened to one grey), then
  // each final thumbnail = tile, faint silhouette, its own layer on top.
  let sil = null;
  if (o.silhouette !== false) {
    const c = make(bw, bh);
    const g = c && c.getContext && c.getContext("2d");
    if (g) {
      for (const L of layers) if (L.canvas && L.count) g.drawImage(L.canvas, 0, 0);
      g.globalCompositeOperation = "source-in";
      g.fillStyle = "rgb(128,128,128)";
      g.fillRect(0, 0, bw, bh);
      sil = c;
    }
  }
  return layers.map((L, i) => {
    if (!L.canvas) return L;
    const canvas = make(bw, bh);
    const ctx = canvas && canvas.getContext && canvas.getContext("2d");
    if (!ctx) return L;
    if (o.background !== false) {
      // A pale thread on a pale tile is invisible, so the tile goes dark for
      // it: the tile is a viewing surface for the thread, not the fabric.
      ctx.fillStyle = isDark(rgbOf((o.colors || [])[i])) ? "#e9e6df" : "#4a4a4a";
      ctx.fillRect(0, 0, bw, bh);
    }
    if (sil) {
      ctx.save();
      ctx.globalAlpha = 0.16;
      ctx.drawImage(sil, 0, 0);
      ctx.restore();
    }
    if (L.count) ctx.drawImage(L.canvas, 0, 0);
    return { ...L, canvas };
  });
}

// Stitch count per block without building anything: the row label shows it at
// once, before (and whether or not) any thumbnail is drawn.
export function blockStitchCounts(design) {
  const counts = [0];
  for (const st of (design && design.stitches) || []) {
    if (st.type === "color") counts.push(0);
    else if (st.type === "stitch") counts[counts.length - 1]++;
  }
  return counts;
}
