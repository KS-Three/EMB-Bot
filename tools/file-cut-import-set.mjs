// The lanes tools/file-cut-census.mjs's own three sets leave out, as a set it
// can read:
//
//   node tools/file-cut-census.mjs --set tools/file-cut-import-set.mjs
//
//   import     a stitch file through `buildImportedDesign`, as the Studio's
//              "Design file" element builds it: at its own size, made smaller
//              and larger, turned a quarter, and placed off the middle of the
//              hoop
//   pair       two elements of one project through `combineDesigns`, as
//              `generateAll` hands them over: the second starts where the
//              first one's thread was cut
//   digitized  the service's result as the Studio keeps it (the committed
//              fixture), through the same builder
//
// They are here because of what an imported file can START with. The builders
// open every run with a jump to its first stitch. A stitch file need not: its
// first record can be a stitch, and the builder then centres the design and
// moves it to where it was placed, so the stream's first record is a stitch
// far from the origin the writers start at. In a pair it is a stitch far from
// where the element before it was cut. That move is travel, and until
// 2026-10-07 the EXP writer sewed it.
//
// The stitch files are the repo's own (digitizer/testdata/reference and
// test/fixtures). FILE_CUT_DST_DIRS, a list of folders in the PATH's own
// syntax, adds more: files kept out of the repo are counted, never named.
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname, delimiter, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);

