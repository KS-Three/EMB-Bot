import { test, expect } from "vitest";
import {
  defaultProject,
  defaultTextElement,
  defaultImageElement,
  defaultDigitizedElement,
  DEFAULT_DIGITIZE_PARAMS,
  update,
  addElement,
  addSeededTextElement,
  removeElement,
  selectElement,
  updateElement,
  migrateProject,
} from "./project.js";

// --- defaults ---------------------------------------------------------

test("defaultProject has sane v2 beginner defaults", () => {
  const p = defaultProject();
  expect(p.version).toBe(2);
  expect(p.garmentId).toBe("left_chest");
  expect(p.selectedId).toBe("e1");
  expect(p.elements).toHaveLength(1);
  expect(p.elements[0]).toEqual(defaultTextElement("e1"));
});

test("defaultProject has a project-level fabricRgb default (Slice 8 Task 2)", () => {
  const p = defaultProject();
  expect(p.fabricRgb).toEqual([235, 232, 223]);
});

test("defaultProject has a project-level hoopId default of null (= use the suggestion)", () => {
  expect(defaultProject().hoopId).toBeNull();
});

test("migrateProject preserves a manual hoopId and fills null onto pre-hoop-picker saves", () => {
  // A pre-hoop save (no hoopId at all) loads as "use the suggestion" —
  // same additive spread-merge story as fabricRgb.
  const old = migrateProject({ version: 2, elements: [defaultTextElement("e1")], selectedId: "e1" });
  expect(old.hoopId).toBeNull();

  // A manual pick survives migration untouched.
  const picked = migrateProject({
    version: 2,
    elements: [defaultTextElement("e1")],
    selectedId: "e1",
    hoopId: "6x10",
  });
  expect(picked.hoopId).toBe("6x10");
});

