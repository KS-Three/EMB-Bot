import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  // load engine (order matters) — these populate globalThis.EMB
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
});
test("emb accessor exposes buildLetteringDesign + satin fonts", async () => {
  const { EMB } = await import("./emb.js");
  expect(typeof EMB.buildLetteringDesign).toBe("function");
  // Floor, not exact — QC demotions shrink the library slightly over time.
  expect(Object.keys(EMB.SATIN_FONTS).length).toBeGreaterThanOrEqual(60);
});
