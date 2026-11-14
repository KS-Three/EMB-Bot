// Pen strokes for the manual lane's two open modes, Column and Line (spec
// docs/superpowers/specs/2026-11-13-pen-auto-branch-design.md, section 2).
//
// A drag on the side canvas is a stroke. This module turns the pointer samples
// of one into the record a click-drawn open shape already has, `points` plus
// `curves`, so nothing new is stored and every edit that works on a clicked
// Column or Line works on a drawn one. It also finds what a stroke's end snaps
// to, and remembers the width and colour the next stroke is born with.
//
// Every length here is in AUTHORED CANVAS PX (manualShapes' 600 x 400 canvas,
// 6 px to the nominal millimetre). They describe a hand on a screen, not
// thread on fabric, so none of them is a sewing constant.
//
// Pure: no DOM, no Svelte. ManualPanel owns the gesture.

import {
  MAX_SHAPE_POINTS, CLOSE_RADIUS_PX, COLUMN_DEFAULT_MM, CANVAS_W, CANVAS_H,
  flattenShape, flattenQuadraticSegment, isColumn, isRun, shapeProblems,
} from "./manualShapes.js";
import { simplifyRingAdaptive } from "./manualTrace.js";

// A press that stays inside this is a click and places a point, as it always
// has. Past it, the press is a stroke. The field's Move shape uses the same 4.
// THESE TWO are in SCREEN (CSS) px, unlike everything below: they are about
// how far a finger or a mouse slips, and the side canvas is drawn smaller than
// its 600 authored px, so in canvas px they would shrink with the panel. The
// panel converts (ManualPanel's `penPx`).
export const PEN_DEAD_ZONE_PX = 4;
// A stroke shorter than this is a click that slipped, not a line: it is handed
// back to the click path.
export const PEN_MIN_STROKE_PX = 12;
// The samples are re-spaced to this before anything else, so smoothing and
// corner finding see even steps whatever the pointer's report rate was.
export const PEN_RESAMPLE_PX = 2;
// Hand jitter is taken out with a Gaussian of this sigma along the stroke.
export const PEN_SMOOTH_SIGMA_PX = 4;
// A turn of at least this many degrees between the 8 px before a sample and
// the 8 px after it is a TIP the author drew (a leaf point, a V), and smoothing
// stops there instead of rounding it off. Deliberately not lower: measured on
// jittered strokes, a 2 mm-radius loop reads up to 68 degrees and a plain 90
// degree corner as little as 54, so no threshold separates those two. A soft
// corner is therefore smoothed like any bend (it rounds by about the sigma);
// only a turn no curve of sewable radius makes is kept sharp.
export const PEN_CORNER_WINDOW_PX = 8;
export const PEN_CORNER_MIN_TURN_DEG = 75;
// How far the fitted curve may sit from the smoothed stroke before its span is
// split in two, and the bulge under which a span is simply a straight segment.
// Chosen on measured fit error, see penStroke.spec.js ("fit error").
export const PEN_FIT_TOL_PX = 1.0;
export const PEN_STRAIGHT_TOL_PX = 0.5;
// A stroke's start or end within this of another stroke lands on it. The
// closing radius every other "near enough" on this canvas already uses.
export const PEN_SNAP_RADIUS_PX = CLOSE_RADIUS_PX;

const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

export function pastPenDeadZone(start, pt, deadZonePx = PEN_DEAD_ZONE_PX) {
  return !!start && !!pt && dist(start, pt) > deadZonePx;
}

export function pathLength(pts) {
  let len = 0;
  for (let i = 1; i < (pts || []).length; i++) len += dist(pts[i - 1], pts[i]);
  return len;
}

// The path re-spaced to `stepPx` along its length. First and last points are
// kept exactly; the last gap may be shorter than a step.
export function resamplePath(pts, stepPx = PEN_RESAMPLE_PX) {
  const src = pts || [];
  if (src.length < 2 || !(stepPx > 0)) return src.map((p) => ({ x: p.x, y: p.y }));
  const out = [{ x: src[0].x, y: src[0].y }];
  let carry = 0; // distance already walked toward the next emitted point
  for (let i = 1; i < src.length; i++) {
    const a = src[i - 1], b = src[i];
    const seg = dist(a, b);
    if (seg === 0) continue;
    let at = stepPx - carry;
    while (at <= seg) {
      const t = at / seg;
      out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
      at += stepPx;
    }
    carry = seg - (at - stepPx);
  }
  const last = src[src.length - 1], tail = out[out.length - 1];
  if (dist(last, tail) > 1e-6) out.push({ x: last.x, y: last.y });
  else out[out.length - 1] = { x: last.x, y: last.y };
  return out;
}

