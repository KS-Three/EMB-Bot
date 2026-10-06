// What the Studio's flatten costs on an image, step by step: every PNG under
// digitizer/testdata and digitizer/testdata/photo, at 2, 4 and 6 colours, with
// and without background removal. It is the table docs/scope-history.md
// carries for 2026-10-04, when the fourth step did not come back.
//
//   node tools/flatten-census.mjs [srcDir] [--only TEXT] [--hashes]
//
// srcDir: the engine to measure (default: this checkout's src). Point it at
// another checkout's src to measure that one. Commit 4e486f62 is the loop as
// it was with the counting added and nothing else, so its src is how the
// "before" column was made -- but give that one `--only`: with the background
// removed it needs minutes on four of the photographs and hours on
// photo_grass_macro.png.
// --only TEXT: only the images whose file name contains TEXT.
// --hashes: one line a setting, its name and the sha256 of the indices the
// flatten returns, and nothing else. Run it on two engines and diff the two
// outputs: that is the proof a change to the flatten moved no pixel.
//
// THE FLATTEN IS THE STUDIO'S OWN: app/src/lib/flatten.js `flattenRGBA` is
// called, with its own order and its own constants, on an image prepared the
// way ImagePanel prepares one (never scaled up, long side cut to WORK_MAX_PX,
// alpha under ALPHA_CUTOFF made 0). The four engine calls inside it are timed
// by wrapping them, not by repeating them here. One thing differs from the
// browser: the resample is tools/png.mjs's box average, not a canvas
// drawImage, so the pixels are near the Studio's and not the same.
//
// `walks` is how often absorbSmallRegions went over the whole image, counted by
// the engine itself (`opts.stats`); an engine from before the counting prints
// a dash. Times are one run each, in milliseconds, on whatever else the
// machine was doing.
import { readdirSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { decodePNG, downscale } from "./png.mjs";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const option = (name) => { const i = args.indexOf(name); return i === -1 ? null : args[i + 1]; };
const SRC = resolve(args[0] && !args[0].startsWith("--") ? args[0] : join(ROOT, "src"));
const ONLY = option("--only");
const HASHES = args.includes("--hashes");

// The engine as the Studio has it: every module on one global EMB. digitize.js
// brings in the rest, and app/src/lib/emb.js refuses to load without it.
for (const f of ["quantize.js", "flatten.js", "digitize.js"]) require(join(SRC, f));
const EMB = globalThis.EMB;
const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await import(pathToFileURL(join(ROOT, "app", "src", "lib", "flatten.js")).href);

// Time the four calls where the Studio makes them.
const STEPS = ["knockoutBackground", "medianCut", "modeFilter", "absorbSmallRegions"];
const ms = {};
let stats = null;
for (const name of STEPS) {
  const real = EMB[name];
  EMB[name] = (...a) => {
    if (name === "absorbSmallRegions") a[4] = { stats };
    const t0 = performance.now();
    const out = real(...a);
    ms[name] = performance.now() - t0;
    return out;
  };
}

const images = [];
for (const dir of ["digitizer/testdata", "digitizer/testdata/photo"]) {
  for (const f of readdirSync(join(ROOT, dir)).filter((f) => f.toLowerCase().endsWith(".png")).sort()) {
    if (!ONLY || f.includes(ONLY)) images.push(dir + "/" + f);
  }
}

const pad = (s, n) => String(s).padEnd(n), lp = (s, n) => String(s).padStart(n);
const fmt = (v) => (v === undefined ? "-" : v < 100 ? v.toFixed(1) : String(Math.round(v)));
if (!HASHES) {
  console.log(`engine: ${SRC}`);
  console.log(pad("image", 30), pad("col", 3), pad("bg", 2), pad("size", 8), lp("absorbed", 8), lp("walks", 9), lp("knock", 6), lp("median", 7), lp("mode", 6), lp("absorb", 9), lp("flatten", 9), " indices");
}
const rows = [];
for (const image of images) {
  let img = decodePNG(join(ROOT, image));
  if (Math.max(img.width, img.height) > WORK_MAX_PX) img = downscale(img, WORK_MAX_PX);
  const { width: w, height: h, rgba } = img;
  for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
  for (const removeBg of [false, true]) for (const nColors of [2, 4, 6]) {
    for (const name of STEPS) delete ms[name];
    stats = { absorbed: 0, imageWalks: 0 };
    const t0 = performance.now();
    const flat = flattenRGBA(rgba, w, h, { nColors, removeBg });
    const total = performance.now() - t0;
    const sha = createHash("sha256").update(Buffer.from(flat.indices.buffer, flat.indices.byteOffset, flat.indices.byteLength)).digest("hex");
    const counted = stats.imageWalks > 0;
    rows.push({ image, total, absorb: ms.absorbSmallRegions });
    if (HASHES) { console.log(`${image}|${nColors}|${removeBg ? 1 : 0}\t${sha}`); continue; }
    console.log(
      pad(image.split("/").pop().replace(/\.png$/i, ""), 30), pad(nColors, 3), pad(removeBg ? "y" : "n", 2), pad(w + "x" + h, 8),
      lp(counted ? stats.absorbed : "-", 8), lp(counted ? stats.imageWalks : "-", 9),
      lp(fmt(ms.knockoutBackground), 6), lp(fmt(ms.medianCut), 7), lp(fmt(ms.modeFilter), 6), lp(fmt(ms.absorbSmallRegions), 9), lp(fmt(total), 9), " " + sha.slice(0, 12)
    );
  }
}
if (!HASHES) {
  const worst = rows.reduce((a, b) => (b.absorb > a.absorb ? b : a), rows[0]);
  const over = (s) => rows.filter((r) => r.absorb > s * 1000).length;
  console.log(`${rows.length} settings. absorbSmallRegions: ${fmt(rows.reduce((s, r) => s + r.absorb, 0))} ms in all, longest ${fmt(worst.absorb)} ms (${worst.image.split("/").pop()}); over 1 s on ${over(1)}, over 10 s on ${over(10)}, over a minute on ${over(60)}.`);
}
