// Cross-validation harness: browser PES / EXP / DST encoders vs. pystitch.
//
// Encodes a small ASYMMETRIC fixture design (asymmetry is essential — a
// symmetric design hides axis flips) through the real browser encoders
// (src/pes.js, src/exp.js, src/dst.js — the exact modules the Studio's
// exporters.js invokes), then decodes the bytes with pystitch (an
// independent, standard-conformant implementation, via
// tools/crossval_decode.py) and measures what a third-party reader sees:
//
//   - stitch coordinates: best-fit dihedral transform (identity / flips /
//     transpositions) + translation + residual, vs. the expected mapping.
//     A correct encoder measures "identity": pystitch's internal
//     convention is +Y down, the Design model is +Y up, so the expected
//     decoded point for a design stitch (x, y) is exactly (x, -y).
//   - color count / color-change count, trims, jumps
//   - design extents
//
// DST runs through the same harness as a CONTROL: it must show the known,
// documented axis transposition (docs/dst-axis-verdict-2026-07-31.md). If it
// doesn't, the harness is broken — not the codec vindicated.
//
// Usage:
//   node tools/crossval-stitch-formats.mjs            # human-readable report
//   node tools/crossval-stitch-formats.mjs --json     # JSON verdict on stdout
//
// Python resolution: $EMB_CROSSVAL_PYTHON if set, else the digitizer venv
// next to this checkout (digitizer/.venv/bin/python or Scripts/python.exe),
// else `python3` on PATH. The interpreter must have pystitch installed.
// (It probed pyembroidery until 2026-08-21. The 2026-08-11 pystitch swap had
// removed that module, so every check skipped and the suite reported
// pass 0 / skipped 6 — green having asserted nothing.)
// Verdict doc: docs/pes-crossval-verdict-2026-08-04.md
// Pinning test: test/crossval-stitch-formats.test.js

import { createRequire } from "module";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { encodePES } = require(path.join(ROOT, "src/pes.js"));
const { encodeEXP } = require(path.join(ROOT, "src/exp.js"));
const { encodeDST } = require(path.join(ROOT, "src/dst.js"));

// ---- fixture ----------------------------------------------------------
// Design-model units: 0.1 mm, origin-relative, +Y UP. Deliberately
// asymmetric under all 8 dihedral transforms: a long bottom run (y=0), a
// short right edge, a jumped-to tail, and a second color block hugging the
// top-LEFT corner. 18 mm x 8 mm.
export function buildFixture({ withTrim = true } = {}) {
  const s = [];
  // color 0: bottom run, left to right
  for (let x = 0; x <= 180; x += 30) s.push({ x, y: 0, type: "stitch" });
  // right edge, upward
  s.push({ x: 180, y: 40, type: "stitch" });
  s.push({ x: 180, y: 80, type: "stitch" });
  // jump to an interior tail
  s.push({ x: 120, y: 60, type: "jump" });
  s.push({ x: 120, y: 60, type: "stitch" });
  s.push({ x: 90, y: 60, type: "stitch" });
  // trim (or plain jump for the no-trim variant), travel to top-left
  s.push({ x: 0, y: 80, type: withTrim ? "trim" : "jump" });
  s.push({ x: 0, y: 80, type: "color" });
  // color 1: small block at the top-left corner
  s.push({ x: 0, y: 80, type: "stitch" });
  s.push({ x: 30, y: 80, type: "stitch" });
  s.push({ x: 0, y: 50, type: "stitch" });
  s.push({ x: 30, y: 50, type: "stitch" });
  s.push({ x: 30, y: 50, type: "end" });
  return {
    label: "CROSSVAL",
    stitches: s,
    colors: [
      { r: 200, g: 30, b: 30, name: "Red" },
      { r: 30, g: 60, b: 200, name: "Blue" },
    ],
    widthMM: 18,
    heightMM: 8,
    stitchCount: s.filter((t) => (t.type || "stitch") === "stitch").length,
    colorCount: 2,
  };
}

