// @vitest-environment jsdom
//
// Component-level coverage for DigitizePanel.svelte's Layers panel and its
// Sequencer view — closing a gap this repo's own MASTER_SCOPE.md has flagged
// since the panel first shipped: the tier/border/fill-angle/underlay-style
// per-shape controls (and now the Sequencer) have only ever been checked via
// live-browser passes, never a component test harness, because none existed
// in this repo. `ManualPanel.spec.js` was the first precedent for the
// pattern this file follows (Svelte 5's `$on` no longer works on a mounted
// instance, so a real *.svelte wrapper that listens with `on:elupdate` is
// the only way to observe a dispatched patch — see DigitizePanel.testHarness
// .svelte's own comment).
//
// Deliberately NOT covered here: the upload -> Digitize -> poll flow. That
// needs a real (or mocked) digitizer service and is already covered by real
// Playwright e2e specs (`app/e2e/digitize-stale-edits.spec.js`). Every test
// below starts from an element that already has a `result`/`review` (as if
// a job already ran). Nothing in the panel starts a run on its own (the
// "nothing runs until Auto Digitize Image is pressed" block below pins that),
// so no network call happens unless a test presses the button.
import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./DigitizePanel.testHarness.svelte";
import { DEFAULT_DIGITIZE_PARAMS } from "../lib/project.js";

// Only `loadImage` is controlled; the rest of lib/rasterize.js is the real
// module, so `isVectorFile`/`rasterSize`/`UNREADABLE` are the shipped ones and
// this cannot pass against a stub of the thing under test. jsdom neither
// implements `createImageBitmap` nor loads a blob: URL into an <img>, so the
// real loadImage would hang rather than reject — the failure has to be
// injected to be observable at all.
let loadImageResult = () => Promise.reject(new Error("stub"));
vi.mock("../lib/rasterize.js", async (importOriginal) => {
  const real = await importOriginal();
  return { ...real, loadImage: (...args) => loadImageResult(...args) };
});

function shapeRow(id, overrides = {}) {
  return {
    id,
    threadIndex: 0,
    threadNumber: "1000",
    rgb: [200, 30, 30],
    areaMm2: 120,
    layer: 0,
    sewOrder: null,
    sewIndex: 0,
    sewBlock: 0,
    tier: "fill",
    stitched: true,
    outline: [[0, 0], [10, 0], [10, 10]],
    outlineFull: [[0, 0], [10, 0], [10, 10]],
    textCandidate: false,
    textClusterId: null,
    ocrChar: null,
    ocrConfidence: null,
    enclosedColourUnknown: false,
    ...overrides,
  };
}

function baseElement(shapes = [], extra = {}) {
  return {
    id: "e1",
    type: "digitized",
    name: "logo.png",
    // Truthy placeholder — real bytes are never read in these tests (the
    // upload/digitize flow itself is out of scope, see the file banner
    // comment), just needed to clear the "!element.sourcePng" upload-prompt
    // gate so the params/result/Layers panel actually renders.
    sourcePng: "data:image/png;base64,AAAA",
    params: { ...DEFAULT_DIGITIZE_PARAMS },
    result: { stitchCount: 100, widthMM: 50, heightMM: 50, colorCount: shapes.length, colors: [], stitches: [] },
    warnings: [],
    blockColors: {},
    review: { brandId: "studio", shapes },
    shapeOverrides: {},
    deletedShapeIds: [],
    appliedEdits: null,
    preflight: null,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
    rotationDeg: 0,
    ...extra,
  };
}

// The per-shape rows live behind a closed-by-default "Edit shapes" disclosure
// (a two-colour logo otherwise opens 329 controls), so every test ABOUT a row
// has to open it first. Done here rather than in each test so the disclosure
// cannot quietly change what 20 tests are asserting; the default-closed state
// gets its own test below, which is the one thing this helper would hide.
function openLayers(utils) {
  // The Layers block lives on the Shapes tab since 2026-09-30 (the panel
  // opens on Settings), so the tab comes first; then the disclosure inside.
  const tab = [...utils.container.querySelectorAll('button[role="tab"]')]
    .find((b) => b.textContent.trim().startsWith("Shapes"));
  if (tab) fireEvent.click(tab);
  const shapesBtn = [...utils.container.querySelectorAll("button")]
    .find((b) => /^Edit shapes/.test(b.textContent.trim()));
  if (shapesBtn) fireEvent.click(shapesBtn);
  return utils;
}

function renderPanel(shapes = [], extra = {}) {
  const patches = [];
  const utils = render(Harness, {
    props: { element: baseElement(shapes, extra), onPatch: (d) => patches.push(d) },
  });
  openLayers(utils);
  return { ...utils, patches };
}

function lastOverride(patches, sid) {
  const p = patches[patches.length - 1].patch;
  return (p.shapeOverrides || {})[sid];
}

// ---- per-shape controls (tier/angle/underlay/border) ----------------------

describe("per-shape stitch-type/angle/underlay/border controls", () => {
  test("changing Stitch type writes a tier override", async () => {
    const { getByLabelText, patches } = renderPanel([shapeRow("s1")]);
    await fireEvent.change(getByLabelText(/^Stitch type \u2014 /), { target: { value: "satin" } });
    expect(patches).toHaveLength(1);
    expect(lastOverride(patches, "s1")).toEqual({ tier: "satin" });
  });

  test("setting Stitch type back to Auto clears the override entirely", async () => {
    const { getByLabelText, patches } = renderPanel([shapeRow("s1")], {
      shapeOverrides: { s1: { tier: "satin" } },
    });
    await fireEvent.change(getByLabelText(/^Stitch type \u2014 /), { target: { value: "auto" } });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapeOverrides.s1).toBeUndefined();
  });

  // The design-wide params section has its OWN "Fill angle"/"Border"
  // controls (label-wrapped `<select>`s, no `aria-label`) sitting on the
  // same page as these per-shape ones — `getByLabelText` matches both and
  // is ambiguous. The per-shape selects are the only ones carrying an
  // explicit `aria-label` attribute, so an attribute selector disambiguates
  // cleanly without needing to scope into the row's own DOM subtree.
  // Prefix, not equality: every per-shape control's name now ends with the
  // row it acts on ("Border \u2014 shape 1 of 3, thread #0134, 18.7 mm\u00b2"), so
  // the list is navigable by screen reader and addressable by voice. The
  // separator is what keeps "Sew later" from also matching "Sew later within
  // this color".
  function perShapeSelect(container, label) {
    return container.querySelector(`select[aria-label^="${label} \u2014 "]`);
  }

  test("Fill angle and Underlay style only appear once a shape's effective tier is fill", async () => {
    const { container } = renderPanel([shapeRow("s1", { tier: "satin" })]);
    expect(perShapeSelect(container, "Fill angle")).toBeNull();
    expect(perShapeSelect(container, "Underlay style")).toBeNull();
  });

  test("Fill angle and Underlay style DO appear for a fill-tiered shape", async () => {
    const { container } = renderPanel([shapeRow("s1", { tier: "fill" })]);
    expect(perShapeSelect(container, "Fill angle")).toBeTruthy();
    expect(perShapeSelect(container, "Underlay style")).toBeTruthy();
  });

  test("changing Fill angle writes a numeric fill_angle_deg override", async () => {
    const { container, patches } = renderPanel([shapeRow("s1", { tier: "fill" })]);
    await fireEvent.change(perShapeSelect(container, "Fill angle"), { target: { value: "45" } });
    expect(lastOverride(patches, "s1")).toEqual({ fill_angle_deg: 45 });
  });

  test("changing Underlay style writes an underlay_style override", async () => {
    const { container, patches } = renderPanel([shapeRow("s1", { tier: "fill" })]);
    await fireEvent.change(perShapeSelect(container, "Underlay style"), { target: { value: "edge_run" } });
    expect(lastOverride(patches, "s1")).toEqual({ underlay_style: "edge_run" });
  });

  test("Border defaults to the design-wide setting and 'No border' writes an explicit off", async () => {
    const { container, patches } = renderPanel([shapeRow("s1")]);
    expect(perShapeSelect(container, "Border").value).toBe("default");
    await fireEvent.change(perShapeSelect(container, "Border"), { target: { value: "off" } });
    expect(lastOverride(patches, "s1")).toEqual({ border: "off" });
  });

  test("recoloring through the thread swatch picker writes thread_index and rgb", async () => {
    const { container, getByRole, patches } = renderPanel([shapeRow("s1", { rgb: [10, 10, 10] })]);
    await fireEvent.click(container.querySelector(".tp-trigger"));
    await waitFor(() => expect(getByRole("listbox")).toBeTruthy());
    const [firstSwatch] = getByRole("listbox").querySelectorAll("[role='option']");
    await fireEvent.click(firstSwatch);
    await waitFor(() => expect(patches.length).toBeGreaterThan(0));
    const ov = lastOverride(patches, "s1");
    expect(ov).toHaveProperty("thread_index");
    expect(ov).toHaveProperty("rgb");
  });
});

// ---- delete / restore ------------------------------------------------------

describe("whole-design params", () => {
  // `detail_layer` moved out of the params list and onto the reading row
  // (Kent's call 2026-08-30): it only does anything on tonal art, so it shows
  // only where the art is actually going down that lane -- by the engine's
  // reading or by the user's own override -- instead of sitting beside stitch
  // width labelled "Detail lines for photos" on a flat logo that never uses it.
  const TONAL = { warnings: [{ code: "CLASSIFIED_PHOTO_SUBJECT", message: "engine prose" }] };

  test("Add fine detail lines renders unchecked on tonal art and patches params on toggle", async () => {
    const { getByLabelText, patches } = renderPanel([shapeRow("s1")], TONAL);
    const box = getByLabelText("Add fine detail lines");
    expect(box.checked).toBe(false);

    await fireEvent.change(box, { target: { checked: true } });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.params.detail_layer).toBe(true);
    // The other params must survive the spread — a params patch replaces the
    // whole object, so dropping one here would silently reset the design.
    expect(patches[0].patch.params.max_colors).toBe(DEFAULT_DIGITIZE_PARAMS.max_colors);
    expect(patches[0].patch.params.satin).toBe(DEFAULT_DIGITIZE_PARAMS.satin);
  });

  test("absent on flat art, which cannot use it", () => {
    const { queryByLabelText } = renderPanel([shapeRow("s1")]);
    expect(queryByLabelText("Add fine detail lines")).toBeNull();
  });

  test("present when stage 1.25 detected a photograph, whatever colour class stage 0 gave", () => {
    // The engine's own verdict (EXIF camera or a face), which is what turns
    // the photographic machinery on since the user-declared override went
    // (Kent, 2026-09-30). It arrives as its own warning code.
    const { getByLabelText } = renderPanel([shapeRow("s1")], {
      warnings: [{ code: "PHOTO_DETECTED", message: "engine prose", signal: "face" }],
    });
    expect(getByLabelText("Add fine detail lines")).toBeTruthy();
  });
});

