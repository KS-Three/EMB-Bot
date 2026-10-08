// Save/load round-trip across EVERY persistence path the Studio has, with one
// project that carries every element type and every field a customer can
// set. The per-module specs (projects / projectFile / project) each pin their
// own slice; this file pins the SEAM: what goes in is what comes out, whichever
// door it leaves by (registry record, .embproj file, duplicate, import).
//
// Undo history is NOT persisted -- history.js is in-memory per project and
// App resets it on every project switch. The last block pins that on purpose,
// so a future "persist history" change has to update a test, not drift in.

import { test, expect, beforeEach, describe } from "vitest";
import {
  createProject,
  loadProject,
  saveProject,
  duplicateProject,
  importProject,
} from "./projects.js";
import { buildProjectFile, parseProjectFile } from "./projectFile.js";
import { serialize, deserialize } from "./save.js";
import { createHistory } from "./history.js";
import {
  defaultProject,
  defaultTextElement,
  defaultImageElement,
  defaultDesignElement,
  defaultDigitizedElement,
  defaultManualElement,
  defaultManualShape,
  defaultShapeElement,
  addElement,
  updateElement,
  removeElement,
  selectElement,
  toggleSelectElement,
  migrateProject,
} from "./project.js";

function memoryStorage() {
  const store = new Map();
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => void store.set(k, String(v)),
    removeItem: (k) => void store.delete(k),
    clear: () => store.clear(),
    _store: store,
  };
}

beforeEach(() => {
  globalThis.localStorage = memoryStorage();
});

// A realistic digitize result: the engine's output shape is rich, so use
// nested arrays/objects/floats/negatives/unicode rather than a stub.
const RESULT = {
  width_mm: 81.25,
  height_mm: 16.5,
  stitches: [
    [0, 0, 0],
    [1.25, -0.5, 0],
    [-3.125, 7.0625, 1],
  ],
  colors: [
    { rgb: [200, 30, 30], name: "Café red", stitches: 1234 },
    { rgb: [0, 0, 0], name: "Black", stitches: 0 },
  ],
  nested: { a: [{ b: [1e-7, 123456789.123] }] },
};

function fullProject() {
  const text = {
    ...defaultTextElement("e1"),
    text: "Fritsch's «Stitches» ✓ 日本",
    fontKey: "medium_font",
    colorRgb: [10, 20, 30],
    colorRanges: [
      { startIdx: 0, endIdx: 3, colorRgb: [200, 30, 30] },
      { startIdx: 4, endIdx: 6, colorRgb: [30, 30, 200] },
    ],
    weightPreset: "bold",
    slantDeg: -12,
    letterSpacingMm: 0.75,
    arcDeg: 45,
    rotationDeg: 15,
    align: "left",
    underlay: false,
    sizeMm: 88.5,
    offsetXMm: -3.25,
    offsetYMm: 4.5,
  };
  const image = {
    ...defaultImageElement("e2"),
    name: "offline logo.png",
    sourcePng: "data:image/png;base64,iVBORw0KGgo=",
    nColors: 6,
    removeBg: false,
    threadRgb: { 0: [1, 2, 3], 2: [250, 250, 250] },
    underlay: false,
    sizeMm: 40,
    offsetXMm: 1,
    offsetYMm: -2,
    _hasImage: true,
  };
  const design = {
    ...defaultDesignElement("e3"),
    name: "pre-digitized.dst",
    dstBase64: "AAECAwQFBgcICQ==",
    blockColors: { 0: [255, 0, 0], 1: [0, 255, 0] },
    sizeMm: 60,
    offsetXMm: 5,
    offsetYMm: 6,
  };
  const digitized = {
    ...defaultDigitizedElement("e4"),
    name: "logo.png",
    sourcePng: "data:image/png;base64,AAAA",
    sourceFile: { key: "sha256-abc", type: "image/png", size: 1234, width: 800, height: 600 },
    crop: { x0: 0.1, y0: 0.2, x1: 0.9, y1: 0.8 },
    params: { ...defaultDigitizedElement("x").params, fill_angle_deg: 33 },
    result: RESULT,
    warnings: ["thin shape dropped", "ünïcode warning"],
    blockColors: { 0: [9, 9, 9] },
    review: { accepted: true, notes: ["ok"] },
    shapeOverrides: { s1: { stitched: false }, s2: { angleOverride: 45, colorRgb: [1, 1, 1] } },
    deletedShapeIds: ["s7", "s9"],
    appliedEdits: { s1: { hole: true } },
    appliedConfig: '{"p":1}',
    preflight: { grade: "B", issues: [] },
    stats: { stitch_count: 2253, color_changes: 1, trims: 3 },
    priorRun: { stitch_count: 3000, color_changes: 2, trims: 4, score: 71, grade: "C" },
    textConversions: { s3: "e1" },
    sizeMm: 81,
    offsetXMm: 7,
    offsetYMm: -7,
    rotationDeg: 90,
  };
  const manual = {
    ...defaultManualElement("e5"),
    shapes: [
      {
        ...defaultManualShape("m1"),
        points: [
          { x: 10, y: 10 },
          { x: 100.5, y: 10 },
          { x: 100.5, y: 80.25 },
        ],
        curves: { 0: { x: 50, y: -5 }, 2: { x: 60, y: 60 } },
        stitchType: "satin",
        colorRgb: [90, 80, 70],
        angleDeg: 30,
      },
      { ...defaultManualShape("m2"), cutOut: true, stitchType: "fill", angleDeg: null },
    ],
    underlay: false,
    sizeMm: 25,
    offsetXMm: 2,
    offsetYMm: 3,
  };
  const shape = {
    ...defaultShapeElement("e6"),
    kind: "star",
    params: { points: 7, innerRatio: 0.42 },
    colorRgb: [255, 215, 0],
    underlay: false,
    sizeMm: 33,
    offsetXMm: -8,
    offsetYMm: 9,
  };
  return {
    ...defaultProject(),
    garmentId: "baseball_cap",
    selectedId: "e4",
    selectedIds: ["e4", "e1", "e6"],
    elements: [text, image, design, digitized, manual, shape],
    fabricRgb: [12, 34, 56],
    hoopId: "5x7",
    fabricProfile: { satinWidthDeltaMm: 0.1, pullDeltaMm: -0.05, densityScale: 1.1 },
  };
}

