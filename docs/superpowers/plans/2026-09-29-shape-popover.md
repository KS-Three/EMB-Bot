# Shape Popover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Click any shape on the hoop canvas — auto-digitized, hand-drawn, or preset — and edit its stitch attributes in a popover anchored where you clicked.

**Architecture:** The engine gains an additive `shapeOutlines` field (field mm, +y up) so hand-drawn and preset shapes become visible and hit-testable on `EmbroideryField` the way digitized shapes already are. A pure `lib/shapePopover.js` decides which controls a shape gets and what patch each edit produces; `ui/ShapePopover.svelte` renders it; the field opens it on a click (pointer moved < 4 px) and writes every edit through the existing `elupdate` paths, so restitch rules, undo and `.embproj` are untouched.

**Tech Stack:** Svelte 5 (legacy `export let` / `on:` syntax, as the rest of `app/src/ui`), Canvas 2D, vitest + `@testing-library/svelte` (jsdom), Playwright e2e, `node:test` for the engine.

**Spec:** `docs/superpowers/specs/2026-09-29-shape-popover-design.md` — read it first; the plan argues from it.

## Global Constraints

- Branch: `claude/shape-popover` (exists; the spec is its first commit). Work in the main checkout on that branch, or cut a worktree from it — never touch other lanes under `.claude/worktrees/` (CLAUDE.md footgun 2).
- **Byte-identical stitches.** No task changes a stitch, trim, colour block or span order. `node --test` from the repo ROOT must report the same pass count before and after Task 1 (record it in Task 1 step 1).
- **Windows box.** PowerShell 7: `cd app && npm test` works; the engine suite runs from the repo root (`node --test` from `app/` reports 0 tests and exits 0 — that is a trap, not a pass). Never pipe a test run to `tail`.
- **Edit with the Edit tool, never a PowerShell regex round-trip** (UTF-8 corruption, CLAUDE.md footgun 3).
- **Outline space:** engine `shapeOutlines` are FIELD mm, +y up, offsets applied — `T(q)` unrounded ÷ `units.DST_UNITS_PER_MM` (10). No bbox fit on the manual lane (spec §2).
- **Left-click only.** Right-click keeps the tool/border menu; inside `ManualPanel` right-click places a curved node. Do not touch either.
- **Restitch lanes unchanged.** Digitized edits go through `shapeOverrides` exactly as `DigitizePanel.setOverride` writes them (`null`/tier `"auto"` deletes the key; an emptied entry is dropped). No new lane in `editKind`.
- **No new persisted keys.** Not on `shapeOverrides`, not on the manual shape record, not on the `.embproj`.
- **Copy rule:** control labels reuse the Layers row's words ("Stitch type", "Fill angle", "Underlay style", "Border", "Auto border", "No border", "Bean border", "Design (…)"), so the popover and the panel never disagree about what a thing is called.
- Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

---

## File structure

| file | responsibility |
|---|---|
| `src/digitize.js` (modify, ~L388-395 and the shape loop L568-731, return L739) | emit `shapeOutlines`; mark dropped shapes |
| `app/src/lib/manualShapes.js` (modify, `shapesToRegions` L583-611) | pass `id` onto each region shape |
| `app/src/lib/shapeOverlay.js` (modify) | `designOutlinesInFieldMm(design)` — the manual lane's outline reader; pure |
| `app/src/lib/shapePopover.js` (create) | pure control model + patch builders, both lanes |
| `app/src/ui/ShapePopover.svelte` (create) | the anchored dialog; no project knowledge, renders a model, emits `change` / `action` / `close` |
| `app/src/ui/ShapePopover.testHarness.svelte` (create) | test-only parent, same pattern as `ShapePanel.testHarness.svelte` |
| `app/src/ui/EmbroideryField.svelte` (modify) | outlines + hit-test for manual/preset; click-vs-drag; opens/closes the popover; `shapeselect` event |
| `app/src/ui/theme.css` (modify, after `.fieldmenu-sep` ~L735) | `.shapepop` styles mirroring `.fieldmenu` |
| `app/src/App.svelte`, `app/src/ui/ContentStep.svelte`, `app/src/ui/ManualPanel.svelte` (modify) | thread `shapeselect` from the field to the manual panel's selection / edit mode |
| tests | `test/digitize.test.js`, `app/src/lib/manualShapes.spec.js`, `app/src/lib/shapeOverlay.spec.js`, `app/src/lib/shapePopover.spec.js` (create), `app/src/ui/ShapePopover.spec.js` (create), `app/e2e/field-shape-popover.spec.js` (create) |
| docs | `MASTER_SCOPE.md` area 5, `docs/scope/5-review-manual-editing.md`, `PRODUCT.md` L58-63 |

---

### Task 1: Engine emits per-shape outlines; manual shapes carry their id

**Files:**
- Modify: `src/digitize.js:388-395` (after `pxPerFinalMm`), `src/digitize.js:568-571`, `:575`, `:721`, `:739`, and the early return at `:357`
- Modify: `app/src/lib/manualShapes.js:600-610`
- Test: `test/digitize.test.js`, `app/src/lib/manualShapes.spec.js`

**Interfaces:**
- Produces: `design.shapeOutlines: Array<{ id: string, points: [number, number][], holes: [number, number][][], dropped: boolean }>` on every `EMB.buildQualityDesign` result, in INPUT order (before the light→dark sort), one entry per input shape. `id` is `String(shape.id)` or `""`.
- Produces: `shapesToRegions()` region shapes carry `id: String(shape.id)` (or `""`).

- [ ] **Step 1: Record the engine baseline**

Run from the repo root (PowerShell):
```powershell
node --test 2>&1 | Select-String -Pattern "^# (tests|pass|fail|skipped)"
```
Write the four numbers down; Step 8 must reproduce `pass` and `fail` exactly.

- [ ] **Step 2: Write the failing engine tests**

Append to `test/digitize.test.js`:

```js
// ---- shapeOutlines (2026-09-29 spec: click a shape on the canvas) ---------
// Additive field: where each input shape landed, in FIELD mm (+y up, the
// stitches' own space, T() without the integer rounding). The Studio draws
// these over a hand-drawn/preset element so it can be clicked; nothing about
// the stitches may move for it.
test("buildQualityDesign: shapeOutlines land on the stitches, in field mm, ids kept", () => {
  const rect = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 50 }, { x: 0, y: 50 }];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: rect, holes: [], id: "s7", tierOverride: "fill" }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 6, underlay: false,
      targetWidthMm: 40, offsetXMm: 5, offsetYMm: -3 }
  );
  assert.strictEqual(d.shapeOutlines.length, 1);
  const o = d.shapeOutlines[0];
  assert.strictEqual(o.id, "s7");
  assert.strictEqual(o.dropped, false);
  assert.deepStrictEqual(o.holes, []);
  const xs = o.points.map((p) => p[0]), ys = o.points.map((p) => p[1]);
  const near = (a, b) => Math.abs(a - b) <= 1e-6;
  assert.ok(near(Math.max(...xs) - Math.min(...xs), 40), "outline width = targetWidthMm");
  assert.ok(near(Math.max(...ys) - Math.min(...ys), 20), "outline height keeps the 2:1 aspect");
  assert.ok(near((Math.max(...xs) + Math.min(...xs)) / 2, 5), "centred on offsetXMm");
  assert.ok(near((Math.max(...ys) + Math.min(...ys)) / 2, -3), "centred on offsetYMm");
  // The stitches (DST units, 10 per mm) sit inside the outline, give or take
  // the engine's default 0.2 mm pull compensation.
  const sew = d.stitches.filter((s) => s.type === "stitch");
  assert.ok(sew.length > 50);
  for (const s of sew) {
    assert.ok(s.x / 10 >= Math.min(...xs) - 0.5 && s.x / 10 <= Math.max(...xs) + 0.5, "x inside outline");
    assert.ok(s.y / 10 >= Math.min(...ys) - 0.5 && s.y / 10 <= Math.max(...ys) + 0.5, "y inside outline");
  }
});

test("buildQualityDesign: shapeOutlines keep INPUT order across the light-to-dark sort, and flag dropped shapes", () => {
  const sq = (x0, s) => [{ x: x0, y: 0 }, { x: x0 + s, y: 0 }, { x: x0 + s, y: s }, { x: x0, y: s }];
  const d = DG.buildQualityDesign(
    [
      // light colour first: darkOnTop (default true) sews it FIRST anyway, but
      // a dark region listed first would be re-ordered — the outlines must not be.
      { rgb: [10, 10, 10], shapes: [{ outer: sq(0, 40), holes: [], id: "dark" }] },
      { rgb: [240, 240, 240], shapes: [
        { outer: sq(60, 40), holes: [], id: "light" },
        { outer: [{ x: 0, y: 0 }, { x: 1, y: 0 }], holes: [], id: "degenerate" },
      ] },
    ],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, underlay: false }
  );
  assert.deepStrictEqual(d.shapeOutlines.map((o) => o.id), ["dark", "light", "degenerate"]);
  assert.deepStrictEqual(d.shapeOutlines.map((o) => o.dropped), [false, false, true]);
  // The sew order is still light first — proving the outlines did not follow the sort.
  assert.strictEqual(d.colors[0].r, 240);
});

test("buildQualityDesign: a shape with no id gets '' and the legacy polygons input still gets outlines", () => {
  const ring = [{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 50, y: 50 }, { x: 0, y: 50 }];
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], polygons: [ring] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, underlay: false });
  assert.strictEqual(d.shapeOutlines.length, 1);
  assert.strictEqual(d.shapeOutlines[0].id, "");
  assert.strictEqual(d.shapeOutlines[0].points.length, 4);
});

test("buildQualityDesign: an empty design carries an empty shapeOutlines", () => {
  const d = DG.buildQualityDesign([], { garment: { widthIn: 4, heightIn: 4 } });
  assert.deepStrictEqual(d.shapeOutlines, []);
});
```