// ---- what the art was read as ---------------------------------------------
//
// Stage 0 classifies every job on its own (flat / gradient / photo_subject /
// photo_scene), and stage 1.25 adds PHOTO_DETECTED when the file's camera
// header or a face says photograph. This row is Studio SAYING so in plain
// words -- and nothing else. Kent, 2026-09-30: "get rid of the 'it's flat
// art' / 'it's a photo' check boxes ... just automatically recognize what it
// is". Until that day the row carried a one-click correction ("It's flat
// art" wrote forced_class=flat, "It's a photo" set isPhoto).
//
// The FLAT half came back the same evening, also Kent's call: his Instagram
// icon read as shaded artwork, sewed badly down that lane, and he had no way
// to say "flat". So a tonal reading offers ONE button, "Sew as flat art",
// and a design it was used on says so and offers the way back. Nothing else
// returned: no "It's a photo", and a flat reading still has no button.
//
// `health` stays null here (renderPanel's default), so the reactive re-run
// bails at runDigitize's own `!health` guard and no digitize is attempted --
// same no-service posture as the rest of this file.
describe("the reading row -- states the reading, offers flat on a tonal one", () => {
  function panelWarnedAs(code, extra = {}) {
    return renderPanel([shapeRow("s1")], {
      warnings: [{ code, message: "engine prose" }],
      ...extra,
    });
  }

  const READINGS = [
    // A face routed the design flat (Kent's ruling 2026-09-30).
    ["FACE_ROUTED_FLAT", /A face was found, so it's sewing as flat art/],
    ["CLASSIFIED_PHOTO_SUBJECT", /Read as a photo/],
    ["CLASSIFIED_PHOTO_SCENE", /Read as a photo/],
    // Stage 1.25's verdict on its own (stage 0 said flat): a photograph, but
    // the sentence promises the tier the art is really sewing in.
    ["PHOTO_DETECTED", /Read as a photograph, sewing as solid color regions/],
    ["CLASSIFIED_GRADIENT", /Read as shaded artwork/],
    ["CLASSIFICATION_UNCERTAIN", /Couldn't tell what this artwork is/],
    ["COLOR_CAP_APPLIED", /Read as flat art/],
  ];

  // The readings that sew down a tonal lane, where flat is a real alternative.
  // FACE_ROUTED_FLAT is already flat, so it offers nothing.
  const OFFERS_FLAT = new Set([
    "CLASSIFIED_PHOTO_SUBJECT", "CLASSIFIED_PHOTO_SCENE", "CLASSIFIED_GRADIENT", "PHOTO_DETECTED",
  ]);

  for (const [code, sentence] of READINGS) {
    test(`${code}: states the reading${OFFERS_FLAT.has(code) ? " and offers flat" : " and has no button"}`, () => {
      const { getByText, container } = panelWarnedAs(code);
      expect(getByText(sentence)).toBeTruthy();
      const row = container.querySelector(".dgp-read");
      expect(row).toBeTruthy();
      const buttons = [...row.querySelectorAll("button")].map((b) => b.textContent.trim());
      expect(buttons).toEqual(OFFERS_FLAT.has(code) ? ["Sew as flat art"] : []);
      // The corrections that did NOT come back, by name.
      expect(row.textContent).not.toMatch(/It's a photo|Use automatic detection|You set this to/);
    });
  }

  test("Sew as flat art writes forced_class=flat and keeps the other params", async () => {
    const { getByRole, patches } = panelWarnedAs("CLASSIFIED_GRADIENT");
    await fireEvent.click(getByRole("button", { name: "Sew as flat art" }));
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.params.forced_class).toBe("flat");
    expect(patches[0].patch.params.max_colors).toBe(DEFAULT_DIGITIZE_PARAMS.max_colors);
  });

  test("a design set to flat says so, offers the way back, and drops the detail-lines option", () => {
    // Once the override takes effect the art classifies flat and the
    // CLASSIFIED_* warning is gone, so the row keys on the stored param.
    const { getByText, container, queryByLabelText } = panelWarnedAs("COLOR_CAP_APPLIED", {
      params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat" },
    });
    expect(getByText(/You set this to flat art/)).toBeTruthy();
    const buttons = [...container.querySelectorAll(".dgp-read button")].map((b) => b.textContent.trim());
    expect(buttons).toEqual(["Use automatic detection"]);
    expect(queryByLabelText("Add fine detail lines")).toBeNull();
  });

  test("a design set to flat keeps its row before any run has landed", () => {
    const { getByText } = renderPanel([shapeRow("s1")], {
      result: null,
      params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat" },
    });
    expect(getByText(/You set this to flat art/)).toBeTruthy();
  });

  test("Use automatic detection REMOVES the key, so the params match a design that never set it", async () => {
    const { getByRole, patches } = panelWarnedAs("COLOR_CAP_APPLIED", {
      params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat" },
    });
    await fireEvent.click(getByRole("button", { name: "Use automatic detection" }));
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.params).toEqual({ ...DEFAULT_DIGITIZE_PARAMS });
    expect("forced_class" in patches[0].patch.params).toBe(false);
  });

  test("says nothing about a reading before the first run has produced one", () => {
    const { queryByText, container } = renderPanel([shapeRow("s1")], { result: null });
    expect(queryByText(/Read as/)).toBeNull();
    expect(container.querySelector(".dgp-read")).toBeNull();
  });

  // One render per test: testing-library only cleans the DOM up BETWEEN
  // tests, so two panels in one test double every label.
  // PHOTO_DETECTED alone is a photograph on a flat tier; the detail lines
  // read off its raster, so the option is offered there too.
  for (const code of ["CLASSIFIED_PHOTO_SUBJECT", "CLASSIFIED_GRADIENT", "PHOTO_DETECTED", "FACE_ROUTED_FLAT"]) {
    test(`${code}: the detail-lines option rides this reading`, () => {
      const { getByLabelText } = panelWarnedAs(code);
      expect(getByLabelText("Add fine detail lines")).toBeTruthy();
    });
  }
  for (const code of ["COLOR_CAP_APPLIED", "CLASSIFICATION_UNCERTAIN"]) {
    test(`${code}: no detail-lines option on a flat reading`, () => {
      const { queryByLabelText } = panelWarnedAs(code);
      expect(queryByLabelText("Add fine detail lines")).toBeNull();
    });
  }

  // A project saved before 2026-09-30 can carry a forced_class the Studio no
  // longer writes, or isPhoto. Neither is sent (digitizer.spec.js) and
  // neither may put a "You set this to..." row up: only "flat" is honoured.
  test("a legacy non-flat forced_class saved in the element changes nothing on screen", () => {
    const legacy = panelWarnedAs("COLOR_CAP_APPLIED", {
      params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "photo_subject" },
    });
    expect(legacy.getByText(/Read as flat art/)).toBeTruthy();
    expect(legacy.queryByText(/You set this to/)).toBeNull();
    expect(legacy.container.querySelectorAll(".dgp-read button")).toHaveLength(0);
  });

  test("a legacy isPhoto saved in the element changes nothing on screen", () => {
    const photo = panelWarnedAs("COLOR_CAP_APPLIED", { isPhoto: true });
    expect(photo.getByText(/Read as flat art/)).toBeTruthy();
    expect(photo.queryByText(/You set this to/)).toBeNull();
    expect(photo.queryByLabelText("Add fine detail lines")).toBeNull();
  });
});

describe("hiding, restoring, and BACKGROUND_ENCLOSED restore", () => {
  test("hiding a shape adds it to deletedShapeIds", async () => {
    const { container, patches } = renderPanel([shapeRow("s1")]);
    const hideBtn = container.querySelector('button[aria-label^="Hide this shape — "]');
    await fireEvent.click(hideBtn);
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.deletedShapeIds).toEqual(["s1"]);
  });

  test("Restore removes an already-hidden shape from deletedShapeIds", async () => {
    const { getByRole, patches } = renderPanel([shapeRow("s1")], { deletedShapeIds: ["s1"] });
    await fireEvent.click(getByRole("button", { name: "Restore" }));
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.deletedShapeIds).toEqual([]);
  });

  test("'Sew it' on an unstitched (BACKGROUND_ENCLOSED) row restores stitching via override, not deletedShapeIds", async () => {
    const { getByRole, patches } = renderPanel([shapeRow("s1", { stitched: false })]);
    await fireEvent.click(getByRole("button", { name: "Sew it" }));
    expect(patches).toHaveLength(1);
    expect(lastOverride(patches, "s1")).toEqual({ stitched: true });
    expect(patches[0].patch.deletedShapeIds).toBeUndefined();
  });

  // ---- enclosed_colour_unknown (contract v1.7): a restored alpha-derived
  // hole inherited its RGB from whatever the exporter flattened under the
  // transparency, so restoring it must surface the row's ThreadPicker /
  // recolorShape path instead of sewing the inherited colour silently.

  test("'Sew it' on a colour-unknown enclosed row restores it AND marks it as needing a colour pick", async () => {
    const { getByRole, queryByText, patches } = renderPanel([
      shapeRow("hole", { stitched: false, enclosedColourUnknown: true }),
    ]);
    // No marker while the row is still unstitched — the inherited colour
    // only becomes a problem once the shape is actually going to sew.
    expect(queryByText("pick a color")).toBeNull();
    await fireEvent.click(getByRole("button", { name: "Sew it" }));
    expect(patches).toHaveLength(1);
    expect(lastOverride(patches, "hole")).toEqual({ stitched: true });
    // The harness merged the patch and re-rendered: the restored row now
    // carries the needs-colour marker beside its ThreadPicker.
    expect(queryByText("pick a color")).toBeTruthy();
  });

  test("the needs-colour marker clears once a thread colour override exists (recolorShape ran)", async () => {
    const { queryByText } = renderPanel(
      [shapeRow("hole", { stitched: false, enclosedColourUnknown: true })],
      { shapeOverrides: { hole: { stitched: true, thread_index: 4, rgb: [200, 200, 200] } } },
    );
    expect(queryByText("pick a color")).toBeNull();
  });

  test("'Sew all' (restoreAllUnstitched) restores every enclosed row in one patch and marks only the colour-unknown one", async () => {
    const { getByRole, queryAllByText, patches } = renderPanel([
      shapeRow("hole", { stitched: false, enclosedColourUnknown: true }),
      shapeRow("known", { stitched: false }),
    ]);
    await fireEvent.click(getByRole("button", { name: "Sew all 2" }));
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapeOverrides).toEqual({
      hole: { stitched: true },
      known: { stitched: true },
    });
    // Only the flag-carrying row is marked — a colour-KNOWN enclosed region
    // (logo_whitebg's White hole) restores clean, no marker.
    expect(queryAllByText("pick a color")).toHaveLength(1);
  });
});

