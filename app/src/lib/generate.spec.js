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

test("generateElement: weightPreset 'bold' lays more thread than 'thin' for the same text", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  // TOTAL sewn path, not the AVERAGE per stitch. This test used to compare
  // averages, which stopped meaning "wider" when `splitSatin` went default ON
  // on 2026-09-11: a split cross is the same thread laid in more, shorter
  // segments, so a WIDER column can read as a SHORTER average (measured on
  // this exact pair — bold 24.537 against thin 24.678, inverted). Total path
  // is exactly invariant under splitting, because every split point lies ON
  // the segment it divides, so it measures the width claim and nothing else.
  function threadPath(d) {
    let sum = 0, prev = null;
    for (const s of d.stitches) {
      if (s.type !== "stitch") { prev = null; continue; }
      if (prev) sum += Math.hypot(s.x - prev.x, s.y - prev.y);
      prev = s;
    }
    return sum;
  }
  const thin = generateElement(textElement({ text: "H", weightPreset: "thin" }), garment, {});
  const bold = generateElement(textElement({ text: "H", weightPreset: "bold" }), garment, {});
  expect(threadPath(bold)).toBeGreaterThan(threadPath(thin));
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
  //
  // Measured on the THREAD, not the stitch count, since `splitSatin` went
  // default ON (2026-09-11): the same sub-millimetre nudge moves crosses
  // across the 5.0 mm split threshold and `k = ceil(cross / 3.0)` changes by
  // a whole segment, so the raw difference here reads 1 with the split off
  // and 594 with it on. Total sewn path is exactly invariant under splitting
  // — every split point lies ON the segment it divides — and it measures 1.0300
  // in BOTH arms, which is the same claim stated in a quantity the engine's
  // own default does not move. (`EMB.stripSplits` looks like the right tool
  // and is not: on a design's DST-rounded integer coordinates, ordinary rail
  // penetrations are routinely collinear and it removes 2,950 of them.)
  const threadPath = (d) => {
    let sum = 0, prev = null;
    for (const s of d.stitches) {
      if (s.type !== "stitch") { prev = null; continue; }
      if (prev) sum += Math.hypot(s.x - prev.x, s.y - prev.y);
      prev = s;
    }
    return sum;
  };
  const ratio = threadPath(slanted) / threadPath(straight);
  expect(ratio).toBeGreaterThan(1);
  expect(ratio).toBeLessThanOrEqual(1 / Math.cos((15 * Math.PI) / 180));
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
  // ONE block: both elements are the default black, and since 2026-09-07
  // combineDesigns merges adjacent blocks in the same thread instead of
  // splicing a colour change — a machine stop — between every pair. This read
  // 2 and was pinning that incidentally; the subject here is the per-element
  // bboxes above, and combine.spec.js owns the merge itself.
  expect(combined.colorCount).toBe(1);
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

// The import lane reads TAJIMA-convention files (generate.js's decodeCached
// calls EMB.decodeDSTStandard), so its fixture has to be one. This used to be
// EMB.encodeDST of a hand-built design — a file in EMB-Bot's OWN convention,
// which is the one kind of .dst a customer is told not to bring back in here.
// Reading it with the corrected reader gives the swapped dimensions, and the
// old expectations below were passing on exactly that.
//
// test/fixtures/standard-tajima.dst is written by pystitch (see
// digitizer/tools/make_standard_dst_fixture.py): 40 x 10 mm, two colour
// blocks, asymmetric under all eight dihedral transforms. No EMB-Bot encoder
// anywhere in the loop.
const STANDARD_DST_MM = { widthMM: 40, heightMM: 10 };
function makeDstBase64() {
  const require = createRequire(import.meta.url);
  const fs = require("node:fs");
  const path = require("node:path");
  // fileURLToPath, NOT `new URL(...).pathname` — this was the only place in the
  // suite using the latter, and on Windows it hands back a string that is not a
  // path: `/C:/Users/.../Claude%20Personal/...`, with a leading slash and the
  // space still percent-encoded. path.resolve then builds `C:\C:\...%20...` and
  // the read fails ENOENT. It needs BOTH a Windows host and a space in the repo
  // path, which is why CI (Linux, /home/runner/work) has never seen it and four
  // tests here have been red on every checkout under "Claude Personal".
  const { fileURLToPath } = require("node:url");
  const file = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../test/fixtures/standard-tajima.dst");
  return fs.readFileSync(file).toString("base64");
}

test("generateElement decodes a DST design element at native size with default block colors", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(designElement({ dstBase64: makeDstBase64() }), garment, {});
  // The size pystitch reads off the same file, not its transpose.
  expect(d.widthMM).toBeCloseTo(STANDARD_DST_MM.widthMM, 5);
  expect(d.heightMM).toBeCloseTo(STANDARD_DST_MM.heightMM, 5);
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
    designElement({ dstBase64: makeDstBase64(), sizeMm: 20, blockColors: { 0: [7, 8, 9] } }),
    garment,
    {}
  );
  expect(d.widthMM).toBeCloseTo(20, 5); // asked for half the 40 mm native width
  expect(d.colors[0]).toMatchObject({ r: 7, g: 8, b: 9 });
});

