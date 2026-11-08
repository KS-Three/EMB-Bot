// Stitched font samples for the font browser (2026-11-07).
//
// A customer picks a font by how it SEWS, but every browser tile was a
// thin-line needle-path PNG (tools/build-previews.mjs -> render-dst.mjs): it
// shows where the needle goes, not what the satin looks like. This module
// builds a short word through the browser lettering engine at ONE fixed
// sewn height and draws it with preview.js's own thread renderer, so every
// tile is the same physical size and reads as thread.
//
// What it must not do is bring back the fetch-everything problem the grid
// was rebuilt to fix (the old dropdown pulled every .embf, ~30 MB, the moment
// it opened). Nothing here fetches by itself: createSampleQueue only loads
// the fonts its caller says are in view (FontBrowser feeds it from an
// IntersectionObserver over the visible rows plus one look-ahead page), and
// it skips any binary over SAMPLE_MAX_BYTES outright -- those tiles keep the
// static PNG. Measured on the shipped library: the first 16 tiles in manifest
// order are 17.6 MB uncapped, because four of the biggest binaries
// (alchemy 4.6, ags_garamond 2.4, barstitch_mandala 4.6, califragilistic 7.7)
// sort into the first page.
import { drawThreads, threadLodLayers, THREAD_WIDTH_MM } from "./preview.js";
import { designToStrands } from "./strands.js";

// The word every tile sews: capital, lower case, a space and digits, which is
// what a customer is choosing between for a name and a number.
export const SAMPLE_TEXT = "Abc 123";
// Fixed SEWN height of the sample, in mm: the size of left-chest name
// lettering. Every font is sewn at this height, so a font that only holds up
// large shows it here instead of being flattered by a scale-to-fit.
export const SAMPLE_HEIGHT_MM = 10;
// Display scale, CSS px per sewn mm. 10 mm -> 35 px inside the tile's fixed
// 48 px image box, so the tile (and therefore the row) does not grow, and a
// sample up to 48 mm wide (most of the library at 10 mm) fits the box at the
// common scale. A wider one is shrunk to fit; none is ever enlarged.
export const SAMPLE_PX_PER_MM = 3.5;
// The tile's image box (FontBrowser .fb-tile-img: 48 px tall, ~176 px wide at
// the panel's 880 px). The canvas is drawn at this CSS size.
export const SAMPLE_BOX = { w: 176, h: 48 };
// Binaries over this many bytes keep their static PNG: one tile must not cost
// a multi-megabyte download. 1 MB keeps 71 of the 85 shipped fonts, and
// brings the first page (16 tiles) from 17.6 MB to 3.4 MB, two pages from
// 30.3 to 8.4 (manifest `bytes`, 2026-11-07).
export const SAMPLE_MAX_BYTES = 1_000_000;
// Same thread and fabric as the browser's live "your text" tiles and the
// static previews (build-previews writes [45,45,50] on white), so the three
// kinds of tile sit together.
export const SAMPLE_RGB = [45, 45, 50];
export const SAMPLE_FABRIC = "#ffffff";

// Which characters a font's sample sets. SAMPLE_TEXT when the font has every
// glyph; else the part of it the font CAN sew (a caps-only face still shows
// "A 123" rather than nothing); else the font's own first few glyphs (a
// Hebrew face) -- the same fallback order tools/font-sample.mjs uses for the
// static tiles, for the same reason: a tile that sews nothing says nothing.
export function sampleTextFor(font) {
  const glyphs = (font && font.glyphs) || {};
  const has = (ch) => ch === " " || !!glyphs[ch];
  if ([...SAMPLE_TEXT].every(has)) return SAMPLE_TEXT;
  const upper = SAMPLE_TEXT.toUpperCase();
  const strip = (t) => [...t].filter(has).join("").replace(/\s+/g, " ").trim();
  const partial = [strip(SAMPLE_TEXT), strip(upper)].sort((a, b) => b.length - a.length)[0];
  if (partial.replace(/ /g, "").length >= 3) return partial;
  const own = Object.keys(glyphs)
    .filter((k) => [...k].length === 1 && k !== " " && k !== ".notdef")
    .slice(0, 5).join("");
  return own || partial || "";
}

// Build the sample design: `text` sewn at exactly `heightMm` tall.
// buildLetteringDesign has no height option, only a width target clamped by
// the garment's hoop height, so a "garment" exactly `heightMm` tall and far
// wider than any sample, with a width target past that, leaves the height as
// the only constraint -- the glyph box lands at `heightMm`. Underlay off: it
// sews under the satin and cannot be seen in a 40 px tile, and it is a third
// of the stitch count to build and draw.
export function buildSample(EMB, font, opts) {
  const o = opts || {};
  const heightMm = o.heightMm || SAMPLE_HEIGHT_MM;
  const text = o.text != null ? o.text : sampleTextFor(font);
  if (!text) return null;
  return EMB.buildLetteringDesign(font, text, {
    garment: { widthIn: 40, heightIn: heightMm / 25.4 },
    targetWidthMm: 1000,
    pxPerMm: 8,
    underlay: false,
  });
}

