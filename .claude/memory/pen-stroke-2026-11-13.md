---
name: pen-stroke-2026-11-13
description: Pen + auto-branch: a drag in Column or Line mode draws the stroke (tangent fit, snap with hook trim, last edited width); "Join touching strokes" tick built OFF sews touching same-colour Columns as one path; Kent's 3 rulings
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
- Traced 2026-11-14: every hand-drawn shape is its own colour block (a trim and a colour change), same thread or not. `shapesToRegions` emits a region per shape and the manual branch never passes `minimizeColorChanges`; already a `todo` in `test/colour-order.test.js`. Not changed: it moves every existing drawing with two same-colour shapes, so it is Kent's call.

**PR 2, auto-branch (2026-11-14), built OFF.** `joinStrokes` on the manual element, tick "Join touching strokes" in ManualPanel. Ticked, same-colour Columns that touch are one region (members keep their own id, ring, rails; `sewAs.join: true`) and `buildQualityDesign` sews them as one path through `satinfont.routeColumnGroup`.
- The glyph router's touch rule is wrong for a drawing: its radius is 1.3 x the median column width (a 4 mm stroke joins anything within 5.2 mm, over bare cloth) and it cuts only between 6% and 94% of a column. Hand-drawn columns use `joinGraph`: an end touches when inside the other column's body (half ITS width), spines that cross touch, no constant. The walk after the graph is `routeGlyph`'s, fonts byte-identical.
- One rule asked twice: the Studio groups with `EMB.joinComponents`, handed into `shapesToRegions` (which stays engine-free); do not restate the touch test in the Studio.
- No proxy ring (the first spec draft had one): it leaves the other members out of the design bbox and unclickable.
- `tuckSatinEnds`: a satin span ends on a rail and the step to the next span lay across finished satin half the time (2.1 mm on a 4 mm L, by walk direction). Sew the last cross back and leave from the other rail when that step is covered.
- Instrument `tools/join-strokes.mjs` (`--svg` for the sheet): 12 groups, jumps + trims inside 0, travel no later satin covers 0.00 mm, on bare cloth 0.00 mm. Tuck off (`joinTuck: false`): up to 2.10 mm on finished satin, never bare cloth.
- A satin run's stitches are NOT rail A on even indices and rail B on odd: `emitZigzag` leads with the other rail on every second cross (A0 B0 B1 A1 A2 B2). A body polygon built on parity crosses itself (holds half the column) and still read a plausible 0.00 to 0.29 mm; stitch triangles (three in a row) leave gaps that pinch to the spine and read 11 mm bare. Use the quad of each four stitches in a row, and give any such measure known-answer cases (the test has three). The reviewer agent caught the first; the tuck shared it.
- A group sews where its LAST member was drawn. On fleece and terry (satin underlay `zigzag`) a group takes the centre walk, not what a lone column gets.
- Lane trap: `node_modules` as a junction to the main checkout's (disk at 10 GB) needs `server.fs.strict: false` for component specs and the dev server, and local Playwright reuses whatever is on :5183, which may be another lane's server.

**Next:** Kent sees the sheet (joined beside as drawn) before any question about the default. Lines in a group, entry/exit dragging: out of scope (spec section 6).
