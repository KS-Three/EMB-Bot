// The click-to-edit popover's decision table (2026-09-29 spec §5). Pure:
// which controls a shape gets, what they read, and the exact patch each
// edit sends — compared against what the two side panels already send for
// the same edit, so the popover can never disagree with them.
import { describe, expect, test } from "vitest";
import {
  laneOf, popoverModel, popoverPatch, recolorPatch,
  DIGITIZED_TIERS, SHAPE_ANGLES, SHAPE_UNDERLAYS, BORDER_OPTIONS, SATIN_CUTOUT_NOTE,
} from "./shapePopover.js";

const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
const manualEl = {
  id: 4, type: "manual", underlay: true, sizeMm: null, offsetXMm: 0, offsetYMm: 0,
  shapes: [
    { id: "s1", points: square, curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null },
    { id: "s2", points: square, curves: {}, stitchType: "satin", colorRgb: [200, 0, 0], angleDeg: 30 },
  ],
};
const presetEl = { id: 5, type: "shape", kind: "heart", params: {}, colorRgb: [9, 8, 7], underlay: true, sizeMm: 50, offsetXMm: 0, offsetYMm: 0 };
const digitizedEl = {
  id: 6, type: "digitized",
  params: { border: null },
  review: { brandId: "isacord", shapes: [
    { id: "Sabc", threadNumber: "1301", areaMm2: 123.4, tier: "fill", rgb: [10, 20, 30] },
    { id: "Sdef", threadNumber: "0015", areaMm2: 4.56, tier: "satin", rgb: [250, 250, 250] },
  ] },
  shapeOverrides: { Sabc: { fill_angle_deg: 45, border: "auto" } },
  deletedShapeIds: [],
};

describe("laneOf", () => {
  test("names the three shape lanes and nothing else", () => {
    expect(laneOf(manualEl)).toBe("manual");
    expect(laneOf(presetEl)).toBe("shape");
    expect(laneOf(digitizedEl)).toBe("digitized");
    expect(laneOf({ type: "text" })).toBeNull();
    expect(laneOf(null)).toBeNull();
  });
});

describe("popoverModel — manual lane", () => {
  test("a fill shape: colour, Fill/Satin, numeric angle, Edit points, Delete", () => {
    const m = popoverModel({ element: manualEl, shapeId: "s1" });
    expect(m.lane).toBe("manual");
    expect(m.name).toBe("Shape 1 · Fill");
    expect(m.rows.map((r) => r.key)).toEqual(["color", "stitchType", "angle", "cutOut", "editPoints", "delete"]);
    expect(m.rows[3]).toEqual({ key: "cutOut", kind: "toggle", label: "Cut out", value: false });
    expect(m.rows[0]).toEqual({ key: "color", kind: "thread", rgb: [20, 20, 20] });
    expect(m.rows[1].options).toEqual([{ value: "fill", label: "Fill" }, { value: "satin", label: "Satin" }]);
    expect(m.rows[1].value).toBe("fill");
    expect(m.rows[2]).toEqual({ key: "angle", kind: "number", label: "Fill angle", value: null, hint: "° (blank = auto)" });
  });
  test("a satin shape reads its own values", () => {
    const m = popoverModel({ element: manualEl, shapeId: "s2" });
    expect(m.name).toBe("Shape 2 · Satin");
    expect(m.rows[1].value).toBe("satin");
    expect(m.rows[2].value).toBe(30);
  });
  test("an unknown shape id is null", () => {
    expect(popoverModel({ element: manualEl, shapeId: "nope" })).toBeNull();
  });
});

