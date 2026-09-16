import { describe, expect, test } from "vitest";
import {
  ADD_TITLE, appliedBorders, borderMenuItems, borderRequestPending,
  borderSummaryText, borderTally, edgeCapState,
  edgeCapSummaryText, effectiveBorder, indexRuns, shapeBorderState,
} from "./borderMenu.js";

describe("effectiveBorder", () => {
  test("no override: the design-wide setting decides, and null means none", () => {
    expect(effectiveBorder(undefined, null)).toEqual({ bordered: false, source: "design" });
    expect(effectiveBorder({}, "off")).toEqual({ bordered: false, source: "design" });
    expect(effectiveBorder(null, "auto")).toEqual({ bordered: true, source: "design" });
    expect(effectiveBorder({ tier: "fill" }, "bean")).toEqual({ bordered: true, source: "design" });
    expect(effectiveBorder({}, "significant")).toEqual({ bordered: true, source: "design" });
  });

  test("an override beats the design setting either way", () => {
    expect(effectiveBorder({ border: "off" }, "auto")).toEqual({ bordered: false, source: "shape" });
    expect(effectiveBorder({ border: "auto" }, "off")).toEqual({ bordered: true, source: "shape" });
    expect(effectiveBorder({ border: "bean" }, null)).toEqual({ bordered: true, source: "shape" });
    // the service lower-cases on the way in; the menu reads the stored spelling the same way
    expect(effectiveBorder({ border: "AUTO" }, null)).toEqual({ bordered: true, source: "shape" });
  });

  test("a non-string override value is not a decision", () => {
    expect(effectiveBorder({ border: true }, null)).toEqual({ bordered: false, source: "design" });
  });
});

describe("borderMenuItems", () => {
  test("a shape with no border offers Add, writing the engine's auto value", () => {
    const items = borderMenuItems(undefined, null);
    expect(items.map((i) => i.id)).toEqual(["add"]);
    expect(items[0]).toMatchObject({ label: "Add border", value: "auto", title: ADD_TITLE });
  });

  test("a shape bordered by the design setting offers Remove only", () => {
    const items = borderMenuItems({}, "auto");
    expect(items.map((i) => i.id)).toEqual(["remove"]);
    expect(items[0]).toMatchObject({ label: "Remove border", value: "off" });
  });

  test("an override adds the way back to the design setting", () => {
    expect(borderMenuItems({ border: "off" }, "auto").map((i) => [i.id, i.value]))
      .toEqual([["add", "auto"], ["design", null]]);
    expect(borderMenuItems({ border: "bean" }, null).map((i) => [i.id, i.value]))
      .toEqual([["remove", "off"], ["design", null]]);
  });

  test("every item carries a title a tooltip can show", () => {
    for (const items of [borderMenuItems({}, null), borderMenuItems({ border: "auto" }, "off")]) {
      for (const it of items) expect(typeof it.title).toBe("string");
    }
  });
});

// ---------------------------------------------------------------------------
// PART TWO: the run-derived reading. Every test below is about the gap between
// what was ASKED FOR and what the engine actually sewed — the thing the app
// could not see before `design.runs` existed.

function run(shape, kind, role = "", i0 = 0, i1 = 0) {
  return { i0, i1, kind, shape, role, block: 0 };
}

// Enough stitches that runStitches has records to count; index == record.
function stitchesOf(types) {
  return types.map((t, i) => ({ x: i, y: i, type: t }));
}

