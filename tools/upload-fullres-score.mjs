// Score a vector upload's stitches against the SVG's OWN geometry, for the
// 1,200-px preview send (what an SVG uploads as today) and the 2,800-px
// full-resolution send (the upload_full_res switch ON), W5-08.
//
// Trims and stitches say the output CHANGED, not that it improved: more detail
// buys more trims, and a vector upload has no pro file to compare against. The
// SVG itself is the ground truth, so this renders it at the SEWN size and asks
// how closely the sewn coverage lies on it:
//
//   iou        intersection over union of the SVG's ink (anything not near-white)
//              and the sewn coverage (every sewn stitch drawn 0.4 mm wide)
//   edge       distance in mm from each edge pixel of one mask to the nearest
//              edge pixel of the other, both ways: mean, 95th percentile, max
//   bands      the same two numbers per line of lettering (small_text_logo.svg),
//              read at the cap height each line is sewn at
//
// The two sends are drawn exactly as the Studio draws them: the preview is the
// 1,200-px canvas at the browser's default smoothing, the full-res send the
// 2,800-px canvas at "high" (app/src/lib/rasterize.js). Both go through the
// Studio's own buildDigitizeConfig and digitize(), so the request is the one a
// customer's browser makes. The coverage is registered to the SVG by bounding-box
// centre (a global offset, not a fit); a scale correction is applied only if the
// sewn extent is more than 3% off the SVG's ink extent, and is reported.
//
// Writes score.json, score.md and one <name>__off_on.png per SVG into --out.
// Needs the digitizer service up (node tools/service-check.mjs) and Playwright
// (app/node_modules). A run is a service digitize: take the wave CPU lock first.
//
// Usage:
//   node tools/upload-fullres-score.mjs [svg ...] [--width-mm 100] [--garment left_chest] [--no-white]
//        [--px-per-mm 10] [--out docs/renders/upload-full-res-2026-10-27]
//        [--sizes 480,1200,2800] [--cache <dir>] [--from-cache]
//   Every digitized design is cached under --cache (default: the OS temp dir);
//   --from-cache re-scores from those files without touching the service.
//   --sizes: the long side in px of each send; 2800 is the full-resolution send, any
//   other is a preview-style send. At 100 mm wide the 1,200-px preview is 11.5 px/mm,
//   above the 8 px/mm work grid, so it and the 2,800-px send digitize alike. The case the
//   upload exists for is a 250 mm jacket back, whose 1,200-px preview is 4.8 px/mm; a
//   250 mm design cannot be digitized here inside the service's 600 s job limit, so that
//   case is EMULATED on the 100 mm design with a 480-px send (4.6 px/mm): the output
//   depends on px per mm and on the features' size in mm, not on the design's size.
//   default svgs: app/e2e/fixtures/small_text_logo.svg, app/e2e/fixtures/vector_logo.svg
import "./_help.mjs";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// ---- pure scoring: masks are { w, h, data: Uint8Array of 0/1 } ----------------

export function iou(a, b, rows = null) {
  const [r0, r1] = rows || [0, a.h];
  let inter = 0, uni = 0;
  for (let y = Math.max(0, r0); y < Math.min(a.h, r1); y++) {
    for (let x = 0; x < a.w; x++) {
      const p = a.data[y * a.w + x], q = b.data[y * a.w + x];
      if (p & q) inter++;
      if (p | q) uni++;
    }
  }
  return uni ? inter / uni : 1;
}

// A mask's edge: set pixels with a 4-neighbour that is clear (the image border counts as clear).
export function edgeOf(m) {
  const e = new Uint8Array(m.w * m.h);
  for (let y = 0; y < m.h; y++) {
    for (let x = 0; x < m.w; x++) {
      if (!m.data[y * m.w + x]) continue;
      const clear = (xx, yy) => xx < 0 || yy < 0 || xx >= m.w || yy >= m.h || !m.data[yy * m.w + xx];
      if (clear(x - 1, y) || clear(x + 1, y) || clear(x, y - 1) || clear(x, y + 1)) e[y * m.w + x] = 1;
    }
  }
  return { w: m.w, h: m.h, data: e };
}

