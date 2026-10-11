// The SVG import risk gate (plan 2026-07-27-svg-import-and-shapes, Task 6,
// never run until 2026-10-11): real vector art through EMB.parseSVG and then
// EMB.buildQualityDesign, the way the Studio's IMAGE branch builds a design
// (app/src/lib/generate.js), and a picture of what comes out.
//
//   node tools/svg-import-gate.mjs [file.svg ...] [--out dir] [--width mm]
//        [--playwright <path to the playwright package>]
//
// With no files it runs the gate's own set: the e2e vector fixture, the
// Studio favicon, and the SVGs under docs/renders/svg-import-gate-2026-10-11/svg/.
//
// Per file it prints what the importer handed over (regions, shapes, holes,
// warnings), the stitches per thread in SEW order, and four pixel measures
// that compare the stitched result with what a browser paints for the same
// file (both rasterized in the same frame, 600 px wide):
//   wrong_top  painted, stitched, but the TOP thread is not the painted colour
//   extra      stitched where the browser paints nothing
//   missing    painted, not stitched at all
//   buried     stitched two or more times (overlaps are not resolved)
// each as a percent of the painted area. "Top thread" is the last region in
// sew order whose importer polygon covers the pixel; it ignores gaps between
// stitch rows, so it measures ORDER and COVERAGE, not density.
// Two arms are measured: `image` (darkOnTop, the image branch's light-to-dark
// sort) and `drawn` (darkOnTop:false, the manual branch's caller order).
//
// It writes one HTML sheet per arm (browser | importer stack | stitches) to a
// temp folder and, when Playwright can be loaded, screenshots each to
// <out>/<name>[-drawn|-today].jpg, plus <out>/results.json. A third arm,
// `today`, is what the Studio does with an SVG upload now (see todayRegions).
import "./_help.mjs";
import { readFileSync, writeFileSync, mkdirSync, readdirSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
globalThis.window = globalThis;
for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "svgpath", "svgimport", "dst", "dstimport", "exp", "pes", "svgexport", "stitchModel"]) require(`../src/${f}.js`);
const DG = require("../src/digitize.js"), FAB = require("../src/fabrics.js"), GAR = require("../src/garments.js");
const EMB = globalThis.EMB;