describe("indexRuns", () => {
  test("a payload with no runs answers null — not an empty tally", () => {
    expect(indexRuns({ stitches: [] })).toBe(null);
    expect(indexRuns(null)).toBe(null);
    expect(indexRuns({ runs: "nope" })).toBe(null);
    // an EMPTY array is a real answer: this design sewed nothing
    expect(indexRuns({ runs: [] })).not.toBe(null);
    expect(indexRuns({ runs: [] }).byShape.size).toBe(0);
  });

  test("border runs are filed under their shape, by weight", () => {
    const ix = indexRuns({
      runs: [
        run("s1", "fill"),
        run("s1", "satin", "border"),
        run("s2", "fill"),
        run("s2", "run", "border"),
        run("s3", "bean", "border"), // the engine's own spelling of a light border
      ],
    });
    expect(ix.byShape.get("s1")).toMatchObject({ body: 1, satin: 1, light: 0 });
    expect(ix.byShape.get("s2")).toMatchObject({ body: 1, satin: 0, light: 1 });
    expect(ix.byShape.get("s3")).toMatchObject({ body: 0, satin: 0, light: 1 });
  });

  test("travel is not thread: it never makes a shape read as sewn", () => {
    const ix = indexRuns({ runs: [run("s1", "travel")] });
    expect(ix.byShape.get("s1")).toMatchObject({ body: 0, runs: 1 });
  });

  test("a shade band's derived id is filed under the region that owns it", () => {
    const ix = indexRuns(
      { runs: [run("s1-blend0", "fill"), run("s1-shade2", "fill"), run("s1", "satin", "border")] },
      new Set(["s1"]),
    );
    expect(ix.byShape.get("s1")).toMatchObject({ body: 2, satin: 1 });
    expect(ix.byShape.has("s1-blend0")).toBe(false);
  });

  test("ids are not prefix-free, so the derived suffix is stripped ONCE and checked", () => {
    // S-2-blend0 belongs to S-2, never to S — the mistake preflight documents.
    const ix = indexRuns(
      { runs: [run("S-2-blend0", "fill"), run("S", "fill")] },
      new Set(["S", "S-2"]),
    );
    expect(ix.byShape.get("S-2")).toMatchObject({ body: 1 });
    expect(ix.byShape.get("S")).toMatchObject({ body: 1 });
  });

  test("edge-cap runs are their own bucket and count only STITCH records", () => {
    const ix = indexRuns({
      // records 0..4: jump, stitch, stitch, trim, stitch -> 3 stitches in 0..4
      stitches: stitchesOf(["jump", "stitch", "stitch", "trim", "stitch"]),
      runs: [{ ...run("", "run", "edge_cap", 0, 4) }],
    });
    expect(ix.edge).toMatchObject({ runs: 1, light: 1, satin: 0, stitches: 3 });
    expect(ix.byShape.size).toBe(0);
  });
});

