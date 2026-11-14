// "Rotate to fit" keeps the design's SIZE. The button's first build (#1414)
// turned each element and left its `sizeMm` alone, but sizeMm is the width
// AFTER rotation, so the engine rescaled the turned design to keep the old
// width: lettering 150 x 15 mm came back 31 x 305 mm with twice the stitches
// (walkthrough 2026-11-13). hoop.spec.js pins the rotation maths; this file
// pins what the customer sees -- the real engine, the real generateAll, the
// patches applied -- per element kind.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";

let EMB, generateAll, rotateToFitPatches, hoopFitNote, updateElements, defaultProject, placementBoxOf, isElementStale;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
  ({ EMB } = await import("./emb.js"));
  ({ generateAll } = await import("./generate.js"));
  ({ rotateToFitPatches, hoopFitNote } = await import("./hoop.js"));
  ({ updateElements, defaultProject } = await import("./project.js"));
  ({ placementBoxOf } = await import("./placement.js"));
  ({ isElementStale } = await import("./staleness.js"));
});

const HOOP = () => EMB.getHoop("5x7"); // 130 x 180 mm usable

function textEl(overrides = {}) {
  return {
    id: "t1", type: "text", text: "ROTATE ME", fontKey: "medium_font",
    colorRgb: [20, 20, 20], colorRanges: [], weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0,
    arcDeg: 0, rotationDeg: 0, align: "center", underlay: true, sizeMm: 150, offsetXMm: 0, offsetYMm: 0,
    ...overrides,
  };
}

// A solid-ish rectangle of stitches, native 100 x 25 mm, in the service's
// result space (0.1 mm ints, +y up). Used as the baked result of a digitized
// element -- the same decoded shape a .dst import produces.
function rectResult() {
  const st = (x, y, type = "stitch") => ({ x, y, type });
  const pts = [];
  for (let y = -125; y <= 125; y += 25) {
    pts.push(...(((y + 125) / 25) % 2 ? [st(500, y), st(-500, y)] : [st(-500, y), st(500, y)]));
  }
  return { colors: [{ r: 30, g: 60, b: 160 }], stitches: [...pts, st(0, 0, "end")] };
}
function digitizedEl(overrides = {}) {
  return {
    id: "d1", type: "digitized", result: rectResult(), blockColors: {}, params: {},
    sizeMm: null, rotationDeg: 0, offsetXMm: 0, offsetYMm: 0, deletedShapeIds: [], shapeOverrides: {},
    review: { shapes: [] }, appliedEdits: null, ...overrides,
  };
}
function designEl(overrides = {}) {
  const fs = createRequire(import.meta.url)("node:fs");
  const { fileURLToPath } = createRequire(import.meta.url)("node:url");
  const path = createRequire(import.meta.url)("node:path");
  const file = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../test/fixtures/standard-tajima.dst");
  return {
    id: "s1", type: "design", name: "starter.dst", dstBase64: fs.readFileSync(file).toString("base64"),
    blockColors: {}, sizeMm: 150, rotationDeg: 0, offsetXMm: 0, offsetYMm: 0, ...overrides,
  };
}

// A full back (304.8 mm box) on the 5x7 hoop: every kind below is wider than
// the hoop's 130 mm and fits only turned.
function projectOf(elements) {
  return { ...defaultProject(), garmentId: "full_back", hoopId: "5x7", elements, selectedId: elements[0].id, selectedIds: [elements[0].id] };
}

function turn(project) {
  const g = generateAll(project, {});
  const patches = rotateToFitPatches(project.elements, g.combined, HOOP(), g.perElement, placementBoxOf(project));
  return { g, patches, after: patches ? updateElements(project, patches) : null };
}

function expectSwapped(project) {
  const { g, patches, after } = turn(project);
  expect(patches, "the button is offered").not.toBeNull();
  expect(hoopFitNote(g.combined.widthMM, g.combined.heightMM, HOOP())).toMatch(/rotate/);
  const g2 = generateAll(after, {});
  expect(g2.combined.widthMM).toBeCloseTo(g.combined.heightMM, 0);
  expect(Math.abs(g2.combined.widthMM - g.combined.heightMM)).toBeLessThan(0.1);
  expect(Math.abs(g2.combined.heightMM - g.combined.widthMM)).toBeLessThan(0.1);
  expect(g2.combined.stitchCount).toBe(g.combined.stitchCount);
  expect(hoopFitNote(g2.combined.widthMM, g2.combined.heightMM, HOOP())).toBeNull();
  return { g, g2, after };
}