describe("popoverPatch — manual lane", () => {
  test("stitchType / angle / colour rewrite ONLY that shape, exactly as ManualPanel.updateShape does", () => {
    const ctx = { element: manualEl, shapeId: "s1" };
    const p1 = popoverPatch(ctx, "stitchType", "satin");
    expect(p1.shapes[0]).toEqual({ ...manualEl.shapes[0], stitchType: "satin" });
    expect(p1.shapes[1]).toBe(manualEl.shapes[1]); // untouched, same reference
    expect(popoverPatch(ctx, "angle", 90).shapes[0].angleDeg).toBe(90);
    expect(popoverPatch(ctx, "angle", "").shapes[0].angleDeg).toBeNull();
    expect(popoverPatch(ctx, "angle", "abc").shapes[0].angleDeg).toBeNull();
    expect(popoverPatch(ctx, "color", [1, 2, 3]).shapes[0].colorRgb).toEqual([1, 2, 3]);
  });
  test("delete removes the shape, as ManualPanel.deleteShape does", () => {
    expect(popoverPatch({ element: manualEl, shapeId: "s1" }, "delete").shapes.map((s) => s.id)).toEqual(["s2"]);
  });
  test("editPoints is an action, not a patch", () => {
    expect(popoverPatch({ element: manualEl, shapeId: "s1" }, "editPoints")).toBeNull();
  });
});

describe("preset lane", () => {
  test("name is the kind; colour is the only control", () => {
    const m = popoverModel({ element: presetEl, shapeId: "" });
    expect(m.name).toBe("Heart");
    expect(m.rows).toEqual([{ key: "color", kind: "thread", rgb: [9, 8, 7] }]);
    expect(popoverPatch({ element: presetEl, shapeId: "" }, "color", [1, 1, 1])).toEqual({ colorRgb: [1, 1, 1] });
    expect(popoverPatch({ element: presetEl, shapeId: "" }, "delete")).toBeNull();
  });
});

describe("popoverModel — digitized lane", () => {
  test("a fill shape gets the Layers row's full control set and reads its overrides", () => {
    const m = popoverModel({ element: digitizedEl, shapeId: "Sabc" });
    expect(m.name).toBe("Thread #1301 · 123 mm²");
    expect(m.rows.map((r) => r.key)).toEqual(["color", "stitchType", "angle", "underlay", "border", "editPoints", "delete"]);
    expect(m.rows[0].rgb).toEqual([10, 20, 30]);
    expect(m.rows[1].value).toBe("auto");
    // The Layers row's ten tiers, with "Auto" saying what auto resolved to.
    expect(m.rows[1].options).toHaveLength(DIGITIZED_TIERS.length);
    expect(m.rows[1].options[0]).toEqual({ value: "auto", label: "Auto (fill)" });
    expect(m.rows[1].options.slice(1)).toEqual(DIGITIZED_TIERS.slice(1));
    expect(m.rows[2].value).toBe("45");
    expect(m.rows[2].options).toEqual(SHAPE_ANGLES);
    expect(m.rows[3].value).toBe("auto");
    expect(m.rows[3].options).toEqual(SHAPE_UNDERLAYS);
    expect(m.rows[4].value).toBe("auto");
    expect(m.rows[4].options).toEqual(BORDER_OPTIONS(null));
    expect(BORDER_OPTIONS(null)[0].label).toBe("Design (automatic)");
    expect(BORDER_OPTIONS("bean")[0].label).toBe("Design (bean)");
  });
  test("a satin shape hides the fill-only rows (angle, underlay), as the Layers row does", () => {
    const m = popoverModel({ element: digitizedEl, shapeId: "Sdef" });
    expect(m.name).toBe("Thread #0015 · 4.6 mm²");
    expect(m.rows.map((r) => r.key)).toEqual(["color", "stitchType", "border", "editPoints", "delete"]);
  });
  test("a tier override to fill brings the fill rows back", () => {
    const el = { ...digitizedEl, shapeOverrides: { Sdef: { tier: "fill" } } };
    expect(popoverModel({ element: el, shapeId: "Sdef" }).rows.map((r) => r.key)).toContain("underlay");
  });
  test("a deleted or unknown shape is null", () => {
    expect(popoverModel({ element: { ...digitizedEl, deletedShapeIds: ["Sabc"] }, shapeId: "Sabc" })).toBeNull();
    expect(popoverModel({ element: digitizedEl, shapeId: "S404" })).toBeNull();
  });
});

