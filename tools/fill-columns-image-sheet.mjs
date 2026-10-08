// What `fillColumns` did to ONE image: the image lane's design with the
// option off beside on, thread by thread, every float and cut marked.
//
//   node tools/fill-columns-image-sheet.mjs <image.png> [out.svg]
//        [--colors N] [--garment id] [--keep-bg]
//
// Kent's ask 2026-10-08, when he flipped the image lane on: for the next ten
// digitized images shown to him, show what the float did or didn't do. This
// is that picture. The design is built the way app/src/lib/generate.js's
// image branch builds it (the Studio's own flatten and trace, the garment's
// fabric preset, underlay on, nColors 4 and the background removed unless
// told otherwise), so "on" is what the Studio now sews and "off" is what it
// sewed until 2026-10-08.
//
// Blue is sewn thread, RED is a float (a move with the thread still
// attached), an orange dot is a cut. The caption under each half counts
// floats, the floats that leave the fill (over 0.8 mm outside every drawn
// shape: a counter, a notch, bare cloth), cuts and stitches.
import { writeFileSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
globalThis.window = globalThis;
for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "svgpath", "svgimport", "dst", "dstimport", "exp", "pes", "svgexport", "stitchModel"]) require(`../src/${f}.js`);
const DG = require("../src/digitize.js"), FAB = require("../src/fabrics.js"), GAR = require("../src/garments.js");
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);

const args = process.argv.slice(2);
const take = (name, dflt) => { const i = args.indexOf(name); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const flag = (name) => { const i = args.indexOf(name); if (i < 0) return false; args.splice(i, 1); return true; };
const N_COLORS = Number(take("--colors", 4)), GARMENT = take("--garment", "left_chest"), KEEP_BG = flag("--keep-bg");
const [SRC, OUT = basename(args[0] || "image", ".png") + "-fill-columns.svg"] = args;
if (!SRC) { console.error("usage: node tools/fill-columns-image-sheet.mjs <image.png> [out.svg] [--colors N] [--garment id] [--keep-bg]"); process.exit(2); }

const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
const { flatToRegions } = await lib("imageRegions.js");
const { decodePNG, downscale } = await import(pathToFileURL(join(ROOT, "tools", "png.mjs")).href);
let img = decodePNG(SRC);
if (Math.max(img.width, img.height) > WORK_MAX_PX) img = downscale(img, WORK_MAX_PX);
const rgba = Uint8ClampedArray.from(img.rgba);
for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
const reg = flatToRegions(flattenRGBA(rgba, img.width, img.height, { nColors: N_COLORS, removeBg: !KEEP_BG }));
const garment = GAR.getGarment(GARMENT);
const build = (fillColumns) => DG.buildQualityDesign(JSON.parse(JSON.stringify(reg.regions)), { garment, fabric: FAB.getFabric(FAB.fabricForGarment(GARMENT)), pxPerMm: reg.pxPerMm, satinMaxWidthMm: 3.0, underlay: true, offsetXMm: 0, offsetYMm: 0, fillColumns });

// drawn ground, mm, y up
function ground(d) {
  const shapes = d.shapeOutlines.filter((o) => !o.dropped && o.points.length > 2);
  const inRing = (x, y, r) => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c; } return c; };
  const rings = shapes.flatMap((o) => [o.points].concat(o.holes || []));
  return {
    rings,
    inside: (x, y) => shapes.some((o) => inRing(x, y, o.points) && !(o.holes || []).some((h) => inRing(x, y, h))),
    edge: (x, y) => { let m = Infinity; for (const r of rings) for (let i = 0; i < r.length; i++) { const [ax, ay] = r[i], [bx, by] = r[(i + 1) % r.length], dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy; const t = L ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / L)) : 0; m = Math.min(m, Math.hypot(x - ax - t * dx, y - ay - t * dy)); } return m; },
  };
}
function thread(d) {
  const g = ground(d), sewn = [], floats = [], cuts = [];
  let attached = false, prev = null, off = 0, offMm = 0;
  for (const s of d.stitches) {
    if (s.type === "end") break;
    if (s.type === "trim" || s.type === "color") { if (s.type === "trim") cuts.push(s); attached = false; prev = s; continue; }
    if (prev && attached && (prev.x !== s.x || prev.y !== s.y)) {
      if (s.type === "stitch") sewn.push([prev, s]);
      else {
        let leaves = false;
        for (let k = 1; k < 20 && !leaves; k++) { const x = (prev.x + ((s.x - prev.x) * k) / 20) / 10, y = (prev.y + ((s.y - prev.y) * k) / 20) / 10; leaves = !g.inside(x, y) && g.edge(x, y) > 0.8; }
        floats.push([prev, s, leaves]);
        if (leaves) { off++; offMm += Math.hypot(s.x - prev.x, s.y - prev.y) / 10; }
      }
    }
    if (s.type === "stitch") attached = true;
    prev = s;
  }
  return { g, sewn, floats, cuts, off, offMm, stitches: d.stitches.filter((s) => s.type === "stitch").length };
}

