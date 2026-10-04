// What the browser's medial satin does with the Studio's preset shapes: which
// designs sew far more than their neighbours in size, how long their longest
// stitch is, how far short of the drawn shape they stop, how much of the
// drawn shape is under thread -- and, against a second tree, exactly which
// designs (in a picture: which shapes) a change to the engine moves.
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
//   node tools/satin-walk-census.mjs --cover               also, per satin design: the share of the drawn
//                                                          shape under thread, and how far outside it a needle lands
//   node tools/satin-walk-census.mjs --against <root> --dst
//                                                          also compare the bytes of the DST file each tree writes
//   node tools/satin-walk-census.mjs --images              the IMAGE lane instead: eight corpus logos (or
//                                                          --images a.png,b.png, paths from the repo root), each at
//                                                          its own size and at 40 mm, 4 colours, shape by shape
//   node tools/satin-walk-census.mjs --render out.png --shape star:12:0.15:20[:garment]
//                                                          draw one design, read back from its DST bytes
//                                                          (rect:<height>:<corner radius>:<width>; with
//                                                          --against, as that tree's engine builds it)
//   node tools/satin-walk-census.mjs --sheet out.png --shape S [--shape S ...]
//                                                          one row per shape; with --against each row is that
//                                                          tree's design beside this tree's, at one scale.
//                                                          S is as for --render, or circle:<size>, heart:<size>,
//                                                          image:<file.png>:<size or auto>[:<shape id to zoom on>]
//   --points 12:12  --sizes 10:30:1  --list                narrow the grid; print every out-of-line design
//
// A design is built exactly as `app/src/lib/generate.js` builds a `shape`
// element: the Studio's own ring (`shapePresetPoints`), `shapesToRegions`,
// `buildQualityDesign` with the garment's fabric preset, underlay on.
//
// A PICTURE is built as generate.js builds an `image` element: the Studio's
// own `flattenRGBA` and `flatToRegions`, then `buildQualityDesign`. Each tree
// flattens the picture itself, with its own modules. Two things are not the
// Studio's: the PNG is decoded and reduced to the Studio's work size by
// `tools/png.mjs` (a box filter, not a browser canvas), and every shape is
// given an id so its stitches can be told from its neighbours' (checked on
// every design: with and without the ids, the stitches are the same).
//
// OUT OF LINE: a satin design's stitches grow with its size and a fill's with
// the square of it, so the count is first divided by that, and then compared
// with the median of the same quantity over the ten sizes either side (same
// star, same garment, same tier). Over twice it, or under half, is out of
// line. A plain "against the size either side" test read the 20 mm star as
// normal: 19 and 21 mm had run away too.
//
// THE SAME DESIGN is one whose every stitch record (x, y, type), reported
// size and stitch count hash alike. THE SAME SHAPE, in a picture, is one
// whose own stitch records hash alike (a trim between two shapes belongs to
// neither; trims are counted per design).
//
// THREAD COVER: the design's outlines (`design.shapeOutlines`, field mm) are
// rasterized at 0.1 mm and every sewn stitch is drawn 0.4 mm wide, the Studio
// preview's own THREAD_WIDTH_MM. A shape's cover is the share of its cells
// under thread, anyone's. FARTHEST OUT is the shape's own needle point that
// lies farthest outside its own outline. Both are of the stitch plan: nothing
// here knows what thread does on cloth.
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
// For the 2026-10-04 spine change it is the same export of `59b30b02`.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import zlib from "node:zlib";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import { decodePNG, downscale } from "./png.mjs";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);
const flag = (name) => argv.includes(name);
const opt = (name, dflt) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : dflt; };
const opts = (name) => argv.flatMap((a, i) => (a === name ? [argv[i + 1]] : []));
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
  const src = (name) => require(path.join(srcDir, name));
  const lib = (name) => import(pathToFileURL(path.join(root, "app", "src", "lib", name)).href);
  return {
    root, counted, src, lib,
    DG: src("digitize.js"), GAR: src("garments.js"), FAB: src("fabrics.js"), DST: src("dst.js"), DSTIN: src("dstimport.js"),
    presets: await lib("shapePresets.js"), manual: await lib("manualShapes.js"),
  };
}
const fabricOf = (E, garmentId) => E.FAB.getFabric(E.FAB.fabricForGarment(garmentId));
function build(E, kind, params, sizeMm, garmentId) {
  const points = E.presets.shapePresetPoints(kind, params, sizeMm);
  const { regions, pxPerMm } = E.manual.shapesToRegions([
    { id: "shape", points, curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  globalThis.__walksAtGuard = 0;
  const t0 = Date.now();
  const design = E.DG.buildQualityDesign(regions, {
    garment: E.GAR.getGarment(garmentId), fabric: fabricOf(E, garmentId), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0,
  });
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of points) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
  return { design, ms: Date.now() - t0, walksAtGuard: globalThis.__walksAtGuard, ringWmm: (x1 - x0) / pxPerMm, ringHmm: (y1 - y0) / pxPerMm };
}
const digestOf = (design) => {
  const h = createHash("sha256");
  for (const s of design.stitches) h.update(s.x + "," + s.y + "," + s.type + ";");
  h.update("|" + design.widthMM + "|" + design.heightMM + "|" + design.stitchCount);
  return h.digest("hex");
};
function measure(design) {
  const st = design.stitches;
  let longest = 0, onPoint = 0, up = 0, upLongest = 0, sewing = false;
  for (let i = 1; i < st.length; i++) {
    const s = st[i];
    const d = Math.hypot(s.x - st[i - 1].x, s.y - st[i - 1].y) / 10;
    // a needle-up move once sewing has begun: the frame carries the thread from one run to the next
    if (s.type === "jump" && sewing) { up += d; if (d > upLongest) upLongest = d; }
    if (s.type !== "stitch") continue;
    sewing = true;
    if (d > longest) longest = d;
    if (d === 0 && st[i - 1].type === "stitch") onPoint++;
  }
  return { stitches: design.stitchCount, tier: design._debug.nSatin ? "satin" : design._debug.nFill ? "fill" : "none",
           longest, onPoint, up, upLongest, wMm: design.widthMM, hMm: design.heightMM, digest: digestOf(design) };
}

// ---- a picture, as the Studio's image lane builds it -------------------------
const IMAGES = ["photo/enthusiast_logo.png", "photo/logo_drone_thermal_badge.png", "photo/logo_gaulke_roofing.png", "logo_script_tires.png",
                "ribbon_curve.png", "becker_marine_logo.png", "logo_whitebg.png", "black_ground_holes.png"].map((f) => "digitizer/testdata/" + f);
async function imageLane(E) {
  if (E.image) return E.image;
  // The Studio's image modules reach the engine through the one global `EMB`,
  // and each tree's engine writes itself over it as it loads: so this tree's
  // whole engine is collected here and put back before its modules are run.
  const { ENGINE_KEYS } = await E.lib("emb.js");
  E.api = {};
  for (const k of ENGINE_KEYS) if (k !== "render.js" && k !== "pdfsheet.js") Object.assign(E.api, E.src(k));
  E.image = { flatten: await E.lib("flatten.js"), regions: await E.lib("imageRegions.js"), flats: new Map() };
  return E.image;
}
async function buildImage(E, rel, sizeMm, garmentId, nColors, noIds) {
  const L = await imageLane(E);
  Object.assign(globalThis.EMB, E.api);
  const key = rel + "|" + nColors;
  if (!L.flats.has(key)) {
    const img = downscale(decodePNG(path.join(ROOT, rel)), L.flatten.WORK_MAX_PX);
    const rgba = new Uint8ClampedArray(img.rgba);
    for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < L.flatten.ALPHA_CUTOFF) rgba[i] = 0;
    L.flats.set(key, JSON.stringify(L.regions.flatToRegions(L.flatten.flattenRGBA(rgba, img.width, img.height, { nColors, removeBg: false }))));
  }
  const reg = JSON.parse(L.flats.get(key));
  let n = 0;
  if (!noIds) for (const r of reg.regions) for (const s of r.shapes) s.id = "s" + n++;
  return E.DG.buildQualityDesign(reg.regions, {
    garment: E.GAR.getGarment(garmentId), fabric: fabricOf(E, garmentId), pxPerMm: reg.pxPerMm, satinMaxWidthMm: 3.0,
    underlay: true, targetWidthMm: sizeMm || undefined, offsetXMm: 0, offsetYMm: 0,
  });
}

// ---- per shape: what is sewn of it -------------------------------------------
const CELL_MM = 0.1, THREAD_MM = 0.4;
function shapesOf(design) {
  const outlines = design.shapeOutlines || [], st = design.stitches;
  if (!outlines.length) return [];
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const o of outlines) for (const p of o.points) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
  x0 -= 2; y0 -= 2; x1 += 2; y1 += 2;
  const gw = Math.ceil((x1 - x0) / CELL_MM), gh = Math.ceil((y1 - y0) / CELL_MM);
  // which shape each cell belongs to (even-odd over its outline and holes, at the cell's centre)
  const label = new Int32Array(gw * gh).fill(-1);
  outlines.forEach((o, si) => {
    const rings = [o.points].concat(o.holes || []);
    let ry0 = Infinity, ry1 = -Infinity;
    for (const p of o.points) { ry0 = Math.min(ry0, p[1]); ry1 = Math.max(ry1, p[1]); }
    for (let j = Math.max(0, Math.floor((ry0 - y0) / CELL_MM)); j <= Math.min(gh - 1, Math.ceil((ry1 - y0) / CELL_MM)); j++) {
      const wy = y0 + (j + 0.5) * CELL_MM, xs = [];
      for (const ring of rings) for (let k = 0; k < ring.length; k++) {
        const a = ring[k], b = ring[(k + 1) % ring.length];
        if ((a[1] <= wy && b[1] > wy) || (b[1] <= wy && a[1] > wy)) xs.push(a[0] + (b[0] - a[0]) * ((wy - a[1]) / (b[1] - a[1])));
      }
      xs.sort((p, q) => p - q);
      for (let m = 0; m + 1 < xs.length; m += 2)
        for (let i = Math.max(0, Math.ceil((xs[m] - x0) / CELL_MM - 0.5)); i <= Math.min(gw - 1, Math.floor((xs[m + 1] - x0) / CELL_MM - 0.5)); i++) label[j * gw + i] = si;
    }
  });
  // every sewn stitch, a disc of the thread's width run along it
  const thread = new Uint8Array(gw * gh), R = THREAD_MM / 2 / CELL_MM;
  const stamp = (grid, value, mx, my) => {
    const cx = (mx - x0) / CELL_MM, cy = (my - y0) / CELL_MM;
    for (let j = Math.floor(cy - R); j <= Math.ceil(cy + R); j++) for (let i = Math.floor(cx - R); i <= Math.ceil(cx + R); i++) {
      if (i < 0 || j < 0 || i >= gw || j >= gh) continue;
      if ((i + 0.5 - cx) ** 2 + (j + 0.5 - cy) ** 2 <= R * R) grid[j * gw + i] = value;
    }
  };
  // the stitch that ends on record i, drawn into a grid
  const lay = (grid, value, i) => {
    const ax = st[i - 1].x / 10, ay = st[i - 1].y / 10, bx = st[i].x / 10, by = st[i].y / 10;
    const steps = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) / (CELL_MM / 2)));
    for (let k = 0; k <= steps; k++) stamp(grid, value, ax + (bx - ax) * k / steps, ay + (by - ay) * k / steps);
  };
  for (let i = 1; i < st.length; i++) if (st[i].type === "stitch") lay(thread, 1, i);
  const area = new Float64Array(outlines.length), under = new Float64Array(outlines.length);
  for (let c = 0; c < label.length; c++) { const s = label[c]; if (s < 0) continue; area[s]++; if (thread[c]) under[s]++; }
  // its own records
  const own = outlines.map(() => ({ tier: null, stitches: 0, pts: [], sewn: [], up: 0, last: null, h: createHash("sha256") }));
  const byId = new Map(outlines.map((o, i) => [o.id, i]));
  for (const run of design.runs || []) {
    const si = outlines.length === 1 ? 0 : byId.get(run.shape);
    if (si == null) continue;
    const o = own[si];
    if (run.kind === "satin" || run.kind === "fill") o.tier = run.kind;
    // from the end of the shape's run before to the start of this one the frame moves with the needle up
    if (o.last != null) o.up += Math.hypot(st[run.i0].x - st[o.last].x, st[run.i0].y - st[o.last].y) / 10;
    o.last = run.i1;
    for (let i = run.i0; i <= run.i1; i++) {
      const s = st[i];
      o.h.update(s.x + "," + s.y + "," + s.type + ";");
      if (s.type === "stitch") { o.stitches++; o.pts.push(s); if (i > run.i0) o.sewn.push(i); }
    }
  }
  // a satin shape's cells under ITS OWN thread: in a picture a fill may run under a shape that lies on it
  const mine = new Int32Array(gw * gh), underOwn = new Float64Array(outlines.length);
  outlines.forEach((o, si) => {
    if (own[si].tier !== "satin") return;
    for (const i of own[si].sewn) lay(mine, si + 1, i);
    let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
    for (const p of o.points) { bx0 = Math.min(bx0, p[0]); bx1 = Math.max(bx1, p[0]); by0 = Math.min(by0, p[1]); by1 = Math.max(by1, p[1]); }
    for (let j = Math.max(0, Math.floor((by0 - y0) / CELL_MM)); j <= Math.min(gh - 1, Math.ceil((by1 - y0) / CELL_MM)); j++)
      for (let i = Math.max(0, Math.floor((bx0 - x0) / CELL_MM)); i <= Math.min(gw - 1, Math.ceil((bx1 - x0) / CELL_MM)); i++)
        if (label[j * gw + i] === si && mine[j * gw + i] === si + 1) underOwn[si]++;
  });
  const inside = (x, y, poly) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const a = poly[i], b = poly[j]; if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; };
  const toSeg = (x, y, a, b) => { const ex = b[0] - a[0], ey = b[1] - a[1], l2 = ex * ex + ey * ey; let u = l2 ? ((x - a[0]) * ex + (y - a[1]) * ey) / l2 : 0; u = Math.max(0, Math.min(1, u)); return Math.hypot(x - a[0] - ex * u, y - a[1] - ey * u); };
  return outlines.map((o, si) => {
    let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
    for (const p of o.points) { bx0 = Math.min(bx0, p[0]); bx1 = Math.max(bx1, p[0]); by0 = Math.min(by0, p[1]); by1 = Math.max(by1, p[1]); }
    let far = 0;
    if (own[si].tier === "satin") for (const s of own[si].pts) {
      const x = s.x / 10, y = s.y / 10;
      if (inside(x, y, o.points)) continue;
      let d = Infinity;
      for (let i = 0; i < o.points.length; i++) d = Math.min(d, toSeg(x, y, o.points[i], o.points[(i + 1) % o.points.length]));
      if (d > far) far = d;
    }
    return { id: o.id, tier: own[si].tier || (o.dropped ? "dropped" : "none"), areaMm2: area[si] * CELL_MM * CELL_MM, wMm: bx1 - bx0, hMm: by1 - by0,
             box: [bx0, by0, bx1, by1], cover: area[si] ? under[si] / area[si] : null, coverOwn: area[si] ? underOwn[si] / area[si] : null,
             far, upMm: own[si].up, stitches: own[si].stitches, digest: own[si].h.digest("hex") };
  });
}