describe("shapeBorderState", () => {
  const ix = indexRuns({
    runs: [
      run("satinborder", "fill"), run("satinborder", "satin", "border"),
      run("beanborder", "fill"), run("beanborder", "run", "border"),
      run("declined", "fill"),
      run("satintier", "satin"),
      run("travelonly", "travel"),
    ],
  });

  test("not asked for: no state to report", () => {
    expect(shapeBorderState({ shapeId: "x", designBorder: "off", index: ix }))
      .toMatchObject({ state: "none", requested: false, label: "" });
  });

  test("turned off by hand while the design wants one is worth showing back", () => {
    expect(shapeBorderState({ shapeId: "x", entry: { border: "off" }, designBorder: "auto", index: ix }))
      .toMatchObject({ state: "off", requested: false, source: "shape" });
  });

  test("sewn as satin", () => {
    expect(shapeBorderState({ shapeId: "satinborder", designBorder: "auto", index: ix, tier: "fill" }))
      .toMatchObject({ state: "satin", requested: true, verified: true, reason: "" });
  });

  test("sewn as a bean run, and THAT is the engine saying it was too narrow", () => {
    expect(shapeBorderState({ shapeId: "beanborder", designBorder: "auto", index: ix, tier: "fill" }))
      .toMatchObject({ state: "bean", verified: true, reason: "too-narrow-column" });
  });

  test("asked for, shape sewed, no border run: declined, with no invented cause", () => {
    const st = shapeBorderState({ shapeId: "declined", designBorder: "auto", index: ix, tier: "fill" });
    expect(st).toMatchObject({ state: "declined", verified: true, reason: "" });
    expect(st.label).toBe("no border sewn");
  });

  test("a satin-tiered shape names its reason — and does so WITHOUT the run list", () => {
    for (const index of [ix, null]) {
      expect(shapeBorderState({ shapeId: "satintier", designBorder: "auto", index, tier: "satin" }))
        .toMatchObject({ state: "declined", reason: "satin-tier" });
    }
    // ...and `verified` still tracks whether runs were there to check it against
    expect(shapeBorderState({ shapeId: "satintier", designBorder: "auto", index: null, tier: "satin" }).verified)
      .toBe(false);
  });

  test("a shape that laid no thread is not a border failure", () => {
    expect(shapeBorderState({ shapeId: "travelonly", designBorder: "auto", index: ix, tier: null }))
      .toMatchObject({ state: "unsewn", reason: "not-sewn" });
    // a shape with no runs at all reads the same way
    expect(shapeBorderState({ shapeId: "ghost", designBorder: "auto", index: ix }))
      .toMatchObject({ state: "unsewn" });
  });

  test("no runs in the payload: says REQUESTED, never claims it sewed", () => {
    const st = shapeBorderState({ shapeId: "satinborder", designBorder: "auto", index: null, tier: "fill" });
    expect(st).toMatchObject({ state: "unverified", requested: true, verified: false });
    expect(st.label).toBe("border requested");
    expect(st.title).toMatch(/what was asked for, not what is on the cloth/);
  });

  test("a changed request beats the evidence: the runs are about the OLD one", () => {
    expect(shapeBorderState({
      shapeId: "satinborder", designBorder: "auto", index: ix, tier: "fill", pending: true,
    })).toMatchObject({ state: "pending", verified: false });
  });
});

describe("borderTally / borderSummaryText", () => {
  const rows = [
    { id: "a", tier: "fill" }, { id: "b", tier: "fill" },
    { id: "c", tier: "fill" }, { id: "d", tier: "satin" },
  ];
  const ix = indexRuns({
    runs: [
      run("a", "fill"), run("a", "satin", "border"),
      run("b", "fill"), run("b", "run", "border"),
      run("c", "fill"),
      run("d", "satin"),
    ],
  });

  test("counts split by what actually sewed", () => {
    const t = borderTally({ rows, overrides: {}, designBorder: "auto", index: ix });
    expect(t).toMatchObject({
      total: 4, requested: 4, satin: 1, bean: 1, declined: 1, satinTier: 1, verified: true,
    });
    expect(borderSummaryText(t, "auto"))
      .toBe("2 of 4 borders sewn (1 satin, 1 bean) · 1 on a shape that sews as satin · 1 not generated.");
  });

  test("the count MOVES when the design toggle does — which is the whole ask", () => {
    const on = borderTally({ rows, overrides: {}, designBorder: "auto", index: ix });
    const off = borderTally({ rows, overrides: {}, designBorder: "off", index: ix });
    expect([on.requested, off.requested]).toEqual([4, 0]);
    expect(borderSummaryText(off, "off")).toMatch(/^No shape borders/);
  });

  test("a per-shape override is counted the way the engine reads it", () => {
    const t = borderTally({
      rows, overrides: { a: { border: "off" }, d: { border: "auto" } },
      designBorder: "off", index: ix,
    });
    expect(t).toMatchObject({ requested: 1, off: 0, declined: 0, satinTier: 1 });
  });

  test("with no runs the tally refuses to say anything sewed", () => {
    const t = borderTally({ rows, overrides: {}, designBorder: "auto", index: null });
    expect(t).toMatchObject({ requested: 4, satin: 0, bean: 0, verified: false });
    expect(borderSummaryText(t, "auto")).toMatch(/the request, not the cloth/);
  });
});

