// combine.js — stitch-level design combining (Slice 5: multi-element studio).
//
// Merges N independently-generated Design objects (see generate.js's
// generateElement) into ONE sewable design: a trim + color-change spliced
// between each pair, colors concatenated, everything else derived from the
// single flat `stitches` array so the exporters (DST/EXP/PES/SVG) and the
// preview renderer never need to know a design was assembled from parts.
//
// ---- "end" records: why they're stripped and never re-added --------------
// A quick node -e probe against the real builders (see task notes) shows:
//   - buildLetteringDesign's real (non-empty) output never appends an `end`
//     stitch at all — its tail is a plain "stitch" record.
//   - buildQualityDesign's real output ALWAYS appends a trailing
//     `{x:0,y:0,type:"end"}` — note x/y are the ABSOLUTE design origin, not
//     relative to the last stitch.
// Reading src/dst.js's encodeDST and src/pes.js's readers settles how to
// normalize:
//   - encodeDST() never special-cases `type:"end"` — it falls through to the
//     "stitch" branch (so a stray one gets encoded as a real, oddly-placed
//     stitch) — AND it unconditionally appends its own endRecord() after
//     every design regardless of what `stitches` contains. It neither needs
//     nor benefits from an upstream "end".
//   - src/pes.js's pecEncodeStitches() and encodePES()'s CSewSeg builder both
//     BREAK the instant they see `type === "end"`, discarding every stitch
//     after it.
// So a naive concatenation of a buildQualityDesign-produced design followed
// by more stitches would silently truncate the PES export at that design's
// old trailing "end". combineDesigns strips every `end` record (interior or
// trailing) from each input's stitches before splicing, and does not append
// one to the combined result — the encoders don't need it, and leaving one
// in mid-stream actively breaks PES.
export function combineDesigns(designs) {
  const list = (designs || []).filter(Boolean);
  if (list.length === 0) return null;
  // Single design in -> returned structurally unchanged (same stitches) —
  // no "end" stripping, no rebuilt fields. Whatever the builder produced
  // (with or without a trailing "end") passes straight through.
  if (list.length === 1) return list[0];

  const stitches = [];
  const colors = [];
  let nSatin = 0, nFill = 0, nTrims = 0, haveDebug = false;

  list.forEach((d, i) => {
    if (i > 0) {
      const last = stitches[stitches.length - 1] || { x: 0, y: 0 };
      stitches.push({ x: last.x, y: last.y, type: "trim" });
      stitches.push({ x: last.x, y: last.y, type: "color" });
    }
    for (const s of d.stitches || []) {
      if (s.type === "end") continue;
      stitches.push(s);
    }
    for (const c of d.colors || []) colors.push(c);
    if (d._debug) {
      haveDebug = true;
      nSatin += d._debug.nSatin || 0;
      nFill += d._debug.nFill || 0;
      nTrims += d._debug.nTrims || 0;
    }
  });

  const bbox = bboxMmFromStitches(stitches);
  const stitchCount = stitches.filter((s) => s.type === "stitch").length;

  const combined = {
    stitches,
    colors,
    widthMM: bbox.x1 - bbox.x0,
    heightMM: bbox.y1 - bbox.y0,
    stitchCount,
    colorCount: colors.length,
  };
  if (haveDebug) combined._debug = { nSatin, nFill, nTrims };
  return combined;
}

// Shared bbox helper (mm, from DST-unit stitches /10). "color" and "end"
// records carry no meaningful geometry of their own (color: a marker at
// whatever position happened to be last; end: often an absolute-origin
// placeholder, see the note above) so both are skipped — stitch/jump/trim
// all have real coordinates and are included, matching the convention
// already used by preview.js's fitTransform/renderRealistic.
export function bboxMmFromStitches(stitches) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of stitches || []) {
    if (s.type === "color" || s.type === "end") continue;
    if (s.x < minX) minX = s.x;
    if (s.x > maxX) maxX = s.x;
    if (s.y < minY) minY = s.y;
    if (s.y > maxY) maxY = s.y;
  }
  if (!isFinite(minX)) return { x0: 0, y0: 0, x1: 0, y1: 0 };
  return { x0: minX / 10, y0: minY / 10, x1: maxX / 10, y1: maxY / 10 };
}
