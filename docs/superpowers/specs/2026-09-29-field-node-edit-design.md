# Node editing of hand-drawn shapes on the field — design

*2026-09-29. The follow-up the click-to-edit popover spec (§8) named. Kent's
calls: the hoop canvas becomes the ONLY node editor for hand-drawn shapes;
the side canvas keeps drawing, the shape list and row selection. Approved in
brainstorm; this is the spec the implementation plan is written from.*

## 0. Where this starts

PR #562 (`claude/shape-popover`) put hand-drawn (`manual`) and preset (`shape`)
shapes on the field: outlined, hit-testable, editable through a popover. Their
NODES are still edited only on `ManualPanel`'s 600×400 side canvas — the
surface Kent named as the confusing one. The field's node editor exists but is
digitized-only: `EmbroideryField.svelte`'s outline press gates on
`edit.el.type !== "digitized"` and only selects on the other lanes.

Three facts decide the shape of this design:

1. **A hand-drawn shape is authored geometry, not a ring.** `shape.points` are
   anchors in a fixed 600×400 canvas-px space (`manualShapes.js` `CANVAS_W/H`,
   `PX_PER_MM`); `shape.curves` is a sparse `{ [segmentIndex]: {x, y} }` map of
   quadratic-bezier CONTROL points, in the same px. `flattenShape` turns that
   into the ring the engine sews. The field today only sees the flattened ring
   (`design.shapeOutlines`), so **outline index ≠ anchor index** — the field
   must draw and edit the authored anchors and controls, not the ring.
2. **The engine's fit is the only correct map between canvas px and field
   mm.** `buildQualityDesign` fits the bbox of ALL of the element's shapes:
   `cx, cy` (bbox centre, px), `sc` (from `targetWidthMm`, else
   `garments.fitScale`), `mmPerPxFinal = sc / pxPerMm`, offsets rounded to
   DST units. `T(q) = ((q.x - cx)·mmPerPx + offX, (cy - q.y)·mmPerPx + offY)`.
   Nothing exports those numbers yet. The digitized lane's
   `fieldMmToOutlineMm` re-derives ITS transform from a bbox fit because the
   service's outlines pass through `buildImportedDesign`; the manual lane does
   not, so re-deriving here would be a second implementation of `T()` — the
   bug class `traceFitRect` exists to prevent.
3. **The fit moves when the geometry moves.** Because `cx, cy, sc` come from
   the bbox of every shape, dragging one anchor outward re-centres and (in
   auto-fit, or via `sc = sizeMm / bw`) rescales EVERYTHING on the next
   generate. An editor that lets the rest of the design jump when one node is
   moved is not usable. This spec rules that out (§4).

## 1. Constraints

- **Byte-identical stitches.** The engine change is one additive field on the
  return object. Engine suite pass count unchanged (+ new tests); the stored
  stitch hash test from #562 (`test/digitize.test.js`) must still pass.
- **One transform.** The engine exports its fit; the Studio never recomputes
  it. Forward and inverse are two pure one-liners in `lib/fieldNodeEdit.js`.
- **Same gestures as the side canvas had**, so nothing Kent learned there is
  lost: drag anchor, drag midpoint handle to bend/straighten (2 px snap to the
  chord straightens), click an edge to insert an anchor (cap
  `MAX_SHAPE_POINTS` 500), commit on release only when `shapeIssues` is empty
  (crossing / <3 points / too small reject and snap back with the message).
- **Single-vertex anchor moves.** Authored shapes have few anchors; the
  digitized lane's rubber-sheet `pullRing` exists because a traced outline has
  a vertex every 1.3 mm. Do not reuse it here.
- **No new persisted keys.** Edits write `element.shapes` (`points`,
  `curves`), `sizeMm`, `offsetXMm`, `offsetYMm` — all existing fields, through
  `elupdate` as `ManualPanel.updateShape` does.
- **Right-click stays the menu; left-click stays select/edit.** Delete-a-node
  is Delete with a focused anchor, plus a "Remove point" menu item.
- **Edit tool only; Svelte legacy syntax; commit trailer** as in every plan.

## 2. Engine: export the fit

`buildQualityDesign` returns, beside `shapeOutlines`:

```js
fit: { cxPx, cyPx, mmPerPx, offsetXMm, offsetYMm, pxPerMm }
```

