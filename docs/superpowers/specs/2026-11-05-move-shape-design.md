# Move shape — design (Kent, 2026-11-05)

Kent: "I want to be able to select a stitch layer or 'body' and move the entire
feature, the outline along with the digitized profile."

## Scope

Digitized elements only; the hand-drawn lane is untouched. One shape (its shell,
its holes, its nodes) translates by (dx, dy) mm as a unit. Its stitches
regenerate at the new place through the existing restitch after the commit;
nothing slides the stitches live (stitches are not tagged per shape on the
wire). Studio only: no service or contract change.

## Entry

A "Move shape" row in the shape popover, directly after "Edit points", and the
same row in the right-click menu inside a shape. Entering Move ends Reshape or a
hole draft if one is on; entering those ends Move (committing a non-zero
pending move first).

State: `shapeMove = { elId, shapeId, eb, shell, holes, dx, dy, drag }`.
`shell` is the shape's ring as the field shows it (a pending `boundary_override`
if present, else `outlineFull`); `holes` likewise (`holes_override`, else
`holesFull`), field mm, indexed as `nodesForShape` indexes them. `eb` is
`editBasis`, frozen at entry so a restitch landing mid-move cannot change the
inverse fit.

Strip (canvas-drawn, an instrument, never a warning): "Moving shape · drag or
arrow keys · Enter to finish · Esc to cancel", with the Reshape strip's
Done / Discard buttons. Canvas attributes for tests: `data-shape-move`
(`on`/`off`), `data-shape-move-delta` ("dx,dy" mm to 0.01),
`data-shape-move-btns` (button centres, canvas CSS px).

## Gestures

- **Drag.** A left press anywhere on the canvas starts a drag of the shape (no
  marquee, no element drag, no node grab; Ctrl/Alt/Shift mean nothing). The
  pointer delta over the field scale adds to (dx, dy) live. `pastClickDeadZone`
  (4 px) with an `armed` latch: a click does not move.
- **Arrows.** 0.1 mm per press, Shift 1 mm, accumulated live, no commit per press.
- **Live paint.** Shell, holes and nodes drawn at basis + (dx, dy); stitches
  unchanged.

## Commit

Enter, Done, or a selection change (another element, no element, another shape
of the same element) commits; Esc and Discard restore and dispatch nothing. A
zero net (dx, dy) commits nothing. Otherwise ONE `elupdate` with
`discrete: true`, for this shape only:

- `boundary_override` = the basis shell translated;
- `holes_override` = the basis holes translated, ONLY when the shape has a
  hole (a hole-less shape leaves it absent, as today);
- `nodes` unchanged: the indices index the same vertices and `ringFingerprint`
  is similarity-invariant, so it still matches (unit-tested).

It goes through `ringEditOverrides` (`moveShapeOverrides` in `shapeNodes.js`),
so the service-space conversion, `boundaryIssues` and precision are the same as
every other ring edit. The "edit all similar shapes" tick is ignored. No
placement limit: a shape may land over neighbours or outside the artwork window;
the service accepts any valid polygon. After the commit the staleness rule
disables machine-file buttons until re-digitized, as for every ring edit.

## Pure helpers

`translateRing(ring, dx, dy)`; `moveShapeOverrides(el, basis, shapeId, shell,
holes, dx, dy)` returning `ringEditOverrides`' result, or null for a zero delta.
Tests: `app/src/lib/shapeNodes.spec.js` ("Move shape"), e2e m1–m7 in
`app/e2e/field-reshape-mode.spec.js`.

## Not in scope

Rotate/scale of a shape; moving several shapes at once (use Reshape's marquee);
snapping; a numeric dx/dy field.
