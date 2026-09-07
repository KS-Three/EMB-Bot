import { EMB } from "./emb.js";

// Lazy font delivery (spec §4.1). The manifest is small and loaded once;
// font binaries are fetched on demand, decoded via EMB.decodeFontBin, and
// cached on EMB.SATIN_FONTS so every existing synchronous call site
// (generate.js, FontSelect, TemplateRow, legacy specs) keeps working
// unchanged once a font has been ensured.
//
// Dual environment: in the browser, /fonts/* is served from app/public
// (copied by scripts/copy-engine.mjs). Under vitest (Node), files are read
// from src/fonts/ directly.
const IS_NODE = typeof window === "undefined";

let manifestPromise = null;
const fontPromises = new Map();

async function readBytes(rel) {
  if (IS_NODE) {
    const { readFileSync } = await import("node:fs");
    const { join, dirname } = await import("node:path");
    const { fileURLToPath } = await import("node:url");
    const here = dirname(fileURLToPath(import.meta.url));
    return readFileSync(join(here, "..", "..", "..", "src", "fonts", rel));
  }
  const res = await fetch("/fonts/" + rel);
  if (!res.ok) throw new Error("Font fetch failed: " + rel + " (" + res.status + ")");
  return new Uint8Array(await res.arrayBuffer());
}

export function loadManifest() {
  if (!manifestPromise) {
    manifestPromise = readBytes("manifest.json").then((b) => {
      const man = JSON.parse(new TextDecoder().decode(b));
      man.fonts = man.fonts.filter((f) => f.tier === "verified"); // belt & braces
      return man;
    }).catch((err) => {
      manifestPromise = null; // transient failure must not poison the session
      throw err;
    });
  }
  return manifestPromise;
}

// Which characters each shipped font can stitch — src/fonts/manifest-coverage.json,
// built by tools/build-font-coverage.mjs from the .embf binaries. Loaded HERE
// rather than in lib/fontCoverage.js so the pure logic stays pure and there is
// one reader (`readBytes`) that works in both Node and the browser.
//
// Lazy on purpose: it is 16 KB and only ever needed once a font has failed on
// a character, so a design that stitches never fetches it. A failure resolves
// to null rather than throwing — fontSuggestion falls back to the generic
// advice, which is what shipped before this existed, so an older build with no
// coverage file degrades instead of erroring.
let coveragePromise = null;
export function loadCoverage() {
  if (!coveragePromise) {
    coveragePromise = readBytes("manifest-coverage.json")
      .then((b) => {
        const cov = JSON.parse(new TextDecoder().decode(b));
        return cov && cov.fonts ? cov : null;
      })
      .catch(() => {
        coveragePromise = null; // transient failure must not poison the session
        return null;
      });
  }
  return coveragePromise;
}

export function ensureFont(key) {
  const cached = (EMB.SATIN_FONTS || {})[key];
  if (cached) return Promise.resolve(cached);
  if (!fontPromises.has(key)) {
    fontPromises.set(key, (async () => {
      const man = await loadManifest();
      if (!man.fonts.some((f) => f.key === key))
        throw new Error("Unknown font: " + key);
      const bytes = await readBytes("bin/" + key + ".embf");
      const font = EMB.decodeFontBin(bytes);
      EMB.SATIN_FONTS = EMB.SATIN_FONTS || {};
      EMB.SATIN_FONTS[key] = font;
      return font;
    })().catch((err) => {
      fontPromises.delete(key); // any failure is retryable; success caches via SATIN_FONTS
      throw err;
    }));
  }
  return fontPromises.get(key);
}

export function ensureFonts(keys) {
  return Promise.all([...new Set(keys)].map(ensureFont)).then(() => {});
}