// Exact Euclidean distance (px) from every pixel to the nearest set pixel of
// `m` (Felzenszwalb & Huttenlocher's two-pass squared transform).
export function distanceTo(m) {
  const BIG = 1e12;
  const { w, h } = m;
  const out = new Float64Array(w * h);
  for (let i = 0; i < out.length; i++) out[i] = m.data[i] ? 0 : BIG;
  const n = Math.max(w, h);
  const f = new Float64Array(n), d = new Float64Array(n), v = new Int32Array(n), z = new Float64Array(n + 1);
  const pass = (len, get, put) => {
    for (let i = 0; i < len; i++) f[i] = get(i);
    let k = 0;
    v[0] = 0; z[0] = -BIG; z[1] = BIG;
    for (let q = 1; q < len; q++) {
      let s;
      for (;;) {
        const p = v[k];
        s = ((f[q] + q * q) - (f[p] + p * p)) / (2 * q - 2 * p);
        if (s <= z[k]) k--; else break;
      }
      k++; v[k] = q; z[k] = s; z[k + 1] = BIG;
    }
    k = 0;
    for (let q = 0; q < len; q++) {
      while (z[k + 1] < q) k++;
      d[q] = (q - v[k]) * (q - v[k]) + f[v[k]];
    }
    for (let i = 0; i < len; i++) put(i, d[i]);
  };
  for (let x = 0; x < w; x++) pass(h, (y) => out[y * w + x], (y, val) => { out[y * w + x] = val; });
  for (let y = 0; y < h; y++) pass(w, (x) => out[y * w + x], (x, val) => { out[y * w + x] = val; });
  return Float64Array.from(out, Math.sqrt);
}

const stats = (xs) => {
  if (!xs.length) return { n: 0, mean: null, p95: null, max: null };
  const s = Float64Array.from(xs).sort();
  return { n: s.length, mean: s.reduce((a, b) => a + b, 0) / s.length, p95: s[Math.min(s.length - 1, Math.floor(0.95 * s.length))], max: s[s.length - 1] };
};

// Edge deviation in mm over the rows [r0, r1): `ab` = distance from the edge of
// `a` to the nearest edge of `b`, `ba` the other way, `both` the two pooled.
export function edgeDeviation(a, b, mmPerPx, rows = null) {
  const [r0, r1] = rows || [0, a.h];
  const ea = edgeOf(a), eb = edgeOf(b);
  const da = distanceTo(ea), db = distanceTo(eb);
  const ab = [], ba = [];
  for (let y = Math.max(0, r0); y < Math.min(a.h, r1); y++) {
    for (let x = 0; x < a.w; x++) {
      const i = y * a.w + x;
      if (ea.data[i]) ab.push(db[i] * mmPerPx);
      if (eb.data[i]) ba.push(da[i] * mmPerPx);
    }
  }
  return { ab: stats(ab), ba: stats(ba), both: stats(ab.concat(ba)) };
}