const clone = (o) => JSON.parse(JSON.stringify(o));

describe("every element type survives every door", () => {
  test("fixture really holds all six element types", () => {
    expect(fullProject().elements.map((e) => e.type)).toEqual([
      "text", "image", "design", "digitized", "manual", "shape",
    ]);
  });

  test("registry: saveProject -> loadProject is lossless", () => {
    const { id } = createProject("Round trip");
    const p = fullProject();
    expect(saveProject(id, p)).toBe(true);
    expect(loadProject(id)).toEqual(p);
  });

  test("legacy blob path: serialize -> deserialize is lossless", () => {
    const p = fullProject();
    expect(deserialize(serialize(p))).toEqual(p);
  });

  test(".embproj: buildProjectFile -> parseProjectFile is lossless, name too", () => {
    const p = fullProject();
    const out = parseProjectFile(buildProjectFile(p, "Hat #2"));
    expect(out.name).toBe("Hat #2");
    expect(out.project).toEqual(p);
  });

  test("file -> importProject -> loadProject is lossless", () => {
    const p = fullProject();
    const parsed = parseProjectFile(buildProjectFile(p, "Hat"));
    const { id } = importProject(parsed.project, parsed.name);
    expect(loadProject(id)).toEqual(p);
  });

  test("duplicateProject copies every element type unchanged", () => {
    const { id } = createProject("Original");
    const p = fullProject();
    saveProject(id, p);
    const dup = duplicateProject(id);
    expect(loadProject(dup.id)).toEqual(p);
  });

  test("a second save/load/save/load cycle is a fixed point (no drift)", () => {
    const { id } = createProject("Drift");
    saveProject(id, fullProject());
    const once = loadProject(id);
    saveProject(id, once);
    const twice = loadProject(id);
    expect(twice).toEqual(once);
    expect(serialize(twice)).toBe(serialize(once));
  });

  test("migrateProject is idempotent on a full project", () => {
    const p = fullProject();
    expect(migrateProject(migrateProject(p))).toEqual(p);
  });
});

