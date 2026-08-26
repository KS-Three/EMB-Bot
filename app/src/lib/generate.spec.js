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
    id: "e1", type: "text", text: "", fontKey: "medium_font",
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

test("generateElement passes a design element's rotationDeg through (90 swaps dims; sizeMm is post-rotation width)", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");

  const rotated = generateElement(
    designElement({ dstBase64: makeDstBase64(EMB), rotationDeg: 90 }),
    garment,
    {}
  );
  expect(rotated.widthMM).toBeCloseTo(10, 1); // native 20x10 -> 10x20
  expect(rotated.heightMM).toBeCloseTo(20, 1);

  const sized = generateElement(
    designElement({ dstBase64: makeDstBase64(EMB), rotationDeg: 90, sizeMm: 15 }),
    garment,
    {}
  );
  expect(sized.widthMM).toBeCloseTo(15, 1); // 15mm wide IN the rotated orientation
  expect(sized.heightMM).toBeCloseTo(30, 1);

  // absent rotationDeg stays the unrotated path
  const plain = generateElement(designElement({ dstBase64: makeDstBase64(EMB) }), garment, {});
  expect(plain.widthMM).toBeCloseTo(20, 5);
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

// ---- Manual digitizing mode (hand-drawn shapes) ---------------------------
// generateElement("manual") is the one place the manual-shape data structure
// meets the REAL engine — no mocking of buildQualityDesign anywhere here, so
// a passing test is proof the full pull-comp/underlay/sequencing pipeline
// accepts manually-authored shapes and produces real, valid stitches.

test("generateElement returns null for a manual element with no shapes yet", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultManualElement } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  expect(generateElement(defaultManualElement("e1"), garment, {})).toBeNull();
});

test("generateElement: a manually-drawn fill shape produces real stitches through the full pipeline", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultManualElement, defaultManualShape } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const shape = {
    ...defaultManualShape("s1"),
    points: [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 300 }, { x: 0, y: 300 }],
    stitchType: "fill",
    colorRgb: [12, 140, 60],
  };
  const el = { ...defaultManualElement("e1"), shapes: [shape] };
  const d = generateElement(el, garment, {});
  expect(d.stitchCount).toBeGreaterThan(20);
  expect(d.colorCount).toBe(1);
  expect(d.colors[0]).toMatchObject({ r: 12, g: 140, b: 60 });
  expect(d._debug.nFill).toBe(1);
  expect(d._debug.nSatin).toBe(0);
  expect(d.stitches[d.stitches.length - 1].type).toBe("end");
});

test("generateElement: a manually-chosen 'satin' stitch type actually satins, even for a shape width auto-classification would fill", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultManualElement, defaultManualShape } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  // A wide square (not remotely "thin") — auto classification would always
  // fill this; the manual tierOverride hook must force satin anyway.
  const shape = {
    ...defaultManualShape("s1"),
    points: [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 200 }, { x: 0, y: 200 }],
    stitchType: "satin",
  };
  const el = { ...defaultManualElement("e1"), shapes: [shape] };
  const d = generateElement(el, garment, {});
  expect(d._debug.nSatin).toBe(1);
  expect(d._debug.nFill).toBe(0);
  expect(d.stitchCount).toBeGreaterThan(0);
});

test("generateElement: manual mode skips invalid/degenerate shapes and still generates the valid ones", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultManualElement, defaultManualShape } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const degenerate = { ...defaultManualShape("s1"), points: [{ x: 0, y: 0 }, { x: 5, y: 0 }] }; // 2 points
  const real = {
    ...defaultManualShape("s2"),
    points: [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 300 }, { x: 0, y: 300 }],
  };
  const el = { ...defaultManualElement("e1"), shapes: [degenerate, real] };
  const d = generateElement(el, garment, {});
  expect(d).not.toBeNull();
  expect(d.colorCount).toBe(1);
});

test("generateElement: two manually-drawn shapes each become their own color/region", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultManualElement, defaultManualShape } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const shapeA = {
    ...defaultManualShape("s1"),
    points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }],
    colorRgb: [200, 20, 20],
  };
  const shapeB = {
    ...defaultManualShape("s2"),
    points: [{ x: 200, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 100 }, { x: 200, y: 100 }],
    colorRgb: [20, 20, 200],
  };
  const el = { ...defaultManualElement("e1"), shapes: [shapeA, shapeB] };
  const d = generateElement(el, garment, {});
  expect(d.colorCount).toBe(2);
});