// ---- drawing, from the file --------------------------------------------------
// every move of the design, read back from its DST bytes (field mm, y up)
function movesOf(E, design) {
  const data = E.DST.encodeDST(design).slice(512);
  const segs = [];
  let x = 0, y = 0, sewing = false, block = 0;
  for (let i = 0; i + 2 < data.length; i += 3) {
    if (data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 0xf3) break;
    const jump = (data[i + 2] & 0x80) !== 0, colour = (data[i + 2] & 0x40) !== 0;
    const [dx, dy] = E.DSTIN.decodeDelta(data[i], data[i + 1], data[i + 2]);
    if (colour) block++; else segs.push({ x0: x / 10, y0: y / 10, x1: (x + dx) / 10, y1: (y + dy) / 10, sewn: !jump && sewing, block });
    sewing = !jump && !colour; x += dx; y += dy;
  }
  return segs;
}
function canvas(W, H) {
  const px = Buffer.alloc(W * H * 4, 255);
  const dot = (ix, iy, c, alpha, clip) => {
    if (ix < clip[0] || iy < clip[1] || ix >= clip[2] || iy >= clip[3]) return;
    const o = (iy * W + ix) * 4;
    for (let k = 0; k < 3; k++) px[o + k] = Math.round(px[o + k] * (1 - alpha) + c[k] * alpha);
  };
  const line = (ax, ay, bx, by, c, alpha, clip = [0, 0, W, H]) => {
    // clipped to the panel before it is stepped: a move may start far outside a zoomed view
    if (Math.max(ax, bx) < clip[0] || Math.min(ax, bx) >= clip[2] || Math.max(ay, by) < clip[1] || Math.min(ay, by) >= clip[3]) return;
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) * 1.5));
    for (let i = 0; i <= n; i++) dot(Math.round(ax + (bx - ax) * i / n), Math.round(ay + (by - ay) * i / n), c, alpha, clip);
  };
  const save = (outPng) => {
    const raw = Buffer.alloc(H * (1 + W * 4));
    for (let r = 0; r < H; r++) px.copy(raw, r * (1 + W * 4) + 1, r * W * 4, (r + 1) * W * 4);
    const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
    const crc = (buf) => { let c = 0xffffffff; for (const v of buf) c = crcTable[(c ^ v) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
    const chunk = (type, body) => { const len = Buffer.alloc(4); len.writeUInt32BE(body.length); const t = Buffer.from(type, "latin1"); const sum = Buffer.alloc(4); sum.writeUInt32BE(crc(Buffer.concat([t, body]))); return Buffer.concat([len, t, body, sum]); };
    const head = Buffer.alloc(13); head.writeUInt32BE(W, 0); head.writeUInt32BE(H, 4); head[8] = 8; head[9] = 6;
    fs.writeFileSync(outPng, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", head), chunk("IDAT", zlib.deflateSync(raw, { level: 9 })), chunk("IEND", Buffer.alloc(0))]));
  };
  return { line, save };
}
// "star:12:0.15:20[:garment]", "rect:<height>:<corner radius>:<width>[:garment]", "circle:<size>", "heart:<size>"
function shapeSpec(spec) {
  const part = spec.split(":"), kind = part[0];
  if (kind === "star") return { kind, params: { points: +part[1], innerRatio: +part[2] }, size: +part[3], garmentId: part[4] || "left_chest" };
  if (kind === "rect") return { kind, params: { heightMm: +part[1], cornerRadiusMm: +part[2] }, size: +part[3], garmentId: part[4] || "left_chest" };
  return { kind, params: {}, size: +part[part.length > 3 ? 3 : 1], garmentId: (part.length > 3 ? part[4] : part[2]) || "left_chest" };
}
function render(E, spec, outPng) {
  const { kind, params, size, garmentId } = shapeSpec(spec);
  const { design } = build(E, kind, params, size, garmentId);
  const outline = (design.shapeOutlines[0] && design.shapeOutlines[0].points) || [];
  const scale = 800 / (Math.max(size, design.widthMM, design.heightMM) + 4), W = 800, H = 800;
  const cv = canvas(W, H);
  const X = (mm) => W / 2 + mm * scale, Y = (mm) => H / 2 - mm * scale;
  outline.forEach((p, i) => { const q = outline[(i + 1) % outline.length]; cv.line(X(p[0]), Y(p[1]), X(q[0]), Y(q[1]), [150, 150, 150], 1); });
  for (const s of movesOf(E, design)) cv.line(X(s.x0), Y(s.y0), X(s.x1), Y(s.y1), s.sewn ? [0, 0, 0] : [230, 30, 30], s.sewn ? 0.55 : 0.8);
  cv.save(outPng);
  const m = measure(design);
  console.log(`${spec}: ${m.stitches} stitches, ${m.tier}, sewn ${m.wMm.toFixed(1)} x ${m.hMm.toFixed(1)} mm, longest stitch ${m.longest.toFixed(1)} mm, ${m.onPoint} stitch records on the point before them`);
  console.log(`grey: the drawn shape; black: thread, as the DST bytes say; red: needle-up moves -> ${outPng} (${scale.toFixed(1)} px per mm)`);
}
async function sheet(engines, specs, outPng) {
  const PW = 800, GAP = 12, MARGIN_MM = 1.5;
  const rows = [];
  for (const spec of specs) {
    const part = spec.split(":"), isImage = part[0] === "image";
    const designs = [];
    for (const E of engines) {
      if (isImage) designs.push(await buildImage(E, part[1], part[2] === "auto" ? null : +part[2], "left_chest", 4));
      else { const s = shapeSpec(spec); designs.push(build(E, s.kind, s.params, s.size, s.garmentId).design); }
    }
    const moves = designs.map((d, i) => movesOf(engines[i], d));
    // the view: the one shape asked for and a margin, or everything drawn and sewn in either design
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const grow = (x, y) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); };
    const zoom = isImage && part[3];
    designs.forEach((d, i) => {
      for (const o of d.shapeOutlines) if (!zoom || o.id === zoom) for (const p of o.points) grow(p[0], p[1]);
      if (!zoom) for (const s of moves[i]) if (s.sewn) { grow(s.x0, s.y0); grow(s.x1, s.y1); }
    });
    if (!(x1 > x0)) throw new Error(`${spec}: nothing to draw`);
    rows.push({ spec, isImage, zoom, designs, moves, x0: x0 - MARGIN_MM, y0: y0 - MARGIN_MM, x1: x1 + MARGIN_MM, y1: y1 + MARGIN_MM });
  }
  for (const r of rows) { r.scale = Math.min(PW / (r.x1 - r.x0), 800 / (r.y1 - r.y0)); r.H = Math.ceil((r.y1 - r.y0) * r.scale); }
  const W = engines.length * PW + (engines.length - 1) * GAP, H = rows.reduce((a, r) => a + r.H, 0) + (rows.length - 1) * GAP;
  const cv = canvas(W, H);
  let top = 0;
  for (const r of rows) {
    r.designs.forEach((d, i) => {
      const left = i * (PW + GAP), clip = [left, top, left + PW, top + r.H];
      const X = (mm) => left + PW / 2 + (mm - (r.x0 + r.x1) / 2) * r.scale, Y = (mm) => top + r.H / 2 - (mm - (r.y0 + r.y1) / 2) * r.scale;
      for (const o of d.shapeOutlines) o.points.forEach((p, k) => { const q = o.points[(k + 1) % o.points.length]; cv.line(X(p[0]), Y(p[1]), X(q[0]), Y(q[1]), [150, 150, 150], 1, clip); });
      // zoomed on one shape of a picture: its colour's thread is black and every other colour's is faint
      const zoomBlock = r.zoom ? ((d.runs || []).find((q) => q.shape === r.zoom) || {}).block : null;
      for (const s of r.moves[i]) {
        // a picture's thread is drawn in its own colour, a pale one darkened so it shows on white
        let c = [0, 0, 0], alpha = r.isImage ? 0.7 : 0.55;
        if (r.isImage && d.colors[s.block]) { const t = d.colors[s.block]; c = [t.r, t.g, t.b]; if (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] > 170) c = c.map((v) => Math.round(v * 0.55)); }
        if (r.zoom) { if (s.block === zoomBlock) c = [0, 0, 0]; else alpha = 0.22; }
        cv.line(X(s.x0), Y(s.y0), X(s.x1), Y(s.y1), s.sewn ? c : [230, 30, 30], s.sewn ? alpha : (r.isImage ? 0.3 : 0.8), clip);
      }
      // the rule, bottom left
      const ruleMm = r.x1 - r.x0 < 12 ? 1 : r.x1 - r.x0 < 60 ? 5 : 10, ry = top + r.H - 7;
      cv.line(left + 8, ry, left + 8 + ruleMm * r.scale, ry, [0, 90, 200], 1, clip);
      for (const rx of [left + 8, left + 8 + ruleMm * r.scale]) cv.line(rx, ry - 4, rx, ry + 4, [0, 90, 200], 1, clip);
      r.ruleMm = ruleMm;
    });
    // between the panels and under the row
    for (let i = 1; i < engines.length; i++) for (let g = 0; g < GAP; g++) cv.line(i * (PW + GAP) - GAP + g, top, i * (PW + GAP) - GAP + g, top + r.H - 1, [225, 225, 225], 1);
    if (top + r.H < H) for (let g = 0; g < GAP; g++) cv.line(0, top + r.H + g, W - 1, top + r.H + g, [225, 225, 225], 1);
    const told = r.designs.map((d) => {
      const m = measure(d);
      if (!r.zoom) {
        const one = r.isImage ? null : shapesOf(d)[0];
        return `${m.stitches} stitches, sewn ${m.wMm.toFixed(1)} x ${m.hMm.toFixed(1)} mm, longest stitch ${m.longest.toFixed(1)} mm` +
               (one && one.cover != null ? `, ${(100 * one.cover).toFixed(0)}% of the drawn shape under thread, needle up for ${m.up.toFixed(1)} mm between its runs` : "");
      }
      const s = shapesOf(d).find((q) => q.id === r.zoom);
      return `shape ${r.zoom} (${s.wMm.toFixed(1)} x ${s.hMm.toFixed(1)} mm, ${s.tier}): ${s.stitches} stitches, ${(100 * s.coverOwn).toFixed(0)}% under its own thread (${(100 * s.cover).toFixed(0)}% under any)`;
    });
    console.log(`row ${rows.indexOf(r) + 1}  ${r.spec}  (${r.scale.toFixed(1)} px per mm; the blue rule is ${r.ruleMm} mm)\n    ` + told.join("\n    "));
    top += r.H + GAP;
  }
  cv.save(outPng);
  console.log(`grey: the drawn shapes; thread as the DST bytes say (black, or a picture's own colours); red: needle-up moves` +
              (engines.length > 1 ? `; left: ${engines[0].root}; right: this tree` : "") + ` -> ${outPng}`);
}

