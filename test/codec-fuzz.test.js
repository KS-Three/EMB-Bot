// Seeded fuzz of the browser stitch codecs: DST, EXP and PES.
//
// Every other codec test in this repo is a hand-built fixture, and every
// codec defect this repo has shipped lived in a case no fixture had: the
// axis transposition (a writer and reader that agreed with each other and
// with nobody else, CLAUDE.md footgun 1), the L-shaped split no axis-aligned
// fixture could show (test/encoder-split.test.js), EXP's missing chain rule
// that no fixture with travel-into-a-run exposed (crossval `travel`). This
// file throws a few hundred seeded random designs at all three writers
// instead: long jumps that must split, colour changes that move and do not,
// trims at every distance, deltas pinned on every record boundary (PEC short
// form 63/64, DST 121/122, EXP 127/128, PEC long form 2047/2048), empty and
// one-stitch designs, and coordinates out at the PES int16 corners.
//
// THREE READINGS of every file, each against an expectation built from the
// DESIGN alone:
//
//   1. the repo's own record readers (dstimport.readDSTRecords,
//      readback.readEXPRecords / readPESRecords) — every record's kind in
//      order, every event landing where the design put it, every sewn split
//      on the straight line and inside the 121-unit sewability bar;
//   2. the import lane (`decodeDST`) and the export read-back the Studio
//      blocks downloads on (`verifyExport`);
//   3. pystitch, an independent standard reader, on the same bytes. This is
//      the leg that catches a codec that is consistent with ITSELF but not
//      with the format — exactly what the 09-08 DST axis bug was. It needs a
//      python with pystitch (the digitizer venv, $EMB_CROSSVAL_PYTHON, or a
//      `python3` that has it — CI's engine job installs one). It is skipped
//      on a developer box without one and is a FAILURE on CI, the same rule
//      test/crossval-stitch-formats.test.js states and for the same reason.
//
// The expectation does NOT call the encoders' splitSteps. It knows only the
// format rules: how far one record reaches, that a sewn move continues a run
// only when the record before it was sewn (the chain rule), that a sewn
// split lands within half a unit per axis of the line, and how each format
// spells a trim and a colour change. A writer that disagrees with those
// fails here whichever way its own code reads.
//
// On a failure the test shrinks the design (greedy one-event removal while
// the same check still fails) and prints the seed and the minimized stitch
// list, so the repro can be pasted straight into a regression test.

const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { encodeDST } = require("../src/dst.js");
const { encodeEXP } = require("../src/exp.js");
const { encodePES, nearestPecIndex, BROTHER_PEC_CHART } = require("../src/pes.js");
const { readDSTRecords, decodeDST } = require("../src/dstimport.js");
const { readEXPRecords, readPESRecords, verifyExport } = require("../src/readback.js");

const FORMATS = ["dst", "exp", "pes"];
const ENCODE = {
  dst: (d, o) => encodeDST(d, o),
  exp: (d) => encodeEXP(d),
  pes: (d) => encodePES(d),
};

// Units are 0.1 mm throughout. Per-record reach, per format: a TRAVEL record
// (jump, trim travel, the move into the first stitch of a run) may use all of
// it; a SEWN record that continues a run may use only SEWN.
const SEWN = 121;
const REACH = { dst: 121, exp: 127, pes: 2047 };

const DESIGNS = 300;     // per format; the same 300 designs go through all three
const COORD_LIMIT = 16383; // keeps every design inside PES's int16 extents

// ---- seeded generator ------------------------------------------------------

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Every record boundary of every format, and one either side.
const BOUNDARY = [
  0, 1, 2, 62, 63, 64, 65, 80, 81, 82, 120, 121, 122, 126, 127, 128, 129,
  241, 242, 243, 244, 253, 254, 255, 362, 363, 364, 365,
  2046, 2047, 2048, 2049, 4094, 4095, 4096,
];

