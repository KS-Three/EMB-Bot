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