// ---- sew-order reorder (across layers, and within one layer) --------------

describe("sew-order reorder buttons", () => {
  test("Sew later steps a shape past the next layer entirely when joining it wouldn't actually move the row", async () => {
    // moveShape's own comment explains why: joining "a" into "b"'s layer
    // (target=1) would place it by its own (lower) sewIndex, which sorts
    // it right back to where it started — a click must always move
    // something, so it steps past the whole neighbouring layer instead
    // (target=2). This is the everyday case: any two simple, differently-
    // layered shapes in normal top-sews-first order hit this branch, not
    // the simpler "join" one.
    const rows = [
      shapeRow("a", { layer: 0, sewIndex: 0 }),
      shapeRow("b", { layer: 1, sewIndex: 1 }),
    ];
    const { patches } = renderPanel(rows);
    const laterBtns = document.querySelectorAll('button[aria-label^="Sew later — "]');
    await fireEvent.click(laterBtns[0]); // move "a" later, past "b"'s layer
    expect(patches).toHaveLength(1);
    expect(lastOverride(patches, "a")).toEqual({ layer: 2 });
  });

  test("Sew later joins the adjacent layer directly when doing so would actually move the row", async () => {
    // The simpler "join" branch: "a" has a HIGHER sewIndex than "b", so
    // joining b's layer (target=1) sorts "a" after "b" — a real move — and
    // the step-past fallback never triggers.
    const rows = [
      shapeRow("a", { layer: 0, sewIndex: 5 }),
      shapeRow("b", { layer: 1, sewIndex: 1 }),
    ];
    const { patches } = renderPanel(rows);
    const laterBtns = document.querySelectorAll('button[aria-label^="Sew later — "]');
    await fireEvent.click(laterBtns[0]);
    expect(patches).toHaveLength(1);
    expect(lastOverride(patches, "a")).toEqual({ layer: 1 });
  });

  test("the first row's Sew earlier and the last row's Sew later are disabled", async () => {
    const rows = [shapeRow("a", { layer: 0 }), shapeRow("b", { layer: 1 })];
    renderPanel(rows);
    const earlierBtns = document.querySelectorAll('button[aria-label^="Sew earlier — "]');
    const laterBtns = document.querySelectorAll('button[aria-label^="Sew later — "]');
    expect(earlierBtns[0]).toBeDisabled();
    expect(laterBtns[laterBtns.length - 1]).toBeDisabled();
  });

  // Rows of one colour used to be indistinguishable to anything that reads
  // names: the merge checkbox was labelled by thread number, which every
  // shape in a colour shares, and the rest were bare verbs repeated once per
  // row. "Click Sew later" was ambiguous as many ways as there were shapes.
  // Same thread number on every row here on purpose — that is the case that
  // used to collapse.
  test("every control in a shape row is named for the row it acts on", async () => {
    const rows = [shapeRow("a", { layer: 0 }), shapeRow("b", { layer: 1 }), shapeRow("c", { layer: 2 })];
    const { container } = renderPanel(rows);

    for (const sel of ['input[type="checkbox"][aria-label]', "button[aria-label]", "select[aria-label]"]) {
      const named = [...container.querySelectorAll(sel)]
        .map((el) => el.getAttribute("aria-label"))
        .filter((n) => / shape \d+ of \d+, /.test(n));
      expect(named.length).toBeGreaterThan(0);
      // The point of the change: no two of them read the same.
      expect(new Set(named).size).toBe(named.length);
    }

    // And the qualifier carries what the row shows on screen, so what is
    // heard matches what is seen.
    const hide = container.querySelector('button[aria-label^="Hide this shape — "]');
    expect(hide.getAttribute("aria-label")).toBe("Hide this shape — shape 1 of 3, thread #1000, 120 mm²");
  });

  // A compact ThreadPicker renders a swatch and nothing else, so before this
  // it reached the accessibility tree as a button with no name at all — one
  // per shape row.
  test("the per-row thread swatch has an accessible name", async () => {
    const { container } = renderPanel([shapeRow("a")]);
    const unnamed = [...container.querySelectorAll("button")]
      .filter((b) => !b.textContent.trim() && !b.getAttribute("aria-label"));
    expect(unnamed).toEqual([]);
    expect(
      container.querySelector('button[aria-label^="Thread color for shape 1 of 1"]'),
    ).toBeTruthy();
  });
});

// ---- Sequencer view (color-block grouping + block-level reorder) ----------

describe("Sequencer view", () => {
  function threeBlockRows() {
    return [
      shapeRow("a", { layer: 0, sewIndex: 0, rgb: [200, 0, 0], threadNumber: "1000" }),
      shapeRow("b", { layer: 1, sewIndex: 1, rgb: [0, 200, 0], threadNumber: "2000" }),
      shapeRow("c", { layer: 1, sewIndex: 2, rgb: [0, 200, 0], threadNumber: "2000" }),
      shapeRow("d", { layer: 2, sewIndex: 3, rgb: [0, 0, 200], threadNumber: "3000" }),
    ];
  }

  test("the toggle is hidden entirely for a single-color design (nothing to sequence)", () => {
    const { queryByText } = renderPanel([shapeRow("a"), shapeRow("b")]); // both default layer 0
    expect(queryByText(/Color sequence/)).toBeNull();
  });

  test("collapsed by default; expanding shows one row per color block with the right member count", async () => {
    const { getByRole, getByText, queryByText } = renderPanel(threeBlockRows());
    const toggle = getByRole("button", { name: /Color sequence \(3 blocks\)/ });
    expect(queryByText("2000")).toBeNull(); // collapsed — block rows not rendered yet
    await fireEvent.click(toggle);
    expect(getByText("1000")).toBeTruthy();
    expect(getByText("2000")).toBeTruthy();
    expect(getByText("3000")).toBeTruthy();
    const middleBlockRow = getByText("2000").closest("li");
    expect(middleBlockRow).toHaveTextContent("2 shapes");
  });

  test("a layer that sews as several machine threads says so in the header and lists them under its row", async () => {
    // `stats.blocks` is the machine's cone list, one per sewn block: the
    // green layer (b, c) is a blend region sewing as three shades, so the
    // machine loads five threads for three colour layers.
    const stats = {
      blocks: [
        { number: "1000", name: "Red", rgb: [200, 0, 0], shape_ids: ["a"] },
        { number: "2100", name: "Dark green", rgb: [0, 120, 0], shape_ids: ["b", "c"] },
        { number: "2000", name: "Green", rgb: [0, 200, 0], shape_ids: ["b", "c"] },
        { number: "2200", name: "Light green", rgb: [0, 240, 0], shape_ids: ["b"] },
        { number: "3000", name: "Blue", rgb: [0, 0, 200], shape_ids: ["d"] },
      ],
    };
    const { getByRole, getByText, getAllByText } = renderPanel(threeBlockRows(), { stats });
    await fireEvent.click(getByRole("button", { name: /Color sequence \(3 blocks, 5 threads on the machine\)/ }));
    const middle = getAllByText("2000")[0].closest("li");
    expect(middle).toHaveTextContent("sews as");
    expect(middle).toHaveTextContent("2100");
    expect(middle).toHaveTextContent("2200");
    // A colour that sews as its one thread keeps a plain row.
    expect(getByText("1000").closest("li")).not.toHaveTextContent("sews as");
  });

  test("a shape hidden or unstitched doesn't get its own block", async () => {
    const rows = [
      shapeRow("a", { layer: 0 }),
      shapeRow("b", { layer: 1, stitched: false }), // BACKGROUND_ENCLOSED, not sewing
      shapeRow("c", { layer: 2 }),
    ];
    const { getByRole } = renderPanel(rows, { deletedShapeIds: [] });
    // Only "a" (layer 0) and "c" (layer 2) are sewable -> 2 blocks, not 3.
    expect(getByRole("button", { name: /Color sequence \(2 blocks\)/ })).toBeTruthy();
  });

  test("sewing a color block later swaps it with its neighbour in one patch, and disables at the ends", async () => {
    const { getByRole, patches } = renderPanel(threeBlockRows());
    await fireEvent.click(getByRole("button", { name: /Color sequence/ }));
    const laterBtns = document.querySelectorAll('button[aria-label="Sew this color later"]');
    const earlierBtns = document.querySelectorAll('button[aria-label="Sew this color earlier"]');
    expect(earlierBtns[0]).toBeDisabled();
    expect(laterBtns[laterBtns.length - 1]).toBeDisabled();

    await fireEvent.click(laterBtns[0]); // move block "a" (layer 0) past block "b/c" (layer 1)
    expect(patches).toHaveLength(1);
    const ov = patches[0].patch.shapeOverrides;
    expect(ov.a).toEqual({ layer: 1 });
    expect(ov.b).toEqual({ layer: 0 });
    expect(ov.c).toEqual({ layer: 0 });
    // The third block ("d", layer 2) wasn't touched by a swap between the
    // first two blocks.
    expect(ov.d).toBeUndefined();
  });

  test("trims-per-1000 shows in the header when preflight data is present", () => {
    const { getByText } = renderPanel(threeBlockRows(), {
      preflight: { metrics: { trims_per_1000: 3.2 }, findings: [] },
    });
    expect(getByText(/3\.2\/1000 trims/)).toBeTruthy();
  });

  test("the trims figure is silent when there's no preflight data", () => {
    const { queryByText } = renderPanel(threeBlockRows());
    expect(queryByText(/trims/)).toBeNull();
  });

  test("a TRIM_HEAVY finding marks the header's trims figure heavy", async () => {
    const { container } = renderPanel(threeBlockRows(), {
      preflight: { metrics: { trims_per_1000: 12.0 }, findings: [{ code: "TRIM_HEAVY", severity: "warn", message: "x" }] },
    });
    const trimsEl = container.querySelector(".dgp-seq-trims");
    expect(trimsEl).toHaveClass("heavy");
  });
});