describe("popoverPatch — digitized lane mirrors DigitizePanel.setOverride", () => {
  const ctx = { element: digitizedEl, shapeId: "Sabc" };
  test("tier: a value sets it, 'auto' clears it; other fields on the entry survive", () => {
    expect(popoverPatch(ctx, "stitchType", "satin").shapeOverrides.Sabc).toEqual({ fill_angle_deg: 45, border: "auto", tier: "satin" });
    expect(popoverPatch(ctx, "stitchType", "auto").shapeOverrides.Sabc).toEqual({ fill_angle_deg: 45, border: "auto" });
  });
  test("angle and underlay: 'auto' clears, a value parses/sets", () => {
    expect(popoverPatch(ctx, "angle", "90").shapeOverrides.Sabc.fill_angle_deg).toBe(90);
    expect(popoverPatch(ctx, "angle", "auto").shapeOverrides.Sabc.fill_angle_deg).toBeUndefined();
    expect(popoverPatch(ctx, "underlay", "edge_run").shapeOverrides.Sabc.underlay_style).toBe("edge_run");
    expect(popoverPatch(ctx, "underlay", "auto").shapeOverrides.Sabc.underlay_style).toBeUndefined();
  });
  test("border: 'default' clears the key (the design setting), any other word is stored", () => {
    expect(popoverPatch(ctx, "border", "off").shapeOverrides.Sabc.border).toBe("off");
    expect(popoverPatch(ctx, "border", "default").shapeOverrides.Sabc.border).toBeUndefined();
  });
  test("an entry emptied by a clear disappears entirely", () => {
    const el = { ...digitizedEl, shapeOverrides: { Sabc: { border: "auto" } } };
    expect(popoverPatch({ element: el, shapeId: "Sabc" }, "border", "default")).toEqual({ shapeOverrides: {} });
  });
  test("delete appends to deletedShapeIds once", () => {
    expect(popoverPatch(ctx, "delete")).toEqual({ deletedShapeIds: ["Sabc"] });
    expect(popoverPatch({ element: { ...digitizedEl, deletedShapeIds: ["Sabc"] }, shapeId: "Sabc" }, "delete")).toBeNull();
  });
  test("colour is async on this lane: popoverPatch declines, recolorPatch resolves through the chart", async () => {
    expect(popoverPatch(ctx, "color", [1, 2, 3])).toBeNull();
    const deps = {
      loadPalette: async (id) => ({ id, threads: [{ index: 0, rgb: [0, 0, 0] }, { index: 7, rgb: [250, 10, 10] }] }),
      nearestInList: (list, rgb) => { expect(list).toHaveLength(2); expect(rgb).toEqual([255, 0, 0]); return list[1]; },
    };
    expect(await recolorPatch(ctx, [255, 0, 0], deps)).toEqual({
      shapeOverrides: { Sabc: { fill_angle_deg: 45, border: "auto", thread_index: 7, rgb: [250, 10, 10] } },
    });
  });
  test("recolorPatch reads the element after the chart loads, so concurrent edits survive", async () => {
    let current = digitizedEl;
    const ctx2 = { element: () => current, shapeId: "Sabc" };
    const deps = {
      loadPalette: async (id) => {
        // Simulate an edit happening while the chart loads
        current = { ...digitizedEl, shapeOverrides: { Sabc: { tier: "satin" } } };
        return { id, threads: [{ index: 0, rgb: [0, 0, 0] }, { index: 7, rgb: [250, 10, 10] }] };
      },
      nearestInList: (list, rgb) => list[1],
    };
    expect(await recolorPatch(ctx2, [255, 0, 0], deps)).toEqual({
      shapeOverrides: { Sabc: { tier: "satin", thread_index: 7, rgb: [250, 10, 10] } },
    });
  });
  test("recolorPatch is null when the chart cannot be loaded or is not the job's", async () => {
    expect(await recolorPatch(ctx, [1, 1, 1], { loadPalette: async () => { throw new Error("offline"); }, nearestInList: () => null })).toBeNull();
    expect(await recolorPatch(ctx, [1, 1, 1], { loadPalette: async () => ({ id: "madeira", threads: [] }), nearestInList: () => null })).toBeNull();
  });
});

