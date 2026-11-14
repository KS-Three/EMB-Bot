---
name: pen-stroke-2026-11-13
description: Pen (PR 1 of pen + auto-branch): a drag in Column or Line mode draws the stroke; tangent curve fit, snap with hook trim, next column takes the last edited width; Kent's 3 rulings; auto-branch is PR 2, built OFF
metadata:
  type: project
---

**What shipped (2026-11-13).** In the manual lane's side canvas (`ManualPanel.svelte`), a press in Column or Line mode that moves past 4 px is a stroke; release finishes the shape. Clicks still place points. `app/src/lib/penStroke.js` turns the samples into the same `points` + `curves` record a clicked open shape has (resample 2 px, Gaussian sigma 4 px, tips over 75 degrees kept sharp, tangent-intersection quadratic fit at 1.0 px). Studio only, no stitch change for existing designs. Spec: `docs/superpowers/specs/2026-11-13-pen-auto-branch-design.md`.

**Why:** Kent 2026-11-13, after a Design Doodler outline tutorial (youtube WvaXuvqbifg): "It's WAY easier than how our tool does it." His rulings that day: (1) "Pen + auto-branch" before any automatic outline lane; (2) auto-branch is a "Checkbox, built OFF"; (3) "Remember last width": a new Column takes the width of the Column last edited, the first is still 4.0 mm (ruling 9 of the 2026-09-30 spec stands).

**How to apply:**
- The tracer's fit (`fitCurvesForRing`) is wrong for pen strokes: it puts the span's worst point at the curve's middle, which hooks short spans (worst tangent break 138 degrees on a jittered arc, against 18). Do not swap it back in.
- A quadratic whose control sits near one end is a straight line ending in a hairpin, and it passes a distance tolerance. `tangentControl` refuses a control under 0.4 balanced; e2e (p2) caught a shallow V refused as "folds over itself" before that. A fit-error bar alone does not see it: test the stroke as a 4 mm Column.
- A snapped end needs `withSnappedEnds`, not just a moved end point: the pointer goes down a few px off the snap point and the path doubles back through it, and a 4 mm Column folds on that hook. Found in the browser, not by the first tests (they snapped a Line, which has no fold check).
- Width memory lives in the MODULE (`nextColumnWidthMm`), because ContentStep remounts the panel per visit; specs must call `resetPenMemory()` in `beforeEach`. Colour must NOT: it was a module map keyed by element id first, and element ids are recycled (`nextElementId` is max+1), so a new project's "e1" inherited the last project's colour. `nextOpenShapeColor(shapes, selected, fallback)` reads the drawing instead. Review caught it, no test did.
- Dead zone (4) and minimum stroke (12) are SCREEN px, converted by the panel's `penPx`: the side canvas is drawn at about 0.66 of its 600 px, and in canvas px a finger tap that drifts became a stroke.
- A refused stroke stays as the draft (`draftFromPen`) and the next drag replaces it; a clicked draft is never preempted. `snapSpines` is computed per shapes change, never per pointer move (`shapeProblems` on a column is a self-crossing test).
- A 90 degree corner is NOT kept sharp: jittered, it reads as little as 54 degrees over the 8 px window and a 2 mm-radius loop reads up to 68, so no threshold separates them. It rounds by about the sigma (0.7 mm at the nominal scale).
- Driving the pen from a page script: a draft left by an earlier synthetic click stops the pen arming (pen needs an empty draft), and localStorage restores earlier test elements after a reload, so count the element rows before reading "colors".
- Observed, not traced: one drawing with two same-colour Columns reads "2 colors" in the footer. `shapesToRegions` emits a region per shape and the Studio never passes `minimizeColorChanges`. Spec section 7 makes this PR 2's first check.

**Next (PR 2):** `joinStrokes` tick, same-colour touching Columns routed by lettering's `routeGlyph` (`src/satinfont.js`), X crossings diced behind an option so fonts stay byte-identical, and the exposed-travel instrument (bar 0.00 mm) before Kent is asked about the default.
