// What `ties: true` does to a design, measured on the records the encoders
// are handed: how many locks, how long their legs really are in millimetres,
// what they cost in stitches, and whether they add a second penetration of a
// hole. Prints the two tables docs/lock-stitches-2026-10-03.md carries.
//
//   node tools/lock-stitch-census.mjs [srcDir] [fontsDir]
//
// srcDir: the engine to measure (default: this checkout's src). Point it at
// another checkout to measure that one -- which is how the "before" column of
// the doc was made. fontsDir: where manifest.json and bin/ are (default:
// <this checkout>/src/fonts).
//
// A LOCK IS FOUND BY DIFF, not by its shape. The tied stream is the untied one
// with records put in, so wherever the two part, the next four records are a
// lock. Looking for "a, b, a, b" instead reads a font's own triple run as one:
// a quarter more locks than there are, and legs of 3 mm.
//
// A LEG IS MEASURED IN THE STREAM'S OWN UNITS, 0.1 mm, after everything the
// builder does to a point. The lettering port of 2026-09-14 computed it in
// pixels and no test asked what that was in millimetres.
import { readFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = resolve(process.argv[2] || join(ROOT, "src"));
const FONT_DIR = resolve(process.argv[3] || join(ROOT, "src", "fonts"));
const DG = require(join(SRC, "digitize.js"));
const FAB = require(join(SRC, "fabrics.js"));
const BIN = require(join(SRC, "fontbin.js"));

const same = (p, q) => p.x === q.x && p.y === q.y;
const count = (d, k) => d.stitches.filter((s) => s.type === k).length;
// two stitch records in a row on one spot: the needle goes down twice in a hole
const doubled = (d) => {
  let n = 0;
  for (let i = 1; i < d.stitches.length; i++) {
    if (d.stitches[i].type === "stitch" && d.stitches[i - 1].type === "stitch" && same(d.stitches[i], d.stitches[i - 1])) n++;
  }
  return n;
};
// -> the leg of every lock, in mm
function lockLegs(off, on) {
  const a = off.stitches, b = on.stitches, legs = [];
  let i = 0, j = 0;
  while (j < b.length) {
    if (i < a.length && a[i].type === b[j].type && same(a[i], b[j])) { i++; j++; continue; }
    legs.push(Math.hypot(b[j + 1].x - b[j].x, b[j + 1].y - b[j].y) / 10);
    j += 4;
  }
  if (i !== a.length) throw new Error("the tied stream is not the untied one plus locks");
  return legs;
}
const median = (a) => (a.length ? a.slice().sort((x, y) => x - y)[Math.floor(a.length / 2)] : NaN);
const mmOf = (x) => (isFinite(x) ? x.toFixed(2) : "-");
const pct = (on, off) => "+" + ((on / off - 1) * 100).toFixed(2) + "%";

// ---- lettering: every shipped font --------------------------------------------
const TEXTS = [["`KENT` (4 ch)", "KENT"], ["`Fritsch's Stitches` (18 ch)", "Fritsch's Stitches"], ["two lines (37 ch)", "Fritsch's Stitches\nFritsch's Stitches"]];
const man = JSON.parse(readFileSync(join(FONT_DIR, "manifest.json"), "utf8"));
const fonts = man.fonts.map((f) => BIN.decodeFontBin(readFileSync(join(FONT_DIR, "bin", f.key + ".embf"))));
console.log(`engine: ${SRC}\n`);
console.log(`Lettering, ${fonts.length} shipped fonts, 5 x 2.25 in box, 8 px per mm:\n`);
console.log("| text | stitches off | on | more | trims added | locks | leg: median | shortest | longest | locks under 0.75 mm | doubled holes added |");
console.log("|---|---|---|---|---|---|---|---|---|---|---|");
for (const [label, text] of TEXTS) {
  const t = { off: 0, on: 0, trims: 0, legs: [], holes: 0 };
  for (const font of fonts) {
    const o = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8 };
    const off = DG.buildLetteringDesign(font, text, { ...o, ties: false });
    const on = DG.buildLetteringDesign(font, text, { ...o, ties: true });
    t.off += off.stitchCount; t.on += on.stitchCount;
    t.trims += count(on, "trim") - count(off, "trim");
    t.holes += doubled(on) - doubled(off);
    t.legs.push(...lockLegs(off, on));
  }
  console.log(`| ${label} | ${t.off.toLocaleString()} | ${t.on.toLocaleString()} | ${pct(t.on, t.off)} | ${t.trims} | ${t.legs.length.toLocaleString()} | ${mmOf(median(t.legs))} mm | ${mmOf(Math.min(...t.legs))} | ${mmOf(Math.max(...t.legs))} | ${t.legs.filter((x) => x < 0.75).length.toLocaleString()} | ${t.holes.toLocaleString()} |`);
}