function makeRng(seed) {
  const r = mulberry32(seed * 2654435761);
  const int = (lo, hi) => lo + Math.floor(r() * (hi - lo + 1));
  const pick = (arr) => arr[Math.floor(r() * arr.length)];
  const sign = () => (r() < 0.5 ? -1 : 1);
  // one axis of a delta; `far` biases toward travel-sized moves
  const delta = (far) => {
    const u = r();
    if (!far && u < 0.45) return int(-30, 30);
    if (u < 0.7) return sign() * pick(BOUNDARY);
    if (!far && u < 0.85) return int(-400, 400);
    return int(-5000, 5000);
  };
  return { r, int, pick, sign, delta };
}

const clamp = (v) => Math.max(-COORD_LIMIT, Math.min(COORD_LIMIT, v));

function randomColors(g, n) {
  const out = [];
  for (let i = 0; i < n; i++) out.push({ r: g.int(0, 255), g: g.int(0, 255), b: g.int(0, 255), name: "c" + i });
  return out;
}

function finish(g, label, stitches) {
  // the terminal sentinel: absent (lettering), on the last point, or
  // somewhere else entirely (buildImportedDesign puts it at the element's
  // offset) — all three must write nothing
  const u = g.r();
  if (u < 0.25 && stitches.length) {
    const last = stitches[stitches.length - 1];
    stitches.push({ x: last.x, y: last.y, type: "end" });
  } else if (u < 0.5) {
    stitches.push({ x: g.int(-3000, 3000), y: g.int(-3000, 3000), type: "end" });
  }
  const colorEvents = stitches.filter((s) => s.type === "color").length;
  const colors = g.r() < 0.1 ? [] : randomColors(g, colorEvents + 1);
  const opts = g.r() < 0.3 ? { jumpsPerTrim: g.pick([1, 2, 3, 4, 5, 10]) } : undefined;
  return { design: { label, stitches, colors }, opts };
}

function genDesign(seed) {
  const g = makeRng(seed);
  const label = "FUZZ" + seed;
  const cls = seed % 25;
  const s = [];

  if (cls === 0) {
    // empty, three ways: nothing at all, a bare sentinel, travel and no thread
    const v = seed % 3;
    if (v === 1) s.push({ x: 0, y: 0, type: "end" });
    if (v === 2) {
      let x = 0, y = 0;
      for (let i = g.int(1, 6); i > 0; i--) {
        x = clamp(x + g.delta(true)); y = clamp(y + g.delta(true));
        s.push({ x, y, type: g.pick(["jump", "trim", "color"]) });
      }
    }
    return { design: { label, stitches: s, colors: randomColors(g, 1) }, opts: undefined };
  }

  if (cls === 1) {
    // one stitch, maybe travelled to, maybe at the origin
    if (g.r() < 0.4) s.push({ x: 0, y: 0, type: "jump" });
    const at = g.r() < 0.3 ? [0, 0] : [clamp(g.delta(true)), clamp(g.delta(true))];
    s.push({ x: at[0], y: at[1], type: "stitch" });
    return finish(g, label, s);
  }

  if (cls === 2) {
    // the corners of the PES int16 box, travelled to and sewn between
    const corners = [[-COORD_LIMIT, -COORD_LIMIT], [COORD_LIMIT, -COORD_LIMIT], [COORD_LIMIT, COORD_LIMIT], [-COORD_LIMIT, COORD_LIMIT]];
    for (let i = g.int(2, 6); i > 0; i--) {
      const [cx, cy] = g.pick(corners);
      s.push({ x: cx, y: cy, type: g.pick(["jump", "trim", "stitch"]) });
      s.push({ x: cx, y: cy, type: "stitch" });
      if (g.r() < 0.5) s.push({ x: clamp(cx + g.delta(false)), y: clamp(cy + g.delta(false)), type: "stitch" });
    }
    return finish(g, label, s);
  }

  // a random walk; most designs are short so a failure shrinks fast
  const len = 1 + Math.floor(g.r() * g.r() * 150);
  let x = g.r() < 0.5 ? 0 : clamp(g.delta(true));
  let y = g.r() < 0.5 ? 0 : clamp(g.delta(true));
  for (let i = 0; i < len; i++) {
    const u = g.r();
    const type = u < 0.72 ? "stitch" : u < 0.82 ? "jump" : u < 0.9 ? "trim" : u < 0.96 ? "color" : "untyped";
    const far = type === "jump" || type === "trim";
    if (type === "color") {
      // a colour change usually sits on the needle; sometimes it carries a
      // move (DST writes that in the colour record, EXP and PES cannot)
      if (g.r() < 0.3) { x = clamp(x + g.delta(true)); y = clamp(y + g.delta(true)); }
      s.push({ x, y, type: "color" });
      continue;
    }
    x = clamp(x + g.delta(far));
    y = clamp(y + g.delta(far));
    // an untyped point is a stitch to every encoder (`st.type || "stitch"`)
    s.push(type === "untyped" ? { x, y } : { x, y, type });
  }
  return finish(g, label, s);
}

