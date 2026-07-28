// Vitest-only synchronous preload. Replaces the old pattern of eval'ing
// src/fonts/satin-fonts.js (removed from the Studio pipeline in Slice 10):
// decodes every manifest font from disk into EMB.SATIN_FONTS so specs can
// keep reading it synchronously.
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

export function preloadAllFontsSync() {
  const g = globalThis;
  if (!g.EMB || typeof g.EMB.decodeFontBin !== "function")
    throw new Error("preloadAllFontsSync: engine (incl. fontbin.js) must be required first");
  const here = dirname(fileURLToPath(import.meta.url));
  const binDir = join(here, "..", "..", "..", "src", "fonts", "bin");
  g.EMB.SATIN_FONTS = g.EMB.SATIN_FONTS || {};
  for (const f of readdirSync(binDir)) {
    if (!f.endsWith(".embf")) continue;
    const key = f.replace(/\.embf$/, "");
    if (!g.EMB.SATIN_FONTS[key])
      g.EMB.SATIN_FONTS[key] = g.EMB.decodeFontBin(readFileSync(join(binDir, f)));
  }
}
