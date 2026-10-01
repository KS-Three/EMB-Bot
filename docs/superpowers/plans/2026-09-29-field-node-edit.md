# Field Node Edit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Edit the anchors and curve handles of a hand-drawn shape directly on the hoop canvas, and retire the side canvas's vertex mode so the field is the only node editor.

**Architecture:** The engine exports the fit it already computes (`design.fit`), so a pure module `lib/fieldNodeEdit.js` maps authored canvas-px anchors/controls to field mm and back with no second transform. `EmbroideryField` draws the authored geometry for a selected hand-drawn shape and mirrors the side canvas's gestures (drag anchor, bend handle, click edge to insert) plus focus-and-Delete for one anchor; every edit commits through `editedElementPatch`, which re-fits `sizeMm` and the offsets so nothing unedited moves. `ManualPanel` loses vertex mode.

**Tech Stack:** Svelte 5 legacy syntax, Canvas 2D, vitest (jsdom for components; the engine loads via `createRequire` as `generate.spec.js` does), Playwright, `node:test` for the engine.

**Spec:** `docs/superpowers/specs/2026-09-29-field-node-edit-design.md` — binding.

## Global Constraints

- Branch `claude/field-node-edit`, cut from `claude/shape-popover` (PR #562). Work in the main checkout. Before opening the PR (Task 7) #562 must have merged; then `git rebase --onto origin/main claude/shape-popover claude/field-node-edit` so the PR shows only this work.
- **Byte-identical stitches**: the engine change is one additive `fit` field. `node --test` from the repo ROOT: same pass count as before + new tests, 0 fail; the stored stitch-hash test from #562 stays green.
- **One transform**: `fit` comes from the engine; `lib/fieldNodeEdit.js` never derives scale or centre from a bbox fit of its own (the invariance test in Task 2 would catch drift, but do not write it in the first place).
- **Single-vertex anchor moves** — never `shapeOverlay.moveNode`/`pullRing` on hand-drawn shapes.
- **Commit only when valid**: every field edit passes `shapeIssues(flattenShape(points, curves, true))` before `elupdate`; a rejected edit snaps back and sets `shapeEditError` to the first issue string.
- **No new persisted keys**: patches touch `element.shapes[].points/curves`, `sizeMm`, `offsetXMm`, `offsetYMm` only.
- **Right-click stays the menu; left-click stays select/edit.** Preset (`shape`) elements are not node-editable.
- **MASTER_SCOPE budget**: 27,000 WORDS via `digitizer/tools/scope_budget.py`; the file is at 26,984 — Task 6 REPLACES a sentence, adds no net words, and re-measures.
- Edit tool only (UTF-8). Svelte legacy syntax. Never pipe a test run to `tail`; log to a file and read the verdict line. Commit trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

---

## File structure

| file | responsibility |
|---|---|
| `src/digitize.js` (modify: after the `shapeOutlines` block ~L392-422; both return objects) | export `fit` |
| `app/src/lib/fieldNodeEdit.js` (create) | px↔mm maps, authored geometry in field mm, hit test, the four apply functions, `editedElementPatch` |
| `app/src/lib/fieldNodeEdit.spec.js` (create) | unit tests incl. the engine invariance |
| `app/src/ui/EmbroideryField.svelte` (modify) | authored-geometry drawing, gestures, focused anchor, Delete, menu item, popover Edit points |
| `app/src/lib/borderMenu.js` (modify) | nothing — the "Remove point" item is field-local; listed to say so |
| `app/src/ui/ManualPanel.svelte`, `ContentStep.svelte`, `App.svelte` (modify) | remove vertex mode and `fieldSelect.edit` |
| `app/src/ui/ManualPanel.spec.js`, `app/e2e/manual-trace-import.spec.js` (modify) | retire/move the edit-mode tests |
| `app/e2e/field-node-edit.spec.js` (create) | the six gesture cases |
| `test/digitize.test.js` (modify) | `fit` test |
| docs: `MASTER_SCOPE.md`, `docs/scope/5-review-manual-editing.md`, `PRODUCT.md` | status |

---

### Task 1: Engine exports the fit

**Files:**
- Modify: `src/digitize.js` — the empty return (~L354), the `shapeOutlines` block (~L392-422), the main return (~L770)
- Test: `test/digitize.test.js`

**Interfaces:**
- Produces: `design.fit = { cxPx, cyPx, mmPerPx, offsetXMm, offsetYMm, pxPerMm } | null` on every `buildQualityDesign` result. Forward map of an authored point `q` (canvas px): `[ (q.x - cxPx) * mmPerPx + offsetXMm, (cyPx - q.y) * mmPerPx + offsetYMm ]` — equal to each `shapeOutlines` point.

- [ ] **Step 1: Baseline** — `node --test 2>&1 | Select-String "^ℹ (tests|pass|fail)"` from the repo root; record the numbers.

- [ ] **Step 2: Failing test** — append to `test/digitize.test.js`:

```js
test("buildQualityDesign: design.fit reproduces shapeOutlines from the input geometry", () => {
  const rect = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 50 }, { x: 0, y: 50 }];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: rect, holes: [], id: "s7", tierOverride: "fill" }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 6, underlay: false, targetWidthMm: 40, offsetXMm: 5, offsetYMm: -3 }
  );
  const f = d.fit;
  assert.ok(f && typeof f.cxPx === "number" && typeof f.mmPerPx === "number");
  assert.strictEqual(f.pxPerMm, 6);
  // the offsets AS APPLIED: rounded to a DST unit (0.1 mm) like T() does
  assert.strictEqual(f.offsetXMm, 5);
  assert.strictEqual(f.offsetYMm, -3);
  const fwd = (q) => [(q.x - f.cxPx) * f.mmPerPx + f.offsetXMm, (f.cyPx - q.y) * f.mmPerPx + f.offsetYMm];
  const out = d.shapeOutlines[0].points;
  rect.forEach((q, i) => {
    assert.ok(Math.abs(fwd(q)[0] - out[i][0]) < 1e-9 && Math.abs(fwd(q)[1] - out[i][1]) < 1e-9, "point " + i);
  });
  // 100 px wide at pxPerMm 6 fitted to 40 mm -> mmPerPx = 0.4
  assert.ok(Math.abs(f.mmPerPx - 0.4) < 1e-12);
});

test("buildQualityDesign: an empty design carries fit null", () => {
  const d = DG.buildQualityDesign([], { garment: { widthIn: 4, heightIn: 4 } });
  assert.strictEqual(d.fit, null);
});
```
Run `node --test test/digitize.test.js` → the two new tests FAIL (`d.fit` undefined).

- [ ] **Step 3: Implement** — in `src/digitize.js`:
  - empty return: add `fit: null,` beside `shapeOutlines: []`;
  - right after the `shapeOutlines` block's closing `}` (before `const dropOutline = …`), add:
```js
    // The fit itself, for callers that must map FIELD mm back to source px —
    // the Studio's node editor for hand-drawn shapes (2026-09-29 field-node-
    // edit spec §2). Same numbers T() uses; offsets are the ones APPLIED
    // (rounded to a DST unit), not the request. Additive bookkeeping.
    const fit = {
      cxPx: cx, cyPx: cy, mmPerPx: mmPerPxFinal,
      offsetXMm: offXu / units.DST_UNITS_PER_MM, offsetYMm: offYu / units.DST_UNITS_PER_MM,
      pxPerMm,
    };
```
  - main return: add `fit,` after `shapeOutlines,`.

- [ ] **Step 4: Verify** — `node --test test/digitize.test.js` → pass; full `node --test` → baseline pass + 2, fail 0 (the #562 hash test among them).

- [ ] **Step 5: Commit** — `git add src/digitize.js test/digitize.test.js` → `Engine: export the fit beside shapeOutlines` + trailer.

---

### Task 2: `lib/fieldNodeEdit.js` — pure geometry and the re-fit rule

**Files:**
- Create: `app/src/lib/fieldNodeEdit.js`, `app/src/lib/fieldNodeEdit.spec.js`

**Interfaces:**
- Consumes: `fit` (Task 1); from `./manualShapes.js`: `flattenShape`, `shapeIssues`, `curveHandlePoint`, `curveControlOrNull`, `insertVertexAtSegment`, `nearestSegmentIndex`, `MAX_SHAPE_POINTS`.
- Produces (exact signatures below). Points in `authoredInFieldMm` are `[x, y]` mm arrays (the field's convention); shape records keep `{x, y}` canvas px.

- [ ] **Step 1: Failing tests** — create `app/src/lib/fieldNodeEdit.spec.js`:

```js
// Node editing of hand-drawn shapes on the field (2026-09-29 spec §3-§4):
// the px<->mm maps, the authored geometry in field mm, the hit test, the four
// edits, and the re-fit rule — pinned as an invariant through the REAL
// engine, because the rule exists so that nothing unedited ever moves.
import { beforeAll, describe, expect, test } from "vitest";
import { createRequire } from "node:module";
import {
  pxToFieldMm, fieldMmToPx, authoredInFieldMm, hitAuthored,
  applyAnchorDrag, applyHandleDrag, insertAnchor, removeAnchor, editedElementPatch,
} from "./fieldNodeEdit.js";

let EMB, generateElement, garment;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  ({ EMB } = await import("./emb.js"));
  ({ generateElement } = await import("./generate.js"));
  garment = EMB.getGarment("left_chest");
});

const fit = { cxPx: 300, cyPx: 200, mmPerPx: 0.2, offsetXMm: 5, offsetYMm: -3, pxPerMm: 6 };
const sq = (x0, y0, s) => [{ x: x0, y: y0 }, { x: x0 + s, y: y0 }, { x: x0 + s, y: y0 + s }, { x: x0, y: y0 + s }];
const shapeA = { id: "s1", points: sq(100, 100, 100), curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
const shapeB = { id: "s2", points: sq(350, 150, 80), curves: {}, stitchType: "fill", colorRgb: [200, 0, 0], angleDeg: null };
const el = (shapes, extra = {}) => ({ id: 4, type: "manual", shapes, underlay: true, sizeMm: 60, offsetXMm: 5, offsetYMm: -3, ...extra });

describe("maps", () => {
  test("pxToFieldMm is T() unrounded and fieldMmToPx inverts it", () => {
    expect(pxToFieldMm(fit, { x: 300, y: 200 })).toEqual([5, -3]);
    expect(pxToFieldMm(fit, { x: 400, y: 200 })).toEqual([25, -3]);   // +100 px -> +20 mm
    expect(pxToFieldMm(fit, { x: 300, y: 100 })).toEqual([5, 17]);    // px y up (smaller) -> mm y up
    const back = fieldMmToPx(fit, [25, 17]);
    expect(back.x).toBeCloseTo(400, 9); expect(back.y).toBeCloseTo(100, 9);
  });
});

describe("authoredInFieldMm", () => {
  test("anchors, controls and handles are mapped; a straight segment's handle is the chord midpoint", () => {
    const s = { ...shapeA, curves: { 0: { x: 150, y: 40 } } };
    const a = authoredInFieldMm(s, fit);
    expect(a.anchors).toHaveLength(4);
    expect(a.anchors[0]).toEqual(pxToFieldMm(fit, { x: 100, y: 100 }));
    expect(a.controls[0]).toEqual(pxToFieldMm(fit, { x: 150, y: 40 }));
    expect(a.controls[1]).toBeUndefined();
    // handle 0 is B(0.5) of the quadratic; handle 1 is the chord midpoint of anchors 1-2
    expect(a.handles[0]).toEqual(pxToFieldMm(fit, { x: 0.25 * 100 + 0.5 * 150 + 0.25 * 200, y: 0.25 * 100 + 0.5 * 40 + 0.25 * 100 }));
    expect(a.handles[1]).toEqual(pxToFieldMm(fit, { x: 200, y: 150 }));
  });
});

describe("hitAuthored (px space)", () => {
  // a plain 100-px square drawn 1:1 in px for readability
  const px = { anchors: [[0, 0], [100, 0], [100, 100], [0, 100]], controls: {}, handles: [[50, 0], [100, 50], [50, 100], [0, 50]] };
  test("anchor beats handle beats edge; each within its radius", () => {
    expect(hitAuthored(px, 3, 3)).toMatchObject({ kind: "anchor", index: 0 });
    expect(hitAuthored(px, 50, 4)).toMatchObject({ kind: "handle", index: 0 });
    expect(hitAuthored(px, 25, 3)).toMatchObject({ kind: "edge", index: 0 });
    expect(hitAuthored(px, 50, 50)).toBeNull();
  });
  test("an edge hit lands on the BOWED part of a curved segment", () => {
    // segment 0 bowed up to y=-40 at its middle; the chord is y=0
    const control = [50, -80]; // quadratic through (50,-40) at t=0.5
    const bowed = { anchors: px.anchors, controls: { 0: control }, handles: [[50, -40], [100, 50], [50, 100], [0, 50]] };
    expect(hitAuthored(bowed, 25, -30)).toMatchObject({ kind: "edge", index: 0 }); // on the curve, 30 px off the chord
    expect(hitAuthored(bowed, 25, 3)).toBeNull(); // the chord is no longer where the edge is
  });
});

describe("edits", () => {
  test("applyAnchorDrag moves ONE anchor and nothing else", () => {
    const s = applyAnchorDrag(shapeA, 2, { x: 250, y: 260 });
    expect(s.points[2]).toEqual({ x: 250, y: 260 });
    expect(s.points[1]).toBe(shapeA.points[1]);
    expect(shapeA.points[2]).toEqual({ x: 200, y: 200 }); // input untouched
  });
  test("applyHandleDrag stores a control, and a drag back to the chord straightens", () => {
    const bent = applyHandleDrag(shapeA, 0, { x: 150, y: 60 });
    expect(bent.curves[0]).toBeDefined();
    const straight = applyHandleDrag(bent, 0, { x: 150, y: 100.5 });
    expect(straight.curves[0]).toBeUndefined();
  });
  test("insertAnchor splices after the segment and reindexes curves; the cap is a no-op", () => {
    const s = insertAnchor({ ...shapeA, curves: { 2: { x: 1, y: 1 } } }, 0, { x: 150, y: 100 });
    expect(s.points).toHaveLength(5);
    expect(s.points[1]).toEqual({ x: 150, y: 100 });
    expect(s.curves[3]).toEqual({ x: 1, y: 1 });
    const capped = { ...shapeA, points: Array.from({ length: 500 }, (_, i) => ({ x: i, y: 0 })) };
    expect(insertAnchor(capped, 0, { x: 0.5, y: 0 })).toBe(capped);
  });
  test("removeAnchor drops the anchor and both curves that touched it, reindexes, floors at 3", () => {
    const s = removeAnchor({ ...shapeA, curves: { 0: { x: 9, y: 9 }, 1: { x: 8, y: 8 }, 2: { x: 7, y: 7 } } }, 1);
    expect(s.points.map((p) => p.x)).toEqual([100, 200, 100]);
    expect(s.curves).toEqual({ 1: { x: 7, y: 7 } }); // old seg 2 (anchors 2->3) is now seg 1; segs 0 and 1 (touching anchor 1) are gone
    const tri = { ...shapeA, points: shapeA.points.slice(0, 3) };
    expect(removeAnchor(tri, 0)).toBeNull();
  });
});

describe("editedElementPatch — the re-fit rule, through the real engine", () => {
  function outlinesOf(element) {
    const d = generateElement(element, garment, {});
    return { fit: d.fit, byId: Object.fromEntries(d.shapeOutlines.map((o) => [o.id, o.points])) };
  }
  const near = (a, b) => a.every((p, i) => Math.abs(p[0] - b[i][0]) < 1e-6 && Math.abs(p[1] - b[i][1]) < 1e-6);

  test("dragging one of A's anchors outward leaves B and A's other anchors exactly where they were", () => {
    const before = el([shapeA, shapeB]);
    const o0 = outlinesOf(before);
    const moved = applyAnchorDrag(shapeA, 0, { x: 20, y: 20 }); // outward: grows the whole bbox
    const patch = editedElementPatch(before, o0.fit, "s1", moved);
    expect(patch.error).toBeUndefined();
    expect(patch.shapes[0].points[0]).toEqual({ x: 20, y: 20 });
    const after = { ...before, ...patch };
    const o1 = outlinesOf(after);
    expect(near(o1.byId.s2, o0.byId.s2)).toBe(true);
    expect(near(o1.byId.s1.slice(1), o0.byId.s1.slice(1))).toBe(true);
    // and the moved anchor landed where the drag put it
    expect(o1.byId.s1[0][0]).toBeCloseTo(pxToFieldMm(o0.fit, { x: 20, y: 20 })[0], 6);
    expect(o1.byId.s1[0][1]).toBeCloseTo(pxToFieldMm(o0.fit, { x: 20, y: 20 })[1], 6);
    expect(patch.sizeMm).not.toBe(before.sizeMm); // width grew, scale held
  });
  test("the same from an auto-fit element (sizeMm null): the patch seeds sizeMm and holds the scale", () => {
    const before = el([shapeA, shapeB], { sizeMm: null });
    const o0 = outlinesOf(before);
    const patch = editedElementPatch(before, o0.fit, "s2", applyAnchorDrag(shapeB, 1, { x: 480, y: 150 }));
    expect(typeof patch.sizeMm).toBe("number");
    const o1 = outlinesOf({ ...before, ...patch });
    expect(near(o1.byId.s1, o0.byId.s1)).toBe(true);
  });
  test("an edit that leaves the shape invalid is refused with the issue text", () => {
    const before = el([shapeA]);
    const o0 = outlinesOf(before);
    const bowtie = { ...shapeA, points: [{ x: 100, y: 100 }, { x: 200, y: 200 }, { x: 200, y: 100 }, { x: 100, y: 200 }] };
    const r = editedElementPatch(before, o0.fit, "s1", bowtie);
    expect(r.shapes).toBeUndefined();
    expect(typeof r.error).toBe("string");
    expect(r.error.length).toBeGreaterThan(0);
  });
});
```

Run `cd app && npx vitest run src/lib/fieldNodeEdit.spec.js` → FAIL (module not found).

- [ ] **Step 2: Implement** — create `app/src/lib/fieldNodeEdit.js`:

```js
// Node editing of hand-drawn shapes on the hoop canvas (2026-09-29 spec).
//
// A hand-drawn shape is AUTHORED geometry — anchors in a fixed 600x400
// canvas-px space plus one optional quadratic control per segment
// (manualShapes.js) — and the engine fits the bbox of all of an element's
// shapes to the hoop. The field only ever saw the flattened ring. This module
// maps the authored anchors and controls through the engine's own fit
// (`design.fit`, exported by buildQualityDesign) so the field can draw and
// edit them, and it owns the one rule that makes editing usable: an edit
// never moves what was not edited (editedElementPatch). Pure: no DOM, no
// Svelte. Points in field mm are [x, y] arrays (the field's convention);
// shape records keep {x, y} canvas px.
import {
  flattenShape, shapeIssues, curveHandlePoint, curveControlOrNull,
  insertVertexAtSegment, nearestSegmentIndex, MAX_SHAPE_POINTS,
} from "./manualShapes.js";

// shapeOverlay.js's grab radii, so a hand-drawn node feels like a digitized one.
export const ANCHOR_GRAB_PX = 9;
export const HANDLE_GRAB_PX = 8;
export const EDGE_GRAB_PX = 6;

// T() without the rounding: canvas px -> field mm (+y up).
export function pxToFieldMm(fit, q) {
  return [(q.x - fit.cxPx) * fit.mmPerPx + fit.offsetXMm, (fit.cyPx - q.y) * fit.mmPerPx + fit.offsetYMm];
}
export function fieldMmToPx(fit, [xMm, yMm]) {
  return { x: fit.cxPx + (xMm - fit.offsetXMm) / fit.mmPerPx, y: fit.cyPx - (yMm - fit.offsetYMm) / fit.mmPerPx };
}

// Anchors, controls and the per-segment handle (B(0.5) of the curve, or the
// chord midpoint when straight) in field mm. The control point is mapped
// directly: the map is affine, so a quadratic drawn through mapped
// anchors/control is the same curve the engine flattened.
export function authoredInFieldMm(shape, fit) {
  const pts = shape.points || [];
  const curves = shape.curves || {};
  const n = pts.length;
  const anchors = pts.map((p) => pxToFieldMm(fit, p));
  const controls = {};
  const handles = [];
  for (let i = 0; i < n; i++) {
    const a = pts[i], c = pts[(i + 1) % n];
    if (curves[i]) controls[i] = pxToFieldMm(fit, curves[i]);
    handles.push(pxToFieldMm(fit, curveHandlePoint(a, c, curves[i])));
  }
  return { anchors, controls, handles };
}

// What a point is on, in ONE px space (the caller maps the authored geometry
// to canvas px first). Anchors beat handles beat edges: an anchor sits on two
// edges and a handle sits on its edge, so distance alone would hand a
// dead-centre hit to whichever rounds smaller. The edge distance is measured
// against the FLATTENED curve chain, so a bowed segment is hit on its bow.
export function hitAuthored(authoredPx, px, py) {
  const { anchors, controls, handles } = authoredPx;
  for (let i = 0; i < anchors.length; i++) {
    if (Math.hypot(px - anchors[i][0], py - anchors[i][1]) <= ANCHOR_GRAB_PX) return { kind: "anchor", index: i, atPx: anchors[i] };
  }
  for (let i = 0; i < handles.length; i++) {
    if (Math.hypot(px - handles[i][0], py - handles[i][1]) <= HANDLE_GRAB_PX) return { kind: "handle", index: i, atPx: handles[i] };
  }
  const pts = anchors.map(([x, y]) => ({ x, y }));
  const cv = {};
  for (const k of Object.keys(controls)) cv[k] = { x: controls[k][0], y: controls[k][1] };
  const near = nearestSegmentIndex(pts, cv, px, py, true);
  if (near && near.index >= 0 && near.dist <= EDGE_GRAB_PX) return { kind: "edge", index: near.index, atPx: [px, py] };
  return null;
}

export function applyAnchorDrag(shape, index, newPx) {
  const points = shape.points.map((p, i) => (i === index ? { x: newPx.x, y: newPx.y } : p));
  return { ...shape, points };
}

// Drag a segment's handle to `throughPx`: store the control that puts the
// curve through it, or delete the key when it is back on the chord
// (manualShapes.curveControlOrNull — the same 2 px rule the side canvas had).
export function applyHandleDrag(shape, seg, throughPx) {
  const n = shape.points.length;
  const a = shape.points[seg], c = shape.points[(seg + 1) % n];
  const control = curveControlOrNull(a, c, throughPx);
  const curves = { ...(shape.curves || {}) };
  if (control) curves[seg] = control; else delete curves[seg];
  return { ...shape, curves };
}

export function insertAnchor(shape, seg, atPx) {
  return insertVertexAtSegment(shape, seg, atPx);
}

// Remove one anchor. The two segments that touched it (seg index-1 and seg
// index) become one straight segment; curves on later segments shift down.
// null at the floor: a shape needs three anchors to be a shape.
export function removeAnchor(shape, index) {
  const pts = shape.points || [];
  const n = pts.length;
  if (n <= 3) return null;
  const points = pts.filter((_, i) => i !== index);
  const old = shape.curves || {};
  const curves = {};
  const prev = (index - 1 + n) % n;
  for (const k of Object.keys(old)) {
    const s = Number(k);
    if (s === index || s === prev) continue;
    curves[s > index ? s - 1 : s] = old[k];
  }
  return { ...shape, points, curves };
}

// The re-fit rule (spec §4). The engine fits the bbox of ALL shapes, so a
// node dragged outward would re-centre and rescale everything on the next
// generate. Hold the scale (sizeMm' = new width * mmPerPx — this also seeds
// sizeMm when it was null, the field's resize convention) and shift the
// offsets by the bbox-centre delta, so T() of every unedited point is
// unchanged. Refuses an invalid shape with the first shapeIssues string.
export function editedElementPatch(element, fit, shapeId, edited) {
  const issues = shapeIssues(flattenShape(edited.points, edited.curves, true));
  if (issues.length) return { error: issues[0] };
  const shapes = (element.shapes || []).map((s) => (s && s.id === shapeId ? edited : s));
  const b0 = flatBBox(element.shapes || []);
  const b1 = flatBBox(shapes);
  if (!b0 || !b1) return { error: "Nothing to fit." };
  const s = fit.mmPerPx;
  return {
    shapes,
    sizeMm: (b1.maxX - b1.minX) * s,
    offsetXMm: fit.offsetXMm + (((b1.minX + b1.maxX) / 2) - ((b0.minX + b0.maxX) / 2)) * s,
    offsetYMm: fit.offsetYMm + (((b0.minY + b0.maxY) / 2) - ((b1.minY + b1.maxY) / 2)) * s,
  };
}

// The engine's bbox: every VALID shape's flattened outer ring (shapesToRegions
// skips invalid ones, and buildQualityDesign fits what it is given).
function flatBBox(shapes) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const sh of shapes) {
    if (!sh) continue;
    const ring = flattenShape(sh.points, sh.curves, true);
    if (shapeIssues(ring).length) continue;
    for (const p of ring) { if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x; if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y; }
  }
  return isFinite(minX) ? { minX, minY, maxX, maxY } : null;
}
```

- [ ] **Step 3: Run** — the spec passes. If the invariance test fails by more than 1e-6, the cause is almost always the ROUNDING of offsets to DST units in the engine (`offXu = Math.round(...)`): the patch's `offsetXMm'` may round differently than `fit.offsetXMm` did. If so, snap the patch's offsets to 0.1 mm (`Math.round(v * 10) / 10`) BEFORE returning and re-run — and record in the module comment that offsets are held on the DST grid because the engine will round them anyway. Do not loosen the tolerance.

- [ ] **Step 4: Commit** — `fieldNodeEdit.js: authored geometry on the field and the re-fit rule` + trailer.

---

### Task 3: Field gestures for hand-drawn shapes

**Files:**
- Modify: `app/src/ui/EmbroideryField.svelte` — imports; state near `selectedShapeElId` (~L534); `drawShapeOutlines` node-dot block (~L1077-1100); the outline-press branch (~L2108-2166); `onPointerMove`'s shapeEdit branch (~L2241); `endDrag` (~L2390); `onWindowKey` Delete path; `onPopAction`'s `editPoints` (~L650-657); `shapeUnderPointer` / the `.fieldmenu` template (menu item)

**Interfaces:**
- Consumes: Task 2's module; `peById[el.id].design.fit`.
- Produces: field-internal `nodeEdit = null | { elId, shapeId, kind: "anchor"|"handle", index, basis: { fit, shape }, live: shape' }`, `focusedAnchor = null | { elId, shapeId, index }`; `shapeselect` loses its `edit` flag (always `{ elementId, shapeId }`).

- [ ] **Step 1: Import and state**
```js
  import { authoredInFieldMm, hitAuthored, applyAnchorDrag, applyHandleDrag, insertAnchor, removeAnchor, editedElementPatch, fieldMmToPx } from "../lib/fieldNodeEdit.js";
```
```js
  // Node editing of a HAND-DRAWN shape (2026-09-29 field-node-edit spec):
  // the authored anchors/controls, mapped through the engine's fit, drawn and
  // grabbable once the shape is selected. `basis` is frozen at press so a
  // regenerate landing mid-drag cannot skew the inverse; `live` is the shape
  // as the drag has it. `focusedAnchor` is the anchor a Delete would remove.
  let nodeEdit = null;
  let focusedAnchor = null;

  function manualFit(el) {
    const pe = peById[el.id];
    return pe && pe.design && pe.design.fit ? pe.design.fit : null;
  }
  function manualShapeOf(el, shapeId) {
    return (el.shapes || []).find((s) => s && s.id === shapeId) || null;
  }
  // The selected hand-drawn shape's authored geometry in CANVAS px, from the
  // live drag if one is running, else from the element.
  function authoredPxFor(el, shapeId) {
    const fit = manualFit(el);
    const shape = nodeEdit && nodeEdit.shapeId === shapeId && nodeEdit.elId === el.id ? nodeEdit.live : manualShapeOf(el, shapeId);
    if (!fit || !shape || !renderResult) return null;
    const mm = authoredInFieldMm(shape, fit);
    const toPx = ([x, y]) => { const c = renderResult.toCanvas(x, y); return [c.x, c.y]; };
    const controls = {};
    for (const k of Object.keys(mm.controls)) controls[k] = toPx(mm.controls[k]);
    return { anchors: mm.anchors.map(toPx), controls, handles: mm.handles.map(toPx), fit, shape };
  }
  // Canvas px -> authored canvas px, through the frozen fit.
  function fieldPxToAuthored(fit, p) {
    const o = renderResult.toCanvas(0, 0), ex = renderResult.toCanvas(1, 0), ey = renderResult.toCanvas(0, 1);
    const xMm = (p.x - o.x) / (ex.x - o.x), yMm = (p.y - o.y) / (ey.y - o.y);
    return fieldMmToPx(fit, [xMm, yMm]);
  }
  function commitNodeEdit(el, edited) {
    const fit = nodeEdit ? nodeEdit.basis.fit : manualFit(el);
    const patch = editedElementPatch(el, fit, edited.id, edited);
    if (patch.error) { shapeEditError = patch.error; return false; }
    shapeEditError = "";
    dispatch("elupdate", { id: el.id, patch });
    return true;
  }
```

- [ ] **Step 2: Draw the authored geometry** — in `drawShapeOutlines`, replace the block that begins `if (el.type !== "digitized") continue;` (before the dot loop) with: keep the dot loop for digitized as is; for `el.type === "manual" && editing` (the selected shape), draw from `authoredPxFor(el, o.id)`: the quadratic outline (`moveTo` anchor 0, then per segment `quadraticCurveTo(control, next)` or `lineTo`), amber like the digitized selected ring; anchor dots (radius `NODE_R + 0.6`, amber fill, dark casing; the `focusedAnchor` one gets a second ring 3 px larger); handle dots (radius `NODE_R - 1`, green `rgba(64, 200, 120, 0.95)` — the side canvas's curve-handle colour — dark casing). Presets: no dots, as today. Comment the colour choice: "the side canvas's vocabulary, so nothing has to be relearned".

- [ ] **Step 3: Gestures in `onPointerDown`** — in the `if (edit)` block, BEFORE the existing `hitOverlay` on the flattened ring, add for a selected hand-drawn shape:
```js
      if (edit.el.type === "manual" && selectedShapeId && selectedShapeElId === edit.el.id) {
        const ap = authoredPxFor(edit.el, selectedShapeId);
        const ah = ap ? hitAuthored(ap, p.x, p.y) : null;
        if (ah) {
          canvas.setPointerCapture(e.pointerId);
          shapeEditError = "";
          pressClient = { x: e.clientX, y: e.clientY, px: p };
          if (ah.kind === "edge") {
            // Click-to-insert on release (endDrag); a drag from an edge does nothing.
            pressEdge = { elId: edit.el.id, shapeId: selectedShapeId, index: ah.index };
            return;
          }
          if (ah.kind === "anchor") focusedAnchor = { elId: edit.el.id, shapeId: selectedShapeId, index: ah.index };
          nodeEdit = { elId: edit.el.id, shapeId: selectedShapeId, kind: ah.kind, index: ah.index,
                       basis: { fit: ap.fit, shape: ap.shape }, live: ap.shape };
          canvas.style.cursor = "grabbing";
          drawOverlay();
          return;
        }
      }
```
Declare `let pressEdge = null;` with the other press state; clear it on every `endDrag` path with `pressClient`. Keep the existing branch for the flattened-ring hit (selection, popover on release) unchanged below it — a press on the ring away from any anchor/handle/edge still selects.

- [ ] **Step 4: `onPointerMove`** — beside the `shapeEdit` branch:
```js
    if (nodeEdit) {
      const el = project.elements.find((x) => x.id === nodeEdit.elId);
      if (!el) return;
      const at = fieldPxToAuthored(nodeEdit.basis.fit, p);
      nodeEdit.live = nodeEdit.kind === "anchor"
        ? applyAnchorDrag(nodeEdit.live, nodeEdit.index, at)
        : applyHandleDrag(nodeEdit.live, nodeEdit.index, at);
      nodeEdit = nodeEdit; // reassign for Svelte
      drawOverlay();
      return;
    }
```

- [ ] **Step 5: `endDrag`** — as the FIRST branch:
```js
    if (nodeEdit) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      const el = project.elements.find((x) => x.id === nodeEdit.elId);
      const changed = nodeEdit.live !== nodeEdit.basis.shape;
      if (el && changed && e.type !== "pointercancel") commitNodeEdit(el, nodeEdit.live);
      nodeEdit = null;
      pressClient = null; pressOutline = false; pressEdge = null;
      if (canvas) canvas.style.cursor = "default";
      drawOverlay();
      return;
    }
    if (pressEdge && pressClient && e && e.type !== "pointercancel" && typeof e.clientX === "number") {
      const moved = Math.hypot(e.clientX - pressClient.x, e.clientY - pressClient.y);
      const el = project.elements.find((x) => x.id === pressEdge.elId);
      const shape = el && manualShapeOf(el, pressEdge.shapeId);
      if (moved < CLICK_PX && el && shape) {
        const at = fieldPxToAuthored(manualFit(el), canvasPointFromEvent(e));
        const grown = insertAnchor(shape, pressEdge.index, at);
        if (grown !== shape) commitNodeEdit(el, grown);
      }
      pressEdge = null; pressClient = null;
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      drawOverlay();
      return;
    }
```
A press on an anchor that did not move (`changed` false) leaves `focusedAnchor` set and commits nothing — that is the focus gesture.

- [ ] **Step 6: Delete a node** — in `onWindowKey`'s Delete/Backspace path, before `deleteSelectedShape()`:
```js
    if (focusedAnchor) {
      const el = project.elements.find((x) => x.id === focusedAnchor.elId);
      const shape = el && manualShapeOf(el, focusedAnchor.shapeId);
      if (shape) {
        const smaller = removeAnchor(shape, focusedAnchor.index);
        if (!smaller) shapeEditError = "A shape needs at least 3 points.";
        else if (commitNodeEdit(el, smaller)) focusedAnchor = null;
        drawOverlay();
        e.preventDefault();
        return;
      }
    }
```
Escape (same handler): if `focusedAnchor`, clear it first and return. Clear `focusedAnchor` wherever `selectedShapeId` is cleared.

- [ ] **Step 7: Menu item** — in `shapeUnderPointer`, when the right-click's element is `manual` and its selected shape's `authoredPxFor` hit is an anchor, add to the returned `items` (before the border items — which the manual lane does not have; give the manual lane a `shape` section with just the name and this item): `{ id: "removepoint", label: "Remove point", value: null, title: shape.points.length <= 3 ? "A shape needs at least 3 points." : "Remove this point; its two edges become one." , disabled: shape.points.length <= 3, anchor: index }`. In the template render `disabled={it.disabled}`; in `chooseBorder`'s place add a `chooseMenuItem(it)` that routes `removepoint` to the same `removeAnchor` + `commitNodeEdit` path. Keep the digitized border items exactly as they are.

- [ ] **Step 8: Popover Edit points** — `onPopAction`'s `editPoints`: for every lane, `closeShapePop()` and `drawOverlay()`; delete the `dispatch("shapeselect", { …, edit: true })`. Remove the `edit: false` field from the two remaining `shapeselect` dispatches (payload `{ elementId, shapeId }`).

- [ ] **Step 9: Verify** — `cd app && npm test` green (ManualPanel's edit tests still pass at this point — they go in Task 4). Browser: draw a shape → click inside → Escape → anchor dots + green handles visible; drag a corner → stitches follow, the other three corners and any second shape do NOT move; drag a handle → segment bows; drag it back → straight; click mid-edge → new anchor; click an anchor, Delete → gone; at three anchors Delete shows the message; right-click an anchor → "Remove point". Screenshots.

- [ ] **Step 10: Commit** — `Field: edit a hand-drawn shape's anchors and curves on the hoop canvas` + trailer.

---

### Task 4: Retire the side canvas's vertex mode

**Files:**
- Modify: `app/src/ui/ManualPanel.svelte` (state L141-160 `editingId/editPoints/editCurves/dragIndex`, `curveTarget === "edit"` paths, `startShapeEdit`/`stopShapeEdit` L535-549, `fieldSelect` block L551-559, `hitTestVertex` L565, `edgeHitOn` L597, `tryInsertVertexAt` L611, pointer handlers' edit branches L676-691/L713-722/L749-777/L786-815, keyboard gates L846-849/L884/L890/L904, `editIssues` markup L1135, Duplicate's `!!editingId`, the buttons L1246-1254, the hint paragraph), `app/src/ui/ContentStep.svelte` L318 (prop stays; payload loses `edit`), `app/src/App.svelte` (no change unless it reads `.edit`)
- Modify tests: `app/src/ui/ManualPanel.spec.js`, `app/e2e/manual-trace-import.spec.js`

- [ ] **Step 1: Remove** — every symbol above; `fieldSelect` keeps ONLY row selection (`selectedShapeId = fieldSelect.shapeId`, scroll into view). `onCanvasClick`'s edge-insert path (`if (hitId === selectedShapeId && tryInsertVertexAt(...))`) goes; a click on the selected shape now just keeps it selected. Cursor: the "cell" edge cursor and edit-mode cursors go; "pointer" over a shape body stays. Hint paragraph: replace "Once a shape is selected, click its edge to add a new point there." with "Edit a shape's points on the design canvas: click the shape there, then drag its dots and handles." Duplicate's `disabled` loses `|| !!editingId`.

- [ ] **Step 2: Tests** — delete from `ManualPanel.spec.js`: "editing a finished shape's points by dragging a vertex", "bowing a finished shape's edge while editing points", the edge-click-to-insert tests, edit-mode cursor tests, "Escape exits vertex edit"; adjust "Delete/Backspace delete the whole shape only with no draft" to drop the `!editingId` half. Keep every draft test. In `manual-trace-import.spec.js`, replace the side-canvas "Edit points → drag firstShapePoints[1]" step with: click the first traced shape on the HOOP canvas (find its dark pixels as `field-shape-popover.spec.js` does), Escape the popover, drag the anchor nearest the top-left of its outline by (+40, −40) CSS px, assert the caption changed and the row count is still 3.

- [ ] **Step 3: Verify** — `cd app && npm test` (read the RUN banner) and `npx playwright test e2e/manual-trace-import.spec.js e2e/field-shape-popover.spec.js` → green. Compile check on ManualPanel (the #562 lesson: `npx svelte-check` if present, else `node -e` with `svelte/compiler` on the file).

- [ ] **Step 4: Commit** — `ManualPanel: the field is the node editor; the side canvas draws` + trailer.

---

### Task 5: e2e — the six gestures

**Files:** Create `app/e2e/field-node-edit.spec.js` (no service needed; same viewport/helper style as `field-shape-popover.spec.js` — draw on `.mp-canvas`, find the design's dark pixels on `.hoop canvas`, read the caption `span.stats`).

Helpers to write: `drawRect(page, fx0, fx1)`; `darkBBox(page)` (canvas px + `scale`); `anchorPx(page, corner)` — the selected shape's anchor is at the design's bbox corner: click inside the shape to select, Escape the popover, then compute the corner from `darkBBox` (dots are drawn ON the corner); `settle(page)` — three equal `span.stats` reads.

- [ ] **Step 1: Tests**
  - (a) **anchor drag**: draw one rect; select; drag its top-left anchor by (−40, −30); `span.stats` changes; `darkBBox` grew leftwards and upwards by ≈ the drag (≥ 25 px each, canvas px × scale); no dialog.
  - (b) **handle drag**: mid-top handle dragged up 40 px; caption changes; a pixel 20 px above the old top edge at mid-x is now dark.
  - (c) **edge click inserts**: click 30 px left of the top edge's midpoint ON the edge (y = top edge); read anchor dots: count amber dot blobs along the top edge before (2) and after (3) — or, simpler and allowed: right-click that spot afterwards and assert the menu offers "Remove point" (proves an anchor is there now).
  - (d) **focus + Delete**: on a 4-anchor rect, click the top-right anchor (no drag), press Delete → caption changes and the dark bbox's top-right is now a diagonal (a pixel just inside the old corner is NOT dark). Repeat until three anchors, then Delete once more → `.fieldwrap` shows "A shape needs at least 3 points." (the `shapeEditError` line — find its selector in the field template) and the caption is unchanged.
  - (e) **invariance**: two rects (15–45% and 55–85%); select the left one; drag its left anchor 40 px further left; the RIGHT rect's dark bbox (x range within its half) is unchanged to ±1 px.
  - (f) **edge drag does nothing**: press on the top edge midpoint of the selected shape, drag 40 px, release → caption unchanged, dark bbox unchanged, no dialog.

- [ ] **Step 2: Run** — `cd app && npx playwright test e2e/field-node-edit.spec.js e2e/field-shape-popover.spec.js e2e/manual-trace-import.spec.js` → log → all pass, none skipped. Iterate on selectors only; never weaken an assertion.

- [ ] **Step 3: Commit** — `e2e: node editing on the field — drag, bend, insert, delete, invariance` + trailer.

---

### Task 6: Docs

- `MASTER_SCOPE.md` area 5, the popover paragraph: REPLACE the sentence `Field node editing of hand-drawn shapes is the agreed follow-up.` with `Their anchors and curve handles edit on the field too; the side canvas only draws (2026-09-29, field-node-edit spec).` — count words before/after with `scope_budget.py`; the total must stay < 27,000 (16 words of headroom: if the swap adds more than that, shorten elsewhere in the SAME paragraph).
- `docs/scope/5-review-manual-editing.md`: a dated section — the fit export, the re-fit rule and its invariant, the gestures, what left ManualPanel, the edge-drag-does-nothing and the Delete-with-focus behaviours, pointers to `fieldNodeEdit.spec.js` / `field-node-edit.spec.js`.
- `PRODUCT.md` L63-66: append "…and, for a hand-drawn shape, drag its points and curve handles there too."
- Commit `Docs: node editing on the field` + trailer.

---

### Task 7: Rebase, look, PR

- [ ] Confirm #562 merged (`gh pr view 562 --json state,mergedAt`). If not, STOP and report — do not open a PR against `claude/shape-popover`.
- [ ] `git fetch origin && git rebase --onto origin/main claude/shape-popover claude/field-node-edit`; resolve conflicts (MASTER_SCOPE/MEMORY are the likely ones); `node --test`, `cd app && npm test`, `npx playwright test` (all; log; EXIT recorded) all green; `scope_budget.py` under 27,000.
- [ ] Browser look at 1440×900 and 1024×768: anchors/handles on a selected hand-drawn shape, a drag, the menu item; screenshots for the PR body; computed colours resolve.
- [ ] `git push -u origin claude/field-node-edit`; `gh pr create` ready-for-review with a body covering: the fit export, the re-fit invariant (through the real engine), gestures, what left the side canvas, behaviour notes (edge drag does nothing; Delete removes a focused anchor else the shape), follow-ups; `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Arm auto-merge (`gh pr merge --auto --squash`) while `mergeStateStatus` is `BLOCKED`.
