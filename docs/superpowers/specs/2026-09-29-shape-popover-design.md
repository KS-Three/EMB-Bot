# Click a shape on the canvas, edit it there — design

*2026-09-29. Kent's ask, verbatim: "can you set it up so i can just click the
layer on the screen, and a dialogue box pops up (similar to how it's setup now
in the side panel), that allows me to edit the layer/shapes feature?" Approved
in brainstorm; this is the spec the implementation plan is written from.*

## 0. How this came up

Kent asked for "a tool that allows me to manually digitize a logo or photo"
and, shown the shipped manual draw lane in the browser (Becker logo traced
into 68 starter shapes, five "interior hole not supported" warnings), said he
had forgotten it existed. His next sentence was the real defect: the editing
surface is confusing because it is in the side panel, not on the design.

Two lanes carry shapes on the hoop canvas today and only one of them can be
edited from there:

| lane | element type | outlines on the field | click-to-select | where the controls are |
|---|---|---|---|---|
| auto-digitized | `digitized` | yes (`shapeOverlay.js`) | yes — nodes, Delete, right-click border | Digitize panel Layers rows, a screen away |
| hand-drawn / preset | `manual`, `shape` | **none** | **none** | `ManualPanel`'s 600×400 side canvas + assign box |

Kent's scope call: **both lanes, one gesture, one popover.** Second call:
**attributes on the field now; node editing of hand-drawn shapes on the field
is a follow-up spec** — "Edit points" on a hand-drawn shape jumps to the side
canvas in edit mode for this build.

## 1. The two gaps, located

1. **Hand-drawn shapes are invisible to the field.** `shapesToRegions`
   ([`app/src/lib/manualShapes.js:583`](../../../app/src/lib/manualShapes.js))
   builds one region per shape and never passes `shape.id` through, so the
   engine's spans carry `shape: ""` for every manual and preset shape
   (`pushSpan(spanI0, kind, shape.id)`, `src/digitize.js:728`). Nothing
   downstream can say which stitches belong to which drawn shape, and nothing
   emits the shape's outline in design space.
2. **Auto-digitized controls are not where the shape is.** Selection,
   outlines and node drag are on the field; tier / angle / underlay / colour /
   border are `<select>`s in `DigitizePanel.svelte`'s Layers rows
   (`setOverride`, line 1084). The 2026-09-09 right-click border menu is the
   only per-shape decision reachable on the canvas.

## 2. Constraints that are forced

- **Byte-identical stitches.** Everything here is additive: a new field on
  the engine's return object, a new component, a new selection model. No
  stitch, trim or colour block moves. The engine `node --test` suite and the
  Studio suite must be green with no golden touched.
- **The engine's outlines come out in the space its own stitches are in —
  no fit, no second transform.** The digitized lane needs
  `shapeOverlay.shapeOutlinesInFieldMm()`'s bbox→bbox fit because the
  service's `outline_mm` goes through `buildImportedDesign` (rotate, re-centre,
  scale, clamp) before it reaches the field. A manual or preset element does
  not: `generate.js` hands `targetWidthMm` and the offsets straight to
  `buildQualityDesign`, whose `T()` already produces field mm. So the engine
  emits each outline through the same `T()` (unrounded), in **field mm, +y
  up** — exactly what `bboxMmFromStitches` reads and `renderResult.toCanvas`
  consumes — and the field draws it with one `toCanvas` call per point. A
  fit here would be a second implementation of `T()` and the class of bug
  `traceFitRect` exists to prevent (MASTER_SCOPE area 5).
- **Existing restitch rules stay.** Auto-digitized edits from the popover
  write `shapeOverrides[sid]` through the identical `elupdate` patch the
  border menu sends, so `editKind`'s 0 ms border lane and 2 s everything-else
  lane apply unchanged (area doc, 2026-09-17). Do not add a third lane.
- **Right-click is taken, twice.** On the field it opens the tool/border
  menu; inside `ManualPanel` it places a curved node. The popover is
  **left-click**. The right-click menu is untouched.
- **A drag is not a click.** The field moves elements on pointer drag
  (`lib/interact.js`). Selection fires only when the pointer travelled less
  than the existing drag threshold between down and up.
