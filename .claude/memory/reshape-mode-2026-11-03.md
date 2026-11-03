---
name: reshape-mode-2026-11-03
description: Reshape mode shipped 2026-11-03 on both lanes ("Edit points"): cross-shape marquee so a seam moves as one gesture, arrows 0.1/1 mm, Delete per ring, one patch + one undo step; panel SVG editor retired
metadata:
  type: project
---

**What shipped (PR 2 of [[node-reshape-spec-2026-11-03]]).** "Edit points" in the
shape popover (it reads "Done" while on) turns on Reshape mode for the selected
ELEMENT, digitized and hand-drawn alike. State is `reshape = { elId, sel }` in
`EmbroideryField.svelte`, `sel` = `Map<shapeId, Map<ring, Set<index>>>` with ring
`"exterior"` (digitized) or `"anchors"` (hand-drawn); PR 4 adds hole indices as
more ring keys. Canvas strip `Editing points · Esc to finish` is drawn like the
rotate badge, never a warning (`no-warnings-reaches-readouts`).

**Why the marquee crosses shapes (the seam reason).** A seam is two shapes'
coincident edges traced from two masks. Stage 5 clips a later colour by the
colours already down and hides an earlier colour's growth under the later one, so
moving ONE side shows nothing or bare fabric. One gesture has to move both: the
marquee selects points of EVERY shape of the element, the drag moves them all, and
ONE `elupdate` carries a `boundary_override` per touched shape = one undo step.
A boundary edit never changes a shape's id, so select-all + drag needs no warning.

**Keys, in the mode.** Click a point = select; Shift-click = toggle; bare drag from
empty canvas or inside a shape = dashed marquee (Shift adds); drag a selected point
= all selected move by the same delta (digitized: `moveNodes` through `pullRing`,
3 mm neighbourhood around each seed, Alt = soft pull; hand-drawn:
`applyAnchorsDrag`, box clamp per anchor, box + cut-out containment hold the WHOLE
gesture); drag an unselected point = it becomes the selection. Arrows nudge the
selection 0.1 mm, Shift 1 mm, field mm, EXACTLY the chosen points (no falloff),
each press its own undo step (`elupdate.discrete` skips history's 500 ms
coalescing, else three quick presses undo as one). Delete/Backspace removes the
selection per ring (`removeNodes` / `removeAnchors`), a ring at three refuses with
"A shape needs at least 3 points." and loses nothing; with no selection Delete
does what it did. Right-click a point: "Delete point" / "Select all points" lead the
menu ("Simplify points" goes there in PR 3). Esc leaves the mode first (ahead of
focused anchor, popover, menu); another element selected also leaves. Outside the
mode a bare drag still moves the element and arrows nudge the element.

**Retired:** `DigitizePanel`'s SVG boundary editor and its Layers-row pencil.
`digitize-boundary-edit.spec.js` now drags a vertex on the hoop canvas. That also
removed the panel's "Reset to auto" for a boundary edit (undo is the way back
until something replaces it).

**How to apply:** a refusal (`boundaryIssues`, `shapeProblems`, cut-out hold) drops
the WHOLE gesture and names the shape in `shapeEditError`; the contract fixture for
a single exterior edit stays byte-identical (`commitShapeEdit` untouched). Holes
(`holes_override`) are PR 4, Simplify PR 3.
