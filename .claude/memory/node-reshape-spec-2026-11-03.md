---
name: node-reshape-spec-2026-11-03
description: Kent 2026-11-03 "entire spline follows" was pullRing's 2x-drag radius, not a bug; grilled spec (7 rulings) for one-node drags, Reshape mode on both lanes, holes_override, cross-shape marquee for seams
metadata:
  type: project
---

**Kent, 2026-11-03,** dragging one node on his digitized Instagram icon: "When
i move one, the entire spline seems to follow. I need the UI to be much easier
to use, so i can edit specific shapes, borders and boundaries very precisely."

**What it was:** `pullRing` (`app/src/lib/shapeOverlay.js`, 2026-08-13), built
for the owl's 1.3 mm-spaced photo outline: radius = max(3 mm, 2 x drag), cap
25% of perimeter. On his ~5 mm-spaced logo ring an 11 mm corner drag moved 9
of 36 nodes, 53 mm = 28% of the ring. Measured with the real `moveNode`.

**Spec with the rulings:**
`docs/superpowers/specs/2026-11-03-digitized-node-reshape-design.md`
(section 9). Short form:

1. Drag = one node; neighbours only within a fixed 3 mm of arc; Alt-drag =
   old soft pull; nearest node wins the grab (today the FIRST within 9 px).
2. Hybrid: quick drag stays; "Edit points" enters Reshape mode (bare-drag
   marquee, arrows nudge points 0.1/1 mm, Delete removes points, strip).
3. Holes: new additive key `holes_override`; `holes_mm` already ships from
   the service and the Studio never read it.
4. Marquee crosses shapes and hole rings: stage 5 clips/hides one side of a
   seam, so a seam only moves visibly when both edges move together.
5. Simplify per shape, 0.2/0.5/1 mm, rides "Apply to all similar shapes".
6. Both lanes (digitized + hand-drawn) in the Reshape PR.
7. Retire `DigitizePanel`'s SVG boundary editor in that PR.

Correction found on the way: a boundary edit never changes a shape's id
(`assign_shape_ids` runs on the auto-traced regions before overrides land), so
the 2026-08 "a pull must never become a move" reason is gone; the 25% cap
stays only as taste.

**Why:** the 2x radius was a session's own tuning on ONE dense photo outline
and was never a ruling; it was generalised to every ring. The seam finding is
the trap: a precise single-shape editor still looks broken on seams.
**How to apply:** build from the spec's section 8 order (PR 1 drag rule first,
Sonnet workers per [[agents-cheap-models-2026-11-02]]). Do not re-tune the
pull on the owl without re-reading section 3's cost line. A node-editing
complaint on a seam is ruling 4, not the drag rule. Ruling 8 (11-04) supersedes
ruling 1: bare drag exact, Alt soft; Done/Discard — [[ember-reshape-measured-2026-11-04]].