- [ ] **Step 3: Run them — expect failure**

```powershell
node --test test/digitize.test.js
```
Expected: the four new tests FAIL (`d.shapeOutlines` is `undefined` → `Cannot read properties of undefined`).

- [ ] **Step 4: Implement in `src/digitize.js`**

(a) Early return at L357 — add the field:
```js
    if (!regions.length) return { stitches: [{ x: 0, y: 0, type: "end" }], colors: [], widthMM: 0, heightMM: 0, stitchCount: 0, colorCount: 0, shapeOutlines: [], _debug: { nSatin: 0, nFill: 0, nTrims: 0 } };
```

(b) Immediately after `const pxPerFinalMm = 1 / mmPerPxFinal;` (L391) insert:
```js
    // Per-shape OUTLINES (2026-09-29 spec §3): where each input shape lands,
    // in FIELD mm — the stitches' own space (+y up, offsets applied), i.e.
    // T(q) without the integer rounding, so the Studio can draw a
    // hand-drawn or preset shape over its stitching and hit-test it with the
    // same `toCanvas` it draws the design with. INPUT order, not sew order:
    // the caller's ids are what a click has to map back to, and the sort
    // above is this function's private business. Bookkeeping only — no
    // stitch, order or count changes with it (same posture as `spans`).
    const shapeOutlines = [];
    const outlineByRing = new Map(); // outer ring -> its entry, for dropped-marking below
    {
      const toFieldMm = (q) => [
        ((q.x - cx) * scalePxToDst + offXu) / units.DST_UNITS_PER_MM,
        ((cy - q.y) * scalePxToDst + offYu) / units.DST_UNITS_PER_MM,
      ];
      for (const r of regions.slice().sort((a, b) => a._origIdx - b._origIdx)) {
        const raw = r.shapes || r.polygons.map((p) => ({ outer: p, holes: [] }));
        for (const s of raw) {
          if (!s) continue;
          const outer = Array.isArray(s.outer) ? s.outer : [];
          const entry = {
            id: s.id == null ? "" : String(s.id),
            points: outer.map(toFieldMm),
            holes: (s.holes || []).filter((h) => h && h.length).map((h) => h.map(toFieldMm)),
            dropped: outer.length < 3,
          };
          shapeOutlines.push(entry);
          if (outer.length) outlineByRing.set(outer, entry);
        }
      }
    }
    const dropOutline = (ring) => { const e = outlineByRing.get(ring); if (e) e.dropped = true; };
```

(c) In the shape loop, mark the three skips. At L570-571:
```js
        const poly = shape.outer;
        if (!poly || poly.length < 3) { if (poly) dropOutline(poly); continue; } // see the shapes0 filter's comment above
```
At L575:
```js
        if (area <= 0 || perim <= 0) { dropOutline(poly); continue; }
```
At L721:
```js
        if (!nonEmpty.length) { dropOutline(poly); continue; }
```

(d) Return object at L739 — add `shapeOutlines`:
```js
    return { stitches, colors, widthMM: extent.widthMM, heightMM: extent.heightMM, stitchCount, colorCount: colors.length, runs: spans, shapeOutlines, _debug: { nSatin, nFill, nTrims, nCenterOut } };
```

Note: `regions` is the filtered copy sorted in place at L361, and `_origIdx` was stamped BEFORE that sort, so sorting a copy by `_origIdx` recovers input order. `units` is already in scope (it is used at L378).

- [ ] **Step 5: Run the engine test file — expect pass**

```powershell
node --test test/digitize.test.js
```
Expected: all tests in the file pass, including the four new ones.

- [ ] **Step 6: Write the failing Studio test for the id passthrough**

Append to `app/src/lib/manualShapes.spec.js` (imports at L1-4 already bring `shapesToRegions`):
```js
test("shapesToRegions: the shape's id rides onto the region shape (the field maps clicks back through it)", () => {
  const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const { regions } = shapesToRegions([
    { id: "s3", points: square, curves: {}, stitchType: "fill", colorRgb: [1, 2, 3], angleDeg: null },
    { points: square.map((p) => ({ x: p.x + 200, y: p.y })), curves: {}, stitchType: "satin", colorRgb: [1, 2, 3], angleDeg: null },
  ]);
  expect(regions[0].shapes[0].id).toBe("s3");
  expect(regions[1].shapes[0].id).toBe("");
});
```

- [ ] **Step 7: Run it, then implement**

```powershell
cd app && npx vitest run src/lib/manualShapes.spec.js
```
Expected: FAIL (`expected undefined to be "s3"`).

In `app/src/lib/manualShapes.js`, inside `shapesToRegions`'s `regions.push({ ... shapes: [{` block (L602-608), add the id as the first field:
```js
      shapes: [{
        // The Studio's own shape id, so the engine's spans and outlines
        // (design.runs / design.shapeOutlines) can be mapped back to the shape
        // a click landed on. "" when the caller has none (preset shapes).
        id: shape.id == null ? "" : String(shape.id),
        outer: outer.map((p) => ({ x: p.x, y: p.y })),
```
Re-run: PASS.

- [ ] **Step 8: Byte-identity check — full engine suite**

```powershell
node --test 2>&1 | Select-String -Pattern "^# (tests|pass|fail|skipped)"
```
Expected: `pass` = Step 1's number + 4, `fail` = Step 1's number (which should be 0). Any other delta is a regression — stop and diagnose.

- [ ] **Step 9: Commit**

```powershell
git add src/digitize.js app/src/lib/manualShapes.js test/digitize.test.js app/src/lib/manualShapes.spec.js
git commit -m "Engine: emit per-shape outlines in field mm; manual shapes carry their id

Additive design.shapeOutlines on buildQualityDesign — input order, +y up,
T() unrounded — so a hand-drawn or preset shape can be drawn over its own
stitching and hit-tested on the field. shapesToRegions passes shape.id, so
spans and outlines map back to the Studio's shape. No stitch moves.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: Hand-drawn and preset shapes get outlines and selection on the field

**Files:**
- Modify: `app/src/lib/shapeOverlay.js` (append after `shapeOutlinesInFieldMm`, ~L190)
- Modify: `app/src/ui/EmbroideryField.svelte` — imports L13; `outlinesPxFor` L546-570; `hiddenShapeIds` L579-584; `$:` clear L640-643; `deleteSelectedShape` L645-655; `drawShapeOutlines` L800-830; `onPointerDown`'s `if (edit)` block L1897-1948; `shapeUnderPointer` L1700
- Test: `app/src/lib/shapeOverlay.spec.js`

**Interfaces:**
- Consumes: `design.shapeOutlines` (Task 1).
- Produces: `designOutlinesInFieldMm(design) -> [{ id, points: [[xMm, yMm], ...] }]` (field mm, +y up; dropped / id-less / sub-triangle entries removed).
- Produces (field-internal, used by Tasks 5): `SHAPE_LANES`, `outlinesPxFor(el)` now answers for `manual` and `shape` elements with `rows: []`; `selectedShapeId` may name a manual/preset shape; `deleteSelectedShape()` handles the manual lane.

- [ ] **Step 1: Failing unit test for the reader**

Append to `app/src/lib/shapeOverlay.spec.js` (add `designOutlinesInFieldMm` to the import list at L6-19):
```js
describe("designOutlinesInFieldMm", () => {
  test("passes engine outlines through untouched and drops what cannot be clicked", () => {
    const design = { shapeOutlines: [
      { id: "s1", points: [[0, 0], [10, 0], [10, 5], [0, 5]], holes: [], dropped: false },
      { id: "s2", points: [[0, 0], [1, 0]], holes: [], dropped: true },      // dropped by the engine
      { id: "",   points: [[0, 0], [10, 0], [10, 5]], holes: [], dropped: false }, // no id -> unaddressable
      { id: "s4", points: [[0, 0], [10, 0]], holes: [], dropped: false },     // under a triangle
    ] };
    expect(designOutlinesInFieldMm(design)).toEqual([
      { id: "s1", points: [[0, 0], [10, 0], [10, 5], [0, 5]] },
    ]);
  });
  test("a design without the field, or no design, is an empty list", () => {
    expect(designOutlinesInFieldMm({ stitches: [] })).toEqual([]);
    expect(designOutlinesInFieldMm(null)).toEqual([]);
  });
});
```
Run: `cd app && npx vitest run src/lib/shapeOverlay.spec.js` → FAIL (not exported).

- [ ] **Step 2: Implement the reader**

Append to `app/src/lib/shapeOverlay.js` after `shapeOutlinesInFieldMm`:
```js
// Outlines the ENGINE emitted for a hand-drawn or preset element
// (`buildQualityDesign`'s `shapeOutlines`, 2026-09-29 spec §3). Already in
// field mm, +y up — the stitches' own space — so unlike the digitized lane
// above there is nothing to fit: `toCanvas` draws them as they are. What is
// filtered is what a click could never act on: shapes the engine dropped,
// rings under a triangle, and shapes with no id (nothing to patch).
export function designOutlinesInFieldMm(design) {
  const list = design && Array.isArray(design.shapeOutlines) ? design.shapeOutlines : [];
  const out = [];
  for (const o of list) {
    if (!o || o.dropped || !o.id) continue;
    if (!Array.isArray(o.points) || o.points.length < MIN_RING_POINTS) continue;
    out.push({ id: o.id, points: o.points.map(([x, y]) => [x, y]) });
  }
  return out;
}
```
Run the spec → PASS.

- [ ] **Step 3: Field — one outline source for three lanes**

In `EmbroideryField.svelte`:

(a) Import (L13): add `designOutlinesInFieldMm` to the `shapeOverlay.js` import list.

(b) Above `outlinesPxFor` (before L546) add:
```js
  // The three element types that carry per-shape geometry the field can
  // outline and address (2026-09-29 spec §4). `digitized` shapes come from
  // the service's review payload and need shapeOverlay's bbox fit;
  // `manual` and `shape` (preset) elements come from the browser engine's own
  // `shapeOutlines`, already in field mm.
  const SHAPE_LANES = new Set(["digitized", "manual", "shape"]);

  // Field-mm outlines + review rows for one element, whatever its lane.
  // `rows` is [] on the manual lanes: they have no review payload, no hidden
  // shapes and no pending boundary edits.
  function outlinesMmFor(el) {
    if (!el || !SHAPE_LANES.has(el.type)) return null;
    const pe = peById[el.id];
    if (!pe) return null;
    if (el.type === "digitized") {
      const rows = digitizedRows(el);
      if (!rows || !pe.bboxMm) return null;
      return { rows, mm: shapeOutlinesInFieldMm(rows, pe.bboxMm, el.rotationDeg || 0, pendingBoundaries(el)) };
    }
    return { rows: [], mm: designOutlinesInFieldMm(pe.design) };
  }
