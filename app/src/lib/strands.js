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

export function designToStrands(design, opts) {
  const o = opts || {};
  const strands = [];
  let ci = 0;
  let cur = design.colors && design.colors[0] ? [design.colors[0].r, design.colors[0].g, design.colors[0].b] : [20, 20, 20];
  let prev = null;
  for (const st of design.stitches) {
    if (st.type === "color") { ci++; const c = design.colors[ci]; if (c) cur = [c.r, c.g, c.b]; prev = null; continue; }
    if (st.type !== "stitch") { prev = null; continue; } // jump/trim/end break the strand chain
    if (prev) strands.push({ x0: prev.x, y0: prev.y, x1: st.x, y1: st.y, rgb: o.colorOverride || cur, kind: "stitch" });
    prev = st;
  }
  return strands;
}
