// simulate.js — pure playback math for the stitch simulator (no canvas, no
// timers here; EmbroideryField owns the rAF loop and rendering).
//
// Progress is measured in STRANDS (drawable segments from designToStrands),
// not raw stitch records — strands are what actually paint, so "N of total"
// maps 1:1 onto what the user sees appear.

import { nearestInList } from "./threads.js";

// Playback rates. BASE_SPS is strands-per-second at 1x — slow enough to watch
// individual letters form, fast enough that a 5k-stitch name finishes in
// ~20s. The speed multipliers are the user-facing options.
export const BASE_SPS = 250;
export const SPEEDS = [1, 2, 4, 8];

// One playback tick: advance `index` (a float — fractional progress carries
// across frames so slow speeds still move on every frame) by dtMs at `speed`,
// clamped to [0, total]. Returns the new index; callers floor it for display
// and drawing.
export function advanceIndex(index, dtMs, speed, total) {
  if (!Number.isFinite(dtMs) || dtMs < 0) dtMs = 0;
  const next = index + (dtMs / 1000) * BASE_SPS * speed;
  return Math.max(0, Math.min(total, next));
}

// Scrub-slider input → clamped integer index.
export function clampIndex(value, total) {
  const n = Math.floor(Number(value) || 0);
  return Math.max(0, Math.min(total, n));
}

// The next speed option after `speed`, cycling back to the first — the
// simulator bar's speed button cycles instead of using a dropdown.
export function nextSpeed(speed) {
  const i = SPEEDS.indexOf(speed);
  return SPEEDS[(i + 1) % SPEEDS.length];
}

// ---- The machine's events, on the strand timeline --------------------------
//
// The bar above plays STRANDS; a machine operator watches EVENTS — which
// thread is on, where the needle is, when it trims, when it travels, when it
// stops for the next colour. `simTimeline` lays those events out once, in
// strand units, so the per-frame work is a binary search and never a walk.
//
// Positions are strand counts: `at` = how many strands are drawn when the
// event happens. The canvas shows strands [0, idx), so an event with
// `at <= idx` has happened.
//
//   blocks[k]  = { start, end, rgb, color }   strands [start, end) sew thread k.
//                One entry per thread block in sew order — one per `color`
//                record plus the first — so `blocks.length` is the PDF's
//                "Thread Sequence" row count and `colors[k]` names block k
//                (combine.js keeps that invariant). A block that sews nothing
//                (start === end) is kept: the machine still stops for it.
//   trims[]    = { at, x, y }      a trim record, at the needle position it names.
//   travels[]  = { at, x0, y0, x1, y1 }   the frame moving with the needle up,
//                between strand at-1's end and strand at's start (jump, trim
//                or colour change — whatever broke the chain). A break that
//                lands where it left (zero length) is kept, so "the latest
//                break" is always the right one; nothing draws it.
//
// It walks the stitches with designToStrands's exact chain rule — color
// breaks and advances the thread, any other non-stitch breaks — and the spec
// pins that its strand count equals designToStrands's on every fixture, so
// the timeline can never drift from what the canvas draws.
export function simTimeline(design) {
  const stitches = (design && design.stitches) || [];
  const colors = (design && design.colors) || [];
  const rgbOf = (c, fallback) => (c ? [c.r, c.g, c.b] : fallback);
  let cur = rgbOf(colors[0], [20, 20, 20]);
  const blocks = [{ start: 0, end: 0, rgb: cur, color: colors[0] || null }];
  const trims = [];
  const travels = [];
  let n = 0;           // strands so far
  let prev = null;     // previous sewn stitch in the current chain
  let lastEnd = null;  // end of the last strand drawn
  let broke = false;   // a non-stitch record since the last strand
  for (const st of stitches) {
    if (st.type === "color") {
      blocks[blocks.length - 1].end = n;
      const c = colors[blocks.length];
      if (c) cur = rgbOf(c, cur);
      blocks.push({ start: n, end: n, rgb: cur, color: c || null });
      prev = null;
      broke = true;
      continue;
    }
    if (st.type !== "stitch") {
      if (st.type === "trim") trims.push({ at: n, x: st.x, y: st.y });
      prev = null;
      broke = true;
      continue;
    }
    if (prev) {
      // Every break is recorded, a zero-length one too, so travelAt can tell
      // "the needle went straight back down here" from "the frame moved".
      if (broke && lastEnd) travels.push({ at: n, x0: lastEnd.x, y0: lastEnd.y, x1: prev.x, y1: prev.y });
      broke = false;
      n++;
      lastEnd = st;
    }
    prev = st;
  }
  blocks[blocks.length - 1].end = n;
  return { total: n, blocks, trims, travels };
}

