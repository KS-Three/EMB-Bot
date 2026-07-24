import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  // load engine (order matters) — these populate globalThis.EMB
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});
test("emb accessor exposes buildLetteringDesign + satin fonts", async () => {
  const { EMB } = await import("./emb.js");
  expect(typeof EMB.buildLetteringDesign).toBe("function");
  expect(Object.keys(EMB.SATIN_FONTS).length).toBeGreaterThanOrEqual(14);
});