test("defaultTextElement has sane beginner defaults", () => {
  const el = defaultTextElement("e1");
  expect(el).toEqual({
    id: "e1",
    type: "text",
    text: "",
    fontKey: "medium_font",
    colorRgb: [20, 20, 20],
    colorRanges: [],
    weightPreset: "normal",
    slantDeg: 0,
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    align: "center",
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});

test("defaultImageElement has sane beginner defaults", () => {
  const el = defaultImageElement("e7");
  expect(el).toEqual({
    id: "e7",
    type: "image",
    nColors: 4,
    removeBg: true,
    threadRgb: {},
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});

test("update returns a new object and merges top-level fields", () => {
  const p = defaultProject();
  const q = update(p, { garmentId: "hat_front" });
  expect(q.garmentId).toBe("hat_front");
  expect(p.garmentId).toBe("left_chest"); // original untouched
  expect(q).not.toBe(p);
});

// --- addElement ---------------------------------------------------------

test("addElement appends a new element, ids increment as eN, and selects it", () => {
  const p = defaultProject();
  const q = addElement(p, "text", 101.6);
  expect(q.elements).toHaveLength(2);
  expect(q.elements[1].id).toBe("e2");
  expect(q.selectedId).toBe("e2");
  // original project untouched
  expect(p.elements).toHaveLength(1);
  expect(p.selectedId).toBe("e1");
});

test("addElement seeds non-first elements with a size relative to the hoop and staggers offsetYMm", () => {
  const p = defaultProject();
  const q = addElement(p, "text", 100); // hoopWmm = 100
  expect(q.elements[1].sizeMm).toBe(Math.round(0.4 * 100));
  expect(q.elements[1].offsetYMm).toBe(-10 * 1);

  const r = addElement(q, "image", 100);
  expect(r.elements[2].sizeMm).toBe(Math.round(0.4 * 100));
  expect(r.elements[2].offsetYMm).toBe(-10 * 2);
  expect(r.elements[2].type).toBe("image");
});

test("addElement leaves the first element's plain defaults alone (no seeding)", () => {
  const p = defaultProject();
  expect(p.elements[0].sizeMm).toBeNull();
  expect(p.elements[0].offsetYMm).toBe(0);
});

test("addElement of type image produces a fresh defaultImageElement shape (seeded)", () => {
  const p = defaultProject();
  const q = addElement(p, "image", 100);
  const el = q.elements[1];
  expect(el.type).toBe("image");
  expect(el.nColors).toBe(4);
  expect(el.removeBg).toBe(true);
});

// --- addSeededTextElement (text-cluster "convert to text") ----------------

test("addSeededTextElement appends one text element seeded over defaultTextElement, and selects it", () => {
  const p = defaultProject(); // e1, one element
  const seed = {
    colorRgb: [10, 20, 30],
    rotationDeg: 12,
    offsetXMm: 5,
    offsetYMm: -7,
    sizeMm: 22,
    text: "",
    fontKey: null,
  };
  const { project: q, id } = addSeededTextElement(p, seed, 100);

  expect(q.elements).toHaveLength(2);
  expect(p.elements).toHaveLength(1); // original untouched

  const el = q.elements.find((e) => e.id === id);
  expect(el).toBeTruthy();
  expect(el.type).toBe("text");
  expect(el.text).toBe("");
  expect(el.fontKey).toBeNull(); // deliberate override of defaultTextElement's "medium_font"
  expect(el.colorRgb).toEqual([10, 20, 30]);
  expect(el.rotationDeg).toBe(12);
  expect(el.offsetXMm).toBe(5);
  expect(el.offsetYMm).toBe(-7);
  expect(el.sizeMm).toBe(22);

  // Fields the seed did NOT touch still come from defaultTextElement.
  expect(el.align).toBe("center");
  expect(el.underlay).toBe(true);

  // Selection moves to the new element, same as addElement.
  expect(q.selectedId).toBe(id);
  expect(q.selectedIds).toEqual([id]);
});

test("addSeededTextElement returns the new element's id explicitly, usable immediately by the caller", () => {
  const p = defaultProject();
  const { project: q, id } = addSeededTextElement(p, { text: "", fontKey: null }, 100);
  // The id is real and resolvable in the returned project without relying on
  // selectedId (the convention addElement's existing callers use) --
  // exercising the alternative convention this function documents choosing.
  expect(id).toBe("e2");
  expect(q.elements.map((e) => e.id)).toContain(id);
});

test("addSeededTextElement seed wins over the hoop-relative size/offset stagger addElement would otherwise apply", () => {
  const p = defaultProject();
  const { project: q, id } = addSeededTextElement(p, { sizeMm: 5, offsetXMm: 1, offsetYMm: 2 }, 100);
  const el = q.elements.find((e) => e.id === id);
  expect(el.sizeMm).toBe(5); // not Math.round(0.4 * 100)
  expect(el.offsetXMm).toBe(1);
  expect(el.offsetYMm).toBe(2); // not -10 * 1
});

// --- removeElement --------------------------------------------------------

test("removeElement removes the given element by id", () => {
  const p = addElement(defaultProject(), "text", 100); // e1, e2
  const q = removeElement(p, "e2");
  expect(q.elements).toHaveLength(1);
  expect(q.elements[0].id).toBe("e1");
});

test("removeElement is a no-op when only one element remains", () => {
  const p = defaultProject();
  const q = removeElement(p, "e1");
  expect(q.elements).toHaveLength(1);
  expect(q).toEqual(p);
});

test("removeElement fixes selectedId when the selected element is removed", () => {
  let p = addElement(defaultProject(), "text", 100); // e1, e2 selected=e2
  expect(p.selectedId).toBe("e2");
  const q = removeElement(p, "e2");
  expect(q.selectedId).toBe("e1");
});

test("removeElement leaves selectedId alone when a non-selected element is removed", () => {
  let p = addElement(defaultProject(), "text", 100); // e1, e2 selected=e2
  p = selectElement(p, "e1");
  const q = removeElement(p, "e2");
  expect(q.selectedId).toBe("e1");
  expect(q.elements).toHaveLength(1);
});

test("removeElement prunes textConversions entries naming the removed element", () => {
  // Element ids are recycled (nextElementId is max+1 over the SURVIVORS), so a
  // conversion entry left pointing at a deleted element ends up naming an
  // innocent NEW one -- and DigitizePanel's "Undo — remove text element"
  // button then deletes that. Found by a sibling-pattern sweep 2026-08-26.
  let p = addElement(defaultProject(), "text", 100); // e1, e2
  p = updateElement(p, "e1", { textConversions: { c1: "e2", c2: "e3" } });

  const q = removeElement(p, "e2");
  const e1 = q.elements.find((el) => el.id === "e1");
  expect(e1.textConversions).toEqual({ c2: "e3" }); // c1 pruned, c2 untouched

  // And the recycling that makes it matter is real, not hypothetical: the very
  // next element added takes the freed id back.
  const r = addElement(q, "text", 100);
  expect(r.elements.map((el) => el.id)).toContain("e2");
  // ...and it inherits nothing.
  const stillE1 = r.elements.find((el) => el.id === "e1");
  expect(Object.values(stillE1.textConversions)).not.toContain("e2");
});

test("removeElement leaves untouched elements strictly identical", () => {
  // The prune must not rebuild elements that carry no matching entry -- keyed
  // {#each} blocks and identity-based memoization would see spurious changes.
  let p = addElement(defaultProject(), "text", 100); // e1, e2
  p = addElement(p, "text", 100);                    // e3
  p = updateElement(p, "e1", { textConversions: { c1: "e3" } });
  const before = p.elements.find((el) => el.id === "e2");
  const q = removeElement(p, "e3");
  expect(q.elements.find((el) => el.id === "e2")).toBe(before); // same object
});

// --- selectElement / updateElement ----------------------------------------

test("selectElement sets selectedId immutably", () => {
  const p = addElement(defaultProject(), "text", 100);
  const q = selectElement(p, "e1");
  expect(q.selectedId).toBe("e1");
  expect(p.selectedId).toBe("e2"); // original untouched
});

test("updateElement patches only the targeted element, immutably", () => {
  const p = addElement(defaultProject(), "text", 100); // e1, e2
  const q = updateElement(p, "e2", { text: "Hi" });
  expect(q.elements[1].text).toBe("Hi");
  expect(q.elements[0].text).toBe(""); // e1 untouched
  // originals untouched
  expect(p.elements[1].text).toBe("");
  expect(q).not.toBe(p);
  expect(q.elements).not.toBe(p.elements);
});

// --- migrateProject ---------------------------------------------------------

test("migrateProject passes a well-formed v2 project through (spread-merged over defaults)", () => {
  const v2 = { version: 2, garmentId: "hat_front", selectedId: "e1", elements: [defaultTextElement("e1")] };
  const m = migrateProject(v2);
  expect(m.version).toBe(2);
  expect(m.garmentId).toBe("hat_front");
  expect(m.elements).toHaveLength(1);
});

test("migrateProject fills in missing top-level fields on a sparse v2 input", () => {
  const sparse = { version: 2, elements: [defaultTextElement("e1")] };
  const m = migrateProject(sparse);
  expect(m.garmentId).toBe("left_chest"); // fell back to default
  expect(m.selectedId).toBe("e1");
});

test("migrateProject falls back to default elements when a v2 project has none", () => {
  const broken = { version: 2, garmentId: "left_chest", selectedId: "e1", elements: [] };
  const m = migrateProject(broken);
  expect(m.elements).toHaveLength(1);
});

test("migrateProject converts a real v1 text-mode fixture into one text element", () => {
  const v1 = {
    garmentId: "left_chest",
    text: "Kent",
    fontKey: "manga_impact",
    sizeMm: 50,
    offsetXMm: 3,
    offsetYMm: -2,
    colorRgb: [200, 0, 0],
    underlay: true,
    mode: "text",
    nColors: 4,
    removeBg: true,
    letterSpacingMm: 1.5,
  };
  const m = migrateProject(v1);
  expect(m.version).toBe(2);
  expect(m.garmentId).toBe("left_chest");
  expect(m.selectedId).toBe("e1");
  expect(m.elements).toHaveLength(1);
  const el = m.elements[0];
  expect(el.id).toBe("e1");
  expect(el.type).toBe("text");
  expect(el.text).toBe("Kent");
  expect(el.fontKey).toBe("manga_impact");
  expect(el.colorRgb).toEqual([200, 0, 0]);
  expect(el.letterSpacingMm).toBe(1.5);
  expect(el.sizeMm).toBe(50);
  expect(el.offsetXMm).toBe(3);
  expect(el.offsetYMm).toBe(-2);
});

test("migrateProject converts a real v1 image-mode fixture into one image element", () => {
  const v1 = {
    garmentId: "patch",
    text: "",
    fontKey: "medium_font",
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
    colorRgb: [20, 20, 20],
    underlay: true,
    mode: "image",
    nColors: 6,
    removeBg: false,
    letterSpacingMm: 0,
  };
  const m = migrateProject(v1);
  expect(m.version).toBe(2);
  expect(m.garmentId).toBe("patch");
  expect(m.elements).toHaveLength(1);
  const el = m.elements[0];
  expect(el.type).toBe("image");
  expect(el.nColors).toBe(6);
  expect(el.removeBg).toBe(false);
});

test("migrateProject (B13) merges fabricRgb (and other project-level defaults) onto a migrated v1 blob", () => {
  const v1 = { garmentId: "hat_front", text: "Kent", mode: "text" };
  const m = migrateProject(v1);
  expect(m.fabricRgb).toEqual([235, 232, 223]);
  // and the v1 fields that WERE present still won out over the defaults
  expect(m.garmentId).toBe("hat_front");
  expect(m.elements[0].text).toBe("Kent");
});

test("migrateProject only carries over v1 fields that were actually present", () => {
  const v1 = { mode: "text" }; // minimal — no text/fontKey/etc present
  const m = migrateProject(v1);
  const el = m.elements[0];
  expect(el).toEqual(defaultTextElement("e1"));
});

test("migrateProject falls back to defaultProject() for unparseable input", () => {
  expect(migrateProject(null)).toEqual(defaultProject());
  expect(migrateProject(undefined)).toEqual(defaultProject());
  expect(migrateProject(42)).toEqual(defaultProject());
  expect(migrateProject("garbage")).toEqual(defaultProject());
  expect(migrateProject({})).toEqual(defaultProject());
  expect(migrateProject({ foo: "bar" })).toEqual(defaultProject());
});

// --- design (imported DST) elements ------------------------------------

import { defaultDesignElement } from "./project.js";

test("defaultDesignElement has the imported-design shape (no file yet, native size)", () => {
  const el = defaultDesignElement("e9");
  expect(el).toMatchObject({
    id: "e9", type: "design", name: "", dstBase64: null,
    blockColors: {}, sizeMm: null, offsetXMm: 0, offsetYMm: 0,
  });
});

test("addElement 'design' appends a design element, selects it, and never seeds sizeMm (native size must survive)", () => {
  let p = defaultProject();
  p = addElement(p, "design", 100);
  expect(p.elements).toHaveLength(2);
  const el = p.elements[1];
  expect(el.type).toBe("design");
  expect(p.selectedId).toBe(el.id);
  // Staggered like any second element, but NOT pre-resized -- a pre-digitized
  // file defaults to its native stitch size.
  expect(el.sizeMm).toBeNull();
  expect(el.offsetYMm).toBe(-10);
});

// ---- multi-select (Ctrl+click): selectedIds ---------------------------------
// Invariants: selectedIds is never empty and always contains selectedId (the
// "primary"). selectedId stays a plain string so every pre-multi-select
// consumer keeps working unchanged.

import { toggleSelectElement, selectedIdsOf, updateElements } from "./project.js";

test("defaultProject starts with a single-member selectedIds matching selectedId", () => {
  const p = defaultProject();
  expect(p.selectedIds).toEqual(["e1"]);
});

test("selectElement collapses a multi-selection to the clicked element", () => {
  let p = { ...defaultProject() };
  p = addElement(p, "text", 100);
  p = toggleSelectElement(p, "e1"); // e2 (added, primary) + e1
  expect(selectedIdsOf(p).sort()).toEqual(["e1", "e2"]);
  p = selectElement(p, "e2");
  expect(p.selectedIds).toEqual(["e2"]);
  expect(p.selectedId).toBe("e2");
});

test("toggleSelectElement adds an unselected element and makes it primary", () => {
  let p = addElement(defaultProject(), "text", 100); // e2 selected
  p = toggleSelectElement(p, "e1");
  expect(selectedIdsOf(p)).toEqual(["e2", "e1"]);
  expect(p.selectedId).toBe("e1"); // last clicked wins
});

test("toggleSelectElement removes a selected member; removing the primary promotes the last remaining", () => {
  let p = addElement(defaultProject(), "text", 100);
  p = toggleSelectElement(p, "e1"); // [e2, e1], primary e1
  p = toggleSelectElement(p, "e1"); // remove the primary
  expect(p.selectedIds).toEqual(["e2"]);
  expect(p.selectedId).toBe("e2");
});

test("toggleSelectElement on the only selected element is a no-op (selection never empties)", () => {
  const p = defaultProject();
  expect(toggleSelectElement(p, "e1")).toBe(p);
});

test("addElement resets the selection to just the new element", () => {
  let p = addElement(defaultProject(), "text", 100);
  p = toggleSelectElement(p, "e1"); // two selected
  p = addElement(p, "text", 100);   // e3
  expect(p.selectedIds).toEqual(["e3"]);
  expect(p.selectedId).toBe("e3");
});

test("removeElement drops the removed id from the multi-selection", () => {
  let p = addElement(defaultProject(), "text", 100);
  p = toggleSelectElement(p, "e1"); // [e2, e1], primary e1
  p = removeElement(p, "e2");
  expect(p.selectedIds).toEqual(["e1"]);
  expect(p.selectedId).toBe("e1");
});

test("selectedIdsOf falls back to selectedId for pre-multi-select project shapes", () => {
  expect(selectedIdsOf({ selectedId: "e7" })).toEqual(["e7"]);
  expect(selectedIdsOf({ selectedId: "e7", selectedIds: [] })).toEqual(["e7"]);
});

test("updateElements patches each listed element with ITS OWN patch, others untouched", () => {
  let p = addElement(defaultProject(), "text", 100);
  p = addElement(p, "text", 100); // e1, e2, e3
  const q = updateElements(p, { e1: { offsetXMm: 5 }, e3: { offsetXMm: -5 } });
  expect(q.elements.find((e) => e.id === "e1").offsetXMm).toBe(5);
  expect(q.elements.find((e) => e.id === "e2").offsetXMm).toBe(0);
  expect(q.elements.find((e) => e.id === "e3").offsetXMm).toBe(-5);
  expect(p.elements.find((e) => e.id === "e1").offsetXMm).toBe(0); // immutable
});

test("migrateProject: a v2 save without selectedIds gets [selectedId]", () => {
  const v2 = { version: 2, garmentId: "hat_front", selectedId: "e2",
    elements: [defaultTextElement("e1"), defaultTextElement("e2")] };
  const m = migrateProject(v2);
  expect(m.selectedIds).toEqual(["e2"]);
});

test("migrateProject: selectedIds referencing unknown elements collapses to [selectedId]", () => {
  const v2 = { version: 2, garmentId: "left_chest", selectedId: "e1", selectedIds: ["e1", "ghost"],
    elements: [defaultTextElement("e1")] };
  // "ghost" filtered out; remaining still contains selectedId, so it survives filtered.
  expect(migrateProject(v2).selectedIds).toEqual(["e1"]);
});

test("migrateProject: a valid multi-selection survives migration intact", () => {
  const v2 = { version: 2, garmentId: "left_chest", selectedId: "e2", selectedIds: ["e1", "e2"],
    elements: [defaultTextElement("e1"), defaultTextElement("e2")] };
  expect(migrateProject(v2).selectedIds).toEqual(["e1", "e2"]);
});

// --- digitized elements (build step 10) -------------------------------------

test("defaultDigitizedElement carries the hybrid-persistence trio: source, params (service field names), baked result", () => {
  const el = defaultDigitizedElement("e9");
  expect(el.type).toBe("digitized");
  expect(el.sourcePng).toBeNull();
  expect(el.result).toBeNull();
  expect(el.params).toEqual(DEFAULT_DIGITIZE_PARAMS);
  expect(el.params).not.toBe(DEFAULT_DIGITIZE_PARAMS); // own copy, never the shared object
  expect(el.sizeMm).toBeNull();
  expect(el.warnings).toEqual([]);
  expect(el.blockColors).toEqual({});
});

test("addElement 'digitized' staggers placement but keeps sizeMm null (native = digitized target size)", () => {
  let p = defaultProject();
  p = addElement(p, "digitized", 100); // e2
  const el = p.elements.find((e) => e.id === "e2");
  expect(el.type).toBe("digitized");
  expect(el.sizeMm).toBeNull();
  expect(el.offsetYMm).toBe(-10);
  expect(p.selectedId).toBe("e2");
});

test("migrateProject fills a digitized element's missing fields (additive migration, same as top-level)", () => {
  // A save from a build where params had fewer knobs and warnings didn't exist.
  const old = {
    version: 2, garmentId: "left_chest", selectedId: "e1",
    elements: [{
      id: "e1", type: "digitized", name: "logo.png", sourcePng: "QQ==",
      params: { target_width_mm: 55 },
      result: { stitches: [], colors: [] },
      offsetXMm: 3, offsetYMm: -4,
    }],
  };
  const m = migrateProject(old);
  const el = m.elements[0];
  expect(el.params.target_width_mm).toBe(55); // saved value wins
  expect(el.params.border).toBe("off"); // newer knob defaulted
  expect(el.params.satin).toBe(true);
  expect(el.warnings).toEqual([]);
  expect(el.blockColors).toEqual({});
  expect(el.offsetXMm).toBe(3);
  expect(el.result).toEqual({ stitches: [], colors: [] });
});

test("migrateProject fills the shape-layers fields on a pre-layers digitized save (review/overrides/deletions/appliedEdits)", () => {
  // A save from the build right before the Layers panel existed: it has a
  // result but none of the layer-list fields. It must load with today's
  // defaults, not undefined — the panel dereferences all four.
  const old = {
    version: 2, garmentId: "left_chest", selectedId: "e1",
    elements: [{
      id: "e1", type: "digitized", name: "logo.png", sourcePng: "QQ==",
      params: { target_width_mm: 80, max_colors: 6, satin: true, fill_angle_deg: null, border: "off" },
      result: { stitches: [], colors: [] }, warnings: [], blockColors: {},
      sizeMm: null, offsetXMm: 0, offsetYMm: 0, rotationDeg: 0,
    }],
  };
  const el = migrateProject(old).elements[0];
  expect(el.review).toBeNull();
  expect(el.shapeOverrides).toEqual({});
  expect(el.deletedShapeIds).toEqual([]);
  expect(el.appliedEdits).toBeNull();
  // And a save that HAS them keeps them verbatim.
  const edited = {
    ...old,
    elements: [{
      ...old.elements[0],
      review: { brandId: "isacord", shapes: [{ id: "Sabc", tier: "fill" }] },
      shapeOverrides: { Sabc: { thread_index: 3, rgb: [1, 2, 3] } },
      deletedShapeIds: ["Sdef"],
      appliedEdits: '[["Sdef"],{}]',
    }],
  };
  const kept = migrateProject(edited).elements[0];
  expect(kept.review.shapes[0].id).toBe("Sabc");
  expect(kept.shapeOverrides.Sabc.thread_index).toBe(3);
  expect(kept.deletedShapeIds).toEqual(["Sdef"]);
  expect(kept.appliedEdits).toBe('[["Sdef"],{}]');
});

test("migrateProject leaves non-digitized elements byte-identical (old projects load unchanged)", () => {
  const text = defaultTextElement("e1");
  const image = { ...defaultImageElement("e2"), nColors: 5 };
  const m = migrateProject({ version: 2, garmentId: "left_chest", selectedId: "e1", elements: [text, image] });
  expect(m.elements[0]).toBe(text); // same object, untouched by the map
  expect(m.elements[1]).toBe(image);
});

// --- manual digitizing mode (element factory) ------------------------------

import { defaultManualElement, defaultManualShape } from "./project.js";

test("defaultManualElement has sane beginner defaults (no shapes yet)", () => {
  const el = defaultManualElement("e9");
  expect(el).toEqual({
    id: "e9",
    type: "manual",
    shapes: [],
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});

test("defaultManualShape defaults to fill, a beginner-safe base color, and auto angle", () => {
  const s = defaultManualShape("s1");
  expect(s).toEqual({
    id: "s1",
    points: [],
    curves: {},
    stitchType: "fill",
    colorRgb: [20, 20, 20],
    angleDeg: null,
  });
});

test("addElement 'manual' produces a fresh defaultManualElement shape, seeded like image/text", () => {
  let p = defaultProject();
  p = addElement(p, "manual", 100);
  const el = p.elements[1];
  expect(el.type).toBe("manual");
  expect(el.shapes).toEqual([]);
  // Non-first elements get a hoop-relative size seed, same rule image/text
  // elements follow (only design/digitized keep sizeMm null for native size).
  expect(el.sizeMm).toBe(40); // 0.4 * 100
  expect(el.offsetYMm).toBe(-10);
  expect(p.selectedId).toBe(el.id);
});

test("migrateProject fills a manual element's missing fields (additive migration, same as digitized)", () => {
  const sparse = { id: "e2", type: "manual" }; // saved before `underlay`/offsets existed
  const m = migrateProject({ version: 2, garmentId: "left_chest", selectedId: "e2", elements: [sparse] });
  const el = m.elements[0];
  expect(el.shapes).toEqual([]);
  expect(el.underlay).toBe(true);
  expect(el.sizeMm).toBeNull();
  expect(el.offsetXMm).toBe(0);
  expect(el.offsetYMm).toBe(0);
});

test("migrateProject preserves a manual element's real shapes, and tolerates a corrupt shapes field", () => {
  const withShapes = { id: "e2", type: "manual", shapes: [defaultManualShape("s1")] };
  const kept = migrateProject({ version: 2, garmentId: "left_chest", selectedId: "e2", elements: [withShapes] }).elements[0];
  expect(kept.shapes).toEqual([defaultManualShape("s1")]);

  const corrupt = { id: "e2", type: "manual", shapes: "not-an-array" };
  const fixed = migrateProject({ version: 2, garmentId: "left_chest", selectedId: "e2", elements: [corrupt] }).elements[0];
  expect(fixed.shapes).toEqual([]);
});

// --- preset basic-shape elements (element factory) ---------------------------

import { defaultShapeElement } from "./project.js";

test("defaultShapeElement starts as a 50 mm circle with beginner-safe defaults", () => {
  const el = defaultShapeElement("e9");
  expect(el).toEqual({
    id: "e9",
    type: "shape",
    kind: "circle",
    params: {},
    colorRgb: [20, 20, 20],
    underlay: true,
    sizeMm: 50,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});

test("addElement 'shape' keeps the factory's explicit 50 mm size (no hoop-relative reseed), staggers like the rest", () => {
  let p = defaultProject();
  p = addElement(p, "shape", 100);
  const el = p.elements[1];
  expect(el.type).toBe("shape");
  expect(el.kind).toBe("circle");
  expect(el.sizeMm).toBe(50); // factory value, NOT 0.4 * hoopWmm
  expect(el.offsetYMm).toBe(-10);
  expect(p.selectedId).toBe(el.id);
});

test("migrateProject fills a shape element's missing fields and tolerates a corrupt params field", () => {
  const sparse = { id: "e2", type: "shape", kind: "star" }; // saved before some field existed
  const m = migrateProject({ version: 2, garmentId: "left_chest", selectedId: "e2", elements: [sparse] });
  const el = m.elements[0];
  expect(el.kind).toBe("star");
  expect(el.params).toEqual({});
  expect(el.underlay).toBe(true);
  expect(el.colorRgb).toEqual([20, 20, 20]);
  expect(el.sizeMm).toBe(50);

  const corrupt = { id: "e2", type: "shape", kind: "rect", params: "not-an-object" };
  const fixed = migrateProject({ version: 2, garmentId: "left_chest", selectedId: "e2", elements: [corrupt] }).elements[0];
  expect(fixed.params).toEqual({});
});

test("migrateProject preserves a shape element's real kind/params", () => {
  const saved = { id: "e2", type: "shape", kind: "star", params: { points: 7, innerRatio: 0.3 }, sizeMm: 32 };
  const el = migrateProject({ version: 2, garmentId: "left_chest", selectedId: "e2", elements: [saved] }).elements[0];
  expect(el.kind).toBe("star");
  expect(el.params).toEqual({ points: 7, innerRatio: 0.3 });
  expect(el.sizeMm).toBe(32);
});