// ---- the expectation, from the design alone ---------------------------------

const recs = (dx, dy, lim) => Math.max(1, Math.ceil(Math.abs(dx) / lim), Math.ceil(Math.abs(dy) / lim));

function trimJumps(opts) {
  const v = opts && opts.jumpsPerTrim;
  return Number.isInteger(v) && v >= 1 && v <= 10 ? v : 3;
}

// One entry per design event: the record kinds it must produce, in order,
// where the needle must stand after them, and whether it continues a run.
function expectedSegments(design, fmt, opts) {
  const out = [];
  const reach = REACH[fmt];
  let px = 0, py = 0, prevSewn = false;
  for (const st of design.stitches || []) {
    const type = st.type || "stitch";
    if (type === "end") break;
    const x = st.x | 0, y = st.y | 0;
    const dx = x - px, dy = y - py;
    const rep = (k, n) => Array(n).fill(k);
    let kinds, moves = true;
    if (type === "stitch") {
      kinds = prevSewn
        ? rep("S", recs(dx, dy, SEWN))
        // travel into a run: jumps at the format's reach, then the stitch —
        // except EXP, whose stitch record is held to the sewability bar
        // even at the end of travel (Kent, 2026-10-07)
        : rep("J", recs(dx, dy, fmt === "exp" ? SEWN : reach) - 1).concat("S");
      out.push({ type, kinds, x, y, fromX: px, fromY: py, chained: prevSewn });
      prevSewn = true;
      px = x; py = y;
      continue;
    }
    if (type === "jump") kinds = rep("J", recs(dx, dy, reach));
    else if (type === "trim") {
      if (fmt === "dst") kinds = rep("J", Math.max(trimJumps(opts), recs(dx, dy, reach)));
      else if (fmt === "exp") kinds = ["T"].concat(dx || dy ? rep("J", recs(dx, dy, reach)) : []);
      else kinds = rep("J", recs(dx, dy, reach) - 1).concat("T");
    } else { // color
      if (fmt === "dst") kinds = rep("J", recs(dx, dy, reach) - 1).concat("C");
      else { kinds = ["C"]; moves = false; }
    }
    out.push({ type, kinds, x: moves ? x : px, y: moves ? y : py, chained: false });
    if (moves) { px = x; py = y; }
    prevSewn = false;
  }
  return out;
}

// Perpendicular distance of (qx,qy) from the segment (ax,ay)->(bx,by).
function stray(qx, qy, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy);
  if (len === 0) return Math.hypot(qx - ax, qy - ay);
  return Math.abs(dx * (qy - ay) - dy * (qx - ax)) / len;
}

// ---- reading 1: the repo's own record readers --------------------------------