- **Draw order is sew order for hand-drawn shapes** (`darkOnTop: false`,
  Kent 2026-08-26). The popover offers no reorder control; that needs list
  context and is out of scope here.

## 3. Engine: per-shape outlines in design mm

`EMB.buildQualityDesign` gains one return field:

```js
shapeOutlines: [
  { id: "<shape id or ''>", points: [[xMm, yMm], ...], holes: [[[xMm, yMm], ...], ...] },
  ...
]
```

- Coordinates: **field mm, +y up, offsets applied** — the stitches' own
  space, `T(q)` without the integer rounding, divided by
  `units.DST_UNITS_PER_MM`. An outline therefore lands on its own stitching
  to within 0.05 mm, and the field maps it with `renderResult.toCanvas`
  alone (see §2). Elements on this lane carry no rotation (`rotatable()`
  excludes them), so none is applied.
- One entry per input shape, in input order, including shapes the engine
  later dropped as too small or degenerate — an entry the field cannot hit
  is harmless; a missing entry is a shape that cannot be selected. Dropped
  shapes carry `dropped: true`.
- `id` is whatever the region shape carried. `shapesToRegions` now passes
  `id: shape.id`; the span `shape` field therefore carries the real id too,
  which also makes `borderMenu.indexRuns` able to answer for manual designs
  (a free side effect, not a goal).
- `buildLetteringDesign` is NOT changed. Text is not a shape lane.

Test (`test/digitize.test.js` or a sibling): a 100×50 px rectangle at
`pxPerMm` 6 with `targetWidthMm` 40 → outline bbox 40 × 20 mm centred on
`(offsetXMm, offsetYMm)`; id preserved; `stitches` byte-identical to the
same call before the change (assert on a stored hash of the fixture's
stitch array, computed on `main` before the edit).

## 4. Field: one selection model for both lanes

`EmbroideryField.svelte` replaces `selectedShapeId` (digitized-only) with

```js
selectedShape = null | { elementId, shapeId, lane: "digitized" | "manual" | "shape" }
```

- **Hit order on a click:** for the element under the pointer, `hitOverlay`
  (on an outline) first, else `hitShapeInterior` (smallest containing ring —
  a click inside a counter picks the counter, not its surround), as the
  border menu already does. Hidden (`stitched: false`) and deleted shapes are
  not hittable. No hit → deselect and close the popover.
- **Outlines for `manual` / `shape` elements** come from
  `peById[el.id].design.shapeOutlines` (already field mm, §3) and go
  straight through `renderResult.toCanvas`. Drawn with the same cased-line
  style; the selected one highlighted; respects the "Show shape outlines"
  toggle exactly as digitized outlines do.
- **Node drag stays digitized-only** in this build. A `manual` selection
  draws the outline and highlight; there are no grab handles on it.
- **Selection sync:** selecting a hand-drawn shape on the field dispatches
  `shapeselect { elementId, shapeId }` up through `App.svelte`, which passes
  it into `ManualPanel` so its shape list highlights the same row. Selecting
  in the side panel does not need to drive the field (Kent's 2026-08-13
  ruling: canvas hit only drives canvas selection).
- Delete key behaviour extends to the new lane: `manual` → remove the shape
  from `element.shapes`; `digitized` → `deletedShapeIds` as today.

## 5. The popover

Two files, mirroring `borderMenu.js` + the `.fieldmenu` markup:

**`app/src/lib/shapePopover.js`** — pure, no DOM. Given
`{ lane, element, shapeId, review?, design? }` returns the control model:
which rows to show, each row's current value and options, the display name
(thread + area for digitized; `summary(shape)` for manual), and
`patchFor(lane, shapeId, fieldName, value)` → the `elupdate` patch. Unit
tests: the full lane × control table, including "underlay row hidden unless
tier is fill", "Auto tier option only for preset shapes", and every
`patchFor` output compared against what `DigitizePanel.setOverride` /
`ManualPanel.updateShape` would have sent for the same edit.

