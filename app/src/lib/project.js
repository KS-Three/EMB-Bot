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
  // NULL, NOT "off" — the same absent-means-auto sentinel `fill_angle_deg`
  // above uses, and for a sharper reason. The service resolves
  // `cfg.border or ("significant" if photo else "off")`, so ANY string the
  // Studio sends short-circuits that per-class default. Shipping "off" here
  // meant every photo digitized from the Studio sent a truthy "off" and could
  // never reach `significant` — the one border mode DOCTRINE actually
  // blesses (borders 4 shapes of 35 for +4% on owl_kent, where blanket
  // "auto" spends +60% to trace the photo's own pixel staircase and makes it
  // WORSE). The measured-good option was unreachable and the measured-bad one
  // was a click away.
  //
  // null means "let the class decide" and is omitted from the wire entirely.
  // An explicit "off" is still a real choice and is still sent — the two have
  // to stay distinguishable, which a string default cannot do.
  border: null,
  // The design-silhouette edge cap (PipelineConfig.edge_cap) — "none",
  // "bean" or "satin". Distinct from `border` above: that outlines each
  // SHAPE, this closes the outer edge of the whole design, which belongs to
  // no single shape and which no per-shape border can reach. From Kent's
  // first sew-out, where every tatami row in the background ended in open
  // air. "none" matches the service default; bean costs about +12.6% of the
  // design's stitches and satin about +15.3% (measured on that icon).
  edge_cap: "none",
  // Off by default, matching the service's own `detail_layer` default — it
  // costs real stitches (+39% on the owl photo below) and buys nothing on
  // flat logo art, which is the common case. Measured 2026-08-12 on a snowy
  // owl photo at 12 colors: without it the bird stitches as one flat pale
  // mass, because a photo's structure lives in edges the region fill has
  // already averaged away; with it the silhouette, facial disc, eye rims and
  // barred chest feathers all come back (7,725 -> 10,727 stitches).
  detail_layer: false,
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
//                       tier, border, layer, stitched, underlay_style) plus
//                       an app-only `rgb` for the swatch, stripped before
//                       the wire.
//                       `stitched: true` restores a BACKGROUND_ENCLOSED
//                       region the digitizer excluded by default (contract
//                       v1.1) — distinct from `deletedShapeIds`, which is a
//                       user hiding a shape the digitizer WOULD sew.
//   `deletedShapeIds` — shapes the user removed in review; they stay in the
//                       stored review so the list can strike them through.
//   `appliedEdits`    — canonical key of the edits the CURRENT result was
//                       digitized with (digitizer.js editsKey), so the panel
//                       knows honestly whether edits are still pending.
//   `preflight`       — the last job's `{ score, grade, findings, metrics }`
//                       report verbatim (server-computed, read-only, no
//                       override key — same "echoed back, not edited"
//                       treatment as the text-cluster fields above), or null
//                       when the job predates this field or the caller
//                       turned preflight off. Used by the Sequencer view's
//                       trims-per-1000 header, and by the review step's
//                       quality report (ui/QualityReport.svelte).
//   `stats`           — the job's own `{ stitch_count, color_changes, trims,
//                       jumps, thread_m_total, thread_m_by_color, size_mm }`
//                       verbatim, or null on an older stored job. Same
//                       read-only, echoed-back treatment as `preflight`;
//                       thread length lives ONLY here, never in preflight's
//                       metrics, which is why the review step reads both.
//   `priorRun`        — the five headline figures from the run BEFORE the
//                       current one, or null on a first digitize. Written by
//                       DigitizePanel's runDigitize at the same moment it
//                       overwrites `stats`/`preflight`, which is the only
//                       moment the old values still exist.
export function defaultDigitizedElement(id) {
  return {
    id,
    type: "digitized",
    name: "",
    sourcePng: null,
    params: { ...DEFAULT_DIGITIZE_PARAMS },
    // A sibling of params, not a member of it (spec 2026-08-18 decision 4):
    // this names a fact about the SOURCE ART ("this is a photo"), not a
    // PipelineConfig field forwarded verbatim, so buildDigitizeConfig reads
    // it straight off the element rather than through the params spread —
    // see that function's own comment for how it turns into forced_class.
    isPhoto: false,
    result: null,
    warnings: [],
    blockColors: {},
    review: null,
    shapeOverrides: {},
    deletedShapeIds: [],
    appliedEdits: null,
    preflight: null,
    stats: null,
    // The numbers the PREVIOUS digitize produced, captured the moment a new
    // result replaces it — so "Digitize again" can say what moved instead of
    // silently swapping the design out. Null until a second run exists; a
    // first digitize has nothing to be different from.
    //
    // A flat snapshot of five figures, deliberately, not a copy of the whole
    // `stats`/`preflight` pair: this rides in the saved project file, and the
    // point is a one-line comparison, not a second full report the reader has
    // to diff by eye. `{ stitch_count, color_changes, trims, score, grade }`.
    priorRun: null,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
    rotationDeg: 0,
  };
}

