// What `cutFloats` changes on the manual lane, with `fillColumns` already on
// there (#662): the same shapes built with the flag off and on, every thread
// counted.
//
//   node tools/cut-floats-sheet.mjs
//
// Prints the table docs/cut-floats-manual-2026-10-08.md carries.
//
// Built the way the Studio's manual lane calls buildQualityDesign
// (app/src/lib/generate.js): a garment, its fabric preset, `darkOnTop: false`,
// underlay on, `fillColumns: true`. The shapes are tools/fill-columns-sheet.mjs's
// four, its 36-hole badge, and a plain square, each under six garments (so six
// fabric presets).
//
// THREAD, not penetrations, as fill-columns-sheet.mjs counts it: a move lays
// thread unless the thread has been cut since the last penetration, so a
// `jump` after a stitch is a float on the cloth.
//
// A CUT NOBODY ASKED FOR: a float the DST writer lays as three or more jump
// records (dst.jumpRecords), with no `trim` in the stream. A DST machine cuts
// there anyway, and `ties` cannot lock what the stream does not call a cut.
//
// LEAVES THE FILL: a float longer than a stitch (4 mm) with a point, sampled
// every 0.25 mm, more than 1 mm outside the drawn shape or inside one of its
// holes -- the #662 audit's measure, with room for pull compensation (up to
// 0.6 mm here), which puts the rim's own thread outside the drawing.
//
// NEW THREAD: a sewn or floated segment in the "on" stream that is not in the
// "off" one. `cutFloats` moves no stitch, so anything here would be thread
// laid where none was before -- including travel over sewn rows.
import "./_help.mjs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const DG = require("../src/digitize.js");
const FAB = require("../src/fabrics.js");
const GAR = require("../src/garments.js");
const DST = require("../src/dst.js");

const PX = 10;
const mm = (pts) => pts.map(([x, y]) => ({ x: x * PX, y: y * PX }));
const box = (x0, y0, x1, y1) => mm([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
const ellipse = (cx, cy, rx, ry, n = 64) =>
  mm(Array.from({ length: n }, (_, i) => [cx + rx * Math.cos((2 * Math.PI * i) / n), cy + ry * Math.sin((2 * Math.PI * i) / n)]));
const grid = (n, sizeMm, make) => {
  const out = [], pitch = sizeMm / n;
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) out.push(make((c + 0.5) * pitch, (r + 0.5) * pitch));
  return out;
};

const DESIGNS = [
  { name: "Badge, two cut-outs", widthMm: 40, outer: box(0, 0, 40, 40), holes: [box(6, 14, 18, 26), box(28.5, 18.5, 31.5, 21.5)] },
  { name: "Ring (an O)", widthMm: 30, outer: ellipse(15, 18, 15, 18), holes: [ellipse(15, 18, 7, 10)] },
  { name: "Two counters (a B)", widthMm: 26, outer: box(0, 0, 26, 36), holes: [box(8, 6, 18, 14), box(8, 20, 20, 30)] },
  { name: "Wide U (a notch)", widthMm: 44, outer: mm([[0, 0], [14, 0], [14, 18], [30, 18], [30, 0], [44, 0], [44, 28], [0, 28]]), holes: [] },
  { name: "36 square holes of 4 mm, 60 mm", widthMm: 60, outer: box(0, 0, 60, 60), holes: grid(6, 60, (x, y) => box(x - 2, y - 2, x + 2, y + 2)) },
  { name: "Plain square, 40 mm", widthMm: 40, outer: box(0, 0, 40, 40), holes: [] },
];
const GARMENTS = ["hat_front", "left_chest", "beanie", "full_back", "tote", "towel"];

function build(design, garmentId, extra) {
  const garment = GAR.getGarment(garmentId);
  return DG.buildQualityDesign(
    [{ rgb: [27, 58, 92], shapes: [{ outer: design.outer, holes: design.holes, tierOverride: "fill" }] }],
    Object.assign({ garment, fabric: FAB.getFabric(FAB.fabricForGarment(garmentId)), pxPerMm: PX,
      targetWidthMm: design.widthMm, darkOnTop: false, underlay: true, fillColumns: true }, extra));
}

function inRing(ring, x, y) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j];
    if ((a.y > y) !== (b.y > y) && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x) c = !c;
  }
  return c;
}
function distToRing(ring, x, y) {
  let best = Infinity;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j], dx = b.x - a.x, dy = b.y - a.y;
    const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / (dx * dx + dy * dy || 1)));
    best = Math.min(best, Math.hypot(a.x + t * dx - x, a.y + t * dy - y));
  }
  return best;
}

// The stream is in 0.1 mm, centred on the drawing's box, +y up; the drawing is
// in source px (PX a mm), +y down. Scale to the target width is 1 here.
function offGround(design, p) {
  const xs = design.outer.map((q) => q.x), ys = design.outer.map((q) => q.y);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const scale = (design.widthMm * PX) / (Math.max(...xs) - Math.min(...xs));
  const x = cx + (p.x / 10) * PX / scale, y = cy - (p.y / 10) * PX / scale, tol = 1.0 * PX;
  const out = !inRing(design.outer, x, y) && distToRing(design.outer, x, y) > tol;
  const inHole = design.holes.some((h) => inRing(h, x, y) && distToRing(h, x, y) > tol);
  return out || inHole;
}