```

(c) Replace the body of `outlinesPxFor` (L552-570) with:
```js
  function outlinesPxFor(el) {
    if (!renderResult || !renderResult.toCanvas) return null;
    const src = outlinesMmFor(el);
    if (!src) return null;
    const pe = peById[el.id];
    return {
      el,
      rows: src.rows,
      pe,
      outlines: src.mm.map((o) => ({
        id: o.id,
        points: (liveRing && liveRing.shapeId === o.id ? liveRing.points : o.points)
          .map(([x, y]) => {
            const c = renderResult.toCanvas(x, y);
            return [c.x, c.y];
          }),
      })),
      mmById: new Map(src.mm.map((o) => [o.id, o.points])),
    };
  }
```

(d) `hiddenShapeIds` (L579): make `rows` optional:
```js
  function hiddenShapeIds(el, rows) {
    return new Set([
      ...(rows || []).filter((r) => r && r.stitched === false).map((r) => r.id),
      ...(el.deletedShapeIds || []),
    ]);
  }
```

(e) The `$:` clear at L640-643:
```js
  $: if (project && project.selectedId !== undefined) {
    const sel = selectedElement();
    if (!sel || !SHAPE_LANES.has(sel.type)) selectedShapeId = null;
  }
```

(f) `deleteSelectedShape` (L645-655) — add the manual lane:
```js
  function deleteSelectedShape() {
    if (!selectedShapeId) return false;
    const el = selectedElement();
    if (!el) return false;
    if (el.type === "manual") {
      // Same patch ManualPanel.deleteShape sends: the shape leaves
      // element.shapes, and the panel's own list drops the row.
      const shapes = el.shapes || [];
      if (!shapes.some((s) => s && s.id === selectedShapeId)) return false;
      dispatch("elupdate", { id: el.id, patch: { shapes: shapes.filter((s) => s.id !== selectedShapeId) } });
      selectedShapeId = null;
      shapeEditError = "";
      return true;
    }
    if (el.type !== "digitized") return false; // a preset element IS its one shape; its chip removes it
    const cur = el.deletedShapeIds || [];
    if (cur.includes(selectedShapeId)) return false;
    dispatch("elupdate", { id: el.id, patch: { deletedShapeIds: [...cur, selectedShapeId] } });
    selectedShapeId = null;
    shapeEditError = "";
    return true;
  }
