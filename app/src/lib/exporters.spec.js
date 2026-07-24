import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
let design;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  design = generateDesign(update(defaultProject(), { text: "AB" }));
});
test("DST export yields bytes and a .dst filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "dst");
  expect(out.filename.endsWith(".dst")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(100);
});