// ---- auto-restitch after a shape edit --------------------------------------
//
// Kent's call, 2026-08-13: a hand edit on the canvas used to move the outline
// and leave the stitches where they were until "Apply layer changes" was
// pressed. It now restitches on its own after a pause.
//
// Debounced rather than immediate because a restitch is a full stage 0-7
// service run — measured 0.65s on line art but ~10s on a real photograph,
// with no useful cache (the job key folds shape_overrides in, so every edit
// misses). These tests pin the DEBOUNCE, which is the part that keeps ten
// nudges from queueing ten 10-second runs.

describe("findings that have a knob behind them", () => {
  // Item 8. Kent's call was that this belongs AFTER the run, not before it —
  // the panel was deliberately moved away from asking anything up front. So
  // this is not a preset picker; it is the findings the app already computes,
  // each paired with the one adjustment that addresses it.
  const RESULT = { stitchCount: 2400, widthMM: 50, heightMM: 40, colorCount: 3,
                   stitches: [], colors: [] };

  function withFindings(findings, params = {}) {
    return render(Harness, {
      props: {
        element: baseElement([], {
          result: RESULT,
          preflight: { score: 60, grade: "D", findings, metrics: {} },
          params: { target_width_mm: 80, max_colors: 6, satin: true,
                    fill_angle_deg: null, border: null, edge_cap: "none",
                    detail_layer: false, ...params },
        }),
        onPatch: () => {},
      },
    });
  }

  test("too many color stops offers fewer colors, and says what it spends", async () => {
    const { getByTestId } = withFindings(
      [{ code: "COLOR_STOPS_HEAVY", severity: "warn", message: "14 color stops." }]);
    const box = getByTestId("digitize-fixes");
    expect(box.textContent).toMatch(/Use fewer colors/);
    // The cost is named up front — a fix that silently halves the palette is
    // not an offer, it is a surprise.
    expect(box.textContent).toMatch(/6 → 4 colors/);
  });

  test("lettering below readable size offers to enlarge", () => {
    const { getByTestId } = withFindings(
      [{ code: "LETTERING_TOO_SMALL", severity: "warn", message: "sews below readable size." }]);
    expect(getByTestId("digitize-fixes").textContent).toMatch(/Make it bigger/);
    expect(getByTestId("digitize-fixes").textContent).toMatch(/80 → 100 mm wide/);
  });

  test("two findings with the SAME cure offer one button, not two", () => {
    const { container } = withFindings([
      { code: "LETTERING_TOO_SMALL", severity: "warn", message: "a" },
      { code: "STITCHES_TOO_SHORT", severity: "warn", message: "b" },
      // The legibility check (2026-09-10) shares that cure and must not add
      // a third identical button.
      { code: "LETTERING_ILLEGIBLE", severity: "warn", message: "c" },
    ]);
    expect(container.querySelectorAll(".dgp-fix").length).toBe(1);
  });

  test("lettering the thread no longer says offers to enlarge", () => {
    const { getByTestId } = withFindings(
      [{ code: "LETTERING_ILLEGIBLE", severity: "warn",
         message: "the artwork says ‘DRONE’ and the thread reads ‘VR74A’." }]);
    const box = getByTestId("digitize-fixes");
    expect(box.textContent).toMatch(/Make it bigger/);
    expect(box.textContent).toMatch(/80 → 100 mm wide/);
    // The finding's own words say WHY the button is offered — on the
    // button's tooltip, where every fix carries its `why`.
    expect(box.querySelector(".dgp-fix").title).toMatch(/the thread reads/);
  });

  test("a finding with NO knob behind it offers nothing — silence beats a button that does not help", () => {
    // TRIM_HEAVY's lever is chain_links, frozen by gate 1; DENSITY_STACKED has
    // no exposed density control. A plausible-looking button there would be
    // worse than none, because it would be tried.
    const { queryByTestId } = withFindings([
      { code: "TRIM_HEAVY", severity: "warn", message: "10.3 trims per 1,000." },
      { code: "DENSITY_STACKED", severity: "block", message: "stacks 7.2 layers." },
    ]);
    expect(queryByTestId("digitize-fixes")).toBeNull();
  });

  test("tight gaps offer the width the finding names, not a 25% step", () => {
    // SATIN_GAPS_TIGHT (2026-09-30) names the width at which its headline
    // shape's gaps clear the pull + the thread; the button jumps there.
    const { getByTestId } = withFindings([
      { code: "SATIN_GAPS_TIGHT", severity: "warn", message: "sews its gaps closed at 80 mm",
        extra: { shapes: [{ shape_id: "S1", clear_width_mm: 158 }, { shape_id: "S2", clear_width_mm: 113 }] } }]);
    const box = getByTestId("digitize-fixes");
    expect(box.textContent).toMatch(/Make it bigger/);
    expect(box.textContent).toMatch(/80 → 158 mm wide/);
    expect(box.querySelector(".dgp-fix").title).toMatch(/gaps closed/);
  });

  test("the named width and the 25% step share one button, and the larger target wins either way", () => {
    for (const findings of [
      [{ code: "LETTERING_TOO_SMALL", severity: "warn", message: "a" },
       { code: "SATIN_GAPS_TIGHT", severity: "warn", message: "b", extra: { shapes: [{ shape_id: "S1", clear_width_mm: 158 }] } }],
      [{ code: "SATIN_GAPS_TIGHT", severity: "warn", message: "b", extra: { shapes: [{ shape_id: "S1", clear_width_mm: 158 }] } },
       { code: "LETTERING_TOO_SMALL", severity: "warn", message: "a" }],
    ]) {
      const { container, getByTestId, unmount } = withFindings(findings);
      expect(container.querySelectorAll(".dgp-fix").length).toBe(1);
      expect(getByTestId("digitize-fixes").textContent).toMatch(/80 → 158 mm wide/);
      unmount();
    }
  });

  test("a named width past the ceiling is capped at 400, and none is offered when already there", () => {
    const tight = { code: "SATIN_GAPS_TIGHT", severity: "warn", message: "x",
                    extra: { shapes: [{ shape_id: "S1", clear_width_mm: 620 }] } };
    const capped = withFindings([tight]);
    expect(capped.getByTestId("digitize-fixes").textContent).toMatch(/80 → 400 mm wide/);
    capped.unmount();
    const atLimit = withFindings([tight], { target_width_mm: 400 });
    expect(atLimit.queryByTestId("digitize-fixes")).toBeNull();
  });

  test("lettering the artwork cannot carry jumps to the width the prep's grid could trace, when one is named", () => {
    // 2026-09-30: LETTERING_TOO_SMALL / LETTERING_ILLEGIBLE carry `traced_at_mm`
    // when a low-resolution source lost the lettering (bridge: 118 mm); the
    // same button jumps there. Without it (a source above the prep floor,
    // where a bigger design adds no pixels) the 25% step stays.
    const named = withFindings([{ code: "LETTERING_TOO_SMALL", severity: "warn", message: "lost in tracing",
                                  extra: { traced_at_mm: 118, shapes: [{ shape_id: "S1", column_mm: 0.8, extent_mm: 3.4 }] } }]);
    expect(named.getByTestId("digitize-fixes").textContent).toMatch(/80 → 118 mm wide/);
    named.unmount();
    const step = withFindings([{ code: "LETTERING_ILLEGIBLE", severity: "warn", message: "x",
                                 extra: { traced_at_mm: null, rows: [] } }]);
    expect(step.getByTestId("digitize-fixes").textContent).toMatch(/80 → 100 mm wide/);
  });

  test("a tight-gaps finding with no named width falls back to the 25% step", () => {
    const { getByTestId } = withFindings(
      [{ code: "SATIN_GAPS_TIGHT", severity: "warn", message: "x", extra: { shapes: [] } }]);
    expect(getByTestId("digitize-fixes").textContent).toMatch(/80 → 100 mm wide/);
  });

  test("a fix already at its limit is not offered", () => {
    // "Make it bigger" on a design already at the 400 mm ceiling would do
    // nothing and cost a full re-digitize.
    const { queryByTestId } = withFindings(
      [{ code: "LETTERING_TOO_SMALL", severity: "warn", message: "small" }],
      { target_width_mm: 400 });
    expect(queryByTestId("digitize-fixes")).toBeNull();
  });

  test("pressing one writes the param, so it takes the normal re-digitize path", async () => {
    const patches = [];
    const view = render(Harness, {
      props: {
        element: baseElement([], {
          result: RESULT,
          preflight: { score: 60, grade: "D", metrics: {},
                       findings: [{ code: "COLOR_STOPS_HEAVY", severity: "warn", message: "x" }] },
          params: { target_width_mm: 80, max_colors: 6, satin: true, fill_angle_deg: null,
                    border: null, edge_cap: "none", detail_layer: false },
        }),
        onPatch: (d) => patches.push(d),
      },
    });
    await fireEvent.click(view.container.querySelector(".dgp-fix"));
    expect(patches.at(-1).patch.params.max_colors).toBe(4);
  });
});

