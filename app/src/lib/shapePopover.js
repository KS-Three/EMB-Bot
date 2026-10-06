// The click-to-edit popover's decision table (2026-09-29 spec §5).
//
// Two side panels already know how to edit a shape: DigitizePanel's Layers
// rows (auto-digitized shapes, via shapeOverrides) and ManualPanel's assign
// box (hand-drawn shapes, via element.shapes). This module is the third way
// in — the popover the field opens where the shape IS — and its one job is to
// say the same things and write the same fields, so nothing downstream can
// tell which surface an edit came from. Pure: no DOM, no Svelte, no fetch
// (the one async dependency, the thread chart, is injected).
import { loadPalette, nearestInList } from "./threads.js";
import { resolveCutOuts, manualShapeName, withCutOut } from "./manualShapes.js";

const LANES = new Set(["digitized", "manual", "shape"]);

export function laneOf(element) {
  return element && LANES.has(element.type) ? element.type : null;
}

// ---- option lists: the Layers row's own words -------------------------------
// Mirror DigitizePanel.svelte's <select>s exactly; a label that differs
// between the two surfaces is a bug, not a style choice.
export const DIGITIZED_TIERS = [
  { value: "auto", label: "Auto" },
  { value: "satin", label: "Satin" },
  { value: "fill", label: "Fill" },
  { value: "run", label: "Run" },
  { value: "sketch", label: "Sketch" },
  { value: "streamline", label: "Streamline" },
  { value: "crosshatch", label: "Cross-hatch" },
  { value: "wave", label: "Wave" },
  { value: "chevron", label: "Chevron" },
  { value: "brick", label: "Brick" },
];

export const SHAPE_ANGLES = [
  { value: "auto", label: "Auto angle" },
  { value: "0", label: "0°" },
  { value: "30", label: "30°" },
  { value: "45", label: "45°" },
  { value: "60", label: "60°" },
  { value: "90", label: "90°" },
  { value: "135", label: "135°" },
];

export const SHAPE_UNDERLAYS = [
  { value: "auto", label: "Auto underlay" },
  { value: "none", label: "None" },
  { value: "edge_run", label: "Edge run" },
  { value: "center_run", label: "Center run" },
  { value: "edge_lattice", label: "Edge + lattice" },
  { value: "edge_zigzag", label: "Edge + zigzag" },
  { value: "double_lattice", label: "Double lattice" },
  { value: "zigzag", label: "Zigzag" },
  { value: "cross_tatami", label: "Crossing pass (pro)" },
];

// The design-level border's name in the "Design (…)" option — DigitizePanel's
// borderLabel: null is the automatic default and has no bare word of its own.
function borderLabel(v) {
  return v == null ? "automatic" : v;
}

export function BORDER_OPTIONS(designBorder) {
  return [
    { value: "default", label: "Design (" + borderLabel(designBorder) + ")" },
    { value: "off", label: "No border" },
    { value: "auto", label: "Auto border" },
    { value: "bean", label: "Bean border" },
  ];
}

const MANUAL_TIERS = [{ value: "fill", label: "Fill" }, { value: "satin", label: "Satin" }];

export const SATIN_CUTOUT_NOTE = "Sews as fill — satin cannot go round a cut-out.";

// ---- names ------------------------------------------------------------------
// The manual lane's name is manualShapeName (shared with ManualPanel); the
// digitized and preset names are reproduced here so the popover's heading
// reads like the row it stands in for.
function digitizedName(row) {
  const parts = [row.threadNumber ? "Thread #" + row.threadNumber : "Shape"];
  const a = row.areaMm2;
  if (a != null) parts.push((a >= 100 ? Math.round(a) : Number(a).toFixed(1)) + " mm²");
  return parts.join(" · ");
}
function presetName(element) {
  const k = String(element.kind || "shape");
  return k.charAt(0).toUpperCase() + k.slice(1);
}

