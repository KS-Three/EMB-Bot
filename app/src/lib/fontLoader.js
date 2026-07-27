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
    });
  }
  return manifestPromise;
}

export function ensureFont(key) {
  const cached = (EMB.SATIN_FONTS || {})[key];
  if (cached) return Promise.resolve(cached);
  if (!fontPromises.has(key)) {
    fontPromises.set(key, (async () => {
      const man = await loadManifest();
      if (!man.fonts.some((f) => f.key === key)) {
        fontPromises.delete(key);
        throw new Error("Unknown font: " + key);
      }
      const bytes = await readBytes("bin/" + key + ".embf");
      const font = EMB.decodeFontBin(bytes);
      EMB.SATIN_FONTS = EMB.SATIN_FONTS || {};
      EMB.SATIN_FONTS[key] = font;
      return font;
    })());
  }
  return fontPromises.get(key);
}

export function ensureFonts(keys) {
  return Promise.all([...new Set(keys)].map(ensureFont)).then(() => {});
}