function measure(design, d) {
  const s = d.stitches, segs = new Set();
  let attached = false, prev = null, floats = 0, floatMm = 0, leaving = 0, unasked = 0, sewnMm = 0;
  for (let i = 0; i < s.length; i++) {
    const r = s[i];
    if (r.type === "end") break;
    if (r.type === "trim" || r.type === "color") { attached = false; prev = r; continue; }
    if (prev && attached && (prev.x !== r.x || prev.y !== r.y)) {
      const len = Math.hypot(r.x - prev.x, r.y - prev.y) / 10;
      segs.add(`${prev.x},${prev.y}>${r.x},${r.y}`);
      if (r.type === "stitch") sewnMm += len;
      else {
        floats++; floatMm += len;
        const n = Math.max(1, Math.ceil(len / 0.25));
        let off = false;
        for (let k = 0; k <= n && !off; k++) off = offGround(design, { x: prev.x + ((r.x - prev.x) * k) / n, y: prev.y + ((r.y - prev.y) * k) / n });
        if (off && len > 4) leaving++;
      }
    }
    // a float the writer lays as three or more jump records, starting here
    if (r.type === "jump" && i > 0 && s[i - 1].type === "stitch") {
      let j = i, n = 0;
      for (; j < s.length && s[j].type === "jump"; j++) n += DST.jumpRecords(s[j].x - s[j - 1].x, s[j].y - s[j - 1].y);
      const next = s[j];
      if (next && next.type === "stitch" && n + DST.jumpRecords(next.x - s[j - 1].x, next.y - s[j - 1].y) - 1 >= 3) unasked++;
    }
    if (r.type === "stitch") attached = true;
    prev = r;
  }
  return { stitches: d.stitchCount, trims: s.filter((r) => r.type === "trim").length, floats, floatMm, leaving, unasked, sewnMm, segs,
    pens: s.filter((r) => r.type === "stitch").map((r) => `${r.x},${r.y}`).join(" ") };
}

const tot = { off: {}, on: {} };
const add = (t, k, v) => (t[k] = (t[k] || 0) + v);
const rows = [];
let moved = 0, newThread = 0, builds = 0;
for (const design of DESIGNS) {
  const r = { name: design.name };
  for (const g of GARMENTS) {
    const arms = {};
    for (const [arm, cutFloats] of [["off", false], ["on", true]]) {
      const t0 = process.hrtime.bigint();
      const d = build(design, g, { cutFloats });
      const ms = Number(process.hrtime.bigint() - t0) / 1e6;
      const tied = build(design, g, { cutFloats, ties: true });
      const m = measure(design, d);
      m.tiedStitches = tied.stitchCount; m.locks = (tied._debug && tied._debug.nTies) || 0; m.ms = ms;
      arms[arm] = m;
      for (const k of ["stitches", "trims", "floats", "floatMm", "leaving", "unasked", "sewnMm", "tiedStitches", "locks", "ms"]) { add(tot[arm], k, m[k]); add(r[arm] || (r[arm] = {}), k, m[k]); }
      builds++;
    }
    if (arms.off.pens !== arms.on.pens) moved++;
    for (const k of arms.on.segs) if (!arms.off.segs.has(k)) newThread++;
  }
  rows.push(r);
}

const n = (v) => Math.round(v).toLocaleString("en-US");
console.log(`manual lane, fillColumns on, ${GARMENTS.length} garments each (${GARMENTS.join(", ")})\n`);
console.log("| shape | stitches | trims off → on | DST cuts nobody asked for off → on | floats off → on (mm) | floats leaving the fill off → on | locks with `ties` off → on | stitches with `ties` off → on |");
console.log("|---|---|---|---|---|---|---|---|");
for (const r of [...rows, { name: "**all**", off: tot.off, on: tot.on }]) {
  const st = r.off.stitches === r.on.stitches ? n(r.on.stitches) : `${n(r.off.stitches)} → ${n(r.on.stitches)}`;
  console.log(`| ${r.name} | ${st} | ${n(r.off.trims)} → ${n(r.on.trims)} | ${n(r.off.unasked)} → ${n(r.on.unasked)} | ${n(r.off.floats)} (${n(r.off.floatMm)}) → ${n(r.on.floats)} (${n(r.on.floatMm)}) | ${n(r.off.leaving)} → ${n(r.on.leaving)} | ${n(r.off.locks)} → ${n(r.on.locks)} | ${n(r.off.tiedStitches)} → ${n(r.on.tiedStitches)} |`);
}
console.log(`\nbuilds: ${builds}; designs whose needle points moved: ${moved}; segments of thread in "on" not in "off": ${newThread}`);
console.log(`sewn thread mm: ${n(tot.off.sewnMm)} → ${n(tot.on.sewnMm)}; build time ms: ${n(tot.off.ms)} → ${n(tot.on.ms)}`);
