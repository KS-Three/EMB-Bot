// What the browser's medial satin does with the Studio's preset shapes: which
// designs sew far more than their neighbours in size, how long their longest
// stitch is, how far short of the drawn shape they stop -- and, against a
// second tree, exactly which designs a change to the engine moves.
//
//   node tools/satin-walk-census.mjs                       the star's control range on left chest
//   node tools/satin-walk-census.mjs --garments all        every garment (ten times the work)
//   node tools/satin-walk-census.mjs --ratios 15:90:1      the Studio's own 1% ratio step
//   node tools/satin-walk-census.mjs --kind rect           bars: nine heights by five corner radii
//   node tools/satin-walk-census.mjs --against <root>      build the same designs with another tree's
//                                                          engine (its src/ and app/src/lib) and say which differ
//   node tools/satin-walk-census.mjs --walks               count, per design, the walks of `skeletonEdges`
//                                                          that only their guard stopped (in --against's
//                                                          tree when one is given, else in this one)
//   node tools/satin-walk-census.mjs --render out.png --shape star:12:0.15:20[:garment]
//                                                          draw one design, read back from its DST bytes
//                                                          (rect:<height>:<corner radius>:<width>; with
//                                                          --against, as that tree's engine builds it)
//   --points 12:12  --sizes 10:30:1  --list                narrow the grid; print every out-of-line design
//
// A design is built exactly as `app/src/lib/generate.js` builds a `shape`
// element: the Studio's own ring (`shapePresetPoints`), `shapesToRegions`,
// `buildQualityDesign` with the garment's fabric preset, underlay on.
//
// OUT OF LINE: a satin design's stitches grow with its size and a fill's with
// the square of it, so the count is first divided by that, and then compared
// with the median of the same quantity over the ten sizes either side (same
// star, same garment, same tier). Over twice it, or under half, is out of
// line. A plain "against the size either side" test read the 20 mm star as
// normal: 19 and 21 mm had run away too.
//
// THE SAME DESIGN is one whose every stitch record (x, y, type), reported
// size and stitch count hash alike.
//
// A WALK AT THE GUARD: `skeletonEdges` follows skeleton pixels until a node,
// under `while (guard++ < w * h)`. `--walks` loads a copy of the tree's
// engine with one counter line after each of the two loops (the text it is
// inserted beside is checked, so a tree whose walk has been rewritten fails
// here rather than counting nothing).
//
// The pre-change tree for the 2026-10-03 fix is `git archive f887e27d src
// app/package.json app/src/lib | tar -x -C <dir>`. Its runaway designs take
// seconds each (the default grid about an hour there); narrow the grid.
import "./_help.mjs";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import zlib from "node:zlib";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);
const flag = (name) => argv.includes(name);
const opt = (name, dflt) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : dflt; };
const range = (text) => { const [a, b, s = 1] = text.split(":").map(Number); const out = []; for (let v = Math.round(a * 1000); v <= Math.round(b * 1000); v += Math.round(s * 1000)) out.push(v / 1000); return out; };

// ---- an engine, from a tree ------------------------------------------------
const GUARD_COUNTERS = [
  // [the last lines of the node walk's loop, before and after 2026-10-03], the ring walk's close
  ["        path.push([cx, cy]); seen.add(id(cx, cy));\n      }\n      return path;\n    };",
   "        path.push([cx, cy]); seen.add(id(cx, cy)); own.add(id(cx, cy));\n      }\n      return path;\n    };"],
  ["      path.push([x, y]); // close ring explicitly"],
];
function countedSrc(srcDir) {
  // a copy of the tree's src with the two counters in satin.js, in a temp dir
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "satin-walk-"));
  for (const f of fs.readdirSync(srcDir)) if (f.endsWith(".js")) fs.copyFileSync(path.join(srcDir, f), path.join(dir, f));
  let text = fs.readFileSync(path.join(srcDir, "satin.js"), "utf8").replace(/\r\n/g, "\n");
  const count = "if (guard > w * h) globalThis.__walksAtGuard = (globalThis.__walksAtGuard || 0) + 1;\n";
  GUARD_COUNTERS.forEach((anchors, which) => {
    const at = anchors.filter((a) => text.split(a).length === 2);
    if (at.length !== 1) throw new Error(`${srcDir}/satin.js: cannot find the ${which ? "ring" : "node"} walk's loop to count it`);
    const a = at[0];
    text = which ? text.replace(a, "      " + count + a) : text.replace(a, a.replace("      return path;", "      " + count + "      return path;"));
  });
  fs.writeFileSync(path.join(dir, "satin.js"), text);
  process.on("exit", () => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}
