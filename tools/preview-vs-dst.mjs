// Does the Studio's PREVIEW match the file the customer downloads?
//
// The crossval harness next door asks whether a third-party reader sees the
// design's stitch COORDINATES where the design put them. That is not the same
// question. A file can carry every stitch at the right place, in the right
// order, with the right extents, and still lay thread along a path nobody was
// shown — which is exactly what all three encoders did until 2026-09-20, when
// a split move clamped each axis independently and walked an L across a
// diagonal the preview drew straight. Counts matched, bounds matched, the
// crossval `long` fixture was AXIS-ALIGNED and so could not see it, and the
// Studio suite never compares a picture to a file at all.
//
// So this tool compares the two things the customer actually gets:
//
//   the PICTURE  `designToStrands(design)` — imported from app/src/lib, the
//                previewer's own module, not a copy. renderRealistic paints
//                exactly these segments (preview.js: strands in, strokes out),
//                so what this measures IS what is on screen.
//   the FILE     the bytes of encodeDST / encodeEXP / encodePES, read back
//                with pystitch — a third-party, standard-conformant reader,
//                never src/dstimport.js (CLAUDE.md footgun #1).
//
// and reports, per fixture and format:
//
//   orientation  which of the 8 dihedral transforms lines the file up with
//                the picture. A correct codec scores identity ~1.0 and
//                everything else ~0. (This is the axis question the 2026-09-08
//                fix settled; it is asserted here so it stays settled.)
//   stray        how far the file's thread wanders from the drawn line, in mm,
//                both directions. This is the number the dogleg moved: 0.41 mm
//                on a resized logo, 3.6 mm on a 30.6 mm diagonal, 0.00 after.
//   thread       sewn millimetres either side. A stitch quietly demoted to
//                travel shortens the file's thread; travel promoted to stitch
//                lengthens it. Neither moves a bounding box.
//
// Usage:
//   node tools/preview-vs-dst.mjs               # human-readable report
//   node tools/preview-vs-dst.mjs --json        # machine-readable verdict
//   node tools/preview-vs-dst.mjs --fixture dogleg
//
// Python resolution is the crossval harness's: $EMB_CROSSVAL_PYTHON, else the
// digitizer venv, else python3 on PATH. Pinning test:
// test/preview-vs-dst.test.js
import { createRequire } from "module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolvePython, pyDecode } from "./crossval-stitch-formats.mjs";
import { designToStrands } from "../app/src/lib/strands.js";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
globalThis.window = globalThis;
const { encodeDST } = require(path.join(ROOT, "src/dst.js"));
const { encodeEXP } = require(path.join(ROOT, "src/exp.js"));
const { encodePES } = require(path.join(ROOT, "src/pes.js"));
require(path.join(ROOT, "src/units.js"));
require(path.join(ROOT, "src/geometry.js"));
require(path.join(ROOT, "src/garments.js"));
require(path.join(ROOT, "src/dstimport.js"));
require(path.join(ROOT, "src/digitize.js"));
const fontbin = require(path.join(ROOT, "src/fontbin.js"));
const EMB = globalThis.EMB;

const UNITS_PER_MM = 10;

// ---- fixtures ---------------------------------------------------------
// Each one must contain a sewn segment the encoders have to SPLIT, or it
// cannot see the class of defect this tool exists for. `dogleg` is the
// regression case; the other two are the customer paths that reach it.

// Diagonals over one record, in both signs, plus travel that has to split too.
export function buildDoglegFixture() {
  const st = (x, y) => ({ x, y, type: "stitch" });
  const s = [
    st(0, 0), st(80, 0),
    st(140, 300),          // 30.6 mm diagonal: 3.6 mm off the line before the fix
    st(1140, 500),         // long run with a shallow rise
    st(1000, 180),
    { x: 200, y: 900, type: "jump" },
    st(200, 900), st(260, 1200), st(900, 1200),
    { x: 900, y: 1200, type: "end" },
  ];
  return {
    label: "DOGLEG", stitches: s, colors: [{ r: 20, g: 20, b: 20, name: "Black" }],
    stitchCount: s.filter((t) => (t.type || "stitch") === "stitch").length,
    colorCount: 1, widthMM: 114, heightMM: 120,
  };
}