const arms = [false, true].map((on) => { const d = build(on); return { on, d, t: thread(d) }; });
const W = arms[0].d.widthMM, H = arms[0].d.heightMM, S = Math.min(12, 520 / Math.max(W, H)), PAD = 6, CAP = 16, GAP = 8;
const colW = W + 2 * PAD, f = (n) => (Math.round(n * 10) / 10).toString(), esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
const svg = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${f((2 * colW + GAP) * S)} ${f((H + 2 * PAD + CAP + 10) * S)}" font-family="system-ui, Segoe UI, Arial, sans-serif">`, `<rect width="100%" height="100%" fill="#fff"/>`];
arms.forEach(({ on, d, t }, col) => {
  const ox = (col * (colW + GAP) + PAD + W / 2) * S, oy = (10 + PAD + H / 2) * S;
  const P = (p) => `${f(ox + (p.x / 10) * S)},${f(oy - (p.y / 10) * S)}`;
  const R = (r) => r.map(([x, y]) => `${f(ox + x * S)},${f(oy - y * S)}`).join(" ");
  svg.push(`<text x="${f((col * (colW + GAP) + PAD) * S)}" y="${f(7 * S)}" font-size="${f(Math.max(14, 3.4 * S))}" font-weight="600">fillColumns ${on ? "on (the Studio since 2026-10-08)" : "off (before)"}</text>`);
  for (const r of t.g.rings) svg.push(`<polygon points="${R(r)}" fill="none" stroke="#c4cbd3" stroke-width="0.8"/>`);
  const chains = [];
  for (const [p, q] of t.sewn) { const last = chains[chains.length - 1]; if (last && last[last.length - 1] === p) last.push(q); else chains.push([p, q]); }
  svg.push(`<path d="${chains.map((c) => "M" + c.map(P).join(" ")).join("")}" stroke="#1b3a5c" stroke-width="0.6" stroke-opacity="0.6" fill="none"/>`);
  const fl = (leaves) => t.floats.filter((x) => x[2] === leaves).map(([p, q]) => `M${P(p)}L${P(q)}`).join("");
  svg.push(`<path d="${fl(false)}" stroke="#e8a0a0" stroke-width="0.8" fill="none"/>`);
  svg.push(`<path d="${fl(true)}" stroke="#d81e1e" stroke-width="1.4" fill="none"/>`);
  for (const c of t.cuts) svg.push(`<circle cx="${P(c).split(",")[0]}" cy="${P(c).split(",")[1]}" r="3" fill="#f08c00" stroke="#7a4300" stroke-width="0.8"/>`);
  svg.push(`<text x="${f((col * (colW + GAP) + PAD) * S)}" y="${f((10 + 2 * PAD + H + 6) * S)}" font-size="${f(Math.max(12, 2.6 * S))}" fill="${t.off ? "#b01212" : "#1a6b2f"}">${esc(`${t.off} floats leave the fill (${Math.round(t.offMm)} mm) · ${t.floats.length} floats in all · ${t.cuts.length} cuts · ${t.stitches.toLocaleString("en-US")} stitches`)}</text>`);
});
svg.push("</svg>");
writeFileSync(OUT, svg.join("\n"));
const [a, b] = arms.map((x) => x.t);
console.log(`${basename(SRC)} on ${GARMENT}, ${N_COLORS} colours, ${f(W)} x ${f(H)} mm -> ${OUT}`);
console.log(`floats leaving the fill: ${a.off} (${Math.round(a.offMm)} mm) -> ${b.off} (${Math.round(b.offMm)} mm)`);
console.log(`cuts: ${a.cuts.length} -> ${b.cuts.length}; stitches: ${a.stitches} -> ${b.stitches} (${b.stitches >= a.stitches ? "+" : ""}${f(((b.stitches - a.stitches) / a.stitches) * 100)}%)`);