- `cxPx, cyPx` = the `cx, cy` used by `T()`; `mmPerPx` = `mmPerPxFinal`;
  `offsetXMm/YMm` = `offXu / 10`, `offYu / 10` — the offsets AS APPLIED (rounded
  to a DST unit), not the request; `pxPerMm` = the source px-per-mm the caller
  passed, kept so a consumer can convert a mm size back to authored px.
- The empty-design return carries `fit: null`.
- `buildLetteringDesign` is untouched.
- Test: for the #562 100×50 fixture, `fit` reproduces every `shapeOutlines`
  point from the input rect through the forward map to 1e-9; the stitch hash
  is unchanged.

## 3. `lib/fieldNodeEdit.js` — pure geometry, no DOM

```js
pxToFieldMm(fit, {x, y})   -> [xMm, yMm]     // T() unrounded
fieldMmToPx(fit, [xMm, yMm]) -> {x, y}       // its inverse
authoredInFieldMm(shape, fit) -> { anchors: [[x,y]…], controls: {[seg]: [x,y]}, handles: [[x,y]…] }
    // anchors + controls mapped; handles = curveHandlePoint per segment (B(0.5) or chord midpoint), mapped
hitAuthored(authoredPx, px, py) -> null | { kind: "anchor"|"handle"|"edge", index, atPx }
    // anchors beat handles beat edges; radii NODE_GRAB_PX 9 / EDGE_GRAB_PX 6 (shapeOverlay's)
    // edge distance measured against the FLATTENED curve chain (manualShapes.nearestSegmentIndex on px geometry)
applyAnchorDrag(shape, index, newPx) -> shape'        // points[index] = newPx (canvas px)
applyHandleDrag(shape, seg, throughPx) -> shape'     // commitCurve: control or delete key (2 px chord snap)
insertAnchor(shape, seg, atPx) -> shape'             // manualShapes.insertVertexAtSegment; same object at the cap
removeAnchor(shape, index) -> shape' | null          // null when 3 would be breached; drops seg curves touching it, reindexes
editedElementPatch(element, fit, shapeId, shape') -> { shapes, sizeMm, offsetXMm, offsetYMm } | { error }
```

`editedElementPatch` is §4 in code. Every function above has a unit test;
`hitAuthored` is tested on a curved shape so an edge hit on the bowed part of a
segment lands (chord-only distance would miss it).

## 4. The re-fit rule

A node edit never moves what was not edited. `editedElementPatch`:

1. `shapes' = element.shapes` with the edited shape replaced; reject with
   `{ error }` if `shapeIssues(flattenShape(shape'))` is non-empty.
2. Compute the flattened bbox of ALL shapes before (`bw₀, cx₀, cy₀`) and after
   (`bw₁, cx₁, cy₁`), exactly as the engine does (flattened outer rings, px).
3. `s = fit.mmPerPx` is held constant: `sizeMm' = bw₁ · s`. (When
   `element.sizeMm` was null — auto-fit — this also seeds it, the field's
   existing resize convention.)
4. Offsets shift by the centre delta so `T` of an unedited point is unchanged:
   `offsetXMm' = fit.offsetXMm + (cx₁ − cx₀)·s`,
   `offsetYMm' = fit.offsetYMm + (cy₀ − cy₁)·s` (y is flipped in `T`).
5. Return the four-field patch; one `elupdate` → one undo step.

Invariant test, through the REAL engine (vitest can run `EMB` — `generate.spec.js`
already does): two shapes; drag an anchor of shape A outward; apply the patch;
`buildQualityDesign` before and after; **shape B's `shapeOutlines` points move by EXACTLY the engine's
offset-rounding residual (≤ 0.05 mm per axis, the DST grid) and `fit.mmPerPx` is
unchanged to 1e-12 — measured 2026-09-29: the residual is inherent
(`offXu = round(offset·10)`), and a looser bare tolerance would have hidden
scale drift**, and A's unedited anchors likewise. A second case starts from
`sizeMm: null`. Hoop clamp: if `sizeMm'` exceeds the hoop the engine clamps
`sc` and the invariant is knowingly broken — the existing hoop warning covers
it; the test pins that the patch itself is still produced (no error).

## 5. Field: gestures and drawing