const args = process.argv.slice(2);
const take = (name, dflt) => { const i = args.indexOf(name); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const GATE = join(ROOT, "docs", "renders", "svg-import-gate-2026-10-11");
const OUT = take("--out", GATE);
const WIDTH_MM = Number(take("--width", 80));
const PW = take("--playwright", process.env.EMB_PLAYWRIGHT || null);
const files = args.length ? args : [
  join(ROOT, "app", "e2e", "fixtures", "vector_logo.svg"),
  join(ROOT, "app", "public", "favicon.svg"),
  ...readdirSync(join(GATE, "svg")).filter((f) => f.endsWith(".svg")).sort().map((f) => join(GATE, "svg", f)),
];
mkdirSync(OUT, { recursive: true });
const SHEETS = mkdtempSync(join(tmpdir(), "svg-import-gate-"));

const garment = GAR.getGarment("left_chest");
const fabric = FAB.getFabric(FAB.fabricForGarment(garment.id));
const bright = (rgb) => rgb[0] + rgb[1] + rgb[2];
const hex = (rgb) => "#" + rgb.map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0")).join("");
const f2 = (v) => +v.toFixed(3);
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

function viewBoxOf(text) {
  const m = /<\s*svg\b([^>]*)>/i.exec(text.replace(/<!--[\s\S]*?-->/g, ""));
  const a = m ? m[1] : "";
  const vb = /viewBox\s*=\s*["']([^"']+)["']/.exec(a);
  if (vb) return vb[1].trim().split(/[\s,]+/).map(Number);
  const w = parseFloat((/\bwidth\s*=\s*["']([^"']+)/.exec(a) || [])[1]) || 100;
  const h = parseFloat((/\bheight\s*=\s*["']([^"']+)/.exec(a) || [])[1]) || 100;
  return [0, 0, w, h];
}

function build(parsed, darkOnTop) {
  // The image branch of app/src/lib/generate.js, plus an explicit width so
  // every file sews at the same size.
  const d = DG.buildQualityDesign(parsed.regions, {
    garment, fabric, pxPerMm: parsed.pxPerMm, satinMaxWidthMm: 3.0, underlay: true,
    fillColumns: true, targetWidthMm: WIDTH_MM, offsetXMm: 0, offsetYMm: 0,
    ...(darkOnTop ? {} : { darkOnTop: false }),
  });
  // Sew order of regions: the engine's own sort (stable, brightness desc).
  const order = parsed.regions.map((r, i) => i);
  if (darkOnTop) order.sort((a, b) => bright(parsed.regions[b].rgb) - bright(parsed.regions[a].rgb));
  // Stitches per thread block, and sewn segments back in source units.
  const fit = d.fit, blocks = [];
  let block = 0, prev = null;
  const toSrc = (p) => [fit.cxPx + (p.x / 10 - fit.offsetXMm) / fit.mmPerPx, fit.cyPx - (p.y / 10 - fit.offsetYMm) / fit.mmPerPx];
  for (const s of d.stitches) {
    if (s.type === "end") break;
    if (s.type === "color") { block++; prev = null; continue; }
    if (s.type === "trim") { prev = null; continue; }
    if (!blocks[block]) blocks[block] = { stitches: 0, segs: [] };
    if (s.type === "stitch") {
      blocks[block].stitches++;
      if (prev) blocks[block].segs.push([toSrc(prev), toSrc(s)]);
      prev = s;
    } else prev = null; // a jump: not drawn
  }
  return { d, order, blocks, mmPerPx: fit ? fit.mmPerPx : 1 };
}

function ringsD(shape) {
  const ring = (r) => "M" + r.map((p) => f2(p.x) + "," + f2(p.y)).join("L") + "Z";
  return ring(shape.outer) + (shape.holes || []).map(ring).join("");
}

function sheet(name, text, parsed, arm) {
  const vb = viewBoxOf(text), vbs = vb.join(" ");
  const { d, order, blocks, mmPerPx } = arm;
  const stack = order.map((i) => parsed.regions[i]);
  // One <path> per SHAPE, not per region: evenodd across a region's shapes
  // would punch a hole wherever two same-colour shapes overlap.
  const shapePaths = (r, fill) => r.shapes.map((s) => `<path fill-rule="evenodd" fill="${fill}" d="${ringsD(s)}"/>`).join("");
  const stackSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vbs}">` + stack.map((r) => shapePaths(r, hex(r.rgb))).join("") + "</svg>";
  const tw = 0.35 / mmPerPx; // a 0.35 mm thread, drawn in source units
  const stitchSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vbs}"><rect x="${vb[0]}" y="${vb[1]}" width="${vb[2]}" height="${vb[3]}" fill="#8f969c"/>` +
    blocks.map((b, i) => {
      const c = d.colors[i] ? [d.colors[i].r, d.colors[i].g, d.colors[i].b] : [255, 0, 255];
      return `<path fill="none" stroke="${hex(c)}" stroke-width="${f2(tw)}" stroke-linecap="round" d="${b ? b.segs.map(([a, z]) => `M${f2(a[0])},${f2(a[1])}L${f2(z[0])},${f2(z[1])}`).join("") : ""}"/>`;
    }).join("") + "</svg>";
  const masks = stack.map((r) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vbs}">${shapePaths(r, "#000")}</svg>`);
  const b64 = (s) => "data:image/svg+xml;base64," + Buffer.from(s).toString("base64");
  const caption = [
    `${name}: ${parsed.regions.length} regions, ${d.stitchCount.toLocaleString("en-US")} stitches at ${WIDTH_MM} mm wide`,
    "sew order (thread, stitches): " + stack.map((r, k) => `${hex(r.rgb)} ${(blocks[k] ? blocks[k].stitches : 0).toLocaleString("en-US")}`).join(" → "),
    ...parsed.warnings.map((w) => "warning: " + w),
    parsed.warnings.length ? "" : "warnings: none",
  ].filter(Boolean);
  const W = 600, H = Math.round(W * vb[3] / vb[2]);
  const ih = Math.round(340 * vb[3] / vb[2]);
  return `<!doctype html><meta charset="utf-8"><title>${esc(name)}</title>
<style>body{margin:0;background:#fff;font:13px/1.35 system-ui,Segoe UI,Arial,sans-serif;color:#222}
.row{display:flex;gap:10px;padding:10px}figure{margin:0;width:340px}figure img{width:340px;height:${ih}px;display:block;border:1px solid #ccd;background:repeating-conic-gradient(#eee 0 25%,#fff 0 50%) 0 0/12px 12px}
figcaption{font-weight:600;margin-bottom:4px}pre{margin:0 10px 10px;white-space:pre-wrap;font:12px/1.4 Consolas,monospace}</style>
<div class="row"><figure><figcaption>1. what a browser paints</figcaption><img id="truth" src="${b64(text)}"></figure>
<figure><figcaption>2. what the importer hands over, in sew order</figcaption><img src="${b64(stackSvg)}"></figure>
<figure><figcaption>3. the stitches (thread on grey cloth)</figcaption><img src="${b64(stitchSvg)}"></figure></div>
<pre id="cap">${esc(caption.join("\n"))}</pre>
<script>
const W=${W},H=${H},masks=${JSON.stringify(masks.map(b64))},rgbs=${JSON.stringify(stack.map((r) => r.rgb))};
const load=(src)=>new Promise((ok,no)=>{const i=new Image();i.onload=()=>ok(i);i.onerror=no;i.src=src;});
const px=(img)=>{const c=document.createElement("canvas");c.width=W;c.height=H;const g=c.getContext("2d");g.drawImage(img,0,0,W,H);return g.getImageData(0,0,W,H).data;};
(async()=>{
  const T=px(await load(document.getElementById("truth").src));
  const M=[];for(const m of masks)M.push(px(await load(m)));
  let painted=0,wrong=0,extra=0,missing=0,buried=0;
  for(let p=0;p<W*H;p++){const o=p*4;let top=-1,n=0;for(let k=0;k<M.length;k++)if(M[k][o+3]>128){top=k;n++;}
    const tp=T[o+3]>128;if(tp)painted++;
    if(n>=2)buried++;
    if(!tp&&n)extra++;else if(tp&&!n)missing++;
    else if(tp&&n){const c=rgbs[top];const dd=Math.hypot(T[o]-c[0],T[o+1]-c[1],T[o+2]-c[2]);if(dd>60)wrong++;}}
  const pc=(v)=>+(100*v/Math.max(1,painted)).toFixed(1);
  window.__result={wrong_top:pc(wrong),extra:pc(extra),missing:pc(missing),buried:pc(buried)};
  document.getElementById("cap").textContent+="\\nvs the browser, % of painted area: wrong top thread "+pc(wrong)+" · stitched where nothing is painted "+pc(extra)+" · painted but not stitched "+pc(missing)+" · stitched twice or more "+pc(buried);
})().catch((e)=>{window.__result={error:String(e)};});
</script>`;
}

// Playwright is optional: without it the sheets are written, unmeasured.
let pw = null;
for (const t of [PW, join(ROOT, "app", "node_modules", "playwright")].filter(Boolean)) {
  try { pw = require(t); break; } catch { /* next */ }
}
const browser = pw ? await pw.chromium.launch() : null;
const tab = browser ? await (await browser.newContext({ viewport: { width: 1060, height: 120 } })).newPage() : null;
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);
const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
const { flatToRegions } = await lib("imageRegions.js");
const DEFAULT_COLORS = 4; // app/src/lib/project.js: a new image element's nColors, removeBg true

// TODAY's offline lane for the same file: the Studio rasterizes an SVG upload
// at WORK_MAX_PX on the long side (rasterize.js, `vector: true`) and traces
// it like any image (ImagePanel: flattenRGBA with the element defaults, then
// flatToRegions). The regions come back in raster px; they are mapped into
// the SVG's own viewBox so every sheet shares one frame.
async function todayRegions(text, vb) {
  const w = vb[2] >= vb[3] ? WORK_MAX_PX : Math.round(WORK_MAX_PX * vb[2] / vb[3]);
  const h = vb[2] >= vb[3] ? Math.round(WORK_MAX_PX * vb[3] / vb[2]) : WORK_MAX_PX;
  await tab.setContent("<!doctype html><body></body>");
  const b64 = await tab.evaluate(async ([src, w, h]) => {
    const img = new Image(); img.src = src; await img.decode();
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const g = c.getContext("2d"); g.drawImage(img, 0, 0, w, h);
    const d = g.getImageData(0, 0, w, h).data;
    let s = ""; for (let i = 0; i < d.length; i += 8192) s += String.fromCharCode.apply(null, d.subarray(i, i + 8192));
    return btoa(s);
  }, ["data:image/svg+xml;base64," + Buffer.from(text).toString("base64"), w, h]);
  const rgba = Uint8ClampedArray.from(Buffer.from(b64, "base64"));
  for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
  const reg = flatToRegions(flattenRGBA(rgba, w, h, { nColors: DEFAULT_COLORS, removeBg: true }));
  const s = vb[2] / w, m = (q) => ({ x: vb[0] + q.x * s, y: vb[1] + q.y * s });
  const regions = reg.regions.map((r) => ({ rgb: r.rgb, shapes: r.shapes.map((sh) => ({ outer: sh.outer.map(m), holes: (sh.holes || []).map((hh) => hh.map(m)) })) }));
  return { regions, pxPerMm: reg.pxPerMm / s, warnings: [] };
}

const results = [], pages = [];
for (const file of files) {
  const name = basename(file, ".svg");
  const text = readFileSync(file, "utf8");
  let parsed;
  try { parsed = EMB.parseSVG(text, { targetLongMm: 60 }); }
  catch (e) { console.log(`\n## ${name}\nparseSVG THREW: ${e && e.stack}`); results.push({ name, crash: String(e) }); continue; }
  console.log(`\n## ${name}`);
  for (const [i, r] of parsed.regions.entries()) {
    const xs = [];
    for (const s of r.shapes) for (const p of s.outer) xs.push(p.x);
    console.log(`  region ${i} ${hex(r.rgb)} rgb(${r.rgb.join(",")}) shapes=${r.shapes.length} holes=${r.shapes.reduce((n, s) => n + s.holes.length, 0)} x ${f2(Math.min(...xs))}..${f2(Math.max(...xs))}`);
  }
  for (const w of parsed.warnings) console.log("  warning:", w);
  const row = { name, regions: parsed.regions.length, warnings: parsed.warnings,
    imported: parsed.regions.map((r) => ({ rgb: hex(r.rgb), shapes: r.shapes.length, holes: r.shapes.reduce((n, s) => n + s.holes.length, 0) })), arms: {} };
  const arms = [];
  if (parsed.regions.length) arms.push(["image", parsed, true, "parseSVG, image branch: light-to-dark"], ["drawn", parsed, false, "parseSVG, drawn order: darkOnTop false"]);
  if (tab) arms.push(["today", await todayRegions(text, viewBoxOf(text)), true, `TODAY: rasterized at ${WORK_MAX_PX} px and traced, ${DEFAULT_COLORS} colours, background removed`]);
  for (const [armName, src, dark, label] of arms) {
    if (!src.regions.length) { row.arms[armName] = { stitches: 0 }; continue; }
    const arm = build(src, dark);
    if (arm.d.colors.length !== src.regions.length) console.log(`  NOTE ${armName}: ${arm.d.colors.length} thread blocks for ${src.regions.length} regions`);
    row.arms[armName] = { stitches: arm.d.stitchCount, colors: arm.d.colors.length, widthMM: f2(arm.d.widthMM), heightMM: f2(arm.d.heightMM),
      sew: arm.order.map((i, k) => ({ rgb: hex(src.regions[i].rgb), stitches: arm.blocks[k] ? arm.blocks[k].stitches : 0 })) };
    console.log(`  ${armName}: ${arm.d.stitchCount} stitches, ${arm.d.colors.length} threads, ${f2(arm.d.widthMM)} x ${f2(arm.d.heightMM)} mm; sew ` + row.arms[armName].sew.map((s) => `${s.rgb}:${s.stitches}`).join(" → "));
    const page = join(SHEETS, `${name}${armName === "image" ? "" : "-" + armName}.html`);
    writeFileSync(page, sheet(`${name} (${label})`, text, src, arm));
    pages.push({ row, armName, page });
  }
  results.push(row);
}

if (tab) {
  for (const { row, armName, page } of pages) {
    await tab.goto(pathToFileURL(page).href);
    await tab.waitForFunction(() => window.__result, null, { timeout: 30000 });
    row.arms[armName].vsBrowser = await tab.evaluate(() => window.__result);
    await tab.screenshot({ path: join(OUT, basename(page, ".html") + ".jpg"), type: "jpeg", quality: 82, fullPage: true });
    console.log(`  ${basename(page, ".html")}: ${JSON.stringify(row.arms[armName].vsBrowser)}`);
  }
  await browser.close();
} else console.log("\nPlaywright not found (pass --playwright <dir>): HTML sheets written to " + SHEETS + ", no JPEGs, no pixel measures, no TODAY arm.");
writeFileSync(join(OUT, "results.json"), JSON.stringify(results, null, 2) + "\n");
console.log("\nwrote " + join(OUT, "results.json"));