function readRecords(bytes, fmt) {
  if (fmt === "dst") return readDSTRecords(bytes);
  if (fmt === "exp") return { records: readEXPRecords(bytes) };
  return { records: readPESRecords(bytes) };
}

// Returns null when the file says what the design says, else a description
// of the first disagreement.
function checkRepoReading(design, opts, fmt, bytes) {
  let read;
  try { read = readRecords(bytes, fmt); } catch (e) { return "reader threw: " + e.message; }
  if (fmt === "dst") {
    if (!read.ended) return "no DST end record";
    if (read.tail !== 0) return read.tail + " stray bytes after the DST end record";
    if (read.header.ST !== read.records.length + 1) return "DST header ST " + read.header.ST + " but " + (read.records.length + 1) + " records";
  }
  const rec = read.records;
  const segs = expectedSegments(design, fmt, opts);
  let i = 0;
  for (let e = 0; e < segs.length; e++) {
    const sg = segs[e];
    const got = rec.slice(i, i + sg.kinds.length);
    const kinds = got.map((r) => r.kind).join("");
    if (kinds !== sg.kinds.join("")) {
      return "event " + e + " (" + sg.type + " to " + sg.x + "," + sg.y + "): expected records " + sg.kinds.join("") + ", read " + kinds;
    }
    for (const r of got) {
      const lim = r.kind === "S" && sg.chained ? SEWN : REACH[fmt];
      if (Math.abs(r.dx) > lim || Math.abs(r.dy) > lim) return "event " + e + ": a " + r.kind + " record of " + r.dx + "," + r.dy + " exceeds " + lim;
      if (sg.chained && stray(r.x, r.y, sg.fromX, sg.fromY, sg.x, sg.y) > Math.SQRT1_2 + 1e-9) {
        return "event " + e + ": a sewn split lands at " + r.x + "," + r.y + ", off the line " + sg.fromX + "," + sg.fromY + " -> " + sg.x + "," + sg.y;
      }
    }
    const last = got[got.length - 1];
    if (last.x !== sg.x || last.y !== sg.y) {
      return "event " + e + " (" + sg.type + "): the needle stands at " + last.x + "," + last.y + ", not " + sg.x + "," + sg.y;
    }
    i += sg.kinds.length;
  }
  if (i !== rec.length) return (rec.length - i) + " records after the design's last event";
  return null;
}

// What a run of consecutive DST jump records means to each DST reader.
// Runs are broken by any stitch or colour record.
function dstJumpRuns(kinds) {
  const runs = [];
  let run = 0, before = "start";
  for (const k of kinds) {
    if (k === "J") { run++; continue; }
    if (run) runs.push({ len: run, before, trailing: false });
    run = 0;
    before = k;
  }
  if (run) runs.push({ len: run, before, trailing: true });
  return runs;
}

// ---- reading 2: the import lane and the download read-back -------------------