// A hand-drawn ("manual digitizing") element (MVP slice, no auto-analysis of
// any input image): the user draws straight-line polygon outlines directly
// on a canvas and assigns stitch properties by hand. `shapes` holds only
// COMPLETED shapes — the in-progress point list being drawn right now is
// ephemeral UI state owned by ManualPanel (same pattern ImagePanel's
// merge-selection uses: not part of the persisted element), so a page
// reload can lose an unfinished shape but never a finished one.
//
// Each shape: { id, points: [{x,y}, ...], curves: {[segmentIndex]: {x,y}},
// stitchType: "satin"|"fill", colorRgb: [r,g,b], angleDeg: number|null }.
// `points` live in a fixed authoring-canvas pixel space (see
// lib/manualShapes.js's CANVAS_W/H) — only the shapes' RELATIVE geometry
// matters, since generation fits the combined bbox to the garment/hoop same
// as every other content type. `curves` is a sparse map from segment index
// (the edge from points[i] to points[i+1]) to that segment's quadratic
// control point — see manualShapes.js's flattenShape for how a curved
// segment becomes real geometry; an empty/absent `curves` means every edge
// is a plain straight line, unchanged from before this field existed.
// stitchType is a required manual choice (never auto-classified — that's
// the whole point of this mode); angleDeg null = per-shape auto (PCA),
// matching the fill-angle-override convention Image mode's swatch bar and
// digitize.js's shape.angleOverride already use elsewhere.
export function defaultManualShape(id) {
  return {
    id,
    points: [],
    curves: {},
    stitchType: "fill",
    colorRgb: [20, 20, 20],
    angleDeg: null,
  };
}