describe("what changed since the last run", () => {
  // A re-digitize replaced the design in place with nothing to compare
  // against, so a knob you turned and a knob you only thought you turned
  // looked the same. `priorRun` is written at the one moment the old numbers
  // still exist -- the patch that overwrites them.
  const RESULT = { stitchCount: 2400, widthMM: 50, heightMM: 40, colorCount: 3,
                   stitches: [], colors: [] };

  function withPrior(prior, extra = {}) {
    return render(Harness, {
      props: {
        element: baseElement([], {
          result: RESULT,
          priorRun: prior,
          preflight: { score: 76, grade: "C", findings: [], metrics: { color_changes: 5 } },
          stats: { trims: 20 },
          ...extra,
        }),
        onPatch: () => {},
      },
    });
  }

  test("a FIRST digitize shows no comparison at all", () => {
    // Not "unchanged" -- there is nothing to be different from, and "+0
    // stitches" here would be a lie dressed as information.
    const { queryByTestId } = withPrior(null);
    expect(queryByTestId("digitize-delta")).toBeNull();
  });

  test("it names what moved, in the operator's direction", () => {
    const { getByTestId } = withPrior({
      stitch_count: 2000, color_changes: 3, trims: 26, score: 88, grade: "B",
    });
    const txt = getByTestId("digitize-delta").textContent;
    expect(txt).toMatch(/\+400 stitches/);
    expect(txt).toMatch(/\+2 thread changes/);
    expect(txt).toMatch(/\u22126 trims/);   // fewer trims reads as a minus
    expect(txt).toMatch(/B \u2192 C/);
  });

  test("a re-digitize that changed NOTHING says so — the point of the line", () => {
    // The most useful answer it gives: the setting you just changed did
    // nothing to the stitches. Without it, that is indistinguishable from a
    // run that changed everything.
    const { getByTestId } = withPrior({
      stitch_count: 2400, color_changes: 5, trims: 20, score: 76, grade: "C",
    });
    expect(getByTestId("digitize-delta").textContent).toMatch(/no change/i);
  });

  test("an unchanged figure is omitted rather than printed as zero", () => {
    const { getByTestId } = withPrior({
      stitch_count: 2400, color_changes: 3, trims: 20, score: 76, grade: "C",
    });
    const txt = getByTestId("digitize-delta").textContent;
    expect(txt).toMatch(/\+2 thread changes/);
    expect(txt).not.toMatch(/stitch/);
    expect(txt).not.toMatch(/trim/);
  });

  test("a missing figure on an older stored run is skipped, not treated as 0", () => {
    // priorRun from a job that predates the trims field: reporting "-20
    // trims" would invent a change that never happened.
    const { getByTestId } = withPrior({
      stitch_count: 2000, color_changes: null, trims: null, score: null, grade: null,
    });
    const txt = getByTestId("digitize-delta").textContent;
    expect(txt).toMatch(/\+400 stitches/);
    expect(txt).not.toMatch(/trim/);
    expect(txt).not.toMatch(/thread change/);
  });
});

describe("the Edit shapes disclosure", () => {
  // Renders WITHOUT openLayers on purpose -- this is the state the shared
  // helper opens past, so it is the one thing the other 46 tests cannot see.
  function raw(shapes) {
    const utils = render(Harness, {
      props: { element: baseElement(shapes), onPatch: () => {} },
    });
    // The disclosure lives on the Shapes tab (2026-09-30); this opens the
    // tab and nothing else, so the disclosure's own state is what is seen.
    const tab = [...utils.container.querySelectorAll('button[role="tab"]')]
      .find((b) => b.textContent.trim().startsWith("Shapes"));
    if (tab) fireEvent.click(tab);
    return utils;
  }

  test("the shape rows are closed on arrival", () => {
    const { container } = raw([shapeRow("s1"), shapeRow("s2")]);
    expect(container.querySelector(".dgp-layerlist")).toBeNull();
    expect(container.querySelectorAll(".dgp-layer").length).toBe(0);
  });

  test("it says how many shapes are behind it, so closed is not blind", () => {
    const { container } = raw([shapeRow("s1"), shapeRow("s2"), shapeRow("s3")]);
    const btn = [...container.querySelectorAll("button")]
      .find((b) => /^Edit shapes/.test(b.textContent.trim()));
    expect(btn).toBeTruthy();
    expect(btn.textContent).toMatch(/Edit shapes \(3\)/);
    expect(btn.getAttribute("aria-expanded")).toBe("false");
  });

  test("opening it reveals the rows and flips aria-expanded", async () => {
    const view = raw([shapeRow("s1"), shapeRow("s2")]);
    const btn = [...view.container.querySelectorAll("button")]
      .find((b) => /^Edit shapes/.test(b.textContent.trim()));
    await fireEvent.click(btn);
    expect(view.container.querySelectorAll(".dgp-layer").length).toBe(2);
    expect(btn.getAttribute("aria-expanded")).toBe("true");
  });

  test("the wall of controls is what closing actually removes", () => {
    // The measured complaint: a two-colour logo opened 329 interactive
    // controls. Counting them is the only assertion that would notice the
    // disclosure being reintroduced open, or the rows leaking out of it.
    const rows = Array.from({ length: 6 }, (_, i) => shapeRow("s" + i));
    const closed = raw(rows);
    const closedCount = closed.container.querySelectorAll("button, select, input").length;
    const open = raw(rows);
    const btn = [...open.container.querySelectorAll("button")]
      .find((b) => /^Edit shapes/.test(b.textContent.trim()));
    fireEvent.click(btn);
    const openCount = open.container.querySelectorAll("button, select, input").length;
    expect(openCount).toBeGreaterThan(closedCount * 2);
  });
});

describe("nothing runs until Auto Digitize Image is pressed", () => {
  // Kent, 2026-10-05: the button is the only thing that starts a run, and it
  // goes transparent when the result on the canvas is behind the settings.
  // This block replaces "auto-restitch on shape edits" and "a moved crop box
  // restitches" (his 2026-08-13 / 08-30 rulings, both reversed that day).
  //
  // `digitize` is the network call runDigitize makes; counting it is how a
  // run is observed without a service.
  let cfgs;
  let releases;
  const RESULT = { stitches: [], colors: [], stitchCount: 0, colorCount: 0, name: "t", widthMM: 50, heightMM: 40 };
  beforeEach(() => {
    cfgs = [];
    releases = [];
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // `hold` keeps each run open until its release is called, so a test can
  // act while one is genuinely in flight.
  async function panel(extra = {}, { shapes = [], hold = false } = {}) {
    const mod = await import("../lib/digitizer.js");
    vi.spyOn(mod, "digitize").mockImplementation((_img, cfg) => {
      cfgs.push(cfg);
      const job = { design: { ...RESULT }, warnings: [], review: null, stats: null, preflight: null };
      if (!hold) return Promise.resolve(job);
      return new Promise((resolve) => releases.push(() => resolve(job)));
    });
    const patches = [];
    const utils = render(Harness, {
      props: {
        element: baseElement(shapes, { result: { ...RESULT }, ...extra }),
        health: { ok: true },
        onPatch: (d) => patches.push(d),
      },
    });
    if (shapes.length) openLayers(utils);
    const run = () => utils.container.querySelector(".dgp-run");
    return { ...utils, patches, run };
  }
  const settle = () => vi.advanceTimersByTimeAsync(5000);

  test("a design that just loaded is current: solid button, nothing running", async () => {
    const { run, queryByTestId } = await panel({ crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 } });
    await settle();
    expect(cfgs).toHaveLength(0);
    expect(run()).toHaveTextContent("Auto Digitize Image");
    expect(run()).not.toHaveClass("dgp-run-stale");
    expect(queryByTestId("digitize-stale")).toBeNull();
  });

  test("new artwork does NOT digitize itself — it waits, solid, for the button", async () => {
    const health = { ok: true };
    const utils = await panel({ sourcePng: null, result: null, review: null });
    await utils.rerender({
      element: baseElement([], { sourcePng: "data:image/png;base64,BBBB", result: null, review: null }),
      health,
    });
    await settle();
    expect(cfgs).toHaveLength(0);
    expect(utils.run()).toHaveTextContent("Auto Digitize Image");
    expect(utils.run()).toBeEnabled();
    expect(utils.run()).not.toHaveClass("dgp-run-stale");
  });

  test("pressing it starts exactly one run", async () => {
    const { run } = await panel({ result: null, review: null });
    await fireEvent.click(run());
    await settle();
    expect(cfgs).toHaveLength(1);
  });

  test("a setting changed after a run starts NOTHING and turns the button transparent", async () => {
    const { run, getByLabelText, getByTestId } = await panel();
    await fireEvent.click(getByLabelText(/Satin for thin shapes/));
    await settle();
    expect(cfgs).toHaveLength(0);
    expect(run()).toHaveClass("dgp-run-stale");
    expect(run()).toHaveTextContent("Auto Digitize Image");
    expect(getByTestId("digitize-stale")).toHaveTextContent(/press Auto Digitize Image/);
  });

  test("putting the setting back makes it solid again — no run was ever needed", async () => {
    const { run, getByLabelText } = await panel();
    await fireEvent.click(getByLabelText(/Satin for thin shapes/));
    expect(run()).toHaveClass("dgp-run-stale");
    await fireEvent.click(getByLabelText(/Satin for thin shapes/));
    expect(run()).not.toHaveClass("dgp-run-stale");
    await settle();
    expect(cfgs).toHaveLength(0);
  });

  test("a shape edit starts nothing and turns it transparent", async () => {
    const { run, getByLabelText } = await panel({}, { shapes: [shapeRow("s1")] });
    await fireEvent.change(getByLabelText(/^Stitch type — /), { target: { value: "satin" } });
    await settle();
    expect(cfgs).toHaveLength(0);
    expect(run()).toHaveClass("dgp-run-stale");
  });

  // A border used to be the one edit with no pause at all. It waits for the
  // button like everything else now.
  test("a border change starts nothing either", async () => {
    const { run, getByLabelText } = await panel({}, { shapes: [shapeRow("s1")] });
    await fireEvent.change(getByLabelText(/^Border — /), { target: { value: "auto" } });
    await settle();
    expect(cfgs).toHaveLength(0);
    expect(run()).toHaveClass("dgp-run-stale");
  });

  test("a moved crop box starts nothing and turns it transparent", async () => {
    const { run, getByRole } = await panel({ crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 } });
    await fireEvent.click(getByRole("button", { name: "Use whole image" }));
    await settle();
    expect(cfgs).toHaveLength(0);
    expect(run()).toHaveClass("dgp-run-stale");
  });

  test("the old armed line and its Restitch now button are gone", async () => {
    const { getByLabelText, queryByText } = await panel({}, { shapes: [shapeRow("s1")] });
    await fireEvent.change(getByLabelText(/^Stitch type — /), { target: { value: "satin" } });
    expect(queryByText("Restitch now")).toBeNull();
    expect(queryByText(/restitching when you stop editing/)).toBeNull();
  });

  test("pressing the transparent button runs once WITH the change, and comes back solid", async () => {
    const { run, getByLabelText, patches } = await panel();
    const before = !!baseElement().params.satin;
    await fireEvent.click(getByLabelText(/Satin for thin shapes/));
    await fireEvent.click(run());
    await settle();
    expect(cfgs).toHaveLength(1);
    expect(cfgs[0].satin).toBe(!before);
    expect(patches[patches.length - 1].patch.appliedConfig).toMatch(/^[0-9a-f]{8}$/);
    expect(run()).not.toHaveClass("dgp-run-stale");
    expect(run()).toHaveTextContent("Auto Digitize Image");
  });

  test("a change made WHILE a run is in flight is not in it: one run, and transparent when it lands", async () => {
    const { run, getByLabelText } = await panel({}, { hold: true });
    await fireEvent.click(run());
    await vi.advanceTimersByTimeAsync(0);
    expect(cfgs).toHaveLength(1);
    expect(run()).toBeDisabled();
    expect(run()).toHaveTextContent("Digitizing…");
    await fireEvent.click(getByLabelText(/Satin for thin shapes/));
    releases[0]();
    await settle();
    expect(cfgs).toHaveLength(1);       // no automatic second run behind it
    expect(run()).toBeEnabled();
    expect(run()).toHaveClass("dgp-run-stale");
  });

  // ContentStep remounts the panel per selection. The key is on the element
  // so an unapplied change survives clicking another element and back.
  test("an unapplied change survives a remount", async () => {
    const mod = await import("../lib/digitizer.js");
    const applied = mod.configKey(mod.buildDigitizeConfig(baseElement(), {}));
    const { run } = await panel({
      appliedConfig: applied,
      params: { ...DEFAULT_DIGITIZE_PARAMS, target_width_mm: 123 },
    });
    expect(run()).toHaveClass("dgp-run-stale");
  });
});

