// The "stitches are behind their settings" rule (lib/staleness.js), one rule
// for the Digitize panel's run button, the field's hatch and the Download step.
//
// The two situations that started it (area-3 doc, 2026-10-08): a corner drag
// from 80 to 62 mm kept all 8,764 stitches on 0.6x the area, and a garment
// switched after digitizing left the file on the old fabric preset. Both are
// asserted below against the same helper the three consumers call, so a
// consumer cannot disagree with another about what "behind" means.
import { describe, expect, test } from "vitest";
import { DEFAULT_DIGITIZE_PARAMS } from "./project.js";
import { buildDigitizeConfig, configKey, editsKey, canonicalShapeEdits } from "./digitizer.js";
import {
  isElementStale,
  staleElements,
  canRedigitize,
  blocksDownload,
  pendingEdits,
} from "./staleness.js";

// 80 x 40 mm as digitized (0.1 mm units), so a sizeMm of 62 is a 77.5% drag.
const RESULT = {
  stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 800, y: 400, type: "stitch" }],
  colors: [], stitchCount: 2, colorCount: 1, name: "t", widthMM: 80, heightMM: 40,
};
// Left Chest sews on the tee fabric preset, Hat Front on the structured cap's.
const TEE = { garmentId: "left_chest" };
const HAT = { garmentId: "hat_front" };

function digitized(extra = {}, project = TEE) {
  const base = {
    id: "e1",
    type: "digitized",
    name: "logo.png",
    sourcePng: "data:image/png;base64,AAAA",
    params: { ...DEFAULT_DIGITIZE_PARAMS },
    result: RESULT,
    review: { brandId: "studio", shapes: [] },
    shapeOverrides: {},
    deletedShapeIds: [],
    appliedEdits: null,
    crop: null,
    sizeMm: null,
    rotationDeg: 0,
  };
  const el = { ...base, ...extra };
  // As runDigitize stamps it: the key of what THESE settings would send.
  if (!("appliedConfig" in extra)) el.appliedConfig = configKey(buildDigitizeConfig(el, project));
  return el;
}

describe("isElementStale: what it covers", () => {
  test("a result that matches its settings is current", () => {
    expect(isElementStale(digitized(), TEE)).toBe(false);
  });

  test("nothing to be behind: no result, or not a digitized element", () => {
    expect(isElementStale(digitized({ result: null }), TEE)).toBe(false);
    expect(isElementStale({ ...digitized(), type: "text" }, TEE)).toBe(false);
    expect(isElementStale({ ...digitized(), type: "manual" }, TEE)).toBe(false);
    expect(isElementStale(null, TEE)).toBe(false);
    expect(isElementStale(undefined, TEE)).toBe(false);
  });

  test("garment: switching Tee to Hat after digitizing is behind", () => {
    const el = digitized({}, TEE);
    expect(isElementStale(el, HAT)).toBe(true);
    // ...and switching back makes it current again, with no run in between.
    expect(isElementStale(el, TEE)).toBe(false);
  });

  test("fabric colour and the calibration profile ride the same config, so they count", () => {
    const el = digitized({}, { ...TEE, fabricRgb: [255, 255, 255] });
    expect(isElementStale(el, { ...TEE, fabricRgb: [255, 255, 255] })).toBe(false);
    expect(isElementStale(el, { ...TEE, fabricRgb: [0, 0, 0] })).toBe(true);
    const calibrated = digitized({}, { ...TEE, fabricProfile: { density_scale: 1.1 } });
    expect(isElementStale(calibrated, { ...TEE, fabricProfile: { density_scale: 1.1 } })).toBe(false);
    expect(isElementStale(calibrated, { ...TEE, fabricProfile: { density_scale: 1.3 } })).toBe(true);
  });

  test("resize: a corner drag from 80 to 62 mm is behind, though the config never moved", () => {
    expect(isElementStale(digitized({ sizeMm: 62 }), TEE)).toBe(true);
    // At the digitized size it is current...
    expect(isElementStale(digitized({ sizeMm: 80 }), TEE)).toBe(false);
    // ...and a hand's jitter inside the 2% tolerance is not a change.
    expect(isElementStale(digitized({ sizeMm: 80.8 }), TEE)).toBe(false);
  });

  test("resize is read in the frame the element is drawn in: a quarter turn swaps width and height", () => {
    // Rotated 90 degrees the drawn width is the result's 40 mm height.
    expect(isElementStale(digitized({ rotationDeg: 90, sizeMm: 40 }), TEE)).toBe(false);
    expect(isElementStale(digitized({ rotationDeg: 90, sizeMm: 31 }), TEE)).toBe(true);
  });

  test("resize still counts when the clamped target equals the digitized width", () => {
    // A 10 mm design dragged smaller clamps to 10 mm, so the config key does
    // not move at all; the stitches are still scaled, not sewn at that size.
    const small = { ...RESULT, widthMM: 10, heightMM: 5, stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 100, y: 50, type: "stitch" }] };
    const el = digitized({ result: small, params: { ...DEFAULT_DIGITIZE_PARAMS, target_width_mm: 10 }, sizeMm: 6 });
    expect(isElementStale(el, TEE)).toBe(true);
  });

  test("a changed setting is behind, and putting it back is current again", () => {
    const el = digitized();
    const changed = { ...el, params: { ...el.params, target_width_mm: 123 } };
    expect(isElementStale(changed, TEE)).toBe(true);
    expect(isElementStale({ ...changed, params: { ...el.params } }, TEE)).toBe(false);
  });

  test("a crop moved after the run is behind", () => {
    const el = digitized({ crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 } });
    expect(isElementStale({ ...el, crop: null }, TEE)).toBe(true);
    expect(isElementStale(el, TEE)).toBe(false);
  });
});

