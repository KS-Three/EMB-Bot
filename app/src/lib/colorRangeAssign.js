// Assign a colour to [start,end) of a text element's colorRanges.
//
// The engine resolves overlapping ranges to whichever appears FIRST (see
// colorForCharIdx in src/digitize.js), so appending a new range after an
// existing one over the same letters changed nothing on the design while the
// list showed both. Assigning therefore carves the new span out of every
// existing range (trimming or splitting them), then appends it.
export function assignColorRange(ranges, start, end, colorRgb) {
  if (!(end > start)) return ranges;
  const out = [];
  for (const r of ranges) {
    if (r.endIdx <= start || r.startIdx >= end) { out.push(r); continue; }
    if (r.startIdx < start) out.push({ ...r, endIdx: start });
    if (r.endIdx > end) out.push({ ...r, startIdx: end });
  }
  out.push({ startIdx: start, endIdx: end, colorRgb });
  return out;
}
