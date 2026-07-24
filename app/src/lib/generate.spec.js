import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});
test("generateDesign produces stitches for text", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  const d = generateDesign(update(defaultProject(), { text: "AB", fontKey: "geneva_simple" }));
  expect(d.stitchCount).toBeGreaterThan(50);
  expect(d.widthMM).toBeGreaterThan(0);
});
test("empty text throws", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  expect(() => generateDesign(defaultProject())).toThrow();
});

test("sizeMm target scales design width appropriately", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  const d = generateDesign(update(defaultProject(), { text: "AB", fontKey: "geneva_simple", sizeMm: 40 }));
  expect(d.widthMM).toBeGreaterThanOrEqual(40 - 1.5);
  expect(d.widthMM).toBeLessThanOrEqual(40 + 1.5);
});

test("offsetXMm shifts stitches on x-axis", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  const baseProject = update(defaultProject(), { text: "AB", fontKey: "geneva_simple" });
  const baseDesign = generateDesign(baseProject);

  const offsetProject = update(baseProject, { offsetXMm: 10 });
  const offsetDesign = generateDesign(offsetProject);

  // Find first stitch of each design
  const baseFirstStitch = baseDesign.stitches.find(s => s.type === "stitch");
  const offsetFirstStitch = offsetDesign.stitches.find(s => s.type === "stitch");

  expect(baseFirstStitch).toBeDefined();
  expect(offsetFirstStitch).toBeDefined();

  // offsetXMm: 10 should shift x by exactly 100 DST units (1 DST unit = 0.1mm)
  expect(offsetFirstStitch.x).toBe(baseFirstStitch.x + 100);
});