describe("isElementStale: shape edits", () => {
  const shape = { id: "s1" };
  const withShapes = (extra = {}) => digitized({ review: { brandId: "studio", shapes: [shape] }, ...extra });

  test("an edit nobody has run is behind", () => {
    const el = withShapes();
    const edited = { ...el, shapeOverrides: { s1: { tier: "satin" } } };
    expect(isElementStale(edited, TEE)).toBe(true);
  });

  test("an edit the current result was digitized with is current", () => {
    const so = { s1: { tier: "satin" } };
    const edits = canonicalShapeEdits({ shapeOverrides: so, deletedShapeIds: [] });
    const el = withShapes({ shapeOverrides: so, appliedEdits: editsKey(edits) });
    expect(isElementStale(el, TEE)).toBe(false);
  });

  test("a toggled-then-untoggled edit reads as nothing pending", () => {
    const el = withShapes({ shapeOverrides: { s1: { tier: "auto" } } });
    expect(pendingEdits(el)).toBe(false);
  });

  test("with no review there is nothing the edit list could be compared to", () => {
    // The panel's own rule: a design with no shape list never had edits to apply.
    const el = digitized({ review: null, deletedShapeIds: ["s9"] });
    expect(pendingEdits(el)).toBe(false);
  });
});

describe("isElementStale: a design saved before appliedConfig existed", () => {
  // project.js: null "on a project saved before 2026-10-05, which the panel
  // reads as current as loaded". Nothing to compare the config with.
  test("without a baseline the config cannot be compared, so a garment switch is not seen", () => {
    const legacy = digitized({ appliedConfig: null }, TEE);
    expect(isElementStale(legacy, HAT)).toBe(false);
  });

  test("the panel's mount key is the baseline it was opened on", () => {
    const legacy = digitized({ appliedConfig: null }, TEE);
    const mountKey = configKey(buildDigitizeConfig(legacy, TEE));
    expect(isElementStale(legacy, TEE, { baselineKey: mountKey })).toBe(false);
    expect(isElementStale(legacy, HAT, { baselineKey: mountKey })).toBe(true);
  });

  test("a stored appliedConfig wins over a baseline", () => {
    const el = digitized({}, TEE);
    const wrong = configKey(buildDigitizeConfig(el, HAT));
    expect(isElementStale(el, TEE, { baselineKey: wrong })).toBe(false);
  });

  test("resize and pending edits are still seen without any key", () => {
    expect(isElementStale(digitized({ appliedConfig: null, sizeMm: 62 }), TEE)).toBe(true);
  });
});

describe("the project-level questions Download asks", () => {
  const stale = (id) => digitized({ id, sizeMm: 62 });
  const current = (id) => digitized({ id });
  const manual = { id: "m1", type: "manual", shapes: [] };

  test("staleElements names every element that is behind and nothing else", () => {
    const project = { ...TEE, elements: [current("a"), stale("b"), manual, stale("c")] };
    expect(staleElements(project).map((e) => e.id)).toEqual(["b", "c"]);
  });

  test("a project with nothing behind blocks nothing", () => {
    const project = { ...TEE, elements: [current("a"), manual] };
    expect(blocksDownload(project, { status: "ok" })).toBe(false);
  });

  test("any one element behind blocks Download, wherever it sits in the list", () => {
    const project = { ...TEE, elements: [current("a"), current("b"), stale("c")] };
    expect(blocksDownload(project, { status: "ok" })).toBe(true);
  });

  test("garment switched after the run blocks Download", () => {
    const project = { ...HAT, elements: [{ ...digitized({ id: "a" }, TEE) }] };
    expect(blocksDownload(project, { status: "ok" })).toBe(true);
    expect(blocksDownload({ ...TEE, elements: project.elements }, { status: "ok" })).toBe(false);
  });

  test("it blocks only what the customer can act on: no service, or no stored art, and the stale file still ships", () => {
    const project = { ...TEE, elements: [stale("a")] };
    expect(blocksDownload(project, null)).toBe(false);
    const noArt = { ...TEE, elements: [{ ...stale("a"), sourcePng: null }] };
    expect(blocksDownload(noArt, { status: "ok" })).toBe(false);
    expect(canRedigitize(stale("a"), { status: "ok" })).toBe(true);
    expect(canRedigitize(stale("a"), null)).toBe(false);
  });

  test("a project with no elements, or none at all, is not a crash", () => {
    expect(blocksDownload({ ...TEE, elements: [] }, { status: "ok" })).toBe(false);
    expect(blocksDownload({ ...TEE }, { status: "ok" })).toBe(false);
    expect(blocksDownload(null, { status: "ok" })).toBe(false);
    expect(staleElements(undefined)).toEqual([]);
  });
});
