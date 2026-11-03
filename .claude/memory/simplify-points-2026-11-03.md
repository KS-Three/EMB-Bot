---
name: simplify-points-2026-11-03
description: Simplify points shipped 2026-11-03 (PR 3 of the node-reshape spec): popover row 0.2/0.5/1 mm, closed-ring Douglas-Peucker, rides the similar tick, never automatic; red-disc 64 -> 44 at 0.5 mm
metadata:
  type: project
---

**What shipped (PR 3 of [[node-reshape-spec-2026-11-03]], after [[reshape-mode-2026-11-03]]).**
`simplifyRing(points, tolMm)` in `shapeOverlay.js`: closed-ring Douglas-Peucker, the two
farthest vertices fixed, each half simplified, rejoined; every original vertex within
`tolMm` of the new ring, never under three points, input order and start kept. Pure and
ring-agnostic on purpose: PR 4 passes hole rings through the same function.

**Where it lives.** Popover row kind `simplify` (digitized, non-cap, needs a ring) with
buttons 0.2 / 0.5 / 1 mm (`SIMPLIFY_TOLS_MM`); `EmbroideryField.simplifyShapes` thins each
shape's CURRENT ring (`edit.mmById`: pending override, else `outlineFull`) in FIELD mm
(the fit is uniform, so mm are physical), converts per ring, runs `boundaryIssues`, and
dispatches ONE `elupdate`. The popover's `Points: N` reads `64 -> 44` via
`popoverModel({pointsWas})`, kept in `simplifiedFrom` until the popover closes or the
shape changes. The Reshape right-click menu has three rows `simplify-<tol>`.

**Why not automatic.** A geometry change nobody asked for changes the stitches under it,
and Kent judges edges by eye. Undo is the way back.

**Measured.** `red-disc.png` ring 64 points; Simplify 0.5 mm committed 44 (e2e (d)).

**How to apply.** A hole ring goes through `simplifyRing` unchanged; the group simplify
must send hole overrides in the same patch (spec section 5).
