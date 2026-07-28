// Project model v2 — a project is a garment + an ordered list of "elements"
// (text or image layers). Only one element is selected/edited at a time via
// `selectedId`. Everything here is immutable: every function returns a fresh
// project (and fresh elements/arrays) rather than mutating its input.

export function defaultTextElement(id) {
  return {
    id,
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
  };
}

export function defaultImageElement(id) {
  return {
    id,
    type: "image",
    nColors: 4,
    removeBg: true,
    threadRgb: {},
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}

// An imported pre-digitized design file (DST). `dstBase64` holds the raw
// file bytes (base64) — small enough for localStorage (DSTs are KB-scale;
// DesignPanel enforces a size cap on upload) and the only representation
// that survives a save/load round-trip losslessly. `blockColors` maps color-
// block index -> [r,g,b] thread overrides (DST files carry no color data).
export function defaultDesignElement(id) {
  return {
    id,
    type: "design",
    name: "",
    dstBase64: null,
    blockColors: {},
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}

export function defaultProject() {
  return {
    version: 2,
    garmentId: "left_chest",
    selectedId: "e1",
    elements: [defaultTextElement("e1")],
    // Project-level (not per-element) — the embroidery field's fabric render
    // color, [r,g,b]. Render-only: never touches stitch generation (see
    // generate.js). "Natural" canvas tone, matching the pre-Slice-8 hardcoded
    // field background so existing projects look unchanged until a user
    // picks a different swatch on the Garment step.
    fabricRgb: [235, 232, 223],
  };
}

// Top-level patch merge — unchanged behavior from v1, still used for
// garment/selectedId-level fields (not per-element fields).
export function update(project, patch) {
  return { ...project, ...patch };
}

function nextElementId(elements) {
  let max = 0;
  for (const el of elements) {
    const m = /^e(\d+)$/.exec(el.id);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  return "e" + (max + 1);
}

// Adds a new element ("text" or "image") to the project and selects it.
// The first element in a project keeps the factory's plain defaults; every
// element added after that is seeded with a size relative to the hoop
// (hoopWmm, in mm) and staggered downward so it doesn't land exactly on top
// of existing elements.
export function addElement(project, type, hoopWmm) {
  const id = nextElementId(project.elements);
  const factory =
    type === "image" ? defaultImageElement :
    type === "design" ? defaultDesignElement :
    defaultTextElement;
  let el = factory(id);
  const n = project.elements.length;
  if (n > 0) {
    // Imported designs keep sizeMm null (= the file's native stitch size,
    // hoop-clamped) — seeding a resize would silently rescale pre-digitized
    // stitches before the user ever sees them at true size.
    el = type === "design"
      ? { ...el, offsetYMm: -10 * n }
      : { ...el, sizeMm: Math.round(0.4 * hoopWmm), offsetYMm: -10 * n };
  }
  return { ...project, elements: [...project.elements, el], selectedId: id };
}

// Removes an element by id. A project must always keep at least one
// element, so removing the last remaining element is a no-op. If the
// removed element was selected, selection falls back to the first
// remaining element.
export function removeElement(project, id) {
  if (project.elements.length <= 1) return project;
  const elements = project.elements.filter((el) => el.id !== id);
  if (elements.length === project.elements.length) return project; // id not found
  const selectedId = project.selectedId === id ? elements[0].id : project.selectedId;
  return { ...project, elements, selectedId };
}

export function selectElement(project, id) {
  return { ...project, selectedId: id };
}

// Patches a single element by id, leaving all other elements untouched.
export function updateElement(project, id, patch) {
  const elements = project.elements.map((el) => (el.id === id ? { ...el, ...patch } : el));
  return { ...project, elements };
}

function migrateV1(input) {
  const garmentId = input.garmentId || defaultProject().garmentId;
  let el;
  if (input.mode === "image") {
    el = defaultImageElement("e1");
    if (input.nColors !== undefined) el.nColors = input.nColors;
    if (input.removeBg !== undefined) el.removeBg = input.removeBg;
    if (input.sizeMm !== undefined) el.sizeMm = input.sizeMm;
    if (input.offsetXMm !== undefined) el.offsetXMm = input.offsetXMm;
    if (input.offsetYMm !== undefined) el.offsetYMm = input.offsetYMm;
  } else {
    el = defaultTextElement("e1");
    if (input.text !== undefined) el.text = input.text;
    if (input.fontKey !== undefined) el.fontKey = input.fontKey;
    if (input.colorRgb !== undefined) el.colorRgb = input.colorRgb;
    if (input.letterSpacingMm !== undefined) el.letterSpacingMm = input.letterSpacingMm;
    if (input.sizeMm !== undefined) el.sizeMm = input.sizeMm;
    if (input.offsetXMm !== undefined) el.offsetXMm = input.offsetXMm;
    if (input.offsetYMm !== undefined) el.offsetYMm = input.offsetYMm;
  }
  return { version: 2, garmentId, selectedId: "e1", elements: [el] };
}

// Normalizes any input (a v2 project, a v1 project, or garbage) into a valid
// v2 project.
export function migrateProject(input) {
  if (!input || typeof input !== "object") return defaultProject();

  if (input.version === 2) {
    // Already v2 — spread-merge over defaults so any missing top-level
    // field (garmentId, selectedId) falls back safely, and guard against a
    // corrupt/empty elements array (a project must have >= 1 element).
    const base = defaultProject();
    const merged = { ...base, ...input };
    if (!Array.isArray(merged.elements) || merged.elements.length === 0) {
      merged.elements = base.elements;
    }
    return merged;
  }

  // B13: migrateV1 returns a literal object with no notion of newer
  // project-level fields (e.g. fabricRgb) — spread-merge its result over
  // defaultProject() just like the v2 branch above does, so a v1 blob
  // migrates into a project that ALSO gets fabricRgb (and any future
  // project-level default) rather than being missing it forever.
  const looksLikeV1 = "mode" in input || "text" in input || "fontKey" in input;
  if (looksLikeV1) return { ...defaultProject(), ...migrateV1(input) };

  return defaultProject();
}
