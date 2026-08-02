import { test, expect, beforeAll, vi } from "vitest";
import { createRequire } from "node:module";
import fixture from "./fixtures/digitized-asym.json";

// Engine load, same recipe as generate.spec.js (buildImportedDesign and the
// DST codec live on the EMB global).
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
});

// localStorage doesn't exist in the node test env; digitizer.js and
// threads.js both read it through try/catch, so a minimal stub is enough to
// exercise the brand-preference path.
function stubStorage(entries = {}) {
  const store = new Map(Object.entries(entries));
  globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
}

function digitizedElement(overrides = {}) {
  return {
    id: "e1", type: "digitized", name: "asym.png", sourcePng: null,
    params: { target_width_mm: 80, max_colors: 6, satin: true, fill_angle_deg: null, border: "off" },
    result: null, warnings: [], blockColors: {},
    sizeMm: null, offsetXMm: 0, offsetYMm: 0, rotationDeg: 0,
    ...overrides,
  };
}

const PROJECT = { version: 2, garmentId: "left_chest", selectedId: "e1", elements: [] };

// A 1x1 transparent PNG — a real, decodable base64 payload for the wire specs.
const TINY_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

// ---- the /digitize request shape (pinned against the service's tests) ------
//
// The other end of this seam is digitizer/tests/test_service.py: multipart
// fields "image" + "config", config keys drawn from PipelineConfig
// (digitizer_core/config.py) — anything else 400s as "unknown config
// field(s)". This list IS that dataclass (minus debug_dir/extra, which the
// service refuses). If a key ever leaves this set, the service rejects the
// request, so the two ends cannot drift silently — this spec makes the drift
// loud on the JS side too.
const PIPELINE_CONFIG_FIELDS = [
  "target_width_mm", "thread_brand", "max_colors", "seed", "merge_delta_e",
  "aa_iterations", "aa_phantom_edge_frac", "bg_tolerance_lab", "bg_margin_mm",
  "bg_intrusion_min_mm", "min_px_per_mm", "upscale_cap", "denoise",
  "min_detail_mm", "report_absorb_frac", "simplify_tol_mm", "garment_id",
  "fabric_id", "overlap_mm", "fill_row_mm", "fill_stitch_mm", "fill_angle_deg",
  "underlay_style", "underlay", "satin", "satin_max_width_mm", "border",
  "border_width_mm", "deleted_shape_ids", "shape_overrides",
];