// Index of the last entry in `list` (sorted by `key`) whose key is <= v, or -1.
function lastAtOrBefore(list, v, key) {
  let lo = 0, hi = list.length - 1, ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (list[mid][key] <= v) { ans = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return ans;
}

// The thread block the needle is in with `idx` strands drawn: the block of
// the last strand drawn (idx - 1), or block 0 before anything is sewn. On a
// boundary that is the block just FINISHED — the machine is stopped at the
// end of it, still threaded with it.
export function blockAt(tl, idx) {
  if (!tl || !tl.blocks.length) return 0;
  if (idx <= 0) {
    // Nothing sewn yet: the first block that sews anything, so a design whose
    // stream opens with a colour record names the thread it really starts on.
    const k = tl.blocks.findIndex((b) => b.end > b.start);
    return k < 0 ? 0 : k;
  }
  // An empty block shares its start with the block after it, so the LAST
  // block starting at or before the strand is the one that contains it.
  return Math.max(0, lastAtOrBefore(tl.blocks, Math.min(idx, tl.total) - 1, "start"));
}

// Where playback must stop on its way from `from` to `to` (strands): the
// first thread change strictly after `from` and at or before `to`, or null.
// A change at 0 (the stream opens with a colour record) or at the very end
// (a trailing record with nothing after it) is not a stop the viewer can
// see, so neither counts.
export function colorStopBetween(tl, from, to) {
  if (!tl) return null;
  for (let k = 1; k < tl.blocks.length; k++) {
    const s = tl.blocks[k].start;
    if (s > from && s <= to && s > 0 && s < tl.total) return s;
    if (s > to) break;
  }
  return null;
}

// The previous/next thread change from `idx` (dir -1 / +1), as a strand
// index; the design's start or end when there is none that way. "Next" lands
// ON the change — the previous thread finished, the next not begun — which is
// where the machine stops.
export function stepBlock(tl, idx, dir) {
  if (!tl) return idx;
  const starts = [];
  for (let k = 1; k < tl.blocks.length; k++) {
    const s = tl.blocks[k].start;
    if (s > 0 && s < tl.total && s !== starts[starts.length - 1]) starts.push(s);
  }
  if (dir > 0) {
    for (const s of starts) if (s > idx) return s;
    return tl.total;
  }
  for (let i = starts.length - 1; i >= 0; i--) if (starts[i] < idx) return starts[i];
  return 0;
}

// The travel to draw "in flight" at `idx`: the latest break the needle has
// reached; it stays up while the needle sews the run that break led into.
// null before the first break, and null when that break moved nowhere.
export function travelAt(tl, idx) {
  if (!tl || !tl.travels.length) return null;
  const i = lastAtOrBefore(tl.travels, idx, "at");
  if (i < 0) return null;
  const t = tl.travels[i];
  return t.x0 === t.x1 && t.y0 === t.y1 ? null : t;
}

// How many of `list` (sorted by `at`) have happened at `idx`.
export function countAt(list, idx) {
  return lastAtOrBefore(list || [], idx, "at") + 1;
}

// The bar's name for each thread block, read off `threads` (a chart's thread
// list) by nearest colour and labelled "<code> <name>" — exactly how the
// Download step's thread list and the PDF worksheet name the same blocks
// (DownloadStep `threadRows` / `namedColors`), so the simulator never calls a
// cone something the sheet does not.
export function blockThreadNames(tl, threads) {
  if (!tl || !Array.isArray(threads) || !threads.length) return [];
  return tl.blocks.map((b) => {
    const t = nearestInList(threads, b.rgb);
    return t.code ? `${t.code} ${t.name}` : t.name;
  });
}

// ---- Underlay vs top stitching, on the strand timeline ---------------------
//
// Underlay sews FIRST and is then covered by the top stitching of the same
// shape. On the finished canvas that is already true (preview.js draws every
// colour block's underlay group under its fill/satin group), but while the
// simulator plays there is a stretch where the underlay is sewn and its top
// is not: it then looks like a thin, open version of the real stitching. The
// simulator marks exactly that stretch — "pending" underlay — and nothing
// else, so the mark never sits on top of stitching that covers it.
//
// The tags are the strands' own (designToStrands copies each run span's
// `kind` and `shape`): no classification happens here. A design without
// `runs` has no underlay strand, so this is empty and nothing changes.
//
//   runs[i] = { start, end, coverAt, rgb }
//     strands [start, end) are underlay, consecutive, of one shape and one
//     thread; coverAt is the first strand AFTER them that is top stitching
//     (not underlay, travel or a tie) of the same shape — or of any shape
//     when the underlay names none — in the same thread block, else the
//     block's end. The run is pending with idx strands drawn when
//     start < idx <= coverAt (sewn, and its top has not begun).
//   maxCover[i] = the largest coverAt over runs[0..i], so a frame can stop
//     scanning backwards as soon as no earlier run can still be pending.
const NOT_TOP = { underlay: true, travel: true, tie: true };

export function isUnderlayStrand(s) {
  return !!s && s.kind === "underlay";
}

export function underlayRuns(strands, tl) {
  const list = strands || [];
  const n = list.length;
  const runs = [];
  if (!n || !list.some(isUnderlayStrand)) return { runs, maxCover: [] };
  // Each strand's block end, from the timeline when there is one.
  const blockEnd = new Int32Array(n).fill(n);
  if (tl && tl.blocks) for (const b of tl.blocks) for (let i = b.start; i < b.end && i < n; i++) blockEnd[i] = b.end;
  // One backward pass: the nearest top strand at or after i, by shape and
  // for any shape, reset at each block boundary (a cover never crosses a
  // thread change).
  const coverOf = new Int32Array(n);
  let byShape = new Map();
  let anyTop = -1;
  let curEnd = -1;
  for (let i = n - 1; i >= 0; i--) {
    if (blockEnd[i] !== curEnd) { curEnd = blockEnd[i]; byShape = new Map(); anyTop = -1; }
    const s = list[i];
    if (!NOT_TOP[s.kind]) {
      anyTop = i;
      if (s.shape) byShape.set(s.shape, i);
      continue;
    }
    if (s.kind !== "underlay") continue;
    const hit = s.shape ? byShape.get(s.shape) : anyTop;
    coverOf[i] = hit != null && hit >= 0 ? hit : blockEnd[i];
  }
  for (let i = 0; i < n; i++) {
    const s = list[i];
    if (!isUnderlayStrand(s)) continue;
    const last = runs[runs.length - 1];
    if (last && last.end === i && last.coverAt === coverOf[i] && last.shape === (s.shape || "")) { last.end = i + 1; continue; }
    runs.push({ start: i, end: i + 1, coverAt: coverOf[i], shape: s.shape || "", rgb: s.rgb });
  }
  const maxCover = [];
  let m = -1;
  for (const r of runs) { if (r.coverAt > m) m = r.coverAt; maxCover.push(m); }
  return { runs, maxCover };
}

// The underlay runs pending with `idx` strands drawn (see underlayRuns), each
// as { start, end: min(end, idx), rgb } — the part already sewn. Walks back
// from the last run that has started and stops once no earlier run can be
// pending, so a frame pays for the underlay in flight, not for the design.
export function pendingUnderlay(ul, idx) {
  const out = [];
  if (!ul || !ul.runs.length || idx <= 0) return out;
  const runs = ul.runs;
  let j = lastAtOrBefore(runs, idx - 1, "start");
  for (; j >= 0; j--) {
    if (ul.maxCover[j] < idx) break;
    const r = runs[j];
    if (r.coverAt >= idx) out.push({ start: r.start, end: Math.min(r.end, idx), rgb: r.rgb });
  }
  return out;
}

// What the needle is sewing with `idx` strands drawn, for the bar: "underlay"
// while it is in an underlay strand, "top" otherwise, null before anything is
// sewn or once the design is finished.
export function phaseAt(strands, idx, total) {
  if (!strands || idx <= 0 || idx >= total) return null;
  return isUnderlayStrand(strands[idx - 1]) ? "underlay" : "top";
}

// The block whose band on the scrubber's thread strip was clicked, as the
// strand index to land on: the block's start, where the machine stops for
// it (the thread before it finished, this one not begun). Block 0 is the
// design's start.
export function blockStart(tl, k) {
  if (!tl || !tl.blocks[k]) return 0;
  return Math.max(0, Math.min(tl.total, tl.blocks[k].start));
}

// ---- Sew time, on the strand timeline --------------------------------------
//
// "About 12 min left of 18" for the bar (Kent, 2026-11-07: "Show it"). The
// minutes are NOT computed here: they come from the engine's own
// `sewTimeMin` (src/sewtime.js) at estimate.js `runSpm` (the Quote speed when
// one is set, else `PLAN_SPM`), the same function and the same rate as the
// "Run time" row in Download, so
// the bar's total and theirs cannot disagree. That function already charges
// every STOP (a trim, or a colour change the thread was not already cut for)
// at TRIM_COST_STITCHES, so the bar uses it as is and adds nothing.
//
// What lives here is only the clock's positions: how many stitches and how
// many stops are still ahead with `idx` strands drawn. `sewClock` walks the
// stitches once, with designToStrands's chain rule for the strands and
// estimate.js `sewFacts`'s rule for the stops (the spec pins both totals to
// sewFacts), and records
//   chainStarts[] = { at }  a sewn stitch that opens a chain (no strand of its
//                   own: the needle goes down there before strand `at`).
//                   Every other sewn stitch ends exactly one strand, so
//                   stitches done = strands done + chain starts done.
//   stopAt[]      = { at }  a stop, before strand `at` is sewn (`stops` is
//                   their count, `stitches` the sewn-stitch count).
// An event at `at` is still AHEAD with idx === at drawn: landed on a thread
// change, the change itself (the stop) has not happened yet.
export function sewClock(design) {
  const stitches = (design && design.stitches) || [];
  const chainStarts = [];
  const stops = [];
  let n = 0;
  let prev = null;
  let cut = false;
  for (const st of stitches) {
    if (st.type === "color") { if (!cut) stops.push({ at: n }); cut = true; prev = null; continue; }
    if (st.type === "trim") { stops.push({ at: n }); cut = true; prev = null; continue; }
    if (st.type !== "stitch") { prev = null; continue; }
    cut = false;
    if (prev) n++;
    else chainStarts.push({ at: n });
    prev = st;
  }
  return { total: n, stitches: n + chainStarts.length, stops: stops.length, chainStarts, stopAt: stops };
}

// How many of `list` (sorted by `at`) are strictly before `idx`.
function countBefore(list, idx) {
  let lo = 0, hi = list.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (list[mid].at < idx) lo = mid + 1; else hi = mid;
  }
  return lo;
}