function checkProductReaders(design, opts, fmt, bytes) {
  const v = verifyExport(design, bytes, fmt, opts);
  if (!v.ok) return "verifyExport refused it: " + v.failed.map((c) => c.check + " expected " + c.expected + " read " + c.read).join("; ");
  if (fmt !== "dst") return null;

  const rec = readDSTRecords(bytes).records;
  const sewn = rec.filter((r) => r.kind === "S");
  let dec;
  try { dec = decodeDST(bytes); } catch (e) {
    if (!sewn.length && /No stitches/.test(e.message)) return null; // stitchless: refused by name
    return "decodeDST threw: " + e.message;
  }
  if (!sewn.length) return "decodeDST accepted a file with no stitches";
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const r of sewn) { x0 = Math.min(x0, r.x); x1 = Math.max(x1, r.x); y0 = Math.min(y0, r.y); y1 = Math.max(y1, r.y); }
  const cx = Math.round((x0 + x1) / 2), cy = Math.round((y0 + y1) / 2);
  const imp = dec.stitches.filter((s) => s.type === "stitch");
  if (imp.length !== sewn.length) return "decodeDST read " + imp.length + " stitches, the records hold " + sewn.length;
  for (let k = 0; k < sewn.length; k++) {
    if (imp[k].x + cx !== sewn[k].x || imp[k].y + cy !== sewn[k].y) return "decodeDST stitch " + k + " at " + (imp[k].x + cx) + "," + (imp[k].y + cy) + ", record at " + sewn[k].x + "," + sewn[k].y;
  }
  const colors = rec.filter((r) => r.kind === "C").length;
  if (dec.colorCount !== colors + 1) return "decodeDST colorCount " + dec.colorCount + ", file has " + colors + " changes";
  const runs = dstJumpRuns(rec.map((r) => r.kind)).filter((r) => !r.trailing);
  const trims = runs.filter((r) => r.len >= 3).length, jumps = runs.length - trims;
  if (dec.trimCount !== trims || dec.jumpCount !== jumps) return "decodeDST read " + dec.trimCount + " trims / " + dec.jumpCount + " jumps, runs say " + trims + " / " + jumps;
  return null;
}

// ---- reading 3: pystitch ------------------------------------------------------

// What pystitch must report for this file, derived from the repo reading
// (which reading 1 has already held to the design). pystitch is +y down.
function pystitchExpectation(fmt, rec, design) {
  const flip = (r) => [r.x, -r.y];
  const stitch = rec.filter((r) => r.kind === "S").map(flip);
  const color = rec.filter((r) => r.kind === "C").map(flip);
  let jump, trims;
  if (fmt === "dst") {
    // pystitch's DstReader also CLIPS jumps (interpolate_trims, clipping on):
    // whenever a run's running displacement returns to zero, the jumps so far
    // are deleted. A zero-length trim (three 0,0 jumps) keeps its TRIM and
    // loses its jumps; a zero-length design jump vanishes. Nothing moves, so
    // nothing is lost — measured on the first run of this file, where it was
    // every one of the DST JUMP-count disagreements.
    jump = [];
    let pending = [], cx = 0, cy = 0;
    const flush = () => { jump.push(...pending); pending = []; cx = 0; cy = 0; };
    for (const r of rec) {
      if (r.kind !== "J") { flush(); continue; }
      pending.push(flip(r));
      cx += r.dx; cy += r.dy;
      if (cx === 0 && cy === 0) pending = [];
    }
    flush();
    // pystitch's DstReader reads >=3 jumps as a trim only after thread has
    // been laid since the start or the last colour change
    // (EmbPattern.interpolate_trims, `trimmed`), a reader convention and not
    // a defect: a colour change already cuts.
    trims = dstJumpRuns(rec.map((r) => r.kind)).filter((r) => r.len >= 3 && r.before === "S").length;
  } else if (fmt === "exp") {
    jump = rec.filter((r) => r.kind === "J").map(flip);
    trims = rec.filter((r) => r.kind === "T").length;
  } else {
    // a PEC trim record is read as TRIM then a move to its end point
    jump = rec.filter((r) => r.kind === "J" || r.kind === "T").map(flip);
    trims = rec.filter((r) => r.kind === "T").length;
  }
  if (fmt !== "pes") return { stitch, jump, color, stop: [], trims, threads: null };
  const pec = pesColorReading(rec, pecIndices(design));
  return {
    stitch, jump, trims,
    color: pec.changes.filter((c) => !c.stop).map((c) => flip(c.r)),
    stop: pec.changes.filter((c) => c.stop).map((c) => flip(c.r)),
    threads: pec.threads.map((i) => "#" + BROTHER_PEC_CHART[i].map((v) => v.toString(16).padStart(2, "0")).join("")),
  };
}

