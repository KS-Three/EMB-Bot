import { test, expect } from "vitest";
import {
  defaultProject,
  defaultTextElement,
  defaultImageElement,
  update,
  addElement,
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

test("defaultTextElement has sane beginner defaults", () => {
  const el = defaultTextElement("e1");
  expect(el).toEqual({
    id: "e1",
    type: "text",
    text: "",
    fontKey: "geneva_simple",
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
    fontKey: "geneva_simple",
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
