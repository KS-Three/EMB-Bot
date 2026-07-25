import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});

// generate.js is NOT reworked in this task (Task 2 will do that) — it still
// expects a flat, v1-ish project object: { text, fontKey, garmentId,
// underlay, colorRgb, sizeMm, offsetXMm, offsetYMm, letterSpacingMm } all on
// one object. The v2 project model (Task 1) moves those text/style fields
// onto `project.elements[N]` and keeps only garmentId at the top level, so
// these specs build a COMPAT object out of the v2 default text element
// (which already carries every field generate.js reads except garmentId)
// plus garmentId, rather than hand-rolling a v1 shape from scratch.
function compatProject(defaultProject, overrides = {}) {
  return { ...defaultProject().elements[0], garmentId: "left_chest", underlay: true, ...overrides };
}

test("generateDesign produces stitches for text", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  const d = generateDesign(compatProject(defaultProject, { text: "AB", fontKey: "geneva_simple" }));
  expect(d.stitchCount).toBeGreaterThan(50);
  expect(d.widthMM).toBeGreaterThan(0);
});
test("empty text throws", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  expect(() => generateDesign(compatProject(defaultProject))).toThrow();
});

test("sizeMm target scales design width appropriately", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  const d = generateDesign(compatProject(defaultProject, { text: "AB", fontKey: "geneva_simple", sizeMm: 40 }));
  expect(d.widthMM).toBeGreaterThanOrEqual(40 - 1.5);
  expect(d.widthMM).toBeLessThanOrEqual(40 + 1.5);
});

test("offsetXMm shifts stitches on x-axis", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  const baseProject = compatProject(defaultProject, { text: "AB", fontKey: "geneva_simple" });
  const baseDesign = generateDesign(baseProject);

  const offsetProject = { ...baseProject, offsetXMm: 10 };
  const offsetDesign = generateDesign(offsetProject);

  // Find first stitch of each design
  const baseFirstStitch = baseDesign.stitches.find(s => s.type === "stitch");
  const offsetFirstStitch = offsetDesign.stitches.find(s => s.type === "stitch");

  expect(baseFirstStitch).toBeDefined();
  expect(offsetFirstStitch).toBeDefined();

  // offsetXMm: 10 should shift x by exactly 100 DST units (1 DST unit = 0.1mm)
  expect(offsetFirstStitch.x).toBe(baseFirstStitch.x + 100);
});

test("letterSpacingMm changes design dimensions", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");

  // Generate with no letter spacing
  const baseProject = compatProject(defaultProject, { text: "AB", fontKey: "geneva_simple", sizeMm: 40 });
  const baseDesign = generateDesign(baseProject);

  // Generate with letter spacing
  const spacedProject = { ...baseProject, letterSpacingMm: 4 };
  const spacedDesign = generateDesign(spacedProject);

  // With same width constraint (40mm), adding letter spacing makes the text wider,
  // forcing it to fit in less vertical space (taller aspect ratio squeezed into same width).
  // Therefore heightMM should be smaller with spacing.
  expect(spacedDesign.heightMM).toBeLessThan(baseDesign.heightMM);
});