// The PEC chart index pes.js must write for each of the design's colours,
// from the design: an explicit paletteIndex, else the nearest chart entry,
// else 1, 2, 3 ... (a design with no colours writes a one-entry table).
function pecIndices(design) {
  const colors = design.colors || [];
  const out = [];
  for (let i = 0; i < Math.max(1, colors.length); i++) {
    const c = colors[i] || {};
    out.push(typeof c.paletteIndex === "number" ? c.paletteIndex
      : typeof c.r === "number" ? nearestPecIndex(c.r, c.g, c.b) : (i % 64) + 1);
  }
  return out;
}

// pystitch's PesReader then runs EmbPattern.interpolate_duplicate_color_as_stop:
// a colour change into a block whose thread is the SAME chart entry as the
// block before is rewritten as a STOP and the duplicate thread dropped. Two
// design colours that snap to one Brother chart thread therefore read as a
// pause, not a change — the "nearest-chart snapping is not lossless" gap
// crossval-stitch-formats.test.js already records, not a stream defect. This
// replays that function on the records, line for line, so the check stays
// exact: only blocks that sew advance the thread index, and a design with
// more colour changes than colours stops being rewritten where pystitch's
// own IndexError stops it.
function pesColorReading(rec, indices) {
  const th = indices.slice();
  const changes = [];
  let ti = 0, init = true, last = null, done = false;
  for (const r of rec) {
    if (r.kind === "C") {
      const c = { r, stop: false };
      changes.push(c); // after an early return, still a plain colour change
      if (!done) { init = true; last = c; }
      continue;
    }
    if (done || r.kind !== "S" || !init) continue;
    init = false;
    if (last !== null && ti !== 0) {
      if (ti >= th.length) { done = true; continue; } // pystitch: IndexError -> return
      if (th[ti - 1] === th[ti]) { th.splice(ti, 1); last.stop = true; continue; }
    }
    ti++;
  }
  return { changes, threads: th };
}

function checkPystitch(fmt, rec, design, d) {
  if (!d) return "pystitch produced no output for this file";
  if (d.error) return "pystitch could not read it: " + d.error;
  const want = pystitchExpectation(fmt, rec, design);
  const of = (name) => d.stitches.filter((s) => s[2] === name).map((s) => [s[0], s[1]]);
  const other = d.stitches.filter((s) => !["STITCH", "JUMP", "TRIM", "COLOR_CHANGE", "STOP", "END"].includes(s[2]));
  if (other.length) return "pystitch read commands the writer never meant: " + JSON.stringify(other.slice(0, 3));
  if (want.threads && JSON.stringify(d.threads) !== JSON.stringify(want.threads)) {
    return "pystitch read threads " + JSON.stringify(d.threads) + ", the design's chart threads are " + JSON.stringify(want.threads);
  }
  for (const [name, list] of [["STITCH", want.stitch], ["JUMP", want.jump], ["COLOR_CHANGE", want.color], ["STOP", want.stop]]) {
    const got = of(name);
    if (got.length !== list.length) return "pystitch read " + got.length + " " + name + ", the file holds " + list.length;
    for (let k = 0; k < got.length; k++) {
      if (got[k][0] !== list[k][0] || got[k][1] !== list[k][1]) {
        return "pystitch " + name + " " + k + " at " + got[k] + ", the repo reader at " + list[k];
      }
    }
  }
  const trims = of("TRIM").length;
  if (trims !== want.trims) return "pystitch read " + trims + " TRIM, expected " + want.trims;
  return null;
}

let pyHarness = null;
async function pythonWithPystitch() {
  if (!pyHarness) pyHarness = await import("../tools/crossval-stitch-formats.mjs");
  return { python: pyHarness.resolvePython(), pyDecode: pyHarness.pyDecode };
}

// ---- shrinking ----------------------------------------------------------------

// Two failures are "the same check" when their messages match with the
// numbers taken out (the event index and the coordinates move as it shrinks).
const failureKey = (why) => String(why).replace(/-?\d+/g, "#");

