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
  // The template's size wins over the dirty project's — which is what this
  // test is about. Asserted against the template's own value rather than a
  // literal: this line read `toBe(76.2)` until 2026-09-08 and so doubled as an
  // accidental pin on a product decision, failing when that decision changed
  // for a measured reason. The behaviour this file should hold that size to is
  // guarded at the bottom, against the engine's lettering verdict.
  const templateSize = chestName.patch.elements[0].sizeMm;
  expect(typeof templateSize).toBe("number");
  expect(p.elements[0].sizeMm).toBe(templateSize);
  expect(p.elements[0].sizeMm).not.toBe(dirty.elements[0].sizeMm);
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
    if (el.type !== "text") continue; // only text elements carry a fontKey
    expect(EMB.SATIN_FONTS[el.fontKey], `${t.id}: fontKey "${el.fontKey}"`).toBeTruthy();
  }
});

// ---- Artwork-intent lane routing (regression: the PR #122 defect class, ----
// ---- template door). The logo-patch template must make the same          ----
// ---- health-based lane decision "+ Artwork" makes in App.onAddElement:   ----
// ---- service up -> digitized (pipeline), down -> image (browser lane).   ----

test("resolveArtworkType routes by digitizer health exactly like onAddElement", async () => {
  const { resolveArtworkType } = await import("./project.js");
  expect(resolveArtworkType({ status: "ok" })).toBe("digitized");
  expect(resolveArtworkType(null)).toBe("image");
});

test("logo-patch becomes a digitized element when the digitizer service is healthy", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject, defaultDigitizedElement } = await import("./project.js");
  const logoPatch = TEMPLATES.find((t) => t.id === "logo-patch");
  const p = applyTemplate(defaultProject(), logoPatch, { status: "ok" });
  expect(p.garmentId).toBe("patch");
  expect(p.elements[0].type).toBe("digitized");
  // A FRESH default digitized element, same shape addElement would build --
  // not an image element with its type string flipped.
  expect(p.elements[0]).toEqual(defaultDigitizedElement("e1"));
});

test("logo-patch stays an image element when the digitizer service is down", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  const logoPatch = TEMPLATES.find((t) => t.id === "logo-patch");
  const p = applyTemplate(defaultProject(), logoPatch, null);
  expect(p.elements[0].type).toBe("image");
  expect(p.elements[0].nColors).toBe(4);
  expect(p.elements[0].removeBg).toBe(true);
});

test("text templates ignore digitizer health entirely", async () => {
  const { TEMPLATES, applyTemplate } = await import("./templates.js");
  const { defaultProject } = await import("./project.js");
  for (const id of ["hat-name", "chest-name", "script-name"]) {
    const t = TEMPLATES.find((x) => x.id === id);
    const up = applyTemplate(defaultProject(), t, { status: "ok" });
    const down = applyTemplate(defaultProject(), t, null);
    expect(up.elements[0].type).toBe("text");
    expect(up.elements[0]).toEqual(down.elements[0]);
  }
});

// ---- What the template HANDS THE USER, not just its shape -----------------
//
// Every test above this point checks structure: the patch is v2-shaped, the
// garment resolves, the fontKey exists. All four passed on 2026-09-08 while
// the chest-name template produced a design the app itself condemned the
// instant you clicked it — "69% of this lettering is under 1 mm wide — size up
// for crisp letters", on the second of four starters advertised under "One
// click starts a ready-made design."
//
// A well-formed patch is not a good design. This generates each text
// template's real design through the same generateElement() the Studio calls
// and asserts the engine's own lettering verdict is silent — so the guard
// resolves against the engine's report, not against the template's fields.

test("no text template hands the user a design its own lettering check condemns", async () => {
  const { generateElement } = await import("./generate.js");
  const { letteringNote } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const { TEMPLATES, applyTemplate } = await import("./templates.js");

  let checked = 0;
  for (const t of TEMPLATES) {
    const project = applyTemplate({}, t, null);
    const el = project.elements[0];
    if (el.type !== "text") continue; // logo-patch has no text until the user uploads
    const garment = EMB.getGarment(project.garmentId);
    const design = generateElement(el, garment, {});
    const note = letteringNote(design.lettering, { lines: 1 });
    expect(note, `${t.id} ("${t.label}") starts the user at: ${note}`).toBe("");
    checked += 1;
  }
  // The loop is all `continue`s away from asserting nothing, which is how a
  // guard like this dies green. Pin the count.
  expect(checked, "expected the three text templates to be reached").toBe(3);
});

test("the chest-name template leaves room to move inside its placement box", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const { TEMPLATES, applyTemplate } = await import("./templates.js");

  // EmbroideryField.nudgeSelected and pointer drags clamp against the GARMENT
  // PLACEMENT BOX (hoopSizeMm returns garment.widthIn — the name says hoop,
  // the value is the placement). A design sewing the full box width therefore
  // has zero slack and cannot be moved at all: the arrow keys answer "At the
  // edge of the hoop" on the first press.
  //
  // This is not hypothetical. The first version of the size fix used 101.6 mm
  // for its cap height, and e2e/field-chrome.spec.js's keyboard-placement test
  // failed on it — correctly. A starter design the user cannot nudge is worse
  // than one 10 mm narrower, so the size is chosen to clear the lettering
  // check AND keep slack, and both halves are guarded.
  const t = TEMPLATES.find((x) => x.id === "chest-name");
  const project = applyTemplate({}, t, null);
  const garment = EMB.getGarment(project.garmentId);
  const design = generateElement(project.elements[0], garment, {});

  const placementMm = garment.widthIn * 25.4;
  const slackEachSide = (placementMm - design.widthMM) / 2;
  expect(
    slackEachSide,
    `sews ${design.widthMM.toFixed(1)} mm in a ${placementMm.toFixed(1)} mm placement — no room to nudge`
  ).toBeGreaterThan(2);
});