describe("per-field fidelity", () => {
  const roundTrip = (p) => {
    const { id } = createProject("rt");
    saveProject(id, p);
    return loadProject(id);
  };

  test("text: colour ranges, spacing, arc, rotation, unicode text", () => {
    const t = roundTrip(fullProject()).elements[0];
    expect(t.colorRanges).toEqual(fullProject().elements[0].colorRanges);
    expect(t.text).toBe("Fritsch's «Stitches» ✓ 日本");
    expect([t.slantDeg, t.letterSpacingMm, t.arcDeg, t.rotationDeg]).toEqual([-12, 0.75, 45, 15]);
    expect(t.underlay).toBe(false);
  });

  test("image: per-colour thread overrides keep their numeric-string keys and pixels", () => {
    const im = roundTrip(fullProject()).elements[1];
    expect(im.threadRgb).toEqual({ 0: [1, 2, 3], 2: [250, 250, 250] });
    expect(im.sourcePng).toBe("data:image/png;base64,iVBORw0KGgo=");
    expect(im.removeBg).toBe(false);
  });

  test("design: dst bytes and per-block thread colours", () => {
    const d = roundTrip(fullProject()).elements[2];
    expect(d.dstBase64).toBe("AAECAwQFBgcICQ==");
    expect(d.blockColors).toEqual({ 0: [255, 0, 0], 1: [0, 255, 0] });
  });

  test("digitized: baked result, edits, overrides, crop, prior run all come back", () => {
    const d = roundTrip(fullProject()).elements[3];
    expect(d.result).toEqual(RESULT);
    expect(d.shapeOverrides).toEqual({ s1: { stitched: false }, s2: { angleOverride: 45, colorRgb: [1, 1, 1] } });
    expect(d.deletedShapeIds).toEqual(["s7", "s9"]);
    expect(d.appliedEdits).toEqual({ s1: { hole: true } });
    expect(d.appliedConfig).toBe('{"p":1}');
    expect(d.crop).toEqual({ x0: 0.1, y0: 0.2, x1: 0.9, y1: 0.8 });
    expect(d.priorRun.grade).toBe("C");
    expect(d.sourceFile.key).toBe("sha256-abc");
    expect(d.params.fill_angle_deg).toBe(33);
    expect(d.textConversions).toEqual({ s3: "e1" });
  });

  test("manual: sparse curves map, cutOut flag, null angle, point order", () => {
    const m = roundTrip(fullProject()).elements[4];
    expect(m.shapes[0].curves).toEqual({ 0: { x: 50, y: -5 }, 2: { x: 60, y: 60 } });
    expect(m.shapes[0].points).toHaveLength(3);
    expect(m.shapes[1].cutOut).toBe(true);
    expect(m.shapes[1].angleDeg).toBeNull();
  });

  test("shape: kind and parametric bag", () => {
    const s = roundTrip(fullProject()).elements[5];
    expect(s.kind).toBe("star");
    expect(s.params).toEqual({ points: 7, innerRatio: 0.42 });
  });

  test("project level: garment, fabric colour, hoop pick, calibration profile", () => {
    const p = roundTrip(fullProject());
    expect(p.garmentId).toBe("baseball_cap");
    expect(p.fabricRgb).toEqual([12, 34, 56]);
    expect(p.hoopId).toBe("5x7");
    expect(p.fabricProfile).toEqual({ satinWidthDeltaMm: 0.1, pullDeltaMm: -0.05, densityScale: 1.1 });
  });

  test("multi-selection and primary survive; element order is preserved", () => {
    const p = roundTrip(fullProject());
    expect(p.selectedId).toBe("e4");
    expect(p.selectedIds).toEqual(["e4", "e1", "e6"]);
    expect(p.elements.map((e) => e.id)).toEqual(["e1", "e2", "e3", "e4", "e5", "e6"]);
  });

  test("a project built through the real edit ops (not a literal) round-trips", () => {
    let p = defaultProject();
    for (const t of ["text", "image", "design", "digitized", "manual", "shape"]) {
      p = addElement(p, t, 100);
    }
    p = updateElement(p, "e1", { text: "Hi", colorRgb: [1, 2, 3] });
    p = toggleSelectElement(selectElement(p, "e3"), "e5");
    p = removeElement(p, "e2");
    const { id } = createProject("ops");
    saveProject(id, p);
    expect(loadProject(id)).toEqual(p);
  });
});

describe("what JSON cannot carry (pinned so a change is deliberate)", () => {
  test("non-finite numbers become null, not NaN -- load never sees NaN", () => {
    const p = updateElement(defaultProject(), "e1", { sizeMm: NaN, offsetXMm: Infinity });
    const { id } = createProject("nan");
    saveProject(id, p);
    const t = loadProject(id).elements[0];
    expect(t.sizeMm).toBeNull(); // null already means "auto size"
    expect(t.offsetXMm).toBeNull();
  });

  test("a persisted _hasImage flag comes back true from storage (App strips it at boot)", () => {
    const { id } = createProject("flag");
    saveProject(id, fullProject());
    expect(loadProject(id).elements[1]._hasImage).toBe(true);
  });

  test("loading is read-only: it never writes back to storage", () => {
    const { id } = createProject("ro");
    saveProject(id, fullProject());
    const before = serialize(JSON.parse(localStorage.getItem("embstudio:p:" + id)));
    loadProject(id);
    expect(localStorage.getItem("embstudio:p:" + id)).toBe(before);
  });
});

describe("undo history is session-only", () => {
  test("a saved record carries no history, and a loaded project starts a fresh stack", () => {
    const { id } = createProject("hist");
    const h = createHistory(defaultProject(), { coalesceMs: 0 });
    let p = defaultProject();
    p = updateElement(p, "e1", { text: "A" });
    h.record(p, 1);
    p = updateElement(p, "e1", { text: "AB" });
    h.record(p, 2);
    expect(h.canUndo()).toBe(true);

    saveProject(id, p);
    const raw = JSON.parse(localStorage.getItem("embstudio:p:" + id));
    expect(Object.keys(raw).sort()).toEqual(Object.keys(p).sort());
    expect(JSON.stringify(raw)).not.toMatch(/undo|redo|history/i);

    // App.enterProject: history.reset(loaded) -- nothing to undo to.
    const loaded = loadProject(id);
    h.reset(loaded);
    expect(h.canUndo()).toBe(false);
    expect(h.canRedo()).toBe(false);
    expect(loaded.elements[0].text).toBe("AB");
  });

  test(".embproj carries no history either", () => {
    const file = JSON.parse(buildProjectFile(fullProject(), "x"));
    expect(Object.keys(file).sort()).toEqual(["format", "name", "project", "savedAt", "version"]);
  });
});