// ---- the census --------------------------------------------------------------
const here = await engine(ROOT, flag("--walks") && !opt("--against"));
const there = opt("--against") ? await engine(path.resolve(opt("--against")), flag("--walks")) : null;
// --render with --against draws the design as the OTHER tree's engine builds it
if (opt("--render")) { render(there || here, opt("--shape", "star:12:0.15:20"), opt("--render")); process.exit(0); }
if (opt("--sheet")) { await sheet(there ? [there, here] : [here], opts("--shape"), opt("--sheet")); process.exit(0); }

const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };
const quantile = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
const pct = (v) => (100 * v).toFixed(1) + "%";

if (flag("--images")) {
  const files = opt("--images") && opt("--images").endsWith(".png") ? opt("--images").split(",") : IMAGES;
  const garmentId = opt("--garments", "left_chest"), nColors = +opt("--colours", 4);
  const designs = [];
  for (const rel of files) for (const sizeMm of [null, 40]) {
    const one = async (E) => {
      const d = await buildImage(E, rel, sizeMm, garmentId, nColors);
      if (digestOf(await buildImage(E, rel, sizeMm, garmentId, nColors, true)) !== digestOf(d)) throw new Error(`${rel}: the stitches change when the shapes are given ids`);
      return { d, shapes: shapesOf(d), digest: digestOf(d), stitches: d.stitchCount, trims: d._debug.nTrims, order: (d.runs || []).map((r) => r.shape).filter((s, i, a) => s !== a[i - 1]).join(",") };
    };
    const row = { name: `${path.basename(rel, ".png")} ${sizeMm ? sizeMm + " mm" : "its own size"}`, here: await one(here), there: there ? await one(there) : null };
    designs.push(row);
    const sat = row.here.shapes.filter((s) => s.tier === "satin"), a = sat.reduce((t, s) => t + s.areaMm2, 0);
    console.log(`${row.name}: ${row.here.d.widthMM.toFixed(1)} x ${row.here.d.heightMM.toFixed(1)} mm, ${row.here.stitches} stitches, ${row.here.shapes.length} shapes, ${sat.length} of them satin` +
                (sat.length ? ` (${a.toFixed(0)} mm2, ${pct(sat.reduce((t, s) => t + s.coverOwn * s.areaMm2, 0) / a)} under their own thread, ${pct(sat.reduce((t, s) => t + s.cover * s.areaMm2, 0) / a)} under any, ${sat.reduce((t, s) => t + s.stitches, 0)} stitches)` : ""));
  }
  const all = designs.flatMap((r) => r.here.shapes.map((s) => ({ ...s, design: r.name })));
  const tier = (t) => all.filter((s) => s.tier === t);
  console.log(`\nIMAGES: ${files.length} pictures x 2 sizes on ${garmentId} at ${nColors} colours: ${designs.length} designs, ${all.length} shapes: satin ${tier("satin").length}, fill ${tier("fill").length}, not sewn ${all.length - tier("satin").length - tier("fill").length}`);
  const told = (label, sat) => {
    if (!sat.length) return;
    const f = sat.map((s) => s.far);
    for (const [name, c] of [["its own thread", sat.map((s) => s.coverOwn)], ["any thread", sat.map((s) => s.cover)]])
      console.log(`${label}SATIN shapes, share under ${name}: least ${pct(Math.min(...c))}, one in ten under ${pct(quantile(c, 0.1))}, median ${pct(quantile(c, 0.5))}; under 90%: ${c.filter((v) => v < 0.9).length} of ${sat.length}`);
    console.log(`${label}SATIN shapes, needle farthest outside the drawn shape: median ${quantile(f, 0.5).toFixed(2)} mm, one in ten over ${quantile(f, 0.9).toFixed(2)} mm, most ${Math.max(...f).toFixed(2)} mm`);
    const u = sat.map((s) => s.upMm);
    console.log(`${label}SATIN shapes, needle-up travel between a shape's own runs: median ${quantile(u, 0.5).toFixed(1)} mm, nine in ten under ${quantile(u, 0.9).toFixed(1)} mm, most ${Math.max(...u).toFixed(1)} mm, in all ${u.reduce((a, v) => a + v, 0).toFixed(0)} mm`);
  };
  told("", tier("satin"));
  if (there) {
    const pairs = [];
    for (const r of designs) {
      const other = new Map(r.there.shapes.map((s) => [s.id, s]));
      for (const s of r.here.shapes) pairs.push({ design: r.name, here: s, there: other.get(s.id) });
    }
    const lost = pairs.filter((p) => !p.there);
    const both = pairs.filter((p) => p.there), sat = both.filter((p) => p.here.tier === "satin" || p.there.tier === "satin"), rest = both.filter((p) => p.here.tier !== "satin" && p.there.tier !== "satin");
    const moved = (l) => l.filter((p) => p.here.digest !== p.there.digest);
    console.log(`\nAGAINST ${there.root}: designs the same ${designs.filter((r) => r.here.digest === r.there.digest).length}, moved ${designs.filter((r) => r.here.digest !== r.there.digest).length}` +
                (lost.length ? `; ${lost.length} SHAPES ARE NOT IN THE OTHER TREE'S DESIGN (the two trees flatten the picture differently)` : ""));
    console.log(`  shapes: satin moved ${moved(sat).length} of ${sat.length}; fill and unsewn shapes whose own stitch records differ ${moved(rest).length} of ${rest.length}; tier changed in ${both.filter((p) => p.here.tier !== p.there.tier).length}`);
    console.log(`  designs whose shapes are sewn in another order: ${designs.filter((r) => r.here.order !== r.there.order).length}; trims, there ${designs.reduce((t, r) => t + r.there.trims, 0)}, here ${designs.reduce((t, r) => t + r.here.trims, 0)} (changed in ${designs.filter((r) => r.here.trims !== r.there.trims).length} designs)`);
    told("  there: ", both.filter((p) => p.there.tier === "satin").map((p) => p.there));
    const s2 = sat.filter((p) => p.here.cover != null && p.there.cover != null);
    const dOwn = (p) => p.here.coverOwn - p.there.coverOwn, dAny = (p) => p.here.cover - p.there.cover;
    for (const [name, d] of [["its own thread", dOwn], ["any thread", dAny]])
      console.log(`  satin shapes, share under ${name}, here minus there: down over 2 points ${s2.filter((p) => d(p) < -0.02).length}, over 10 points ${s2.filter((p) => d(p) < -0.1).length}; up over 2 points ${s2.filter((p) => d(p) > 0.02).length}, over 10 points ${s2.filter((p) => d(p) > 0.1).length}`);
    const line = (p) => `    ${p.design}, ${p.here.id}: ${p.here.wMm.toFixed(1)} x ${p.here.hMm.toFixed(1)} mm, ${p.here.areaMm2.toFixed(1)} mm2 | own thread ${pct(p.there.coverOwn)} -> ${pct(p.here.coverOwn)} | any ${pct(p.there.cover)} -> ${pct(p.here.cover)} | ${p.there.stitches} -> ${p.here.stitches} stitches`;
    const down = s2.filter((p) => dOwn(p) < -0.02).sort((p, q) => dOwn(p) - dOwn(q)), up = s2.filter((p) => dOwn(p) > 0.02).sort((p, q) => dOwn(q) - dOwn(p));
    if (down.length) console.log("  the satin shapes that lose over 2 points of their own thread, worst first:\n" + down.slice(0, flag("--list") ? down.length : 12).map(line).join("\n"));
    if (up.length) console.log("  the satin shapes that gain over 2 points of their own thread, best first:\n" + up.slice(0, flag("--list") ? up.length : 12).map(line).join("\n"));
    console.log("  per design, its satin shapes: area | under their own thread, there -> here | under any thread | their stitches | the whole design's stitches | its trims");
    for (const r of designs) {
      const mine = sat.filter((p) => p.design === r.name);
      const a = mine.reduce((t, p) => t + p.here.areaMm2, 0);
      if (!mine.length) { console.log(`    ${r.name}: no satin shape | ${r.there.stitches} -> ${r.here.stitches}`); continue; }
      const share = (side, key) => pct(mine.reduce((t, p) => t + p[side][key] * p[side].areaMm2, 0) / a);
      console.log(`    ${r.name}: ${a.toFixed(0)} mm2 | ${share("there", "coverOwn")} -> ${share("here", "coverOwn")} | ${share("there", "cover")} -> ${share("here", "cover")} | ` +
                  `${mine.reduce((t, p) => t + p.there.stitches, 0)} -> ${mine.reduce((t, p) => t + p.here.stitches, 0)} | ${r.there.stitches} -> ${r.here.stitches} | ${r.there.trims} -> ${r.here.trims}`);
    }
  }
  process.exit(0);
}