// ---- shapes: what a person draws in the manual lane ----------------------------
const PX = 10; // source px per mm
const mm = (pts) => pts.map(([x, y]) => ({ x: x * PX, y: y * PX }));
const box = (x0, y0, x1, y1) => mm([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
const round = (cx, cy, r, n = 48) => mm(Array.from({ length: n }, (_, i) => [cx + r * Math.cos((2 * Math.PI * i) / n), cy + r * Math.sin((2 * Math.PI * i) / n)]));
const star = (cx, cy, r, n = 5) => mm(Array.from({ length: 2 * n }, (_, i) => {
  const rr = i % 2 ? r * 0.45 : r, a = (Math.PI * i) / n - Math.PI / 2;
  return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)];
}));
const fill = (outer, holes) => ({ outer, holes: holes || [], tierOverride: "fill" });
const one = (shape) => [{ rgb: [27, 58, 92], shapes: [shape] }];
const holes36 = [];
for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) holes36.push(box(6 + c * 9, 6 + r * 9, 10 + c * 9, 10 + r * 9));
// Sizes in mm.
const DESIGNS = [
  ["Square, 40 mm", 40, one(fill(box(0, 0, 40, 40)))],
  ["Circle, 30 mm", 30, one(fill(round(15, 15, 15)))],
  ["Star, 40 mm", 38, one(fill(star(20, 20, 20)))],
  ["Triangle, 10 mm", 10, one(fill(mm([[0, 10], [5, 0], [10, 10]])))],
  ["Badge, two cut-outs, 40 mm", 40, one(fill(box(0, 0, 40, 40), [box(6, 14, 18, 26), box(28.5, 18.5, 31.5, 21.5)]))],
  ["Ring (an O), 40 mm", 40, one(fill(round(20, 20, 20, 64), [round(20, 20, 11)]))],
  ["Badge, 36 holes, 60 mm", 60, one(fill(box(0, 0, 60, 60), holes36))],
  ["Thin bar, 3 x 40 mm (satin)", 40, one({ outer: box(0, 0, 40, 3), holes: [] })],
  ["Three squares apart, one colour", 100, [{ rgb: [27, 58, 92], shapes: [fill(box(0, 0, 20, 20)), fill(box(40, 0, 60, 20)), fill(box(80, 0, 100, 20))] }]],
  ["Three squares, three colours", 70, [{ rgb: [27, 58, 92], shapes: [fill(box(0, 0, 20, 20))] }, { rgb: [200, 30, 30], shapes: [fill(box(25, 0, 45, 20))] }, { rgb: [30, 30, 200], shapes: [fill(box(50, 0, 70, 20))] }]],
  ["Twelve 6 mm dots, one colour", 51, [{ rgb: [27, 58, 92], shapes: Array.from({ length: 12 }, (_, i) => fill(round(3 + (i % 4) * 15, 3 + Math.floor(i / 4) * 15, 3, 20))) }]],
];
// buildQualityDesign the way the Studio's manual lane calls it (generate.js).
const build = (regions, widthMm, extra) => DG.buildQualityDesign(JSON.parse(JSON.stringify(regions)),
  { garment: { id: "left_chest", widthIn: 6, heightIn: 6 }, fabric: FAB.getFabric(FAB.fabricForGarment("left_chest")),
    pxPerMm: PX, targetWidthMm: widthMm, darkOnTop: false, underlay: true, ...extra });
console.log("\nShapes, left chest, the pique preset, underlay on:\n");
console.log("| design | `fillColumns` | cuts | locks | stitches off | on | more | shortest leg |");
console.log("|---|---|---|---|---|---|---|---|");
const all = [];
let totOff = 0, totOn = 0;
for (const [name, widthMm, regions] of DESIGNS) {
  for (const fillColumns of [false, true]) {
    const off = build(regions, widthMm, { fillColumns });
    const on = build(regions, widthMm, { fillColumns, ties: true });
    const legs = lockLegs(off, on);
    all.push(...legs); totOff += off.stitchCount; totOn += on.stitchCount;
    console.log(`| ${name} | ${fillColumns ? "on" : "off"} | ${count(on, "trim")} | ${legs.length} | ${off.stitchCount.toLocaleString()} | ${on.stitchCount.toLocaleString()} | ${pct(on.stitchCount, off.stitchCount)} | ${legs.length ? mmOf(Math.min(...legs)) + " mm" : "-"} |`);
  }
}
console.log(`\nshapes in all: ${totOff.toLocaleString()} -> ${totOn.toLocaleString()} stitches (${pct(totOn, totOff)}); ${all.length} locks, median leg ${mmOf(median(all))} mm, ${all.filter((x) => x < 0.75).length} under 0.75 mm, shortest ${all.length ? mmOf(Math.min(...all)) : "-"}, longest ${all.length ? mmOf(Math.max(...all)) : "-"}`);
