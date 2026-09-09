# The border on the canvas: right-click a recognised shape, Add / Remove border

**Status: IN BUILD 2026-09-09, Kent's pick after item 6 (#437). A Studio
feature on the field's existing right-click menu; the engine is untouched.**

## 0. What already governs this — read before changing the plan

- **PRODUCT.md** — a launch-scope call. Direct manipulation of the recognised
  shapes is shipped scope (MASTER_SCOPE area 5, Kent's 2026-08-12 request);
  this extends it with one more per-shape decision made where the shape is.
- **The per-shape border override already exists end to end.** The engine
  reads `Region.meta["border"]` (contract v1; `_BORDER_VALUES` in
  `digitizer_service/app.py`: `off` / `auto` / `bean`), the Studio stores it
  as `element.shapeOverrides[sid].border` and shows it as the Border select
  in the Digitize panel's shape rows (`DigitizePanel.setShapeBorder`), and
  `canonicalShapeEdits` folds it into the edits key that restitches after a
  two-second pause (Kent's call 2026-08-13: shape edits restitch on their
  own). This feature adds a second way to set the same field. No new
  contract, no new persistence, no new restitch path.
- **The field's right-click menu is Kent's** (2026-08-13: the drawing tools
  live on a right-click, not an upload button). The border actions join that
  menu; the tools stay on it.
- **What the engine does with each value** (`config.py`, `border`): `auto`
  sews a satin border on a fill-classified shape wide enough to host a
  column and a bean run where it is not; `bean` the light tier wherever a
  centreline fits; `off` none. **A shape classified as satin never gets a
  border** (stage 7). So "Add border" on a lettering stroke changes the
  stored decision and nothing on the cloth — the panel's select has the
  same limit, and the item's tooltip says so.
- **COOKBOOK's convention: a Studio change is not verified until it has been
  looked at in a browser.** Screenshots at two widths, read here.

## 1. The gap

The border decision per shape is reachable only through the panel: open
"Edit shapes", find the row (by thread and area), change its Border select.
On the canvas — where the shape is — right-click offers the drawing tools and
nothing about the shape under the pointer. Kent asked (2026-09-09) for a
clickable satin border on the image: right-click, Add, Remove.

## 2. The design

`EmbroideryField.svelte`, `onContextMenu`:

- **Hit-test the shape under the pointer.** The element under the pointer
  is `pickElement(perElementRects)`, as a left-click reads it. For a
  digitized element with review rows, its outlines in canvas px come from
  the same `shapeOutlinesInFieldMm` fit the editor uses (generalised from
  `editableOutlinesPx`, which only ever built the SELECTED element's).
  `hitOverlay` finds a node or an edge; failing that, `hitShapeInterior`
  (new, pure) finds the smallest outline ring containing the point, so a
  right-click anywhere inside a shape reaches it — the border is the
  outline, but nobody aims at a one-pixel line to ask for one.
- **Select what the menu acts on.** The element (if it is not already
  selected) and the shape, so the amber highlight shows which shape the
  items will change — the same rule the left-click editor follows ("first
  click on a shape selects it and stops there").
- **The menu.** `fieldMenu` gains a `shape` section above the two tool
  items: the shape's name (the panel's own `rowName`: thread and area),
  then ONE toggling action — **Add border** when the shape has no border
  (override `off`, or no override under a design setting that gives it
  none) or **Remove border** when it has one (override `auto`/`bean`, or
  no override under a design setting that borders it) — and **Use design
  setting** when an override exists. `borderMenuItems` (new, pure) decides
  the list from the override entry and the design-wide `params.border`.
  Add writes `auto` (satin where a column fits, bean otherwise — the same
  value the panel's "Auto border" option writes); Remove writes `off`.
- **Commit** through `elupdate` with a `shapeOverrides` patch, exactly as
  `commitShapeEdit` does for a boundary — undo records one step, the
  panel's select shows the new value, and the restitch fires after the
  idle pause. No `patch` beyond that field.
- **Everything else as today:** Escape and any press outside close the menu;
  a right-click that hits no shape shows the tools alone; the simulator
  keeps the canvas while playing.

## 3. Tests

- `shapeOverlay.spec.js`: `hitShapeInterior` — inside one ring, in a hole
  (a smaller ring inside a larger one: the smaller wins), outside all,
  on the boundary.
- `borderMenu.spec.js`: `effectiveBorder` and `borderMenuItems` over the
  override × design matrix: no override under `off`/null/`auto`/`bean`/
  `significant`; override `off`/`auto`/`bean` under each.
- `app/e2e/field-border-menu.spec.js` against the real service on the
  two-squares fixture: right-click on an outline → the menu names the shape
  and offers Add border → the panel's Border select for that row reads
  `auto` and the stitch count moves after the restitch → right-click again →
  Remove border → `off`; Escape closes; a right-click on the empty field
  shows the drawing tools only.
- Screenshots of the open menu at 1440 × 900 and 1024 × 768, looked at.

## 4. What must not regress

- The drawing tools on the right-click (`wizard-smoke` / `touch-drawing-
  tools` e2e), the boundary editor's left-click flow (`digitize-boundary-
  edit`), the outlines toggle (`field-outlines`).
- `DigitizePanel`'s Border select stays the other way in; both read one
  field.

## 5. Decisions for Kent

- Whether "Add border" should offer the bean variant too (a second item), or
  stay one gesture with the panel's select as the place for the finer
  choice. Built as one gesture.