test("generateElement: manual shapes sew in DRAW order, not brightest-first", async () => {
  // The bug this exists for (found by a sibling-pattern sweep, 2026-08-26, and
  // reproduced against the real engine): digitize.js sequences light-to-dark
  // by default, and the manual branch did not opt out. A dark shape drawn
  // FIRST and a pale shape drawn on top of it came back sewn pale-then-dark,
  // so the dark one covered the shape the user deliberately put above it.
  // ManualPanel paints later-over-earlier and hit-tests back-to-front to
  // match, and it has no reorder control -- so the stacking the user drew was
  // simply unreachable.
  //
  // Asserted as "the engine's colour order equals the shape order I passed",
  // not as a hardcoded [navy, cream]: the point is the RELATIONSHIP, and a
  // literal pair would still pass if the sort were reinstated and the fixture
  // happened to be already-sorted.
  const { generateElement } = await import("./generate.js");
  const { defaultManualElement, defaultManualShape } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");

  const NAVY = [20, 30, 80];
  const CREAM = [245, 240, 220];
  // Navy drawn first, cream drawn second and therefore ON TOP.
  const navy = {
    ...defaultManualShape("s1"),
    points: [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 300 }, { x: 0, y: 300 }],
    colorRgb: NAVY,
  };
  const cream = {
    ...defaultManualShape("s2"),
    points: [{ x: 80, y: 80 }, { x: 220, y: 80 }, { x: 220, y: 220 }, { x: 80, y: 220 }],
    colorRgb: CREAM,
  };
  const el = { ...defaultManualElement("e1"), shapes: [navy, cream] };
  const d = generateElement(el, garment, {});

  const sewn = d.colors.map((c) => [c.r, c.g, c.b]);
  expect(sewn).toEqual([NAVY, CREAM]);

  // And the other way round, so this cannot pass by the fixture happening to
  // already be in brightness order: reverse the draw order, get the reverse
  // sew order.
  const flipped = { ...defaultManualElement("e1"), shapes: [cream, navy] };
  const d2 = generateElement(flipped, garment, {});
  expect(d2.colors.map((c) => [c.r, c.g, c.b])).toEqual([CREAM, NAVY]);
});

test("generateElement: manual sizeMm target scales the design width, same rule text/image follow", async () => {
  const { generateElement } = await import("./generate.js");
  const { defaultManualElement, defaultManualShape } = await import("./project.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const shape = {
    ...defaultManualShape("s1"),
    points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }],
  };
  const el = { ...defaultManualElement("e1"), shapes: [shape], sizeMm: 40 };
  const d = generateElement(el, garment, {});
  expect(d.widthMM).toBeGreaterThanOrEqual(40 - 1.5);
  expect(d.widthMM).toBeLessThanOrEqual(40 + 1.5);
});

test("generateAll combines a manual shape element with a text element into one multi-color design", async () => {
  const { generateAll } = await import("./generate.js");
  const { defaultManualElement, defaultManualShape } = await import("./project.js");
  const shape = {
    ...defaultManualShape("s1"),
    points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }],
  };
  const project = {
    version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223],
    elements: [
      textElement({ id: "e1", text: "AB" }),
      { ...defaultManualElement("e2"), shapes: [shape], offsetYMm: -20 },
    ],
  };
  const { combined, perElement } = generateAll(project, {});
  expect(perElement).toHaveLength(2);
  expect(combined.colors.length).toBeGreaterThanOrEqual(2); // text 1 + manual shape's own color
});

// ---- Preset shape elements (basic shapes tool) -----------------------------
// Same "meets the REAL engine" rule as the manual-mode block above: no
// mocking anywhere, so a passing test is proof a preset circle/rect/heart/
// star digitizes end-to-end through the identical shapesToRegions ->
// buildQualityDesign lane manual draw uses.

function shapeElement(overrides = {}) {
  return {
    id: "e1", type: "shape", kind: "circle", params: {}, colorRgb: [20, 20, 20],
    underlay: true, sizeMm: 50, offsetXMm: 0, offsetYMm: 0, ...overrides,
  };
}

// Needle-down extent only — jumps/trims travel, they don't cover fabric.
function stitchBboxMm(design) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of design.stitches) {
    if (s.type !== "stitch") continue;
    if (s.x < minX) minX = s.x;
    if (s.x > maxX) maxX = s.x;
    if (s.y < minY) minY = s.y;
    if (s.y > maxY) maxY = s.y;
  }
  return { wMm: (maxX - minX) / 10, hMm: (maxY - minY) / 10 };
}