// Expected pystitch view of the fixture's needle-down points: (x, -y).
export function expectedPyembStitches(design) {
  return design.stitches
    .filter((t) => (t.type || "stitch") === "stitch")
    .map((t) => [t.x, -t.y]);
}

// ---- transform classification ----------------------------------------
// The 8 dihedral transforms of the plane, applied to the EXPECTED points.
// "identity" = encoder is standard-conformant.
export const TRANSFORMS = {
  identity: ([u, v]) => [u, v],
  "flip-x": ([u, v]) => [-u, v],
  "flip-y": ([u, v]) => [u, -v],
  rot180: ([u, v]) => [-u, -v],
  transpose: ([u, v]) => [v, u],
  rot90: ([u, v]) => [-v, u],
  rot270: ([u, v]) => [v, -u],
  "anti-transpose": ([u, v]) => [-v, -u],
};

// Best transform T (+ translation) with actual[i] ~= T(expected[i]) + d.
// Compared index-by-index over the common prefix length; count mismatches
// are reported, not hidden.
export function classifyTransform(expected, actual) {
  const n = Math.min(expected.length, actual.length);
  if (n === 0) {
    return { transform: "none", rms: null, maxErr: null, offset: null, compared: 0 };
  }
  let best = null;
  for (const [name, fn] of Object.entries(TRANSFORMS)) {
    const t = expected.map(fn);
    // translation = mean residual, rounded to integer units
    let sx = 0, sy = 0;
    for (let i = 0; i < n; i++) {
      sx += actual[i][0] - t[i][0];
      sy += actual[i][1] - t[i][1];
    }
    const dx = Math.round(sx / n);
    const dy = Math.round(sy / n);
    let sumSq = 0, maxErr = 0;
    for (let i = 0; i < n; i++) {
      const ex = actual[i][0] - t[i][0] - dx;
      const ey = actual[i][1] - t[i][1] - dy;
      const e = Math.hypot(ex, ey);
      sumSq += e * e;
      if (e > maxErr) maxErr = e;
    }
    const rms = Math.sqrt(sumSq / n);
    if (!best || rms < best.rms) {
      best = { transform: name, rms, maxErr, offset: [dx, dy], compared: n };
    }
  }
  best.rms = +best.rms.toFixed(3);
  best.maxErr = +best.maxErr.toFixed(3);
  return best;
}

// ---- python bridge ----------------------------------------------------
export function resolvePython() {
  const candidates = [];
  if (process.env.EMB_CROSSVAL_PYTHON) candidates.push(process.env.EMB_CROSSVAL_PYTHON);
  candidates.push(
    path.join(ROOT, "digitizer", ".venv", "bin", "python"),
    path.join(ROOT, "digitizer", ".venv", "Scripts", "python.exe"),
    // worktree checkouts share the main repo's venv
    path.resolve(ROOT, "../../..", "digitizer", ".venv", "bin", "python"),
    path.resolve(ROOT, "../../..", "digitizer", ".venv", "Scripts", "python.exe"),
    "python3"
  );
  for (const p of candidates) {
    try {
      const r = spawnSync(p, ["-c", "import pystitch"], { timeout: 30000 });
      if (r.status === 0) return p;
    } catch {
      /* try next */
    }
  }
  return null;
}

function pyDecode(python, files) {
  const r = spawnSync(python, [path.join(ROOT, "tools", "crossval_decode.py"), ...files], {
    encoding: "utf8",
    timeout: 120000,
    maxBuffer: 64 * 1024 * 1024,
  });
  if (r.status !== 0) {
    throw new Error("crossval_decode.py failed: " + (r.stderr || r.error || "unknown"));
  }
  return JSON.parse(r.stdout);
}