// The bar's sew-time figures with `idx` strands drawn: { left, total } in
// whole minutes, from `sewTimeMin(stitches, stops, spm)` (src/sewtime.js;
// passed in, so this file stays free of the engine global). null when the
// function is missing or cannot support a figure, so the bar drops the
// readout rather than print a wrong one. A finished design has 0 left.
export function sewTimeAt(clock, idx, sewTimeMin, spm) {
  if (!clock || typeof sewTimeMin !== "function") return null;
  const total = sewTimeMin(clock.stitches, clock.stops, spm);
  if (total == null) return null;
  if (idx >= clock.total) return { left: 0, total };
  const i = Math.max(0, idx);
  const stitchesDone = i + countBefore(clock.chainStarts, i);
  const stopsDone = countBefore(clock.stopAt, i);
  const left = sewTimeMin(clock.stitches - stitchesDone, clock.stops - stopsDone, spm);
  if (left == null) return null;
  return { left: Math.min(left, total), total };
}

// "about 12 min left of 18": the words, labelled as an estimate. Finished,
// it says the whole run, which is what the viewer has just watched.
export function sewTimeText(t) {
  if (!t) return "";
  if (t.left <= 0) return `about ${t.total} min in all`;
  return `about ${t.left} min left of ${t.total}`;
}
