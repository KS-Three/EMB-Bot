// Vitest-only synchronous preload. Replaces the old pattern of eval'ing
// src/fonts/satin-fonts.js (removed from the Studio pipeline in Slice 10):
// makes every manifest font on disk readable synchronously from
// EMB.SATIN_FONTS so specs can keep indexing it directly.
//
// LAZY on purpose. The library is 85 .embf files / 53 MB, and decoding all
// of it costs ~5 s of one core; vitest isolates each spec file, so the eight
// lib specs and two ui specs that call this each paid it again in their
// beforeAll, four at a time on a four-core box — past the 10 s default hook
// timeout whenever anything else loaded the host. Each key is now an
// enumerable getter that decodes on first read and then replaces itself with
// a plain data property, so Object.keys / `in` cost nothing and a spec pays
// only for the fonts it actually touches. Assignment and delete still work
// (fontLoader.spec deletes and re-populates a key).
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

export function preloadAllFontsSync() {
  const g = globalThis;
  if (!g.EMB || typeof g.EMB.decodeFontBin !== "function")
    throw new Error("preloadAllFontsSync: engine (incl. fontbin.js) must be required first");
  const here = dirname(fileURLToPath(import.meta.url));
  const binDir = join(here, "..", "..", "..", "src", "fonts", "bin");
  const fonts = (g.EMB.SATIN_FONTS = g.EMB.SATIN_FONTS || {});
  const settle = (key, value) =>
    Object.defineProperty(fonts, key, { value, writable: true, enumerable: true, configurable: true });
  for (const f of readdirSync(binDir)) {
    if (!f.endsWith(".embf")) continue;
    const key = f.replace(/\.embf$/, "");
    if (Object.prototype.hasOwnProperty.call(fonts, key)) continue;
    Object.defineProperty(fonts, key, {
      enumerable: true,
      configurable: true,
      get() {
        const font = g.EMB.decodeFontBin(readFileSync(join(binDir, f)));
        settle(key, font);
        return font;
      },
      set(value) {
        settle(key, value);
      },
    });
  }
}