const kind = opt("--kind", "star");
const garmentIds = opt("--garments", "left_chest") === "all" ? here.GAR.GARMENTS.map((g) => g.id) : opt("--garments", "left_chest").split(",");
const sizes = range(opt("--sizes", "10:100:1"));
const bags = [];
if (kind === "star") {
  const P = here.presets;
  for (const points of range(opt("--points", `${P.STAR_MIN_POINTS}:${P.STAR_MAX_POINTS}`)))
    for (const pc of range(opt("--ratios", `${Math.round(P.STAR_MIN_INNER_RATIO * 100)}:${Math.round(P.STAR_MAX_INNER_RATIO * 100)}:5`)))
      bags.push({ name: `${points} points, ratio ${(pc / 100).toFixed(2)}`, params: { points, innerRatio: pc / 100 } });
} else if (kind === "rect") {
  for (const heightMm of [1, 2, 3, 4, 6, 10, 20, 30, 60]) for (const cornerRadiusMm of [0, 0.5, 1.5, 5, 30])
    bags.push({ name: `${heightMm} mm tall, corner radius ${cornerRadiusMm}`, params: { heightMm, cornerRadiusMm } });
} else bags.push({ name: kind, params: {} });

const rows = [];
const t00 = Date.now();
for (const g of garmentIds) for (const bag of bags) {
  const series = [];
  for (const size of sizes) {
    const b = build(here, kind, bag.params, size, g);
    const fileOf = (E, design) => (flag("--dst") ? createHash("sha256").update(E.DST.encodeDST(design)).digest("hex") : null);
    const row = { g, bag: bag.name, size, ringWmm: b.ringWmm, ringHmm: b.ringHmm, ms: b.ms, walks: here.counted ? b.walksAtGuard : null, ...measure(b.design), dst: fileOf(here, b.design) };
    let o = null;
    if (there) {
      o = build(there, kind, bag.params, size, g);
      row.other = { ms: o.ms, walks: there.counted ? o.walksAtGuard : null, ...measure(o.design), dst: fileOf(there, o.design) };
    }
    // cover is measured where either tree sews satin (a fill both trees sew alike is not measured)
    if (flag("--cover") && (row.tier === "satin" || (o && row.other.tier === "satin"))) {
      const s = shapesOf(b.design)[0];
      row.cover = s.cover; row.far = s.far;
      if (o) { const t = shapesOf(o.design)[0]; row.other.cover = t.cover; row.other.far = t.far; }
    }
    series.push(row); rows.push(row);
  }
  // out of line, within this star on this garment (and the same for the other tree's builds)
  const judge = (of) => {
    // (a bar's height is fixed and its size is its length: a fill bar grows with its size too, not the square)
    const linear = (r) => of(r).tier === "satin" || kind === "rect";
    const norm = (i) => linear(series[i]) ? of(series[i]).stitches / series[i].size : of(series[i]).stitches / (series[i].size * series[i].size);
    series.forEach((r, i) => {
      const near = [];
      for (let j = Math.max(0, i - 10); j <= Math.min(series.length - 1, i + 10); j++) if (j !== i && of(series[j]).tier === of(r).tier) near.push(norm(j));
      if (near.length < 3) return;
      const mid = median(near);
      of(r).times = mid > 0 ? norm(i) / mid : 1;
      of(r).expected = Math.round(mid * (linear(r) ? r.size : r.size * r.size));
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
// where the hoop does not scale the design down
const fits = (r) => { const hoop = here.GAR.getGarment(r.g); return r.ringWmm < hoop.widthIn * 25.4 - 0.01 && r.ringHmm < hoop.heightIn * 25.4 - 0.01; };
// the satin designs of one tree (`of` picks the tree's own measures off a row), told under a label
function satinLines(label, of) {
  const sat = rows.filter((r) => of(r).tier === "satin");
  if (!sat.length) return;
  const L = sat.map((r) => of(r).longest);
  console.log(`${label}SATIN, longest single stitch: least ${Math.min(...L).toFixed(1)} mm, median ${quantile(L, 0.5).toFixed(1)} mm, nine in ten under ${quantile(L, 0.9).toFixed(1)} mm, longest ${Math.max(...L).toFixed(1)} mm; over 12.1 mm (one DST record): ${sat.filter((r) => of(r).longest > 12.1).length} of ${sat.length}`);
  if (kind === "rect") {
    // a bar's crosses span its SHORT side; a stitch nine tenths as long as the bar runs along it
    const along = (r) => of(r).longest >= 0.9 * Math.max(r.ringWmm, r.ringHmm);
    const sharp = sat.filter((r) => r.bag.endsWith("radius 0")), round = sat.filter((r) => !r.bag.endsWith("radius 0"));
    console.log(`${label}SATIN bars with a stitch at least nine tenths as long as the bar: sharp-cornered ${sharp.filter(along).length} of ${sharp.length}, round-cornered ${round.filter(along).length} of ${round.length}`);
    const over = (l) => l.map((r) => Math.min(of(r).wMm, of(r).hMm) - Math.min(r.ringWmm, r.ringHmm));
    if (sharp.length) console.log(`${label}SATIN bars, sewn short side minus drawn: sharp-cornered median ${quantile(over(sharp), 0.5).toFixed(1)} mm, most ${Math.max(...over(sharp)).toFixed(1)} mm; round-cornered median ${quantile(over(round), 0.5).toFixed(1)} mm, most ${Math.max(...over(round)).toFixed(1)} mm`);
    const long = (l) => l.filter(fits).map((r) => Math.max(of(r).wMm, of(r).hMm) - Math.max(r.ringWmm, r.ringHmm));
    for (const [name, l] of [["sharp-cornered", long(sharp)], ["round-cornered", long(round)]])
      if (l.length) console.log(`${label}SATIN bars, sewn long side minus drawn, ${name}: least ${Math.min(...l).toFixed(1)} mm, median ${quantile(l, 0.5).toFixed(1)} mm, most ${Math.max(...l).toFixed(1)} mm; over 0.5 mm short: ${l.filter((v) => v < -0.5).length} of ${l.length}`);
  }
  // for a shape whose own width is its extent
  const short = sat.filter((r) => fits(r) && kind !== "rect").map((r) => r.ringWmm - of(r).wMm);
  if (short.length) console.log(`${label}SATIN, drawn width minus sewn width: median ${quantile(short, 0.5).toFixed(1)} mm, one in ten over ${quantile(short, 0.9).toFixed(1)} mm, most ${Math.max(...short).toFixed(1)} mm`);
  console.log(`${label}SATIN, stitch records on the point before them: ${sat.reduce((a, r) => a + of(r).onPoint, 0)}; largest design ${Math.max(...sat.map((r) => of(r).stitches))} stitches; slowest ${Math.max(...sat.map((r) => of(r).ms))} ms`);
  const U = sat.map((r) => of(r).up), UL = sat.map((r) => of(r).upLongest);
  console.log(`${label}SATIN, needle-up travel between a design's runs: median ${quantile(U, 0.5).toFixed(1)} mm, nine in ten under ${quantile(U, 0.9).toFixed(1)} mm, most ${Math.max(...U).toFixed(1)} mm; longest single move: median ${quantile(UL, 0.5).toFixed(1)} mm, most ${Math.max(...UL).toFixed(1)} mm`);
  if (flag("--cover")) {
    const c = sat.map((r) => of(r).cover), f = sat.map((r) => of(r).far);
    console.log(`${label}SATIN, share of the drawn shape under thread: least ${pct(Math.min(...c))}, one in ten under ${pct(quantile(c, 0.1))}, median ${pct(quantile(c, 0.5))}; under 90%: ${sat.filter((r) => of(r).cover < 0.9).length} of ${sat.length}`);
    console.log(`${label}SATIN, needle farthest outside the drawn shape: median ${quantile(f, 0.5).toFixed(2)} mm, one in ten over ${quantile(f, 0.9).toFixed(2)} mm, most ${Math.max(...f).toFixed(2)} mm`);
  }
}
console.log("");
satinLines("", (r) => r);
if (here.counted) {
  const hit = rows.filter((r) => r.walks > 0);
  console.log(`\nWALKS only their guard stopped: in ${hit.length} of ${rows.length} designs (${hit.reduce((a, r) => a + r.walks, 0)} walks, all calls of skeletonEdges counted)`);
}
if (there) {
  const moved = rows.filter((r) => r.other.digest !== r.digest);
  console.log(`\nAGAINST ${there.root}: the same ${rows.length - moved.length}, moved ${moved.length} (${moved.filter((r) => r.other.tier === "fill").length} of them fills there; tier changed in ${rows.filter((r) => r.other.tier !== r.tier).length})`);
  const satinThere = rows.filter((r) => r.other.tier === "satin");
  const still = satinThere.filter((r) => r.other.digest === r.digest);
  console.log(`  satin there ${satinThere.length}: moved ${satinThere.length - still.length}, the same ${still.length}` +
              (still.length && still.length <= 40 ? ": " + still.map((r) => `${r.g} ${r.bag} ${r.size} mm (${r.stitches} stitches)`).join("; ") : ""));
  if (flag("--dst")) {
    const byFile = rows.filter((r) => r.other.dst !== r.dst);
    console.log(`  by the bytes of the DST file each tree writes: the same ${rows.length - byFile.length}, moved ${byFile.length}; moved by one measure and not by the other: ${rows.filter((r) => (r.other.dst !== r.dst) !== (r.other.digest !== r.digest)).length}`);
  }
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
  satinLines("  there: ", (r) => r.other);
  if (flag("--cover")) {
    const both = rows.filter((r) => r.cover != null && r.other.cover != null), d = (r) => r.cover - r.other.cover;
    console.log(`  share under thread, here minus there, over the ${both.length} designs satin in either tree: down over 2 points ${both.filter((r) => d(r) < -0.02).length}, over 10 points ${both.filter((r) => d(r) < -0.1).length}; up over 2 points ${both.filter((r) => d(r) > 0.02).length}, over 10 points ${both.filter((r) => d(r) > 0.1).length}`);
    const line = (r) => `    ${r.g} ${r.bag} ${r.size} mm: ${(100 * r.other.cover).toFixed(0)}% -> ${(100 * r.cover).toFixed(0)}% under thread, ${r.other.stitches} -> ${r.stitches} stitches`;
    const down = both.filter((r) => d(r) < -0.02).sort((p, q) => d(p) - d(q)), up = both.filter((r) => d(r) > 0.02).sort((p, q) => d(q) - d(p));
    if (down.length) console.log("  the designs that lose over 2 points, worst first:\n" + down.slice(0, flag("--list") ? down.length : 10).map(line).join("\n"));
    if (up.length) console.log("  the designs that gain over 2 points, best first:\n" + up.slice(0, flag("--list") ? up.length : 10).map(line).join("\n"));
  }
  if (flag("--list")) for (const r of moved) console.log(`    ${r.g} ${r.bag} ${r.size} mm: ${r.other.stitches} -> ${r.stitches} stitches, ${r.other.wMm.toFixed(1)} x ${r.other.hMm.toFixed(1)} -> ${r.wMm.toFixed(1)} x ${r.hMm.toFixed(1)} mm`);
}