async function engine(root, counted) {
  const srcDir = counted ? countedSrc(path.join(root, "src")) : path.join(root, "src");
  const require = createRequire(path.join(srcDir, "digitize.js"));
  const lib = (name) => import(pathToFileURL(path.join(root, "app", "src", "lib", name)).href);
  return {
    root, counted,
    DG: require(path.join(srcDir, "digitize.js")), GAR: require(path.join(srcDir, "garments.js")), FAB: require(path.join(srcDir, "fabrics.js")),
    DST: require(path.join(srcDir, "dst.js")), DSTIN: require(path.join(srcDir, "dstimport.js")),
    presets: await lib("shapePresets.js"), manual: await lib("manualShapes.js"),
  };
}
function build(E, kind, params, sizeMm, garmentId) {
  const points = E.presets.shapePresetPoints(kind, params, sizeMm);
  const { regions, pxPerMm } = E.manual.shapesToRegions([
    { id: "shape", points, curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  globalThis.__walksAtGuard = 0;
  const t0 = Date.now();
  const design = E.DG.buildQualityDesign(regions, {
    garment: E.GAR.getGarment(garmentId), fabric: E.FAB.getFabric(E.FAB.fabricForGarment(garmentId)), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0,
  });
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of points) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
  return { design, ms: Date.now() - t0, walksAtGuard: globalThis.__walksAtGuard, ringWmm: (x1 - x0) / pxPerMm, ringHmm: (y1 - y0) / pxPerMm };
}
function measure(design) {
  const st = design.stitches, h = createHash("sha256");
  let longest = 0, onPoint = 0;
  for (let i = 0; i < st.length; i++) {
    const s = st[i];
    h.update(s.x + "," + s.y + "," + s.type + ";");
    if (s.type !== "stitch" || i === 0) continue;
    const d = Math.hypot(s.x - st[i - 1].x, s.y - st[i - 1].y) / 10;
    if (d > longest) longest = d;
    if (d === 0 && st[i - 1].type === "stitch") onPoint++;
  }
  h.update("|" + design.widthMM + "|" + design.heightMM + "|" + design.stitchCount);
  return { stitches: design.stitchCount, tier: design._debug.nSatin ? "satin" : design._debug.nFill ? "fill" : "none",
           longest, onPoint, wMm: design.widthMM, hMm: design.heightMM, digest: h.digest("hex") };
}

// ---- one design, drawn from the file ---------------------------------------
function render(E, spec, outPng) {
  const [kind, a, b, size, garmentId = "left_chest"] = spec.split(":");
  const params = kind === "star" ? { points: +a, innerRatio: +b } : kind === "rect" ? { heightMm: +a, cornerRadiusMm: +b } : {};
  const { design } = build(E, kind, params, +size, garmentId);
  const data = E.DST.encodeDST(design).slice(512);
  const segs = [];
  let x = 0, y = 0, sewing = false;
  for (let i = 0; i + 2 < data.length; i += 3) {
    if (data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 0xf3) break;
    const jump = (data[i + 2] & 0x80) !== 0, colour = (data[i + 2] & 0x40) !== 0;
    const [dx, dy] = E.DSTIN.decodeDelta(data[i], data[i + 1], data[i + 2]);
    if (!colour) segs.push({ x0: x, y0: y, x1: x + dx, y1: y + dy, sewn: !jump && sewing });
    sewing = !jump && !colour; x += dx; y += dy;
  }
  const outline = (design.shapeOutlines[0] && design.shapeOutlines[0].points) || [];
  const scale = 800 / (Math.max(+size, design.widthMM, design.heightMM) + 4), W = 800, H = 800;
  const px = Buffer.alloc(W * H * 4, 255);
  const X = (mm) => W / 2 + mm * scale, Y = (mm) => H / 2 - mm * scale;
  const line = (ax, ay, bx, by, c, alpha) => {
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) * 1.5));
    for (let i = 0; i <= n; i++) {
      const ix = Math.round(ax + (bx - ax) * i / n), iy = Math.round(ay + (by - ay) * i / n);
      if (ix < 0 || iy < 0 || ix >= W || iy >= H) continue;
      const o = (iy * W + ix) * 4;
      for (let k = 0; k < 3; k++) px[o + k] = Math.round(px[o + k] * (1 - alpha) + c[k] * alpha);
    }
  };
  outline.forEach((p, i) => { const q = outline[(i + 1) % outline.length]; line(X(p[0]), Y(p[1]), X(q[0]), Y(q[1]), [150, 150, 150], 1); });
  for (const s of segs) line(X(s.x0 / 10), Y(s.y0 / 10), X(s.x1 / 10), Y(s.y1 / 10), s.sewn ? [0, 0, 0] : [230, 30, 30], s.sewn ? 0.55 : 0.8);
  const raw = Buffer.alloc(H * (1 + W * 4));
  for (let r = 0; r < H; r++) px.copy(raw, r * (1 + W * 4) + 1, r * W * 4, (r + 1) * W * 4);
  const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (buf) => { let c = 0xffffffff; for (const v of buf) c = crcTable[(c ^ v) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, body) => { const len = Buffer.alloc(4); len.writeUInt32BE(body.length); const t = Buffer.from(type, "latin1"); const sum = Buffer.alloc(4); sum.writeUInt32BE(crc(Buffer.concat([t, body]))); return Buffer.concat([len, t, body, sum]); };
  const head = Buffer.alloc(13); head.writeUInt32BE(W, 0); head.writeUInt32BE(H, 4); head[8] = 8; head[9] = 6;
  fs.writeFileSync(outPng, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", head), chunk("IDAT", zlib.deflateSync(raw, { level: 9 })), chunk("IEND", Buffer.alloc(0))]));
  const m = measure(design);
  console.log(`${spec}: ${m.stitches} stitches, ${m.tier}, sewn ${m.wMm.toFixed(1)} x ${m.hMm.toFixed(1)} mm, longest stitch ${m.longest.toFixed(1)} mm, ${m.onPoint} stitch records on the point before them`);
  console.log(`grey: the drawn shape; black: thread, as the DST bytes say; red: needle-up moves -> ${outPng} (${scale.toFixed(1)} px per mm)`);
}

// ---- the census ------------------------------------------------------------
const here = await engine(ROOT, flag("--walks") && !opt("--against"));
const there = opt("--against") ? await engine(path.resolve(opt("--against")), flag("--walks")) : null;
// --render with --against draws the design as the OTHER tree's engine builds it
if (opt("--render")) { render(there || here, opt("--shape", "star:12:0.15:20"), opt("--render")); process.exit(0); }

const kind = opt("--kind", "star");
const garmentIds = opt("--garments", "left_chest") === "all" ? here.GAR.GARMENTS.map((g) => g.id) : opt("--garments", "left_chest").split(",");
const sizes = range(opt("--sizes", "10:100:1"));
const bags = [];
if (kind === "star") {
  const P = here.presets;
  for (const points of range(opt("--points", `${P.STAR_MIN_POINTS}:${P.STAR_MAX_POINTS}`)))
    for (const pct of range(opt("--ratios", `${Math.round(P.STAR_MIN_INNER_RATIO * 100)}:${Math.round(P.STAR_MAX_INNER_RATIO * 100)}:5`)))
      bags.push({ name: `${points} points, ratio ${(pct / 100).toFixed(2)}`, params: { points, innerRatio: pct / 100 } });
} else if (kind === "rect") {
  for (const heightMm of [1, 2, 3, 4, 6, 10, 20, 30, 60]) for (const cornerRadiusMm of [0, 0.5, 1.5, 5, 30])
    bags.push({ name: `${heightMm} mm tall, corner radius ${cornerRadiusMm}`, params: { heightMm, cornerRadiusMm } });
} else bags.push({ name: kind, params: {} });

const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };
const quantile = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
const rows = [];
const t00 = Date.now();
for (const g of garmentIds) for (const bag of bags) {
  const series = [];
  for (const size of sizes) {
    const b = build(here, kind, bag.params, size, g);
    const row = { g, bag: bag.name, size, ringWmm: b.ringWmm, ringHmm: b.ringHmm, ms: b.ms, walks: here.counted ? b.walksAtGuard : null, ...measure(b.design) };
    if (there) {
      const o = build(there, kind, bag.params, size, g);
      row.other = { ms: o.ms, walks: there.counted ? o.walksAtGuard : null, ...measure(o.design) };
    }
    series.push(row); rows.push(row);
  }
  // out of line, within this star on this garment (and the same for the other tree's builds)
  const judge = (of) => {
    const norm = (i) => of(series[i]).tier === "satin" ? of(series[i]).stitches / series[i].size : of(series[i]).stitches / (series[i].size * series[i].size);
    series.forEach((r, i) => {
      const near = [];
      for (let j = Math.max(0, i - 10); j <= Math.min(series.length - 1, i + 10); j++) if (j !== i && of(series[j]).tier === of(r).tier) near.push(norm(j));
      if (near.length < 3) return;
      const mid = median(near);
      of(r).times = mid > 0 ? norm(i) / mid : 1;
      of(r).expected = Math.round(mid * (of(r).tier === "satin" ? r.size : r.size * r.size));
    });
  };
  judge((r) => r);
  if (there) judge((r) => r.other);
}