test("buildDigitizeConfig sends the stored thread-brand preference and the project garment, in service field names", async () => {
  stubStorage({ "embstudio:threadPalette": "madeira-rayon" });
  const { buildDigitizeConfig } = await import("./digitizer.js");
  const cfg = buildDigitizeConfig(digitizedElement(), PROJECT);

  expect(cfg).toEqual({
    target_width_mm: 80,
    max_colors: 6,
    satin: true,
    border: "off",
    thread_brand: "madeira-rayon",
    garment_id: "left_chest",
  });
  for (const k of Object.keys(cfg)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
});

test("buildDigitizeConfig omits thread_brand for the generic Studio palette (service default applies), includes fill_angle_deg only when set", async () => {
  stubStorage({}); // no stored preference -> "studio"
  const { buildDigitizeConfig } = await import("./digitizer.js");

  const plain = buildDigitizeConfig(digitizedElement(), PROJECT);
  expect("thread_brand" in plain).toBe(false);
  expect("fill_angle_deg" in plain).toBe(false);

  const angled = buildDigitizeConfig(
    digitizedElement({ params: { target_width_mm: 60, max_colors: 4, satin: false, fill_angle_deg: 45, border: "bean" } }),
    PROJECT
  );
  expect(angled.fill_angle_deg).toBe(45);
  expect(angled.satin).toBe(false);
  expect(angled.border).toBe("bean");
  expect(angled.target_width_mm).toBe(60);
});

test("startDigitize POSTs multipart image+config to /digitize exactly as test_service.py's client does", async () => {
  stubStorage({ "embstudio:threadPalette": "isacord" });
  const { startDigitize, buildDigitizeConfig } = await import("./digitizer.js");

  const calls = [];
  const fetchFn = vi.fn(async (url, opts) => {
    calls.push({ url, opts });
    return { ok: true, status: 202, json: async () => ({ job_id: "j1", state: "queued", cached: false }) };
  });

  const cfg = buildDigitizeConfig(digitizedElement(), PROJECT);
  const sub = await startDigitize(TINY_PNG_B64, cfg, fetchFn);
  expect(sub.job_id).toBe("j1");

  expect(calls).toHaveLength(1);
  expect(calls[0].url).toBe("http://127.0.0.1:8721/digitize");
  expect(calls[0].opts.method).toBe("POST");

  const form = calls[0].opts.body;
  expect(form).toBeInstanceOf(FormData);
  const image = form.get("image");
  expect(image.type).toBe("image/png");
  expect(image.size).toBeGreaterThan(0);

  const sent = JSON.parse(form.get("config"));
  expect(sent.thread_brand).toBe("isacord");
  expect(sent.garment_id).toBe("left_chest");
  for (const k of Object.keys(sent)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
});

test("startDigitize surfaces the service's own detail sentence on a 400", async () => {
  stubStorage({});
  const { startDigitize } = await import("./digitizer.js");
  const fetchFn = async () => ({
    ok: false, status: 400,
    json: async () => ({ detail: "unknown thread brand 'nope'. See /health for the list." }),
  });
  await expect(startDigitize(TINY_PNG_B64, {}, fetchFn)).rejects.toThrow(/unknown thread brand 'nope'/);
});

test("pollJob follows queued -> running -> done, reports states, and returns the finished payload", async () => {
  stubStorage({});
  const { pollJob } = await import("./digitizer.js");
  const states = [
    { state: "queued", job_id: "j1" },
    { state: "running", job_id: "j1" },
    { state: "done", job_id: "j1", design: { stitches: [] }, warnings: [] },
  ];
  let i = 0;
  const fetchFn = async () => ({ ok: true, json: async () => states[Math.min(i++, states.length - 1)] });
  const seen = [];
  const job = await pollJob("j1", { fetchFn, intervalMs: 0, onState: (s) => seen.push(s) });
  expect(job.state).toBe("done");
  expect(job.design).toBeDefined();
  expect(seen).toEqual(["queued", "running"]);
});

test("pollJob throws the job's error for a failed job", async () => {
  stubStorage({});
  const { pollJob } = await import("./digitizer.js");
  const fetchFn = async () => ({ ok: true, json: async () => ({ state: "error", error: "ValueError: bad art" }) });
  await expect(pollJob("j1", { fetchFn, intervalMs: 0 })).rejects.toThrow(/bad art/);
});

test("fetchHealth returns the payload when the service is up and null for down/non-ok/garbage", async () => {
  stubStorage({});
  const { fetchHealth } = await import("./digitizer.js");
  const up = await fetchHealth(async () => ({ ok: true, json: async () => ({ status: "ok", brands: [] }) }));
  expect(up && up.status).toBe("ok");
  expect(await fetchHealth(async () => ({ ok: false, status: 500, json: async () => ({}) }))).toBeNull();
  expect(await fetchHealth(async () => { throw new TypeError("fetch failed"); })).toBeNull();
});

// ---- shape-layers edits (review-screen contract v1) ------------------------
//
// The other end of this seam is digitizer_service/app.py's
// _canonicalize_shape_edits: the job cache keys on sha256(image) + the
// canonical config, so the app must send edits ALREADY canonical — sorted,
// deduped, no null/"auto"/app-only fields — or two spellings of one edit
// would be two jobs (and the panel's pending-edits check would lie).

test("canonicalShapeEdits: sorts+dedupes deletions, strips rgb/null/auto, drops empty entries and overrides for deleted shapes", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    deletedShapeIds: ["Sbbb", "Saaa", "Sbbb"],
    shapeOverrides: {
      Szzz: { thread_index: 4, rgb: [1, 2, 3], tier: "auto", fill_angle_deg: null },
      Saaa: { tier: "satin" }, // deleted above -> omitted (engine would only warn)
      Smmm: { tier: "auto", rgb: [9, 9, 9] }, // canonicalizes to nothing -> dropped
      Sfff: { fill_angle_deg: 90, layer: 2, border: "bean" },
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    deleted_shape_ids: ["Saaa", "Sbbb"],
    shape_overrides: {
      Sfff: { fill_angle_deg: 90, border: "bean", layer: 2 },
      Szzz: { thread_index: 4 },
    },
  });
  // No edits at all -> a config indistinguishable from the pre-layers one.
  expect(canonicalShapeEdits(digitizedElement())).toEqual({});
});

