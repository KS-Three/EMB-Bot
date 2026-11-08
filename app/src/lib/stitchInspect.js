// The field's stitch inspector (2026-11-08): hover a stitch, read what it is.
//
// While the Inspect toggle is on, the field names the stitch nearest the
// pointer (within INSPECT_RADIUS_MM): its number in sew order, what kind of
// stitch it is, the thread, its length, and the colour block it sews in.
//
// Every number here is read the way the simulator reads it, so the two can
// never disagree on one screen:
//
//   - A "stitch" is a STRAND, the segment designToStrands draws INTO a needle
//     penetration (lib/strands.js). That is the thing the pointer is over.
//   - Its number is strandStitchOrdinals' entry for that strand, which is
//     what SimBar's counter shows once that strand is drawn: with `idx`
//     strands on screen the counter reads ordinals[idx - 1], so strand j
//     reads ordinals[j]. The total is the counter's total, the last entry.
//   - Its block is simulate.js blockAt(tl, j + 1), the block the simulator
//     names with strand j just drawn ("Thread K of B").
//
// The lookup is a uniform grid over the design, built once per generation:
// each strand is listed in every cell its bounding box touches, so a query
// reads the few cells under a 2r x 2r box and measures only the strands in
// them. A machine stitch is at most 12.1 mm (the DST record limit), so no
// strand spans more than a handful of cells. Nothing here touches a canvas.
import { designToStrands, strandStitchOrdinals } from "./strands.js";
import { simTimeline, blockAt } from "./simulate.js";

export const INSPECT_RADIUS_MM = 1.5;
// Cell edge, mm. Equal to the radius: a query reads a 3 x 3 block of cells
// (4 x 4 when the pointer is not centred in one), each holding the strands
// that pass near it. Smaller cells list a long satin cross in more of them;
// larger ones hand the query more strands to measure.
export const INSPECT_CELL_MM = 1.5;

// What each run-span `kind` is called in the tooltip (strands.js "Run spans").
// `fill` is the engine's tatami; a strand with no span (an imported file, the
// lettering lane) is plainly a stitch.
const KIND_LABEL = {
  satin: "Satin",
  fill: "Tatami",
  run: "Run",
  bean: "Bean",
  underlay: "Underlay",
  tie: "Tie",
  travel: "Travel",
  stitch: "Stitch",
};
const ROLE_LABEL = { border: "border", edge_cap: "edge cap" };

export function kindLabel(kind, role) {
  const base = KIND_LABEL[kind] || "Stitch";
  const r = ROLE_LABEL[role];
  return r ? `${base} (${r})` : base;
}

// Build the index for one design (field mm, +y up: generate.js `combined`).
// Returns null for a design with nothing drawn.
export function buildStitchIndex(design, opts) {
  const cell = (opts && opts.cellMm) || INSPECT_CELL_MM;
  const strands = designToStrands(design || { stitches: [], colors: [] });
  const n = strands.length;
  if (!n) return null;
  const ordinals = strandStitchOrdinals(design);
  const tl = simTimeline(design);
  // Segment ends in one flat array; the walk below reads nothing else.
  const seg = new Float64Array(n * 4);
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let j = 0; j < n; j++) {
    const s = strands[j];
    seg[j * 4] = s.x0; seg[j * 4 + 1] = s.y0; seg[j * 4 + 2] = s.x1; seg[j * 4 + 3] = s.y1;
    if (s.x0 < minX) minX = s.x0; if (s.x1 < minX) minX = s.x1;
    if (s.y0 < minY) minY = s.y0; if (s.y1 < minY) minY = s.y1;
    if (s.x0 > maxX) maxX = s.x0; if (s.x1 > maxX) maxX = s.x1;
    if (s.y0 > maxY) maxY = s.y0; if (s.y1 > maxY) maxY = s.y1;
  }
  const nx = Math.max(1, Math.floor((maxX - minX) / cell) + 1);
  const ny = Math.max(1, Math.floor((maxY - minY) / cell) + 1);
  const cx = (x) => Math.min(nx - 1, Math.max(0, Math.floor((x - minX) / cell)));
  const cy = (y) => Math.min(ny - 1, Math.max(0, Math.floor((y - minY) / cell)));
  // Two passes, compressed rows: count per cell, prefix-sum, then fill. One
  // Int32Array of strand ids, no per-cell arrays.
  const start = new Int32Array(nx * ny + 1);
  for (let j = 0; j < n; j++) {
    const o = j * 4;
    const i0 = cx(Math.min(seg[o], seg[o + 2])), i1 = cx(Math.max(seg[o], seg[o + 2]));
    const k0 = cy(Math.min(seg[o + 1], seg[o + 3])), k1 = cy(Math.max(seg[o + 1], seg[o + 3]));
    for (let k = k0; k <= k1; k++) for (let i = i0; i <= i1; i++) start[k * nx + i + 1]++;
  }
  for (let c = 0; c < nx * ny; c++) start[c + 1] += start[c];
  const fillAt = start.slice(0, nx * ny);
  const ids = new Int32Array(start[nx * ny]);
  for (let j = 0; j < n; j++) {
    const o = j * 4;
    const i0 = cx(Math.min(seg[o], seg[o + 2])), i1 = cx(Math.max(seg[o], seg[o + 2]));
    const k0 = cy(Math.min(seg[o + 1], seg[o + 3])), k1 = cy(Math.max(seg[o + 1], seg[o + 3]));
    for (let k = k0; k <= k1; k++) for (let i = i0; i <= i1; i++) ids[fillAt[k * nx + i]++] = j;
  }
  return { design, strands, ordinals, tl, seg, cell, minX, minY, nx, ny, start, ids, n };
}

