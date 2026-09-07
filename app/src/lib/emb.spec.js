import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  // load engine (order matters) — these populate globalThis.EMB
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
});
test("emb accessor exposes buildLetteringDesign + satin fonts", async () => {
  const { EMB } = await import("./emb.js");
  expect(typeof EMB.buildLetteringDesign).toBe("function");
  // Floor, not exact — QC demotions and license pulls shrink the library
  // over time (55 as of the 2026-08-04 ShareAlike removal, audit §9); 50
  // still catches a catastrophic manifest/loader regression. Was over time.
  expect(Object.keys(EMB.SATIN_FONTS).length).toBeGreaterThanOrEqual(50);
});

test("the engine functions the Studio calls BY NAME are actually there", () => {
  // `EMB.foo` is a string lookup on a global the engine assigns to, so a
  // rename or a missed entry in scripts/copy-engine.mjs is a runtime miss, not
  // a build error — and the import lane swallows it: DesignPanel's decodeSafe
  // catches and returns null, which renders as "no file chosen yet". A
  // customer would see their upload silently do nothing.
  //
  // Only names with no other guard belong here. decodeDSTStandard is the one
  // this list was started for: it is called from generate.js and from
  // DesignPanel, and it is what makes a third-party .dst land the right way
  // round rather than mirrored.
  for (const name of ["decodeDST", "decodeDSTStandard", "buildImportedDesign", "IMPORT_BLOCK_COLORS"]) {
    expect(globalThis.EMB[name], name).toBeDefined();
  }
});
