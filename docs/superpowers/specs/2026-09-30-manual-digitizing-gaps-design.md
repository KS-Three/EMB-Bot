# Holes, open runs and satin columns in the manual lane — design

## 0. Where this starts

`2026-09-29-shape-popover-design.md` §8 named three things out of scope and
called them "the deeper manual-digitizing gaps surfaced in the same session
(Explore report 2026-09-29); separate brainstorm". Kent picked them on
2026-09-30 and made two rulings before any code was designed:

- **One spec for all three**, because they share one change to the shape
  model and doing that twice is how the two `generate.js` branches drifted
  apart before (`generate.js`'s manual/preset comments, 2026-08-26).
- **A satin column is authored as a spine plus a width in mm**, not as two
  drawn rails. Drawn rails stay possible later (§9) but are not built.

Everything below was read off the tree at `4b75546`, not remembered.

**Amended 2026-10-01 — how a hole is expressed (ruling 11, §10).** Two
sessions designed holes on the same day: this spec's first draft (a ring
stored inside its parent, drawn in a Hole mode) and a second one (a normal
shape marked **Cut out**). Kent was shown the two side by side with their
catches and picked **Cut out**, twice. §1's holes paragraph, §4's model, §5,
§8 and §9 are rewritten to that; rulings 3, 4 and 10 are kept and restated
for it. Runs and columns are untouched.

## 1. What is actually missing, located

**Holes — the engine is nearly done.** `app/src/lib/manualShapes.js:609`
hardcodes `holes: []`. Every consumer downstream already handles holes:
`src/digitize.js:612` reads `shape.holes`, forces the fill tier when there is
one (`:619`, `:626` — "satinColumn can't represent a hole"), fills even-odd
over `rings = [poly].concat(holes)` (`:661`), insets each hole for pull
compensation with the winding-flip guard (`:727-733`), running-outlines each
hole (`underlayRuns`, `:228`), and `pcaAngleDeg(rings)` takes holes into its
axis. `imageRegions.js` has produced holes since Image mode shipped.

**One engine defect stands in the way, measured 2026-10-01 on `8776db77`:**
both hole readers keep only rings of **four or more points** (`:216`, `:612`
— `hh.length >= 4`), so a triangular hole is dropped without a word. A 300 px
square at 50 mm, fill, no underlay: 4,678 stitches with no hole, **4,678 with
a 3-point triangle hole**, 4,456 with a 4-point square hole. Traced holes are
pixel contours and never have three points, which is why Image mode never met
it; a hand-drawn A's counter is exactly three. The outer ring's own floor was
relaxed 4 → 3 for this same reason (`:591-600`); the hole floor was missed.
The first draft's "no engine change" was wrong by this much.

**Open runs — nothing to stand on.** Every manual shape is a closed ring, in
four places independently: `shapeIssues()` demands ≥3 points and non-zero
area (`manualShapes.js:77-104`), `shapesToRegions` flattens with
`closed=true` (`:586`), `digitize.js:600` filters out any shape without
`outer.length >= 3`, and `tierOverride` accepts only `"satin"|"fill"`
(`:630`). The stitching primitive half-exists: `satinplay.beanFromGeom(geom,
f0, f1, {passes})` (`src/satinplay.js:846`) is what the lettering lane sews a
hairline stretch with, but it takes a `columnGeom`, not a bare polyline, and
`fill.runningOutline(ring, …)` takes a closed ring. **A path-walker is the
one genuinely new piece of stitch code in this spec.**

**Columns — the rails exist, the authoring does not.** `stitchType: "satin"`
already forces the satin tier and deliberately bypasses the branch guard
(`digitize.js:621-632`), but the rails are *derived*: `medialSatin(poly, …)`
(`:716`) reads them off the polygon's medial axis, and the fallback splits the
outline at `farthestBoundaryPair`. The author gets no say in where the column
starts, ends, or which way the stitches run.
`satinplay.satinFromRails(railA, railB, rungs, opts)` is public and already
sews from given rails; `buildLetteringDesign` is the standing precedent for
feeding the engine authored geometry instead of a traced polygon.

## 2. The shortcut this spec is built on