test("every preset shape kind digitizes end-to-end with sane stats", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  for (const kind of ["circle", "rect", "heart", "star"]) {
    const d = generateElement(shapeElement({ kind }), garment, {});
    expect(d, kind).not.toBeNull();
    expect(d.stitchCount, `${kind} stitchCount`).toBeGreaterThan(300);
    expect(d.stitchCount, `${kind} stitchCount ceiling`).toBeLessThan(40000);
    expect(d.colorCount, kind).toBe(1);
    expect(d.stitches[d.stitches.length - 1].type).toBe("end");
  }
});

test("shape element: thread color rides through to the design palette", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(shapeElement({ colorRgb: [200, 30, 30] }), garment, {});
  expect(d.colors[0]).toMatchObject({ r: 200, g: 30, b: 30 });
});

test("shape element: satin-vs-fill is the engine classifier's call (no tierOverride forced)", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  // A 50 mm circle is far too wide for satin — the classifier must fill it.
  const wide = generateElement(shapeElement({ kind: "circle", sizeMm: 50 }), garment, {});
  expect(wide._debug.nFill).toBe(1);
  expect(wide._debug.nSatin).toBe(0);
  // A long thin 2 mm-tall rectangle is a classic satin column — the
  // classifier must be FREE to pick satin, which it can't be if the shape
  // branch forced tierOverride "fill" the way manual mode's default does.
  const thin = generateElement(
    shapeElement({ kind: "rect", params: { heightMm: 2, cornerRadiusMm: 0 }, sizeMm: 40 }),
    garment,
    {}
  );
  expect(thin._debug.nSatin).toBe(1);
  expect(thin._debug.nFill).toBe(0);
});

test("shape element: sizeMm is the sewn width, exactly like every other element type", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  for (const kind of ["circle", "rect", "heart", "star"]) {
    const d = generateElement(shapeElement({ kind, sizeMm: 40 }), garment, {});
    expect(d.widthMM, kind).toBeGreaterThanOrEqual(40 - 1.5);
    expect(d.widthMM, kind).toBeLessThanOrEqual(40 + 1.5);
  }
});

test("shape element: rect honors width AND height (w/h contract), circle sews round", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const rect = generateElement(
    shapeElement({ kind: "rect", params: { heightMm: 20, cornerRadiusMm: 0 }, sizeMm: 60 }),
    garment,
    {}
  );
  expect(rect.widthMM).toBeCloseTo(60, 0);
  expect(rect.heightMM).toBeCloseTo(20, 0);
  const circle = generateElement(shapeElement({ kind: "circle", sizeMm: 40 }), garment, {});
  expect(circle.heightMM).toBeCloseTo(circle.widthMM, 1);
});

test("star acid test: narrow tips get real needle-down coverage, not silently dropped", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  // Sharper-than-default tips on purpose (innerRatio 0.3). A 5-point star's
  // bbox extremes ARE its five tips (top tip = max y, side tips = x
  // extremes, bottom tips = min y), so needle-down stitches reaching the
  // design bbox on every side proves every tip actually sews. 1.5 mm slack
  // covers the last tatami row's spacing plus pull-comp rounding.
  const d = generateElement(
    shapeElement({ kind: "star", params: { points: 5, innerRatio: 0.3 }, sizeMm: 50 }),
    garment,
    {}
  );
  expect(d.stitchCount).toBeGreaterThan(300);
  const sb = stitchBboxMm(d);
  expect(sb.wMm).toBeGreaterThanOrEqual(d.widthMM - 1.5);
  expect(sb.hMm).toBeGreaterThanOrEqual(d.heightMM - 1.5);
});

test("generateAll combines a preset shape with a text element into one design", async () => {
  const { generateAll } = await import("./generate.js");
  const project = {
    version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223],
    elements: [
      textElement({ id: "e1", text: "AB" }),
      shapeElement({ id: "e2", kind: "heart", colorRgb: [200, 30, 60], offsetYMm: -20 }),
    ],
  };
  const { combined, perElement } = generateAll(project, {});
  expect(perElement).toHaveLength(2);
  expect(combined.colors.length).toBeGreaterThanOrEqual(2);
});

test("generateAll on a non-cap garment keeps element-list order", async () => {
  const { generateAll } = await import("./generate.js");
  const project = { version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223], elements: twoStackedElements() };
  const { combined, perElement } = generateAll(project, {});
  expect(perElement.map((p) => p.id)).toEqual(["e1", "e2"]); // list order
  const first = combined.stitches.find((s) => s.type === "stitch");
  expect(first.y).toBeGreaterThan(0); // e1, the upper element, sews first
});

