import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
});

// generate.js's real unit of work post-rework is generateElement(element,
// garment, runtime) — an element straight out of project.js's
// defaultTextElement/defaultImageElement, plus the resolved garment object.
// No more flat "compat" project object standing in for a real element.
function textElement(overrides = {}) {
  return {
    id: "e1", type: "text", text: "", fontKey: "geneva_simple",
    colorRgb: [20, 20, 20], colorRanges: [], weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, underlay: true,
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

test("generateElement: a colorRange covering the first character produces a second thread color", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(
    textElement({ text: "AB", colorRanges: [{ startIdx: 0, endIdx: 1, colorRgb: [200, 30, 30] }] }),
    garment,
    {}
  );
  expect(d.colors.length).toBe(2);
  expect(d.colors[0]).toMatchObject({ r: 200, g: 30, b: 30 });
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

test("generateElement: rotationDeg 180 flips the reported bbox — heightMM stays the same as unrotated (fixture is landscape)", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const flat = generateElement(textElement({ text: "SD WHEEL" }), garment, {});
  const rotated = generateElement(textElement({ text: "SD WHEEL", rotationDeg: 180 }), garment, {});
  expect(Math.abs(rotated.widthMM - flat.widthMM)).toBeLessThan(0.5);
  expect(Math.abs(rotated.heightMM - flat.heightMM)).toBeLessThan(0.5);
});

test("generateElement: weightPreset 'bold' produces a wider average stitch spacing than 'thin' for the same text", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  function avgSpacing(d) {
    let sum = 0, n = 0, prev = null;
    for (const s of d.stitches) {
      if (s.type !== "stitch") { prev = null; continue; }
      if (prev) { sum += Math.hypot(s.x - prev.x, s.y - prev.y); n++; }
      prev = s;
    }
    return n ? sum / n : 0;
  }
  const thin = generateElement(textElement({ text: "H", weightPreset: "thin" }), garment, {});
  const bold = generateElement(textElement({ text: "H", weightPreset: "bold" }), garment, {});
  expect(avgSpacing(bold)).toBeGreaterThan(avgSpacing(thin));
});

test("generateElement: slantDeg 15 produces different stitch geometry than slantDeg 0 for the same text", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const straight = generateElement(textElement({ text: "H" }), garment, {});
  const slanted = generateElement(textElement({ text: "H", slantDeg: 15 }), garment, {});
  // buildLetteringDesign's two-pass fit-to-width scaling means slant's tiny
  // bbox shift (the clamped-end taper nudges the outermost rail contact by a
  // fraction of a mm) can nudge the fit scale enough to push one column's
  // step count across a Math.ceil() rounding boundary — see the equivalent,
  // more detailed note in test/digitize.test.js. A stitch or two of
  // difference here is expected noise, not a regression.
  expect(Math.abs(slanted.stitches.length - straight.stitches.length)).toBeLessThanOrEqual(10);
  const anyDiffer = straight.stitches.some((s, i) => Math.abs(s.x - slanted.stitches[i].x) > 1 || Math.abs(s.y - slanted.stitches[i].y) > 1);
  expect(anyDiffer).toBe(true);
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

// --- imported-design elements (DST import) -----------------------------

function designElement(overrides = {}) {
  return {
    id: "e1", type: "design", name: "test.dst", dstBase64: null,
    blockColors: {}, sizeMm: null, offsetXMm: 0, offsetYMm: 0, ...overrides,
  };
}

function makeDstBase64(EMB) {
  const bytes = EMB.encodeDST({
    stitches: [
      { x: -100, y: -50, type: "stitch" },
      { x: 100, y: -50, type: "stitch" },
      { x: 100, y: 50, type: "color" },
      { x: 100, y: 50, type: "stitch" },
      { x: -100, y: 50, type: "stitch" },
      { x: -100, y: 50, type: "end" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }, { r: 1, g: 1, b: 1 }],
    label: "SPEC",
  });
  return Buffer.from(bytes).toString("base64");
}

test("generateElement decodes a DST design element at native size with default block colors", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(designElement({ dstBase64: makeDstBase64(EMB) }), garment, {});
  expect(d.widthMM).toBeCloseTo(20, 5); // 200 units native
  expect(d.heightMM).toBeCloseTo(10, 5);
  expect(d.colorCount).toBe(2);
  expect(d.stitchCount).toBeGreaterThan(0);
  expect(d.stitches[d.stitches.length - 1].type).toBe("end");
});

test("generateElement: design element without a file yet returns null (not ready), and blockColors/sizeMm flow through", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  expect(generateElement(designElement(), garment, {})).toBeNull();

  const d = generateElement(
    designElement({ dstBase64: makeDstBase64(EMB), sizeMm: 40, blockColors: { 0: [7, 8, 9] } }),
    garment,
    {}
  );
  expect(d.widthMM).toBeCloseTo(40, 5);
  expect(d.colors[0]).toMatchObject({ r: 7, g: 8, b: 9 });
});