A column and a run do not need a new kind of region, a second builder, or a
parallel pipeline. **Both still hand the engine a closed `outer`; what is new
is a per-shape instruction for how to sew it.**

- A column's `outer` is `railA` + `reverse(railB)`, closed. That ring is a
  truthful outline of the column, so `underlayRuns` (`:212`, reads
  `shape.outer`/`shape.holes`), the finishing outline (`:751`), the bbox and
  centre-out qualification (`:736`), the trim decision (`:761`), `pushSpan`
  and — load-bearing for #562 and #570 — the `shapeOutlines` entry a click
  hit-tests all work **unchanged**. Only the top-stitch line changes: call
  `satinFromRails` with the authored rails instead of `medialSatin(poly)`.
- A run's `outer` is its path stroked at a hairline, closed. Same deal: it
  gives the run a clickable outline, a bbox and a place in the sew order,
  while the top stitch comes from the path.

So the engine change is small and local: `digitize.js:600`'s filter, the
region loop, sequencing, trims and spans are untouched — which is what
keeps every existing fixture byte-identical.

**For a column the shortcut is free. For a run it is not, and the first
draft of this spec was wrong about it** (closed in the grilling, ruling 1).
A column's ring is truthful geometry, so everything that reads `outer` keeps
meaning what it says. A run's stroked ring is a PROXY — it is not area — and
two consumers would sew it if allowed: the underlay would read the hairline
ring as `thin` (`:619`) and walk a `center_run` down it, turning a 3-pass
bean into 4, and `o.outline` would running-stitch AROUND the line at half a
hairline's offset for double the stitches. So a run takes **three explicit
gates**, not one field read:

```js
const isRun = shape.sewAs && shape.sewAs.kind === "run";
if (useUnderlay && !isRun) { /* existing */ }
pts = isRun ? runAlongPath(...) : (thin ? satinOrRails : fill);
if (o.outline && !isRun)   { /* existing */ }
```

`manualShapes.js` carries the matching comment: a run's `outer` is a stroked
proxy for hit-testing and the bbox, and nothing may sew it.

## 3. Constraints that are forced

- **Byte-identical for everything that exists today.** A shape with no `kind`
  is a closed shape; a shape with no `sewAs` sews exactly as it does now.
  Engine `node --test`, the Studio suite and every golden must be green with
  nothing re-captured.
- **One door into the engine.** `buildQualityDesign` owns pull comp, underlay,
  trims, sequencing and spans — and no ties, because it has none (ruling 7).
  Nothing here gets a second path to the stitch list (`generate.js`'s manual
  branch comment: "no parallel pipeline").
- **Do not bump `PROJECT_FILE_VERSION`.** It is 2
  (`app/src/lib/projectFile.js:30`) and these fields are additive inside an
  element. Bumping has burned this repo once already: the migrator matched
  `version === 2` exactly and imported a v3 save as an empty design carrying
  the customer's file name, reported as success (`projectFile.js:143-149`).
- **Draw order is sew order** (`darkOnTop: false`, Kent 2026-08-26). A hole
  sews with its shell; a run and a column take their own place in the list.
- **Holes force fill. That is engine law, not a bug to route around**
  (`digitize.js:619`). A satin shape that gains a hole becomes a fill shape.
  The UI says so in words; it does not silently re-tier and it does not try
  to satin a ring.
- **Every shape must have an outline on the field or it is unreachable.**
  #562's popover and #570's node editing both hit-test that outline. A shape
  with no filled area still needs one (§2). A cut-out is the one shape whose
  outline the field builds itself rather than reading from `shapeOutlines`
  (§5) — it has no region for the engine to outline.
- **Authored geometry travels through `design.fit`.** `lib/fieldNodeEdit.js`
  converts px↔mm through the engine's own fit and nothing else (#570). Holes,
  paths and spines use the same route — no second transform.
