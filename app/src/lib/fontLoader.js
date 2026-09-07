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
  // A dead connection is the one font failure a customer can do something
  // about, and it was the one that reached them worst: `fetch` rejects with a
  // bare TypeError and EmbroideryField rendered its `.message` verbatim, so
  // the whole of what the app said was "Failed to fetch" — no cause, no
  // action, no retry control. Measured 2026-09-07 by aborting
  // `**/fonts/bin/**`.
  //
  // Flagged rather than reworded here so the component decides the wording
  // and this module keeps saying what happened. `offline` is set only for a
  // transport failure; an HTTP status is a different problem (a bad deploy,
  // a missing file) and keeps its own message.
  // DOCUMENT-RELATIVE, not "/fonts/". vite.config.js sets `base: "./"`, which
  // exists precisely so the bundle works wherever it is served from, and Vite
  // emits every asset it owns that way (index.html references "./assets/…").
  // These hand-written asset paths were the exception, and an absolute one
  // silently breaks the whole lettering lane anywhere but the domain root.
  //
  // Measured 2026-09-07 on a real `npm run build`, served from /studio/: seven
  // 404s on /fonts/manifest.json and not one stitch. At the domain root the
  // two forms resolve identically, so this is a no-op for the deployment
  // shipping today. (A path served without its trailing slash -- /studio
  // rather than /studio/ -- still resolves a directory up, which no
  // client-side scheme can fix; static servers redirect for exactly this
  // reason.)
  let res;
  try {
    res = await fetch("fonts/" + rel);
  } catch (e) {
    const err = new Error("Font fetch failed: " + rel + " (" + (e && e.message ? e.message : "network error") + ")");
    err.offline = true;
    throw err;
  }
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
