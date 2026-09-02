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
// a job already ran) and never touches `element.params`, so the "re-digitize
// automatically when params change" reactive statement never fires and no
// network call happens.
import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./DigitizePanel.testHarness.svelte";
import { DEFAULT_DIGITIZE_PARAMS } from "../lib/project.js";

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
  const btn = utils.container.querySelector('button[aria-expanded][class*="seq-toggle"]');
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

  test("present on a user-declared photo, whose reading carries no warning at all", () => {
    // The override path, not the engine's: isPhoto forces the tonal lane, and
    // the forced row has no CLASSIFIED_* warning to read.
    const { getByLabelText } = renderPanel([shapeRow("s1")], { isPhoto: true, warnings: [] });
    expect(getByLabelText("Add fine detail lines")).toBeTruthy();
  });

  test("absent under a forced-FLAT override, even if the engine had read it as a photo", () => {
    const { queryByLabelText } = renderPanel([shapeRow("s1")], {
      ...TONAL,
      params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat" },
    });
    expect(queryByLabelText("Add fine detail lines")).toBeNull();
  });
});

// ---- what the art was read as, and correcting it ---------------------------
//
// Stage 0 classifies every job on its own (flat / gradient / photo_subject /
// photo_scene). This row is Studio finally SAYING so in plain words, with the
// override recast as a correction to that sentence instead of a question asked
// before anything has been digitized -- Kent 2026-08-30, "choose flat work,
// real photo etc. IDK what ANY of that even means".
//
// What gets SENT is unchanged, and these tests hold that line: "It's flat art"
// still writes forced_class=flat, "It's a photo" still sets isPhoto (which
// buildDigitizeConfig turns into forced_class=photo_subject -- see
// digitizer.spec.js's precedence test).
//
// `health` stays null here (renderPanel's default), so the reactive re-run
// bails at runDigitize's own `!health` guard and no digitize is attempted --
// same no-service posture as the rest of this file, and the reason these
// assert on the PATCH rather than on a network call.
//
// The flat correction is scoped to FLAT-COLOR art on purpose and the copy has
// to keep saying so: forcing flat on genuinely TEXTURED logo art measured
// WORSE (k-means shatters the texture into confetti), so "no shading or photo
// texture" is load-bearing, not padding.
describe("the reading row -- correcting a photo/gradient reading to flat", () => {
  const MISROUTE_CODES = [
    "CLASSIFIED_PHOTO_SUBJECT", "CLASSIFIED_PHOTO_SCENE", "CLASSIFIED_GRADIENT",
  ];

  function panelWarnedAs(code, extra = {}) {
    return renderPanel([shapeRow("s1")], {
      warnings: [{ code, message: "engine prose" }],
      ...extra,
    });
  }

  for (const code of MISROUTE_CODES) {
    test(`offers the flat correction on ${code}`, () => {
      const { getByRole, getByText } = panelWarnedAs(code);
      expect(getByRole("button", { name: "It's flat art" })).toBeTruthy();
      // The texture caveat, not just the button.
      expect(getByText(/no shading or photo texture/)).toBeTruthy();
    });
  }

  test("a flat reading states itself and offers the OTHER direction instead", () => {
    // Was "stays silent for a flat result whose warnings are about something
    // else". It no longer stays silent -- saying what the art was read as is
    // the point of the row -- but the FLAT correction is still absent, which
    // is what that test was actually protecting.
    const { queryByRole, getByRole, getByText } = panelWarnedAs("COLOR_CAP_APPLIED");
    expect(queryByRole("button", { name: "It's flat art" })).toBeNull();
    expect(getByText(/Read as flat art/)).toBeTruthy();
    expect(getByRole("button", { name: "It's a photo" })).toBeTruthy();
  });

  test("an uncertain classification says so rather than claiming a reading", () => {
    const { getByText, getByRole } = panelWarnedAs("CLASSIFICATION_UNCERTAIN");
    expect(getByText(/Couldn't tell what this artwork is/)).toBeTruthy();
    expect(getByRole("button", { name: "It's a photo" })).toBeTruthy();
  });

  test("stays silent once the override is already set -- offering it twice is nonsense", () => {
    const { queryByRole } = panelWarnedAs("CLASSIFIED_PHOTO_SUBJECT", {
      params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat" },
    });
    expect(queryByRole("button", { name: "It's flat art" })).toBeNull();
  });

  test("says nothing about a reading before the first run has produced one", () => {
    const { queryByText, queryByRole } = renderPanel([shapeRow("s1")], { result: null });
    expect(queryByText(/Read as/)).toBeNull();
    expect(queryByRole("button", { name: "It's a photo" })).toBeNull();
  });

  test("taking the correction writes forced_class in exactly one params patch (one undo step)", async () => {
    const { getByRole, patches } = panelWarnedAs("CLASSIFIED_PHOTO_SUBJECT");
    await fireEvent.click(getByRole("button", { name: "It's flat art" }));
    expect(patches).toHaveLength(1);
    expect(Object.keys(patches[0].patch)).toEqual(["params"]);
    expect(patches[0].patch.params.forced_class).toBe("flat");
    // A params patch replaces the whole object -- dropping a sibling here would
    // silently reset the design's width/colors along with the override.
    expect(patches[0].patch.params.max_colors).toBe(DEFAULT_DIGITIZE_PARAMS.max_colors);
    expect(patches[0].patch.params.target_width_mm).toBe(DEFAULT_DIGITIZE_PARAMS.target_width_mm);
  });
});

describe("the reading row -- a standing override, and going back to automatic", () => {
  const FORCED = { params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat" } };

  test("a standing row says the design is being forced, with no warning left to hang it off", () => {
    // The point of "standing": after the forced re-digitize the art classifies
    // as flat and the CLASSIFIED_* warning is GONE. If the row hung off the
    // warning, the override would become invisible and permanent one run after
    // the user set it. Hence `warnings: []` here.
    const { getByText, getByRole } = renderPanel([shapeRow("s1")], { ...FORCED, warnings: [] });
    expect(getByText("You set this to flat art.")).toBeTruthy();
    expect(getByRole("button", { name: "Use automatic detection" })).toBeTruthy();
  });

  test("absent entirely when no override is set", () => {
    const { queryByText, queryByRole } = renderPanel([shapeRow("s1")]);
    expect(queryByText(/^You set this to/)).toBeNull();
    expect(queryByRole("button", { name: "Use automatic detection" })).toBeNull();
  });

  test("reverting DELETES the key rather than nulling it, in one patch", async () => {
    // Deleted, not set to null: the params object has to come back byte-
    // identical to a design that never overrode anything, or the service's job
    // cache key differs and the revert re-runs a job it already has.
    const { getByRole, patches } = renderPanel([shapeRow("s1")], FORCED);
    await fireEvent.click(getByRole("button", { name: "Use automatic detection" }));
    expect(patches).toHaveLength(1);
    expect(Object.keys(patches[0].patch)).toEqual(["params"]);
    expect("forced_class" in patches[0].patch.params).toBe(false);
    expect(patches[0].patch.params).toEqual({ ...DEFAULT_DIGITIZE_PARAMS });
  });

  test("a standing PHOTO override reads the same way, and reverting clears isPhoto alone", async () => {
    // isPhoto lives on the element, not in params, so reverting it must not
    // manufacture a params patch -- that would change the job cache key on a
    // design whose params never moved.
    const { getByText, getByRole, patches } = renderPanel([shapeRow("s1")], { isPhoto: true });
    expect(getByText("You set this to a photo.")).toBeTruthy();
    await fireEvent.click(getByRole("button", { name: "Use automatic detection" }));
    expect(patches).toHaveLength(1);
    expect(Object.keys(patches[0].patch)).toEqual(["isPhoto"]);
    expect(patches[0].patch.isPhoto).toBe(false);
  });
});

// Controller ruling 2026-08-19 (fix round 1, Important 2): declaring the art a
// photo while a flat-art override is standing left the config and the row
// disagreeing -- buildDigitizeConfig sends photo_subject (isPhoto wins, see
// digitizer.spec.js's precedence test) while the row read only
// params.forced_class and kept saying flat. Fixed at the source: the handler
// clears params.forced_class in the SAME patch. The row now also resolves
// isPhoto first, so the two cannot disagree even if a patch ever left both set.
describe("the reading row -- \"It's a photo\" from a standing flat override", () => {
  const FORCED = { params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat" } };

  test("clears forced_class in the same patch, and the row stops saying flat", async () => {
    const { getByRole, getByText, queryByText, patches } = renderPanel([shapeRow("s1")], FORCED);
    // Sanity on the starting contradiction this fix removes.
    expect(getByText("You set this to flat art.")).toBeTruthy();

    await fireEvent.click(getByRole("button", { name: "It's a photo" }));
    expect(patches).toHaveLength(1);
    expect(Object.keys(patches[0].patch)).toEqual(["isPhoto", "params"]);
    expect(patches[0].patch.isPhoto).toBe(true);
    expect("forced_class" in patches[0].patch.params).toBe(false);
    // Rest of the design's params survive the spread, same rule as every
    // other params-replacing patch in this file.
    expect(patches[0].patch.params).toEqual({ ...DEFAULT_DIGITIZE_PARAMS });

    // Proves the row CONDITION, not just the patch shape: the harness merges
    // the patch into `element` and re-renders the real panel off it.
    expect(queryByText("You set this to flat art.")).toBeNull();
    expect(getByText("You set this to a photo.")).toBeTruthy();
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
    return render(Harness, {
      props: { element: baseElement(shapes), onPatch: () => {} },
    });
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

describe("auto-restitch on shape edits", () => {
  // `digitize` is the network call runDigitize makes; counting it is how we
  // observe a restitch without a service.
  let calls;
  beforeEach(() => {
    calls = [];
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  async function panelWithService(shapes, extra = {}) {
    const mod = await import("../lib/digitizer.js");
    vi.spyOn(mod, "digitize").mockImplementation(async () => {
      calls.push(Date.now());
      return null;   // runDigitize bails on a null job before patching
    });
    const patches = [];
    const utils = render(Harness, {
      props: {
        element: baseElement(shapes, {
          // Enough of a real design for the panel's own stats line to render;
          // these tests are about the debounce, not the readout.
          result: { stitches: [], colors: [], stitchCount: 0, colorCount: 0,
                    name: 'test', widthMM: 50, heightMM: 40 },
          ...extra,
        }),
        health: { ok: true },
        onPatch: (d) => patches.push(d),
      },
    });
    openLayers(utils);   // these tests drive a per-shape control; see openLayers
    return { ...utils, patches };
  }

  test("a shape edit does NOT restitch immediately", async () => {
    const { getByLabelText } = await panelWithService([shapeRow("s1")]);
    await fireEvent.change(getByLabelText(/^Stitch type \u2014 /), { target: { value: "satin" } });
    vi.advanceTimersByTime(1500);
    expect(calls).toHaveLength(0);
  });

  test("it restitches once the user stops editing", async () => {
    const { getByLabelText } = await panelWithService([shapeRow("s1")]);
    await fireEvent.change(getByLabelText(/^Stitch type \u2014 /), { target: { value: "satin" } });
    vi.advanceTimersByTime(2500);
    await Promise.resolve();
    expect(calls.length).toBeGreaterThanOrEqual(1);
  });

  test("rapid edits collapse into ONE restitch, not one per edit", async () => {
    // The whole point of the debounce: ten adjustments cost one 10-second
    // run, not ten queued behind each other.
    const { getByLabelText } = await panelWithService([shapeRow("s1")]);
    for (const v of ["satin", "fill", "satin", "fill"]) {
      await fireEvent.change(getByLabelText(/^Stitch type \u2014 /), { target: { value: v } });
      vi.advanceTimersByTime(300);
    }
    expect(calls).toHaveLength(0);       // still inside the idle window
    vi.advanceTimersByTime(2500);
    await Promise.resolve();
    expect(calls.length).toBeLessThanOrEqual(1);
  });
});