// A real shipped font at a real garment size, with shipping defaults.
export function buildLetteringFixture() {
  const font = fontbin.decodeFontBin(
    fs.readFileSync(path.join(ROOT, "src/fonts/bin/manga_impact.embf"))
  );
  return EMB.buildLetteringDesign(font, "A", {
    garment: EMB.getGarment("left_chest"), pxPerMm: 8, emMm: 18,
    rgb: [25, 25, 25], pullCompMm: 0.2,
  });
}

// The path that actually reaches the split today: an imported or
// auto-digitized element RESIZED on the field. buildImportedDesign scales the
// stitch coordinates, so segments that fitted a record at the original size do
// not at the new one.
//
// 300 mm because THIS source needs it: the lettering fixture's longest sewn
// segment is 4.5 mm, so it only crosses 12.1 mm past ~2.7x. The Studio's own
// auto-digitized logo crosses at 250 mm (measured 2026-09-20: 24 sewn segments
// over one record, worst axis 15.6 mm, file thread 0.41 mm off the drawn line)
// — the number that matters is that the fixture REACHES the split, which
// test/preview-vs-dst.test.js asserts rather than assumes.
export function buildResizedFixture() {
  const src = buildLetteringFixture();
  const decoded = EMB.decodeDST(encodeDST(src));
  return EMB.buildImportedDesign(decoded, {
    garment: EMB.getGarment("full_back"), targetWidthMm: 300,
  });
}

export const FIXTURES = {
  dogleg: buildDoglegFixture,
  lettering: buildLetteringFixture,
  resized: buildResizedFixture,
};

// ---- geometry ---------------------------------------------------------
// pystitch's frame is +Y DOWN, the Design model's is +Y UP, so a design point
// (x, y) must read back as (x, -y). Everything below works in design frame.
// Sewn thread is STITCH records and nothing else: a JUMP or a TRIM is the
// needle up. Inlined rather than parameterised, because widening it would
// silently redefine every number below it — including the thread length that
// is the tell for a stitch quietly demoted to travel.
function fileSegments(records) {
  const segs = [];
  let prev = null;
  for (const [x, y, cmd] of records) {
    if (cmd !== "STITCH") { prev = null; continue; }
    const p = [x, -y];
    if (prev) segs.push([prev[0], prev[1], p[0], p[1]]);
    prev = p;
  }
  return segs;
}

function travelSegments(records) {
  const out = [];
  let prev = null;
  for (const [x, y, cmd] of records) {
    if (cmd === "END") continue;
    const p = [x, -y];
    if (cmd === "JUMP" || cmd === "TRIM") {
      if (prev && (prev[0] !== p[0] || prev[1] !== p[1])) out.push([prev[0], prev[1], p[0], p[1]]);
      prev = p;
      continue;
    }
    if (cmd === "COLOR_CHANGE") { prev = null; continue; }
    prev = p;
  }
  return out;
}

function bbox(segs) {
  if (!segs.length) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const s of segs) {
    x0 = Math.min(x0, s[0], s[2]); x1 = Math.max(x1, s[0], s[2]);
    y0 = Math.min(y0, s[1], s[3]); y1 = Math.max(y1, s[1], s[3]);
  }
  return [x0, y0, x1, y1];
}

function threadUnits(segs) {
  let t = 0;
  for (const s of segs) t += Math.hypot(s[2] - s[0], s[3] - s[1]);
  return t;
}

// A uniform grid over one segment set, so "how far is this point from that
// thread" is a local lookup rather than a scan. Segments here are at most one
// record long, so a 64-unit cell keeps each one in a handful of cells.
const CELL = 64;
function grid(segs) {
  const m = new Map();
  segs.forEach((s, i) => {
    const cx0 = Math.floor(Math.min(s[0], s[2]) / CELL), cx1 = Math.floor(Math.max(s[0], s[2]) / CELL);
    const cy0 = Math.floor(Math.min(s[1], s[3]) / CELL), cy1 = Math.floor(Math.max(s[1], s[3]) / CELL);
    for (let cx = cx0; cx <= cx1; cx++) {
      for (let cy = cy0; cy <= cy1; cy++) {
        const k = cx + "," + cy;
        const b = m.get(k);
        if (b) b.push(i); else m.set(k, [i]);
      }
    }
  });
  return m;
}

function pointToSegment(px, py, s) {
  const vx = s[2] - s[0], vy = s[3] - s[1];
  const len2 = vx * vx + vy * vy;
  let t = len2 === 0 ? 0 : ((px - s[0]) * vx + (py - s[1]) * vy) / len2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (s[0] + vx * t), py - (s[1] + vy * t));
}