// ---- a corner drag on the field is a Design width change -------------------
//
// The field's corner handles SCALE the baked stitches (generate.js passes
// `sizeMm` to buildImportedDesign). Measured in the running Studio 2026-10-08
// on logo_golden_tee.jpg: dragged 80 -> 62 mm, the caption still read 8,764
// stitches — 1.66x the thread per mm² — while the Auto Digitize button stayed
// SOLID, Design width still said 80, and the only word about it sat under the
// fold. Its "Re-digitize at 62 mm" button then put the design BACK at 80 mm
// and ran nothing: it cleared the scale and waited for the automatic re-run
// Kent's 2026-10-05 ruling removed.
describe("a resize on the field", () => {
  let cfgs;
  // 80 x 40 mm as digitized (0.1 mm units), so a sizeMm of 60 is a 75% drag.
  const RESULT = {
    stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 800, y: 400, type: "stitch" }],
    colors: [], stitchCount: 2, colorCount: 1, name: "t", widthMM: 80, heightMM: 40,
  };
  beforeEach(() => { cfgs = []; vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  async function panel(extra = {}) {
    const mod = await import("../lib/digitizer.js");
    const applied = mod.configKey(mod.buildDigitizeConfig(baseElement([], { result: RESULT }), {}));
    vi.spyOn(mod, "digitize").mockImplementation((_img, cfg) => {
      cfgs.push(cfg);
      return Promise.resolve({ design: { ...RESULT }, warnings: [], review: null, stats: null, preflight: null });
    });
    const patches = [];
    const utils = render(Harness, {
      props: {
        element: baseElement([], { result: RESULT, appliedConfig: applied, ...extra }),
        health: { ok: true },
        onPatch: (d) => patches.push(d),
      },
    });
    const run = () => utils.container.querySelector(".dgp-run");
    const width = () => utils.getByLabelText(/Design width/);
    return { ...utils, patches, run, width };
  }
  const settle = () => vi.advanceTimersByTimeAsync(5000);

  test("at its digitized size the design is current", async () => {
    const { run, width } = await panel({ sizeMm: 80 });
    expect(run()).not.toHaveClass("dgp-run-stale");
    expect(width()).toHaveValue(80);
  });

  test("a drag turns the button transparent, says so, and Design width shows the dragged width", async () => {
    const { run, width, getByTestId } = await panel({ sizeMm: 60 });
    await settle();
    expect(cfgs).toHaveLength(0);                       // still nothing runs on its own
    expect(run()).toHaveClass("dgp-run-stale");
    expect(width()).toHaveValue(60);
    expect(getByTestId("digitize-stale")).toHaveTextContent(/Resized to 60 mm/);
  });

  test("Auto Digitize Image runs AT the dragged width and the scale goes on landing", async () => {
    const { run, patches } = await panel({ sizeMm: 60 });
    await fireEvent.click(run());
    await settle();
    expect(cfgs).toHaveLength(1);
    expect(cfgs[0].target_width_mm).toBe(60);
    const last = patches[patches.length - 1].patch;
    expect(last.sizeMm).toBeNull();
    expect(last.params.target_width_mm).toBe(60);
    expect(run()).not.toHaveClass("dgp-run-stale");
  });

  test("Re-digitize at N mm RUNS, and never puts the design back at its old size first", async () => {
    const { getByRole, patches } = await panel({ sizeMm: 60 });
    await fireEvent.click(getByRole("button", { name: "Re-digitize at 60 mm" }));
    await settle();
    expect(cfgs).toHaveLength(1);
    expect(cfgs[0].target_width_mm).toBe(60);
    // The one patch is the landing: no earlier patch dropped the scale while
    // the old 80 mm stitches were still the result.
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.result).toBeTruthy();
    expect(patches[0].patch.sizeMm).toBeNull();
  });

  test("a typed width replaces the dragged one", async () => {
    const { width, patches } = await panel({ sizeMm: 60 });
    await fireEvent.change(width(), { target: { value: "70" } });
    const last = patches[patches.length - 1].patch;
    expect(last.params.target_width_mm).toBe(70);
    expect(last.sizeMm).toBeNull();
  });
});

describe("a file picked before the element existed", () => {
  beforeEach(() => {
    fakeStore.clear();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage() {} });
    vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue("data:image/png;base64,AAAA");
    loadImageResult = () => Promise.resolve({ width: 1400, height: 316 });
  });
  afterEach(() => vi.restoreAllMocks());

  test("is ingested on mount, reported consumed, and does not start a run", async () => {
    const mod = await import("../lib/digitizer.js");
    const runs = [];
    vi.spyOn(mod, "digitize").mockImplementation(async () => { runs.push(1); return null; });
    const patches = [];
    let consumed = 0;
    const { container } = render(Harness, {
      props: {
        element: baseElement([], { sourcePng: null, result: null, review: null }),
        health: { ok: true },
        pendingFile: new File([new Uint8Array([1, 2, 3])], "picked.png", { type: "image/png" }),
        onFileConsumed: () => { consumed += 1; },
        onPatch: (d) => patches.push(d),
      },
    });
    await waitFor(() => expect(patches.length).toBeGreaterThanOrEqual(1));
    expect(consumed).toBe(1);
    expect(patches[0].patch.sourcePng).toBe("AAAA");
    expect(patches[0].patch.name).toBe("picked.png");
    await waitFor(() => expect(container.querySelector(".dgp-run")).toBeEnabled());
    expect(runs).toHaveLength(0);
  });
});

// ---- the upload error, on a panel that has no artwork yet ------------------
//
// `{#if error}` used to sit beside the Digitize button, which lives in the
// `{:else}` arm of `{#if !element.sourcePng}` — so it could only ever render
// once artwork had ALREADY loaded. A file that fails to decode never sets
// `sourcePng`, so `onFile` set the message and the template had no way to show
// it. Measured 2026-09-07 by dropping a .txt on a fresh panel: `error` set,
// unchanged empty state on screen.
//
// The case that stayed silent is the one where the user has nothing to look at
// and no reason to think the app is working; the case that spoke is the one
// where their artwork is still on screen. Exactly backwards.
describe("a file that cannot be decoded", () => {
  test("says so on a FRESH panel, where there is no artwork to explain the silence", async () => {
    loadImageResult = () => Promise.reject(new Error("Couldn’t read that file as an image."));
    const { container, findByRole } = render(Harness, {
      props: { element: baseElement([], { sourcePng: null, result: null, review: null }) },
    });
    const input = container.querySelector('.dgp-upload input[type="file"]');
    Object.defineProperty(input, "files", {
      value: [new File(["nope"], "logo.pdf", { type: "application/pdf" })],
    });
    await fireEvent.change(input);

    const alert = await findByRole("alert");
    expect(alert).toHaveTextContent(/Couldn’t read that file as an image/);
    // Still no artwork — the message is the ONLY thing that changed, which is
    // the whole point: the empty-upload state must be able to carry it.
    expect(container.querySelector(".dgp-stats")).toBeNull();
  });

  test("and still says so when REPLACING artwork that already loaded", async () => {
    loadImageResult = () => Promise.reject(new Error("Couldn’t read that file as an image."));
    const { container, findByRole } = render(Harness, { props: { element: baseElement([]) } });
    const input = container.querySelector('.dgp-upload input[type="file"]');
    Object.defineProperty(input, "files", {
      value: [new File(["nope"], "logo.pdf", { type: "application/pdf" })],
    });
    await fireEvent.change(input);
    expect(await findByRole("alert")).toHaveTextContent(/Couldn’t read that file as an image/);
  });
});

