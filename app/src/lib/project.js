// Project model v2 — a project is a garment + an ordered list of "elements"
// (text or image layers). Only one element is selected/edited at a time via
// `selectedId`. Everything here is immutable: every function returns a fresh
// project (and fresh elements/arrays) rather than mutating its input.

export function defaultTextElement(id) {
  return {
    id,
    type: "text",
    text: "",
    // Default font for new text elements. Was geneva_simple until the
    // 2026-08-04 ShareAlike pull removed it from the shipping library
    // (font-license audit §9); medium_font is the OFL-licensed Ink/Stitch
    // workhorse with full charset coverage.
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

// Digitizing params, in the service's OWN field names (PipelineConfig,
// digitizer_core/config.py) so the persisted params object IS the /digitize
// config — no translation layer to drift. Lives here (not digitizer.js)
// because the element factory below needs it and the model layer imports
// nothing. fill_angle_deg null = per-shape auto (the service's default).
export const DEFAULT_DIGITIZE_PARAMS = {
  target_width_mm: 80,
  max_colors: 6,
  satin: true,
  fill_angle_deg: null,
  border: "off",
};

// An auto-digitized artwork element (build step 10). Persistence is hybrid
// (owner decision, do not relitigate): the element stores the SOURCE image
// (downscaled to processing size, PNG base64), the digitizing params, and
// the BAKED result Design — so save/load/export work fully offline. The
// localhost digitizer service is only needed to RE-digitize with new params.
// `result` is the service's Design verbatim ({ stitches, colors, widthMM,
// heightMM, ... }, 0.1 mm integer units, +y UP — the same space decodeDST
// outputs, which is what lets generation reuse the imported-design path).
// `warnings` is the last job's pipeline warnings, kept so the review panel
// can still explain the result after a reload. `blockColors` overrides the
// service palette per color block, same shape as a design element's.
//
// Shape-layers (contract v1) — the same hybrid-persistence decision extended,
// not relitigated: the element also stores everything the Layers list needs
// to render and edit OFFLINE, after a reload, with no service running:
//   `review`          — slimmed per-shape payload from the last job
//                       ({ brandId, shapes: [{ id, rgb, tier, layer,
//                       sewIndex, ... }] }, see digitizer.js reviewFromJob).
//   `shapeOverrides`  — keyed by shape_id; PipelineConfig.shape_overrides
//                       field names verbatim (thread_index, fill_angle_deg,
//                       tier, border, layer) plus an app-only `rgb` for the
//                       swatch, stripped before the wire.
//   `deletedShapeIds` — shapes the user removed in review; they stay in the
//                       stored review so the list can strike them through.
//   `appliedEdits`    — canonical key of the edits the CURRENT result was
//                       digitized with (digitizer.js editsKey), so the panel
//                       knows honestly whether edits are still pending.
export function defaultDigitizedElement(id) {
  return {
    id,
    type: "digitized",
    name: "",
    sourcePng: null,
    params: { ...DEFAULT_DIGITIZE_PARAMS },
    result: null,
    warnings: [],
    blockColors: {},
    review: null,
    shapeOverrides: {},
    deletedShapeIds: [],
    appliedEdits: null,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
    rotationDeg: 0,
  };
}

export function defaultProject() {
  return {
    version: 2,
    garmentId: "left_chest",
    selectedId: "e1",
    // Multi-select (Ctrl+click): the FULL selection. Invariants, maintained
    // by every selection-touching function here: never empty, and
    // selectedId (the "primary" — the element the single-element editor
    // panels bind to) is always a member. Single selection is the
    // one-element array; selectedId alone remains authoritative for every
    // pre-multi-select consumer, which is why it stays a plain string.
    selectedIds: ["e1"],
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
    type === "digitized" ? defaultDigitizedElement :
    defaultTextElement;
  let el = factory(id);
  const n = project.elements.length;
  if (n > 0) {
    // Imported designs keep sizeMm null (= the file's native stitch size,
    // hoop-clamped) — seeding a resize would silently rescale pre-digitized
    // stitches before the user ever sees them at true size. Digitized
    // elements too: their native size IS params.target_width_mm, the size
    // the stitches were generated for.
    el = type === "design" || type === "digitized"
      ? { ...el, offsetYMm: -10 * n }
      : { ...el, sizeMm: Math.round(0.4 * hoopWmm), offsetYMm: -10 * n };
  }
  return { ...project, elements: [...project.elements, el], selectedId: id, selectedIds: [id] };
}

// Removes an element by id. A project must always keep at least one
// element, so removing the last remaining element is a no-op. If the
// removed element was selected, selection falls back to the first
// remaining element; it's also dropped from the multi-selection (which
// falls back the same way if that empties it).
export function removeElement(project, id) {
  if (project.elements.length <= 1) return project;
  const elements = project.elements.filter((el) => el.id !== id);
  if (elements.length === project.elements.length) return project; // id not found
  const selectedId = project.selectedId === id ? elements[0].id : project.selectedId;
  let selectedIds = selectedIdsOf(project).filter((sid) => sid !== id);
  if (!selectedIds.length) selectedIds = [selectedId];
  if (!selectedIds.includes(selectedId)) selectedIds = [...selectedIds, selectedId];
  return { ...project, elements, selectedId, selectedIds };
}

// The full selection, tolerating projects saved before selectedIds existed
// (loaded snapshots, undo history from an old session): falls back to the
// single selectedId.
export function selectedIdsOf(project) {
  const ids = project.selectedIds;
  if (Array.isArray(ids) && ids.length) return ids;
  return project.selectedId ? [project.selectedId] : [];
}

// Plain click: collapse the selection to just this element.
export function selectElement(project, id) {
  return { ...project, selectedId: id, selectedIds: [id] };
}

// Ctrl/Cmd+click: toggle this element in the multi-selection. Adding makes
// it the primary (selectedId — matching "last clicked wins" in every design
// tool); removing the primary promotes the last remaining member. Removing
// the only member is a no-op — a selection is never empty.
export function toggleSelectElement(project, id) {
  const ids = selectedIdsOf(project);
  if (ids.includes(id)) {
    if (ids.length <= 1) return project;
    const selectedIds = ids.filter((sid) => sid !== id);
    const selectedId = project.selectedId === id ? selectedIds[selectedIds.length - 1] : project.selectedId;
    return { ...project, selectedId, selectedIds };
  }
  return { ...project, selectedId: id, selectedIds: [...ids, id] };
}

// Patches a single element by id, leaving all other elements untouched.
export function updateElement(project, id, patch) {
  const elements = project.elements.map((el) => (el.id === id ? { ...el, ...patch } : el));
  return { ...project, elements };
}

// Bulk patch (multi-select group move / bulk-edit): one immutable pass,
// each listed id merged with ITS OWN patch — { id: patch, ... }. Ids not in
// the map pass through untouched.
export function updateElements(project, patchById) {
  const elements = project.elements.map((el) => (patchById[el.id] ? { ...el, ...patchById[el.id] } : el));
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
    // Digitized elements get the same additive treatment the project's
    // top-level fields get above: spread over the factory defaults so a
    // project saved before a digitized field existed (or with an older
    // params set) loads with today's defaults filled in, never undefined.
    // Other element types pass through untouched — identical to how every
    // pre-digitize project has always loaded.
    merged.elements = merged.elements.map((el) => {
      if (!el || el.type !== "digitized") return el;
      const d = defaultDigitizedElement(el.id);
      return { ...d, ...el, params: { ...d.params, ...(el.params || {}) } };
    });
    // selectedIds invariants for pre-multi-select saves (and corrupt input):
    // members must be real element ids, the array must be non-empty, and
    // selectedId must be a member. Anything off -> collapse to [selectedId]
    // (the exact selection the project had before selectedIds existed).
    const known = new Set(merged.elements.map((el) => el.id));
    const ids = Array.isArray(merged.selectedIds) ? merged.selectedIds.filter((id) => known.has(id)) : [];
    merged.selectedIds =
      Array.isArray(input.selectedIds) && ids.length && ids.includes(merged.selectedId)
        ? ids
        : [merged.selectedId];
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