// Squared distance from (px, py) to segment o of `seg`.
function dist2(seg, o, px, py) {
  const x0 = seg[o], y0 = seg[o + 1], dx = seg[o + 2] - x0, dy = seg[o + 3] - y0;
  const len2 = dx * dx + dy * dy;
  let t = len2 > 0 ? ((px - x0) * dx + (py - y0) * dy) / len2 : 0;
  if (t < 0) t = 0; else if (t > 1) t = 1;
  const ex = x0 + t * dx - px, ey = y0 + t * dy - py;
  return ex * ex + ey * ey;
}

// The strand nearest (xMm, yMm) within `radiusMm`, or -1. On a tie the LATER
// strand wins: it was sewn on top, so it is the one the pointer is over.
export function nearestStrand(ix, xMm, yMm, radiusMm = INSPECT_RADIUS_MM) {
  if (!ix || !Number.isFinite(xMm) || !Number.isFinite(yMm)) return -1;
  const r = radiusMm;
  const { cell, minX, minY, nx, ny, start, ids, seg } = ix;
  const i0 = Math.floor((xMm - r - minX) / cell), i1 = Math.floor((xMm + r - minX) / cell);
  const k0 = Math.floor((yMm - r - minY) / cell), k1 = Math.floor((yMm + r - minY) / cell);
  if (i1 < 0 || k1 < 0 || i0 >= nx || k0 >= ny) return -1;
  let best = -1, bestD = r * r;
  for (let k = Math.max(0, k0); k <= Math.min(ny - 1, k1); k++) {
    for (let i = Math.max(0, i0); i <= Math.min(nx - 1, i1); i++) {
      const c = k * nx + i;
      for (let p = start[c]; p < start[c + 1]; p++) {
        const j = ids[p];
        const d = dist2(seg, j * 4, xMm, yMm);
        if (d < bestD || (d === bestD && j > best)) { bestD = d; best = j; }
      }
    }
  }
  return best;
}

// What the tooltip says about strand j. `names` is the thread label per block
// (simulate.js blockThreadNames, the simulator's own list), optional.
export function strandInfo(ix, j, names) {
  if (!ix || !(j >= 0 && j < ix.n)) return null;
  const s = ix.strands[j];
  const tl = ix.tl;
  const k = blockAt(tl, j + 1);
  const block = tl.blocks[k] || null;
  const o = j * 4;
  return {
    strand: j,
    ordinal: ix.ordinals[j] || 0,
    total: ix.ordinals[ix.ordinals.length - 1] || 0,
    kind: s.kind || "stitch",
    role: s.role || "",
    label: kindLabel(s.kind || "stitch", s.role || ""),
    rgb: s.rgb,
    block: k + 1,
    blocks: tl.blocks.length,
    thread: (names && names[k]) || (block && block.color && block.color.name) || "",
    lengthMm: Math.hypot(ix.seg[o + 2] - ix.seg[o], ix.seg[o + 3] - ix.seg[o + 1]),
  };
}

export function inspectAt(ix, xMm, yMm, names, radiusMm = INSPECT_RADIUS_MM) {
  return strandInfo(ix, nearestStrand(ix, xMm, yMm, radiusMm), names);
}

// Canvas drawing px -> field mm, by inverting `toCanvas` (preview.js's
// mm -> px, view included). Read off three probes rather than re-derived, so
// the y flip and the view's pan and zoom come from the one place that owns
// them, as EmbroideryField's pxToMmDelta does. Null when it cannot invert.
export function canvasPxToMm(toCanvas, px, py) {
  if (typeof toCanvas !== "function") return null;
  const o = toCanvas(0, 0), ex = toCanvas(1, 0), ey = toCanvas(0, 1);
  const a = ex.x - o.x, b = ey.x - o.x, c = ex.y - o.y, d = ey.y - o.y;
  const det = a * d - b * c;
  if (!(Math.abs(det) > 1e-12)) return null;
  const qx = px - o.x, qy = py - o.y;
  return { x: (d * qx - b * qy) / det, y: (a * qy - c * qx) / det };
}