- **Right-click is taken twice** (field tool menu; `ManualPanel` curved
  node) and left-click opens the popover (#562). New tools need a mode, not
  another click meaning.

## 4. The shape model

```js
// today — closed is the only kind
{ id, points, curves, stitchType: "fill"|"satin"|"auto", colorRgb, angleDeg }

// after — `kind` absent means "closed", so every saved file and every
// preset element is unchanged by definition
{ id, kind: "closed"|"run"|"column", points, curves, colorRgb,

  // closed only
  stitchType, angleDeg,
  cutOut: true,   // absent === today. A cut-out sews nothing; it removes its
                  // own area from the smallest shape that contains it (§5)

  // run only
  passes,        // 1 = single run, 3 = bean
  stitchLenMm,

  // column only
  widthMm,
  taperMm }      // null = untapered
```

`shapesToRegions` (`manualShapes.js:583`) grows one field beside the
`tierOverride`/`angleOverride` hooks it already sets:

```js
{ id, outer, holes, tierOverride, angleOverride,
  sewAs: null                                   // closed: unchanged
       | { kind: "run",    path, passes, stitchLenMm }
       | { kind: "column", railA, railB } }
```

`sewAs` is in region px, like `outer`. `digitize.js` reads it in the
top-stitch branch at `:713`, plus the two gates §2 names for a run.

**The author draws on the SIDE canvas, in four modes** (ruling 4):
`Shape | Hole | Column | Line` as a segmented strip above the existing draft
buttons — the control pattern #564 used for hoops and views. Every kind reuses
the draft machinery that is already there (points, curves, `Undo point`,
`Clear shape`, `Finish shape`) and differs only in its commit rule and its
validity rule, so there is no second drawing surface to build. Hole mode
draws a shape that is born marked Cut out (ruling 11) — it needs no selected
parent, because the parent is found by containment, not chosen. Editing
stays on the hoop canvas, where #570 put it; drawing on the field was
considered and deferred — the field already binds left-click, right-click,
body drag and node drag, and a drawing mode has to take the canvas over and
hand it back cleanly.

**A run and a column convert into each other** (ruling 8). Both are the same
open spine, so the popover offers *Make it a column* / *Make it a line* and the
conversion swaps which fields the shape carries — no geometry code, no new
validity rule. Drawing in the wrong mode costs a click, not a redraw.
Closed ↔ open is NOT offered: it needs real geometry rules and would have to
decide what happens to a converted shape's holes.

## 5. Holes (plan 1) — a shape marked Cut out

**The model (ruling 11).** A hole is an ordinary closed shape with
`cutOut: true`. It stays in `element.shapes`, keeps its own id, and is
selected, node-edited, duplicated, copied and deleted by the code that already
does those things to a shape. Nothing is stored about which shape it cuts:
that is **resolved by containment every time**, by one pure function,
`resolveCutOuts(shapes)` in `manualShapes.js`:

- A cut-out's **parent** is the smallest-area valid, non-cut-out shape whose
  flattened ring contains every vertex of the cut-out's flattened ring with no
  edge of one crossing an edge of the other. Smallest, so an O's counter drawn
  over a patch cuts the O and leaves the patch whole.
- A cut-out with no such shape **cuts nothing**, and says so: *"Not inside a
  shape — cuts nothing."*
- Two cut-outs of one parent that cross or nest: the earlier one in the list
  stands, the later one cuts nothing — *"Overlaps another cut-out — cuts
  nothing."* The engine fills even-odd, so letting both through would sew the
  overlap back in.
- An invalid cut-out reports its own first `shapeIssues` string. The area
  floor is the existing `MIN_AREA_PX2` (ruling 10) — a cut-out is a shape.
- A normal shape drawn inside a cut-out is just a shape: it sews, as an
  island.

**Authoring — two ways in, one record.** Click a shape on the hoop canvas and
flip **Cut out** in the popover (#562); or pick **Hole** in the side canvas's
mode strip (ruling 4) and the next finished shape is born marked. The assign
box carries the same toggle. A cut-out's popover hides colour, stitch type and
angle — it sews nothing — and reads *"Cuts Shape 3."* or the reason it cuts
nothing. The shape list reads `Shape 7 · Cut out`.

**Trace import marks holes itself.** `manualTrace.js` used to drop a traced
hole with a warning ("it will render solid; cut it in by hand"). It now emits
each real hole as a `cutOut` shape right after its parent, simplified and
curve-fitted like an outer ring. A hole that no longer resolves to that parent
after simplification is dropped, with the warning kept for exactly that case.

**Sewing.** `shapesToRegions` emits one region per sewn shape, as today, with
`holes:` the flattened rings of the cut-outs that resolved to it. A cut-out
emits no region. `digitize.js` changes in one way only: the hole floor at
`:216` and `:612` goes 4 → 3 points (§1).

**Outlines.** A cut-out has no region, so the engine emits no `shapeOutlines`
entry for it. The field builds a cut-out's outline itself from the authored
ring through `design.fit` (`pxToFieldMm` — T() without the rounding, the same
map the engine's own outlines use) and draws it dashed. That covers a cut-out
that cuts nothing too, which no engine entry ever could — it has to stay
clickable so it can be fixed or deleted. `fieldNodeEdit`'s bbox skips cut-outs
so it keeps agreeing with the engine's, which never sees them.

**Saying it.** A satin shape with a cut-out in it shows *"Sews as fill — satin
cannot go round a cut-out."* beside the stitch-type control, and the control
reads Fill. The stored `stitchType` is left alone, so removing the cut-out
gives the satin back.

**A drag cannot break containment — it HOLDS** (ruling 3). A node drag that
would take a cut-out outside its parent, or pull the parent across one of its
cut-outs, stops at the last good position, the same posture as Kent's
placement-box ruling on this canvas in #570, with the hint *"A cut-out has to
stay inside its shape."* The test is one function, `breaksContainment(before,
after)`: any cut-out that had a parent before the edit and does not have that
same parent after it. `editedElementPatch` refuses on the same predicate, so
inserting or removing a point cannot break it either. A cut-out that already
cuts nothing is free to move. The same hold-last-good guard closes the gap
#570 left in the placement box: a bent edge is tested on its flattened curve,
not on the handle's through point (a quadratic through a clamped midpoint can
still bulge past the box — worked example about 2%).
Rejected: refusing the edit outright the way the digitized lane's
`apply_shape_edits` does (`Hole lies outside shell`, 400) — #570 already chose
clamping over refusing on this surface.

**Known residue, deliberately left** (ruling 3, the half not taken):
`shapesToRegions:697` still drops an invalid shape SILENTLY, with no message
anywhere. A self-crossing hand-drawn shape vanishes from the stitch-out today
and still will. The clamp means editing cannot cause it; drawing and import
still can.

**Drawing and editing.** The side canvas draws a parent and its cut-outs as
one even-odd path so a hole reads as a hole while it is being drawn, and a
cut-out's own outline dashed. On the hoop canvas the stitching itself shows
the hole. Node editing needs no wider address: a cut-out is a shape, so
`(elementId, shapeId, anchorIndex)` already reaches every one of its points,
and the re-fit rule (`editedElementPatch`) already patches
`shapes + sizeMm + offsets` together.

**What the first draft's design would have cost, for the record.** A ring
stored inside its parent is not a shape: click-to-select, the popover, node
drag, insert, remove, Delete, duplicate and copy/paste would each have needed
a `holeIndex` beside the shape id. That is the trade Kent was shown.

**As built (2026-10-01) — where the build went past this section.**
- **Hole mode on the side canvas: a click always draws, never selects.** In
  Shape mode a click inside a finished shape selects it (PR #104), which made
  it impossible to start a shape inside another — exactly where a hole goes.
  (Session ruling; not yet the owner's.)
- **The hoop's Cut out switch goes through the re-fit rule**
  (`refitShapesPatch`, the arithmetic factored out of `editedElementPatch`),
  so flipping it moves nothing else. The side panel's switch does not: the
  panel has no fit to hold. (Session ruling; not yet the owner's.)
- **An equal-area tie for the parent stays with the earlier shape**, so
  Duplicate leaves a hole with the original. (Session ruling after the final
  review.)
- **The drag guard's box test only holds a shape that was inside the placement
  box when the drag began** (`boxOk`); one already past it keeps #570's
  behaviour.
- **A cut-out that cuts nothing is drawn dashed on the hoop whenever its
  element is selected** — it has no stitches to show where it is.
- **Trace import:** a hole is tried curve-fitted, then straight, then dropped
  with the warning; each try is checked against the parent's already-kept
  holes as well as the parent. The preview draws a parent and its holes as one
  even-odd path.
- **`flow.js`'s `isSewable` ignores cut-outs:** an element holding only
  cut-outs sews nothing.
- **§8 named a new `test/manualkinds.test.js`;** the engine test for the hole
  floor lives in `test/digitize.test.js` instead.

## 6. Satin columns (plan 2 — Kent's spine + width)

**One new pure function**, `railsFromSpine(spine, halfWidthPx, { taperPx })`,
in a new `app/src/lib/spineRails.js`: per-vertex normals from the averaged
adjacent tangents, miter clamped (the clamp `offsetRing` already needs, for
the same reason), both rails emitted with **the same point count in the same
order**, so `satinplay.correspond` has nothing left to guess and no rung list
is needed. Taper scales the half-width from the ends inward.

`shapesToRegions` then sets `outer = railA.concat(reverse(railB))`,
`tierOverride = "satin"`, and `sewAs = { kind: "column", railA, railB }`.

In `digitize.js:713`, inside the existing `if (thin)`:

```js
pts = (shape.sewAs && shape.sewAs.kind === "column")
  ? satinplay.satinFromRails(shape.sewAs.railA, shape.sewAs.railB, [],
      { spacingMm: satinSpacingMm, pxPerMm: pxPerFinalMm, pullCompMm, slantDeg })
  : sat(poly, { spacingMm: satinSpacingMm, pxPerMm: pxPerFinalMm, pullCompMm, slantDeg });
```

Pull comp stays where it is — inside satin, through `pullCompMm`, exactly as
the derived path gets it (`:707-710`). Underlay comes from the synthetic
`outer` and is the same `satinUnderlay` style a derived column gets. **The 3
mm satin ceiling must not touch this**: `satinMaxWidthMm` is a classifier
threshold and `tierOverride` already replaces it (`:621-632`), so a 6 mm
authored column sews as the author drew it — but the UI warns above the
`wide_columns` ceiling read off the pro's sewn MARINE (6.5 mm, MASTER_SCOPE
item 4), because that is a sewability fact, not a code limit. The warn names
where 6.5 comes from (the pro's p99 6.2) and offers the two outs — a fill, or
split into two columns — and **never blocks**, the same posture
`legibility_check` was ruled into (warn, never block, 2026-09-10). A hard
clamp would refuse what the pro's own sewn files do: 7–23% of their satin
crosses are over the 5.0 mm cap.

**`widthMm` is the DRAWN width, and the panel shows the sewn one beside it**
(ruling 2). Rails are built exactly `widthMm` apart and satin's own pull comp
pushes each out by `pullCompMm / 2` (`satin.js:259`), so 4.0 mm drawn lands
4.4 mm wide on jersey. The panel reads `Width 4.0 mm → sews 4.4 mm on Jersey
tee`. The alternative — `widthMm` meaning the ruler reading on the garment —
was rejected because it makes the stored geometry move whenever the garment,
the fabric preset or #569's calibration profile changes, and inverts the rails
below `pullCompMm`. Gate 1 stays: the amount is untouched.

## 7. Open run paths (plan 3 — the only new stitch code)

**One new pure emitter**, `runAlongPath(path, { stitchLenPx, passes })` in
`src/fill.js` beside `runningOutline`: walk the open path at `stitchLenPx`,
land a stitch on the final vertex exactly, and for `passes: 3` go
forward/back/forward over the same stations so the bean is a true bean and
not three independent walks (the mistake `satinplay`'s own comment records
about the convenience underlay form, `satinplay.js:853-860`).

**Defaults are the corpus's, not invented** (ruling 6): `passes` 3 and
`stitchLenMm` 0.73, reusing `BEAN_PASSES` / `BEAN_STITCH_MM` — the same
constants both engines already carry (`satinfont.js:79-80`,
`machine.py:708-709`), measured off 14 professional bean outlines at 2.75
passes median (p90 3.27) and 0.73 mm (p10 0.67, p90 1.87). In JS the two are
private to `satinfont.js` and reach other code only through its exported
`LETTERING_GUARDS` (`:1286`, on the `EMB` global) — read them there, do not
re-declare them. A run
shorter than `RUN_MIN_LOOP_MM` 2.2 is refused, the same floor that already
decides when a run "reads as lint". **That one is Python-only**
(`machine.py:724`; the browser engine has it as a comment at
`app/src/lib/digitizer.js:717`, not a value), so plan 3 adds ONE JS constant
mirroring it — a new declaration, not a new number. Both controls stay
editable. A 40 mm line sews ~165 stitches, which is what a pro's bean outline
is.

**A run sews untied, like every other shape in this lane** (ruling 7).
`buildQualityDesign` has no tie code at all — lock stitches exist only in
`buildLetteringDesign`, default OFF (`digitize.js:1053-1081`), whose own
comment says the Python lane ties every block and this one ties nothing. That
gap is real and is NOT closed here: porting `tieIn`/`tieOff` into
`buildQualityDesign` changes every file a customer exports, so it gets its own
PR with the bill measured in front of Kent, which is what that comment says
this house does. The bean's three passes over the same stations are partly
self-securing meanwhile.

`shapesToRegions` sets `outer = strokeClosed(path, hairlinePx)` for
hit-testing and bbox, `tierOverride = "fill"` (never satin — nothing here is
a column), and `sewAs = { kind: "run", path, passes, stitchLenMm }`.
`digitize.js` branches on `sewAs.kind === "run"` **before** the
`thin`/fill decision and emits `runAlongPath` as the top stitch, with
`runKinds` entry `"run"` — the span kind already exists.

No pull compensation (a run has no width to lose), no fill underlay, and no
tie — `buildQualityDesign` has none to give (ruling 7). So a **single-pass
run sews unlocked** and does not get even the bean's partial self-securing;
that is the known cost of `passes: 1` until the tie PR lands, not something
this plan papers over.

**The validity split is the real cost here.** `shapeIssues` currently means
"is this a sewable closed ring". It becomes two rules: closed as today; open
needs ≥2 points, total length over a floor, and self-crossing is *allowed*
(a signature crosses itself). Every caller of `isValidShape` has to say which
it means — `shapesToRegions:697`, `ManualPanel`'s draft gating,
`lib/flow.js:22`, `fieldNodeEdit.js:222`'s bbox.

## 8. Tests

**Engine** (`node --test`, new `test/manualkinds.test.js`):
a column's stitches equal a direct `satinFromRails` call on the same rails;
`railsFromSpine` on a straight spine gives two parallel rails exactly
`widthMm` apart and a closed `outer` of the right area; `runAlongPath` with
`passes: 3` gives 3× the stations of `passes: 1` and both end on the last
vertex; a shape with `holes` sews fewer stitches than the same shell without
one and its tier is fill even with `tierOverride: "satin"`; **a 3-point hole
cuts as a 4-point one does** (§1's measured defect); **and every existing
fixture is byte-identical with `sewAs` absent.**

**Studio** (`vitest`): `spineRails.spec.js`; `manualShapes.spec.js` for
per-kind validity and `resolveCutOuts` (inside, crossing the parent, crossing
or nesting in a sibling cut-out, smallest parent wins, degenerate, no parent);
`shapesToRegions` emitting holes on the parent and no region for a cut-out,
and each `sewAs` shape; `fieldNodeEdit.spec.js` for `breaksContainment` and
the bbox skipping cut-outs; `shapePopover.spec.js` for the Cut out row, the
cut-out's reduced rows and the satin→fill note; `manualTrace.spec.js` for a
traced ring arriving with its hole; `ManualPanel.spec.js` for the mode strip
and the tools' gestures.

**e2e** (`app/e2e/`, against the live service, reading pixels **inside the
fabric** — the rule three specs now share since #564's surround): draw a
shape, cut a hole, see the caption's stitch count drop and the hole in the
render; draw a spine, set a width, see a column; draw a line, set 3 passes,
see a bean; node-edit a hole's anchor and a spine's anchor on the hoop
canvas and confirm nothing unedited moved (#570's invariance assertion,
reused).

Plus the standing rule: **a Studio change is not verified until it has been
looked at in a browser** (MASTER_SCOPE; six buyer-visible defects none of
which a green suite saw). Screenshots at 1440×900 and 1024×768 per plan.

## 9. Build order

1. **Holes** — the Cut out mark, plus the engine's 3-point hole floor.
   Smallest, and it lands the hold-last-good drag guard the other two reuse.
2. **Columns** — `railsFromSpine` + the one-line `sewAs` branch in the satin
   emit. Medium.
3. **Runs** — `runAlongPath` + the validity split across the four callers §7 names.
   Largest, and last because the split touches the other two's callers.

Each is its own PR with its own plan, off this spec.

## 10. Rulings — ten closed in the grilling (2026-09-30 / 10-01), an eleventh after it

Nothing in this spec is waiting on Kent. Where an earlier section once said
"recommendation", the ruling here is the decision and the section has been
rewritten to match.

1. **A run's `outer` is a proxy, and nothing may sew it.** Three explicit
   gates: underlay off, finishing outline off, `runAlongPath` as the top
   stitch. Closed the defect that would have turned a 3-pass bean into 4 and
   double-outlined every line (§2).
2. **`widthMm` is the drawn width; the panel shows the sewn one beside it.**
   Rails built at `widthMm`, satin's pull comp pushes them out as it does for
   every traced shape. Geometry never moves when the garment, preset or
   calibration profile changes (§6).
3. **A node drag CLAMPS at containment** rather than going invalid or being
   refused — #570's placement-box posture. The silent-skip of an invalid shape
   stays unfixed and is named as residue (§5).
4. **Four mode buttons on the side canvas** — `Shape | Hole | Column | Line`,
   reusing the draft flow. Editing stays on the hoop. Drawing on the field
   deferred, not rejected (§4).
5. **A column wider than 6.5 mm warns and still sews.** The message names the
   pro's p99 6.2 and offers a fill or a split. Never blocks — `legibility_check`'s
   ruled posture (§6).
6. **A run defaults to 3 passes at 0.73 mm, floor 2.2 mm**, reusing
   `BEAN_PASSES` / `BEAN_STITCH_MM` / `RUN_MIN_LOOP_MM`. No new NUMBERS: they
   are measured off 14 professional bean outlines. One new JS declaration,
   since `RUN_MIN_LOOP_MM` exists only in Python today (§7).
7. **Lock stitches are out of scope here.** `buildQualityDesign` has none at
   all; porting them changes every exported file, so it gets its own PR with the
   bill measured. Runs ship untied like everything else in the lane (§7).
8. **Run ↔ column converts; closed ↔ open does not** (§4).
9. **A column defaults to 4.0 mm and taper is deferred** out of plan 2. The
   stored model keeps `taperMm`, so taper lands later without a migration.
10. **A hole's minimum size reuses the existing sewability floor** rather than
    introducing a second number.
11. **A hole is a shape marked Cut out** (2026-10-01, outside the grilling:
    Kent shown both designs side by side, and again after the collision
    between the two sessions was found). Not a ring stored in its parent. The
    parent is resolved by containment (§5). Rulings 3, 4 and 10 stand and are
    restated for this model: the drag guard holds a cut-out inside its parent,
    the side canvas's Hole mode draws a shape born marked, and a cut-out's
    floor is a shape's floor. Also Kent's, same day: **a satin shape with a
    cut-out sews as fill and says so**, rather than the cut-out being refused
    until the author switches the shape to Fill by hand.

Two things the grilling corrected in this spec rather than decided: the
"one field read in one place" claim in §2 was wrong for runs, and §10's
original item 5 asked about a run's tie as if the lane had ties — it has none.

## 11. Out of scope, named

- **Drawn rails** for a column (Kent's ruling). The stored model leaves room
  for `rails` beside the spine, so this arrives without a second migration.
- Multi-rail / branching columns; rungs authored by hand.
- Reorder, merge, split, or converting a closed shape into a column or a run.
- Holes on the *digitized* lane — the boundary override already carries them
  and rejects a shell dragged across one (area 5 doc).
- Any change to the Python pipeline. This is the browser engine and the
  manual lane only.