console.log(`${kind}: ${rows.length} designs (${bags.length} shapes x ${sizes.length} sizes x ${garmentIds.length} garments), built in ${((Date.now() - t00) / 1000).toFixed(0)} s`);
const satin = rows.filter((r) => r.tier === "satin"), fill = rows.filter((r) => r.tier === "fill");
console.log(`satin ${satin.length}, fill ${fill.length}, nothing sewn ${rows.length - satin.length - fill.length}`);
const off = rows.filter((r) => r.times > 2 || r.times < 0.5);
console.log(`\nOUT OF LINE with their neighbours in size: ${off.length} designs (${off.filter((r) => r.times > 2).length} over twice, ${off.filter((r) => r.times < 0.5).length} under half)`);
const byBag = new Map();
for (const r of off) { const k = r.bag; if (!byBag.has(k)) byBag.set(k, new Map()); const m = byBag.get(k); if (!m.has(r.size)) m.set(r.size, []); m.get(r.size).push(r); }
for (const [name, bySize] of byBag) console.log(`  ${name}: ` + [...bySize].map(([size, l]) => `${size} mm ${Math.min(...l.map((r) => r.stitches))}${l.length > 1 ? ".." + Math.max(...l.map((r) => r.stitches)) : ""} (x${Math.max(...l.map((r) => r.times)).toFixed(1)})`).join(", "));
if (flag("--list")) for (const r of off) console.log(`    ${r.g} ${r.bag} ${r.size} mm: ${r.stitches} stitches, its neighbours predict ${r.expected}, ${r.tier}`);
if (satin.length) {
  const L = satin.map((r) => r.longest);
  console.log(`\nSATIN, longest single stitch: least ${Math.min(...L).toFixed(1)} mm, median ${quantile(L, 0.5).toFixed(1)} mm, nine in ten under ${quantile(L, 0.9).toFixed(1)} mm, longest ${Math.max(...L).toFixed(1)} mm; over 12.1 mm (one DST record): ${satin.filter((r) => r.longest > 12.1).length} of ${satin.length}`);
  if (kind === "rect") {
    // a bar's crosses span its SHORT side; a stitch nine tenths as long as the bar runs along it
    const along = (r) => r.longest >= 0.9 * Math.max(r.ringWmm, r.ringHmm);
    const sharp = satin.filter((r) => r.bag.endsWith("radius 0")), round = satin.filter((r) => !r.bag.endsWith("radius 0"));
    console.log(`SATIN bars with a stitch at least nine tenths as long as the bar: sharp-cornered ${sharp.filter(along).length} of ${sharp.length}, round-cornered ${round.filter(along).length} of ${round.length}`);
    const over = (l) => l.map((r) => Math.min(r.wMm, r.hMm) - Math.min(r.ringWmm, r.ringHmm));
    if (sharp.length) console.log(`SATIN bars, sewn short side minus drawn: sharp-cornered median ${quantile(over(sharp), 0.5).toFixed(1)} mm, most ${Math.max(...over(sharp)).toFixed(1)} mm; round-cornered median ${quantile(over(round), 0.5).toFixed(1)} mm, most ${Math.max(...over(round)).toFixed(1)} mm`);
  }
  // where the hoop does not scale the design down, and for a shape whose own width is its extent
  const fits = (r) => { const hoop = here.GAR.getGarment(r.g); return r.ringWmm < hoop.widthIn * 25.4 - 0.01 && r.ringHmm < hoop.heightIn * 25.4 - 0.01; };
  const short = satin.filter((r) => fits(r) && kind !== "rect").map((r) => r.ringWmm - r.wMm);
  if (short.length) console.log(`SATIN, drawn width minus sewn width: median ${quantile(short, 0.5).toFixed(1)} mm, one in ten over ${quantile(short, 0.9).toFixed(1)} mm, most ${Math.max(...short).toFixed(1)} mm`);
  console.log(`SATIN, stitch records on the point before them: ${satin.reduce((a, r) => a + r.onPoint, 0)}; largest design ${Math.max(...satin.map((r) => r.stitches))} stitches; slowest ${Math.max(...satin.map((r) => r.ms))} ms`);
}
if (here.counted) {
  const hit = rows.filter((r) => r.walks > 0);
  console.log(`\nWALKS only their guard stopped: in ${hit.length} of ${rows.length} designs (${hit.reduce((a, r) => a + r.walks, 0)} walks, all calls of skeletonEdges counted)`);
}
if (there) {
  const moved = rows.filter((r) => r.other.digest !== r.digest);
  console.log(`\nAGAINST ${there.root}: the same ${rows.length - moved.length}, moved ${moved.length} (${moved.filter((r) => r.other.tier === "fill").length} of them fills there; tier changed in ${rows.filter((r) => r.other.tier !== r.tier).length})`);
  const offThere = rows.filter((r) => r.other.times > 2 || r.other.times < 0.5);
  console.log(`  out of line there: ${offThere.length} designs` + (offThere.length ? `, ${Math.min(...offThere.map((r) => r.other.stitches))} to ${Math.max(...offThere.map((r) => r.other.stitches))} stitches` : ""));
  if (moved.length) {
    const d = moved.map((r) => r.stitches - r.other.stitches);
    console.log(`  stitches, here minus there, over the moved: least ${Math.min(...d)}, median ${median(d)}, most ${Math.max(...d)}; largest design there ${Math.max(...moved.map((r) => r.other.stitches))}, here ${Math.max(...moved.map((r) => r.stitches))}`);
    console.log(`  time to build the moved designs: there median ${median(moved.map((r) => r.other.ms))} ms, here median ${median(moved.map((r) => r.ms))} ms`);
  }
  if (there.counted) {
    const hit = rows.filter((r) => r.other.walks > 0);
    console.log(`  walks only their guard stopped, there: in ${hit.length} designs. Moved without one: ${moved.filter((r) => !(r.other.walks > 0)).length}. With one and not moved: ${hit.filter((r) => r.other.digest === r.digest).length}.`);
  }
  if (flag("--list")) for (const r of moved) console.log(`    ${r.g} ${r.bag} ${r.size} mm: ${r.other.stitches} -> ${r.stitches} stitches, ${r.other.wMm.toFixed(1)} x ${r.other.hMm.toFixed(1)} -> ${r.wMm.toFixed(1)} x ${r.hMm.toFixed(1)} mm`);
}