// The ring search stops at 6 cells (38.4 mm) and then scans everything. The
// fallback is not a nicety: a file that is transposed, displaced or in the
// wrong units — the 2026-09-08 class of defect, the one this tool is FOR — has
// its thread further away than any ring, and an Infinity here reaches `--json`
// as `null`, which reads exactly like a field that was never measured.
function nearest(px, py, segs, g) {
  let best = Infinity;
  for (let ring = 0; ring <= 6; ring++) {
    const cx = Math.floor(px / CELL), cy = Math.floor(py / CELL);
    for (let ix = cx - ring; ix <= cx + ring; ix++) {
      for (let iy = cy - ring; iy <= cy + ring; iy++) {
        if (ring > 0 && Math.abs(ix - cx) !== ring && Math.abs(iy - cy) !== ring) continue;
        const b = g.get(ix + "," + iy);
        if (!b) continue;
        for (const i of b) best = Math.min(best, pointToSegment(px, py, segs[i]));
      }
    }
    // Anything in a further ring is at least (ring)*CELL away, so once the
    // best beats that, searching wider cannot improve it.
    if (best <= ring * CELL) return best;
  }
  if (Number.isFinite(best)) return best;
  for (const s of segs) best = Math.min(best, pointToSegment(px, py, s));
  return best;
}

// The worst distance from one thread path to the other, sampling each segment
// at its ends and middle. Sub-unit rounding shows up here as ~0.05 mm; the
// dogleg showed up as millimetres.
function maxStrayUnits(from, to) {
  if (!from.length || !to.length) return null;
  const g = grid(to);
  let worst = 0;
  for (const s of from) {
    for (const [px, py] of [[s[0], s[1]], [(s[0] + s[2]) / 2, (s[1] + s[3]) / 2], [s[2], s[3]]]) {
      worst = Math.max(worst, nearest(px, py, to, g));
    }
  }
  return worst;
}

const DIHEDRAL = {
  identity: (x, y) => [x, y],
  flipX: (x, y) => [-x, y],
  flipY: (x, y) => [x, -y],
  rot180: (x, y) => [-x, -y],
  transpose: (x, y) => [y, x],
  rot90: (x, y) => [-y, x],
  rot270: (x, y) => [y, -x],
  antitranspose: (x, y) => [-y, -x],
};

// Which orientation lines the file up with the picture? Segment ENDPOINTS,
// matched exactly after aligning bounding-box minima — a translation is not an
// orientation error, and a split segment lands on the picture's line either
// way, so this is scored as "how much of the file lies on a drawn segment".
function orientationFit(previewSegs, fileSegs) {
  const pb = bbox(previewSegs);
  const table = {};
  if (!pb || !fileSegs.length) return { best: "none", table };
  const g = grid(previewSegs);
  for (const [name, fn] of Object.entries(DIHEDRAL)) {
    const t = fileSegs.map((s) => { const a = fn(s[0], s[1]), b = fn(s[2], s[3]); return [a[0], a[1], b[0], b[1]]; });
    const tb = bbox(t);
    const dx = pb[0] - tb[0], dy = pb[1] - tb[1];
    let on = 0;
    for (const s of t) {
      const a = nearest(s[0] + dx, s[1] + dy, previewSegs, g);
      const b = nearest(s[2] + dx, s[3] + dy, previewSegs, g);
      if (a < 1 && b < 1) on++;
    }
    table[name] = +(on / t.length).toFixed(6);
  }
  // "none" rather than the first key when nothing fits: `sort` is stable, so a
  // table of zeros would hand back `identity` — the reassuring answer — for a
  // file that lines up under no orientation at all. The crossval harness's
  // `classifyTransform` returns "none" for the same reason.
  const ranked = Object.entries(table).sort((a, b) => b[1] - a[1]);
  const best = ranked[0][1] > 0 ? ranked[0][0] : "none";
  return { best, table };
}