**`app/src/ui/ShapePopover.svelte`** — rendered by `EmbroideryField` when
`selectedShape` is set. Anchored at the click point, clamped inside the
field's box, `role="dialog"` with `aria-label` = the shape name, focus moves
into it on open, Escape and any pointerdown outside close it (reuse
`onWindowPointerDown`'s `.closest()` guard). Rows:

| row | digitized | manual | preset shape |
|---|---|---|---|
| name (thread · area) | ✓ | ✓ (`Shape N · Fill/Satin`) | ✓ (kind) |
| Colour — `ThreadPicker compact` | ✓ → `thread_index` + `rgb` (nearest cone in the job's chart, as `DigitizePanel.recolorShape`) | ✓ → `colorRgb` | ✓ → `colorRgb` |
| Stitch type | the Layers row's own ten-entry list (Auto / Satin / Fill / Run / Sketch / Streamline / Cross-hatch / Wave / Chevron / Brick) → `tier` | Fill / Satin → `stitchType` | — |
| Fill angle | the Layers row's `SHAPE_ANGLES` list → `fill_angle_deg` (shown when the effective tier is fill) | number, blank = auto → `angleDeg` | — |
| Underlay style (shown when fill) | ✓ → `underlay_style` | — | — |
| Border | Design setting / No border / Auto border / Bean border → `border` | — | — |
| Edit points | closes the popover with the shape selected — the field's node mode is already armed by selection | selects the shape in `ManualPanel` and enters its edit mode (scrolls the side canvas into view if clipped) | — |
| Delete | → `deletedShapeIds` | → removes from `shapes` | — (a preset element IS one shape; the element chip's own remove control already does this) |

A preset element persists only `kind`, `params`, `colorRgb` — `generate.js`
hardcodes `stitchType: "auto"` and `angleDeg: null` for it — so its popover is
name and colour, nothing more. Everything a row writes is a field that already
exists and is already tested end to end; the popover adds no new keys to
`shapeOverrides`, to the manual shape record, or to the `.embproj` schema.

**Side panels stay.** The Digitize panel's Layers rows and `ManualPanel`'s
assign box are not removed in this build — drawing still happens on the side
canvas, and the Layers list is the only place with reorder and merge/split.
Retiring the assign box is a separate call once the popover has been used.

## 6. Error handling

- Stale review (edit no longer matches a shape id): the existing stale-edit
  notice and "Clear them" flow apply; the popover simply closes on the next
  result if its shape is gone.
- A `manual` element whose design failed to generate has no
  `shapeOutlines`: nothing to hit, nothing drawn — same as today.
- Popover open during a restitch: controls stay enabled; the panel's
  "restitching when you stop editing" line is the feedback, as today.
- Viewport too small to fit the popover at the anchor: clamp, never
  overflow the field; on a very short viewport it may cover the shape — the
  outline highlight remains visible around it.

## 7. Testing

- **Engine** (`node --test`): outline geometry and id preservation (§3);
  byte-identical stitches on the fixture.
- **Studio unit** (`cd app && npm test`): `shapePopover.spec.js` (control
  table, `patchFor` parity); `shapeOverlay.spec.js` gains manual-lane
  mapping cases; `manualShapes.spec.js` pins `id` on the region shape.
- **e2e** (`app/e2e/field-shape-popover.spec.js`, sibling of
  `field-border-menu.spec.js`): (a) draw a rectangle via the tool menu,
  click inside it on the field → popover with "Fill" active → click "Satin"
  → the stats line moves; (b) on the two-squares fixture against the live
  service, click inside a square → popover → set Border Auto → stats move at
  the 0 ms lane; Escape closes; a click on empty fabric closes and deselects;
  (c) a drag that starts inside a shape moves the element and opens no
  popover.
- **Browser check before the PR**: drive it at 1440×900 and 1024×768 and
  look at the open popover on both lanes — this is a display change, and
  MASTER_SCOPE area 5's rule stands: read computed styles, do not trust the
  spec count.

## 8. Out of scope, named

- Node / curve-handle editing of hand-drawn shapes on the field — the agreed
  follow-up spec.
- Reorder, merge, split, convert-to-text from the popover.
- Holes, open run paths, satin column tools — the deeper manual-digitizing
  gaps surfaced in the same session (Explore report 2026-09-29); separate
  brainstorm.
- Removing either side panel.