// ---- the model --------------------------------------------------------------
export function popoverModel({ element, shapeId }) {
  const lane = laneOf(element);
  if (!lane) return null;

  if (lane === "manual") {
    const shape = (element.shapes || []).find((s) => s && s.id === shapeId);
    if (!shape) return null;
    const cut = resolveCutOuts(element.shapes);
    const name = manualShapeName(shape, cut);
    const tail = [
      { key: "editPoints", kind: "action", label: "Edit points" },
      { key: "delete", kind: "action", label: "Delete shape", danger: true },
    ];
    if (shape.cutOut) {
      const parent = cut.parentOf[shape.id];
      const toggle = { key: "cutOut", kind: "toggle", label: "Cut out", value: true };
      if (parent != null) { toggle.note = `Cuts Shape ${String(parent).replace(/^s/, "")}.`; toggle.warn = false; }
      else { toggle.note = cut.reasonOf[shape.id]; toggle.warn = true; }
      return { lane, shapeId, name, rows: [toggle, ...tail] };
    }
    const holed = (cut.holesOf[shape.id] || []).length > 0;
    const stored = shape.stitchType === "satin" ? "satin" : "fill";
    const typeRow = { key: "stitchType", kind: "choice", label: "Stitch type", value: holed ? "fill" : stored, options: MANUAL_TIERS };
    if (holed && stored === "satin") typeRow.note = SATIN_CUTOUT_NOTE;
    return {
      lane, shapeId, name,
      rows: [
        { key: "color", kind: "thread", rgb: shape.colorRgb },
        typeRow,
        { key: "angle", kind: "number", label: "Fill angle", value: shape.angleDeg == null ? null : shape.angleDeg, hint: "° (blank = auto)" },
        { key: "cutOut", kind: "toggle", label: "Cut out", value: false },
        ...tail,
      ],
    };
  }

  if (lane === "shape") {
    return { lane, shapeId, name: presetName(element), rows: [{ key: "color", kind: "thread", rgb: element.colorRgb }] };
  }

  // digitized
  const rows = (element.review && element.review.shapes) || [];
  const row = rows.find((r) => r && r.id === shapeId);
  if (!row) return null;
  if ((element.deletedShapeIds || []).includes(shapeId)) return null;
  const entry = (element.shapeOverrides || {})[shapeId] || {};
  const effectiveTier = entry.tier && entry.tier !== "auto" ? entry.tier : row.tier;
  const tierOptions = DIGITIZED_TIERS.map((t) =>
    t.value === "auto" ? { value: "auto", label: "Auto" + (row.tier ? " (" + row.tier + ")" : "") } : t);
  const out = [
    { key: "color", kind: "thread", rgb: Array.isArray(entry.rgb) ? entry.rgb : row.rgb },
    { key: "stitchType", kind: "choice", label: "Stitch type", value: entry.tier || "auto", options: tierOptions },
  ];
  if (effectiveTier === "fill") {
    out.push({ key: "angle", kind: "choice", label: "Fill angle", value: entry.fill_angle_deg == null ? "auto" : String(entry.fill_angle_deg), options: SHAPE_ANGLES });
    out.push({ key: "underlay", kind: "choice", label: "Underlay style", value: entry.underlay_style == null ? "auto" : entry.underlay_style, options: SHAPE_UNDERLAYS });
  }
  out.push({ key: "border", kind: "choice", label: "Border", value: entry.border == null ? "default" : entry.border, options: BORDER_OPTIONS(element.params ? element.params.border : null) });
  out.push({ key: "editPoints", kind: "action", label: "Edit points" });
  out.push({ key: "delete", kind: "action", label: "Delete shape", danger: true });
  return { lane, shapeId, name: digitizedName(row), rows: out };
}