// ---- harness ----------------------------------------------------------
export function runPreviewVsDst({ python = resolvePython(), fixtures = Object.keys(FIXTURES), keepDir = null } = {}) {
  if (!python) {
    throw new Error("No python with pystitch found (set EMB_CROSSVAL_PYTHON or create digitizer/.venv)");
  }
  const dir = keepDir || fs.mkdtempSync(path.join(os.tmpdir(), "emb-preview-vs-"));
  fs.mkdirSync(dir, { recursive: true });

  const designs = {};
  const files = [];
  for (const name of fixtures) {
    const design = FIXTURES[name]();
    designs[name] = design;
    for (const [fmt, enc] of [["dst", encodeDST], ["exp", encodeEXP], ["pes", encodePES]]) {
      const file = path.join(dir, `pv_${name}.${fmt}`);
      fs.writeFileSync(file, Buffer.from(enc(design)));
      files.push(file);
    }
  }
  const decoded = pyDecode(python, files);

  const results = {};
  for (const name of fixtures) {
    const design = designs[name];
    const previewSegs = designToStrands(design).map((s) => [s.x0, s.y0, s.x1, s.y1]);
    const overRecord = previewSegs.filter((s) => Math.max(Math.abs(s[2] - s[0]), Math.abs(s[3] - s[1])) > 121).length;
    for (const fmt of ["dst", "exp", "pes"]) {
      const d = decoded[`pv_${name}.${fmt}`];
      const key = `${fmt}.${name}`;
      if (!d || d.error) { results[key] = { error: (d && d.error) || "no decode output" }; continue; }
      const fileSegs = fileSegments(d.stitches);
      const travel = travelSegments(d.stitches);
      const pb = bbox(previewSegs), fb = bbox(fileSegs);
      const off = pb && fb ? [pb[0] - fb[0], pb[1] - fb[1]] : [0, 0];
      const aligned = fileSegs.map((s) => [s[0] + off[0], s[1] + off[1], s[2] + off[0], s[3] + off[1]]);
      const fit = orientationFit(previewSegs, fileSegs);
      results[key] = {
        previewSegments: previewSegs.length,
        fileSegments: fileSegs.length,
        previewSegmentsOverOneRecord: overRecord,
        orientation: fit.best,
        orientationFit: fit.table,
        strayMm: {
          previewToFile: +((maxStrayUnits(previewSegs, aligned) || 0) / UNITS_PER_MM).toFixed(4),
          fileToPreview: +((maxStrayUnits(aligned, previewSegs) || 0) / UNITS_PER_MM).toFixed(4),
        },
        threadMm: {
          preview: +(threadUnits(previewSegs) / UNITS_PER_MM).toFixed(2),
          file: +(threadUnits(fileSegs) / UNITS_PER_MM).toFixed(2),
          delta: +((threadUnits(fileSegs) - threadUnits(previewSegs)) / UNITS_PER_MM).toFixed(2),
        },
        translationUnits: off,
        travelSegments: travel.length,
        counts: d.counts,
        sizeMm: fb ? [+((fb[2] - fb[0]) / UNITS_PER_MM).toFixed(1), +((fb[3] - fb[1]) / UNITS_PER_MM).toFixed(1)] : null,
      };
    }
  }
  if (!keepDir) fs.rmSync(dir, { recursive: true, force: true });
  return { python, dir: keepDir, results };
}

function report(results) {
  const lines = [];
  lines.push("fixture.format        prev segs  file segs  >1 rec  orient     stray mm  thread mm (prev/file)");
  for (const [key, r] of Object.entries(results)) {
    if (r.error) { lines.push(`${key.padEnd(22)} ERROR: ${r.error}`); continue; }
    lines.push(
      key.padEnd(22) +
      String(r.previewSegments).padStart(9) +
      String(r.fileSegments).padStart(11) +
      String(r.previewSegmentsOverOneRecord).padStart(8) +
      "  " + r.orientation.padEnd(10) +
      r.strayMm.fileToPreview.toFixed(3).padStart(8) +
      `   ${r.threadMm.preview} / ${r.threadMm.file}`
    );
  }
  return lines.join("\n");
}

// pathToFileURL, not a hand-built file:/// string: this repo lives under a
// path with a space in it, and only the URL form percent-encodes it — the
// string comparison silently never matched, so the CLI printed nothing.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const argv = process.argv.slice(2);
  const i = argv.indexOf("--fixture");
  const only = i >= 0 && argv[i + 1] ? [argv[i + 1]] : Object.keys(FIXTURES);
  const out = runPreviewVsDst({ fixtures: only });
  if (argv.includes("--json")) console.log(JSON.stringify(out, null, 2));
  else console.log(report(out.results));
}