describe("edgeCapState / edgeCapSummaryText", () => {
  const capApplied = { code: "EDGE_CAP_APPLIED", stitches: 1204, percent: 21.3, edges: 1 };

  test("off is off", () => {
    expect(edgeCapState({ mode: "none", warnings: [capApplied] }))
      .toMatchObject({ state: "off" });
  });

  test("the engine's own bill is preferred, so two lines cannot print two numbers", () => {
    const s = edgeCapState({
      mode: "bean", warnings: [capApplied],
      index: indexRuns({ runs: [run("__edge_cap__", "run", "edge_cap", 0, 9)] }),
    });
    expect(s).toMatchObject({ state: "sewn", stitches: 1204, percent: 21.3, verified: true });
    expect(edgeCapSummaryText(s)).toBe("Bean edge sewn — 1,204 stitches (+21.3% of the design).");
  });

  test("runs alone still prove it sewed, and say the count is measured not billed", () => {
    const s = edgeCapState({
      mode: "satin", warnings: [],
      index: indexRuns({
        stitches: stitchesOf(["stitch", "stitch", "jump", "stitch"]),
        runs: [run("", "satin", "edge_cap", 0, 3)],
      }),
    });
    expect(s).toMatchObject({ state: "sewn", stitches: 3, percent: null });
    expect(s.title).toMatch(/measured off the stitch plan/);
  });

  test("switched on with nothing long enough to sew", () => {
    expect(edgeCapState({ mode: "bean", warnings: [{ code: "EDGE_CAP_EMPTY" }] }))
      .toMatchObject({ state: "empty" });
    // and the run list alone says it too
    expect(edgeCapState({ mode: "bean", warnings: [], index: indexRuns({ runs: [run("s1", "fill")] }) }))
      .toMatchObject({ state: "empty", verified: true });
  });

  test("a cap that was PRICED and then dropped never reads as sewn", () => {
    const s = edgeCapState({ mode: "bean", warnings: [{ ...capApplied, dropped: true }] });
    expect(s).toMatchObject({ state: "dropped", stitches: 1204 });
    expect(s.title).toMatch(/no edge cap on this design/);
  });

  test("lightened stretches ride along in the sentence", () => {
    const s = edgeCapState({ mode: "satin", warnings: [capApplied, { code: "EDGE_CAP_LIGHTENED", count: 2 }] });
    expect(edgeCapSummaryText(s)).toMatch(/2 stretches sewed as a light bean run/);
  });

  test("the label names the style that SEWED, not the one now selected", () => {
    // Mid-restitch after bean -> satin, the select says satin and the cloth is
    // still bean. The line describes the cloth; the block's own "reads the
    // previous stitch plan" note carries the staleness.
    const s = edgeCapState({ mode: "satin", warnings: [{ ...capApplied, style: "bean" }] });
    expect(s.label).toBe("Bean edge sewn");
    // ...and with no warning, the run kinds answer the same question
    const fromRuns = edgeCapState({
      mode: "bean", warnings: [],
      index: indexRuns({ runs: [run("__edge_cap__", "border", "edge_cap", 0, 1)] }),
    });
    expect(fromRuns.label).toBe("Satin edge sewn");
  });

  test("no runs, no warnings: requested, and it says so", () => {
    expect(edgeCapState({ mode: "bean", warnings: [] }))
      .toMatchObject({ state: "unverified", verified: false });
  });
});

describe("appliedBorders / borderRequestPending", () => {
  const key = (ov) => JSON.stringify([[], ov, [], {}]);

  test("reads the per-shape border set the CURRENT stitches were sewn with", () => {
    const m = appliedBorders(key({ a: { border: "auto" }, b: { tier: "satin" } }));
    expect(m.get("a")).toBe("auto");
    expect(m.has("b")).toBe(false);
  });

  test("nothing to compare against is not the same as 'nothing changed'", () => {
    // no result yet / unparseable: cannot tell, so nothing reads as pending
    for (const bad of [null, undefined, "", "{not json"]) {
      expect(appliedBorders(bad)).toBe(null);
      expect(borderRequestPending(appliedBorders(bad), "a", { border: "auto" })).toBe(false);
    }
  });

  test("pending is per shape, so one toggle does not stale every row", () => {
    const m = appliedBorders(key({ a: { border: "auto" } }));
    expect(borderRequestPending(m, "a", { border: "off" })).toBe(true);   // just toggled
    expect(borderRequestPending(m, "a", { border: "auto" })).toBe(false); // as sewn
    expect(borderRequestPending(m, "b", undefined)).toBe(false);          // untouched
    expect(borderRequestPending(m, "b", { border: "bean" })).toBe(true);  // newly set
    expect(borderRequestPending(m, "a", undefined)).toBe(true);           // cleared
  });
});