// ---- the border readout ----------------------------------------------------
//
// Kent, 2026-09-15: "easier to identify when a satin border is or isn't
// generated and what it looks like going back and forth between satin border
// on/off". The panel used to read `params.border` / `shapeOverrides[sid]
// .border` straight back and call that the answer; the engine declines in
// three different ways and none of them were visible. These tests are about
// the gap: the request is the input, `design.runs` is the truth, and the panel
// must never print the first as if it were the second.
//
// The decision table itself is tested browser-free in lib/borderMenu.spec.js;
// what is checked here is that the panel feeds it the right things (the
// EMITTED tier, not a forced one; the per-shape override; the design param)
// and renders both halves.
describe("border readout — what sewed, not what was asked for", () => {
  function resultWith(runs) {
    const base = {
      stitchCount: 100, widthMM: 50, heightMM: 50, colorCount: 1,
      colors: [], stitches: [],
    };
    return runs === null ? base : { ...base, runs };
  }
  const run = (shape, kind, role = "") => ({ i0: 0, i1: 0, kind, shape, role, block: 0 });

  // Three shapes, one of each interesting outcome, with the design-wide
  // Border select on: s1 gets its satin column, s2 is too narrow and gets a
  // bean run, s3 is asked for one and the engine adds none.
  const SHAPES = [shapeRow("s1"), shapeRow("s2"), shapeRow("s3")];
  const RUNS = [
    run("s1", "fill"), run("s1", "satin", "border"),
    run("s2", "fill"), run("s2", "run", "border"),
    run("s3", "fill"),
  ];

  function panelWithRuns(runs = RUNS, extra = {}) {
    return renderPanel(SHAPES, {
      params: { ...DEFAULT_DIGITIZE_PARAMS, border: "auto" },
      result: resultWith(runs),
      ...extra,
    });
  }

  test("counts what is on the cloth, and names the declines", () => {
    const { getByText } = panelWithRuns();
    expect(getByText("2 of 3 borders sewn (1 satin, 1 bean) · 1 not generated.")).toBeTruthy();
  });

  test("with NO runs in the payload it says requested, and never says sewn", () => {
    const { getByText, queryByText } = panelWithRuns(null);
    expect(getByText(/3 shapes asking for a border/)).toBeTruthy();
    expect(getByText(/the request, not the cloth/)).toBeTruthy();
    expect(queryByText(/sewn \(/)).toBeNull();
  });

  test("toggling the design Border select moves the numbers — the whole ask", async () => {
    const { getByText, getByLabelText, queryByText } = panelWithRuns();
    expect(getByText(/2 of 3 borders sewn/)).toBeTruthy();
    await fireEvent.change(getByLabelText("Border"), { target: { value: "off" } });
    expect(queryByText(/2 of 3 borders sewn/)).toBeNull();
    expect(getByText(/^No shape borders/)).toBeTruthy();
    // ...and back again, off the same evidence
    await fireEvent.change(getByLabelText("Border"), { target: { value: "auto" } });
    expect(getByText(/2 of 3 borders sewn/)).toBeTruthy();
  });

  test("a per-shape override is counted the way the engine reads it", async () => {
    const { getByText, getByLabelText } = panelWithRuns();
    const sel = getByLabelText(/^Border — shape 1 of 3/);   // s1's own row
    await fireEvent.change(sel, { target: { value: "off" } });
    expect(getByText(/1 of 2 borders sewn \(1 bean\)/)).toBeTruthy();
  });

  test("each row is badged with the border it actually has", () => {
    const { container } = panelWithRuns();
    const badges = [...container.querySelectorAll(".dgp-lborder")].map((b) => b.textContent.trim());
    expect(badges).toEqual(["satin border", "bean border", "no border sewn"]);
  });

  test("the declined badge explains itself without inventing a cause", () => {
    const { container } = panelWithRuns();
    const declined = container.querySelector(".dgp-lborder-warn");
    expect(declined.getAttribute("title")).toMatch(/did not add one/);
    expect(declined.getAttribute("title")).toMatch(/too narrow to hold one/);
    expect(declined.getAttribute("title")).toMatch(/would be a guess/);
  });

  test("an expected decline is NOT painted as a fault", () => {
    // The engine declining a satin-tiered shape is it working as documented.
    // Toning that off `state` alone turned three of four rows red on the first
    // real design this was driven on, which is how a healthy design comes to
    // look broken.
    const { container } = renderPanel([shapeRow("sat", { tier: "satin" })], {
      params: { ...DEFAULT_DIGITIZE_PARAMS, border: "auto" },
      result: resultWith(RUNS),
    });
    expect(container.querySelector(".dgp-lborder-warn")).toBeNull();
    expect(container.querySelector(".dgp-lborder-quiet")).toBeTruthy();
  });

  test("a satin-tiered shape says WHY, and says it with no runs to check", () => {
    for (const runs of [RUNS, null]) {
      const { container } = renderPanel([shapeRow("sat", { tier: "satin" })], {
        params: { ...DEFAULT_DIGITIZE_PARAMS, border: "auto" },
        result: resultWith(runs),
      });
      const badge = container.querySelector(".dgp-lborder");
      expect(badge.textContent.trim()).toBe("no border — sews as satin");
      expect(badge.getAttribute("title")).toMatch(/already an outline/);
    }
  });

  test("a row nobody asked to border carries no badge — the list stays readable", () => {
    const { container } = renderPanel(SHAPES, { result: resultWith(RUNS) });
    expect(container.querySelectorAll(".dgp-lborder")).toHaveLength(0);
  });

  test("a just-toggled row reads PENDING, and only that row does", async () => {
    const { container, getByLabelText } = panelWithRuns(RUNS, {
      // as if the current stitches were made with s1 bordered and nothing else set
      appliedEdits: JSON.stringify([[], { s1: { border: "auto" } }, [], {}]),
    });
    await fireEvent.change(getByLabelText(/^Border — shape 1 of 3/), { target: { value: "bean" } });
    const badges = [...container.querySelectorAll(".dgp-lborder")].map((b) => b.textContent.trim());
    expect(badges[0]).toBe("border pending");
    expect(badges.slice(1)).toEqual(["bean border", "no border sewn"]);
  });

  test("the design edge reports the engine's own bill", () => {
    const { getByText } = renderPanel(SHAPES, {
      result: resultWith(RUNS),
      warnings: [{ code: "EDGE_CAP_APPLIED", stitches: 1204, percent: 21.3, edges: 1 }],
    });
    expect(getByText("Bean edge sewn — 1,204 stitches (+21.3% of the design).")).toBeTruthy();
  });

  test("the design edge says when it found nothing to sew", () => {
    const { getByText } = renderPanel(SHAPES, {
      result: resultWith(RUNS),        // runs present, none of them edge_cap
      warnings: [],
    });
    expect(getByText("Design edge found nothing to sew.")).toBeTruthy();
  });

  test("switching the design edge off says so rather than staying silent", async () => {
    const { getByText, getByLabelText } = renderPanel(SHAPES, { result: resultWith(RUNS) });
    await fireEvent.change(getByLabelText("Design edge"), { target: { value: "none" } });
    expect(getByText("Design edge off.")).toBeTruthy();
  });
});

// ---- what the upload STORES and what a digitize SENDS (2026-09-20) --------
//
// The panel used to send its 1,200-px canvas PNG to the service; it now
// stores the file's own bytes (lib/sourceStore.js) and sends THOSE, keeping
// the canvas as the preview. jsdom has neither a canvas nor IndexedDB, so
// both are stood in for: the canvas by a stub returning a fixed data URL,
// the store by an in-memory map through vi.mock. `loadImage` is the same
// controlled stub the file banner describes.
const { fakeStore } = vi.hoisted(() => ({ fakeStore: new Map() }));
vi.mock("../lib/sourceStore.js", () => ({
  sourceStoreAvailable: () => true,
  sourceKeyFor: async (bytes) => "key-" + bytes.length,
  putSource: async (key, rec) => { fakeStore.set(key, rec); },
  getSource: async (key) => fakeStore.get(key) || null,
  deleteSource: async (key) => { fakeStore.delete(key); },
}));

const { proposeCropMock } = vi.hoisted(() => ({ proposeCropMock: vi.fn(() => null) }));
vi.mock("../lib/cropProposal.js", () => ({ proposeCrop: proposeCropMock }));

describe("the upload proposes a crop", () => {
  beforeEach(() => {
    fakeStore.clear();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      drawImage() {},
      getImageData: () => ({ width: 10, height: 10, data: new Uint8ClampedArray(400) }),
    });
    vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue("data:image/png;base64,AAAA");
    loadImageResult = () => Promise.resolve({ width: 1400, height: 316 });
  });
  afterEach(() => vi.restoreAllMocks());

  test("the patch carries proposeCrop's rectangle, measured with the target width", async () => {
    const proposal = { x0: 0.1, y0: 0.1, x1: 0.9, y1: 0.9 };
    proposeCropMock.mockClear();
    proposeCropMock.mockReturnValue(proposal);
    const patches = [];
    const { container } = render(Harness, {
      props: {
        element: baseElement([], { sourcePng: null, result: null, review: null }),
        health: { ok: true, limits: { max_upload_bytes: 12 * 1024 * 1024, max_pixels: 40_000_000 } },
        onPatch: (d) => patches.push(d),
      },
    });
    const input = container.querySelector('.dgp-upload input[type="file"]');
    Object.defineProperty(input, "files", { value: [new File([new Uint8Array([1, 2, 3])], "l.png", { type: "image/png" })] });
    await fireEvent.change(input);
    await waitFor(() => expect(patches.length).toBeGreaterThanOrEqual(1));
    expect(patches[0].patch.crop).toEqual(proposal);
    expect(proposeCropMock.mock.calls[0][1]).toBeGreaterThan(0);
    proposeCropMock.mockReturnValue(null);
  });
});

describe("the crop box's drag floor tracks the preview raster", () => {
  // The service refuses a crop under 16 px on either axis. On a 100 x 100
  // preview that is 16%, far above CropBox's own 2% default.
  function pngB64(width, height) {
    const b = new Uint8Array(24);
    b.set([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13, 0x49, 0x48, 0x44, 0x52], 0);
    new DataView(b.buffer).setUint32(16, width);
    new DataView(b.buffer).setUint32(20, height);
    return Buffer.from(b).toString("base64");
  }
  function ptr(type, x, y) {
    const e = new Event(type, { bubbles: true, cancelable: true });
    e.clientX = x; e.clientY = y;
    return e;
  }
  afterEach(() => vi.restoreAllMocks());

  async function dragRightEdgeToTenPercent(sourcePng) {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 200, bottom: 100, width: 200, height: 100, x: 0, y: 0,
    });
    const patches = [];
    const { getByRole } = render(Harness, {
      props: {
        element: baseElement([], { sourcePng, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 } }),
        onPatch: (d) => patches.push(d.patch),
      },
    });
    getByRole("button", { name: "Drag right edge" }).dispatchEvent(ptr("pointerdown", 160, 50));
    // -100 px of 200: x1 0.8 -> 0.3, a 0.1-wide box.
    window.dispatchEvent(ptr("pointermove", 60, 50));
    window.dispatchEvent(ptr("pointerup", 60, 50));
    return patches.filter((p) => "crop" in p);
  }

  test("a 100 px preview refuses a box 10 px wide", async () => {
    expect(await dragRightEdgeToTenPercent(pngB64(100, 100))).toHaveLength(0);
  });

  test("a 1200 px preview allows the same drag (120 px)", async () => {
    const got = await dragRightEdgeToTenPercent(pngB64(1200, 1200));
    expect(got).toHaveLength(1);
    expect(got[0].crop.x1).toBeCloseTo(0.3);
  });
});

