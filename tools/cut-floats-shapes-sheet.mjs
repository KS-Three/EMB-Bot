// What `cutFloats` changes on the basic-shape lane, with `fillColumns` already
// on there (#673): every preset built with the flag off and on, every thread
// counted, one row per family.
//
//   node tools/cut-floats-shapes-sheet.mjs
//
// Prints the table docs/cut-floats-shapes-2026-10-08.md carries.
//
// The presets are tools/file-cut-census.mjs's `--set shapes` presets (circle,
// heart, 9 rectangles, 30 stars; 7 sizes; every garment), built the way the
// Studio's shape branch calls buildQualityDesign (app/src/lib/generate.js):
// shapePresetPoints -> shapesToRegions, the garment's fabric preset,
// `darkOnTop: false`, underlay on, `fillColumns: true`.
//
// The measures are tools/cut-floats-sheet.mjs's (#672), unchanged:
// THREAD, not penetrations: a `jump` after a stitch is a float on the cloth.
// A CUT NOBODY ASKED FOR: a float the DST writer lays as three or more jump
// records (dst.jumpRecords), with no `trim` in the stream.
// LEAVES THE OUTLINE: a float longer than 4 mm with a point, sampled every
// 0.25 mm, more than 1 mm outside the preset's ring.
// NEW THREAD: a sewn or floated segment in the "on" stream not in the "off"
// one. `cutFloats` moves no stitch, so anything here is thread laid anew.
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DG = require("../src/digitize.js");
const FAB = require("../src/fabrics.js");
const GAR = require("../src/garments.js");
const DST = require("../src/dst.js");
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);
const { shapePresetPoints } = await lib("shapePresets.js");
const { shapesToRegions } = await lib("manualShapes.js");

const kinds = [["circle", {}, "circle"], ["heart", {}, "heart"]];
for (const heightMm of [10, 30, 50]) for (const cornerRadiusMm of [0, 3, 8]) kinds.push(["rect", { heightMm, cornerRadiusMm }, "rectangle"]);
for (const points of [3, 4, 5, 6, 8, 12]) for (const innerRatio of [0.15, 0.3, 0.45, 0.6, 0.9]) kinds.push(["star", { points, innerRatio }, `${points}-point star`]);
const SIZES = [12, 20, 30, 40, 50, 65, 80];

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

// The stream is in 0.1 mm, centred on the drawing's box, +y up; the ring is in
// source px (pxPerMm a mm), +y down, scaled to the target width.
function offRing(ring, pxPerMm, widthMm, p) {
  const xs = ring.map((q) => q.x), ys = ring.map((q) => q.y);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const scale = (widthMm * pxPerMm) / (Math.max(...xs) - Math.min(...xs));
  const x = cx + ((p.x / 10) * pxPerMm) / scale, y = cy - ((p.y / 10) * pxPerMm) / scale;
  return !inRing(ring, x, y) && distToRing(ring, x, y) * (scale / pxPerMm) > 1.0;
}

function measure(ring, pxPerMm, widthMm, d) {
  const s = d.stitches, segs = new Set();
  let attached = false, prev = null, floats = 0, leaving = 0, unasked = 0;
  for (let i = 0; i < s.length; i++) {
    const r = s[i];
    if (r.type === "end") break;
    if (r.type === "trim" || r.type === "color") { attached = false; prev = r; continue; }
    if (prev && attached && (prev.x !== r.x || prev.y !== r.y)) {
      const len = Math.hypot(r.x - prev.x, r.y - prev.y) / 10;
      segs.add(`${prev.x},${prev.y}>${r.x},${r.y}`);
      if (r.type !== "stitch") {
        floats++;
        const n = Math.max(1, Math.ceil(len / 0.25));
        let off = false;
        for (let k = 0; k <= n && !off; k++) off = offRing(ring, pxPerMm, widthMm, { x: prev.x + ((r.x - prev.x) * k) / n, y: prev.y + ((r.y - prev.y) * k) / n });
        if (off && len > 4) leaving++;
      }
    }
    if (r.type === "jump" && i > 0 && s[i - 1].type === "stitch") {
      let j = i, n = 0;
      for (; j < s.length && s[j].type === "jump"; j++) n += DST.jumpRecords(s[j].x - s[j - 1].x, s[j].y - s[j - 1].y);
      const next = s[j];
      if (next && next.type === "stitch" && n + DST.jumpRecords(next.x - s[j - 1].x, next.y - s[j - 1].y) - 1 >= 3) unasked++;
    }
    if (r.type === "stitch") attached = true;
    prev = r;
  }
  return { stitches: d.stitchCount, trims: s.filter((r) => r.type === "trim").length, floats, leaving, unasked, segs,
    pens: s.filter((r) => r.type === "stitch").map((r) => `${r.x},${r.y}`).join(" ") };
}

const KEYS = ["designs", "stitches", "trims", "floats", "leaving", "unasked", "withUnasked"];
const fam = new Map();
const tot = { off: {}, on: {} };
const add = (t, k, v) => (t[k] = (t[k] || 0) + v);
let moved = 0, newThread = 0, newLeaving = 0, builds = 0;
for (const [kind, params, family] of kinds) {
  if (!fam.has(family)) fam.set(family, { off: {}, on: {} });
  const row = fam.get(family);
  for (const sizeMm of SIZES) {
    const points = shapePresetPoints(kind, params, sizeMm);
    const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points, curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null }]);
    const ring = regions[0].shapes[0].outer;
    for (const garment of GAR.GARMENTS) {
      const arms = {};
      for (const [arm, cutFloats] of [["off", false], ["on", true]]) {
        const d = DG.buildQualityDesign(regions, { garment, fabric: FAB.getFabric(FAB.fabricForGarment(garment.id)), pxPerMm,
          darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0, fillColumns: true, cutFloats });
        const m = measure(ring, pxPerMm, sizeMm, d);
        m.designs = 1; m.withUnasked = m.unasked > 0 ? 1 : 0;
        arms[arm] = m;
        for (const k of KEYS) { add(tot[arm], k, m[k]); add(row[arm], k, m[k]); }
        builds++;
      }
      if (arms.off.pens !== arms.on.pens) moved++;
      for (const k of arms.on.segs) if (!arms.off.segs.has(k)) newThread++;
      if (arms.on.leaving > arms.off.leaving) newLeaving++;
    }
  }
}

const n = (v) => Math.round(v).toLocaleString("en-US");
console.log(`basic-shape lane, fillColumns on, ${SIZES.length} sizes x ${GAR.GARMENTS.length} garments per preset\n`);
console.log("| family | designs | stitches | trims off → on | DST cuts nobody asked for off → on (designs) | floats off → on | floats > 4 mm leaving the outline off → on |");
console.log("|---|---|---|---|---|---|---|");
for (const [name, r] of [...fam, ["**all**", tot]]) {
  const st = r.off.stitches === r.on.stitches ? n(r.on.stitches) : `${n(r.off.stitches)} → ${n(r.on.stitches)}`;
  console.log(`| ${name} | ${n(r.off.designs)} | ${st} | ${n(r.off.trims)} → ${n(r.on.trims)} | ${n(r.off.unasked)} (${n(r.off.withUnasked)}) → ${n(r.on.unasked)} (${n(r.on.withUnasked)}) | ${n(r.off.floats)} → ${n(r.on.floats)} | ${n(r.off.leaving)} → ${n(r.on.leaving)} |`);
}
console.log(`\nbuilds: ${builds}; designs whose needle points moved: ${moved}; segments of thread in "on" not in "off": ${newThread}; designs with more floats leaving the outline: ${newLeaving}`);