test("typed lettering 150 x 15 turns to 15 x 150, same stitches, and the hoop warning clears", () => {
  const { g } = turn(projectOf([textEl()]));
  expect(Math.round(g.combined.widthMM)).toBe(150);
  expect(Math.round(g.combined.heightMM)).toBe(15);
  expectSwapped(projectOf([textEl()]));
});

test("a starter design (imported .dst, 150 mm wide) keeps its scale when turned", () => {
  const { g, after } = expectSwapped(projectOf([designEl()]));
  expect(after.elements[0].rotationDeg).toBe(90);
  expect(after.elements[0].sizeMm).toBeCloseTo(g.combined.heightMM, 1); // the width it has once turned
});

test("digitized artwork keeps its scale when turned", () => {
  expectSwapped(projectOf([digitizedEl({ sizeMm: 150 })]));
});

test("digitized artwork with no typed width (sizeMm null, native 150 mm) keeps its native size when turned", () => {
  const st = (x, y, type = "stitch") => ({ x, y, type });
  const result = { colors: [{ r: 1, g: 2, b: 3 }], stitches: [st(-750, -100), st(750, -100), st(750, 100), st(-750, 100), st(0, 0, "end")] };
  const { g, after } = expectSwapped(projectOf([digitizedEl({ result, sizeMm: null })]));
  expect(after.elements[0].sizeMm).toBeCloseTo(g.combined.heightMM, 1);
});

test("a digitized design drawn at its native width is not made stale by the turn", () => {
  const wide = projectOf([digitizedEl({ sizeMm: 150 })]);
  const staleBefore = isElementStale(wide.elements[0], wide);
  const { after } = expectSwapped(wide);
  // 150 is a 1.5x resize of the 100 mm result: stale before, still stale
  // after (the stitches ARE scaled), never silently cleared or newly raised
  expect(staleBefore).toBe(true);
  expect(isElementStale(after.elements[0], after)).toBe(true);
});

test("a design at its native size reads current before and after the turn", () => {
  // native 150 mm result drawn at 150: no resize in play, the turn must not invent one
  const st = (x, y, type = "stitch") => ({ x, y, type });
  const result = { colors: [{ r: 1, g: 2, b: 3 }], stitches: [st(-750, -100), st(750, -100), st(750, 100), st(-750, 100), st(0, 0, "end")] };
  const p = projectOf([digitizedEl({ result, sizeMm: 150 })]);
  expect(isElementStale(p.elements[0], p)).toBe(false);
  const { after } = expectSwapped(p);
  expect(isElementStale(after.elements[0], after)).toBe(false);
});

test("a multi-element layout turns as a unit: combined width and height swap, stitches unchanged", () => {
  const p = projectOf([
    textEl({ id: "t1", offsetXMm: -30, offsetYMm: 20, sizeMm: 110 }),
    designEl({ id: "s1", offsetXMm: 20, offsetYMm: -20, sizeMm: 100 }),
  ]);
  const { g } = turn(p);
  expect(g.combined.widthMM).toBeGreaterThan(130);
  expectSwapped(p);
});

test("an element already turned 90 degrees turns on to 180 and keeps its size", () => {
  // a strip already upside down (180) is still 150 wide: turning goes to 270
  const p = projectOf([textEl({ rotationDeg: 180 })]);
  expectSwapped(p);
});

test("elements the engine cannot turn make the answer null (no fake fix)", () => {
  for (const type of ["image", "manual", "shape"]) {
    const p = projectOf([textEl({ id: "t1" }), { id: "x1", type, sizeMm: 50, rotationDeg: 0, offsetXMm: 0, offsetYMm: 0 }]);
    const g = generateAll(projectOf([textEl({ id: "t1" })]), {});
    expect(rotateToFitPatches(p.elements, g.combined, HOOP(), g.perElement, placementBoxOf(p))).toBeNull();
  }
});

test("a turn the placement box would clamp is not offered (it would rescale)", () => {
  const p = projectOf([textEl()]);
  const g = generateAll(p, {});
  expect(rotateToFitPatches(p.elements, g.combined, HOOP(), g.perElement, { w: 100, h: 200 })).not.toBeNull();
  const narrow = { w: 10, h: 400 }; // narrower than the turned 15 mm width
  expect(rotateToFitPatches(p.elements, g.combined, HOOP(), g.perElement, narrow)).toBeNull();
});
