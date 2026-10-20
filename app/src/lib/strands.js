// Travel/trim geometry for the field's diagnostic overlays (Ember-audit
// follow-up): every positional discontinuity the machine crosses with the
// needle UP becomes a dashed "jump" segment, and every trim record becomes a
// marker at its position. Color/end records break the chain like they do in
// designToStrands (an end record's position is a bookkeeping artifact, and a
// color change doesn't move the hoop).
export function jumpTrimMarks(design) {
  const jumps = [];
  const trims = [];
  let prev = null;
  for (const st of design.stitches) {
    if (st.type === "color" || st.type === "end") { prev = null; continue; }
    if (st.type === "jump" || st.type === "trim") {
      if (st.type === "trim") trims.push({ x: st.x, y: st.y });
      if (prev && (prev.x !== st.x || prev.y !== st.y)) {
        jumps.push({ x0: prev.x, y0: prev.y, x1: st.x, y1: st.y });
      }
      prev = st;
      continue;
    }
    // stitch: a gap between the previous JUMP/TRIM landing point and here is
    // already covered (prev tracks position through jump records above).
    prev = st;
  }
  return { jumps, trims };
}

// The STITCH NUMBER each strand ends at, 1-based among `type === "stitch"`
// records — so the simulator can count in the same unit the field caption
// does.
//
// It has to exist because a strand is a SEGMENT BETWEEN two consecutive
// stitches, so N stitches in K runs make N − K strands, and the two numbers
// were on screen together saying different things: "1289 stitches · 102×12 mm"
// under the canvas and "1280 / 1280" in the simulator bar, nine apart, on a
// design with nine runs. Both were correct measurements of different things
// and only one of them was labelled.
//
// Same walk as designToStrands, deliberately — if that ever stops breaking the
// chain on a record type this does not, the mapping silently skews. The tests
// drive both from the same fixtures for exactly that reason.
//
// A run of a SINGLE stitch paints no segment, so its ordinal never appears
// here. That is why the simulator's total is the last entry rather than
// `design.stitchCount`: it must never claim to have drawn a stitch it cannot.
export function strandStitchOrdinals(design) {
  const out = [];
  let prev = null;
  let ordinal = 0;
  for (const st of (design && design.stitches) || []) {
    if (st.type === "color") { prev = null; continue; }
    if (st.type !== "stitch") { prev = null; continue; }
    ordinal++;
    if (prev) out.push(ordinal);
    prev = st;
  }
  return out;
}

// ---- Run spans: what each stitch IS ---------------------------------------
//
// The browser's design model is a flat {x,y,type} stream, so satin, tatami
// fill, bean runs, underlay and needle-down travel all arrive looking
// identical — which is why the canvas drew them identically, and why a satin
// border was impossible to pick out of the fill it borders (Kent, 2026-09-15).
//
// `design.runs` is the missing half: a list of spans over design.stitches,
//
//   { i0, i1, kind, shape, role, block }
//
// with i0/i1 INCLUSIVE indices into design.stitches (all records, not just
// sewn ones), `kind` one of satin|fill|run|underlay|travel, `role` "" |
// "border" | "edge_cap", `shape` a shape id or "".
//
// It is OPTIONAL and always will be: every .embproj saved before today, every
// imported .dst, and the browser's own lettering/manual/shape lanes produce
// designs without it. Absent runs must render exactly as they did before this
// existed — so the no-runs path below is the ORIGINAL loop, untouched, and
// strands from it carry no `role`/`shape` keys at all rather than empty ones.

// Validate + order the spans ONCE, so the walk below stays O(n + m) instead of
// searching per stitch. The common case (already sorted, all entries sane)
// allocates nothing and returns the caller's array as-is.
//
// An entry with a non-finite i0/i1 is dropped rather than tolerated: the walk
// advances a single monotonic pointer, so one undefined `i1` would wedge it
// and silently un-kind every stitch after that point — a corrupt span is
// better skipped than left to poison the rest of the design.
function orderedRuns(runs) {
  if (!Array.isArray(runs) || runs.length === 0) return null;
  let sorted = true, clean = true;
  for (let i = 0; i < runs.length; i++) {
    const r = runs[i];
    if (!r || !Number.isFinite(r.i0) || !Number.isFinite(r.i1) || r.i1 < r.i0) { clean = false; continue; }
    if (i > 0 && runs[i - 1] && Number.isFinite(runs[i - 1].i0) && r.i0 < runs[i - 1].i0) sorted = false;
  }
  if (clean && sorted) return runs;
  const out = runs.filter((r) => r && Number.isFinite(r.i0) && Number.isFinite(r.i1) && r.i1 >= r.i0);
  if (!out.length) return null;
  out.sort((a, b) => a.i0 - b.i0);
  return out;
}

