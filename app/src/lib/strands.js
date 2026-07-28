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