describe("the upload stores the file and a digitize sends it", () => {
  const LIMITS = { max_upload_bytes: 12 * 1024 * 1024, max_pixels: 40_000_000 };
  beforeEach(() => {
    fakeStore.clear();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage() {} });
    vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue("data:image/png;base64,AAAA");
    loadImageResult = () => Promise.resolve({ width: 1400, height: 316 });
  });
  afterEach(() => vi.restoreAllMocks());

  async function upload(container, file) {
    const input = container.querySelector('.dgp-upload input[type="file"]');
    Object.defineProperty(input, "files", { value: [file] });
    await fireEvent.change(input);
  }

  test("a PNG is stored under its content key; the element carries the key and the preview, never the bytes", async () => {
    const patches = [];
    const { container } = render(Harness, {
      props: {
        element: baseElement([], { sourcePng: null, result: null, review: null }),
        health: { ok: true, limits: LIMITS },
        onPatch: (d) => patches.push(d),
      },
    });
    const bytes = new Uint8Array([137, 80, 78, 71, 9, 9, 9]);
    await upload(container, new File([bytes], "logo.png", { type: "image/png" }));
    await waitFor(() => expect(patches.length).toBeGreaterThanOrEqual(1));
    const p = patches[0].patch;
    expect(p.sourcePng).toBe("AAAA");
    expect(p.name).toBe("logo.png");
    expect(p.sourceFile).toEqual({ key: "key-7", type: "image/png", size: 7, width: 1400, height: 316 });
    expect(fakeStore.get("key-7")).toEqual({ bytes, type: "image/png", name: "logo.png" });
    expect(JSON.stringify(p)).not.toContain('"bytes"');
  });

  test("an SVG keeps the preview path — nothing stored, sourceFile null — because only a browser rasterises it", async () => {
    const patches = [];
    const { container } = render(Harness, {
      props: {
        element: baseElement([], { sourcePng: null, result: null, review: null }),
        health: { ok: true, limits: LIMITS },
        onPatch: (d) => patches.push(d),
      },
    });
    await upload(container, new File(["<svg xmlns='http://www.w3.org/2000/svg'/>"], "logo.svg", { type: "image/svg+xml" }));
    await waitFor(() => expect(patches.length).toBeGreaterThanOrEqual(1));
    expect(patches[0].patch.sourcePng).toBe("AAAA");
    expect(patches[0].patch.sourceFile).toBeNull();
    expect(fakeStore.size).toBe(0);
  });

  test("a digitize sends the stored bytes while they are there, and the preview — saying so — once they are gone", async () => {
    const mod = await import("../lib/digitizer.js");
    const sent = [];
    vi.spyOn(mod, "digitize").mockImplementation(async (image) => { sent.push(image); return null; });
    const bytes = new Uint8Array([82, 73, 70, 70]);
    fakeStore.set("k9", { bytes, type: "image/webp", name: "logo.webp" });
    const { getByRole, queryByTestId, findByTestId } = render(Harness, {
      props: {
        element: baseElement([], { name: "logo.webp", sourceFile: { key: "k9", type: "image/webp", size: 4, width: 10, height: 10 } }),
        health: { ok: true, limits: LIMITS },
      },
    });
    await fireEvent.click(getByRole("button", { name: "Auto Digitize Image" }));
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toEqual({ bytes, type: "image/webp", name: "logo.webp" });
    expect(queryByTestId("source-note")).toBeNull();

    // Cleared site data, another browser: the original is gone. The preview
    // goes up (the pre-2026-09-20 result) and the panel says which one this is.
    fakeStore.clear();
    await fireEvent.click(getByRole("button", { name: "Auto Digitize Image" }));
    await waitFor(() => expect(sent).toHaveLength(2));
    expect(sent[1]).toBe("data:image/png;base64,AAAA");
    expect(await findByTestId("source-note")).toHaveTextContent(/original file is no longer stored/);
  });
});

// ---- The list <-> canvas shape sync (2026-09-30) ----------------------------
// The canvas half (the outline drawn, the amber selection applied) is pinned
// in e2e/field-panel-sync.spec.js against the live service; this is the
// list's half: what a row sends, and what it shows for what it is sent.
describe("list <-> canvas shape sync", () => {
  test("hovering a row sends its shape id, leaving it sends null", async () => {
    const hovers = [];
    const utils = render(Harness, {
      props: { element: baseElement([shapeRow("s1"), shapeRow("s2")]), onShapeHover: (d) => hovers.push(d) },
    });
    openLayers(utils);
    const rows = utils.container.querySelectorAll(".dgp-layer");
    expect(rows).toHaveLength(2);
    await fireEvent.mouseEnter(rows[1]);
    await fireEvent.mouseLeave(rows[1]);
    expect(hovers).toEqual(["s2", null]);
  });

  test("clicking a sewing row's name sends its shape id; hidden and deleted rows have no name button", async () => {
    const picks = [];
    const utils = render(Harness, {
      props: {
        element: baseElement(
          [shapeRow("live"), shapeRow("off", { stitched: false }), shapeRow("gone")],
          { deletedShapeIds: ["gone"] },
        ),
        onShapeSelect: (d) => picks.push(d),
      },
    });
    openLayers(utils);
    const btns = utils.container.querySelectorAll(".dgp-lname-btn");
    expect(btns).toHaveLength(1);
    expect(btns[0]).toHaveAttribute("aria-label", expect.stringMatching(/^Show .* on the canvas$/));
    await fireEvent.click(btns[0]);
    expect(picks).toEqual(["live"]);
    // Nothing else was patched by the click — selection is App's state, not
    // the element's.
    expect(utils.container.querySelector(".dgp-layer-sel")).toBeNull();
  });

  test("the hovered and selected ids mark their rows, and a selection opens the closed list", async () => {
    const utils = render(Harness, {
      props: { element: baseElement([shapeRow("a"), shapeRow("b")]), hoverShapeId: "a" },
    });
    // Closed by default: no rows at all yet.
    expect(utils.container.querySelectorAll(".dgp-layer")).toHaveLength(0);
    await utils.rerender({ element: baseElement([shapeRow("a"), shapeRow("b")]), hoverShapeId: "a", selectedShapeId: "b" });
    await waitFor(() => expect(utils.container.querySelectorAll(".dgp-layer")).toHaveLength(2));
    const rows = utils.container.querySelectorAll(".dgp-layer");
    expect(rows[0]).toHaveClass("dgp-layer-hover");
    expect(rows[0]).not.toHaveClass("dgp-layer-sel");
    expect(rows[1]).toHaveClass("dgp-layer-sel");
    expect(rows[1]).toHaveAttribute("data-shape-id", "b");
  });
});

// ---- The three tabs (2026-09-30) ---------------------------------------------
describe("Settings / Shapes / Threads", () => {
  function tabs(container) {
    return [...container.querySelectorAll('button[role="tab"]')];
  }
  function tabNamed(container, name) {
    return tabs(container).find((b) => b.textContent.trim().startsWith(name));
  }

  test("opens on Settings: the knobs and Rotation, no Layers block, no spool list", () => {
    const { container } = render(Harness, { props: { element: baseElement([shapeRow("s1")]) } });
    expect(tabs(container).map((b) => b.getAttribute("aria-selected"))).toEqual(["true", "false", "false"]);
    // Names are the plain words: the counts are aria-hidden.
    expect(tabs(container).map((b) => b.textContent.replace(/\d+/g, "").trim())).toEqual(["Settings", "Shapes", "Threads"]);
    expect(container.querySelector(".dgp-params")).not.toBeNull();
    expect(container.querySelector(".dgp-layers")).toBeNull();
    expect(container.querySelector(".dgp-blocks")).toBeNull();
    expect([...container.querySelectorAll("label")].some((l) => /Rotation/.test(l.textContent))).toBe(true);
  });

  test("Shapes shows the Layers block and its count; Threads shows the spools; the knobs stay on Settings", async () => {
    const { container } = render(Harness, { props: { element: baseElement([shapeRow("s1"), shapeRow("s2")]) } });
    expect(tabNamed(container, "Shapes").querySelector(".dgp-tab-count")).toHaveTextContent("2");
    await fireEvent.click(tabNamed(container, "Shapes"));
    expect(container.querySelector(".dgp-layers")).not.toBeNull();
    expect(container.querySelector(".dgp-blocks")).toBeNull();
    await fireEvent.click(tabNamed(container, "Threads"));
    expect(container.querySelector(".dgp-layers")).toBeNull();
    expect(container.querySelector(".dgp-blocks")).not.toBeNull();
    expect(container.querySelector(".dgp-params")).not.toBeNull(); // the knobs are above the tabs
  });

  test("a shape selected on the canvas switches to Shapes and opens the list", async () => {
    const utils = render(Harness, { props: { element: baseElement([shapeRow("a"), shapeRow("b")]) } });
    expect(tabNamed(utils.container, "Settings").getAttribute("aria-selected")).toBe("true");
    await utils.rerender({ element: baseElement([shapeRow("a"), shapeRow("b")]), selectedShapeId: "b" });
    await waitFor(() => expect(utils.container.querySelectorAll(".dgp-layer")).toHaveLength(2));
    expect(tabNamed(utils.container, "Shapes").getAttribute("aria-selected")).toBe("true");
    expect(utils.container.querySelector(".dgp-layer-sel")).toHaveAttribute("data-shape-id", "b");
  });

  test("Threads lists spools, not sew blocks: a cone loaded twice is one row, and a pick recolors both blocks", async () => {
    const patches = [];
    const element = baseElement([shapeRow("s1")], {
      result: {
        stitchCount: 100, widthMM: 10, heightMM: 10, colorCount: 2, stitches: [],
        colors: [
          { r: 20, g: 20, b: 20, name: "0134 Smoky" },
          { r: 200, g: 30, b: 30, name: "1720 Not Quite Red" },
          { r: 200, g: 30, b: 30, name: "1720 Not Quite Red" },
        ],
      },
    });
    const { container } = render(Harness, { props: { element, onPatch: (d) => patches.push(d) } });
    await fireEvent.click(tabNamed(container, "Threads"));
    const rows = [...container.querySelectorAll(".dgp-block")];
    expect(rows.map((r) => r.querySelector(".dgp-block-n").textContent)).toEqual(["0134 Smoky", "1720 Not Quite Red"]);
    expect(rows[1].querySelector(".dgp-block-note")).toHaveTextContent("loaded 2 times");
    expect(rows[0].querySelector(".dgp-block-note")).toBeNull();
    expect(tabNamed(container, "Threads").querySelector(".dgp-tab-count")).toHaveTextContent("2");
  });
});