// Greedy one-event removal while `fails` still reports the same check.
function shrink(design, fails) {
  let st = design.stitches.slice();
  let changed = true;
  while (changed) {
    changed = false;
    for (let k = 0; k < st.length; k++) {
      const trial = st.slice(0, k).concat(st.slice(k + 1));
      if (fails({ ...design, stitches: trial })) { st = trial; changed = true; break; }
    }
  }
  return { ...design, stitches: st };
}

// The same shrink against pystitch, one python spawn per round: every
// one-event-shorter candidate is written and decoded together, and the first
// that still fails the same way is kept. Runs only on a failure.
function shrinkWithPystitch(python, pyDecode, dir, fmt, f, why) {
  const verdict = (designs) => {
    const paths = [], recs = [];
    designs.forEach((d, k) => {
      try {
        const bytes = ENCODE[fmt](d, f.opts);
        if (checkRepoReading(d, f.opts, fmt, bytes)) { paths.push(null); recs.push(null); return; }
        const p = path.join(dir, `shrink_${k}.${fmt}`);
        fs.writeFileSync(p, Buffer.from(bytes));
        paths.push(p);
        recs.push(readRecords(bytes, fmt).records);
      } catch { paths.push(null); recs.push(null); }
    });
    const live = paths.filter(Boolean);
    const decoded = live.length ? pyDecode(python, live) : {};
    return paths.map((p, k) => (p ? checkPystitch(fmt, recs[k], designs[k], decoded[path.basename(p)]) : null));
  };
  let cur = f.design, curWhy = why;
  for (let round = 0; round < 80; round++) {
    const cands = cur.stitches.map((_, k) => ({ ...cur, stitches: cur.stitches.filter((_, j) => j !== k) }));
    if (!cands.length) break;
    const whys = verdict(cands);
    const k = whys.findIndex((w) => w && failureKey(w) === failureKey(why));
    if (k < 0) break;
    cur = cands[k]; curWhy = whys[k];
  }
  return { design: cur, why: curWhy };
}

function report(seed, fmt, opts, design, why) {
  return "seed " + seed + " " + fmt.toUpperCase() + (opts ? " opts " + JSON.stringify(opts) : "") + ": " + why +
    "\n  minimized stitches: " + JSON.stringify(design.stitches) +
    "\n  colors: " + design.colors.length;
}

// ---- the corpus ---------------------------------------------------------------

const corpus = [];
for (let seed = 1; seed <= DESIGNS; seed++) corpus.push({ seed, ...genDesign(seed) });

test("codec fuzz: the generator covers what it claims to", (t) => {
  // A fuzz corpus that silently stopped producing the hard cases would pass
  // forever. Count them instead of trusting the weights.
  const tally = { empty: 0, single: 0, split: 0, longJump: 0, colorMove: 0, trim: 0, pecBoundary: 0, sentinelOff: 0, jpt: 0 };
  for (const { design, opts } of corpus) {
    const ev = design.stitches.filter((s) => s.type !== "end");
    if (!ev.some((s) => (s.type || "stitch") === "stitch")) tally.empty++;
    if (ev.length === 1 && (ev[0].type || "stitch") === "stitch") tally.single++;
    if (opts) tally.jpt++;
    let px = 0, py = 0, prev = null;
    for (const s of ev) {
      const ty = s.type || "stitch", dx = s.x - px, dy = s.y - py, m = Math.max(Math.abs(dx), Math.abs(dy));
      if (ty === "stitch" && prev === "stitch" && m > SEWN) tally.split++;
      if (ty === "jump" && m > REACH.pes) tally.longJump++;
      if (ty === "color" && m > 0) tally.colorMove++;
      if (ty === "trim") tally.trim++;
      if (m === 63 || m === 64 || Math.abs(dx) === 2047 || Math.abs(dx) === 2048) tally.pecBoundary++;
      px = s.x; py = s.y;
      prev = ty;
    }
    const end = design.stitches.find((s) => s.type === "end");
    const last = ev[ev.length - 1];
    if (end && (!last || end.x !== last.x || end.y !== last.y)) tally.sentinelOff++;
  }
  t.diagnostic("corpus: " + JSON.stringify(tally));
  for (const [k, v] of Object.entries(tally)) assert.ok(v >= 5, "the corpus has only " + v + " designs/events of kind " + k);
});