// The vocabulary above was written against the brief and then CHECKED against
// a live digitize (logo_script_tires.png, 2026-09-15). The engine does not
// spell a satin border "satin": `stage6_border.border_runs` stamps BORDER when
// a column fits and BEAN when it lightens, and the silhouette cap's bean style
// goes through `run_outline`, which stamps RUN. These are the spellings that
// actually arrive, pinned so the mapping cannot drift back to the guess.
describe("the kinds the engine really emits", () => {
  test("a satin border arrives as kind 'border', not kind 'satin'", () => {
    const ix = indexRuns({ runs: [run("s1", "fill"), run("s1", "border", "border")] });
    expect(ix.byShape.get("s1")).toMatchObject({ satin: 1, light: 0 });
    expect(shapeBorderState({ shapeId: "s1", designBorder: "auto", index: ix, tier: "fill" }))
      .toMatchObject({ state: "satin" });
  });

  test("a lightened border arrives as kind 'bean'", () => {
    const ix = indexRuns({ runs: [run("s1", "fill"), run("s1", "bean", "border")] });
    expect(shapeBorderState({ shapeId: "s1", designBorder: "auto", index: ix, tier: "fill" }))
      .toMatchObject({ state: "bean", reason: "too-narrow-column" });
  });

  test("the border's TRAVEL bridge is not a border", () => {
    // border_runs emits its bridge as a TRAVEL run carrying role "border"
    // (stage6_border, the `travel_path` branch). A shape whose border produced
    // nothing else has no border on it.
    const ix = indexRuns({ runs: [run("s1", "fill"), run("s1", "travel", "border")] });
    expect(ix.byShape.get("s1")).toMatchObject({ borderRuns: 0, body: 1 });
    expect(shapeBorderState({ shapeId: "s1", designBorder: "auto", index: ix, tier: "fill" }))
      .toMatchObject({ state: "declined" });
  });

  test("the bean edge cap arrives as kind 'run' under the sentinel shape id", () => {
    const ix = indexRuns({ runs: [run("__edge_cap__", "run", "edge_cap")] });
    expect(ix.edge).toMatchObject({ runs: 1, light: 1 });
    expect(ix.byShape.size).toBe(0);
    expect(edgeCapState({ mode: "bean", warnings: [], index: ix })).toMatchObject({ state: "sewn" });
  });

  test("the satin edge cap arrives as kind 'border' — never as a per-shape border", () => {
    const ix = indexRuns({ runs: [run("__edge_cap__", "border", "edge_cap")] });
    expect(ix.edge).toMatchObject({ runs: 1, satin: 1 });
    expect(ix.byShape.size).toBe(0);
  });

  test("the sentinel id alone keeps a cap run off a shape, role or no role", () => {
    const ix = indexRuns({ runs: [run("__edge_cap__", "run")] });
    expect(ix.byShape.size).toBe(0);
    expect(ix.edge.runs).toBe(1);
  });

  test("a rescued small shape's outline is kind 'run' with NO role, and is not a border", () => {
    const ix = indexRuns({ runs: [run("s1", "run")] });
    expect(ix.byShape.get("s1")).toMatchObject({ body: 1, borderRuns: 0 });
    expect(shapeBorderState({ shapeId: "s1", designBorder: "auto", index: ix, tier: "run" }))
      .toMatchObject({ state: "declined" });
  });
});
