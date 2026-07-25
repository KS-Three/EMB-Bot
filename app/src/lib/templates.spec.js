import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";

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

test("applyTemplate merges patch fields into the project", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  const hatName = TEMPLATES.find((t) => t.id === "hat-name");
  const p = applyTemplate(defaultProject(), hatName);
  expect(p.garmentId).toBe("hat_front");
  expect(p.mode).toBe("text");
  expect(p.fontKey).toBe("manga_impact");
  expect(p.text).toBe("YOUR NAME");
});

test("applyTemplate does not mutate the original project", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  const original = defaultProject();
  const snapshot = { ...original };
  applyTemplate(original, TEMPLATES[0]);
  expect(original).toEqual(snapshot);
});

test("applyTemplate resets offsets to 0 when the patch omits them", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject, update } = await import("./project.js");
  // chest-name's patch has no offsetXMm/offsetYMm keys.
  const chestName = TEMPLATES.find((t) => t.id === "chest-name");
  expect(chestName.patch.offsetXMm).toBeUndefined();
  const dirty = update(defaultProject(), { offsetXMm: 12, offsetYMm: -8 });
  const p = applyTemplate(dirty, chestName);
  expect(p.offsetXMm).toBe(0);
  expect(p.offsetYMm).toBe(0);
});

test("applyTemplate keeps offsets when the patch explicitly sets them", async () => {
  const { applyTemplate } = await import("./templates.js");
  const { defaultProject, update } = await import("./project.js");
  const dirty = update(defaultProject(), { offsetXMm: 12, offsetYMm: -8 });
  const customTemplate = { id: "x", label: "x", hint: "x", patch: { garmentId: "left_chest", offsetXMm: 5, offsetYMm: 3 } };
  const p = applyTemplate(dirty, customTemplate);
  expect(p.offsetXMm).toBe(5);
  expect(p.offsetYMm).toBe(3);
});

test("applyTemplate resets sizeMm to the patch's value or null", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject, update } = await import("./project.js");
  const dirty = update(defaultProject(), { sizeMm: 40 });

  const chestName = TEMPLATES.find((t) => t.id === "chest-name");
  const withSize = applyTemplate(dirty, chestName);
  expect(withSize.sizeMm).toBe(76.2);

  const scriptName = TEMPLATES.find((t) => t.id === "script-name");
  const withoutSize = applyTemplate(dirty, scriptName);
  expect(withoutSize.sizeMm).toBeNull();

  const logoPatch = TEMPLATES.find((t) => t.id === "logo-patch");
  expect(logoPatch.patch.sizeMm).toBeUndefined();
  const logoResult = applyTemplate(dirty, logoPatch);
  expect(logoResult.sizeMm).toBeNull();
});

// Engine-backed validation: every template must reference a real garment
// and (for text-mode templates) a real font in the satin font registry.
// Loads the actual engine scripts the same way generate.spec.js does.
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin", "satinplay", "satinfont", "dst", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});

test("every TEMPLATES entry resolves a real garment via EMB.getGarment", async () => {
  const { EMB } = await import("./emb.js");
  const { TEMPLATES } = await import("./templates.js");
  for (const t of TEMPLATES) {
    expect(EMB.getGarment(t.patch.garmentId), `${t.id}: garmentId "${t.patch.garmentId}"`).toBeTruthy();
  }
});

test("every non-image TEMPLATES entry's fontKey exists in EMB.SATIN_FONTS", async () => {
  const { EMB } = await import("./emb.js");
  const { TEMPLATES } = await import("./templates.js");
  for (const t of TEMPLATES) {
    if (t.patch.mode === "image") continue;
    expect(EMB.SATIN_FONTS[t.patch.fontKey], `${t.id}: fontKey "${t.patch.fontKey}"`).toBeTruthy();
  }
});
