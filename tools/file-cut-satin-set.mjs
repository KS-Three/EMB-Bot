// Hand-drawn shapes SET TO SATIN, as a set tools/file-cut-census.mjs can read:
//
//   node tools/file-cut-census.mjs --set tools/file-cut-satin-set.mjs
//
// The census's own "manual" lane is all fills. A drawn shape whose stitch type
// is set to satin goes to the browser's medial satin instead (MASTER_SCOPE
// defect 57), and that is where the builder's stream holds a stitch that
// FOLLOWS travel from far away: the satin floats to another arm of the shape
// and sews back where it was. On `main` before 2026-10-07 the EXP writer
// sewed along that move.
//
// The shapes are the census's own 150: the generator below is the hand-drawn
// half of `shapes()` in tools/file-cut-census.mjs, copied whole (the cut-outs
// and the fill angle are drawn and thrown away, so that the random numbers
// fall as they do there). Each is built as generate.js builds a `manual`
// element, at the three sizes of that lane (fitted to the garment's placement,
// 25 mm and 60 mm) and on its six garments, with its stitch type "satin" and
// without its cut-outs, which would make it a fill.
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);

export default async function ({ DG, FAB, GAR }) {
  const { shapesToRegions, flattenShape, isValidShape, CANVAS_W, CANVAS_H } = await lib("manualShapes.js");
  const designs = [];
  let seed = 20261003;
  const rnd = () => { seed = (Math.imul(seed, 1103515245) + 12345) >>> 0; return seed / 4294967296; };
  const oneOfEach = ["hat_front", "left_chest", "beanie", "full_back", "tote", "towel"].map((id) => GAR.getGarment(id));
  for (let t = 0, made = 0; made < 150 && t < 2000; t++) {
    const n = 3 + Math.floor(rnd() * 12), reach = 60 + 120 * rnd(), whole = rnd() < 0.5;
    const snap = (v) => (whole ? Math.round(v) : Math.round(v * 100) / 100);
    const at = (cx, cy, r, a, wide) => ({ x: snap(Math.max(2, Math.min(CANVAS_W - 2, cx + wide * r * Math.cos(a)))), y: snap(Math.max(2, Math.min(CANVAS_H - 2, cy + r * Math.sin(a)))) });
    const points = [];
    for (let i = 0; i < n; i++) points.push(at(CANVAS_W / 2, CANVAS_H / 2, reach * (0.35 + 0.65 * rnd()), (2 * Math.PI * (i + 0.6 * (rnd() - 0.5))) / n, 1.4));
    const curves = {};
    for (let i = 0; i < n; i++) {
      if (rnd() >= 0.4) continue;
      const a = points[i], c = points[(i + 1) % n], bow = -0.2 + 0.5 * rnd();
      curves[i] = { x: (a.x + c.x) / 2 + bow * (c.y - a.y), y: (a.y + c.y) / 2 - bow * (c.x - a.x) };
    }
    if (!isValidShape(flattenShape(points, curves, true))) continue;
    for (let h = rnd() < 0.5 ? 1 + Math.floor(rnd() * 2) : 0; h > 0; h--) {
      const m = 4 + Math.floor(rnd() * 5), r = 8 + 22 * rnd(), off = 0.3 * reach * rnd(), dir = 2 * Math.PI * rnd(), turn = 2 * Math.PI * rnd();
      for (let i = 0; i < m; i++) at(CANVAS_W / 2 + off * Math.cos(dir), CANVAS_H / 2 + off * Math.sin(dir), r, turn + (2 * Math.PI * i) / m, 1);
    }
    rnd();   // the fill angle of that lane's second arm
    for (const sizeMm of [null, 25, 60]) for (const garment of oneOfEach) {
      designs.push({ lane: "hand-drawn, set to satin", list: [{ id: "s", points, curves, stitchType: "satin", colorRgb: [20, 20, 20], angleDeg: null }], sizeMm, garment });
    }
    made++;
  }
  const build = (d, extra, dg) => {
    const { regions, pxPerMm } = shapesToRegions(d.list);
    return (dg || DG).buildQualityDesign(regions, Object.assign({ garment: d.garment, fabric: FAB.getFabric(FAB.fabricForGarment(d.garment.id)), pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: d.sizeMm || undefined, offsetXMm: 0, offsetYMm: 0 }, extra));
  };
  return { designs, build, arms: { "as shipped": {} } };
}