test("generateElement passes a design element's rotationDeg through (90 swaps dims; sizeMm is post-rotation width)", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");

  const rotated = generateElement(
    designElement({ dstBase64: makeDstBase64(), rotationDeg: 90 }),
    garment,
    {}
  );
  expect(rotated.widthMM).toBeCloseTo(10, 1); // native 40x10 -> 10x40
  expect(rotated.heightMM).toBeCloseTo(40, 1);

  const sized = generateElement(
    designElement({ dstBase64: makeDstBase64(), rotationDeg: 90, sizeMm: 15 }),
    garment,
    {}
  );
  expect(sized.widthMM).toBeCloseTo(15, 1); // 15mm wide IN the rotated orientation
  expect(sized.heightMM).toBeCloseTo(60, 1); // 40:10 native, so 15 wide is 60 tall

  // absent rotationDeg stays the unrotated path
  const plain = generateElement(designElement({ dstBase64: makeDstBase64() }), garment, {});
  expect(plain.widthMM).toBeCloseTo(STANDARD_DST_MM.widthMM, 5);
});

test("generateAll combines an imported design with a text element into one multi-color design", async () => {
  const { generateAll } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const project = {
    version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223],
    elements: [
      textElement({ id: "e1", text: "AB" }),
      designElement({ id: "e2", dstBase64: makeDstBase64(), offsetYMm: -20 }),
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
    // Red, not the default black the text also uses. This test says
    // "multi-color" and was only getting two blocks because combineDesigns
    // spliced a colour change between every pair whatever colour they were;
    // now that same-thread neighbours merge (2026-09-07) the premise has to
    // be real for the subject to be.
    colorRgb: [200, 20, 20],
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
  // 60.6 x 20.6, not 60 x 20: since 2026-09-07 a design reports the extent it
  // SEWS, and pull compensation pushes the outline's rails 0.3 mm past it on
  // each side. The contract this test exists for is unaffected — a 60x20 rect
  // must not come back square — so the tolerance stays loose enough to survive
  // a routing change and tight enough to catch an axis being ignored.
  expect(rect.widthMM).toBeCloseTo(60.6, 1);
  expect(rect.heightMM).toBeCloseTo(20.6, 1);
  expect(rect.widthMM / rect.heightMM).toBeGreaterThan(2.5);
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

// ---- letteringNote (width guards, 2026-09-03) ------------------------------
// Wording is logic. The report shape is buildLetteringDesign's `lettering`;
// every number the note quotes has to come from it.
function report(over = {}) {
  return {
    capMm: 12, capFloorMm: 4, columns: 10, strokeMm: 100, thinMm: 0, hairlineMm: 0,
    hairlineSpans: 0, columnFloorMm: 1, crossFloorMm: 0.5, ...over,
  };
}

test("letteringNote is silent on a healthy report, a null report, and an empty one", async () => {
  const { letteringNote } = await import("./generate.js");
  expect(letteringNote(report())).toBe("");
  expect(letteringNote(null)).toBe("");
  expect(letteringNote(report({ strokeMm: 0, columns: 0 }))).toBe("");
});

test("letteringNote: a cap under the 4 mm floor wins over everything else", async () => {
  const { letteringNote } = await import("./generate.js");
  const n = letteringNote(report({ capMm: 3.24, hairlineMm: 90, hairlineSpans: 5, thinMm: 100 }));
  // The verdict half is what this test is about — it outranks the hairline and
  // thin findings that are also present in this report. The fix half after it
  // gained levers 2026-09-07 and is pinned in its own tests below.
  expect(n.startsWith("Letters 3.2 mm tall — under the 4 mm floor, thin strokes will shred")).toBe(true);
  expect(n).not.toMatch(/running stitch/);
});

test("letteringNote: lettering that is mostly hairline at this size says so, with the share", async () => {
  const { letteringNote } = await import("./generate.js");
  const n = letteringNote(report({ hairlineMm: 61, thinMm: 80, hairlineSpans: 7 }));
  expect(n).toBe("61% of this lettering is under 0.5 mm wide at this size and sews as running stitch — size up or pick a bolder font");
});

test("letteringNote: the odd hairline stroke is reported as what the engine did about it", async () => {
  const { letteringNote } = await import("./generate.js");
  expect(letteringNote(report({ hairlineMm: 4, thinMm: 6, hairlineSpans: 1 }))).toBe("1 hairline stroke under 0.5 mm sewn as running stitch");
  expect(letteringNote(report({ hairlineMm: 8, thinMm: 12, hairlineSpans: 3 }))).toBe("3 hairline strokes under 0.5 mm sewn as running stitch");
});

test("letteringNote: thin lettering warns at a quarter of the stroke length and not below", async () => {
  const { letteringNote } = await import("./generate.js");
  expect(letteringNote(report({ thinMm: 30 }))).toBe("30% of this lettering is under 1 mm wide — size up for crisp letters");
  expect(letteringNote(report({ thinMm: 20 }))).toBe("");
});

// ---- atWidthCap: which advice is actually available ------------------------
//
// Lettering is fit by WIDTH, so for a fixed character count the cap height is
// proportional to the design width. Measured 2026-09-07 with `medium_font` on
// left_chest's 101.6 mm placement box, every one of them at that same width:
// "WIDE DESIGN TEXT HERE" → 4.33 mm cap, "SHORTER TEXT" → 7.16, "ABC" → 30.03.
//
// An auto-fit design (the default) is already AT that box. "Size up for crisp
// letters" is then advice to do the one thing the customer cannot, and the
// levers that remain — fewer characters, a bolder font, a bigger placement —
// went unnamed.
test("letteringNote: at the width cap, 'size up' is replaced by the levers that exist", async () => {
  const { letteringNote } = await import("./generate.js");
  const thin = letteringNote(report({ thinMm: 30 }), { atWidthCap: true });
  expect(thin).toContain("30% of this lettering is under 1 mm wide");
  expect(thin).toContain("fewer characters or a bigger placement");
  expect(thin).not.toContain("size up");

  const hairline = letteringNote(report({ hairlineMm: 61, thinMm: 80, hairlineSpans: 7 }), { atWidthCap: true });
  expect(hairline).toContain("sews as running stitch");
  expect(hairline).toContain("fewer characters");
  expect(hairline).toContain("bolder font");     // still true at the cap
  expect(hairline).not.toContain("size up");
});

test("letteringNote: below the cap, 'size up' stays — it is the fix there", async () => {
  const { letteringNote } = await import("./generate.js");
  expect(letteringNote(report({ thinMm: 30 }), { atWidthCap: false }))
    .toBe("30% of this lettering is under 1 mm wide — size up for crisp letters");
  // Omitting the option is the same as false, so no caller is silently changed.
  expect(letteringNote(report({ thinMm: 30 }), {})).toBe(letteringNote(report({ thinMm: 30 })));
});

test("letteringNote: a lone hairline span is a report, not advice, so the cap cannot change it", async () => {
  const { letteringNote } = await import("./generate.js");
  // This one states what the ENGINE did — it is not advice, so there is no fix
  // clause for the width cap to switch. (The cap-floor line used to be in here
  // too, on the reasoning that naming a height was not an action either. That
  // was the defect: it was the most severe verdict and the only one with no
  // way out. It now varies with the cap, and is pinned separately.)
  for (const opts of [{}, { atWidthCap: true }]) {
    expect(letteringNote(report({ hairlineMm: 4, thinMm: 6, hairlineSpans: 1 }), opts))
      .toBe("1 hairline stroke under 0.5 mm sewn as running stitch");
  }
  // And the cap-floor verdict itself is identical either way — only its fix moves.
  const a = letteringNote(report({ capMm: 3.24, hairlineMm: 90, thinMm: 100 }), {});
  const b = letteringNote(report({ capMm: 3.24, hairlineMm: 90, thinMm: 100 }), { atWidthCap: true });
  const verdict = (n) => n.split(" — ").slice(0, 2).join(" — ");
  expect(verdict(a)).toBe(verdict(b));
  expect(a).not.toBe(b);
});

test("generateElement: a text element's design carries the lettering report", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(textElement({ text: "AB" }), garment, {});
  expect(d.lettering).toBeTruthy();
  expect(d.lettering.capMm).toBeGreaterThan(0);
  expect(d.lettering.strokeMm).toBeGreaterThan(0);
  expect(d.lettering.crossFloorMm).toBe(0.5);
});

// ---- One design, one width ------------------------------------------------
//
// The Studio shows a design's size in two places at once: EmbroideryField's
// caption reads `combined.widthMM`, SizePanel reads `perElement[].bboxMm`.
// For a single-element project combineDesigns returns that element's design
// UNCHANGED (combine.js documents this deliberately), so the caption gets
// whatever the engine builder reported while the panel gets the stitch bbox —
// and until 2026-09-07 those were two different measurements. Driving the
// shipped app: caption "127×13 mm", size field "5.05 in" (=128.3 mm), max
// "5.00". Same design, same instant, two answers, one of them out of its own
// input's range.
//
// The engine now reports the stitch bbox (digitize.js designExtentMm), so this
// holds by construction — which is exactly why it needs a test: nothing else
// in either codebase asserts that the two numbers describe the same thing, and
// the last thing to break it was a builder change three files away.
test("caption width and size-panel width are the same number, for one element and for many", async () => {
  const { generateAll } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("hat_front");
  const mk = (n) => ({
    garmentId: "hat_front", fabricRgb: [255, 255, 255], selectedId: "e1",
    elements: Array.from({ length: n }, (_, i) => textElement({ id: `e${i + 1}`, text: "YOUR NAME", offsetYMm: i * 8 })),
  });
  for (const n of [1, 2, 3]) {
    const { combined, perElement } = generateAll(mk(n), {});
    expect(perElement.length, `${n} elements`).toBe(n);
    const xs = perElement.flatMap((pe) => [pe.bboxMm.x0, pe.bboxMm.x1]);
    const ys = perElement.flatMap((pe) => [pe.bboxMm.y0, pe.bboxMm.y1]);
    expect(combined.widthMM, `${n}: caption vs panel width`).toBeCloseTo(Math.max(...xs) - Math.min(...xs), 6);
    expect(combined.heightMM, `${n}: caption vs panel height`).toBeCloseTo(Math.max(...ys) - Math.min(...ys), 6);
  }
});

test("the reported size is thread, not the box the design was fit to", async () => {
  const { generateAll } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  // hat_front's placement box is 5.00 x 2.25 in. An auto-fit text element is
  // scaled to that box; the satin rails then sew past it. Before this was
  // fixed the design reported exactly 127.0 — the box — and the hoop ceiling
  // check in hoop.js therefore ran against a number the thread had already
  // left. Measured across 7,470 designs (10 garments x 85 shipped fonts x 3
  // texts x 3 weights): 65.6% sewed outside their own placement box, by up to
  // 9.6 mm, and four told the ceiling check "fits" when the thread needed the
  // hoop rotated.
  const garment = EMB.getGarment("hat_front");
  const boxWmm = garment.widthIn * 25.4;
  const { combined } = generateAll({
    garmentId: "hat_front", fabricRgb: [255, 255, 255], selectedId: "e1",
    elements: [textElement({ id: "e1", text: "YOUR NAME" })],
  }, {});
  expect(combined.widthMM).toBeGreaterThan(boxWmm);
  // The stitches back it up — this is a measurement, not a fudge factor.
  const geo = combined.stitches.filter((s) => s.type !== "color" && s.type !== "end");
  const xs = geo.map((s) => s.x);
  expect((Math.max(...xs) - Math.min(...xs)) / 10).toBeCloseTo(combined.widthMM, 6);
});

// ---- emptyFieldHint (the pointer the advice assumes, 2026-09-07) -----------
//
// The empty canvas is the only place in the product that says the drawing
// tools exist, and it used to say "right-click" to everyone. Measured that
// day against the production build at 390x844 with touch emulation: a real
// 1.4-second long-press (dispatched through CDP, not as a synthetic event)
// produced zero contextmenu events and never opened the menu, while a real
// right-click on a desktop context opened it every time — and no button
// anywhere in the app reaches those tools. So on a device reporting no fine
// pointer the sentence has to name something else.

test("emptyFieldHint names right-click only where a mouse exists", async () => {
  const { emptyFieldHint } = await import("./generate.js");
  expect(emptyFieldHint(true)).toBe(
    "Your embroidery appears here as you add content. Right-click the canvas for drawing tools.",
  );
});

test("emptyFieldHint on a device with no mouse names a lane that device has", async () => {
  const { emptyFieldHint } = await import("./generate.js");
  const n = emptyFieldHint(false);
  // The point of the change: no gesture this device cannot perform.
  expect(n).not.toMatch(/right-click/i);
  // And not a dead end either — it says what IS reachable there. Both lanes
  // were driven on that phone viewport: typing gave 1,223 stitches at
  // 102x19 mm with a 5x7 hoop picked.
  expect(n).toMatch(/text/i);
  expect(n).toMatch(/artwork/i);
  // ...and says why the tools are missing rather than pretending they aren't.
  expect(n).toMatch(/mouse/i);
});

test("emptyFieldHint keeps the same lead sentence either way", async () => {
  const { emptyFieldHint } = await import("./generate.js");
  const lead = "Your embroidery appears here as you add content.";
  expect(emptyFieldHint(true).startsWith(lead)).toBe(true);
  expect(emptyFieldHint(false).startsWith(lead)).toBe(true);
});

// ---- the cap-floor branch names a fix (2026-09-07) ------------------------
//
// The most severe verdict letteringNote gives — the lettering cannot be sewn
// at all — was the only one that named no fix, while the milder branch below
// it named two. Measured that day: a 74-character sentence auto-fit to the
// default left chest gives 1.7 mm letters against a 4 mm floor, and the
// customer was told what was wrong and nothing about what to do.
//
// All three levers were measured on that sentence and garment before being
// named: 3 lines -> 4.8 mm, 6 lines -> 6.3 mm, 18 characters -> 6.7 mm, full
// back placement -> 4.0 mm. All clear the floor. 40 characters gives 3.1 mm
// and does NOT, which is why "fewer characters" is named second.

test("letteringNote: a design under the cap floor says what to do about it", async () => {
  const { letteringNote } = await import("./generate.js");
  const under = report({ capMm: 1.7, capFloorMm: 4 });

  // At the width cap "size up" is the one thing the customer cannot do, so it
  // must not appear — the same rule the hairline branch already follows.
  const capped = letteringNote(under, { atWidthCap: true, lines: 1 });
  expect(capped).toMatch(/1\.7 mm tall/);
  expect(capped).toMatch(/shred/);
  expect(capped).toMatch(/break it across lines/);
  expect(capped).toMatch(/fewer characters/);
  expect(capped).not.toMatch(/size up/);

  // Off the cap, sizing up IS available and leads.
  const free = letteringNote(under, { atWidthCap: false, lines: 1 });
  expect(free).toMatch(/size up/);
  expect(free).toMatch(/break it across lines/);
});

test("letteringNote: text already on several lines is told to use more, not to start", async () => {
  const { letteringNote } = await import("./generate.js");
  const n = letteringNote(report({ capMm: 2.2, capFloorMm: 4 }), { atWidthCap: true, lines: 3 });
  expect(n).toMatch(/use more lines/);
  expect(n).not.toMatch(/break it across lines/);
});

test("letteringNote: the cap floor still outranks the width warnings", async () => {
  // Unchanged precedence — a design that cannot be sewn at all is reported
  // ahead of one whose strokes are merely thin.
  const { letteringNote } = await import("./generate.js");
  const n = letteringNote(report({ capMm: 1.7, capFloorMm: 4, hairlineMm: 90, hairlineSpans: 5, thinMm: 100 }), { atWidthCap: true });
  expect(n).toMatch(/1\.7 mm tall/);
  expect(n).not.toMatch(/running stitch/);
});
