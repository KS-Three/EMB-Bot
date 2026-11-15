# Pen and auto-branch in the manual lane — design (Kent, 2026-11-13)

Kent, after watching a manual outline-digitizing tutorial
(<https://www.youtube.com/watch?v=WvaXuvqbifg>, Design Doodler): "It's WAY
easier than how our tool does it." Asked which takeaway to spec first:
"Pen + auto-branch".

## 0. What the video does that we do not

The author traces a simple two-colour drawing by dragging a stylus along each
line with a 1 mm satin tool. Strokes that meet are sewn as one continuous path:
a running stitch travels to the far end and the satin sews back over it, so the
machine never jumps or trims inside a colour. The app offers to do that routing
itself ("auto branch") and the author recommends beginners use it.

Ours, measured against the code on `main` bb5655bf:

| Step in the video | Ours today |
|---|---|
| Drag to draw a stroke, hand jitter smoothed | Click one point at a time, double-click to finish (`ManualPanel.svelte` `onCanvasClick`, `onCanvasDblClick`). Drawn input is stored raw |
| Thin satin stroke at a set width | Column mode exists (spine + width, `manualShapes.js`). A new Column is 4.0 mm (`COLUMN_DEFAULT_MM`, ruling 9 of the 2026-09-30 spec) |
| Strokes that touch sew as one path | Every shape is its own region and its own sew unit (`shapesToRegions`). Travel over `trimAtMm` between two shapes is a trim |
| Auto branch | The router exists for lettering only: `routeGlyph` (`src/satinfont.js`), a Chinese-postman walk over one glyph's satin columns with the running underpath laid first and the satin over it |

Already there and not part of this spec: the fadeable tracing image, Line mode
with a stitch length, centre-run underlay under a Column, the stitch player.

## 1. Scope

Two PRs, in this order. Browser engine and the manual lane only; no service,
contract or Python change.

1. **Pen.** Dragging in Column or Line mode draws the stroke. Studio only, no
   engine change, no stitch change for any existing design.
2. **Auto-branch.** A per-drawing tick, "Join touching strokes", built OFF.
   Ticked, same-colour Columns that touch sew as one continuous path.

## 2. Pen (PR 1)

**Gesture.** In Column and Line mode, a press that moves past the 4 px click
dead zone becomes a stroke; the release finishes the shape. No double-click.
A press that stays inside the dead zone is a click and places a point exactly
as today, so click-drawing, right-click curved nodes and Backspace are
unchanged. Shape and Hole modes are unchanged (a dragged closed outline is out
of scope, §6). Pointer events, so a stylus or a finger draws the same way; the
canvas takes `touch-action: none` while one of the two open modes is on so a
drag draws instead of scrolling the page.

**Stabilising.** The raw samples are smoothed and curve-fitted into the
record a click-drawn open shape already has: `points` plus `curves`. Nothing
new is stored, so node and handle editing, Simplify points, run ↔ column
conversion and `.embproj` all work on a pen stroke as they do on a clicked one.
The fit loosens until the stroke is under `MAX_SHAPE_POINTS` (500).

*Amended in the build, 2026-11-13.* This section first said the fit would
reuse the tracer's pair (`simplifyRingAdaptive` + `fitCurvesForRing`) and not
add a second algorithm. Measured, that pair is wrong for a pen stroke:
`fitCurvesForRing` puts a span's worst point at the curve's parametric middle,
and on the short spans a stroke simplifies to, that hooks the curve back on
itself. Worst tangent break at an anchor on a 60 px arc with 1.2 px of jitter:
138 degrees, and a Column's rails spike at every one. So `penStroke.js` has its
own fit: re-space to 2 px, Gaussian-smooth (sigma 4 px, ends pinned), then
quadratics whose control point is where the path's tangents at the span's ends
cross, split until within 1.0 px. A control that sits lopsidedly near one end
is refused and its span split: such a curve is a straight line ending in a
hairpin, and e2e (p2) caught a shallow V refused as "folds over itself"
because of one. Same arc: 18 degrees, 13 nodes, 0.91 px from the true curve;
with 0.5 px of jitter, 0 degrees and 7 nodes. Every bar is in
`penStroke.spec.js`, "fit error".

A tip (a turn of 75 degrees or more over 8 px each side: a leaf point, a V)
is kept sharp. A soft corner is not: jittered, a plain 90 degree corner reads
as little as 54 degrees and a 2 mm-radius loop up to 68, so no threshold
separates them, and a 90 degree corner rounds by about the sigma (0.7 mm at
the nominal scale).

These are lengths in authored canvas px: properties of a hand on a screen, not
of thread on fabric, so ROADMAP gate 1 does not apply. No machine would settle
them.

**Snap.** While drawing, a stroke's start and its end snap onto the nearest
endpoint, or else the nearest point of the spine, of an open shape of the same
kind within 10 px (the canvas's existing closing radius); a red dot marks the
target. This is what makes "touching" exact for §3 instead of a near miss the
author cannot see. Holding Alt draws without snapping. Every sample inside the
radius of a snapped end is dropped (`withSnappedEnds`): the pointer goes down a
few px off the snap point, and moving only the end point left a hook there that
a 4 mm Column folded over (found in the browser during the build).

**Short strokes.** A drag under 12 screen px is a click that slipped and
places a point. The dead zone (4) and this floor are SCREEN px, converted to
canvas px by the panel, because the side canvas is drawn narrower than its 600
authored px and a finger's slip does not shrink with it. A draft already open
by clicks is never preempted by a drag. A stroke belongs to the pointer that
started it: a second touch neither restarts nor ends it. Points are held to the
canvas, so a drag that runs off its edge stops at the edge.

**Width (Kent, 2026-11-13: "Remember last width").** The first Column of a
session is 4.0 mm, ruling 9 unchanged. Each later one takes the width of the
Column last EDITED, in this panel's Width row or the hoop's popover. No new
number, no new control. (As built: a width is remembered when it is edited. A
Column drawn at the remembered width keeps it; opening a saved drawing does
not adopt its widths.) Applies to a click-drawn Column too.

**Colour.** A new open shape takes the colour of the selected shape (a shape is
selected the moment it is finished), else of the shape drawn last in this
drawing, else today's default. It is read off the drawing, nothing is stored:
the first build kept it in a map keyed by element id, and element ids are
recycled, so a new project's first drawing inherited the last project's colour
(caught in review). The width IS session memory and carries into the next
drawing and project. (Colour is mine, not a ruling: without it every stroke of
a second colour is drawn black and recoloured one at a time.)

**Validity.** `columnIssues` / `runIssues` gate a pen stroke as they gate a
clicked one. A stroke that fails (a Column that folds over itself at its
width) is not added: it stays on the canvas as the draft with the existing
reason string, to be fixed or cleared like any draft, and the next drag simply
replaces it.

## 3. Auto-branch (PR 2)

**Switch (Kent, 2026-11-13: "Checkbox, built OFF").** `joinStrokes` on the
manual element, absent or false by default, saved in `.embproj`. A tick in the
manual panel, "Join touching strokes". With it off, nothing in this section is
read and every design sews byte-for-byte what it sews today, pinned by a test.
The default flips only on Kent's say, after renders.

**What joins.** Columns only, of exactly the same colour, within one drawing.
Lines and closed shapes sew as today (§6). The Columns' spines form a graph: a
junction is where one spine's end lands on another spine, or where two spines
cross. Each connected component of two or more Columns is a group. A Column
that touches nothing is not in a group and sews as today, tick or no tick.

**Router.** The group is handed to lettering's `routeGlyph`: it already takes
`{ railA, railB, rungs }` columns, which is what a hand-drawn Column carries.
Per group it returns one needle-down path in which a span's last visit sews as
satin and every earlier visit as a running underpath, so travel is always laid
first and covered. It dices columns only where an END lands on another column;
a mid-stroke X crossing is new and is added behind an option only this caller
passes, so every font's stitch stream stays byte-identical (pinned).

**Hand-off.** `shapesToRegions` emits one region shape per group with
`sewAs: { kind: "columnGroup", columns: [{ id, railA, railB }] }`. Its `outer`
is a proxy, the first member's rail ring, read only for the bbox and the sew
order, the same posture a Line's hairline ring has (ruling 1 of the 2026-09-30
spec). The router reports which column each span came from, so every satin
span is tagged with its own member's id and a click on the field still opens
that Column's popover. Underpath spans map to the existing `travel` kind.

**What a group inherits.** Satin spacing, pull compensation and slant as a
single Column gets them today. Underlay: the fabric's satin underlay; a group
whose members carry different per-shape underlay overrides is not joined and
sews as today. No ties (ruling 7 stands). Between groups, and between a group
and any other shape, the existing `trimAtMm` rule is unchanged.

**Start point.** The router's own. Dragging a group's entry or exit is out of
scope until a real drawing shows it is needed (§6).

*Amended in the build, 2026-11-14 (PR 2).* Five things above are not what was
built, each for a reason found while building:

- **What touches.** `routeGlyph` dices a glyph by a radius read off the glyph
  (1.3 x its median column width) and by fractions of a column's length. For a
  drawing that joins a 4 mm stroke to anything within 5.2 mm of it, across
  bare cloth, and misses a stem landing in the last 6% of a long bar. Hand-drawn
  columns get a graph of their own (`joinGraph`, `src/satinfont.js`) with one
  rule and no constant: an end touches a column when it lies inside that
  column's body (within half ITS width of its spine); two columns touch where
  their spines cross; a column whose own ends lie that close is a closed loop.
  The walk after the graph (postman, Euler trail, last visit sews satin) is
  `routeGlyph`'s, unchanged, and every font's stream is byte-identical
  (`satinfont.test.js`'s md5 pins).
- **One rule, asked twice.** The Studio does not restate it: `shapesToRegions`
  is handed the engine's `joinComponents` and groups by what it returns, and
  `routeColumnGroup` dices by the same `joinGraph`.
- **Hand-off: no proxy ring.** A group is one region whose shapes are its
  members, each an ordinary column shape with its own id, rail ring and rails,
  plus `sewAs.join: true`. The engine sews a region's joined columns as one
  path. A proxy `outer` of the first member would have left the others out of
  the design's bbox and without an outline to click. A group the router cannot
  sew falls through: its members sew one by one.
- **Where a group sews.** At the place of its LAST-drawn member, so strokes
  drawn over a fill still sew over it.
- **Underlay.** No shape carries a per-shape underlay override today, so that
  clause had nothing to test. A group takes the router's centre walk under
  each satin span. On the two fabrics whose satin underlay is `zigzag`
  (fleece, terry) that is NOT what a lone column gets there; the router has no
  zigzag pass.

Also built, not in the first draft: **the tuck** (`tuckSatinEnds`). A satin
span ends on a rail and the walk then steps needle-down to the next span's
start on a spine. Measured, that step lay across finished satin half the time
(an L of two 4 mm strokes: 2.1 mm, or none, by which way the walk went). When
the step from the other end of the span's last cross is covered and this one
is not, the span sews that cross back, one stitch, and leaves from there.

## 4. The instrument, before any flip

A group's promise is "no jumps, no trims, no bare travel". The third is the
one a green suite has hidden before (ROADMAP gate 3), so it is measured, not
assumed:

- **Exposed travel, mm.** Every underpath stitch of a group must lie under a
  satin span sewn after it, within that span's half width. Reported per group;
  the test bar is 0.00 mm.
- **Trims and jumps inside a group.** Bar: 0.
- **Trims per design, joined vs unjoined**, same drawing.

Fixtures, each drawn as Columns at 1 mm and at 4 mm: a T, an X, a Y fork, a
closed loop with a stem (the video's rose, redrawn by us), two components that
do not touch. Kent gets renders of each, joined beside unjoined, before he is
asked about the default.

*As built, 2026-11-14.* `tools/join-strokes.mjs` (the table; `--svg` writes
the sheet), bars in `test/join-strokes.test.js`. It reports two lengths per
group: travel no LATER satin covers, and of that, travel under no satin at all
(bare cloth).

| | bar | measured, 12 groups | with the tuck off |
|---|---|---|---|
| jumps + trims inside a group | 0 | 0 on all | 0 on all |
| travel no later satin covers | 0.00 mm | 0.00 on all | 0.00 on 7; 0.50, 0.52, 0.55, 2.02, 2.10 |
| of that, on bare cloth | 0.00 mm | 0.00 on all | 0.00 on all |

Trims per design, as drawn -> joined: T 1 -> 0, X 1 -> 0, Y 2 -> 0, loop +
stem 2 -> 0, two sets 3 -> 1. Not sewn.

**The instrument was wrong twice before it was right**, and read plausibly
both times. A satin span's body was first taken as "even stitches are one
rail, odd the other". The zigzag leads with the other rail on every second
cross, so that polygon crosses itself and holds about half the column; it
read 0.00 to 0.29 mm (the repo reviewer caught it, and the tuck shared the
mistake). The second try, the triangles of each three stitches in a row,
leaves a gap at alternate rails that pinches to the spine, where the travel
runs: it read up to 11 mm on bare cloth. The body is now the quad of each four
stitches in a row, and `measure` is held to three cases with known answers
(30 mm of travel under a later satin, on top of an earlier one, beside one).
ROADMAP gate 3 in miniature: a bar met by an instrument nobody checked.

## 5. Tests

- `penStroke` unit tests: dead zone, simplify under the cap, snap, sticky
  width and colour, a stroke equals a clicked shape's record shape.
- Component and e2e: drag draws a Column and a Line; click-drawing unchanged.
- `node --test`: group routing on the §4 fixtures; flag off is byte-identical;
  lettering byte-identical with the crossing option absent.

## 6. Out of scope, named

- **Lines in a group.** A 3-pass bean is not covered by anything, so a doubled
  Line edge is visible thread. Needs its own rule.
- **Entry / exit dragging, auto centre start/stop.**
- **Dragging a closed Shape or Hole**, and drawing on the hoop instead of the
  side canvas (ruling 4 of the 2026-09-30 spec deferred that; still deferred).
- **An automatic outline lane in the Python digitizer.** Its nearest form,
  `line_chain_one_thread`, was ruled OFF by Kent on 2026-11-11; gate 3 bars
  flipping a chaining tier before its instrument is rebuilt; and sewing lines
  as 1 mm satin where we sew bean under 1.2 mm is a satin-width-floor question
  that only a sew-out settles (gate 1).
- **Any change to a width floor.** A 1 mm Column is already accepted; whether
  it sews well on a given fabric is not decided here.

## 7. To verify first in PR 2

`shapesToRegions` emits one region per shape and the Studio never passes
`minimizeColorChanges`, so whether two same-colour hand-drawn shapes share a
thread today, or take a colour record each, was not traced through
`generate.js` for this spec. Auto-branch needs the answer before it groups.

Observed while building PR 1 (2026-11-13, browser, not traced through the
code): one drawing holding two Columns of the same default colour reads
"2 colors" in the Studio's footer. That points at a colour record per shape.

*Traced, 2026-11-14 (PR 2).* It is a colour record per shape. `shapesToRegions`
emits a region per shape; `buildQualityDesign` opens a colour block (a trim
and a colour change) per region unless `minimizeColorChanges` is passed, and
the manual branch of `generate.js` does not pass it. So every hand-drawn shape
is a machine stop, same thread or not. Already on file as a `todo` in
`test/colour-order.test.js` ("engine default emits a needless colour change
between adjacent same-rgb regions"). Auto-branch does not depend on it: a
group is one region, so one block. Left as it is here, because changing it
moves every existing drawing with two same-colour shapes; it is Kent's call.

## 8. Rulings

1. Spec pen and auto-branch first, ahead of an automatic outline lane (Kent,
   2026-11-13: "Pen + auto-branch").
2. Auto-branch is a per-drawing tick, built OFF; existing designs are
   byte-identical (Kent, 2026-11-13: "Checkbox, built OFF").
3. A new Column takes the last Column's width; the first is still 4.0 mm
   (Kent, 2026-11-13: "Remember last width").
