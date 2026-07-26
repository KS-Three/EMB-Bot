import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});

// generate.js's real unit of work post-rework is generateElement(element,
// garment, runtime) — an element straight out of project.js's
// defaultTextElement/defaultImageElement, plus the resolved garment object.
// No more flat "compat" project object standing in for a real element.
function textElement(overrides = {}) {
  return {
    id: "e1", type: "text", text: "", fontKey: "geneva_simple",
    colorRgb: [20, 20, 20], letterSpacingMm: 0, arcDeg: 0, underlay: true,
    sizeMm: null, offsetXMm: 0, offsetYMm: 0, ...overrides,
  };
}

test("generateElement produces stitches for text", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(textElement({ text: "AB" }), garment, {});
  expect(d.stitchCount).toBeGreaterThan(50);
  expect(d.widthMM).toBeGreaterThan(0);
});

test("empty text returns null, not a throw", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  expect(generateElement(textElement(), garment, {})).toBeNull();
});

test("unknown font throws", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  expect(() => generateElement(textElement({ text: "AB", fontKey: "no_such_font" }), garment, {}))
    .toThrow(/Unknown font/);
});

test("sizeMm target scales design width appropriately", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(textElement({ text: "AB", sizeMm: 40 }), garment, {});
  expect(d.widthMM).toBeGreaterThanOrEqual(40 - 1.5);
  expect(d.widthMM).toBeLessThanOrEqual(40 + 1.5);
});

test("offsetXMm shifts stitches on x-axis", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const baseDesign = generateElement(textElement({ text: "AB" }), garment, {});
  const offsetDesign = generateElement(textElement({ text: "AB", offsetXMm: 10 }), garment, {});

  const baseFirstStitch = baseDesign.stitches.find((s) => s.type === "stitch");
  const offsetFirstStitch = offsetDesign.stitches.find((s) => s.type === "stitch");

  expect(baseFirstStitch).toBeDefined();
  expect(offsetFirstStitch).toBeDefined();
  // offsetXMm: 10 should shift x by exactly 100 DST units (1 DST unit = 0.1mm)
  expect(offsetFirstStitch.x).toBe(baseFirstStitch.x + 100);
});

test("letterSpacingMm changes design dimensions", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const baseDesign = generateElement(textElement({ text: "AB", sizeMm: 40 }), garment, {});
  const spacedDesign = generateElement(textElement({ text: "AB", sizeMm: 40, letterSpacingMm: 4 }), garment, {});

  // With the same width constraint (40mm), adding letter spacing makes the
  // text wider, forcing it to fit in less vertical space (taller aspect
  // ratio squeezed into the same width) -> heightMM shrinks with spacing.
  expect(spacedDesign.heightMM).toBeLessThan(baseDesign.heightMM);
});

test("arcDeg curves text and changes heightMM differently than straight text", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const straightDesign = generateElement(textElement({ text: "HELLO", sizeMm: 40, arcDeg: 0 }), garment, {});
  const arcedDesign = generateElement(textElement({ text: "HELLO", sizeMm: 40, arcDeg: 120 }), garment, {});

  // Curved text should have different heightMM than straight text
  expect(arcedDesign.heightMM).not.toBeCloseTo(straightDesign.heightMM, 1);
});

test("generateElement returns null for an image element with no flat state", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultImageElement } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const el = defaultImageElement("e1");
  expect(generateElement(el, garment, { flats: {} })).toBeNull();
  expect(generateElement(el, garment, {})).toBeNull();
});

function synthRGBA(w, h) {
  const rgba = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const o = (y * w + x) * 4;
    if (x < w / 2) { rgba[o] = 200; rgba[o + 1] = 30; rgba[o + 2] = 30; }
    else { rgba[o] = 30; rgba[o + 1] = 30; rgba[o + 2] = 200; }
    rgba[o + 3] = 255;
  }
  return rgba;
}

test("generateElement builds an image design from runtime.flats[element.id]", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultImageElement } = await import("./project.js");
  const { flattenRGBA } = await import("./flatten.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const w = 96, h = 64;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  const el = defaultImageElement("e1");
  const design = generateElement(el, garment, { flats: { e1: flat } });
  expect(design.stitchCount).toBeGreaterThan(100);
  expect(design.colorCount).toBe(2);
});

test("generateAll over a 2-element project combines both, with per-element bboxes that differ in y", async () => {
  const { generateAll } = await import("./generate.js");
  const { defaultProject, addElement, updateElement } = await import("./project.js");
  let project = defaultProject();
  project = updateElement(project, "e1", { text: "AB" });
  project = addElement(project, "text", 100); // seeds e2 staggered downward (offsetYMm -10)
  project = updateElement(project, "e2", { text: "CD" });

  const { combined, perElement } = generateAll(project, {});
  expect(perElement.length).toBe(2);
  expect(perElement[0].id).toBe("e1");
  expect(perElement[1].id).toBe("e2");
  expect(perElement[0].bboxMm.y0).not.toBeCloseTo(perElement[1].bboxMm.y0, 0);
  expect(combined.colorCount).toBe(2);
});

test("generateAll returns { combined: null, perElement: [] } when nothing is ready", async () => {
  const { generateAll } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  const result = generateAll(defaultProject(), {}); // default text element has empty text
  expect(result.combined).toBeNull();
  expect(result.perElement).toEqual([]);
});

test("generateDesign back-compat: works for a single-text-element v2 project", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, updateElement } = await import("./project.js");
  const project = updateElement(defaultProject(), "e1", { text: "AB" });
  const d = generateDesign(project);
  expect(d.stitchCount).toBeGreaterThan(50);
});

test("generateDesign throws when nothing in the project is ready", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  expect(() => generateDesign(defaultProject())).toThrow();
});