Selected hand-drawn shape (`selectedShapeElId` + `selectedShapeId`, from #562):

- **Draw** the authored outline — anchors as dots (the amber/indigo the
  digitized editor uses), segments as `quadraticCurveTo` through mapped
  controls, a small midpoint handle per segment (side canvas's green dot
  vocabulary). The flattened cased outline stays underneath.
- **Basis frozen at press**: `fit` and the shape are captured when the drag
  starts, as `editBasis` does for digitized — a regenerate landing mid-drag
  cannot skew the inverse.
- **Anchor drag**: `hitAuthored` → `kind: "anchor"` on the already-selected
  shape → pointer capture → live `shape'` via `applyAnchorDrag` with
  `fieldMmToPx` → redraw each move → on release `editedElementPatch` →
  `elupdate`, or `shapeEditError` + snap back.
- **Handle drag**: same with `applyHandleDrag`.
- **Edge click**: press-and-release under `CLICK_PX` on `kind: "edge"` of the
  selected shape → `insertAnchor` → patch immediately (as the side canvas did),
  no popover. Hand-drawn segments have no edge-DRAG (the digitized lane's
  `moveEdge` is for dense rings); a drag that starts on an edge does nothing
  and, per #562, does not move the element. Documented in the area doc.
- **Focused anchor**: a click (not drag) on an anchor sets `focusedAnchor`
  (drawn ringed). **Delete** with a focused anchor → `removeAnchor` → patch
  (floor 3 → message); with none → deletes the shape as today. Escape clears
  the focus first. Right-click on an anchor grows the menu's shape section with
  **Remove point** (disabled with a title at the floor).
- **Preset shapes** are not node-editable (their geometry is a recipe) —
  unchanged.
- The **popover's Edit points** on a hand-drawn shape now just closes the
  popover (the shape is selected, so handles are live) — identical to
  digitized. `shapeselect`'s `edit` flag is removed.

## 6. Side canvas (`ManualPanel.svelte`)

Removed: `startShapeEdit`/`stopShapeEdit`, `editingId`/`editPoints`/
`editCurves`/`dragIndex`, the edit-target curve drag, `hitTestVertex`,
`tryInsertVertexAt` and `edgeHitOn` (edge-click insert), the "Edit points" /
"Done editing" buttons, the edit-mode cursors, `fieldSelect.edit`. Kept:
drafting (straight and curved nodes, draft curve handles, Backspace/Escape/
Enter), the shape list, row selection, `fieldSelect` row sync, Duplicate,
copy/paste, Dim, trace import, the backdrop. The hint paragraph loses its
"click its edge to add a new point" sentence and gains "edit its points on the
design canvas".

Tests that retire with the behaviour: `ManualPanel.spec.js` "editing a
finished shape's points by dragging a vertex", "bowing a finished shape's edge
while editing points", the edge-click-to-insert block, edit-mode cursor tests,
"Escape exits vertex edit". `manual-trace-import.spec.js`'s drag step moves to
the field (drag the traced shape's anchor on the hoop canvas).

## 7. Tests

- Engine: `fit` reproduces `shapeOutlines`; hash unchanged.
- `fieldNodeEdit.spec.js`: round trip px↔mm; `authoredInFieldMm` on a curved
  shape; `hitAuthored` precedence and the bowed-edge hit; each apply function;
  `editedElementPatch` invariance through the real engine (two cases) and its
  rejection path.
- `EmbroideryField` has no component spec (a known gap): the e2e carries the
  gestures — `app/e2e/field-node-edit.spec.js`: (a) drag an anchor of a
  hand-drawn rectangle; the stitch caption changes and the SIDE canvas's
  rendering of that shape changes (read `.mp-canvas` pixels); (b) drag a
  midpoint handle; the caption changes and a pixel on the bowed edge is now
  covered; (c) click an edge → the popover's name still reads Shape 1 and a new
  anchor dot exists at the click (pixel read); (d) focus an anchor, Delete →
  one fewer anchor, shape survives; at 3 anchors Delete shows the message; (e)
  **invariance**: two shapes, drag shape A's outer anchor 40 px outward, shape
  B's dark-pixel bbox is unchanged; (f) a drag that starts on an edge moves
  nothing and opens nothing.
- Existing #562 e2e stays green.

## 8. Out of scope

Drawing new shapes on the field; digitized delete-node; multi-anchor
selection; cubic handles; converting a shape's authoring space to mm.