export function bbox(m) {
  let x0 = m.w, y0 = m.h, x1 = -1, y1 = -1;
  for (let y = 0; y < m.h; y++) for (let x = 0; x < m.w; x++) if (m.data[y * m.w + x]) {
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  return x1 < 0 ? null : { x0, y0, x1: x1 + 1, y1: y1 + 1 };
}

// ---- the browser half: draw the SVG and the stitches ----------------------------
// Everything below the pure functions runs only when the file is executed.

// In the page: the SVG's natural size as the panel's <img> sees it, then the two
// sends drawn the way the panel draws them.
const PAGE = {
  load: async function (svgB64) {
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = "data:image/svg+xml;base64," + svgB64; });
    window.__img = img;
    return { w: img.width, h: img.height };
  },
  send: async function ({ w, h, high }) {
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const ctx = cv.getContext("2d");
    if (high) { ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high"; }
    ctx.drawImage(window.__img, 0, 0, w, h);
    const blob = await new Promise((r) => cv.toBlob(r, "image/png"));
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  },
  // The SVG's ink at the sewn size: not near-white -> 1.
  truth: async function ({ w, h, offX, offY, cw, ch }) {
    const cv = document.createElement("canvas");
    cv.width = cw; cv.height = ch;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cw, ch);
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
    ctx.drawImage(window.__img, offX, offY, w, h);
    const px = ctx.getImageData(0, 0, cw, ch).data;
    const m = new Uint8Array(cw * ch);
    for (let i = 0; i < m.length; i++) m[i] = 255 - Math.min(px[i * 4], px[i * 4 + 1], px[i * 4 + 2]) > 127 ? 1 : 0;
    let bin = "";
    for (let i = 0; i < m.length; i += 0x8000) bin += String.fromCharCode(...m.subarray(i, i + 0x8000));
    return btoa(bin);
  },
  // Sewn coverage: every stitch segment that was sewn (the record's own type is
  // "stitch"), `thread` mm wide, at `S` px/mm, placed by (ox, oy) px.
  coverage: async function ({ stitches, cw, ch, S, thread, ox, oy, scale }) {
    const cv = document.createElement("canvas");
    cv.width = cw; cv.height = ch;
    const ctx = cv.getContext("2d");
    ctx.strokeStyle = "#000"; ctx.lineWidth = thread * S; ctx.lineCap = "round"; ctx.lineJoin = "round";
    ctx.beginPath();
    let prev = null;
    for (const s of stitches) {
      const x = ox + s.x / 10 * S * scale, y = oy - s.y / 10 * S * scale;
      if (s.type === "stitch" && prev && !s.skip) { ctx.moveTo(prev[0], prev[1]); ctx.lineTo(x, y); }
      prev = [x, y];
    }
    ctx.stroke();
    const a = ctx.getImageData(0, 0, cw, ch).data;
    const m = new Uint8Array(cw * ch);
    for (let i = 0; i < m.length; i++) m[i] = a[i * 4 + 3] > 127 ? 1 : 0;
    let bin = "";
    for (let i = 0; i < m.length; i += 0x8000) bin += String.fromCharCode(...m.subarray(i, i + 0x8000));
    return btoa(bin);
  },
  // OFF | ON beside the SVG, each at `view` px/mm, thread coloured per block.
  sheet: async function ({ panels, view, cwMm, chMm, zoom, svgBox }) {
    const pad = 12, head = 28;
    const pw = Math.round(cwMm * view), ph = Math.round(chMm * view);
    const zh = zoom ? Math.round(zoom.h * view * zoom.k) : 0;
    const cv = document.createElement("canvas");
    cv.width = pad + panels.length * (pw + pad); cv.height = head + ph + pad + (zoom ? zh + pad : 0);
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#f2efe8"; ctx.fillRect(0, 0, cv.width, cv.height);
    const draw = (p, ox, oy, k, clip) => {
      ctx.save();
      ctx.beginPath(); ctx.rect(ox, oy, clip.w, clip.h); ctx.clip();
      if (p.svg) {
        ctx.fillStyle = "#fff"; ctx.fillRect(ox, oy, clip.w, clip.h);
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(window.__img, ox + (svgBox.x - clip.x) * k, oy + (svgBox.y - clip.y) * k, svgBox.w * k, svgBox.h * k);
      } else {
        ctx.fillStyle = "#f2efe8"; ctx.fillRect(ox, oy, clip.w, clip.h);
        ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.lineWidth = 0.42 * view * k;
        let ci = 0, prev = null, last = -1;
        for (const s of p.stitches) {
          const x = ox + (p.ox + s.x / 10 * view * p.scale) * k - clip.x * k, y = oy + (p.oy - s.y / 10 * view * p.scale) * k - clip.y * k;
          if (s.type === "color") ci++;
          if (s.type === "stitch" && prev) {
            if (ci !== last) {
              ctx.stroke(); ctx.beginPath();
              const c = p.colors[ci] || p.colors[0] || { r: 0, g: 0, b: 0 };
              ctx.strokeStyle = `rgb(${c.r},${c.g},${c.b})`; last = ci;
            }
            ctx.moveTo(prev[0], prev[1]); ctx.lineTo(x, y);
          }
          prev = [x, y];
        }
        ctx.stroke();
      }
      ctx.restore();
    };
    ctx.font = "600 14px system-ui, sans-serif"; ctx.fillStyle = "#222";
    panels.forEach((p, i) => {
      const ox = pad + i * (pw + pad);
      ctx.fillText(p.label, ox, 19);
      draw(p, ox, head, 1, { x: 0, y: 0, w: pw, h: ph });
      ctx.strokeStyle = "#999"; ctx.lineWidth = 1; ctx.strokeRect(ox + 0.5, head + 0.5, pw, ph);
      if (zoom) {
        const zx = zoom.x * view, zy = zoom.y * view;
        draw(p, ox, head + ph + pad, zoom.k, { x: zx, y: zy, w: pw, h: zh });
        ctx.strokeRect(ox + 0.5, head + ph + pad + 0.5, pw, zh);
      }
    });
    return cv.toDataURL("image/png").split(",")[1];
  },
};