export default async function ({ DG, FAB, GAR }) {
  const EMB = globalThis.EMB;
  const { combineDesigns } = await lib("combine.js");
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions } = await lib("manualShapes.js");

  const files = [];
  const add = (dir, whose) => {
    if (!existsSync(dir)) return;
    for (const f of readdirSync(dir).filter((n) => /\.dst$/i.test(n)).sort()) {
      try { files.push({ whose, decoded: EMB.decodeDSTStandard(new Uint8Array(readFileSync(join(dir, f)))) }); } catch { /* not a DST the importer reads */ }
    }
  };
  add(join(ROOT, "digitizer", "testdata", "reference"), "the repo's files");
  add(join(ROOT, "test", "fixtures"), "the repo's files");
  for (const dir of (process.env.FILE_CUT_DST_DIRS || "").split(delimiter).filter(Boolean)) add(resolve(dir), "other files");
  // buildImportedDesign turns a copy when it turns, and reads the rest.
  const imported = (decoded, o) => EMB.buildImportedDesign(decoded, Object.assign({ blockColors: {} }, o));

  const designs = [];
  for (const f of files) for (const id of ["left_chest", "full_back", "hat_front"]) for (const scale of [null, 0.6, 1.5, 2.5]) for (const rot of [0, 90]) for (const off of [0, 30]) {
    const size = scale == null ? "as it is" : scale < 1 ? "made smaller" : "made larger";
    designs.push({ lane: `import, ${size} (${f.whose})`, sizeMm: null, make: () => imported(f.decoded, { garment: GAR.getGarment(id), targetWidthMm: scale == null ? undefined : f.decoded.widthMM * scale, rotationDeg: rot, offsetXMm: off, offsetYMm: -off }) });
  }

  // digitizer.js's decodedFromDesign, restated: drop `end`, centre on the box
  // of the stitches.
  const fx = JSON.parse(readFileSync(join(ROOT, "app", "src", "lib", "fixtures", "digitized-asym.json"), "utf8")).design;
  const st = fx.stitches.filter((s) => s.type !== "end").map((s) => ({ x: s.x, y: s.y, type: s.type }));
  const sewn = st.filter((s) => s.type === "stitch"), xs = sewn.map((s) => s.x), ys = sewn.map((s) => s.y);
  const cx = Math.round((Math.min(...xs) + Math.max(...xs)) / 2), cy = Math.round((Math.min(...ys) + Math.max(...ys)) / 2);
  for (const s of st) { s.x -= cx; s.y -= cy; }
  const service = { stitches: st, stitchCount: sewn.length, jumpCount: 0, trimCount: 0, colorCount: fx.colors.length, widthMM: (Math.max(...xs) - Math.min(...xs)) / 10, heightMM: (Math.max(...ys) - Math.min(...ys)) / 10, label: "" };
  for (const id of ["left_chest", "full_back", "hat_front"]) for (const scale of [null, 0.6, 1.5, 2.5, 4]) for (const rot of [0, 37, 90]) {
    designs.push({ lane: "digitized", sizeMm: null, make: () => imported(service, { garment: GAR.getGarment(id), targetWidthMm: scale == null ? undefined : service.widthMM * scale, rotationDeg: rot, offsetXMm: 0, offsetYMm: 0 }) });
  }

  // Three fonts: the first, the middle and the last of the shipped library.
  const dir = join(ROOT, "src", "fonts");
  const keys = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8")).fonts.map((f) => f.key);
  const fonts = [keys[0], keys[Math.floor(keys.length / 2)], keys[keys.length - 1]].map((key) => EMB.decodeFontBin(readFileSync(join(dir, "bin", key + ".embf"))));
  // `b` is { dg, extra }: the engine to build with and the builder options of
  // the arm, which reach the text and the shapes of a pair and nothing else.
  // An imported design is sewn as it was written, and by the engine measured:
  // the importer is not in the digitize.js a second engine hands over.
  const text = (font, t, g, y, b) => b.dg.buildLetteringDesign(font, t, Object.assign({ garment: g, pxPerMm: 8, underlay: true, rgb: [20, 20, 20], colorRanges: [], weightPreset: "normal", slantDeg: 0, offsetXMm: 0, offsetYMm: y, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, align: "center" }, b.extra));
  const shape = (kind, params, mm, g, y, b) => {
    const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points: shapePresetPoints(kind, params, mm), curves: {}, stitchType: "auto", colorRgb: [200, 30, 30], angleDeg: null }]);
    return b.dg.buildQualityDesign(regions, Object.assign({ garment: g, fabric: FAB.getFabric(FAB.fabricForGarment(g.id)), pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: mm, offsetXMm: 0, offsetYMm: y }, b.extra));
  };
  for (const id of ["left_chest", "full_back", "tote"]) {
    const g = GAR.getGarment(id);
    for (const font of fonts) {
      designs.push({ lane: "pair: text, then text", sizeMm: null, make: (b) => combineDesigns([text(font, "KENT", g, 20, b), text(font, "Schaefer", g, -20, b)]) });
      designs.push({ lane: "pair: text, then a shape", sizeMm: null, make: (b) => combineDesigns([text(font, "KENT", g, 20, b), shape("star", { points: 5, innerRatio: 0.45 }, 30, g, -25, b)]) });
      designs.push({ lane: "pair: a shape, then text", sizeMm: null, make: (b) => combineDesigns([shape("circle", {}, 30, g, 25, b), text(font, "KENT", g, -20, b)]) });
      for (const f of files) {
        designs.push({ lane: `pair: text, then an import (${f.whose})`, sizeMm: null, make: (b) => combineDesigns([text(font, "KENT", g, 25, b), imported(f.decoded, { garment: g, offsetXMm: 0, offsetYMm: -25 })]) });
        designs.push({ lane: `pair: an import, then text (${f.whose})`, sizeMm: null, make: (b) => combineDesigns([imported(f.decoded, { garment: g, offsetXMm: 0, offsetYMm: 25 }), text(font, "KENT", g, -25, b)]) });
      }
    }
    files.forEach((f, a) => designs.push({ lane: "pair: an import, then an import", sizeMm: null, make: () => combineDesigns([imported(f.decoded, { garment: g, offsetXMm: 0, offsetYMm: 25 }), imported(files[(a + 1) % files.length].decoded, { garment: g, offsetXMm: 0, offsetYMm: -25 })]) }));
  }

  return { designs, build: (d, extra, dg) => d.make({ dg: dg || DG, extra: extra || {} }), arms: { "as shipped": {} } };
}
