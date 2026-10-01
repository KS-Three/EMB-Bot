# Cut-outs (holes) in hand-drawn shapes — Implementation Plan (plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A hand-drawn shape can be marked **Cut out**; it then sews nothing and removes its own area from the smallest shape that contains it.

**Architecture:** A cut-out is an ordinary shape record with `cutOut: true`. One pure function, `resolveCutOuts(shapes)`, decides by containment which shape each one cuts; `shapesToRegions` hands the engine those rings as the parent's `holes`. The engine changes in one way: its hole floor goes from four points to three. Everything that already edits a shape (popover, node drag, delete, duplicate) keeps working because a cut-out is still a shape.

**Tech Stack:** `src/digitize.js` (browser-global engine, `node --test`), Svelte 5 in legacy syntax (`export let`, `on:`, `$:`), vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-30-manual-digitizing-gaps-design.md` — §1 (the measured engine defect), §4, **§5**, §8, §10 rulings 3, 4, 10, 11.

**Supersedes** the first version of this file (commit `59ea11a4`), which planned a ring stored inside its parent. Kent ruled for Cut out on 2026-10-01 (spec ruling 11).

## Global Constraints

- **Byte-identical for every design that has no cut-out.** `shapesToRegions` on shapes with no `cutOut` must emit exactly what it emits today (`holes: []`). Engine `node --test` stays at its baseline count with no stored hash changed and no golden re-captured. If an existing engine test moves, STOP and report — do not edit the expectation.
- **Do not bump `PROJECT_FILE_VERSION`** (`app/src/lib/projectFile.js`). `cutOut` is an optional field on a shape; absent means a normal shape.
- **Never store `cutOut: false`.** Turning it off removes the key, so an untouched record equals a pre-feature record.
- **The stored `stitchType` of a shape with a cut-out in it is never rewritten.** The display says Fill; the record keeps the author's choice.
- **Exact user-facing strings** (copy them, do not paraphrase):
  - `Not inside a shape — cuts nothing.`
  - `Overlaps another cut-out — cuts nothing.`
  - `A cut-out has to stay inside its shape.`
  - `Sews as fill — satin cannot go round a cut-out.`
  - `Cuts Shape N.` (N = the parent's id with its leading `s` removed)
  - list / heading name of a cut-out: `Shape N · Cut out`
- **Engine files are edited in `src/` only.** `app/public/engine/*` is a generated copy; after an engine edit run `node app/scripts/copy-engine.mjs` before any Studio or e2e run, or the browser serves the old engine with no error.
- Svelte: legacy syntax only. A `$:` statement tracks only what it reads lexically — a value read inside a called function is invisible to it. Compile-check every `.svelte` you touch (the component specs do this by mounting; `EmbroideryField` has no mount test, so run `cd app && npx vite build` once after touching it).
- Source edits with the Edit tool only — never a PowerShell regex round-trip (it corrupts UTF-8 in this repo).
- Suites: `node --test` from the repo root (count the tests; from `app/` it reports 0 and exits 0). `cd app && npx vitest run` from `app/` (read the `RUN` banner). Never pipe a test run to `tail`; redirect to a log and append the exit code: `... > log 2>&1; echo "EXIT=$?" >> log`.
- Work only in this worktree: `C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\.claude\worktrees\manual-holes`. Never touch the main checkout or any other directory under `.claude/worktrees/`.
- Never start, stop or restart the digitizer service on port 8721. If it is down, the digitize e2e specs skip; say so in the report.
- Commits end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01WQy2mffhR9ExF1c8PGKmM7
  ```
- This repo is PUBLIC. No client artwork, names or third-party stitch files in fixtures — synthesize test images in code.

## File map

| File | Responsibility in this plan |
|---|---|
| `src/digitize.js` | hole floor 4 → 3 at the two readers |
| `test/digitize.test.js` | the triangle-hole test |
| `app/src/lib/manualShapes.js` | `resolveCutOuts`, the strings, `shapesToRegions` emitting holes, `manualShapeName` |
| `app/src/lib/fieldNodeEdit.js` | `breaksContainment`, `ringInsideBox`, `cutOutOutlinesInFieldMm`, bbox skips cut-outs, `editedElementPatch` guard |
| `app/src/lib/shapePopover.js` | Cut out row, reduced rows for a cut-out, satin note, `cutOut` patch |
| `app/src/ui/ShapePopover.svelte`, `app/src/ui/theme.css` | `toggle` row kind and the note line |
| `app/src/ui/EmbroideryField.svelte` | cut-out outlines (dashed, clickable), the hold-last-good drag guard |
| `app/src/ui/ManualPanel.svelte` | `Shape | Hole` mode strip, list/assign-box Cut out, even-odd + dashed drawing, hole-aware hit test |
| `app/src/lib/manualTrace.js` | traced holes arrive as cut-outs |
| `app/e2e/manual-cutout.spec.js` | end-to-end proof |
| `docs/scope/5-review-manual-editing.md`, `MASTER_SCOPE.md`, `PRODUCT.md`, `.claude/memory/` | status |

---

### Task 0: Baseline

**Files:** none changed.

- [ ] **Step 1:** `cd app && npm install` (a fresh worktree has no `node_modules`).
- [ ] **Step 2:** From the repo root: `node --test > <workspace>/engine-base.log 2>&1; echo "EXIT=$?" >> <workspace>/engine-base.log`, where `<workspace>` is the plan's git-ignored directory `.superpowers/sdd/2026-10-01-manual-holes/` (all logs in this plan go there). Record the `# tests` / `# pass` / `# skip` counts.
- [ ] **Step 3:** `cd app && npx vitest run > <workspace>/studio-base.log 2>&1; echo "EXIT=$?" >> <workspace>/studio-base.log`. Record files and tests from the summary.
- [ ] **Step 4:** Report both baselines. No commit.

---

### Task 1: Engine — a 3-point hole cuts

**Files:**
- Modify: `src/digitize.js` (the two `hh.length >= 4` filters — `underlayRuns`, about line 216, and the region loop, about line 612)
- Test: `test/digitize.test.js`

**Interfaces:**
- Consumes: `DG.buildQualityDesign(colorRegions, opts)` as the existing tests call it.
- Produces: a region shape's `holes` ring of exactly 3 points is honoured. Nothing else changes.

- [ ] **Step 1: Write the failing test** (append near the other `buildQualityDesign` tests):

```js
test("buildQualityDesign: a 3-point hole cuts, like a 4-point one (manual A's counter)", () => {
  const sq = [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 300 }, { x: 0, y: 300 }];
  const tri = [{ x: 100, y: 200 }, { x: 200, y: 200 }, { x: 150, y: 100 }];
  const box = [{ x: 100, y: 100 }, { x: 200, y: 100 }, { x: 200, y: 200 }, { x: 100, y: 200 }];
  const run = (holes, underlay) => DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: sq, holes, id: "s", tierOverride: "fill" }] }],
    { garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 6, underlay, targetWidthMm: 50 });
  const solid = run([], false).stitches.length;
  const withTri = run([tri], false).stitches.length;
  const withBox = run([box], false).stitches.length;
  assert.ok(withBox < solid, "a 4-point hole already cuts");
  assert.ok(withTri < solid, "a 3-point hole must cut too: " + withTri + " vs " + solid);
  // the triangle is half the box's area, so it removes less than the box does
  assert.ok(withTri > withBox, "and removes less than the bigger hole");
  // the underlay reader has the same floor: with underlay on, the hole still cuts
  assert.ok(run([tri], true).stitches.length < run([], true).stitches.length);
});
```

- [ ] **Step 2: Run it and see it fail** — `node --test test/digitize.test.js`. Expected: FAIL on "a 3-point hole must cut too: 4678 vs 4678" (the counts may differ slightly from 4678; equality is the failure).
- [ ] **Step 3: Implement** — change `hh.length >= 4` to `hh.length >= 3` at both sites. At the region-loop site add one comment line pointing at the outer floor's comment directly above it (`:591-600`), which already explains why 3 is the real minimum; say the hole floor was missed when the outer one was relaxed.
- [ ] **Step 4: Run** `node --test test/digitize.test.js` — PASS. Then the full `node --test` from the repo root to a log with the exit code appended. **Counts must equal Task 0's baseline plus one test; zero failures.** If any pre-existing test fails (a stored hash, a golden, a font test), STOP and report which — do not touch its expectation.
- [ ] **Step 5:** `node app/scripts/copy-engine.mjs`.
- [ ] **Step 6: Commit** — `Engine: a three-point hole cuts — the hole floor follows the outer ring's to 3`.

---

### Task 2: `resolveCutOuts` and the hand-off to the engine

**Files:**
- Modify: `app/src/lib/manualShapes.js`
- Test: `app/src/lib/manualShapes.spec.js`
- Check (modify only if needed): `app/src/lib/flow.js` (line ~13 uses `isValidShape`), `app/src/lib/projectFile.spec.js`

**Interfaces:**
- Consumes (same module, private): `segmentsIntersect(p1, p2, p3, p4)`, `polygonArea(points)`; exported `flattenShape`, `shapeIssues`, `pointInShape`.
- Produces:
  - `export const CUTOUT_NO_PARENT = "Not inside a shape — cuts nothing.";`
  - `export const CUTOUT_OVERLAP = "Overlaps another cut-out — cuts nothing.";`
  - `export function resolveCutOuts(shapes) → { parentOf: {[cutId]: parentId|null}, reasonOf: {[cutId]: string}, holesOf: {[parentId]: cutId[]}, flat: Map<id, ring> }`
  - `export function manualShapeName(shape, cut) → string` — `Shape N · Cut out` | `Shape N · Fill` | `Shape N · Satin`; a shape with at least one resolved cut-out reads `Fill` whatever its stored `stitchType`. `cut` is a `resolveCutOuts` result (optional; without it, no holed override).
  - `export function withCutOut(shape, on) → shape` — a copy with `cutOut: true`, or with the key removed.
  - `shapesToRegions(shapes)` — unchanged signature; a cut-out emits no region; a parent's `holes` are its resolved cut-outs' flattened rings.

- [ ] **Step 1: Write the failing tests** in `manualShapes.spec.js`:

```js
import { resolveCutOuts, shapesToRegions, manualShapeName, withCutOut, CUTOUT_NO_PARENT, CUTOUT_OVERLAP } from "./manualShapes.js";

const rect = (id, x0, y0, x1, y1, extra = {}) => ({
  id, points: [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }],
  curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null, ...extra,
});

describe("resolveCutOuts", () => {
  it("a cut-out inside one shape cuts that shape", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 300, 300), rect("s2", 100, 100, 200, 200, { cutOut: true })]);
    expect(r.parentOf).toEqual({ s2: "s1" });
    expect(r.holesOf).toEqual({ s1: ["s2"] });
    expect(r.reasonOf).toEqual({});
  });
  it("list order does not matter: a cut-out listed before its parent still resolves", () => {
    const r = resolveCutOuts([rect("s2", 100, 100, 200, 200, { cutOut: true }), rect("s1", 0, 0, 300, 300)]);
    expect(r.parentOf.s2).toBe("s1");
  });
  it("the SMALLEST containing shape is the parent (an O's counter over a patch cuts the O)", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 400, 400), rect("s2", 50, 50, 350, 350), rect("s3", 150, 150, 250, 250, { cutOut: true }),
    ]);
    expect(r.parentOf.s3).toBe("s2");
    expect(r.holesOf.s1).toBeUndefined();
  });
  it("no containing shape: cuts nothing, with the reason", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 100, 100), rect("s2", 200, 200, 260, 260, { cutOut: true })]);
    expect(r.parentOf.s2).toBeNull();
    expect(r.reasonOf.s2).toBe(CUTOUT_NO_PARENT);
  });
  it("crossing the parent's edge is not inside", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 100, 100), rect("s2", 50, 50, 150, 90, { cutOut: true })]);
    expect(r.parentOf.s2).toBeNull();
    expect(r.reasonOf.s2).toBe(CUTOUT_NO_PARENT);
  });
  it("two cut-outs of one parent that cross: the earlier stands, the later cuts nothing", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 300, 300),
      rect("s2", 50, 50, 150, 150, { cutOut: true }),
      rect("s3", 100, 100, 200, 200, { cutOut: true }),
    ]);
    expect(r.parentOf).toEqual({ s2: "s1", s3: null });
    expect(r.reasonOf.s3).toBe(CUTOUT_OVERLAP);
    expect(r.holesOf.s1).toEqual(["s2"]);
  });
  it("a cut-out nested in a sibling cut-out is an overlap, not a second hole", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 300, 300),
      rect("s2", 50, 50, 250, 250, { cutOut: true }),
      rect("s3", 100, 100, 200, 200, { cutOut: true }),
    ]);
    expect(r.parentOf.s3).toBeNull();
    expect(r.reasonOf.s3).toBe(CUTOUT_OVERLAP);
  });
  it("a cut-out never has a cut-out as its parent; an island's own cut-out resolves to the island", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 400, 400),
      rect("s2", 50, 50, 350, 350, { cutOut: true }),
      rect("s3", 100, 100, 300, 300),                    // island inside the hole
      rect("s4", 150, 150, 250, 250, { cutOut: true }),  // the island's hole
    ]);
    expect(r.parentOf).toEqual({ s2: "s1", s4: "s3" });
  });
  it("an invalid cut-out reports its own shape issue", () => {
    const bow = { id: "s2", cutOut: true, curves: {}, points: [{ x: 10, y: 10 }, { x: 90, y: 90 }, { x: 90, y: 10 }, { x: 10, y: 90 }] };
    const r = resolveCutOuts([rect("s1", 0, 0, 100, 100), bow]);
    expect(r.parentOf.s2).toBeNull();
    expect(r.reasonOf.s2).toBe("This shape crosses itself.");
  });
  it("a triangle is a legal cut-out (three points)", () => {
    const tri = { id: "s2", cutOut: true, curves: {}, points: [{ x: 100, y: 200 }, { x: 200, y: 200 }, { x: 150, y: 100 }] };
    expect(resolveCutOuts([rect("s1", 0, 0, 300, 300), tri]).parentOf.s2).toBe("s1");
  });
  it("no cut-outs: empty maps", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 10, 10)]);
    expect(r.parentOf).toEqual({}); expect(r.holesOf).toEqual({}); expect(r.reasonOf).toEqual({});
  });
});

describe("shapesToRegions with cut-outs", () => {
  it("without any cut-out the output is exactly today's (holes: [])", () => {
    const { regions } = shapesToRegions([rect("s1", 0, 0, 300, 300), rect("s2", 100, 100, 200, 200)]);
    expect(regions).toHaveLength(2);
    expect(regions[0].shapes[0].holes).toEqual([]);
    expect(regions[1].shapes[0].holes).toEqual([]);
  });
  it("a resolved cut-out becomes its parent's hole and emits no region", () => {
    const { regions } = shapesToRegions([rect("s1", 0, 0, 300, 300), rect("s2", 100, 100, 200, 200, { cutOut: true })]);
    expect(regions).toHaveLength(1);
    expect(regions[0].shapes[0].id).toBe("s1");
    expect(regions[0].shapes[0].holes).toEqual([[{ x: 100, y: 100 }, { x: 200, y: 100 }, { x: 200, y: 200 }, { x: 100, y: 200 }]]);
  });
  it("a cut-out that cuts nothing emits no region and no hole", () => {
    const { regions } = shapesToRegions([rect("s1", 0, 0, 100, 100), rect("s2", 200, 200, 260, 260, { cutOut: true })]);
    expect(regions).toHaveLength(1);
    expect(regions[0].shapes[0].holes).toEqual([]);
  });
  it("a curved cut-out is flattened like an outer ring", () => {
    const c = rect("s2", 100, 100, 200, 200, { cutOut: true, curves: { 0: { x: 150, y: 60 } } });
    const hole = shapesToRegions([rect("s1", 0, 0, 300, 300), c]).regions[0].shapes[0].holes[0];
    expect(hole.length).toBeGreaterThan(4);
  });
});

describe("names and the toggle", () => {
  it("manualShapeName", () => {
    const shapes = [rect("s1", 0, 0, 300, 300, { stitchType: "satin" }), rect("s2", 100, 100, 200, 200, { cutOut: true })];
    const cut = resolveCutOuts(shapes);
    expect(manualShapeName(shapes[1], cut)).toBe("Shape 2 · Cut out");
    expect(manualShapeName(shapes[0], cut)).toBe("Shape 1 · Fill");      // holed: sews as fill
    expect(manualShapeName(shapes[0])).toBe("Shape 1 · Satin");          // no cut info: the stored type
  });
  it("withCutOut adds the key, and removes it rather than storing false", () => {
    const s = rect("s1", 0, 0, 10, 10);
    expect(withCutOut(s, true).cutOut).toBe(true);
    expect("cutOut" in withCutOut(withCutOut(s, true), false)).toBe(false);
    expect(withCutOut(s, false)).toEqual(s);
  });
});
```

- [ ] **Step 2: Run** `cd app && npx vitest run src/lib/manualShapes.spec.js` — the new tests FAIL (`resolveCutOuts is not a function`).
> **Superseded in one detail (commit `e8c8157e`, after the final review):** the code below gives an equal-area tie to the LATER shape (`<=`). That let Duplicate take a hole away from the original, so the shipped rule is strict-smaller with an epsilon and a tie stays with the EARLIER shape. The block is kept as the plan was written; `manualShapes.js` is the truth.

- [ ] **Step 3: Implement** in `manualShapes.js`, placed after `pointInShape`'s section and before `shapesToRegions` (it must come after `flattenShape` is defined, or be a function declaration that only runs later — function declarations hoist, constants do not):

```js
// ---- Cut-outs (holes) -------------------------------------------------------
// A hole is an ordinary shape marked `cutOut: true` (spec 2026-09-30 §5,
// Kent's ruling 11). Nothing is stored about WHICH shape it cuts — that is
// resolved here, by containment, every time, so moving, duplicating or
// deleting shapes can never leave a stale link behind.
export const CUTOUT_NO_PARENT = "Not inside a shape — cuts nothing.";
export const CUTOUT_OVERLAP = "Overlaps another cut-out — cuts nothing.";

function ringBox(ring) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of ring) { if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x; if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y; }
  return { minX, minY, maxX, maxY };
}
function ringsCross(a, b) {
  for (let i = 0; i < a.length; i++) {
    const a1 = a[i], a2 = a[(i + 1) % a.length];
    for (let j = 0; j < b.length; j++) {
      if (segmentsIntersect(a1, a2, b[j], b[(j + 1) % b.length])) return true;
    }
  }
  return false;
}
// Every vertex of `inner` inside `outer`, and no edge of one touching an edge
// of the other. The box test first: most pairs fail it, and this runs on
// every frame of a node drag.
function ringInside(inner, innerBox, outer, outerBox) {
  if (innerBox.minX < outerBox.minX || innerBox.maxX > outerBox.maxX || innerBox.minY < outerBox.minY || innerBox.maxY > outerBox.maxY) return false;
  for (const p of inner) if (!pointInShape(outer, p.x, p.y)) return false;
  return !ringsCross(inner, outer);
}

// -> { parentOf: {cutId: parentId|null}, reasonOf: {cutId: why it cuts
// nothing}, holesOf: {parentId: [cutId...]}, flat: Map(id -> flattened ring) }.
// Parent = the SMALLEST valid non-cut-out shape that contains the cut-out
// (an O's counter drawn over a patch cuts the O, not the patch); a tie goes
// to the later shape (drawn on top). Two cut-outs of one parent that cross or
// nest: the earlier in the list stands — the engine fills even-odd, so both
// would sew the overlap back in. Shapes without an id take no part.
export function resolveCutOuts(shapes) {
  const list = (shapes || []).filter((s) => s && s.id != null);
  const flat = new Map(), box = new Map(), valid = new Map();
  for (const s of list) {
    const ring = flattenShape(s.points, s.curves, true);
    flat.set(s.id, ring);
    box.set(s.id, ringBox(ring));
    valid.set(s.id, shapeIssues(ring).length === 0);
  }
  const solids = list.filter((s) => !s.cutOut && valid.get(s.id));
  const area = new Map(solids.map((s) => [s.id, polygonArea(flat.get(s.id))]));
  const parentOf = {}, reasonOf = {}, holesOf = {};
  for (const c of list) {
    if (!c.cutOut) continue;
    parentOf[c.id] = null;
    const ring = flat.get(c.id);
    if (!valid.get(c.id)) { reasonOf[c.id] = shapeIssues(ring)[0]; continue; }
    let best = null;
    for (const p of solids) {
      if (!ringInside(ring, box.get(c.id), flat.get(p.id), box.get(p.id))) continue;
      if (!best || area.get(p.id) <= area.get(best.id)) best = p;
    }
    if (!best) { reasonOf[c.id] = CUTOUT_NO_PARENT; continue; }
    const taken = holesOf[best.id] || [];
    const clash = taken.some((id) => {
      const other = flat.get(id);
      return ringsCross(ring, other)
        || pointInShape(other, ring[0].x, ring[0].y)
        || pointInShape(ring, other[0].x, other[0].y);
    });
    if (clash) { reasonOf[c.id] = CUTOUT_OVERLAP; continue; }
    parentOf[c.id] = best.id;
    holesOf[best.id] = [...taken, c.id];
  }
  return { parentOf, reasonOf, holesOf, flat };
}

// A copy of `shape` marked as a cut-out, or with the mark REMOVED — never
// `cutOut: false`, so an untouched record equals a pre-feature record.
export function withCutOut(shape, on) {
  if (on) return { ...shape, cutOut: true };
  const { cutOut, ...rest } = shape;
  return rest;
}

// The one name a shape goes by — list row, assign box, popover heading. A
// shape with a cut-out in it reads Fill whatever it stores: the engine cannot
// satin round a hole, and the name says what will sew.
export function manualShapeName(shape, cut) {
  const n = String(shape.id).replace(/^s/, "");
  if (shape.cutOut) return `Shape ${n} · Cut out`;
  const holed = !!(cut && cut.holesOf && (cut.holesOf[shape.id] || []).length);
  return `Shape ${n} · ${shape.stitchType === "satin" && !holed ? "Satin" : "Fill"}`;
}
```

  Then in `shapesToRegions`: call `const cut = resolveCutOuts(shapes);` once before the loop; `if (!shape) continue;` gains `|| shape.cutOut` (with a comment: a cut-out sews nothing); and `holes: []` becomes

```js
        holes: (cut.holesOf[shape.id] || []).map((id) => cut.flat.get(id).map((p) => ({ x: p.x, y: p.y }))),
```

  Update the function's header comment: cut-outs emit no region and arrive as their parent's holes.
- [ ] **Step 4: Check the neighbours.** (a) `lib/flow.js` ~line 13: if it counts "has a sewable shape" with `isValidShape`, make it ignore cut-outs (an element holding only cut-outs sews nothing) and add one test; if it does something else, leave it and say what it does in the report. (b) `duplicateShape`: add a test that a duplicated cut-out is still a cut-out; fix only if it drops the field. (c) `projectFile.spec.js`: add one round-trip test — a manual element whose shape has `cutOut: true` saves and loads with the field intact and the file version unchanged.
- [ ] **Step 5: Run** the spec, then the full `cd app && npx vitest run` to a log with the exit code. Zero failures; the count is Task 0's plus the new tests.
- [ ] **Step 6: Commit** — `manualShapes: a shape marked Cut out cuts the smallest shape that contains it`.

---

### Task 3: Geometry guards for the field (`fieldNodeEdit.js`)

**Files:**
- Modify: `app/src/lib/fieldNodeEdit.js`
- Test: `app/src/lib/fieldNodeEdit.spec.js`

**Interfaces:**
- Consumes: `resolveCutOuts`, `flattenShape`, `shapeIssues` from `./manualShapes.js`; this module's own `pxToFieldMm(fit, {x,y}) → [xMm, yMm]`.
- Produces:
  - `export const CUTOUT_HOLD_HINT = "A cut-out has to stay inside its shape.";`
  - `export function breaksContainment(shapesBefore, shapesAfter) → boolean` — true when any cut-out that HAD a parent before no longer has that same parent.
  - `export function ringInsideBox(shape, fit, box, epsMm = 0.01) → boolean` — the shape's FLATTENED ring, in field mm, inside `box = {wMm, hMm}` centred on the origin. `true` when the box has no positive size.
  - `export function cutOutOutlinesInFieldMm(shapes, fit) → [{ id, points: [[xMm, yMm], ...], cutOut: true }]` — one entry per cut-out whose flattened ring has ≥ 3 points, resolved or not.
  - `editedElementPatch` returns `{ error: CUTOUT_HOLD_HINT }` when the edit breaks containment.
  - the module's private bbox (`flatBBox`) skips cut-outs.

- [ ] **Step 1: Write the failing tests** (reuse the spec file's existing fixture helpers for `fit` and the element; the shapes below use the same `rect` helper as Task 2 — define it locally):

```js
describe("cut-outs", () => {
  const P = rect("s1", 0, 0, 300, 300);
  const C = rect("s2", 100, 100, 200, 200, { cutOut: true });
  const fit = { cxPx: 150, cyPx: 150, mmPerPx: 0.2, offsetXMm: 0, offsetYMm: 0, pxPerMm: 6 };

  it("breaksContainment: dragging a cut-out's corner outside its parent", () => {
    const moved = applyAnchorDrag(C, 1, { x: 350, y: 100 });
    expect(breaksContainment([P, C], [P, moved])).toBe(true);
    expect(breaksContainment([P, C], [P, applyAnchorDrag(C, 1, { x: 250, y: 100 })])).toBe(false);
  });
  it("breaksContainment: pulling the parent's edge across its cut-out", () => {
    const pulled = applyAnchorDrag(P, 0, { x: 180, y: 180 });
    expect(breaksContainment([P, C], [pulled, C])).toBe(true);
  });
  it("breaksContainment: a cut-out that already cut nothing is free to move", () => {
    const orphan = rect("s2", 400, 400, 450, 450, { cutOut: true });
    expect(breaksContainment([P, orphan], [P, applyAnchorDrag(orphan, 0, { x: 380, y: 380 })])).toBe(false);
  });
  it("editedElementPatch refuses a containment-breaking edit with the hint", () => {
    const el = { id: "e1", type: "manual", shapes: [P, C], sizeMm: 60, offsetXMm: 0, offsetYMm: 0 };
    const out = editedElementPatch(el, fit, "s2", applyAnchorDrag(C, 1, { x: 350, y: 100 }));
    expect(out).toEqual({ error: CUTOUT_HOLD_HINT });
  });
  it("the bbox ignores cut-outs: moving an orphan cut-out far away changes no size or offset", () => {
    const orphan = rect("s2", 400, 400, 450, 450, { cutOut: true });
    const el = { id: "e1", type: "manual", shapes: [P, orphan], sizeMm: 60, offsetXMm: 1, offsetYMm: -2 };
    const out = editedElementPatch(el, fit, "s2", applyAnchorDrag(orphan, 2, { x: 590, y: 390 }));
    expect(out.error).toBeUndefined();
    expect(out.sizeMm).toBeCloseTo(60, 9);
    expect(out.offsetXMm).toBeCloseTo(1, 9);
    expect(out.offsetYMm).toBeCloseTo(-2, 9);
  });
  it("ringInsideBox tests the FLATTENED curve, not the handle's through point", () => {
    // a.x = 0, c.x = 5 mm on the top edge; the curve through x = 10 mm at t=0.5
    // peaks at about 10.21 mm — past a box whose half-width is exactly 10 mm.
    const sh = { id: "s1", curves: {}, points: [{ x: 0, y: 0 }, { x: 25, y: 0 }, { x: 25, y: -50 }, { x: 0, y: -50 }] };
    const f = { cxPx: 0, cyPx: 0, mmPerPx: 0.2, offsetXMm: 0, offsetYMm: 0, pxPerMm: 6 };
    const bent = applyHandleDrag(sh, 0, { x: 50, y: 10 });       // through point at x = 10 mm
    expect(ringInsideBox(sh, f, { wMm: 20, hMm: 40 })).toBe(true);
    expect(ringInsideBox(bent, f, { wMm: 20, hMm: 40 })).toBe(false);
    expect(ringInsideBox(bent, f, { wMm: 0, hMm: 0 })).toBe(true);  // no garment: nothing to hold to
  });
  it("cutOutOutlinesInFieldMm: one entry per cut-out, mapped through the fit, resolved or not", () => {
    const orphan = rect("s3", 400, 400, 450, 450, { cutOut: true });
    const out = cutOutOutlinesInFieldMm([P, C, orphan], fit);
    expect(out.map((o) => o.id)).toEqual(["s2", "s3"]);
    expect(out[0].cutOut).toBe(true);
    expect(out[0].points[0][0]).toBeCloseTo((100 - 150) * 0.2, 9);
    expect(out[0].points[0][1]).toBeCloseTo((150 - 100) * 0.2, 9);
  });
});
```

  If the bent-handle fixture's numbers do not produce a ring past 10 mm with this module's real `applyHandleDrag` (it stores a control derived from the through point), adjust the THROUGH point until the flattened ring's max x is between 10.05 and 10.5 mm while the through point itself is at ≤ 10 mm, and state the final numbers in the report. The assertion that matters: through point inside the box, flattened ring outside it.

- [ ] **Step 2: Run** — FAIL (missing exports).
- [ ] **Step 3: Implement.**

```js
export const CUTOUT_HOLD_HINT = "A cut-out has to stay inside its shape.";

// Ruling 3 (spec 2026-09-30 §5): an edit may not take a cut-out out of the
// shape it cuts, nor pull that shape across it. Compared before -> after, so
// a cut-out that already cut nothing is free to move.
export function breaksContainment(shapesBefore, shapesAfter) {
  const before = resolveCutOuts(shapesBefore).parentOf;
  const ids = Object.keys(before).filter((id) => before[id] != null);
  if (!ids.length) return false;
  const after = resolveCutOuts(shapesAfter).parentOf;
  return ids.some((id) => after[id] !== before[id]);
}

// The placement box, tested on the FLATTENED ring. A handle's through point
// (the curve at t = 0.5) can sit on the box edge while the curve bulges past
// it — a quadratic's extreme along an axis is not at t = 0.5 — and a ring
// past the box trips the engine's scale clamp, which rescales the design.
export function ringInsideBox(shape, fit, box, epsMm = 0.01) {
  if (!(box && box.wMm > 0 && box.hMm > 0)) return true;
  const hw = box.wMm / 2 + epsMm, hh = box.hMm / 2 + epsMm;
  for (const p of flattenShape(shape.points, shape.curves, true)) {
    const [x, y] = pxToFieldMm(fit, p);
    if (Math.abs(x) > hw || Math.abs(y) > hh) return false;
  }
  return true;
}

// A cut-out emits no region, so the engine has no outline for it. The field
// draws and hit-tests this one instead — the authored ring through the same
// fit the engine's outlines use. Unresolved cut-outs are included: one that
// cuts nothing still has to be clickable, to be fixed or deleted.
export function cutOutOutlinesInFieldMm(shapes, fit) {
  const out = [];
  for (const sh of shapes || []) {
    if (!sh || !sh.cutOut || sh.id == null) continue;
    const ring = flattenShape(sh.points, sh.curves, true);
    if (ring.length < 3) continue;
    out.push({ id: String(sh.id), points: ring.map((p) => pxToFieldMm(fit, p)), cutOut: true });
  }
  return out;
}
```

  In `editedElementPatch`, right after `const shapes = ...map(...)`:

```js
  if (breaksContainment(element.shapes || [], shapes)) return { error: CUTOUT_HOLD_HINT };
```

  In `flatBBox`: `if (!sh || sh.cutOut) continue;` and extend its comment — the engine never sees a cut-out (it emits no region), so the bbox must not either.
- [ ] **Step 4: Run** the spec, then the full Studio suite to a log. Zero failures. The existing invariance tests (through the real engine) must still pass untouched.
- [ ] **Step 5: Commit** — `fieldNodeEdit: an edit cannot break a cut-out's containment, and the box is tested on the curve`.

---

### Task 4: The popover — Cut out row, a cut-out's rows, the satin note

**Files:**
- Modify: `app/src/lib/shapePopover.js`, `app/src/ui/ShapePopover.svelte`, `app/src/ui/theme.css`
- Test: `app/src/lib/shapePopover.spec.js`, `app/src/ui/ShapePopover.spec.js`

**Interfaces:**
- Consumes: `resolveCutOuts`, `manualShapeName`, `withCutOut` from `./manualShapes.js`.
- Produces:
  - `export const SATIN_CUTOUT_NOTE = "Sews as fill — satin cannot go round a cut-out.";`
  - `popoverModel` (manual lane): a normal shape gets a row `{ key: "cutOut", kind: "toggle", label: "Cut out", value: false }` placed after the angle row and before `editPoints`; when the shape has a resolved cut-out its `stitchType` row has `value: "fill"` and, if the stored type is satin, `note: SATIN_CUTOUT_NOTE`; the name comes from `manualShapeName(shape, cut)`.
  - `popoverModel` for a cut-out: `rows = [ { key: "cutOut", kind: "toggle", label: "Cut out", value: true, note, warn }, editPoints, delete ]` where `note` is `Cuts Shape N.` (`warn: false`) or the `reasonOf` string (`warn: true`). No colour, stitch-type or angle rows.
  - `popoverPatch(ctx, "cutOut", boolean)` → `{ shapes: [...] }` using `withCutOut`.
  - `ShapePopover.svelte` renders `kind === "toggle"` as a `<button type="button" role="switch" aria-checked aria-label={row.label} class="shapepop-toggle">` that dispatches `change` with `{ key: row.key, value: !row.value }`, and renders `row.note` (any row kind) as `<p class="shapepop-note" class:warn={row.warn}>` directly under the row.

- [ ] **Step 1: Failing tests** in `shapePopover.spec.js`: (1) normal manual shape → row keys `["color","stitchType","angle","cutOut","editPoints","delete"]`, cutOut value false; (2) cut-out inside a parent → row keys `["cutOut","editPoints","delete"]`, value true, note `"Cuts Shape 1."`, `warn` false, name `"Shape 2 · Cut out"`; (3) cut-out outside everything → note `"Not inside a shape — cuts nothing."`, `warn` true; (4) satin parent with a resolved cut-out → stitchType row `value: "fill"`, `note: SATIN_CUTOUT_NOTE`, name `"Shape 1 · Fill"`; the same parent stored as fill → no note; (5) `popoverPatch(..., "cutOut", true)` sets `cutOut: true` on that shape only and leaves the others by reference; `false` removes the key (`"cutOut" in shape === false`); (6) the digitized and preset lanes' models are unchanged (assert their row keys as the existing tests do).
  In `ShapePopover.spec.js`: a `toggle` row renders a `role="switch"` with `aria-checked="true"`; clicking it emits `change` with `{ key: "cutOut", value: false }`; a row with `note` renders the note text, with class `warn` when `warn` is true.
- [ ] **Step 2: Run** both specs — FAIL.
- [ ] **Step 3: Implement.** In `shapePopover.js` replace the private `manualName` with `manualShapeName` (delete the old function); compute `const cut = resolveCutOuts(element.shapes);` once in the manual branch. In `ShapePopover.svelte` add the `toggle` branch and the note line (legacy syntax; keep the `{#each model.rows as row (row.key)}` keying). The switch shows the word `On` or `Off` as its text. CSS in `theme.css` beside the other `.shapepop*` rules, using the existing tokens only (no new colours): `.shapepop-toggle` matches `.shapepop-action`'s size; `[aria-checked="true"]` uses the same accent the panel's active buttons use; `.shapepop-note` is the hint size and muted colour; `.shapepop-note.warn` uses the existing warning token.
- [ ] **Step 4: Run** both specs and the full Studio suite to a log. Zero failures.
- [ ] **Step 5: Commit** — `Popover: Cut out on a hand-drawn shape, and what a cut-out cuts`.

---

### Task 5: The hoop canvas — cut-out outlines and the hold-last-good guard

**Files:**
- Modify: `app/src/ui/EmbroideryField.svelte`

**Interfaces:**
- Consumes: `cutOutOutlinesInFieldMm`, `breaksContainment`, `ringInsideBox`, `CUTOUT_HOLD_HINT` from `../lib/fieldNodeEdit.js`; the component's own `manualFit(el)`, `outlinesMmFor(el)`, `outlinesPxFor(el)`, `drawShapeOutlines(ctx)`, `hoopSizeMm(project)`, `nodeEdit`, `shapeEditError`, `repaintNodeChrome()`.
- Produces: no new exports. Behaviour:
  1. **Outlines.** In `outlinesMmFor`, for `el.type === "manual"` the returned `mm` is `designOutlinesInFieldMm(pe.design)` followed by `cutOutOutlinesInFieldMm(el.shapes, fit)` when `manualFit(el)` is non-null. `outlinesPxFor` carries `cutOut: !!o.cutOut` onto each px outline. Hit-testing is unchanged — `hitShapeInterior` already picks the smallest containing ring, so a click inside a cut-out selects the cut-out, not its parent.
  2. **Drawing.** `drawShapeOutlines` strokes a `cutOut` outline dashed (`ctx.setLineDash([4, 3])`, reset to `[]` afterwards — the canvas keeps dash state), same casing and colours otherwise, selected highlight unchanged.
  3. **The guard.** At the node-edit press (where `nodeEdit` is created with its frozen `basis`), also freeze `basis.shapes = el.shapes` and `basis.boxOk = ringInsideBox(basis.shape, basis.fit, hoopSizeMm(project))`. In `onPointerMove`'s `if (nodeEdit)` branch, compute the candidate (`applyAnchorDrag` / `applyHandleDrag` as today) but assign it to `nodeEdit.live` only when BOTH hold:
     - `!nodeEdit.basis.boxOk || ringInsideBox(candidate, fit, hoopSizeMm(project))` — a shape already past the box at press keeps today's behaviour;
     - `!breaksContainment(nodeEdit.basis.shapes, nodeEdit.basis.shapes.map((s) => (s && s.id === candidate.id ? candidate : s)))`.
     Otherwise leave `nodeEdit.live` as it was (the last good position). When the containment test is the one that failed, set `shapeEditError = CUTOUT_HOLD_HINT`; when a later frame is accepted, clear that hint (only if it is still this hint). The existing point clamp (`clampAuthoredToBox`) stays as the first step — it is what lets a node slide along the box edge.
  4. Release (`endDrag`) is unchanged: it commits `nodeEdit.live` through `commitNodeEdit`, whose `editedElementPatch` now refuses a containment break as a second line of defence (insert point, remove point).
  5. **Right-click on a cut-out must not throw.** A cut-out has no stitch runs, so anything the right-click menu derives from `design.runs` for the shape under the pointer (the border items, `borderMenu.indexRuns`) must cope with an id that has none: offer what applies to a hand-drawn shape (`Remove point` on an anchor) and nothing that needs runs.

- [ ] **Step 1:** Read the component's node-edit code first: `nodeEdit` creation in `onPointerDown`, the `if (nodeEdit)` branch of `onPointerMove` (~line 2757), `endDrag`, `outlinesMmFor` (~838), `outlinesPxFor` (~856), `drawShapeOutlines` (~1245), and where `shapeEditError` is rendered.
- [ ] **Step 2: Implement** the four behaviours. Every repaint during the drag goes through `repaintNodeChrome()` — a bare `drawOverlay()` smears (the comment above `repaintNodeChrome` explains).
- [ ] **Step 3: Compile check** — `cd app && npx vite build > <workspace>/task-5-build.log 2>&1; echo "EXIT=$?" >> <workspace>/task-5-build.log`. A Svelte `reactive_declaration_cycle` or any compile error fails this task. Then the full Studio suite to a log.
- [ ] **Step 4: Drive it once** (Task 8 writes the permanent e2e; this is the implementer's own look): with the dev server from this worktree, draw two nested rectangles on the side canvas, click the inner one on the hoop, flip Cut out, and confirm the dashed outline, the hole in the stitching, and that dragging the cut-out's corner outward stops with the hint. Say what you saw in the report; if you cannot run a browser, say that instead.
- [ ] **Step 5: Commit** — `Field: a cut-out is drawn dashed and clickable, and a drag holds it inside its shape`.

---

### Task 6: The side canvas — Hole mode, the list, the assign box

**Files:**
- Modify: `app/src/ui/ManualPanel.svelte` (and its styles where the panel's styles live)
- Test: `app/src/ui/ManualPanel.spec.js`

**Interfaces:**
- Consumes: `resolveCutOuts`, `manualShapeName`, `withCutOut` from `../lib/manualShapes.js`; `SATIN_CUTOUT_NOTE` from `../lib/shapePopover.js`; the panel's own `patch`, `updateShape`, `finishShape`, `summary`, `drawShape`, `render`, `hitTestShapeAt`.
- Produces (behaviour):
  1. **Mode strip** above the draft buttons: two segments, `Shape` and `Hole`, each a `<button type="button" aria-pressed>`; `Shape` is the default. It is a pick, not a toggle: pressing the active one does nothing. Plans 2 and 3 add `Column` and `Line` — build no placeholders for them. Switching mode does not clear the draft.
  2. `finishShape` in Hole mode appends the new shape with `cutOut: true`. Validity is the same `isValidShape` as a normal shape. The mode stays on Hole after finishing.
  3. `summary(shape)` returns `manualShapeName(shape, cut)` where `cut` is a reactive `$: cut = resolveCutOuts(shapes)`.
  4. **List row:** a cut-out's row shows its name and, when `cut.reasonOf[shape.id]` exists, that reason on a second line with class `mp-reason`.
  5. **Assign box:** a row `Cut out` with one `<button role="switch" aria-checked>` (`On` / `Off`) that calls `patch({ shapes: shapes.map((s) => (s.id === id ? withCutOut(s, !s.cutOut) : s)) })`. For a cut-out: hide the Stitch type, Color and Fill angle rows; show `Cuts Shape N.` or the reason. For a shape with a resolved cut-out and stored `stitchType === "satin"`: show `SATIN_CUTOUT_NOTE` under the stitch-type buttons, with `Fill` shown active.
  6. **Drawing:** a shape with resolved cut-outs is filled as ONE even-odd path (its ring plus each cut-out's ring, `ctx.fill("evenodd")`), so the hole reads as a hole; a cut-out itself is not filled and is stroked dashed (`setLineDash([4, 3])`, reset after). Dim (`alphaFor`) still applies to the parent's fill.
  7. **Hit test:** `hitTestShapeAt` skips a shape when the point lies inside one of ITS resolved cut-outs (a hole is not part of the shape), so a click in the hole reaches the cut-out even when the cut-out is earlier in the list.

- [ ] **Step 1: Failing tests** in `ManualPanel.spec.js` (follow the file's existing mount helpers): the strip renders with `Shape` pressed; choosing `Hole` then drawing and finishing a shape emits a patch whose new shape has `cutOut: true`, and the next finished shape in `Shape` mode has no `cutOut` key; the list row of a cut-out reads `Shape 2 · Cut out`; an orphan cut-out's row shows `Not inside a shape — cuts nothing.`; the assign box of a cut-out has no Stitch type row and its switch is `aria-checked="true"`; clicking the switch emits a patch where that shape has no `cutOut` key; a satin parent with a resolved cut-out shows the note and its heading reads `Shape 1 · Fill`.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement.** Style the strip with the tokens and the `aria-pressed` pattern the Studio's existing segmented strips use (find one — the hoop/view strip from #564 — and copy its class pattern rather than inventing colours).
- [ ] **Step 4: Run** the spec and the full Studio suite to a log. Zero failures.
- [ ] **Step 5: Commit** — `ManualPanel: Hole mode draws a cut-out, and the list and assign box say what it cuts`.

---

### Task 7: Trace import marks holes

**Files:**
- Modify: `app/src/lib/manualTrace.js`
- Test: `app/src/lib/manualTrace.spec.js`
- Check: `app/src/ui/TraceImportPanel.svelte` (id assignment — it must keep working when the batch contains cut-outs; change only if it filters or reorders by a field a cut-out lacks)

**Interfaces:**
- Consumes: `resolveCutOuts`, `isValidShape` from `./manualShapes.js`; the module's own `simplifyRingAdaptive`, `fitCurvesForRing`.
- Produces: `traceShapesFromRGBA` returns, right after each traced shape, one extra shape per real hole: `{ points, curves, colorRgb: <the parent's>, stitchType: "fill", angleDeg: null, cutOut: true }`. A hole is kept only if, checked against its own parent with temporary ids, `resolveCutOuts([parent, hole]).parentOf` resolves it; otherwise it is dropped and the warning is pushed once per parent. The warning text becomes: `A traced hole could not be kept — that shape will sew solid; cut it in by hand if needed.`

- [ ] **Step 1: Failing tests** in `manualTrace.spec.js`, on a synthesized RGBA buffer (white background, a filled dark square 120×120 with a 40×40 white square hole in its middle, on a 200×200 image): the result contains exactly one non-cut-out shape and one `cutOut: true` shape directly after it; `warnings` contains no hole warning; and `resolveCutOuts` over the result (after assigning ids `s1`, `s2`) resolves the cut-out to the square. A second test: a solid square (no hole) returns no cut-out. Keep the existing tests that asserted the old warning in step with the new behaviour — a test that pinned "hole dropped + warning" now pins "hole kept, no warning"; say in the report which tests you changed and why.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement.** Replace the `realHoles` warning block: for each real hole, `simplifyRingAdaptive(hole, simplifyTolPx)`, skip if `< 3` points, `fitCurvesForRing(hole, simplified, curveTolPx)`, build the cut-out, verify with `resolveCutOuts` against the just-emitted parent, push or count as dropped. Rewrite the "Hole handling" comment block above the function to say what it does now and why the containment check exists (the outer and the hole are simplified independently, so a thin wall can cross).
- [ ] **Step 4: Run** the spec and the full Studio suite to a log. Zero failures.
- [ ] **Step 5: Commit** — `Trace import: a traced hole arrives as a cut-out instead of a warning`.

---

### Task 8: End-to-end proof, the browser, the docs

**Files:**
- Create: `app/e2e/manual-cutout.spec.js`
- Modify: `docs/scope/5-review-manual-editing.md`, `MASTER_SCOPE.md`, `PRODUCT.md` (only where it describes the manual lane), `.claude/memory/concurrent-session-designed-the-same-tool-2026-09-17.md` and its line in `.claude/memory/MEMORY.md`

**Interfaces:**
- Consumes: the helpers `app/e2e/field-node-edit.spec.js` already has for drawing shapes, clicking a shape on the hoop canvas, reading the stitch caption, and sampling pixels inside the fabric (`FABRIC_BOX_SRC`). Copy what you need into the new spec; do not import across spec files.

- [ ] **Step 1: Write `manual-cutout.spec.js`** with these tests, each asserting on the real app:
  - (a) **Cut out cuts.** Draw a large rectangle and a smaller one inside it. Read the stitch count. Click the inner one on the hoop canvas → the popover opens named `Shape 2 · Fill` → press the `Cut out` switch → the count DROPS, the dialog's name becomes `Shape 2 · Cut out`, the note reads `Cuts Shape 1.`, and a pixel sampled at the hole's centre inside the fabric is fabric, not thread (use the spec's existing thread/fabric discriminator).
  - (b) **Off gives it back.** Press the switch again → the count returns to exactly the two-shape count from before.
  - (c) **A triangle cuts.** Same as (a) with a 3-point inner shape — the count drops. This is the engine fix seen from the UI.
  - (d) **The drag holds.** With the cut-out selected, drag its top-right anchor far outside the parent (+300, −300 canvas px) and release → the hint `A cut-out has to stay inside its shape.` was shown, the stitch count is still below the two-shape count (it still cuts), and the parent's far corner did not move (within 2 canvas px — the invariance assertion from `field-node-edit.spec.js`).
  - (e) **Hole mode.** On the side canvas choose `Hole`, draw a shape inside the first rectangle, finish → the shape list's new row reads `Shape N · Cut out` and the count dropped.
  - (f) **A cut-out outside everything says so.** Mark a shape that is not inside another as Cut out → its popover note reads `Not inside a shape — cuts nothing.`.
- [ ] **Step 2: Run** `cd app && npx playwright test e2e/manual-cutout.spec.js > <workspace>/task-8-cutout.log 2>&1; echo "EXIT=$?" >> <workspace>/task-8-cutout.log`. All pass. Prove (a) is a real test: temporarily make `shapesToRegions` emit `holes: []` again, see (a) FAIL, restore, see it pass — say so in the report.
- [ ] **Step 3: Full e2e** — `npx playwright test > <workspace>/task-8-e2e.log 2>&1; echo "EXIT=$?" >> ...`. Report passed / failed / skipped. Digitize specs skip when the service on 8721 is down — report the skip count; do not start the service.
- [ ] **Step 4: Docs.**
  - `docs/scope/5-review-manual-editing.md`: a new dated section — what shipped, the measured engine defect (4,678 / 4,678 / 4,456), the rules (smallest parent, overlap, orphan), the hold-last-good guard and that it also closes #570's curve-bulge gap, what is not built (runs, columns).
  - `MASTER_SCOPE.md`: update the area-5 lines that say hand-drawn shapes have no holes / trace import drops holes. **Word budget is 27,000** — run `digitizer/tools/scope_budget.py` with the main checkout's venv python (`/c/Users/EE-LT-11030/CLAUDE~4/EMB-Bot/digitizer/.venv/Scripts/python.exe`, read-only use); if over, MOVE text into the area doc, never delete a claim. Every claim carries a `(verb date — source)` pointer.
  - `PRODUCT.md`: only if it lists holes as a known gap of the manual lane.
  - Memory: update `concurrent-session-designed-the-same-tool-2026-09-17.md` with the third occurrence — 2026-10-01, two resumed background sessions both designing manual holes, opposite designs, one entered the other's freshly created worktree within three minutes; what caught it (an unexpected untracked file in a new worktree, then the worktree's `locked` file naming the other session's pid); the rule: before creating a worktree or writing a spec, `claude agents --json` / the process list for a session on the same topic, and after creating a worktree re-check `git status` before the first write. Keep the `MEMORY.md` index line under 260 characters.
- [ ] **Step 5:** `cd digitizer && <main venv python> -m pytest -q tests/test_scope_budget.py > <workspace>/task-8-budget.log 2>&1; echo "EXIT=$?" >> ...` — passes.
- [ ] **Step 6: Commit** — `e2e + docs: cut-outs proven end to end, and the manual lane's status says so`.

---

## Done means

- [ ] Engine `node --test`: baseline + 1, zero failures, no stored hash or golden touched.
- [ ] Studio `npx vitest run` from `app/`: zero failures, count read off the summary.
- [ ] `manual-cutout.spec.js` green; full Playwright run reported with its skip count.
- [ ] Driven in a real browser at 1440×900 and 1024×768 with screenshots — the open popover on a cut-out, the hole in the stitching, the side canvas in Hole mode.
- [ ] PR ready for review (not a draft), auto-merge armed while `mergeStateStatus` is `BLOCKED`. Body names rulings 3, 4, 10, 11, the engine fix with its measurement, and what plans 2 and 3 still owe.

## Not in this plan

Open runs and satin columns (plans 2 and 3 of the same spec); `Column` and `Line` segments in the mode strip; holes on the digitized lane (it already has them); drawing on the hoop canvas (ruling 4 deferred it); reordering shapes.