const fmt = (n, d = 2) => (n == null ? "–" : Number(n).toFixed(d));

function parseArgs(argv) {
  const o = { svgs: [], widthMm: 100, garment: "left_chest", keepWhite: true, S: 10, out: "docs/renders/upload-full-res-2026-10-27", sizes: [1200, 2800], only: null,
    cache: path.join(os.tmpdir(), "upload-fullres-score-cache"), fromCache: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--width-mm") o.widthMm = +argv[++i];
    else if (a === "--garment") o.garment = argv[++i];
    else if (a === "--no-white") o.keepWhite = false;
    else if (a === "--px-per-mm") o.S = +argv[++i];
    else if (a === "--out") o.out = argv[++i];
    else if (a === "--sizes") o.sizes = argv[++i].split(",").map(Number);
    else if (a === "--only") o.only = argv[++i];
    else if (a === "--cache") o.cache = argv[++i];
    else if (a === "--from-cache") o.fromCache = true;
    else o.svgs.push(a);
  }
  if (!o.svgs.length) o.svgs = ["app/e2e/fixtures/small_text_logo.svg", "app/e2e/fixtures/vector_logo.svg"];
  return o;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const { rasterSize } = await import("../app/src/lib/rasterize.js");
  const { buildDigitizeConfig, digitize } = await import("../app/src/lib/digitizer.js");
  const { defaultDigitizedElement, defaultProject } = await import("../app/src/lib/project.js");
  const { TEXT_LINES, SVG_W, SVG_H } = await import("./make-upload-fixtures.mjs");
  const require = createRequire(path.join(ROOT, "app", "package.json"));
  const { chromium } = require("playwright");

  const el = defaultDigitizedElement("e1");
  // The white field inside the frame is paper in the SVG and a fill in the sewn file
  // (sew_enclosed_white, the Studio's default, kept). It is left out of the coverage
  // below; --no-white drops it from the digitize too, which is much faster.
  el.params = { ...el.params, target_width_mm: opts.widthMm, sew_enclosed_white: opts.keepWhite };
  const cfg = buildDigitizeConfig(el, { ...defaultProject(), garmentId: opts.garment });
  const outDir = path.resolve(ROOT, opts.out);
  mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage();
  const results = [];
  try {
    for (const svgRel of opts.svgs) {
      const svgPath = path.resolve(ROOT, svgRel);
      const name = path.basename(svgPath).replace(/\.svg$/i, "");
      const natural = await page.evaluate(`(${PAGE.load})(${JSON.stringify(readFileSync(svgPath).toString("base64"))})`);
      const call = (fn, arg) => page.evaluate(`(${fn})(${JSON.stringify(arg)})`);

      // Ground truth at the sewn size, with a 6 mm margin for pull-comp overshoot.
      const aspect = natural.h / natural.w;
      const S = opts.S, margin = 6;
      const mmW = opts.widthMm, mmH = opts.widthMm * aspect;
      const cw = Math.round((mmW + 2 * margin) * S), ch = Math.round((mmH + 2 * margin) * S);
      const offX = Math.round(margin * S), offY = Math.round(margin * S);
      const truth = await call(PAGE.truth, { w: Math.round(mmW * S), h: Math.round(mmH * S), offX, offY, cw, ch });
      const gt = { w: cw, h: ch, data: new Uint8Array(Buffer.from(truth, "base64")) };
      const gtBox = bbox(gt);
      const mmPerPx = 1 / S;

      const lineBands = /small_text_logo/.test(name)
        ? TEXT_LINES.map((ln) => {
            const upm = mmW / SVG_W;   // mm per viewBox unit
            return {
              name: `${ln.text} (cap ${fmt(ln.capUnits * upm, 1)} mm)`,
              rows: [Math.round(offY + (ln.y0 - ln.capUnits * 1.25) * upm * S), Math.round(offY + (ln.y0 + ln.capUnits * 0.3) * upm * S)],
            };
          })
        : [];

      const panels = [{ label: "SVG (ground truth)", svg: true }];
      const rows = [];
      for (const size of opts.sizes) {
        const arm = size >= 2800 ? "on" : "off";
        // rasterSize reads { width, height } (a bare { w, h } silently draws 1 x 1).
        const dim = rasterSize({ width: natural.w, height: natural.h }, size, { vector: true });
        if (Math.max(dim.w, dim.h) !== size) throw new Error(`send size ${dim.w}x${dim.h} is not ${size} px on the long side`);
        const b64 = await call(PAGE.send, { w: dim.w, h: dim.h, high: size >= 2800 });
        const image = size < 2800 ? b64 : { bytes: new Uint8Array(Buffer.from(b64, "base64")), type: "image/png", name: `${name}.png` };
        mkdirSync(opts.cache, { recursive: true });
        const cacheFile = path.join(opts.cache, `${name}__${size}px__${opts.widthMm}mm_${opts.garment}${opts.keepWhite ? "" : "_nowhite"}.json`);
        let job, secs;
        if (opts.fromCache && existsSync(cacheFile)) {
          ({ job, secs } = JSON.parse(readFileSync(cacheFile, "utf8")));
        } else {
          const t0 = Date.now();
          try {
            job = await digitize(image, cfg, {});
          } catch (e) {
            // A 250 mm design can overrun the service's 600 s job limit: that is a
            // finding for the arm, not a reason to lose the other arm's numbers.
            secs = (Date.now() - t0) / 1000;
            const inkFracF = (gtBox.x1 - gtBox.x0) * mmPerPx / mmW;
            rows.push({
              svg: path.basename(svgPath), arm, size, pxPerMm: +(dim.w * inkFracF / opts.widthMm).toFixed(2), sendPx: `${dim.w}x${dim.h}`,
              secs: +secs.toFixed(1), error: `${e.kind || "error"}: ${String(e.message || e).slice(0, 160)}`, bands: [],
            });
            console.error(`${name} ${arm}: digitize FAILED after ${secs.toFixed(0)} s (${e.kind || "error"}: ${String(e.message || e).slice(0, 160)})`);
            continue;
          }
          secs = (Date.now() - t0) / 1000;
          writeFileSync(cacheFile, JSON.stringify({ job: { design: job.design, stats: job.stats }, secs }));
        }
        const design = job.design;

        // The ink is scored, so thread near white is left out of the coverage: the
        // Studio sews the white field inside a frame by default (sew_enclosed_white,
        // fabric-coloured on a white garment), which the SVG draws as paper.
        let ci = 0, whiteStitches = 0;
        const marked = design.stitches.map((s) => {
          if (s.type === "color") ci++;
          const c = (design.colors || [])[ci];
          const white = !!c && Math.min(c.r, c.g, c.b) > 235;
          if (white && s.type === "stitch") whiteStitches++;
          return { x: s.x, y: s.y, type: s.type, skip: white ? 1 : 0 };
        });
        // Register by bounding-box centre; scale only when the extent is >3% off.
        const sewn = [];
        let prev = null;
        for (const s of marked) { if (s.type === "stitch" && prev && !s.skip) sewn.push(prev, s); prev = s; }
        let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
        for (const s of sewn) { x0 = Math.min(x0, s.x / 10); x1 = Math.max(x1, s.x / 10); y0 = Math.min(y0, -s.y / 10); y1 = Math.max(y1, -s.y / 10); }
        const gtW = (gtBox.x1 - gtBox.x0) * mmPerPx, gtH = (gtBox.y1 - gtBox.y0) * mmPerPx;
        const ratio = ((x1 - x0) / gtW + (y1 - y0) / gtH) / 2;
        // Pixels of the send per sewn mm of ink: the service scales the art's own
        // bounding box to the target width, so the ink spans inkFrac of the send.
        const inkFrac = gtW / mmW, pxPerMm = dim.w * inkFrac / opts.widthMm;
        const scale = Math.abs(ratio - 1) > 0.03 ? 1 / ratio : 1;
        const gcx = (gtBox.x0 + gtBox.x1) / 2 / S, gcy = (gtBox.y0 + gtBox.y1) / 2 / S;
        const ox = (gcx - ((x0 + x1) / 2) * scale) * S, oy = (gcy - ((y0 + y1) / 2) * scale) * S;   // y0,y1 are image-y (-stitch y)
        const cov64 = await call(PAGE.coverage, { stitches: marked, cw, ch, S, thread: 0.4, ox, oy, scale });
        const cov = { w: cw, h: ch, data: new Uint8Array(Buffer.from(cov64, "base64")) };

        const count = (m) => m.data.reduce((a, b) => a + b, 0);
        const covBox = bbox(cov);
        const diag = {
          whiteStitches, gtInkMm2: +(count(gt) * mmPerPx * mmPerPx).toFixed(1), covInkMm2: +(count(cov) * mmPerPx * mmPerPx).toFixed(1),
          gtBoxMm: [gtBox.x0, gtBox.y0, gtBox.x1, gtBox.y1].map((v) => +(v * mmPerPx).toFixed(1)),
          covBoxMm: covBox && [covBox.x0, covBox.y0, covBox.x1, covBox.y1].map((v) => +(v * mmPerPx).toFixed(1)),
        };
        {
          // GT only = red, sewn only = blue, both = near-black, neither = white.
          const rgba = new Uint8ClampedArray(cw * ch * 4);
          for (let i = 0; i < cw * ch; i++) {
            const g = gt.data[i], c = cov.data[i];
            const [r, gg, b] = g && c ? [30, 30, 40] : g ? [220, 60, 60] : c ? [70, 110, 230] : [255, 255, 255];
            rgba.set([r, gg, b, 255], i * 4);
          }
          const { encodePNG } = await import("./png.mjs");
          writeFileSync(path.join(outDir, `${name}__${size}px__overlay.png`), Buffer.from(encodePNG(cw, ch, rgba)));
        }
        const whole = { iou: iou(gt, cov), edge: edgeDeviation(gt, cov, mmPerPx), diag };
        const bands = lineBands.map((b) => ({
          name: b.name, iou: iou(gt, cov, b.rows), edge: edgeDeviation(gt, cov, mmPerPx, b.rows),
        }));
        const st = job.stats || {};
        rows.push({
          svg: path.basename(svgPath), arm, size, pxPerMm: +pxPerMm.toFixed(2), sendPx: `${dim.w}x${dim.h}`, secs: +secs.toFixed(1),
          stitches: st.stitch_count, trims: st.trims, jumps: st.jumps, colorChanges: st.color_changes,
          sizeMm: st.size_mm, extentRatio: +ratio.toFixed(4), scaleApplied: +scale.toFixed(4),
          whole, bands,
        });
        panels.push({ label: `${size >= 2800 ? "ON" : "OFF"} · ${size.toLocaleString("en-US")} px (${pxPerMm.toFixed(1)} px/mm)`, stitches: design.stitches, colors: design.colors || [], ox, oy, scale });
        console.error(`${name} ${arm}: ${st.stitch_count} stitches, ${st.trims} trims, iou ${fmt(whole.iou, 4)}, edge mean ${fmt(whole.edge.both.mean, 3)} mm (${secs.toFixed(0)} s)`);
      }

      // Sheet: each panel is the whole canvas (margin included) at 6 px/mm; the
      // second row zooms 2.5x on the smallest line of lettering.
      const view = 5;
      const sheetPanels = panels.map((p) => p.svg ? p : { ...p, ox: p.ox / S * view, oy: p.oy / S * view });
      const zoom = lineBands.length
        ? { x: margin + 0.26 * mmW, y: lineBands[2].rows[0] / S, h: (lineBands[2].rows[1] - lineBands[2].rows[0]) / S + 2, k: 2.5 }
        : null;
      const sheet = await call(PAGE.sheet, {
        panels: sheetPanels, view, cwMm: mmW + 2 * margin, chMm: mmH + 2 * margin, zoom,
        svgBox: { x: margin * view, y: margin * view, w: mmW * view, h: mmH * view },
      });
      writeFileSync(path.join(outDir, `${name}__off_on.png`), Buffer.from(sheet, "base64"));
      results.push(...rows);
    }
  } finally {
    await browser.close();
  }

  writeFileSync(path.join(outDir, "score.json"), JSON.stringify({ widthMm: opts.widthMm, garment: opts.garment, pxPerMm: opts.S, rows: results }, null, 2));
  const md = [
    `Scored at ${opts.widthMm} mm wide, garment ${opts.garment}, ${opts.S} px/mm, coverage = sewn stitches of non-white thread drawn 0.4 mm wide; sew_enclosed_white ${opts.keepWhite ? "on (the Studio default)" : "off (the SVG draws that field as paper, and it multiplies the digitize time)"}.`,
    "",
    "| svg | send | stitches | trims | jumps | colour chg | IoU | edge mean mm | edge p95 mm | edge max mm | digitize s |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ...results.map((r) => r.error
      ? `| ${r.svg} | ${r.arm.toUpperCase()} ${r.sendPx} (${r.pxPerMm.toFixed(1)} px/mm) | digitize failed: ${r.error} | – | – | – | – | – | – | – | ${r.secs} |`
      : `| ${r.svg} | ${r.arm.toUpperCase()} ${r.sendPx} (${r.pxPerMm.toFixed(1)} px/mm) | ${r.stitches} | ${r.trims} | ${r.jumps} | ${r.colorChanges} | ${fmt(r.whole.iou, 4)} | ${fmt(r.whole.edge.both.mean, 3)} | ${fmt(r.whole.edge.both.p95, 3)} | ${fmt(r.whole.edge.both.max, 3)} | ${r.secs} |`),
  ];
  const withBands = results.filter((r) => r.bands.length);
  if (withBands.length) {
    md.push("", "Per line of lettering (small_text_logo.svg):", "", "| line | send | IoU | edge mean mm | edge p95 mm |", "|---|---|---:|---:|---:|");
    for (const r of withBands) for (const b of r.bands) md.push(`| ${b.name} | ${r.arm.toUpperCase()} ${r.size.toLocaleString("en-US")} px | ${fmt(b.iou, 4)} | ${fmt(b.edge.both.mean, 3)} | ${fmt(b.edge.both.p95, 3)} |`);
  }
  writeFileSync(path.join(outDir, "score.md"), md.join("\n") + "\n");
  console.log(md.join("\n"));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
