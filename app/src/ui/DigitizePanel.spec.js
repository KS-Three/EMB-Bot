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

function renderPanel(shapes = [], extra = {}) {
  const patches = [];
  const utils = render(Harness, {
    props: { element: baseElement(shapes, extra), onPatch: (d) => patches.push(d) },
  });
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
    await fireEvent.change(getByLabelText("Stitch type"), { target: { value: "satin" } });
    expect(patches).toHaveLength(1);
    expect(lastOverride(patches, "s1")).toEqual({ tier: "satin" });
  });

  test("setting Stitch type back to Auto clears the override entirely", async () => {
    const { getByLabelText, patches } = renderPanel([shapeRow("s1")], {
      shapeOverrides: { s1: { tier: "satin" } },
    });
    await fireEvent.change(getByLabelText("Stitch type"), { target: { value: "auto" } });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapeOverrides.s1).toBeUndefined();
  });

  // The design-wide params section has its OWN "Fill angle"/"Border"
  // controls (label-wrapped `<select>`s, no `aria-label`) sitting on the
  // same page as these per-shape ones — `getByLabelText` matches both and
  // is ambiguous. The per-shape selects are the only ones carrying an
  // explicit `aria-label` attribute, so an attribute selector disambiguates
  // cleanly without needing to scope into the row's own DOM subtree.
  function perShapeSelect(container, label) {
    return container.querySelector(`select[aria-label="${label}"]`);
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
  test("Detail lines for photos renders unchecked and patches params on toggle", async () => {
    const { getByLabelText, patches } = renderPanel([shapeRow("s1")]);
    const box = getByLabelText("Detail lines for photos");
    expect(box.checked).toBe(false);

    await fireEvent.change(box, { target: { checked: true } });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.params.detail_layer).toBe(true);
    // The other params must survive the spread — a params patch replaces the
    // whole object, so dropping one here would silently reset the design.
    expect(patches[0].patch.params.max_colors).toBe(DEFAULT_DIGITIZE_PARAMS.max_colors);
    expect(patches[0].patch.params.satin).toBe(DEFAULT_DIGITIZE_PARAMS.satin);
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
    const hideBtn = container.querySelector('button[aria-label="Hide this shape"]');
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
    const laterBtns = document.querySelectorAll('button[aria-label="Sew later"]');
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
    const laterBtns = document.querySelectorAll('button[aria-label="Sew later"]');
    await fireEvent.click(laterBtns[0]);
    expect(patches).toHaveLength(1);
    expect(lastOverride(patches, "a")).toEqual({ layer: 1 });
  });

  test("the first row's Sew earlier and the last row's Sew later are disabled", async () => {
    const rows = [shapeRow("a", { layer: 0 }), shapeRow("b", { layer: 1 })];
    renderPanel(rows);
    const earlierBtns = document.querySelectorAll('button[aria-label="Sew earlier"]');
    const laterBtns = document.querySelectorAll('button[aria-label="Sew later"]');
    expect(earlierBtns[0]).toBeDisabled();
    expect(laterBtns[laterBtns.length - 1]).toBeDisabled();
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
    return { ...utils, patches };
  }

  test("a shape edit does NOT restitch immediately", async () => {
    const { getByLabelText } = await panelWithService([shapeRow("s1")]);
    await fireEvent.change(getByLabelText("Stitch type"), { target: { value: "satin" } });
    vi.advanceTimersByTime(1500);
    expect(calls).toHaveLength(0);
  });

  test("it restitches once the user stops editing", async () => {
    const { getByLabelText } = await panelWithService([shapeRow("s1")]);
    await fireEvent.change(getByLabelText("Stitch type"), { target: { value: "satin" } });
    vi.advanceTimersByTime(2500);
    await Promise.resolve();
    expect(calls.length).toBeGreaterThanOrEqual(1);
  });

  test("rapid edits collapse into ONE restitch, not one per edit", async () => {
    // The whole point of the debounce: ten adjustments cost one 10-second
    // run, not ten queued behind each other.
    const { getByLabelText } = await panelWithService([shapeRow("s1")]);
    for (const v of ["satin", "fill", "satin", "fill"]) {
      await fireEvent.change(getByLabelText("Stitch type"), { target: { value: v } });
      vi.advanceTimersByTime(300);
    }
    expect(calls).toHaveLength(0);       // still inside the idle window
    vi.advanceTimersByTime(2500);
    await Promise.resolve();
    expect(calls.length).toBeLessThanOrEqual(1);
  });
});
