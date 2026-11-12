// Writes src/lib/starterThreads.js: a thread colour per colour block for each
// starter-pack design (public/starter/).
//
// Why it exists: a DST file carries no colours, so a starter design would
// land in the import lane's placeholder palette (dark grey, red, blue, ...)
// under a thumbnail showing the real art. The colours are read back from the
// pack's OWN art instead: the SVG is rasterized, the stitch bounding box is
// laid over the art's opaque bounding box, and each block takes the colour
// most of its thread lies on (sampled at the midpoint of every stitch).
// Nothing is re-digitized and no file in the pack changes.
//
// Run from app/ after the pack changes:  node scripts/derive-starter-threads.mjs
// It needs a Chromium (the SVGs are rasterized by a real browser), which is
// why the result is committed rather than computed in the Studio.
import { chromium } from "@playwright/test";
import { createRequire } from "node:module";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const APP = dirname(dirname(fileURLToPath(import.meta.url)));
const PACK = join(APP, "public", "starter");
const OUT = join(APP, "src", "lib", "starterThreads.js");
const { decodeDSTStandard } = createRequire(import.meta.url)(join(APP, "..", "src", "dstimport.js"));
const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium"; // see playwright.config.js

// Runs in the page. Returns one { rgb, share } per colour block, plus the two
// aspect ratios the overlay assumes are equal.
async function sample({ svgBase64, stitches }) {
  const img = new Image();
  img.src = "data:image/svg+xml;base64," + svgBase64;
  await img.decode();
  const W = 1280;
  const H = Math.round((W * img.naturalHeight) / img.naturalWidth);
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const g = canvas.getContext("2d");
  g.drawImage(img, 0, 0, W, H);
  const px = g.getImageData(0, 0, W, H).data;

  let ax0 = W, ax1 = -1, ay0 = H, ay1 = -1;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (px[(y * W + x) * 4 + 3] <= 24) continue;
      if (x < ax0) ax0 = x;
      if (x > ax1) ax1 = x;
      if (y < ay0) ay0 = y;
      if (y > ay1) ay1 = y;
    }
  }
  let sx0 = Infinity, sx1 = -Infinity, sy0 = Infinity, sy1 = -Infinity;
  for (const s of stitches) {
    if (s.type !== "stitch") continue;
    sx0 = Math.min(sx0, s.x);
    sx1 = Math.max(sx1, s.x);
    sy0 = Math.min(sy0, s.y);
    sy1 = Math.max(sy1, s.y);
  }
  // Stitch space is +y up; the image is +y down.
  const toPx = (s) => [
    ax0 + ((s.x - sx0) / (sx1 - sx0)) * (ax1 - ax0),
    ay0 + ((sy1 - s.y) / (sy1 - sy0)) * (ay1 - ay0),
  ];

  const blocks = [];
  let bins = new Map();
  let prev = null;
  const flush = () => {
    let best = null;
    let total = 0;
    for (const bin of bins.values()) {
      total += bin.n;
      if (!best || bin.n > best.n) best = bin;
    }
    blocks.push(
      best
        ? { rgb: [best.r, best.g, best.b].map((v) => Math.round(v / best.n)), share: best.n / total }
        : null
    );
    bins = new Map();
  };
  for (const s of stitches) {
    if (s.type === "color") { flush(); prev = null; continue; }
    if (s.type !== "stitch") { prev = null; continue; }
    if (prev) {
      const a = toPx(prev);
      const b = toPx(s);
      const x = Math.round((a[0] + b[0]) / 2);
      const y = Math.round((a[1] + b[1]) / 2);
      const i = (y * W + x) * 4;
      if (x >= 0 && x < W && y >= 0 && y < H && px[i + 3] >= 128) {
        // 16 levels per channel: close shades of a gradient count as one.
        const key = (px[i] >> 4) + "," + (px[i + 1] >> 4) + "," + (px[i + 2] >> 4);
        let bin = bins.get(key);
        if (!bin) bins.set(key, (bin = { n: 0, r: 0, g: 0, b: 0 }));
        bin.n++;
        bin.r += px[i];
        bin.g += px[i + 1];
        bin.b += px[i + 2];
      }
    }
    prev = s;
  }
  flush();
  return { blocks, artAspect: (ax1 - ax0) / (ay1 - ay0), stitchAspect: (sx1 - sx0) / (sy1 - sy0) };
}

const manifest = JSON.parse(readFileSync(join(PACK, "manifest.json"), "utf8"));
const browser = await chromium.launch(existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {});
const page = await browser.newPage();
const lines = [];
try {
  for (const d of manifest.designs) {
    const decoded = decodeDSTStandard(new Uint8Array(readFileSync(join(PACK, d.dst))));
    const res = await page.evaluate(sample, {
      svgBase64: readFileSync(join(PACK, d.art)).toString("base64"),
      stitches: decoded.stitches,
    });
    if (res.blocks.length !== d.colors || res.blocks.some((b) => !b)) {
      throw new Error(`${d.id}: ${res.blocks.filter(Boolean).length} of ${d.colors} blocks found a colour`);
    }
    const drift = Math.abs(res.artAspect / res.stitchAspect - 1);
    console.log(`${d.id}: ${d.colors} blocks, art/stitch aspect drift ${(drift * 100).toFixed(1)}%`);
    lines.push(`  ${JSON.stringify(d.id)}: ${JSON.stringify(res.blocks.map((b) => b.rgb))},`);
  }
} finally {
  await browser.close();
}

writeFileSync(
  OUT,
  `// GENERATED by scripts/derive-starter-threads.mjs -- do not edit by hand.
//
// One [r, g, b] per colour block of each starter-pack DST (public/starter/),
// in block order. A DST carries no colours; these are read back from the
// pack's own art, at the places each block's thread lies. They are a starting
// point the customer can change per block like on any import.
export const STARTER_THREADS = {
${lines.join("\n")}
};
`
);
console.log("wrote " + OUT);