export function designToStrands(design, opts) {
  const o = opts || {};
  const strands = [];
  const spans = orderedRuns(design && design.runs);
  let ci = 0;
  let cur = design.colors && design.colors[0] ? [design.colors[0].r, design.colors[0].g, design.colors[0].b] : [20, 20, 20];
  let prev = null;
  if (!spans) {
    // ORIGINAL loop, deliberately duplicated rather than branched inside: the
    // fallback is a hard requirement, and the cheapest way to keep it true is
    // for it to be the same code it always was.
    for (const st of design.stitches) {
      if (st.type === "color") { ci++; const c = design.colors[ci]; if (c) cur = [c.r, c.g, c.b]; prev = null; continue; }
      if (st.type !== "stitch") { prev = null; continue; } // jump/trim/end break the strand chain
      if (prev) strands.push({ x0: prev.x, y0: prev.y, x1: st.x, y1: st.y, rgb: o.colorOverride || cur, kind: "stitch" });
      prev = st;
    }
    return strands;
  }
  // Spans present: one pointer walked alongside the stitches. Queries only ever
  // happen at increasing i, so advancing lazily here is O(m) across the whole
  // design, not O(m) per stitch.
  let si = 0;
  const stitches = design.stitches;
  for (let i = 0; i < stitches.length; i++) {
    const st = stitches[i];
    if (st.type === "color") { ci++; const c = design.colors[ci]; if (c) cur = [c.r, c.g, c.b]; prev = null; continue; }
    if (st.type !== "stitch") { prev = null; continue; } // jump/trim/end break the strand chain
    if (prev) {
      while (si < spans.length && spans[si].i1 < i) si++;
      // A strand is the segment INTO stitch i, so it takes stitch i's span:
      // where two runs meet without a break between them, the thread crossing
      // from one to the next belongs to the run it is entering, which is the
      // one the needle is now sewing. A stitch inside no span (a gap, or a
      // design whose spans cover only part of it) falls back to the
      // kind-less "stitch" every pre-runs design uses.
      const sp = (si < spans.length && spans[si].i0 <= i) ? spans[si] : null;
      strands.push({
        x0: prev.x, y0: prev.y, x1: st.x, y1: st.y,
        rgb: o.colorOverride || cur,
        kind: (sp && sp.kind) || "stitch",
        role: (sp && sp.role) || "",
        shape: (sp && sp.shape) || "",
      });
    }
    prev = st;
  }
  return strands;
}

// ---- Sewn width: a satin strand with its pull compensation taken back ----
//
// Every satin column in a machine file is wider than its artwork by the
// fabric's pull compensation on each rail (`_push_rails` service-side,
// `src/satin.js` in the lettering lane): the cloth pulls the rails in as the
// thread tightens, and the file pre-empts it. A preview drawn at the file's
// width therefore shows every satin letter heavier than it sews — Hotel
// Fremont's 0.76 mm letters are 1.23 in the file and so was the pro's own
// file of the same logo (2026-10-06, `lib/sewnWidth.js` has the story). This
// takes the pull back off: each satin strand (a cross, or the lean leg to the
// next cross — both run rail to rail) loses `pullMm` at each end along its
// own direction, which is the rail stepping back in by what it was pushed.
// Fill, run, underlay, travel and kind-less strands are returned as they are,
// and the input array is never mutated. A VIEW only: no stitch moves.
//
// A cross too short to give up two pulls keeps one thread width, centred:
// SATIN_MIN_CROSS_MM is 0.5 in the file, so after a 0.3 mm pull each side a
// minimum cross is still a 0.4 mm thread on cloth, not a vanished stitch.
// 0.4 is preview.js's THREAD_WIDTH_MM; it is not imported here because
// preview.js imports this module.
export const SEWN_WIDTH_FLOOR_MM = 0.4;

export function shrinkSatinStrands(strands, pullMm) {
  if (!Array.isArray(strands) || strands.length === 0) return [];
  const pull = Number(pullMm);
  if (!(pull > 0)) return strands;
  const out = new Array(strands.length);
  for (let i = 0; i < strands.length; i++) {
    const s = strands[i];
    if (!s || s.kind !== "satin") { out[i] = s; continue; }
    const dx = s.x1 - s.x0, dy = s.y1 - s.y0;
    const len = Math.hypot(dx, dy);
    if (!(len > 0)) { out[i] = s; continue; }
    let cut = pull;
    if (len - 2 * pull < SEWN_WIDTH_FLOOR_MM) cut = Math.max(0, (len - SEWN_WIDTH_FLOOR_MM) / 2);
    const ux = (dx / len) * cut, uy = (dy / len) * cut;
    out[i] = { ...s, x0: s.x0 + ux, y0: s.y0 + uy, x1: s.x1 - ux, y1: s.y1 - uy };
  }
  return out;
}