test("editsKey is stable across edit spellings and distinguishes real differences (the pending-edits check)", async () => {
  stubStorage({});
  const { canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const a = editsKey(canonicalShapeEdits(digitizedElement({ deletedShapeIds: ["Sb", "Sa"] })));
  const b = editsKey(canonicalShapeEdits(digitizedElement({ deletedShapeIds: ["Sa", "Sb", "Sa"] })));
  expect(a).toBe(b);
  const c = editsKey(canonicalShapeEdits(digitizedElement({ deletedShapeIds: ["Sa"] })));
  expect(c).not.toBe(a);
  expect(editsKey(canonicalShapeEdits(digitizedElement()))).toBe(editsKey({}));
});

test("buildDigitizeConfig carries the edits — two elements differing only in shape_overrides produce different configs (cache-key proof, app side)", async () => {
  stubStorage({});
  const { buildDigitizeConfig } = await import("./digitizer.js");
  const plain = buildDigitizeConfig(digitizedElement(), PROJECT);
  const edited = buildDigitizeConfig(
    digitizedElement({ shapeOverrides: { S1: { tier: "fill" } }, deletedShapeIds: ["S9"] }),
    PROJECT
  );
  expect("shape_overrides" in plain).toBe(false);
  expect("deleted_shape_ids" in plain).toBe(false);
  expect(edited.shape_overrides).toEqual({ S1: { tier: "fill" } });
  expect(edited.deleted_shape_ids).toEqual(["S9"]);
  expect(JSON.stringify(edited)).not.toBe(JSON.stringify(plain));
  for (const k of Object.keys(edited)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
});

test("buildDigitizeConfig pins thread_brand to the chart a recolor's indexes were picked against, and only then", async () => {
  // Preference moved to madeira AFTER the user picked threads against an
  // isacord job: sending madeira would re-aim every stored thread_index at
  // a different manufacturer's chart, so the config pins isacord.
  stubStorage({ "embstudio:threadPalette": "madeira-rayon" });
  const { buildDigitizeConfig } = await import("./digitizer.js");
  const recolored = buildDigitizeConfig(
    digitizedElement({
      review: { brandId: "isacord", shapes: [] },
      shapeOverrides: { S1: { thread_index: 7, rgb: [1, 2, 3] } },
    }),
    PROJECT
  );
  expect(recolored.thread_brand).toBe("isacord");
  // No thread_index override -> the preference rides as always.
  const tiered = buildDigitizeConfig(
    digitizedElement({
      review: { brandId: "isacord", shapes: [] },
      shapeOverrides: { S1: { tier: "fill" } },
    }),
    PROJECT
  );
  expect(tiered.thread_brand).toBe("madeira-rayon");
});

test("reviewFromJob slims the wire review: per-shape thread rgb by number, sew facts kept, outlines thinned", async () => {
  stubStorage({});
  const { reviewFromJob, thinOutline } = await import("./digitizer.js");
  const bigOutline = Array.from({ length: 300 }, (_, i) => [i, i * 2]);
  const wire = {
    palette: [
      { brand: "Isacord Polyester 40", brand_id: "isacord", number: "0020", name: "Black", rgb: [0, 0, 0] },
      { brand: "Isacord Polyester 40", brand_id: "isacord", number: "1902", name: "Poinsettia", rgb: [204, 0, 0] },
    ],
    design_size_mm: [80, 40],
    shapes: [
      { shape_id: "Sa", thread_index: 4, thread_number: "1902", area_mm2: 412.126, source: "quant",
        layer: 1, sew_index: 1, sew_block: 1, tier: "fill", outline_mm: bigOutline, holes_mm: [] },
      // Unstitched shape: no sew facts, but its thread still resolves by number.
      { shape_id: "Sb", thread_index: 0, thread_number: "0020", area_mm2: 3.2, source: "quant",
        layer: null, sew_index: null, sew_block: null, tier: null, outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
    ],
  };
  const r = reviewFromJob(wire);
  expect(r.brandId).toBe("isacord");
  expect(r.shapes).toHaveLength(2);
  expect(r.shapes[0]).toMatchObject({
    id: "Sa", threadNumber: "1902", rgb: [204, 0, 0], areaMm2: 412.126,
    layer: 1, sewIndex: 1, sewBlock: 1, tier: "fill",
  });
  expect(r.shapes[0].outline.length).toBeLessThanOrEqual(48);
  // Endpoints survive thinning (aggregate check, not per-entry).
  expect(r.shapes[0].outline[0]).toEqual([0, 0]);
  expect(r.shapes[0].outline[r.shapes[0].outline.length - 1]).toEqual([299, 598]);
  expect(r.shapes[1].rgb).toEqual([0, 0, 0]);
  expect(r.shapes[1].tier).toBeNull();
  expect(thinOutline([[0, 0], [1, 1]])).toEqual([[0, 0], [1, 1]]); // short outlines pass through
  expect(reviewFromJob(null)).toBeNull();
});

test("reconcileReview keeps a deleted shape's last known row so the panel can strike it through and restore it", async () => {
  stubStorage({});
  const { reconcileReview } = await import("./digitizer.js");
  const prev = { brandId: "isacord", shapes: [
    { id: "Sa", tier: "fill" }, { id: "Sdead", tier: "satin", areaMm2: 5 },
  ]};
  // The fresh review after digitizing WITH the deletion: Sdead is gone (the
  // engine dropped it after stage 4 — it was never planned).
  const fresh = { brandId: "isacord", shapes: [{ id: "Sa", tier: "fill" }] };
  const merged = reconcileReview(prev, fresh, ["Sdead"]);
  expect(merged.shapes.map((s) => s.id)).toEqual(["Sa", "Sdead"]);
  expect(merged.shapes[1].areaMm2).toBe(5); // the carried row is the old one
  // A deletion the previous review never knew either simply isn't renderable.
  expect(reconcileReview(prev, fresh, ["Sghost"]).shapes.map((s) => s.id)).toEqual(["Sa"]);
  // Un-deleted (restored, then applied): the fresh review wins outright.
  expect(reconcileReview(prev, fresh, []).shapes).toHaveLength(1);
  // No fresh review (a failed run patches nothing, but be safe): keep prev.
  expect(reconcileReview(prev, null, ["Sdead"])).toBe(prev);
});

// ---- adapter ---------------------------------------------------------------

test("decodedFromDesign strips the end record, centers on the sewn bbox, and counts every record type", async () => {
  stubStorage({});
  const { decodedFromDesign } = await import("./digitizer.js");
  // Uncentered on purpose: stitch bbox x 100..300, y 50..150 -> center (200, 100).
  const design = {
    stitches: [
      { x: 100, y: 50, type: "jump" },
      { x: 100, y: 50, type: "stitch" },
      { x: 300, y: 50, type: "stitch" },
      { x: 300, y: 150, type: "trim" },
      { x: 300, y: 150, type: "color" },
      { x: 300, y: 150, type: "stitch" },
      { x: 0, y: 0, type: "end" },
    ],
    colors: [{ r: 1, g: 2, b: 3 }, { r: 4, g: 5, b: 6 }],
    name: "spec",
  };
  const dec = decodedFromDesign(design);
  expect(dec.stitchCount).toBe(3);
  expect(dec.jumpCount).toBe(1);
  expect(dec.trimCount).toBe(1);
  expect(dec.colorCount).toBe(2);
  expect(dec.widthMM).toBeCloseTo(20, 5);
  expect(dec.heightMM).toBeCloseTo(10, 5);
  expect(dec.stitches.some((s) => s.type === "end")).toBe(false);
  // Centered: first stitch (100,50) -> (-100,-50).
  const first = dec.stitches.find((s) => s.type === "stitch");
  expect(first.x).toBe(-100);
  expect(first.y).toBe(-50);
});

test("digitizedBlockColors defaults every block to the service palette; a user override wins per block", async () => {
  stubStorage({});
  const { digitizedBlockColors } = await import("./digitizer.js");
  const el = digitizedElement({
    result: { colors: [{ r: 0, g: 0, b: 0 }, { r: 204, g: 0, b: 0 }] },
    blockColors: { 1: [10, 20, 30] },
  });
  expect(digitizedBlockColors(el)).toEqual({ 0: [0, 0, 0], 1: [10, 20, 30] });
});

// ---- THE Y-AXIS GOLDEN (blueprint demand: day one) --------------------------
//
// fixtures/digitized-asym.json was captured from the LIVE service at this
// branch's base: asym_source.png is a black bar across the TOP of the image
// and a red square at the BOTTOM-LEFT, on white. The service Design is +y UP
// (digitizer_core/adapter.py owns the one flip), so in the app's design
// space the bar must sit at POSITIVE y and the red square at NEGATIVE y and
// NEGATIVE x. If any layer between the service and the field flips an axis,
// these signs invert and this fails.

function blocksOf(design) {
  const blocks = [[]];
  for (const s of design.stitches) {
    if (s.type === "color") blocks.push([]);
    else if (s.type === "stitch") blocks[blocks.length - 1].push(s);
  }
  return blocks;
}

test("GOLDEN: a service-digitized asymmetric design renders right way up (and right way round) through generateElement", async () => {
  stubStorage({});
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");

  const el = digitizedElement({ result: fixture.design, warnings: fixture.warnings });
  const d = generateElement(el, garment, {});
  expect(d.stitchCount).toBe(fixture.design.stitchCount);
  expect(d.widthMM).toBeCloseTo(fixture.design.widthMM, 0);

  // Service thread palette flows through as block colors (black, then red).
  expect(d.colors[0]).toMatchObject({ r: 0, g: 0, b: 0 });
  expect(d.colors[1]).toMatchObject({ r: 204, g: 0, b: 0 });

  const blocks = blocksOf(d);
  expect(blocks).toHaveLength(2);
  // Aggregate min/max, then assert once (per-entry expect() over big arrays
  // is a known Vitest-timeout foot-gun in this repo).
  const bar = blocks[0], square = blocks[1];
  const barMinY = Math.min(...bar.map((s) => s.y));
  const squareMaxY = Math.max(...square.map((s) => s.y));
  const squareMaxX = Math.max(...square.map((s) => s.x));
  expect(bar.length).toBeGreaterThan(100);
  expect(barMinY).toBeGreaterThan(0); // the TOP bar sews entirely above center
  expect(squareMaxY).toBeLessThan(0); // the BOTTOM square entirely below
  expect(squareMaxX).toBeLessThan(0); // ...and on the LEFT
});

test("GOLDEN: placement controls act on the digitized result like any element (scale + offset)", async () => {
  stubStorage({});
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");

  const native = generateElement(digitizedElement({ result: fixture.design }), garment, {});
  const sized = generateElement(digitizedElement({ result: fixture.design, sizeMm: 20 }), garment, {});
  expect(sized.widthMM).toBeCloseTo(20, 1);
  expect(sized.heightMM).toBeCloseTo((20 / native.widthMM) * native.heightMM, 1);

  const shifted = generateElement(digitizedElement({ result: fixture.design, offsetXMm: 10 }), garment, {});
  const a = native.stitches.find((s) => s.type === "stitch");
  const b = shifted.stitches.find((s) => s.type === "stitch");
  expect(b.x).toBe(a.x + 100); // 10 mm = 100 units
  expect(b.y).toBe(a.y);
});

test("a digitized element with no result yet is not ready (null), and an element with a result needs no service at all", async () => {
  stubStorage({});
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  expect(generateElement(digitizedElement(), garment, {})).toBeNull();
  // No fetch stub installed here: generation from the baked result must be
  // fully offline (the hybrid-persistence decision).
  const d = generateElement(digitizedElement({ result: fixture.design }), garment, {});
  expect(d.stitchCount).toBeGreaterThan(0);
});

test("export: Studio bakes its OWN DST from a digitized element and it round-trips through its own decoder", async () => {
  stubStorage({});
  const { generateAll } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const project = {
    version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223],
    elements: [digitizedElement({ result: fixture.design })],
  };
  const { combined } = generateAll(project, {});
  const bytes = EMB.encodeDST(combined);
  expect(bytes.length).toBeGreaterThan(512);
  const back = EMB.decodeDST(bytes);
  // +1: the trailing "end" record encodes as one extra stitch at the design
  // origin (encodeDST's documented fall-through — see combine.js's note);
  // identical behavior to every other single-element export.
  expect(back.stitchCount).toBe(fixture.design.stitchCount + 1);
  expect(back.colorCount).toBe(fixture.design.colorCount);
  expect(back.widthMM).toBeCloseTo(combined.widthMM, 0);
});

// ---- warnings --------------------------------------------------------------

test("describeWarnings translates pipeline codes to customer language, with counts", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings([
    { code: "DROPPED_SMALL_SHAPES", message: "engine prose", count: 3 },
    { code: "DROPPED_SMALL_SHAPES", message: "engine prose", count: 1 },
    { code: "LONG_JUMPS_TRIMMED", message: "engine prose", count: 2 },
  ]);
  expect(out[0].text).toBe("3 parts of the art were too small to sew and were left out.");
  expect(out[1].text).toBe("One part of the art was too small to sew and was left out.");
  expect(out[2].text).toBe("The thread gets cut 2 times where it has to travel a long way.");
});

test("describeWarnings speaks the two shape-edit codes: deletions agree with the panel's count, unmatched edits are named, not swallowed", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings([
    { code: "SHAPES_DELETED_BY_USER", message: "engine prose", count: 2, ids: ["Sa", "Sb"] },
    { code: "SHAPE_EDIT_UNKNOWN_ID", message: "engine prose", count: 1, ids: ["Sz"] },
  ]);
  expect(out[0].text).toBe("2 shapes are hidden by you. Restore them from the Layers list to sew them again.");
  expect(out[1].text).toBe("One layer edit no longer matches any shape in the art, so it wasn't applied.");
});

test("describeWarnings falls back to the service's own message for a code it doesn't know (codes are append-only)", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings([{ code: "SOME_FUTURE_CODE", message: "The engine said a thing." }]);
  expect(out[0].text).toBe("The engine said a thing.");
});

test("the fixture's own warnings translate cleanly (no raw codes leak to the panel)", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings(fixture.warnings);
  const anyRaw = out.some((w) => /_/.test(w.text));
  expect(anyRaw).toBe(false);
  expect(out.length).toBe(fixture.warnings.length);
});