test("generateAll combines an imported design with a text element into one multi-color design", async () => {
  const { generateAll } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const project = {
    version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223],
    elements: [
      textElement({ id: "e1", text: "AB" }),
      designElement({ id: "e2", dstBase64: makeDstBase64(EMB), offsetYMm: -20 }),
    ],
  };
  const { combined, perElement } = generateAll(project, {});
  expect(perElement).toHaveLength(2);
  expect(combined.stitchCount).toBeGreaterThan(50);
  expect(combined.colors.length).toBeGreaterThanOrEqual(3); // text 1 + design 2
});

test("generateElement: align left vs right shifts a short second line (justification plumbs through)", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const mk = (align) => generateElement(textElement({ text: "AAA\nA", align, sizeMm: 60 }), garment, {});
  const left = mk("left"), right = mk("right");
  // Same overall design bbox either way (widest line dominates), but the
  // stitch distribution differs -- identical output would mean align was
  // silently dropped.
  expect(left.widthMM).toBeCloseTo(right.widthMM, 1);
  // Compare the FULL stitch stream: line 1 ("AAA") is identical either way,
  // so an early-slice signature would false-pass — only line 2 moves.
  const sig = (d) => JSON.stringify(d.stitches);
  expect(sig(left)).not.toBe(sig(right));
});

// ---- Cap sew order: elements splice bottom-up on cap garments ---------------
// generateAll on hat_front/beanie combines element designs lowest-bbox-first
// (bill toward crown) and returns perElement in that same sew order (sew
// order IS paint order — EmbroideryField's topmost-wins hit-testing depends
// on the two matching). Non-cap garments keep element-list order.

function twoStackedElements() {
  // e1 sits ABOVE e2 in the hoop (offsetYMm is +y UP). Explicit small
  // sizeMm — auto-fit would inflate both to hoop size and make them
  // overlap, muddying the "first stitch is below center" assertions.
  return [
    textElement({ id: "e1", text: "AAA", sizeMm: 30, offsetYMm: 10 }),
    textElement({ id: "e2", text: "VVV", sizeMm: 30, offsetYMm: -10 }),
  ];
}

test("generateAll on a cap sews the LOWER element first and returns perElement in sew order", async () => {
  const { generateAll } = await import("./generate.js");
  const project = { version: 2, garmentId: "hat_front", selectedId: "e1", fabricRgb: [235, 232, 223], elements: twoStackedElements() };
  const { combined, perElement } = generateAll(project, {});
  expect(perElement.map((p) => p.id)).toEqual(["e2", "e1"]); // lower first
  // The combined design's first sewn stitch comes from e2 (the lower element):
  // its y sits below hoop center (DST +y up -> negative-ish y).
  const first = combined.stitches.find((s) => s.type === "stitch");
  expect(first.y).toBeLessThan(0);
});

test("generateAll on a non-cap garment keeps element-list order", async () => {
  const { generateAll } = await import("./generate.js");
  const project = { version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223], elements: twoStackedElements() };
  const { combined, perElement } = generateAll(project, {});
  expect(perElement.map((p) => p.id)).toEqual(["e1", "e2"]); // list order
  const first = combined.stitches.find((s) => s.type === "stitch");
  expect(first.y).toBeGreaterThan(0); // e1, the upper element, sews first
});