// Characters a font cannot render (2026-08-22). Adding Hebrew to the library
// made a previously-obscure failure reachable in one click: pick a Hebrew font,
// type Latin, and the element generates as a structurally valid design of ZERO
// stitches with nothing in the UI saying why. The engine now reports which
// characters it dropped; generateAll carries that per element, because the fix
// is per element — it is THAT element's font that cannot set THAT text.
test("generateAll reports characters an element's font cannot render", async () => {
  const { generateAll } = await import("./generate.js");
  // medium_font has no Cyrillic; "Дом" is three characters it cannot set.
  const project = { garmentId: "left_chest", elements: [textElement({ text: "AДB" })] };
  const { perElement, unsupported, combined } = generateAll(project, {});
  expect(perElement).toHaveLength(1);
  expect(perElement[0].unsupported).toEqual(["Д"]);
  expect(unsupported).toEqual(["Д"]);
  // The A and the B still sew. That matters beyond bookkeeping: EmbroideryField
  // has TWO branches for this, and they say different things — an empty design
  // gets "Try a different font, or different text", while a design that partly
  // stitched gets the note on the stats line beside the stitch count. Without
  // this assertion the test would pass just as happily if the whole element
  // had produced nothing, which is the other branch entirely.
  expect(combined).toBeTruthy();
  expect(combined.stitchCount).toBeGreaterThan(0);
});

// A glyph that EXISTS in the font and sews nothing reaches the UI by the same
// route as a missing one, and lands on the same partly-stitched branch — the
// case worth pinning, because the note's wording ("This font can't stitch X")
// was written for missing glyphs and has to carry both.
test("a present-but-unstitchable glyph is reported like a missing one", async () => {
  const { generateAll } = await import("./generate.js");
  // western_light HAS a "4" — it is one of the 26 shipped glyphs that put no
  // thread down (test/font-dead-glyphs.test.js is the census). Typing a year
  // in this font drops the 4 and keeps the rest.
  const project = {
    garmentId: "left_chest",
    elements: [textElement({ text: "2024", fontKey: "western_light" })],
  };
  const { unsupported, combined } = generateAll(project, {});
  expect(unsupported).toEqual(["4"]);
  expect(combined).toBeTruthy();
  expect(combined.stitchCount).toBeGreaterThan(0);
});

test("generateAll reports nothing unsupported when every character renders", async () => {
  const { generateAll } = await import("./generate.js");
  const project = { garmentId: "left_chest", elements: [textElement({ text: "AB" })] };
  const { unsupported, perElement } = generateAll(project, {});
  expect(unsupported).toEqual([]);
  expect(perElement[0].unsupported).toEqual([]);
});

test("generateAll deduplicates unsupported characters across elements", async () => {
  const { generateAll } = await import("./generate.js");
  const project = { garmentId: "left_chest", elements: [
    textElement({ id: "e1", text: "AД" }),
    textElement({ id: "e2", text: "BД" }),
  ] };
  const { unsupported } = generateAll(project, {});
  expect(unsupported).toEqual(["Д"]);
});

test("a project with nothing ready still reports an unsupported array", async () => {
  const { generateAll } = await import("./generate.js");
  const { combined, perElement, unsupported } = generateAll(
    { garmentId: "left_chest", elements: [textElement({ text: "" })] }, {});
  expect(combined).toBe(null);
  expect(perElement).toEqual([]);
  expect(unsupported).toEqual([]);
});

test("charList formats an unsupported-character list for a person", async () => {
  const { charList } = await import("./generate.js");
  expect(charList([])).toBe("");
  expect(charList(null)).toBe("");
  expect(charList(["E"])).toBe("“E”");
  expect(charList(["E", "m"])).toBe("“E” and “m”");
  expect(charList(["E", "m", "b"])).toBe("“E”, “m” and “b”");
});

test("charList caps a long list instead of printing a paragraph", async () => {
  const { charList } = await import("./generate.js");
  // A whole sentence typed into a font that has none of it should not turn the
  // stats line into the same sentence.
  const many = "ABCDEFGHIJ".split("");
  const out = charList(many);
  expect(out).toContain("and 4 more");
  expect(out).not.toContain("“G”");
  expect(charList(many, 2)).toBe("“A”, “B” and 8 more");
});