```

(g) `drawShapeOutlines` (L800-812): replace the per-element prologue
```js
    for (const el of project.elements || []) {
      if (el.type !== "digitized") continue;
      const rows = digitizedRows(el);
      if (!rows) continue;
      const pe = peById[el.id];
      if (!pe || !pe.bboxMm) continue;

      const outlines = shapeOutlinesInFieldMm(
        rows, pe.bboxMm, el.rotationDeg || 0, pendingBoundaries(el));
      if (!outlines.length) continue;
```
with
```js
    for (const el of project.elements || []) {
      const src = outlinesMmFor(el);
      if (!src) continue;
      const rows = src.rows;
      const outlines = src.mm;
      if (!outlines.length) continue;
```
The rest of the loop (`pulses.startedAt(el.id)` → 0 for manual lanes since `noteOutlineResults` only registers digitized elements; `hiddenShapeIds(el, rows)`; the cased-line drawing) is unchanged. Do NOT extend the pulse to manual lanes — the pulse means "the app found these", and a hand-drawn shape was not found.

(h) `onPointerDown`'s `if (edit)` block (L1897-1948): node/edge dragging stays digitized-only. Change the inner start:
```js
    const edit = editableOutlinesPx();
    if (edit) {
      const hit = hitOverlay(edit.outlines, p.x, p.y);
      if (hit) {
        // First click on a shape selects it and stops there — no geometry
        // moves until you have said which shape you mean. On the manual and
        // preset lanes it ALWAYS stops there: node editing for hand-drawn
        // shapes lives in ManualPanel for now (2026-09-29 spec §8).
        if (hit.shapeId !== selectedShapeId || edit.el.type !== "digitized") {
          selectedShapeId = hit.shapeId;
          shapeEditError = "";
          drawOverlay();
          return;
        }
```
(the `ring = edit.mmById.get(...)` branch below it is unchanged).

(i) `shapeUnderPointer` (L1700) — the right-click menu stays digitized-only (its items are border items, which the manual lanes have no field for). Leave the `x.type === "digitized"` filter as is.

- [ ] **Step 4: Run the Studio suite**

```powershell
cd app && npm test
```
Expected: green, `53+` files — read the `RUN v…` banner to confirm it resolved `app/`. `EmbroideryField` has no component spec; the regression net here is `shapeOverlay.spec.js` plus the e2e specs `field-outlines`, `field-border-menu` (Task 6 runs them).

- [ ] **Step 5: Look at it**

Start the Studio (`preview_start` name `studio`, or `cd app && npm run dev`), Content step → right-click the field → Basic shape → toggle "Show shape outlines" in the zoom bar. Expected: a cased outline traces the circle's stitching; clicking its edge highlights it (amber); Delete does nothing (preset). Then Draw shapes → draw a 4-point shape → Enter → the outline appears on the field; click its edge → highlighted; Delete removes the shape and the stitches. Screenshot both for the PR.

- [ ] **Step 6: Commit**

```powershell
git add app/src/lib/shapeOverlay.js app/src/lib/shapeOverlay.spec.js app/src/ui/EmbroideryField.svelte
git commit -m "Field: outline and select hand-drawn and preset shapes

designOutlinesInFieldMm reads the engine's shapeOutlines (already field mm,
no fit). outlinesMmFor is the one outline source for all three lanes; the
draw pass, hit-test and Delete key ride it. Node drag stays digitized-only.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: `lib/shapePopover.js` — the control model, pure

**Files:**
- Create: `app/src/lib/shapePopover.js`
- Test: `app/src/lib/shapePopover.spec.js`

**Interfaces:**
- Produces:
  ```js
  laneOf(element) -> "digitized" | "manual" | "shape" | null
  popoverModel({ element, shapeId }) -> null | {
    lane, shapeId, name: string,
    rows: Array<
      | { key: "color",      kind: "thread", rgb: [r,g,b] }
      | { key: "stitchType", kind: "choice", label: "Stitch type", value: string, options: [{ value, label }] }
      | { key: "angle",      kind: "choice", label: "Fill angle",  value: string, options: [{ value, label }] }   // digitized
      | { key: "angle",      kind: "number", label: "Fill angle",  value: number|null, hint: "° (blank = auto)" } // manual
      | { key: "underlay",   kind: "choice", label: "Underlay style", value, options }
      | { key: "border",     kind: "choice", label: "Border", value, options }
      | { key: "editPoints", kind: "action", label: "Edit points" }
      | { key: "delete",     kind: "action", label: "Delete shape", danger: true }
    >
  }
  popoverPatch({ element, shapeId }, key, value) -> object | null   // the `elupdate` patch, sync keys only
  recolorPatch({ element, shapeId }, rgb, deps?) -> Promise<object | null> // digitized colour needs the chart
  DIGITIZED_TIERS, SHAPE_ANGLES, SHAPE_UNDERLAYS, BORDER_OPTIONS (exported option lists)
  ```
- Consumes: `loadPalette`, `nearestInList` from `../lib/threads.js` (injectable via `deps` for tests).

- [ ] **Step 1: Write the failing tests**

Create `app/src/lib/shapePopover.spec.js`:
```js
// The click-to-edit popover's decision table (2026-09-29 spec §5). Pure:
// which controls a shape gets, what they read, and the exact patch each
// edit sends — compared against what the two side panels already send for
// the same edit, so the popover can never disagree with them.
import { describe, expect, test } from "vitest";
import {
  laneOf, popoverModel, popoverPatch, recolorPatch,
  DIGITIZED_TIERS, SHAPE_ANGLES, SHAPE_UNDERLAYS, BORDER_OPTIONS,
} from "./shapePopover.js";

const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
const manualEl = {
  id: 4, type: "manual", underlay: true, sizeMm: null, offsetXMm: 0, offsetYMm: 0,
  shapes: [
    { id: "s1", points: square, curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null },
    { id: "s2", points: square, curves: {}, stitchType: "satin", colorRgb: [200, 0, 0], angleDeg: 30 },
  ],
};
const presetEl = { id: 5, type: "shape", kind: "heart", params: {}, colorRgb: [9, 8, 7], underlay: true, sizeMm: 50, offsetXMm: 0, offsetYMm: 0 };
const digitizedEl = {
  id: 6, type: "digitized",
  params: { border: null },
  review: { brandId: "isacord", shapes: [
    { id: "Sabc", threadNumber: "1301", areaMm2: 123.4, tier: "fill", rgb: [10, 20, 30] },
    { id: "Sdef", threadNumber: "0015", areaMm2: 4.56, tier: "satin", rgb: [250, 250, 250] },
  ] },
  shapeOverrides: { Sabc: { fill_angle_deg: 45, border: "auto" } },
  deletedShapeIds: [],
};

describe("laneOf", () => {
  test("names the three shape lanes and nothing else", () => {
    expect(laneOf(manualEl)).toBe("manual");
    expect(laneOf(presetEl)).toBe("shape");
    expect(laneOf(digitizedEl)).toBe("digitized");
    expect(laneOf({ type: "text" })).toBeNull();
    expect(laneOf(null)).toBeNull();
  });
});

describe("popoverModel — manual lane", () => {
  test("a fill shape: colour, Fill/Satin, numeric angle, Edit points, Delete", () => {
    const m = popoverModel({ element: manualEl, shapeId: "s1" });
    expect(m.lane).toBe("manual");
    expect(m.name).toBe("Shape 1 · Fill");
    expect(m.rows.map((r) => r.key)).toEqual(["color", "stitchType", "angle", "editPoints", "delete"]);
    expect(m.rows[0]).toEqual({ key: "color", kind: "thread", rgb: [20, 20, 20] });
    expect(m.rows[1].options).toEqual([{ value: "fill", label: "Fill" }, { value: "satin", label: "Satin" }]);
    expect(m.rows[1].value).toBe("fill");
    expect(m.rows[2]).toEqual({ key: "angle", kind: "number", label: "Fill angle", value: null, hint: "° (blank = auto)" });
  });
  test("a satin shape reads its own values", () => {
    const m = popoverModel({ element: manualEl, shapeId: "s2" });
    expect(m.name).toBe("Shape 2 · Satin");
    expect(m.rows[1].value).toBe("satin");
    expect(m.rows[2].value).toBe(30);
  });
  test("an unknown shape id is null", () => {
    expect(popoverModel({ element: manualEl, shapeId: "nope" })).toBeNull();
  });
});

describe("popoverPatch — manual lane", () => {
  test("stitchType / angle / colour rewrite ONLY that shape, exactly as ManualPanel.updateShape does", () => {
    const ctx = { element: manualEl, shapeId: "s1" };
    const p1 = popoverPatch(ctx, "stitchType", "satin");
    expect(p1.shapes[0]).toEqual({ ...manualEl.shapes[0], stitchType: "satin" });
    expect(p1.shapes[1]).toBe(manualEl.shapes[1]); // untouched, same reference
    expect(popoverPatch(ctx, "angle", 90).shapes[0].angleDeg).toBe(90);
    expect(popoverPatch(ctx, "angle", "").shapes[0].angleDeg).toBeNull();
    expect(popoverPatch(ctx, "angle", "abc").shapes[0].angleDeg).toBeNull();
    expect(popoverPatch(ctx, "color", [1, 2, 3]).shapes[0].colorRgb).toEqual([1, 2, 3]);
  });
  test("delete removes the shape, as ManualPanel.deleteShape does", () => {
    expect(popoverPatch({ element: manualEl, shapeId: "s1" }, "delete").shapes.map((s) => s.id)).toEqual(["s2"]);
  });
  test("editPoints is an action, not a patch", () => {
    expect(popoverPatch({ element: manualEl, shapeId: "s1" }, "editPoints")).toBeNull();
  });
});

describe("preset lane", () => {
  test("name is the kind; colour is the only control", () => {
    const m = popoverModel({ element: presetEl, shapeId: "" });
    expect(m.name).toBe("Heart");
    expect(m.rows).toEqual([{ key: "color", kind: "thread", rgb: [9, 8, 7] }]);
    expect(popoverPatch({ element: presetEl, shapeId: "" }, "color", [1, 1, 1])).toEqual({ colorRgb: [1, 1, 1] });
    expect(popoverPatch({ element: presetEl, shapeId: "" }, "delete")).toBeNull();
  });
});

describe("popoverModel — digitized lane", () => {
  test("a fill shape gets the Layers row's full control set and reads its overrides", () => {
    const m = popoverModel({ element: digitizedEl, shapeId: "Sabc" });
    expect(m.name).toBe("Thread #1301 · 123 mm²");
    expect(m.rows.map((r) => r.key)).toEqual(["color", "stitchType", "angle", "underlay", "border", "editPoints", "delete"]);
    expect(m.rows[0].rgb).toEqual([10, 20, 30]);
    expect(m.rows[1].value).toBe("auto");
    // The Layers row's ten tiers, with "Auto" saying what auto resolved to.
    expect(m.rows[1].options).toHaveLength(DIGITIZED_TIERS.length);
    expect(m.rows[1].options[0]).toEqual({ value: "auto", label: "Auto (fill)" });
    expect(m.rows[1].options.slice(1)).toEqual(DIGITIZED_TIERS.slice(1));
    expect(m.rows[2].value).toBe("45");
    expect(m.rows[2].options).toEqual(SHAPE_ANGLES);
    expect(m.rows[3].value).toBe("auto");
    expect(m.rows[3].options).toEqual(SHAPE_UNDERLAYS);
    expect(m.rows[4].value).toBe("auto");
    expect(m.rows[4].options).toEqual(BORDER_OPTIONS(null));
    expect(BORDER_OPTIONS(null)[0].label).toBe("Design (automatic)");
    expect(BORDER_OPTIONS("bean")[0].label).toBe("Design (bean)");
  });
  test("a satin shape hides the fill-only rows (angle, underlay), as the Layers row does", () => {
    const m = popoverModel({ element: digitizedEl, shapeId: "Sdef" });
    expect(m.name).toBe("Thread #0015 · 4.6 mm²");
    expect(m.rows.map((r) => r.key)).toEqual(["color", "stitchType", "border", "editPoints", "delete"]);
  });
  test("a tier override to fill brings the fill rows back", () => {
    const el = { ...digitizedEl, shapeOverrides: { Sdef: { tier: "fill" } } };
    expect(popoverModel({ element: el, shapeId: "Sdef" }).rows.map((r) => r.key)).toContain("underlay");
  });
  test("a deleted or unknown shape is null", () => {
    expect(popoverModel({ element: { ...digitizedEl, deletedShapeIds: ["Sabc"] }, shapeId: "Sabc" })).toBeNull();
    expect(popoverModel({ element: digitizedEl, shapeId: "S404" })).toBeNull();
  });
});

describe("popoverPatch — digitized lane mirrors DigitizePanel.setOverride", () => {
  const ctx = { element: digitizedEl, shapeId: "Sabc" };
  test("tier: a value sets it, 'auto' clears it; other fields on the entry survive", () => {
    expect(popoverPatch(ctx, "stitchType", "satin").shapeOverrides.Sabc).toEqual({ fill_angle_deg: 45, border: "auto", tier: "satin" });
    expect(popoverPatch(ctx, "stitchType", "auto").shapeOverrides.Sabc).toEqual({ fill_angle_deg: 45, border: "auto" });
  });
  test("angle and underlay: 'auto' clears, a value parses/sets", () => {
    expect(popoverPatch(ctx, "angle", "90").shapeOverrides.Sabc.fill_angle_deg).toBe(90);
    expect(popoverPatch(ctx, "angle", "auto").shapeOverrides.Sabc.fill_angle_deg).toBeUndefined();
    expect(popoverPatch(ctx, "underlay", "edge_run").shapeOverrides.Sabc.underlay_style).toBe("edge_run");
    expect(popoverPatch(ctx, "underlay", "auto").shapeOverrides.Sabc.underlay_style).toBeUndefined();
  });
  test("border: 'default' clears the key (the design setting), any other word is stored", () => {
    expect(popoverPatch(ctx, "border", "off").shapeOverrides.Sabc.border).toBe("off");
    expect(popoverPatch(ctx, "border", "default").shapeOverrides.Sabc.border).toBeUndefined();
  });
  test("an entry emptied by a clear disappears entirely", () => {
    const el = { ...digitizedEl, shapeOverrides: { Sabc: { border: "auto" } } };
    expect(popoverPatch({ element: el, shapeId: "Sabc" }, "border", "default")).toEqual({ shapeOverrides: {} });
  });
  test("delete appends to deletedShapeIds once", () => {
    expect(popoverPatch(ctx, "delete")).toEqual({ deletedShapeIds: ["Sabc"] });
    expect(popoverPatch({ element: { ...digitizedEl, deletedShapeIds: ["Sabc"] }, shapeId: "Sabc" }, "delete")).toBeNull();
  });
  test("colour is async on this lane: popoverPatch declines, recolorPatch resolves through the chart", async () => {
    expect(popoverPatch(ctx, "color", [1, 2, 3])).toBeNull();
    const deps = {
      loadPalette: async (id) => ({ id, threads: [{ index: 0, rgb: [0, 0, 0] }, { index: 7, rgb: [250, 10, 10] }] }),
      nearestInList: (list, rgb) => list[1],
    };
    expect(await recolorPatch(ctx, [255, 0, 0], deps)).toEqual({
      shapeOverrides: { Sabc: { fill_angle_deg: 45, border: "auto", thread_index: 7, rgb: [250, 10, 10] } },
    });
  });
  test("recolorPatch is null when the chart cannot be loaded or is not the job's", async () => {
    expect(await recolorPatch(ctx, [1, 1, 1], { loadPalette: async () => { throw new Error("offline"); }, nearestInList: () => null })).toBeNull();
    expect(await recolorPatch(ctx, [1, 1, 1], { loadPalette: async () => ({ id: "madeira", threads: [] }), nearestInList: () => null })).toBeNull();
  });
});
```

- [ ] **Step 2: Run — expect failure**

```powershell
cd app && npx vitest run src/lib/shapePopover.spec.js
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `app/src/lib/shapePopover.js`**

```js
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

// ---- names ------------------------------------------------------------------
// ManualPanel.summary and EmbroideryField.shapeMenuName, reproduced so the
// popover's heading reads like the row it stands in for.
function manualName(shape) {
  return `Shape ${String(shape.id).replace(/^s/, "")} · ${shape.stitchType === "satin" ? "Satin" : "Fill"}`;
}
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
    return {
      lane, shapeId, name: manualName(shape),
      rows: [
        { key: "color", kind: "thread", rgb: shape.colorRgb },
        { key: "stitchType", kind: "choice", label: "Stitch type", value: shape.stitchType === "satin" ? "satin" : "fill", options: MANUAL_TIERS },
        { key: "angle", kind: "number", label: "Fill angle", value: shape.angleDeg == null ? null : shape.angleDeg, hint: "° (blank = auto)" },
        { key: "editPoints", kind: "action", label: "Edit points" },
        { key: "delete", kind: "action", label: "Delete shape", danger: true },
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
// lookup, reproduced. `deps` is for tests; the app passes nothing.
export async function recolorPatch({ element, shapeId }, rgb, deps = {}) {
  const load = deps.loadPalette || loadPalette;
  const nearest = deps.nearestInList || nearestInList;
  const brand = (element.review && element.review.brandId) || "isacord";
  try {
    const pal = await load(brand);
    if (!pal || pal.id !== brand) return null;
    const n = nearest(pal.threads, rgb);
    if (!n) return null;
    return overridePatch(element, shapeId, { thread_index: n.index, rgb: [...n.rgb] });
  } catch (e) {
    return null;
  }
}
```

- [ ] **Step 4: Run — expect pass**

```powershell
cd app && npx vitest run src/lib/shapePopover.spec.js
```
Expected: all green. If `manualName` for id `"s1"` reads "Shape 1 · Fill" — matches `ManualPanel.summary`.

- [ ] **Step 5: Commit**

```powershell
git add app/src/lib/shapePopover.js app/src/lib/shapePopover.spec.js
git commit -m "shapePopover.js: the click-to-edit control model, pure

Which controls a shape gets per lane, what they read, and the exact patch
each edit sends — reproducing DigitizePanel.setOverride/recolorShape and
ManualPanel.updateShape/deleteShape so the popover can never disagree with
the side panels. Digitized recolour is async through the thread chart.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `ShapePopover.svelte` — the dialog

**Files:**
- Create: `app/src/ui/ShapePopover.svelte`, `app/src/ui/ShapePopover.testHarness.svelte`
- Modify: `app/src/ui/theme.css` (append after `.fieldmenu-sep`, ~L739)
- Test: `app/src/ui/ShapePopover.spec.js`

**Interfaces:**
- Props: `model` (from `popoverModel`), `anchor: { x, y }` (px inside `.hoop`), `bounds: { w, h }` (the `.hoop` box, for clamping).
- Events: `change { key, value }` for `thread` / `choice` / `number` rows; `action { key }` for `action` rows; `close`.
- Markup contract (the e2e and field rely on it): root `div.shapepop[role="dialog"][aria-label=model.name]`; choice rows are `<select aria-label={row.label}>`; number row is `<input type="number" aria-label="Fill angle">`; actions are `<button>` with the row label; ThreadPicker rendered `compact` with `name={model.name}`.

- [ ] **Step 1: Harness + failing component tests**

`app/src/ui/ShapePopover.testHarness.svelte`:
```svelte
<script>
  import ShapePopover from "./ShapePopover.svelte";
  // Test-only parent (see ShapePopover.spec.js) — Svelte 5 gives a test no
  // way to observe a mounted component's dispatched events, so a real parent
  // records them. Same pattern as ShapePanel.testHarness.svelte.
  export let model;
  export let anchor = { x: 40, y: 40 };
  export let bounds = { w: 800, h: 600 };
  export let onEvent = () => {};
</script>

<div style="position: relative; width: {bounds.w}px; height: {bounds.h}px">
  <ShapePopover
    {model} {anchor} {bounds}
    on:change={(e) => onEvent("change", e.detail)}
    on:action={(e) => onEvent("action", e.detail)}
    on:close={() => onEvent("close", null)}
  />
</div>
```

`app/src/ui/ShapePopover.spec.js`:
```js
// @vitest-environment jsdom
// ShapePopover renders a shapePopover.js model and emits what the field
// needs; the model's contents are shapePopover.spec.js's business. Uses the
// render-through-a-real-parent harness ShapePanel.spec.js established.
import { beforeAll, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { popoverModel } from "../lib/shapePopover.js";

let Harness;
beforeAll(async () => {
  globalThis.fetch = () => Promise.reject(new Error("no network in tests")); // ThreadPicker's catalog loader
  ({ default: Harness } = await import("./ShapePopover.testHarness.svelte"));
});

const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
const manualEl = { id: 4, type: "manual", shapes: [
  { id: "s1", points: square, curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null },
] };
const digitizedEl = { id: 6, type: "digitized", params: { border: null },
  review: { brandId: "isacord", shapes: [{ id: "Sabc", threadNumber: "1301", areaMm2: 123.4, tier: "fill", rgb: [10, 20, 30] }] },
  shapeOverrides: {}, deletedShapeIds: [] };

function renderPop(model, extra = {}) {
  const events = [];
  const utils = render(Harness, { model, onEvent: (kind, detail) => events.push({ kind, detail }), ...extra });
  return { events, ...utils };
}

test("is a dialog named after the shape, and focus lands inside it", () => {
  const { getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }));
  const dlg = getByRole("dialog", { name: "Shape 1 · Fill" });
  expect(dlg).toBeInTheDocument();
  expect(dlg.contains(document.activeElement)).toBe(true);
});

test("manual lane: Fill/Satin select, numeric angle, Edit points, Delete — each emits its key", async () => {
  const { events, getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }));
  const tier = getByRole("combobox", { name: "Stitch type" });
  expect(tier).toHaveValue("fill");
  await fireEvent.change(tier, { target: { value: "satin" } });
  const angle = getByRole("spinbutton", { name: "Fill angle" });
  await fireEvent.input(angle, { target: { value: "60" } });
  await fireEvent.click(getByRole("button", { name: "Edit points" }));
  await fireEvent.click(getByRole("button", { name: "Delete shape" }));
  expect(events).toEqual([
    { kind: "change", detail: { key: "stitchType", value: "satin" } },
    { kind: "change", detail: { key: "angle", value: "60" } },
    { kind: "action", detail: { key: "editPoints" } },
    { kind: "action", detail: { key: "delete" } },
  ]);
});

test("digitized lane: the Layers row's selects, in its words", async () => {
  const { events, getByRole } = renderPop(popoverModel({ element: digitizedEl, shapeId: "Sabc" }));
  expect(getByRole("dialog", { name: "Thread #1301 · 123 mm²" })).toBeInTheDocument();
  expect(getByRole("combobox", { name: "Stitch type" })).toHaveValue("auto");
  expect(getByRole("combobox", { name: "Fill angle" })).toHaveValue("auto");
  expect(getByRole("combobox", { name: "Underlay style" })).toHaveValue("auto");
  const border = getByRole("combobox", { name: "Border" });
  expect(border).toHaveValue("default");
  await fireEvent.change(border, { target: { value: "auto" } });
  expect(events).toEqual([{ kind: "change", detail: { key: "border", value: "auto" } }]);
});

test("Escape closes", async () => {
  const { events, getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }));
  await fireEvent.keyDown(getByRole("dialog"), { key: "Escape" });
  expect(events).toEqual([{ kind: "close", detail: null }]);
});

test("clamps inside its bounds", () => {
  const { getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }), {
    anchor: { x: 790, y: 590 }, bounds: { w: 800, h: 600 },
  });
  const dlg = getByRole("dialog");
  // jsdom has no layout, so the component's fallback size (POP_W/POP_H) is
  // what gets clamped; the assertion is that the anchor was NOT used raw.
  expect(parseFloat(dlg.style.left)).toBeLessThan(790);
  expect(parseFloat(dlg.style.top)).toBeLessThan(590);
});
```

Run: `cd app && npx vitest run src/ui/ShapePopover.spec.js` → FAIL (module not found).

- [ ] **Step 2: Implement the component**

`app/src/ui/ShapePopover.svelte`:
```svelte
<script>
  // The click-to-edit popover (2026-09-29 spec §5). Renders a
  // lib/shapePopover.js model where the shape was clicked and emits what the
  // field then turns into an `elupdate` patch. Knows nothing about projects
  // or lanes — the model is the whole contract — so the same markup serves an
  // auto-digitized shape and a hand-drawn one.
  import { createEventDispatcher, onMount, tick } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";

  export let model;
  export let anchor = { x: 0, y: 0 };   // px inside the positioned parent (.hoop)
  export let bounds = { w: 0, h: 0 };   // that parent's box, for clamping

  const d = createEventDispatcher();
  let root;
  // Fallback size until the browser has laid the dialog out (jsdom never
  // does): roughly the rendered size at the default font scale.
  const POP_W = 260;
  const POP_H = 240;
  let w = POP_W;
  let h = POP_H;

  // Sit just right/below the click, but never past the parent's edge: on a
  // short viewport the dialog may cover the shape — the outline highlight
  // stays visible around it (spec §6).
  $: left = Math.max(0, Math.min(anchor.x + 8, Math.max(0, (bounds.w || Infinity) - w - 4)));
  $: top = Math.max(0, Math.min(anchor.y + 8, Math.max(0, (bounds.h || Infinity) - h - 4)));

  onMount(async () => {
    await tick();
    if (root) {
      const r = root.getBoundingClientRect();
      if (r.width) w = r.width;
      if (r.height) h = r.height;
      const first = root.querySelector("select, input, button");
      (first || root).focus();
    }
  });

  function onKey(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      d("close");
    }
  }
</script>

<!-- role=dialog with a real name: the shape's own, so a screen reader hears
     which shape it is about to change. Escape closes; the field closes it on
     an outside pointerdown (EmbroideryField.onWindowPointerDown). -->
<div
  class="shapepop"
  role="dialog"
  aria-label={model.name}
  tabindex="-1"
  bind:this={root}
  style="left: {left}px; top: {top}px"
  on:keydown={onKey}
>
  <div class="shapepop-head">{model.name}</div>
  {#each model.rows as row (row.key)}
    {#if row.kind === "thread"}
      <div class="shapepop-row">
        <span class="shapepop-label">Color</span>
        <ThreadPicker compact rgb={row.rgb} name={model.name} on:pick={(e) => d("change", { key: "color", value: e.detail })} />
      </div>
    {:else if row.kind === "choice"}
      <label class="shapepop-row">
        <span class="shapepop-label">{row.label}</span>
        <select value={row.value} aria-label={row.label} on:change={(e) => d("change", { key: row.key, value: e.currentTarget.value })}>
          {#each row.options as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </label>
    {:else if row.kind === "number"}
      <label class="shapepop-row">
        <span class="shapepop-label">{row.label}</span>
        <input
          type="number" step="1" placeholder="auto" aria-label={row.label}
          value={row.value == null ? "" : row.value}
          on:input={(e) => d("change", { key: row.key, value: e.currentTarget.value })}
        />
        {#if row.hint}<span class="shapepop-hint">{row.hint}</span>{/if}
      </label>
    {:else if row.kind === "action"}
      <button type="button" class="shapepop-action" class:danger={row.danger} on:click={() => d("action", { key: row.key })}>
        {row.label}
      </button>
    {/if}
  {/each}
</div>
```

Append to `app/src/ui/theme.css` after `.fieldmenu-sep`:
```css
/* Click-to-edit popover on the design canvas (EmbroideryField ->
   ShapePopover, 2026-09-29). Same surface as the right-click menu above,
   because it is the same kind of thing — a per-shape decision made where the
   shape is — laid out as labelled rows rather than menu items. Absolutely
   positioned inside .hoop. */
.shapepop {
  position: absolute;
  z-index: 6;
  min-width: 15rem;
  padding: var(--space-2);
  background: var(--surface, #fff);
  border: 1px solid var(--border);
  border-radius: var(--radius-m);
  box-shadow: var(--shadow-2);
  font-size: var(--fs-sm);
  color: var(--ink);
}
.shapepop:focus { outline: none; }
.shapepop-head {
  padding: 0 var(--space-1) var(--space-2);
  font-size: var(--fs-sm);
  color: var(--muted);
  white-space: nowrap;
}
.shapepop-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1);
}
.shapepop-label { flex: 0 0 5.5rem; color: var(--muted); }
.shapepop-row select,
.shapepop-row input[type="number"] {
  flex: 1 1 auto;
  min-width: 0;
  font: inherit;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-s);
  background: var(--surface, #fff);
  color: var(--ink);
}
.shapepop-row input[type="number"] { max-width: 5rem; }
.shapepop-hint { color: var(--muted); font-size: var(--fs-xs); white-space: nowrap; }
.shapepop-action {
  display: block;
  width: 100%;
  margin-top: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 0;
  border-radius: var(--radius-s);
  background: none;
  text-align: left;
  font: inherit;
  color: var(--ink);
  cursor: pointer;
}
.shapepop-action:hover,
.shapepop-action:focus-visible { background: var(--tint); }
.shapepop-action.danger { color: var(--danger-text, #b42318); }
```
Check `--danger-text` exists in `theme.css` (`grep -n "danger" app/src/ui/theme.css`); if the token has another name there, use that one.

- [ ] **Step 3: Run the component spec — expect pass**

```powershell
cd app && npx vitest run src/ui/ShapePopover.spec.js
```
Expected: 5 pass. If the focus test fails under jsdom because `tick()` runs after the assertion, move the focus call out of the `await tick()` (call `focus()` synchronously in `onMount` first, then measure after the tick).

- [ ] **Step 4: Commit**

```powershell
git add app/src/ui/ShapePopover.svelte app/src/ui/ShapePopover.testHarness.svelte app/src/ui/ShapePopover.spec.js app/src/ui/theme.css
git commit -m "ShapePopover.svelte: the anchored per-shape dialog

Renders a shapePopover.js model where the click landed, clamped inside the
hoop, focus inside, Escape closes; emits change/action for the field to
turn into patches. No project knowledge — the model is the contract.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: Wire the popover into the field; sync the manual panel

**Files:**
- Modify: `app/src/ui/EmbroideryField.svelte` — imports L13-22; state near L524; `onWindowKey` L745; `onWindowPointerDown` L1793; `onPointerDown` `if (edit)` block (Task 2 h) and the body-drag start L1985-2010; `endDrag` L2168; template after the `{#if fieldMenu}` block L2306
- Modify: `app/src/App.svelte` (ContentStep props L1121-1136, field events L1209-1220), `app/src/ui/ContentStep.svelte` (L315), `app/src/ui/ManualPanel.svelte` (props L32-41, after `stopShapeEdit` L541)

**Interfaces:**
- Field state: `shapePop: null | { x, y }` (px inside `.hoop`), `popModel` derived from `(selectedElement(), selectedShapeId)`.
- Field event (new): `shapeselect { elementId, shapeId, edit: boolean }` → App → ContentStep → ManualPanel prop `fieldSelect: null | { shapeId, edit, n }`.
- Field constant: `CLICK_PX = 4` — a pointer that travels less than this between down and up is a click.

- [ ] **Step 1: Field — state, open/close, patches**

(a) Imports:
```js
  import { popoverModel, popoverPatch, recolorPatch } from "../lib/shapePopover.js";
  import ShapePopover from "./ShapePopover.svelte";
```

(b) After `let shapeEditError = "";` (L527) add:
```js
  // The click-to-edit popover (2026-09-29 spec §5). Open when a CLICK — a
  // press and release that travelled under CLICK_PX — lands on or inside a
  // shape; the shape is selected first so the amber highlight shows what the
  // controls act on. {x, y} are offsets inside .hoop, like fieldMenu's.
  const CLICK_PX = 4;
  let shapePop = null;
  let hoopBounds = { w: 0, h: 0 };
  $: popModel = shapePop && selectedShapeId && project
    ? popoverModel({ element: selectedElement(), shapeId: selectedShapeId })
    : null;
  // A shape that stopped existing (deleted, or gone in a new result) closes it.
  $: if (shapePop && !popModel) shapePop = null;

  function openShapePop(e) {
    if (!canvas || !hoopEl) return;
    const r = canvas.getBoundingClientRect();
    const hb = hoopEl.getBoundingClientRect();
    hoopBounds = { w: hb.width, h: hb.height };
    shapePop = { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  // Which shape of `el` a canvas point is on or inside — the outline the
  // point is ON wins, else the smallest ring it is INSIDE (a counter beats
  // its surround). Hidden and deleted shapes are not offered.
  function shapeAtPoint(el, p) {
    const edit = outlinesPxFor(el);
    if (!edit) return null;
    const hidden = hiddenShapeIds(el, edit.rows);
    const live = edit.outlines.filter((o) => !hidden.has(o.id));
    return hitOverlay(live, p.x, p.y) || hitShapeInterior(live, p.x, p.y);
  }

  async function onPopChange(e) {
    const el = selectedElement();
    if (!el || !selectedShapeId) return;
    const { key, value } = e.detail;
    const ctx = { element: el, shapeId: selectedShapeId };
    let patch = popoverPatch(ctx, key, value);
    if (!patch && key === "color" && el.type === "digitized") patch = await recolorPatch(ctx, value);
    if (!patch) {
      if (key === "color") shapeEditError = "Couldn't match that color to the job's thread chart.";
      return;
    }
    dispatch("elupdate", { id: el.id, patch });
  }

  function onPopAction(e) {
    const el = selectedElement();
    if (!el || !selectedShapeId) return;
    const { key } = e.detail;
    if (key === "delete") {
      const patch = popoverPatch({ element: el, shapeId: selectedShapeId }, "delete");
      shapePop = null;
      if (patch) dispatch("elupdate", { id: el.id, patch });
      selectedShapeId = null;
      drawOverlay();
      return;
    }
    if (key === "editPoints") {
      // Digitized: selection already arms node mode on the canvas, so the
      // popover just gets out of the way. Manual: the nodes live on
      // ManualPanel's canvas for now — hand it the shape and ask for edit mode.
      shapePop = null;
      if (el.type === "manual") dispatch("shapeselect", { elementId: el.id, shapeId: selectedShapeId, edit: true });
      drawOverlay();
    }
  }
```
`hoopEl` already exists (`bind:this={hoopEl}` on `.hoop`, L2231).

(c) `onWindowKey` (L745) — Escape closes the popover before the menu check:
```js
    if (e.key === "Escape" && shapePop) {
      shapePop = null;
      e.preventDefault();
      return;
    }
```
(the Delete/Backspace path below already calls `deleteSelectedShape`; add `shapePop = null;` right after a successful delete there: `if (deleteSelectedShape()) { shapePop = null; e.preventDefault(); }`).

(d) `onWindowPointerDown` (L1793):
```js
  function onWindowPointerDown(e) {
    const inside = (cls) => e.target && e.target.closest && e.target.closest(cls);
    if (fieldMenu && !inside(".fieldmenu")) fieldMenu = null;
    // A press anywhere but on the popover (or its ThreadPicker's floating
    // list, which portals under .tp-pop) closes it; the canvas press that
    // follows decides whether another shape opens it again.
    if (shapePop && !inside(".shapepop") && !inside(".tp-pop")) shapePop = null;
  }
```
Check ThreadPicker's popover class with `grep -n "class=\"tp-" app/src/ui/ThreadPicker.svelte` and use the real root class of its open list in place of `.tp-pop`.

(e) `onPointerDown` — in Task 2(h)'s select-and-return branch, also open the popover (both lanes) when the click lands on an outline:
```js
        if (hit.shapeId !== selectedShapeId || edit.el.type !== "digitized") {
          selectedShapeId = hit.shapeId;
          shapeEditError = "";
          openShapePop(e);
          drawOverlay();
          return;
        }
```
And where the body-drag starts (after `dragStartPx = p;` at ~L1990) record the press event's client point for the click test:
```js
    pressClient = { x: e.clientX, y: e.clientY, px: p };
```
with `let pressClient = null;` declared next to `shapePop`.

(f) `endDrag` (L2168) — before `dragMode = null;` add the click test:
```js
    // A press-and-release that did not travel is a CLICK, and a click inside
    // a shape opens its popover (spec §4). Tested on the element the press
    // selected, at the RELEASE point.
    if (dragMode === "move" && pressClient && e && typeof e.clientX === "number") {
      const moved = Math.hypot(e.clientX - pressClient.x, e.clientY - pressClient.y);
      if (moved < CLICK_PX) {
        const el = selectedElement();
        const p = canvasPointFromEvent(e);
        const hit = el && SHAPE_LANES.has(el.type) ? shapeAtPoint(el, p) : null;
        if (hit) {
          selectedShapeId = hit.shapeId;
          shapeEditError = "";
          openShapePop(e);
        } else if (selectedShapeId) {
          selectedShapeId = null;
          shapePop = null;
        }
        drawOverlay();
      }
    }
    pressClient = null;
```
Note `canvasPointFromEvent` uses `canvas.width / r.width / dpr`, the same conversion the press used, so the hit-test runs in the space `outlinesPxFor` produced.

(g) Template — after the `{#if fieldMenu} … {/if}` block (L2306), inside `.hoop`:
```svelte
    {#if popModel && shapePop}
      <ShapePopover
        model={popModel}
        anchor={shapePop}
        bounds={hoopBounds}
        on:change={onPopChange}
        on:action={onPopAction}
        on:close={() => { shapePop = null; }}
      />
    {/if}
```

- [ ] **Step 2: Thread `shapeselect` to ManualPanel**

`App.svelte`: add state `let fieldShapeSelect = null;` near the other UI state; on the `<EmbroideryField>` (L1209) add
```svelte
      on:shapeselect={(e) => { fieldShapeSelect = { ...e.detail, n: (fieldShapeSelect ? fieldShapeSelect.n : 0) + 1 }; }}
```
and pass `{fieldShapeSelect}` into `<ContentStep>` (L1121).

`ContentStep.svelte`: `export let fieldShapeSelect = null;` and at L315:
```svelte
      <ManualPanel element={el} fieldSelect={fieldShapeSelect && fieldShapeSelect.elementId === el.id ? fieldShapeSelect : null} on:elupdate={(e) => d("elupdate", e.detail)} />
```

`ManualPanel.svelte`: after `export let traceWorkImage = null;` (L41):
```js
  // A selection made ON THE FIELD (EmbroideryField's click-to-edit popover,
  // 2026-09-29): { shapeId, edit, n }. `n` changes on every field click so
  // the same shape clicked twice still re-fires; `edit` asks for vertex
  // mode, which lives on this canvas for hand-drawn shapes for now.
  export let fieldSelect = null;
  let fieldSelectSeen = 0;
```
and after `stopShapeEdit` (L541):
```js
  $: if (fieldSelect && fieldSelect.n !== fieldSelectSeen) {
    fieldSelectSeen = fieldSelect.n;
    if (shapes.some((s) => s.id === fieldSelect.shapeId)) {
      stopShapeEdit();
      selectedShapeId = fieldSelect.shapeId;
      if (fieldSelect.edit && !draft.length) startShapeEdit(fieldSelect.shapeId);
      if (canvasEl && typeof canvasEl.scrollIntoView === "function") canvasEl.scrollIntoView({ block: "nearest" });
    }
  }
```
(`shapes` is the panel's existing derived list of `element.shapes`; confirm its name at the top of the script and use it.)

Also, so selecting on the field highlights the row WITHOUT edit mode, the field dispatches `shapeselect` with `edit: false` whenever it selects a manual shape. In `openShapePop`'s two call sites (Task 5 e/f), after `selectedShapeId = hit.shapeId;` add:
```js
          if (el.type === "manual") dispatch("shapeselect", { elementId: el.id, shapeId: hit.shapeId, edit: false });
```
(in (e) the element is `edit.el`).

- [ ] **Step 3: Studio suite + drive it**

```powershell
cd app && npm test
```
Expected: green. Then in the running Studio: draw a hand-drawn shape → click INSIDE it on the field → the dialog opens at the click, named "Shape 1 · Fill", the side panel's row highlights → pick Satin → the stats line changes and the side panel's Satin button is active → Edit points → the popover closes and the side canvas shows the shape's vertices in edit mode → Escape → nothing open. Basic shape → click inside → "Circle" dialog with only the colour swatch. Drag from inside a shape → the element moves, no dialog. Screenshot the open dialog on both lanes.

- [ ] **Step 4: Commit**

```powershell
git add app/src/ui/EmbroideryField.svelte app/src/App.svelte app/src/ui/ContentStep.svelte app/src/ui/ManualPanel.svelte
git commit -m "Field: click a shape, edit it in the popover — both lanes

A press-and-release under 4 px on or inside a shape selects it and opens
ShapePopover at the click; edits go through popoverPatch/recolorPatch into
the same elupdate paths the panels use. Escape / outside press close it.
A manual-lane selection syncs to ManualPanel; Edit points enters its vertex
mode there. Drags still move the element.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: End-to-end, both lanes

**Files:**
- Create: `app/e2e/field-shape-popover.spec.js`

**Interfaces:**
- Consumes the markup contract from Task 4 (`role=dialog`, select `aria-label`s), the `.fieldmenu` menu, `span.stats` (the field's caption) and `.dgp-stats` (the Digitize panel's line).

- [ ] **Step 1: Write the spec**

```js
// End-to-end for the click-to-edit popover (2026-09-29 spec §7). Three
// tests: the hand-drawn lane needs no service; the digitized lane drives the
// real digitizer through the real field; the third proves a drag is still a
// drag. Service bootstrap and fixture copied from field-border-menu.spec.js,
// per this directory's convention of self-contained specs.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");

async function healthy() {
  try { const r = await fetch(SERVICE_URL + "/health"); if (!r.ok) return false; const h = await r.json(); return !!h && h.status === "ok"; }
  catch (e) { return false; }
}
function venvPythonCandidates() {
  const roots = [path.resolve(__dirname, "../..")];
  try {
    const stat = readFileSync(path.join(roots[0], ".git"), "utf8");
    const m = stat.match(/^gitdir:\s*(.+)$/m);
    if (m) { const mainRoot = path.resolve(m[1].trim(), "../../.."); if (mainRoot !== roots[0]) roots.push(mainRoot); }
  } catch (e) { /* .git is a directory */ }
  const out = [];
  for (const root of roots) {
    out.push(path.join(root, "digitizer", ".venv", "bin", "python"));
    out.push(path.join(root, "digitizer", ".venv", "Scripts", "python.exe"));
  }
  return out.filter(existsSync);
}
let serviceProc = null, serviceUp = false, skipReason = "";
test.beforeAll(async () => {
  if (await healthy()) { serviceUp = true; return; }
  const [python] = venvPythonCandidates();
  if (!python) { skipReason = "digitizer service not running and no venv python found"; return; }
  serviceProc = spawn(python, ["-m", "digitizer_service"], { cwd: path.resolve(__dirname, "../../digitizer"), stdio: "ignore" });
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) { if (await healthy()) { serviceUp = true; return; } await new Promise((r) => setTimeout(r, 500)); }
  skipReason = "digitizer service failed to answer /health within 30s";
});
test.afterAll(() => { if (serviceProc) serviceProc.kill("SIGTERM"); });

const STATS = "span.stats";

async function toContent(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
}

// Draw a rectangle on ManualPanel's canvas: four clicks at fractions of the
// canvas's displayed box, then Enter to finish (the panel's own key).
async function drawRectangle(page) {
  await page.locator(".hoop canvas").click({ button: "right" });
  await page.locator(".fieldmenu button").filter({ hasText: "Draw shapes" }).click();
  const mp = page.locator(".mp-canvas");
  await expect(mp).toBeVisible();
  const box = await mp.boundingBox();
  for (const [fx, fy] of [[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75]]) {
    await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
  }
  await mp.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(STATS)).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
}

async function hoopCentre(page) {
  const box = await page.locator(".hoop canvas").boundingBox();
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

test("hand-drawn lane: click inside the shape opens its popover; Satin restitches; Escape closes", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await drawRectangle(page);
  const before = await page.locator(STATS).innerText();

  // The design is centred in the hoop by default, so the hoop's centre is inside the rectangle.
  const c = await hoopCentre(page);
  await page.mouse.click(c.x, c.y);
  const dlg = page.getByRole("dialog", { name: "Shape 1 · Fill" });
  await expect(dlg).toBeVisible();
  // The side panel's row followed the field's selection.
  await expect(page.locator(".mp-shaperow.sel")).toHaveCount(1);

  await dlg.getByRole("combobox", { name: "Stitch type" }).selectOption("satin");
  await expect.poll(() => page.locator(STATS).innerText(), { timeout: 20_000 }).not.toBe(before);
  // The panel's own control agrees.
  await expect(page.locator(".mp-assign .mp-btn.active")).toHaveText("Satin");
  // ...and so does the dialog's name, re-derived from the shape.
  await expect(page.getByRole("dialog", { name: "Shape 1 · Satin" })).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Empty fabric: click well outside the rectangle — no dialog.
  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + 12, box.y + 12);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("a drag that starts inside a shape moves the element and opens nothing", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await drawRectangle(page);
  const c = await hoopCentre(page);
  await page.mouse.move(c.x, c.y);
  await page.mouse.down();
  await page.mouse.move(c.x + 40, c.y + 10, { steps: 8 });
  await page.mouse.up();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  // The offset moved: the SizePanel/App reports it via the project; cheapest
  // observable is that a click at the OLD centre still hits the (moved) shape
  // only if the move was small — so assert on the field's own drag cue
  // instead: the design's left edge shifted right. Read it off the canvas.
  const shifted = await page.evaluate(() => {
    const c2 = document.querySelector(".hoop canvas");
    const d = c2.getContext("2d").getImageData(0, 0, c2.width, c2.height).data;
    // first dark (stitch) pixel column
    for (let x = 0; x < c2.width; x++) for (let y = 0; y < c2.height; y++) {
      const i = (y * c2.width + x) * 4;
      if (d[i] < 80 && d[i + 1] < 80 && d[i + 2] < 80) return x;
    }
    return -1;
  });
  expect(shifted).toBeGreaterThan(0);
});

test("digitized lane: click inside a square opens the Layers row's controls; Border restitches at once", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await toContent(page);
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await page.waitForTimeout(1200);
  const before = await page.locator(".dgp-stats").innerText();

  // Inside the LEFT square: the fixture is two squares side by side, centred.
  const box = await page.locator(".hoop canvas").boundingBox();
  await page.mouse.click(box.x + box.width * 0.4, box.y + box.height * 0.5);
  const dlg = page.getByRole("dialog", { name: /^Thread #/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByRole("combobox", { name: "Stitch type" })).toBeVisible();
  await expect(dlg.getByRole("combobox", { name: "Border" })).toHaveValue("default");

  await dlg.getByRole("combobox", { name: "Border" }).selectOption("auto");
  await expect.poll(() => page.locator(".dgp-stats").innerText(), { timeout: 120_000 }).not.toBe(before);

  // The panel's own Border select reads the same value.
  const rows = page.getByRole("button", { name: /^Edit shapes/ });
  if ((await rows.getAttribute("aria-expanded")) !== "true") await rows.click();
  await expect.poll(() => page.locator('select[aria-label^="Border — "]').evaluateAll((els) => els.map((e) => e.value))).toContain("auto");
});
```

- [ ] **Step 2: Run the new spec, then the two neighbours it could have broken**

```powershell
cd app && npx playwright test e2e/field-shape-popover.spec.js e2e/field-border-menu.spec.js e2e/field-outlines.spec.js e2e/manual-trace-import.spec.js
```
Expected: all pass (the digitized test skips only if no venv python exists — on Kent's box `.venv/Scripts/python.exe` is there, so it must RUN). If the hand-drawn click at the hoop centre misses (e.g. the auto-fit size leaves the centre outside the ring), read the shape's outline pixel as `field-border-menu`'s `outlinePoint` does and click 14 px inside it instead. If `.mp-canvas` is not the drawing canvas's class, read it from `ManualPanel.svelte` (`class="mp-canvas"` at ~L1090).

- [ ] **Step 3: Commit**

```powershell
git add app/e2e/field-shape-popover.spec.js
git commit -m "e2e: the click-to-edit popover on both lanes, and a drag is still a drag

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Docs — status, area detail, product line, memory

**Files:**
- Modify: `MASTER_SCOPE.md` area 5 (after the "border decision is on the canvas" paragraph, ~L753; keep the file under 800 lines — check `(Get-Content MASTER_SCOPE.md).Count` before and after)
- Modify: `docs/scope/5-review-manual-editing.md` (append a dated section)
- Modify: `PRODUCT.md:58-63` (one sentence)
- Add: `.claude/memory/check-shipped-before-building-2026-09-29.md` and the `MEMORY.md` line (both already written, untracked)

- [ ] **Step 1: MASTER_SCOPE area 5 — one paragraph**

Insert after the paragraph ending "(confirmed 2026-09-09 — `borderMenu.spec.js` … 1024 px)":
```markdown
**Click a shape, edit it there — both lanes (2026-09-29, Kent's ask after seeing the manual lane again).** A click (under 4 px of travel) on or inside any shape on the field opens `ShapePopover` at the click: for an auto-digitized shape the Layers row's own controls (thread, stitch type, fill angle, underlay, border, Edit points, Delete) writing `shapeOverrides` exactly as the panel does, so the 0 ms border lane and 2 s pause are unchanged; for a hand-drawn shape Fill/Satin, colour, angle, Edit points (jumps to the side canvas in vertex mode) and Delete writing `element.shapes` as `ManualPanel` does; a preset shape gets its colour. Hand-drawn and preset shapes are outlined and hit-testable on the field for the first time — `buildQualityDesign` now emits `shapeOutlines` in field mm (input order, no fit; `designOutlinesInFieldMm`), and `shapesToRegions` passes the shape id so spans map back. Node editing of hand-drawn shapes on the field is the agreed follow-up. *(confirmed 2026-09-29 — `shapePopover.spec.js`, `ShapePopover.spec.js`, `e2e/field-shape-popover.spec.js` on both lanes; spec `docs/superpowers/specs/2026-09-29-shape-popover-design.md`)*
```

- [ ] **Step 2: Area doc section**

Append to `docs/scope/5-review-manual-editing.md`:
```markdown
## Click a shape on the canvas, edit it there (2026-09-29)

Kent asked for "a tool that allows me to manually digitize a logo or photo",
was shown the manual draw lane in the browser, and said what was actually
wrong: the controls are in a side panel, not on the shape. Spec:
`docs/superpowers/specs/2026-09-29-shape-popover-design.md`; plan:
`docs/superpowers/plans/2026-09-29-shape-popover.md`.

What was true before: only auto-digitized shapes existed on the field
(outlines, node drag, right-click border). Hand-drawn shapes had no field
presence because `shapesToRegions` never passed `shape.id` and the engine
emitted no outlines — every span for a manual design read `shape: ""`.

What ships: `design.shapeOutlines` from `buildQualityDesign` (field mm, +y
up, `T()` unrounded — the stitches' own space, so no second fit), one outline
source for three lanes in `EmbroideryField.outlinesMmFor`, a pure decision
table (`lib/shapePopover.js`) that reproduces `DigitizePanel.setOverride` /
`recolorShape` and `ManualPanel.updateShape` / `deleteShape` so an edit from
the popover is indistinguishable from one made in a panel, and the dialog
itself (`ui/ShapePopover.svelte`) anchored at the click and clamped inside the
hoop. A click is a press-and-release under 4 px; a drag still moves the
element. Selecting a hand-drawn shape on the field highlights its row in
`ManualPanel` (`shapeselect` → `fieldSelect`), and "Edit points" opens vertex
mode there.

Deliberately not done: node editing of hand-drawn shapes on the field
(follow-up spec), reorder/merge/split from the popover, removing either side
panel, a Delete for preset shapes (the element chip already does it).
```

- [ ] **Step 3: PRODUCT.md**

After the sentence ending "…the engine's rule, stated on the item." (L63) add:
```markdown
  Since 2026-09-29 a left-click on any shape — auto-digitized, hand-drawn or
  preset — opens a popover with that shape's controls where it is; the
  right-click menu is unchanged.
```

- [ ] **Step 4: Commit docs + memory**

```powershell
(Get-Content MASTER_SCOPE.md).Count   # must print <= 800
git add MASTER_SCOPE.md docs/scope/5-review-manual-editing.md PRODUCT.md .claude/memory/check-shipped-before-building-2026-09-29.md .claude/memory/MEMORY.md
git commit -m "Docs: the click-to-edit popover in area 5, PRODUCT, and the lesson in memory

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: Look, then PR

- [ ] **Step 1: The look-at-it step**

Start the Studio; at 1440×900 and again at 1024×768: open the popover on a hand-drawn shape, a preset, and (with the service up) a digitized square. Read computed styles for the dialog (`getComputedStyle(document.querySelector('.shapepop'))` — background, colour, border must resolve to real values, not empty) and check the dialog never extends past `.hoop`'s box (`getBoundingClientRect` of both). Screenshot each and attach to the PR body. Fix anything that fails before opening the PR.

- [ ] **Step 2: Full verification**

```powershell
node --test 2>&1 | Select-String -Pattern "^# (tests|pass|fail)"
cd app && npm test
cd app && npx playwright test
```
Expected: engine `fail 0` and pass = baseline + 4; Studio green (read the `RUN` banner); e2e green with the digitizer running (a skipped digitized test is NOT green here — start the service).

- [ ] **Step 3: Adversarial re-read of the diff**

`git diff main...HEAD` — check specifically: no change to any stitch-producing line in `digitize.js` beyond the three `continue` sites and the two return objects; `onWindowPointerDown` still closes the right-click menu; `shapeUnderPointer` still filters digitized only; no `.embproj` key added.

- [ ] **Step 4: Open the PR ready for review, arm auto-merge**

```powershell
git push -u origin claude/shape-popover
gh pr create --title "Click a shape on the canvas, edit it in a popover — both lanes" --body-file - <<'EOF'
Kent's ask 2026-09-29: click the shape on the design and edit it there instead of in the side panel.

- Engine: additive `design.shapeOutlines` (field mm, input order); `shapesToRegions` passes the shape id. Byte-identical stitches — engine suite pass count unchanged +4 new.
- Field: hand-drawn and preset shapes are outlined and hit-testable; a click (<4 px) on or inside any shape opens `ShapePopover`; drags still move the element.
- `lib/shapePopover.js` reproduces the two panels' patch semantics (tests compare against them); `ShapePopover.svelte` is the dialog.
- e2e on both lanes + a drag-is-still-a-drag test.
- Follow-up (spec §8): node editing of hand-drawn shapes on the field.

Spec: docs/superpowers/specs/2026-09-29-shape-popover-design.md. Screenshots at 1440×900 and 1024×768 attached.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```
Then arm auto-merge while `mergeable_state` is `blocked` (CLAUDE.md: ready-for-review first, arm by default, `digitizer` takes 33–55 min).