const files = {}; // fmt -> [{ seed, design, opts, bytes, rec }]

for (const fmt of FORMATS) {
  test(`codec fuzz: ${DESIGNS} ${fmt.toUpperCase()} files read back as the design`, (t) => {
    const failures = [];
    files[fmt] = [];
    let records = 0;
    for (const { seed, design, opts } of corpus) {
      const bytes = ENCODE[fmt](design, opts);
      const fails = (d) => {
        let b;
        try { b = ENCODE[fmt](d, opts); } catch (e) { return "writer threw: " + e.message; }
        return checkRepoReading(d, opts, fmt, b) || checkProductReaders(d, opts, fmt, b);
      };
      const why = fails(design);
      if (why) {
        const min = shrink(design, (d) => { const w = fails(d); return w && failureKey(w) === failureKey(why); });
        failures.push(report(seed, fmt, opts, min, fails(min) || why));
        continue;
      }
      const rec = readRecords(bytes, fmt).records;
      records += rec.length;
      files[fmt].push({ seed, design, opts, bytes, rec });
    }
    t.diagnostic(`${fmt}: ${DESIGNS} designs, ${records} records read, ${failures.length} mismatches`);
    assert.deepStrictEqual(failures, [], failures.join("\n\n"));
  });
}

test("codec fuzz: pystitch reads every file the way the repo reader does", async (t) => {
  const { python, pyDecode } = await pythonWithPystitch();
  if (!python) {
    if (process.env.CI) {
      throw new Error("no python with pystitch, and CI is set: the independent cross-read must run on CI (see the engine job's pystitch install). Do not allow the skip.");
    }
    t.diagnostic("pystitch cross-read SKIPPED: no python with pystitch on this machine");
    t.skip("no python with pystitch available");
    return;
  }
  for (const fmt of FORMATS) assert.ok(files[fmt], fmt + " corpus was not built (its own test failed first)");

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "emb-codec-fuzz-"));
  const failures = [];
  try {
    const paths = [];
    for (const fmt of FORMATS) {
      for (const f of files[fmt]) {
        f.file = path.join(dir, `fuzz_${f.seed}.${fmt}`);
        fs.writeFileSync(f.file, Buffer.from(f.bytes));
        paths.push(f.file);
      }
    }
    const decoded = pyDecode(python, paths);
    for (const fmt of FORMATS) {
      let n = 0, shrunk = 0, stops = 0;
      for (const f of files[fmt]) {
        n++;
        const dd = decoded[path.basename(f.file)];
        if (dd && dd.stitches) stops += dd.stitches.filter((s) => s[2] === "STOP").length;
        const why = checkPystitch(fmt, f.rec, f.design, decoded[path.basename(f.file)]);
        if (!why) continue;
        // minimize the first two per format; the rest are reported as found
        if (shrunk++ < 2) {
          const min = shrinkWithPystitch(python, pyDecode, dir, fmt, f, why);
          failures.push(report(f.seed, fmt, f.opts, min.design, min.why));
        } else failures.push(report(f.seed, fmt, f.opts, f.design, why + " (not minimized)"));
      }
      t.diagnostic(`${fmt}: pystitch cross-read ${n} files` + (stops ? `, ${stops} colour changes read as STOP (adjacent colours on one chart thread)` : ""));
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
  t.diagnostic(`pystitch (${python}): ${failures.length} mismatches`);
  assert.deepStrictEqual(failures, [], failures.slice(0, 5).join("\n\n"));
});