// ---- harness ----------------------------------------------------------
export function runCrossval({ python = resolvePython(), keepDir = null } = {}) {
  if (!python) {
    throw new Error(
      "No python with pystitch found (set EMB_CROSSVAL_PYTHON or create digitizer/.venv)"
    );
  }
  const dir = keepDir || fs.mkdtempSync(path.join(os.tmpdir(), "emb-crossval-"));
  fs.mkdirSync(dir, { recursive: true });

  const fixtures = {
    full: buildFixture({ withTrim: true }),
    notrim: buildFixture({ withTrim: false }),
  };
  const files = [];
  for (const [variant, design] of Object.entries(fixtures)) {
    for (const [fmt, enc] of [["pes", encodePES], ["exp", encodeEXP], ["dst", encodeDST]]) {
      const file = path.join(dir, `crossval_${variant}.${fmt}`);
      fs.writeFileSync(file, Buffer.from(enc(design)));
      files.push(file);
    }
  }

  const decoded = pyDecode(python, files);

  const results = {};
  for (const [variant, design] of Object.entries(fixtures)) {
    const expected = expectedPyembStitches(design);
    for (const fmt of ["pes", "exp", "dst"]) {
      const d = decoded[`crossval_${variant}.${fmt}`];
      const key = `${fmt}.${variant}`;
      if (!d || d.error) {
        results[key] = { error: (d && d.error) || "no decode output" };
        continue;
      }
      const actual = d.stitches.filter((s) => s[2] === "STITCH").map((s) => [s[0], s[1]]);
      const fit = classifyTransform(expected, actual);
      results[key] = {
        expectedStitches: expected.length,
        decodedStitches: actual.length,
        fit,
        counts: d.counts,
        bounds: d.bounds,
        threads: d.threads,
        expectedColorChanges: 1,
        decodedColorChanges: d.counts.COLOR_CHANGE || 0,
        decodedTrims: d.counts.TRIM || 0,
        decodedSequinToggles: d.counts.SEQUIN_MODE || 0,
      };
    }
  }
  if (!keepDir) fs.rmSync(dir, { recursive: true, force: true });
  return { python, dir: keepDir, results };
}

function fmtReport(results) {
  const lines = [];
  for (const [key, r] of Object.entries(results)) {
    lines.push(`== ${key} ==`);
    if (r.error) {
      lines.push(`  ERROR: ${r.error}`);
      continue;
    }
    const f = r.fit;
    lines.push(
      `  stitches: expected ${r.expectedStitches}, decoded ${r.decodedStitches}` +
        (r.decodedStitches !== r.expectedStitches ? "  << COUNT MISMATCH" : "")
    );
    lines.push(
      `  best-fit transform: ${f.transform}  (rms ${f.rms}, max ${f.maxErr}, ` +
        `offset [${f.offset}], over ${f.compared} pts)` +
        (f.transform !== "identity" || f.rms > 0.5 ? "  << NOT CLEAN" : "  (clean)")
    );
    lines.push(`  commands seen by pystitch: ${JSON.stringify(r.counts)}`);
    lines.push(
      `  color changes: expected ${r.expectedColorChanges}, decoded ${r.decodedColorChanges}` +
        (r.decodedSequinToggles ? `  (plus ${r.decodedSequinToggles} spurious SEQUIN_MODE)` : "")
    );
    lines.push(`  bounds (py, +Y down): ${JSON.stringify(r.bounds)}`);
    if (r.threads.length) lines.push(`  threads: ${r.threads.join(", ")}`);
  }
  return lines.join("\n");
}

const isMain =
  process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const json = process.argv.includes("--json");
  const keep = process.argv.includes("--keep")
    ? path.join(ROOT, "scratch_crossval")
    : null;
  const { python, results } = runCrossval({ keepDir: keep });
  if (json) {
    console.log(JSON.stringify({ python, results }, null, 2));
  } else {
    console.error(`python: ${python}`);
    if (keep) console.error(`encoded files kept in: ${keep}`);
    console.log(fmtReport(results));
  }
}
