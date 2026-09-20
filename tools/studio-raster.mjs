#!/usr/bin/env node
// tools/studio-raster.mjs — write the raster the Studio ACTUALLY sends the
// digitizer, so an engine measurement reads the pixels a customer's job reads.
//
// DigitizePanel downsamples every upload to PROCESS_MAX_PX = 1200 on its long
// edge (a localStorage-size choice — `app/src/ui/DigitizePanel.svelte`)
// through `loadImage` + `rasterSize` (`app/src/lib/rasterize.js`), a 2D canvas
// `drawImage`, and `toDataURL("image/png")`, BEFORE the service ever sees the
// pixels. Seven of the nine REAL_ART corpus logos are larger than that, so a
// measurement on the file in `digitizer/testdata/` reads a raster no customer
// sends. Found 2026-09-19: the quality-report e2e's ENTHUSIAST job read 2,311
// stitches / 9 trims / grade A through the Studio and the same file read
// 2,318 / 14 / grade B straight into the engine — and no cv2 resample of the
// file reproduces the browser's (INTER_AREA 14 trims, INTER_LINEAR 13).
//
// So this script approximates nothing: it loads the checkout's `rasterize.js`
// verbatim into the Playwright Chromium the e2e suite already uses, calls the
// panel's two functions and makes the panel's canvas calls, and writes the
// PNG the panel would have uploaded.
//
//   node tools/studio-raster.mjs [--out DIR] [--max 1200] [--smoothing high] FILE...
//
// `--smoothing low|medium|high` sets the canvas's `imageSmoothingQuality`
// before the draw. The panel sets NOTHING (Chrome's default is "low", a
// bilinear tap with no area averaging, which is what turns a 1585-px tires
// logo into 14 trims where cv2's INTER_AREA at the same size reads 8) — so
// the default here is the panel's, and the flag exists to measure a candidate
// Studio fix with the same instrument. Output names carry the choice
// (`.studio-high.png`) so a capped raster is never mistaken for the panel's.
//
// Writes DIR/<basename>.studio.png; DIR defaults to
// digitizer/.cache/studio-raster (gitignored). Needs app/node_modules
// (`cd app && npm install`); launches /opt/pw-browsers/chromium when that path
// exists (the cloud sandbox, where Playwright's own download is blocked) and
// Playwright's default browser otherwise — the same rule as
// app/playwright.config.js.
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const usage = "usage: node tools/studio-raster.mjs [--out DIR] [--max 1200] [--smoothing low|medium|high] FILE...";

const args = process.argv.slice(2);
let out = join(root, "digitizer", ".cache", "studio-raster");
let max = 1200;
// null = leave the canvas default alone, exactly as the panel does.
let smoothing = null;
const files = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--out") out = resolve(args[++i]);
  else if (args[i] === "--max") max = Number(args[++i]);
  else if (args[i] === "--smoothing") smoothing = args[++i];
  else if (args[i] === "--help" || args[i] === "-h") { console.log(usage); process.exit(0); }
  else files.push(args[i]);
}
if (!files.length || !Number.isFinite(max) || max < 1 || (smoothing !== null && !["low", "medium", "high"].includes(smoothing))) {
  console.error(usage);
  process.exit(2);
}
mkdirSync(out, { recursive: true });

// The Studio's own module, byte for byte, exposed on window for evaluate().
const rasterizeSrc = readFileSync(join(root, "app", "src", "lib", "rasterize.js"), "utf8");
const require = createRequire(join(root, "app", "package.json"));
const { chromium } = require("playwright");
const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium";
const browser = await chromium.launch(existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {});
try {
  const page = await browser.newPage();
  await page.setContent("<!doctype html><html><body></body></html>");
  await page.addScriptTag({
    type: "module",
    content: rasterizeSrc + "\nwindow.__studio = { loadImage, rasterSize, isVectorFile };",
  });
  await page.waitForFunction(() => Boolean(window.__studio));

  // What a real file picker assigns; `loadImage` needs the type for the
  // createImageBitmap path and `isVectorFile` reads it first.
  const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                 ".gif": "image/gif", ".bmp": "image/bmp", ".svg": "image/svg+xml" };
  for (const f of files) {
    const ext = extname(f).toLowerCase();
    const res = await page.evaluate(async ({ b64, name, type, max, smoothing }) => {
      const bin = atob(b64);
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      const file = new File([arr], name, { type });
      const { loadImage, rasterSize, isVectorFile } = window.__studio;
      // DigitizePanel.onFile, verbatim from here to the data URL.
      const img = await loadImage(file);
      const { w, h } = rasterSize(img, max, { vector: isVectorFile(file) });
      const cv = document.createElement("canvas");
      cv.width = w;
      cv.height = h;
      const ctx = cv.getContext("2d");
      if (smoothing) ctx.imageSmoothingQuality = smoothing;   // never set by the panel
      ctx.drawImage(img, 0, 0, w, h);
      const dataUrl = cv.toDataURL("image/png");
      return { w, h, iw: img.width, ih: img.height, b64: dataUrl.slice(dataUrl.indexOf(",") + 1) };
    }, { b64: readFileSync(f).toString("base64"), name: basename(f), type: MIME[ext] || "", max, smoothing });
    const target = join(out, basename(f, ext) + (smoothing ? `.studio-${smoothing}.png` : ".studio.png"));
    writeFileSync(target, Buffer.from(res.b64, "base64"));
    console.log(`${f}: ${res.iw}x${res.ih} -> ${res.w}x${res.h}  ${target}`);
  }
} finally {
  await browser.close();
}
