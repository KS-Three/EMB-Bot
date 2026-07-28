import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";

test("TEMPLATES has exactly 4 entries with id/label/hint/patch", async () => {
  const { TEMPLATES } = await import("./templates.js");
  expect(TEMPLATES).toHaveLength(4);
  for (const t of TEMPLATES) {
    expect(typeof t.id).toBe("string");
    expect(typeof t.label).toBe("string");
    expect(typeof t.hint).toBe("string");
    expect(typeof t.patch).toBe("object");
  }
  expect(TEMPLATES.map((t) => t.id)).toEqual(["hat-name", "chest-name", "script-name", "logo-patch"]);
});

test("every TEMPLATES patch is v2-shaped: garmentId, selectedId 'e1', one element", async () => {
  const { TEMPLATES } = await import("./templates.js");
  for (const t of TEMPLATES) {
    expect(typeof t.patch.garmentId).toBe("string");
    expect(t.patch.selectedId).toBe("e1");
    expect(t.patch.elements).toHaveLength(1);
    expect(t.patch.elements[0].id).toBe("e1");
  }
});

test("applyTemplate merges patch fields into a fresh project", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  const hatName = TEMPLATES.find((t) => t.id === "hat-name");
  const p = applyTemplate(defaultProject(), hatName);
  expect(p.version).toBe(2);
  expect(p.garmentId).toBe("hat_front");
  expect(p.elements[0].type).toBe("text");
  expect(p.elements[0].fontKey).toBe("manga_impact");
  expect(p.elements[0].text).toBe("YOUR NAME");
});

test("applyTemplate does not mutate the original project", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  const original = defaultProject();
  const snapshot = JSON.parse(JSON.stringify(original));
  applyTemplate(original, TEMPLATES[0]);
  expect(original).toEqual(snapshot);
});

test("applyTemplate REPLACES the project entirely, ignoring prior dirty state", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject, addElement, updateElement } = await import("./project.js");

  let dirty = defaultProject();
  dirty = addElement(dirty, "text", 100); // now has 2 elements, offsets/size dirtied
  dirty = updateElement(dirty, "e1", { offsetXMm: 12, offsetYMm: -8, text: "leftover" });

  const chestName = TEMPLATES.find((t) => t.id === "chest-name");
  const p = applyTemplate(dirty, chestName);

  expect(p.elements).toHaveLength(1); // the stray second element is gone
  expect(p.elements[0].offsetXMm).toBe(0);
  expect(p.elements[0].offsetYMm).toBe(0);
  expect(p.elements[0].sizeMm).toBe(76.2);
  expect(p.elements[0].text).toBe("Your Name");
});

test("applyTemplate does not share element objects with TEMPLATES (regression: final-review-s5.md Important #2)", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  const hatName = TEMPLATES.find((t) => t.id === "hat-name");
  const originalText = hatName.patch.elements[0].text;

  const p = applyTemplate(defaultProject(), hatName);
  // Mutate the returned project's element in place, the way a two-way
  // `bind:value` would have before it was fixed -- this must NOT reach back
  // into the TEMPLATES constant.
  p.elements[0].text = "Smith";

  expect(hatName.patch.elements[0].text).toBe(originalText);
  expect(TEMPLATES.find((t) => t.id === "hat-name").patch.elements[0].text).toBe(originalText);

  // Applying the same template again must hand back a fresh copy with the
  // original starter text, not the mutated "Smith".
  const p2 = applyTemplate(defaultProject(), hatName);
  expect(p2.elements[0].text).toBe(originalText);
  expect(p2.elements[0]).not.toBe(p.elements[0]);
});

test("logo-patch template produces a fresh default image element", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  const logoPatch = TEMPLATES.find((t) => t.id === "logo-patch");
  const p = applyTemplate(defaultProject(), logoPatch);
  expect(p.garmentId).toBe("patch");
  expect(p.elements[0].type).toBe("image");
  expect(p.elements[0].nColors).toBe(4);
  expect(p.elements[0].removeBg).toBe(true);
  expect(p.elements[0].sizeMm).toBeNull();
});

// Engine-backed validation: every template must reference a real garment
// and (for text elements) a real font in the satin font registry.
// Loads the actual engine scripts the same way generate.spec.js does.
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin", "satinplay", "satinfont", "fontbin", "dst", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
});

test("every TEMPLATES entry resolves a real garment via EMB.getGarment", async () => {
  const { EMB } = await import("./emb.js");
  const { TEMPLATES } = await import("./templates.js");
  for (const t of TEMPLATES) {
    expect(EMB.getGarment(t.patch.garmentId), `${t.id}: garmentId "${t.patch.garmentId}"`).toBeTruthy();
  }
});

test("every text-element TEMPLATES entry's fontKey exists in EMB.SATIN_FONTS", async () => {
  const { EMB } = await import("./emb.js");
  const { TEMPLATES } = await import("./templates.js");
  for (const t of TEMPLATES) {
    const el = t.patch.elements[0];
    if (el.type === "image") continue;
    expect(EMB.SATIN_FONTS[el.fontKey], `${t.id}: fontKey "${el.fontKey}"`).toBeTruthy();
  }
});