// Indices of the corners in an evenly spaced path: local maxima of the turn
// between the window behind a sample and the window ahead of it.
export function cornerIndices(pts, stepPx = PEN_RESAMPLE_PX, windowPx = PEN_CORNER_WINDOW_PX, minTurnDeg = PEN_CORNER_MIN_TURN_DEG) {
  const n = (pts || []).length;
  const k = Math.max(1, Math.round(windowPx / stepPx));
  if (n < 2 * k + 1) return [];
  const turn = new Array(n).fill(0);
  for (let i = k; i < n - k; i++) {
    const ax = pts[i].x - pts[i - k].x, ay = pts[i].y - pts[i - k].y;
    const bx = pts[i + k].x - pts[i].x, by = pts[i + k].y - pts[i].y;
    const la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
    if (la < 1e-9 || lb < 1e-9) continue;
    const c = Math.max(-1, Math.min(1, (ax * bx + ay * by) / (la * lb)));
    turn[i] = (Math.acos(c) * 180) / Math.PI;
  }
  const out = [];
  for (let i = k; i < n - k; i++) {
    if (turn[i] < minTurnDeg) continue;
    let peak = true;
    for (let j = i - k; j <= i + k; j++) {
      if (j === i) continue;
      // ties go to the earlier sample, so one corner is reported once
      if (turn[j] > turn[i] || (turn[j] === turn[i] && j < i)) { peak = false; break; }
    }
    if (peak) out.push(i);
  }
  return out;
}

// Gaussian smoothing along an evenly spaced open piece. The window shrinks
// symmetrically toward each end, so both ends stay exactly where they are and
// nothing is pulled inward off them.
export function smoothPiece(pts, stepPx = PEN_RESAMPLE_PX, sigmaPx = PEN_SMOOTH_SIGMA_PX) {
  const n = (pts || []).length;
  if (n < 3 || !(sigmaPx > 0)) return (pts || []).map((p) => ({ x: p.x, y: p.y }));
  const sigma = sigmaPx / stepPx;
  const R = Math.max(1, Math.ceil(3 * sigma));
  const w = [];
  for (let j = 0; j <= R; j++) w.push(Math.exp(-(j * j) / (2 * sigma * sigma)));
  const out = new Array(n);
  for (let i = 0; i < n; i++) {
    const r = Math.min(R, i, n - 1 - i);
    let sx = 0, sy = 0, sw = 0;
    for (let j = -r; j <= r; j++) {
      const wj = w[Math.abs(j)];
      sx += pts[i + j].x * wj; sy += pts[i + j].y * wj; sw += wj;
    }
    out[i] = { x: sx / sw, y: sy / sw };
  }
  return out;
}

// One stroke's pointer samples -> { points, curves }, the open-shape record.
// null when the samples do not make a stroke (fewer than two distinct points).
// The first and last samples come back as the first and last points, exactly:
// that is what lets a snapped end stay on what it snapped to.
export function strokeToPath(samples, opts = {}) {
  const src = [];
  for (const p of samples || []) {
    if (!p || !isFinite(p.x) || !isFinite(p.y)) continue;
    if (src.length && dist(src[src.length - 1], p) < 1e-6) continue;
    src.push({ x: p.x, y: p.y });
  }
  if (src.length < 2) return null;
  const step = opts.resamplePx > 0 ? opts.resamplePx : PEN_RESAMPLE_PX;
  const sigma = opts.sigmaPx >= 0 ? opts.sigmaPx : PEN_SMOOTH_SIGMA_PX;
  const fitTol = opts.fitTolPx > 0 ? opts.fitTolPx : PEN_FIT_TOL_PX;
  const straightTol = opts.straightTolPx > 0 ? opts.straightTolPx : PEN_STRAIGHT_TOL_PX;
  const maxPoints = opts.maxPoints > 1 ? opts.maxPoints : MAX_SHAPE_POINTS;

  const even = resamplePath(src, step);
  const cuts = [0, ...cornerIndices(even, step), even.length - 1];
  const pieces = [];
  for (let c = 0; c + 1 < cuts.length; c++) pieces.push(smoothPiece(even.slice(cuts[c], cuts[c + 1] + 1), step, sigma));

  let tol = fitTol, fitted = null;
  for (let attempt = 0; attempt < 6; attempt++, tol *= 2) {
    fitted = fitPieces(pieces, tol, straightTol);
    if (fitted.points.length <= maxPoints) return fitted;
  }
  // Still over the cap after six doublings: straight segments, decimated by
  // the tracer's own guard. Not reachable from a stroke on this canvas; here
  // so the cap is a guarantee and not a likelihood.
  const all = [];
  pieces.forEach((p, c) => { for (let i = c === 0 ? 0 : 1; i < p.length; i++) all.push(p[i]); });
  const points = simplifyRingAdaptive(all, tol, maxPoints);
  return points.length >= 2 ? { points: points.map((p) => ({ x: p.x, y: p.y })), curves: {} } : null;
}