// ---- patches ----------------------------------------------------------------
// DigitizePanel.setOverride, reproduced: merge fields into the entry, drop a
// null field (and tier "auto"), drop an emptied entry.
function overridePatch(element, shapeId, fields) {
  const cur = { ...(element.shapeOverrides || {}) };
  const entry = { ...(cur[shapeId] || {}), ...fields };
  for (const k of Object.keys(entry)) {
    if (entry[k] == null || (k === "tier" && entry[k] === "auto")) delete entry[k];
  }
  if (Object.keys(entry).length) cur[shapeId] = entry;
  else delete cur[shapeId];
  return { shapeOverrides: cur };
}

// ManualPanel.updateShape, reproduced: rewrite one shape, keep the rest by reference.
function manualShapePatch(element, shapeId, fields) {
  return { shapes: (element.shapes || []).map((s) => (s && s.id === shapeId ? { ...s, ...fields } : s)) };
}

function parseAngle(v) {
  if (v === "" || v == null) return null;
  const n = typeof v === "number" ? v : parseFloat(String(v).trim());
  return Number.isFinite(n) ? n : null;
}

// -> the `elupdate` patch for one edit, or null when the key is not a
// synchronous patch on this lane (an action, or a colour on the digitized
// lane — see recolorPatch).
export function popoverPatch({ element, shapeId }, key, value) {
  const lane = laneOf(element);
  if (!lane) return null;
  if (lane === "manual") {
    switch (key) {
      case "stitchType": return manualShapePatch(element, shapeId, { stitchType: value === "satin" ? "satin" : "fill" });
      case "angle": return manualShapePatch(element, shapeId, { angleDeg: parseAngle(value) });
      case "color": return manualShapePatch(element, shapeId, { colorRgb: [...value] });
      case "cutOut": return { shapes: (element.shapes || []).map((s) => (s && s.id === shapeId ? withCutOut(s, !!value) : s)) };
      case "delete": return { shapes: (element.shapes || []).filter((s) => !s || s.id !== shapeId) };
      default: return null;
    }
  }
  if (lane === "shape") {
    return key === "color" ? { colorRgb: [...value] } : null;
  }
  switch (key) {
    case "stitchType": return overridePatch(element, shapeId, { tier: value === "auto" ? null : value });
    case "angle": return overridePatch(element, shapeId, { fill_angle_deg: value === "auto" ? null : parseFloat(value) });
    case "underlay": return overridePatch(element, shapeId, { underlay_style: value === "auto" ? null : value });
    case "border": return overridePatch(element, shapeId, { border: value === "default" ? null : value });
    case "delete": {
      const cur = element.deletedShapeIds || [];
      return cur.includes(shapeId) ? null : { deletedShapeIds: [...cur, shapeId] };
    }
    default: return null;
  }
}

// Recolour on the digitized lane: the engine wants an index into the job's
// thread chart, not an rgb — DigitizePanel.recolorShape's nearest-in-brand
// lookup, reproduced. `deps` is for tests; the app passes nothing. `element`
// may be a getter so the patch is built against the element as it is when the
// chart has loaded, not as it was when the click happened — the caller
// (EmbroideryField) passes `() => selectedElement()`.
export async function recolorPatch({ element, shapeId }, rgb, deps = {}) {
  const load = deps.loadPalette || loadPalette;
  const nearest = deps.nearestInList || nearestInList;
  // Resolve element up front for the brand read
  const el0 = typeof element === "function" ? element() : element;
  const brand = (el0.review && el0.review.brandId) || "isacord";
  try {
    const pal = await load(brand);
    if (!pal || pal.id !== brand) return null;
    // Re-resolve element after the await so the patch is built against
    // the element as it is when the chart has loaded, not as it was when
    // the click happened
    const el = typeof element === "function" ? element() : element;
    const n = nearest(pal.threads, rgb);
    if (!n) return null;
    return overridePatch(el, shapeId, { thread_index: n.index, rgb: [...n.rgb] });
  } catch (e) {
    return null;
  }
}