const box = (x0, y0, x1, y1) => [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }];
const holeEl = (parentType = "satin", holePts = box(20, 20, 40, 40)) => ({
  id: 7, type: "manual",
  shapes: [
    { id: "s1", points: square, curves: {}, stitchType: parentType, colorRgb: [1, 1, 1], angleDeg: null },
    { id: "s2", points: holePts, curves: {}, stitchType: "fill", colorRgb: [2, 2, 2], angleDeg: null, cutOut: true },
  ],
});

describe("cut-outs in the popover", () => {
  test("a cut-out inside a parent: toggle on, names its parent, no colour/type/angle rows", () => {
    const m = popoverModel({ element: holeEl(), shapeId: "s2" });
    expect(m.name).toBe("Shape 2 · Cut out");
    expect(m.rows.map((r) => r.key)).toEqual(["cutOut", "editPoints", "delete"]);
    expect(m.rows[0]).toEqual({ key: "cutOut", kind: "toggle", label: "Cut out", value: true, note: "Cuts Shape 1.", warn: false });
  });
  test("a cut-out outside everything says it cuts nothing, as a warning", () => {
    const m = popoverModel({ element: holeEl("fill", box(300, 300, 320, 320)), shapeId: "s2" });
    expect(m.rows[0].note).toBe("Not inside a shape — cuts nothing.");
    expect(m.rows[0].warn).toBe(true);
  });
  test("a satin parent with a cut-out reads Fill with the note; stored fill has no note", () => {
    const m = popoverModel({ element: holeEl("satin"), shapeId: "s1" });
    expect(m.name).toBe("Shape 1 · Fill");
    expect(m.rows[1].value).toBe("fill");
    expect(m.rows[1].note).toBe(SATIN_CUTOUT_NOTE);
    expect(SATIN_CUTOUT_NOTE).toBe("Sews as fill — satin cannot go round a cut-out.");
    const f = popoverModel({ element: holeEl("fill"), shapeId: "s1" });
    expect(f.rows[1].value).toBe("fill");
    expect("note" in f.rows[1]).toBe(false);
  });
  test("a satin shape with no cut-out keeps satin and no note", () => {
    const m = popoverModel({ element: manualEl, shapeId: "s2" });
    expect(m.rows[1].value).toBe("satin");
    expect("note" in m.rows[1]).toBe(false);
  });
  test("popoverPatch cutOut true marks only that shape; false removes the key", () => {
    const el = holeEl();
    const on = popoverPatch({ element: el, shapeId: "s1" }, "cutOut", true);
    expect(on.shapes[0].cutOut).toBe(true);
    expect(on.shapes[1]).toBe(el.shapes[1]);
    const off = popoverPatch({ element: el, shapeId: "s2" }, "cutOut", false);
    expect("cutOut" in off.shapes[1]).toBe(false);
    expect(off.shapes[0]).toBe(el.shapes[0]);
  });
  test("digitized and preset lanes are unchanged", () => {
    expect(popoverModel({ element: digitizedEl, shapeId: "Sabc" }).rows.map((r) => r.key)).toEqual(["color", "stitchType", "angle", "underlay", "border", "editPoints", "delete"]);
    expect(popoverModel({ element: presetEl, shapeId: "" }).rows.map((r) => r.key)).toEqual(["color"]);
  });
});