// ---- The curve fit ----------------------------------------------------------
// Each smoothed piece (corner to corner) becomes a chain of anchors joined by
// straight segments or quadratic curves. A curve's control point is where the
// path's own tangents at the span's two ends cross, so the curve leaves one
// anchor and arrives at the next along the path's direction, and two curves
// that meet at an anchor meet without a kink. That is what a Column needs: its
// rails are the spine pushed sideways, and a kink in the spine is a spike on a
// rail.
//
// (The tracer's fit, manualTrace.fitCurvesForRing, was tried here first and
// measured: it puts the span's worst point at the curve's parametric middle,
// which on the short spans a pen stroke simplifies to hooks the curve back on
// itself. Worst tangent break at an anchor, 60 px arc with 1.2 px of jitter:
// 138 degrees, against 18 for this fit. penStroke.spec.js, "fit error".)

const cross = (ax, ay, bx, by) => ax * by - ay * bx;

// Unit direction of travel at index i of an evenly spaced piece, read over two
// samples either side (one-sided at the piece's ends).
function tangentAt(P, i) {
  const a = P[Math.max(0, i - 2)], b = P[Math.min(P.length - 1, i + 2)];
  const dx = b.x - a.x, dy = b.y - a.y, l = Math.hypot(dx, dy);
  return l > 1e-9 ? { x: dx / l, y: dy / l } : null;
}