export function defaultManualElement(id) {
  return {
    id,
    type: "manual",
    shapes: [],
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}

// A preset basic-shape element (launch-checklist item 4): one parametric
// shape — circle, rectangle, heart, or star — that digitizes through the
// SAME shapesToRegions -> buildQualityDesign lane manual draw uses. The
// element persists only the recipe (`kind` + `params`); the point ring is
// regenerated from it on every generate (lib/shapePresets.js), so there's no
// baked geometry to go stale when a param changes.
//
// `params` is the per-kind SHAPE parameter bag (rect heightMm/cornerRadiusMm,
// star points/innerRatio — see shapePresets.defaultShapeParams); size is NOT
// in it: sizeMm below is the shape's width in mm, the same field SizePanel
// and the canvas resize handles already edit for every element type. Unlike
// manual mode there is no stitchType — satin-vs-fill is deliberately left to
// the engine's classifier (generation passes stitchType "auto").
export function defaultShapeElement(id) {
  return {
    id,
    type: "shape",
    kind: "circle",
    params: {},
    colorRgb: [20, 20, 20],
    underlay: true,
    sizeMm: 50,
    offsetXMm: 0,
    offsetYMm: 0,
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
    // Project-level hoop pick (launch item 2 — home-machine hoop picker).
    // null = use the per-garment suggestion (the engine's suggestHoop rule);
    // a hoop preset id ("4x4", "5x7", "6x10", "8x8") = the user's manual
    // override. Resolution lives in lib/hoop.js's effectiveHoop(). Same
    // additive-migration story as fabricRgb: older saves simply spread-merge
    // over this default and load as "use the suggestion".
    hoopId: null,
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

// The ONE artwork lane decision (the PR #122 defect class: an entry point
// that picks a lane without asking is indistinguishable from a dead service).
// Every place that turns "user gave us artwork" into an element type must call
// this: service up -> "digitized" (the pipeline classifies and stitches it),
// down -> "image" (the browser engine's flatten-and-sew lane, no service
// needed). App.onAddElement and applyTemplate are the two callers today.
export function resolveArtworkType(digitizerHealth) {
  return digitizerHealth ? "digitized" : "image";
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
    type === "manual" ? defaultManualElement :
    type === "shape" ? defaultShapeElement :
    defaultTextElement;
  let el = factory(id);
  const n = project.elements.length;
  if (n > 0) {
    // Imported designs keep sizeMm null (= the file's native stitch size,
    // hoop-clamped) — seeding a resize would silently rescale pre-digitized
    // stitches before the user ever sees them at true size. Digitized
    // elements too: their native size IS params.target_width_mm, the size
    // the stitches were generated for. Shape elements keep their factory
    // sizeMm (an explicit, predictable "50 mm" beats a hoop-relative
    // stagger for a shape the user is about to type an exact size into).
    el = type === "design" || type === "digitized" || type === "shape"
      ? { ...el, offsetYMm: -10 * n }
      : { ...el, sizeMm: Math.round(0.4 * hoopWmm), offsetYMm: -10 * n };
  }
  return { ...project, elements: [...project.elements, el], selectedId: id, selectedIds: [id] };
}

// Adds a new "text" element SEEDED from a partial patch (`seed`) — a sibling
// to addElement, not a replacement: addElement's signature/behavior are left
// untouched because other callers depend on them. Used by the "convert text
// cluster to text element" action (DigitizePanel, Studio-side text-cluster
// detection feature): the seed carries the cluster's bbox-derived position/
// size, dominant color, and a baseline-derived rotation, PLUS explicit
// `text: ""` / `fontKey: null` overrides of defaultTextElement's own
// `fontKey: "medium_font"` default — deliberately empty/unset so the user
// picks a font and types the word themselves (FontSelect already renders a
// falsy/null fontKey as its "Choose a font" empty state; TextStep already
// renders an empty `text` as a normal empty textarea) — nothing is ever
// auto-filled that could be silently wrong.
//
// Same append-and-select-new-element behavior addElement already has,
// including the hoop-relative size/offset seeding for non-first elements —
// `seed` is merged AFTER that seeding, so any field the seed actually
// specifies (sizeMm, offsetXMm/offsetYMm, etc.) wins over the generic
// stagger; anything the seed omits keeps addElement's usual placement.
//
// Returns { project, id } rather than relying on the caller re-deriving the
// new element's id from project.selectedId (the convention addElement's
// existing callers use): the one caller of this function (App.svelte's
// text-conversion handler) needs the new id in the SAME synchronous step to
// patch a DIFFERENT element's shapeOverrides/textConversions, before that
// coordinated project value is ever assigned/rendered — reading it back off
// selectedId would work too (selection does move to the new element, same as
// addElement), but returning it explicitly avoids a second implicit
// assumption ("selectedId still means what I think it means") in a function
// that's already doing two things at once.
export function addSeededTextElement(project, seed, hoopWmm) {
  const id = nextElementId(project.elements);
  let el = defaultTextElement(id);
  const n = project.elements.length;
  if (n > 0) {
    el = { ...el, sizeMm: Math.round(0.4 * hoopWmm), offsetYMm: -10 * n };
  }
  el = { ...el, ...seed, id };
  const newProject = {
    ...project,
    elements: [...project.elements, el],
    selectedId: id,
    selectedIds: [id],
  };
  return { project: newProject, id };
}

// Removes an element by id. A project must always keep at least one
// element, so removing the last remaining element is a no-op. If the
// removed element was selected, selection falls back to the first
// remaining element; it's also dropped from the multi-selection (which
// falls back the same way if that empties it).
export function removeElement(project, id) {
  if (project.elements.length <= 1) return project;
  let elements = project.elements.filter((el) => el.id !== id);
  if (elements.length === project.elements.length) return project; // id not found

  // Prune conversion provenance that pointed at the element just removed.
  //
  // Element ids are RECYCLED: nextElementId is max+1 over the SURVIVING
  // elements, so deleting e2 hands "e2" straight back to the next element
  // added. A `textConversions` entry left naming the dead id would then name
  // an innocent NEW element, and DigitizePanel's cluster bar would still show
  // "Undo — remove text element" — which deletes that new element instead of
  // the one the user converted. Found by a sibling-pattern sweep 2026-08-26;
  // it is the same never-pruned-map-over-a-recycled-id shape as the shapeAlpha
  // bug fixed in PR #264, one level up.
  //
  // Pruning rather than making ids monotonic: a project-level counter would
  // change the persisted schema, need a migrateProject default for every
  // existing save, and break the literal-id expectations this file's own spec
  // asserts. Recycling is already a documented property the app compensates
  // for elsewhere; this keeps that contract instead of inverting it.
  //
  // Elements with no matching entry pass through BY REFERENCE, so keyed
  // {#each} blocks and identity-based memoization see no change.
  if (elements.some((el) => el.textConversions && Object.values(el.textConversions).includes(id))) {
    elements = elements.map((el) => {
      if (!el.textConversions) return el;
      const kept = Object.entries(el.textConversions).filter(([, v]) => v !== id);
      if (kept.length === Object.keys(el.textConversions).length) return el;
      return { ...el, textConversions: Object.fromEntries(kept) };
    });
  }
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
    // Manual elements get the same additive treatment: spread over the
    // factory defaults so a project saved before a manual field existed
    // loads with today's defaults filled in, and `shapes` always ends up a
    // real array even if storage returned something corrupt.
    merged.elements = merged.elements.map((el) => {
      if (!el || el.type !== "manual") return el;
      const d = defaultManualElement(el.id);
      return { ...d, ...el, shapes: Array.isArray(el.shapes) ? el.shapes : d.shapes };
    });
    // Shape elements: same additive treatment again — defaults filled in for
    // fields that postdate the save, and `params` guaranteed to be a real
    // object even if storage returned something corrupt (shapePresets'
    // resolvedShapeParams fills per-kind defaults from a sparse bag, so an
    // empty object is always safe here).
    merged.elements = merged.elements.map((el) => {
      if (!el || el.type !== "shape") return el;
      const d = defaultShapeElement(el.id);
      return { ...d, ...el, params: el.params && typeof el.params === "object" ? el.params : d.params };
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
