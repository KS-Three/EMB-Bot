// The design-silhouette cap, as a set of things the customer can click.
//
// The service sews the cap (digitizer_core/stage7_sequence.py) as one run per
// stretch of edge, each in the thread of the shape beside it, and stamps every
// run with a `cap:<x>:<y>` id in `design.runs[].piece`. This module turns those
// spans into what the field needs to treat a stretch like a recognised shape:
// an open polyline to outline and hit-test, and a row for the popover.
//
// A piece is edited through the SAME two fields a shape is — its id in
// `deletedShapeIds`, or a `thread_index` in `shapeOverrides[id]` — and the
// service reads both back (`_cap_follow_pieces`), so nothing else here has to
// persist anything.
import { displayResult } from "./digitizer.js";

export const CAP_PREFIX = "cap:";

export function isCapPieceId(id) {
  return typeof id === "string" && id.startsWith(CAP_PREFIX);
}

// A run that lays thread of the cap (not the needle crossing to it).
const NON_SEWING = new Set(["travel", "tie"]);

// -> [{ id, block, i0, i1 }] in sew order, from the design the canvas draws
// (so a deletion that is still waiting on its restitch is already gone).
export function capPieceSpans(design) {
  const runs = design && design.runs;
  if (!Array.isArray(runs)) return [];
  const out = [];
  for (const r of runs) {
    if (!r || r.role !== "edge_cap" || !isCapPieceId(r.piece)) continue;
    if (NON_SEWING.has(String(r.kind || "").toLowerCase())) continue;
    out.push({ id: r.piece, block: r.block, i0: r.i0, i1: r.i1 });
  }
  return out;
}

// The stretch's thread colour: what the service sewed it in, as [r, g, b].
export function capPieceRgb(element, pieceId) {
  const design = displayResult(element);
  const span = capPieceSpans(design).find((s) => s.id === pieceId);
  const c = span && design.colors && design.colors[span.block];
  return c ? [c.r, c.g, c.b] : null;
}

// Open polylines in FIELD mm (+y up), one per piece, read off the BUILT design
// the field draws — the same stitch array the spans index, so rotation, scale
// and offset are already in it. Stitch units are 0.1 mm.
export function capOutlinesMm(element, built) {
  const spans = capPieceSpans(displayResult(element));
  const st = built && built.stitches;
  if (!spans.length || !Array.isArray(st)) return [];
  const out = [];
  for (const s of spans) {
    const pts = [];
    for (let i = s.i0; i <= s.i1 && i < st.length; i++) {
      if (st[i] && st[i].type === "stitch") pts.push([st[i].x / 10, st[i].y / 10]);
    }
    if (pts.length >= 2) out.push({ id: s.id, points: pts, open: true });
  }
  return out;
}

// The popover's view of one piece (see shapePopover.popoverModel).
export function capPieceRow(element, pieceId) {
  const entry = (element.shapeOverrides || {})[pieceId] || {};
  const rgb = Array.isArray(entry.rgb) ? entry.rgb : capPieceRgb(element, pieceId);
  return rgb ? { id: pieceId, rgb } : null;
}