function distToChord(p, a, c) {
  const dx = c.x - a.x, dy = c.y - a.y, l2 = dx * dx + dy * dy;
  if (l2 === 0) return dist(p, a);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

// Where the tangent lines at the span's ends cross, when that point lies ahead
// of the start and behind the end and the span turns by under a quarter turn.
// null otherwise (parallel tangents, an inflection, too sharp a bend): the
// caller splits the span.
const MAX_SPAN_TURN_COS = Math.cos((85 * Math.PI) / 180);
const MIN_CONTROL_BALANCE = 0.4;
function tangentControl(P, i0, i1) {
  const a = P[i0], c = P[i1], ta = tangentAt(P, i0), tc = tangentAt(P, i1);
  if (!ta || !tc) return null;
  if (ta.x * tc.x + ta.y * tc.y < MAX_SPAN_TURN_COS) return null;
  const den = cross(ta.x, ta.y, tc.x, tc.y);
  if (Math.abs(den) < 1e-6) return null;
  const s = cross(c.x - a.x, c.y - a.y, tc.x, tc.y) / den;
  const u = cross(ta.x, ta.y, c.x - a.x, c.y - a.y) / den;
  if (!(s > 0) || !(u > 0)) return null;
  // A LOPSIDED control is refused too. `s` and `u` are how far the control
  // sits from each end, and a quadratic's bend concentrates at the end its
  // control is near (curvature there goes with the cube of the ratio). A long
  // straight leg running into a short bend fits one such curve to within the
  // tolerance, and the curve is then a straight line with a hairpin of a few
  // px radius at its end: a 4 mm Column folds on it (found by e2e (p2), a
  // shallow V refused as "folds over itself"). Split instead: the leg comes
  // back as a straight segment and the bend as a balanced curve of its own.
  if (Math.min(s, u) < MIN_CONTROL_BALANCE * Math.max(s, u)) return null;
  return { x: a.x + ta.x * s, y: a.y + ta.y * s };
}

// Worst distance from the span's samples to the curve a-control-c, and the
// index it happens at.
function curveError(P, i0, i1, control) {
  const a = P[i0], c = P[i1];
  const chain = [a, ...flattenQuadraticSegment(a, control, c), c];
  let worst = 0, at = i0;
  for (let i = i0 + 1; i < i1; i++) {
    let d = Infinity;
    for (let k = 0; k + 1 < chain.length; k++) d = Math.min(d, distToChord(P[i], chain[k], chain[k + 1]));
    if (d > worst) { worst = d; at = i; }
  }
  return { worst, at };
}

function fitSpan(P, i0, i1, tol, straightTol, out) {
  const a = P[i0], c = P[i1];
  let dev = 0, devAt = i0;
  for (let i = i0 + 1; i < i1; i++) {
    const d = distToChord(P[i], a, c);
    if (d > dev) { dev = d; devAt = i; }
  }
  if (dev <= straightTol || i1 - i0 < 2) { out.push({ to: i1, control: null }); return; }
  const control = tangentControl(P, i0, i1);
  let splitAt = devAt;
  if (control) {
    const e = curveError(P, i0, i1, control);
    if (e.worst <= tol) { out.push({ to: i1, control }); return; }
    splitAt = e.at;
  }
  // Split away from the ends, so neither half is a sliver whose tangents are
  // read off the same few samples.
  const lo = i0 + 1, hi = i1 - 1;
  const mid = (i0 + i1) >> 1;
  if (splitAt - i0 < 3 || i1 - splitAt < 3) splitAt = mid;
  splitAt = Math.max(lo, Math.min(hi, splitAt));
  fitSpan(P, i0, splitAt, tol, straightTol, out);
  fitSpan(P, splitAt, i1, tol, straightTol, out);
}

function fitPieces(pieces, tol, straightTol) {
  const points = [], curves = {};
  pieces.forEach((P, c) => {
    if (c === 0) points.push({ x: P[0].x, y: P[0].y });
    if (P.length < 2) return;
    const segs = [];
    fitSpan(P, 0, P.length - 1, tol, straightTol, segs);
    for (const s of segs) {
      if (s.control) curves[points.length - 1] = { x: s.control.x, y: s.control.y };
      points.push({ x: P[s.to].x, y: P[s.to].y });
    }
  });
  return { points, curves };
}

// What a stroke's start or end at `pt` lands on: the nearest END of another
// open shape of the same kind within the radius, else the nearest point of
// such a shape's spine. null when nothing is that close. `kind` is the draw
// mode's, "column" or "run". Shapes with problems are not targets: they do
// not sew.
//
// It reads SPINES, not shapes: `snapSpines` does the per-shape work (the
// validity check builds a column's rails and tests them for self-crossing, and
// every shape is flattened) once per change to the drawing, so that this, which
// runs on every pointer move, only measures distances.
export function snapSpines(shapes, kind) {
  const same = kind === "column" ? isColumn : kind === "run" ? isRun : null;
  if (!same) return [];
  const out = [];
  for (const s of shapes || []) {
    if (!same(s) || shapeProblems(s).length) continue;
    const flat = flattenShape(s.points, s.curves, false);
    if (flat.length >= 2) out.push({ id: s.id, flat });
  }
  return out;
}

export function snapTarget(pt, spines, radiusPx = PEN_SNAP_RADIUS_PX) {
  if (!pt) return null;
  let end = null, spine = null;
  for (const s of spines || []) {
    const flat = s.flat;
    for (const e of [flat[0], flat[flat.length - 1]]) {
      const d = dist(pt, e);
      if (d <= radiusPx && (!end || d < end.d)) end = { x: e.x, y: e.y, d, on: "end", shapeId: s.id };
      // (s.id: a spine carries its shape's id)
    }
    for (let i = 0; i + 1 < flat.length; i++) {
      const a = flat[i], b = flat[i + 1];
      const dx = b.x - a.x, dy = b.y - a.y, l2 = dx * dx + dy * dy;
      let t = l2 > 0 ? ((pt.x - a.x) * dx + (pt.y - a.y) * dy) / l2 : 0;
      t = Math.max(0, Math.min(1, t));
      const q = { x: a.x + dx * t, y: a.y + dy * t };
      const d = dist(pt, q);
      if (d <= radiusPx && (!spine || d < spine.d)) spine = { x: q.x, y: q.y, d, on: "spine", shapeId: s.id };
    }
  }
  const hit = end || spine;
  return hit ? { x: hit.x, y: hit.y, on: hit.on, shapeId: hit.shapeId } : null;
}

// A stroke's samples with its ends moved onto what they snapped to.
//
// Moving only the end POINT is not enough. The pointer went down a few px off
// the snap point and was already travelling, so the samples just after it can
// lie on the far side of the snap point: the path then leaves the snap point,
// doubles back through where the pointer really was, and carries on. That hook
// is a few px long, and a Column's rails fold over it (found in the browser,
// 2026-11-13: a 4 mm column snapped to another's end was refused as "folds
// over itself"). So every sample still inside the snap radius of a snapped end
// goes, and the snap point stands in for all of them.
//   samples:   the raw pointer samples, down to up
//   startSnap: { x, y } the start landed on, or null
//   endSnap:   { x, y } the end landed on, or null
export function withSnappedEnds(samples, startSnap, endSnap, radiusPx = PEN_SNAP_RADIUS_PX) {
  let pts = (samples || []).slice();
  if (startSnap) {
    let i = 0;
    while (i < pts.length && dist(pts[i], startSnap) <= radiusPx) i++;
    pts = [{ x: startSnap.x, y: startSnap.y }, ...pts.slice(i)];
  }
  if (endSnap) {
    let j = pts.length;
    // never eat the snapped start: index 0 stays when there was one
    const floor = startSnap ? 1 : 0;
    while (j > floor && dist(pts[j - 1], endSnap) <= radiusPx) j--;
    pts = [...pts.slice(0, j), { x: endSnap.x, y: endSnap.y }];
  }
  return pts;
}

// ---- What the next stroke is born with ------------------------------------
// Kent, 2026-11-13: a new Column takes the width of the Column last drawn or
// edited; the first is still COLUMN_DEFAULT_MM (ruling 9 stands). Held in the
// module, not the panel: ContentStep remounts the panel per element and per
// visit to the step, and a width that reset on each visit would not be
// "remembered". It is the session's, so it carries into the next drawing and
// the next project too: that is what remembering a pen's width means.
let penWidthMm = null;

export function nextColumnWidthMm() {
  return penWidthMm > 0 ? penWidthMm : COLUMN_DEFAULT_MM;
}
export function rememberColumnWidthMm(mm) {
  if (typeof mm === "number" && isFinite(mm) && mm > 0) penWidthMm = mm;
}
export function resetPenMemory() {
  penWidthMm = null;
}

// The colour a new Column or Line is born with: the selected shape's, else the
// colour of the shape drawn last in THIS drawing, else the fallback. Read off
// the drawing itself and nothing else. (It was first a module map keyed by
// element id, and element ids are recycled: a new project's first manual
// element is "e1" again and would have inherited the last project's colour.
// Review, 2026-11-13.)
const isRgb = (c) => Array.isArray(c) && c.length === 3 && c.every((v) => typeof v === "number" && isFinite(v));
export function nextOpenShapeColor(shapes, selectedShape, fallbackRgb) {
  if (selectedShape && isRgb(selectedShape.colorRgb)) return selectedShape.colorRgb.slice();
  const list = shapes || [];
  for (let i = list.length - 1; i >= 0; i--) if (list[i] && isRgb(list[i].colorRgb)) return list[i].colorRgb.slice();
  return fallbackRgb;
}

// A pointer position held to the authored canvas. With the pointer captured a
// drag keeps reporting past the canvas edge, and a point out there would be
// invisible on this canvas and still count toward the design's size.
export function clampToCanvas(pt, w = CANVAS_W, h = CANVAS_H) {
  return { x: Math.max(0, Math.min(w, pt.x)), y: Math.max(0, Math.min(h, pt.y)) };
}

// The one column whose width was just EDITED between two shape lists: the same
// ids on both sides, and exactly one column's `widthPx` differs. A new or
// deleted shape is not an edit, and neither is a change to several at once.
export function widthEditedColumn(prevShapes, nextShapes) {
  const prev = prevShapes || [], next = nextShapes || [];
  if (prev.length !== next.length) return null;
  const byId = new Map(prev.map((s) => [s && s.id, s]));
  let hit = null;
  for (const s of next) {
    const p = byId.get(s && s.id);
    if (!p) return null;
    if (!isColumn(s) || !isColumn(p) || s.widthPx === p.widthPx) continue;
    if (hit) return null;
    hit = s;
  }
  return hit;
}
