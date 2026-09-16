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
// ---- `runs`: the run-span index, and why it is all-or-nothing -----------
// A design carries `runs` — spans of `{i0, i1, kind, shape, role, block}`
// over `stitches` — so the renderer can draw a satin column differently from
// a tatami fill and the UI can say whether a border was actually generated.
// Both lanes emit it: `digitizer_core/adapter.py` for a digitized design (and
// it owns the contract), `src/digitize.js`'s pushSpan for one built in the
// browser. Its load-bearing property is that the spans PARTITION the stitch
// records: every one is covered, none twice.
//
// Combining has to preserve that or drop it. Two things move the indices
// here and both must be counted, not assumed: every `end` record stripped out
// of an input (interior or trailing — see the note above) pulls its design's
// later stitches DOWN by one, and the trim/color spliced before an input
// pushes it UP by one or two. So the mapping is a running delta per design,
// never `i0 + offset`.
//
// If any input that SEWS lacks `runs`, the combined design carries none at
// all. A partial index would still look like a partition to a reader and
// would leave unclaimed the stitches of an element that never had spans — a
// wrong render with no symptom. The fallback (no `runs`, draw everything as
// ordinary stitching) is honest, and it is what every design produced before
// the index existed already gets.
//
// "that sews" is the one exception and it is not a loophole: an element whose
// font cannot sew any of its characters comes back with no stitches and no
// `runs` (`emptyWith` in digitize.js). It claims no records, so it can leave
// none unclaimed, and dropping the index over it would punish every other
// element for one unsupported character.
export function combineDesigns(designs) {
  const list = (designs || []).filter(Boolean);
  if (list.length === 0) return null;
  // Single design in -> returned structurally unchanged (same stitches) —
  // no "end" stripping, no rebuilt fields. Whatever the builder produced
  // (with or without a trailing "end") passes straight through. Its `runs`,
  // if it has one, is still an index into the very array being returned.
  if (list.length === 1) return list[0];

  const stitches = [];
  const colors = [];
  // Nulled by the loop the moment a stitch-bearing input turns out to have no
  // index, or to carry one that does not describe its own records. Started
  // only when there is something to carry, so a project of browser-built
  // designs on an engine without spans does no work at all.
  let runs = list.some((d) => Array.isArray(d.runs)) ? [] : null;
  let nSatin = 0, nFill = 0, nTrims = 0, haveDebug = false;

  list.forEach((d) => {
    // ---- Two elements in the same thread are ONE block ------------------
    //
    // A colour change is a machine stop. On a single-needle home machine it
    // is a full pause with a prompt to rethread; the operator then loads the
    // colour that is already loaded. This spliced one between EVERY pair,
    // whatever colour they were, so the commonest real design there is — a
    // two-line name, one thread — cost a stop it could not use, and the
    // review's thread list and the PDF worksheet both listed the same cone
    // twice. Measured 2026-09-07: two black text elements produced
    // `colors: [Color 1 (20,20,20), Color 1 (20,20,20)]`, colorCount 2, one
    // colour-change record.
    //
    // Only ADJACENT blocks merge, and only across the splice. Merging a
    // black/red/black project down to two would mean reordering the sew,
    // which changes what lands on top of what — that is a different question
    // and not a free one. (`COLOR_STOPS_HEAVY` in the Python preflight names
    // the same saving on the digitized lane; this is the browser lane's.)
    //
    // The TRIM stays either way: the needle still has to travel between two
    // elements without dragging thread across the garment.
    const first = (d.colors || [])[0];
    const prev = colors[colors.length - 1];
    const mergesWithPrevious = !!first && !!prev && sameThread(prev, first);
    // Where this design's colours will land. Read BEFORE the push below, and
    // shifted by one when the splice merged its first block into the previous
    // design's last — the same shift the colours themselves take.
    const colorBase = colors.length - (mergesWithPrevious ? 1 : 0);
    const srcStitches = d.stitches || [];
    // ---- An element that contributes NOTHING splices nothing ------------
    //
    // Both splice records are conditional on the element having something to
    // splice them in front of, because each one is a claim about the stream.
    //
    // A `color` record is a BLOCK DELIMITER: `colors[k]` names the records
    // after the k-th one. So it is spliced only when this element OPENS a
    // block — it has a colour of its own (`first`), there is already a block
    // in front of it to delimit (`prev`), and that block is a different
    // thread. The old test was `i > 0 && !mergesWithPrevious`, which splices
    // one in front of an element with NO colours at all, and in front of the
    // first element that sews when everything before it was empty. Either way
    // the count of `color` records runs ahead of `colors`, and every block
    // after the stray one is named by the wrong entry — or by nothing.
    //
    // `buildLetteringDesign`'s `emptyWith` (digitize.js) is exactly that
    // element and it is reachable from the shipped UI, not just from tests:
    // a text element whose font has no glyph for any of its characters
    // (`hebrew_font_large` + "Emb") comes back with `colors: []` and a lone
    // `end` record, and `generateAll` passes it straight to this function.
    // Measured 2026-09-16 on a four-text project (red / unsupported / green /
    // blue) — with the empty element in the middle, against the same project
    // without it:
    //   colour records   2 -> 3      (`colors` stayed 3 either way)
    //   DST colour stops 3 -> 4      PEC 0xfe 0xb0 stops   2 -> 3
    //   EXP 0x80 0x01    2 -> 3      sewFacts.threadChanges 2 -> 3
    //   SVG strokes      #ff0000, #00ff00, #0000ff
    //                 -> #ff0000, #0000ff, #ff0000
    //   preview strands  red/green/blue -> red, then blue for BOTH the green
    //                    and the blue element
    // So it is a phantom rethread prompt on the machine in all three binary
    // formats AND the wrong thread on screen and in the SVG: the green
    // element is drawn in blue, and the blue one falls back to `colors[0]`
    // (svgexport.js's `colors[p.colorIndex] || colors[0]`) and exports red.
    //
    // The TRIM is a travel cut, so it needs the needle to actually travel:
    // something already emitted to travel FROM, and a record of this
    // element's own to travel TO. An element with neither costs a cut, a
    // `trims` count on the review card, and a stop on machines that pause
    // there — for a journey of zero length.
    //
    // For any element with a colour and a predecessor that sewed, both tests
    // reduce to the old ones, so nothing about a normal project moves.
    const contributes = srcStitches.some((s) => s.type !== "end");
    const last = stitches[stitches.length - 1] || { x: 0, y: 0 };
    if (stitches.length > 0 && contributes) stitches.push({ x: last.x, y: last.y, type: "trim" });
    if (!!first && !!prev && !mergesWithPrevious) stitches.push({ x: last.x, y: last.y, type: "color" });
    // The splice records are in; everything this design contributes starts
    // here. `dropped` is the running delta the `end` strip opens up.
    const base = stitches.length;
    // src index -> combined index, or -1 for a record that was dropped. Built
    // only when there is an index to remap, since it costs one entry per
    // stitch of every element.
    const at = runs ? new Int32Array(srcStitches.length) : null;
    let dropped = 0, sewn = 0;
    for (let k = 0; k < srcStitches.length; k++) {
      const s = srcStitches[k];
      if (s.type === "end") {
        if (at) at[k] = -1;
        dropped++;
        continue;
      }
      if (at) at[k] = base + k - dropped;
      if (s.type === "stitch") sewn++;
      stitches.push(s);
    }
    if (runs) {
      if (Array.isArray(d.runs)) runs = remapSpans(runs, d.runs, at, colorBase, (d.colors || []).length);
      else if (sewn > 0) runs = null;   // it sewed and said nothing about it
    }
    // When the splice carried no colour change, this design's first block is
    // a continuation of the previous one — the colours array has to lose the
    // duplicate with it, or `colors[i]` stops naming block i.
    const own = d.colors || [];
    for (let c = mergesWithPrevious ? 1 : 0; c < own.length; c++) colors.push(own[c]);
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
  // Absent, not empty, when there is nothing trustworthy to say — `[]` would
  // read as "this design contains no runs" and a renderer keying off the
  // index would draw nothing over a design full of stitches.
  if (runs) combined.runs = runs;
  if (haveDebug) combined._debug = { nSatin, nFill, nTrims };
  return combined;
}

// One element's spans, moved onto the combined record array. Returns the
// accumulator with this element's spans appended, or `null` to abandon the
// whole index — which is what happens the moment a span does not describe
// what it claims to, because half an index is indistinguishable from a whole
// one to every reader.
function remapSpans(acc, spans, at, colorBase, colorCount) {
  if (!Array.isArray(spans)) return null;
  for (const s of spans) {
    const i0 = at[s.i0];
    const i1 = at[s.i1];
    // -1 is a record that was stripped, undefined an index off the end of the
    // element's own stitches. Either means the span was not describing this
    // array — a span covers `stitch` records only and none of those are ever
    // dropped here, so neither can happen on a well-formed input.
    if (!(i0 >= 0) || !(i1 >= 0) || i1 < i0) return null;
    // The strip cannot reach INSIDE a span (no `end` record sits between two
    // stitches of one run), so a span's length has to survive the move. If it
    // did not, the index is describing some other array.
    if (i1 - i0 !== s.i1 - s.i0) return null;
    if (!(s.block >= 0) || s.block >= colorCount) return null;
    const block = colorBase + s.block;
    if (block < 0) return null;
    acc.push({ i0, i1, kind: s.kind, shape: s.shape, role: s.role, block });
  }
  return acc;
}

// Two colour entries name the same thread. Compared on r/g/b alone: `name`
// is display text (the lettering builder labels every block "Color 1", the
// import builder numbers them per element), so two entries that sew
// identically can carry different names and must still merge.
function sameThread(a, b) {
  return a.r === b.r && a.g === b.g && a.b === b.b;
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