// Draw a sample design into a 2D context whose drawing units are CSS px,
// centred in a w x h box at SAMPLE_PX_PER_MM (shrunk only if it would not
// fit). Returns the px-per-mm actually used, or 0 when there was nothing to
// draw. Fabric first, then preview.js's lit thread renderer.
export function drawSample(ctx, design, opts) {
  const o = opts || {};
  const w = o.w || SAMPLE_BOX.w, h = o.h || SAMPLE_BOX.h, pad = o.pad != null ? o.pad : 4;
  ctx.fillStyle = o.fabric || SAMPLE_FABRIC;
  ctx.fillRect(0, 0, w, h);
  if (!design || !design.stitchCount) return 0;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const s of design.stitches) {
    if (s.type !== "stitch") continue;
    if (s.x < x0) x0 = s.x; if (s.x > x1) x1 = s.x;
    if (s.y < y0) y0 = s.y; if (s.y > y1) y1 = s.y;
  }
  if (!(x1 >= x0)) return 0;
  // Design units are DST units (0.1 mm), Y up; canvas Y points down.
  const wMm = (x1 - x0) / 10, hMm = (y1 - y0) / 10;
  const pxPerMm = Math.min(o.pxPerMm || SAMPLE_PX_PER_MM, (w - 2 * pad) / (wMm || 1), (h - 2 * pad) / (hMm || 1));
  const k = pxPerMm / 10; // px per DST unit
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const SX = (x) => w / 2 + (x - cx) * k;
  const SY = (y) => h / 2 - (y - cy) * k;
  const strands = designToStrands(design, { colorOverride: o.rgb || SAMPLE_RGB });
  const lw = Math.max(1.2, THREAD_WIDTH_MM * pxPerMm);
  drawThreads(ctx, strands, SX, SY, lw, { layers: threadLodLayers(lw, strands.length) });
  return pxPerMm;
}

// Build + draw + encode one sample; "" when the font sews nothing for it.
// `dpr` backs the canvas with a denser bitmap so the thread stays crisp on
// HiDPI screens; drawing stays in CSS px through the base transform.
export function renderSampleUrl(EMB, font, opts) {
  const o = opts || {};
  const design = buildSample(EMB, font, o);
  if (!design || !design.stitchCount) return "";
  const dpr = Math.min(2, Math.max(1, o.dpr || 1));
  const c = (o.makeCanvas || (() => document.createElement("canvas")))();
  c.width = Math.round(SAMPLE_BOX.w * dpr);
  c.height = Math.round(SAMPLE_BOX.h * dpr);
  const ctx = c.getContext("2d");
  if (!ctx) return "";
  if (dpr !== 1) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (!drawSample(ctx, design, o)) return "";
  return c.toDataURL();
}

// Which rows can get a stitched sample at all: an .embf font (outline fonts
// have no binary here -- the browser draws those itself) whose binary is
// within the byte cap. A row with no `bytes` is allowed: an older manifest
// simply did not record it.
export function sampleEligible(row, maxBytes = SAMPLE_MAX_BYTES) {
  if (!row || !row.key || row.kind === "outline") return false;
  return !(row.bytes > maxBytes);
}

// Finished samples, per font key, for the whole session: the sample does not
// depend on anything the customer types, so reopening the browser shows every
// sample it has already sewn without fetching or drawing again.
export const SAMPLE_CACHE = new Map();

// The lazy queue. `want(row)` asks for a row's sample, `unwant(key)` takes
// back a request that has not started (the row scrolled out of the window
// before its turn), `stop()` drops everything (the dialog closed). Loads
// start in request order, at most `concurrency` at a time, and each render
// waits for `yieldFn` first so a burst of finished fetches cannot freeze a
// scroll. `onReady(key, url)` fires once per sample that finished.
//
// `load(key)` is FontBrowser's ensureFont: a font fetched for its sample is
// decoded and cached the same way a picked font is, so picking it afterwards
// costs nothing. Nothing outside want()'d rows is ever loaded.
export function createSampleQueue(opts) {
  const o = opts || {};
  const load = o.load;
  const render = o.render;
  const onReady = o.onReady || (() => {});
  const cache = o.cache || SAMPLE_CACHE;
  const maxBytes = o.maxBytes != null ? o.maxBytes : SAMPLE_MAX_BYTES;
  const concurrency = Math.max(1, o.concurrency || 2);
  const yieldFn = o.yieldFn || (() => new Promise((r) => setTimeout(r, 0)));
  const wanted = new Map(); // key -> row, insertion order = request order
  const inflight = new Set();
  const failed = new Set(); // this queue's load failures: not retried until the next open
  const loaded = []; // every key handed to load(), in order (the spec reads it)
  let stopped = false;

  function want(row) {
    if (stopped || !sampleEligible(row, maxBytes)) return;
    const key = row.key;
    if (cache.has(key) || inflight.has(key) || failed.has(key) || wanted.has(key)) return;
    wanted.set(key, row);
    pump();
  }
  function unwant(key) { wanted.delete(key); }
  function stop() { stopped = true; wanted.clear(); }

  function pump() {
    while (!stopped && inflight.size < concurrency && wanted.size) {
      const [key, row] = wanted.entries().next().value;
      wanted.delete(key);
      inflight.add(key);
      run(row);
    }
  }

  async function run(row) {
    const key = row.key;
    let font = null;
    try {
      loaded.push(key);
      font = await load(key);
    } catch (e) {
      failed.add(key);
    }
    if (font && !stopped) {
      await yieldFn();
      let url = "";
      if (!stopped) {
        try { url = render(font, row) || ""; } catch (e) { url = ""; }
        // A render that came back empty is cached too: drawing it again
        // would come back empty again.
        cache.set(key, url);
        if (url) onReady(key, url);
      }
    }
    inflight.delete(key);
    pump();
  }

  return {
    want,
    unwant,
    stop,
    get loaded() { return loaded.slice(); },
    get idle() { return !inflight.size && !wanted.size; },
  };
}
