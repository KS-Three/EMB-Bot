# Precise node editing on the hoop canvas — design

Status: rulings closed in Kent's grilling, 2026-11-03 (section 9). Build order
in section 8. Nothing built yet at the time of writing.

## 0. Where this starts

Kent, 2026-11-03, after digitizing his Instagram icon (63 x 52 mm, 6 colours,
digitizer service) and dragging ONE node on the outer purple rounded square:

> the nodes are very difficult to edit. When i move one, the entire spline
> seems to follow. I need the UI to be much easier to use, so i can edit
> specific shapes, borders and boundaries very precisely.

His screenshot shows a smooth flap, about 50 mm of the outer ring's boundary,
swung out to the upper left from one corner drag.

Kent's pick, same day, from three options: **precise drag + a reshape tool**
(point selection, multi-drag, nudge, delete, right-click, readout), over
"precise drag only" and "precise drag + select/delete". The grilling that
followed (section 9) widened it to both lanes and to holes.

## 1. What happens today, located

**It is not a bug. It is `pullRing`** (`app/src/lib/shapeOverlay.js`,
commit `a027d3cd`, 2026-08-13). A node drag on a digitized shape moves the
grabbed vertex by the full delta and every vertex within an arc-length
RADIUS by a raised-cosine share of it, where

    radius = min( max(3 mm, 2 x drag distance), 25% of the ring's perimeter )

It was built after Kent said, of the owl photo, "i can move the nodes, but
the stitch fill STILL isn't working": that outline has 346 vertices on a
458 mm perimeter (1.3 mm apart), so a one-vertex drag added a needle no fill
row could occupy. The 2x radius was swept against the pipeline at a 6 mm
pull: 1x put 11 stitches in the new area, 2x 31, 3x 27. 2x shipped.

The rule was tuned on one dense photo outline and applied to every digitized
shape. Measured with the real `moveNode` on a 52 x 52 mm rounded square with
nodes ~5 mm apart (Kent's Instagram outer ring, spacing read off the
screenshot; script `pull_measure.mjs`, scratch, 2026-11-03):

| gesture | nodes moved | boundary moved |
|---|---|---|
| 11 mm corner drag (the screenshot) | 9 of 36 | 53 mm = 28% of the ring |
| 3 mm nudge | 3 of 36 | 21 mm = 11% |
| 1 mm nudge | 1 of 36 | 11 mm = 6% |
| same ring at 2 mm spacing, 11 mm drag | 22 of 96 | 46 mm = 24% |
| 63 mm ring, 25 mm drag (hits the cap) | 21 of 48 | 106 mm = 46% |

At 5 mm spacing a single-vertex move of 11 mm is a triangle 10 mm wide at
its base: fillable without any pull at all. The needle problem exists only
when nodes sit closer than a fill row can turn in, about 1-2 mm. So the pull
should key on NODE SPACING, which is what made the owl fail, not on drag
distance, which is what the user is trying to control.

**Four more things found on the way, all real:**

- `hitOverlay` returns the FIRST node within `NODE_GRAB_PX` (9 px), not the
  nearest. On a ring with nodes under 9 px apart on screen (1.3 mm nodes at
  the 1x hoop scale of ~7 px/mm) the grab lands on a neighbour of the node
  under the pointer. That alone reads as "imprecise".
- The service already sends every shape's holes (`holes_mm`,
  `digitizer_service/app.py` `_review_payload`). The Studio's
  `reviewFromJob` never reads them, nothing draws them, and
  `boundary_override` is exterior-ring-only by contract (v1.4): the server
  re-attaches the shape's ORIGINAL holes to the edited shell and 400s when
  one pokes out. The Instagram white ring's inner edge, the lens, is a hole.
  Kent cannot see it as a boundary, let alone edit it, and an outer-edge
  edit that crosses it is refused with a server message.
- There is no way to remove a point on a digitized shape from the canvas.
  Delete removes the SHAPE. Point removal exists only in `DigitizePanel`'s
  old SVG editor (`startBoundaryEdit`, right-click a vertex), which the
  canvas editor superseded on 2026-08-12. Adding a point (double-click an
  edge) is on the canvas.
- **Moving one side of a seam shows nothing, or shows fabric.** Stage 5
  (`stage5_overlap.py`) clips a later colour by the colours already down and
  hides an earlier colour's growth under the later one; a gap between two
  artwork edges is bare fabric (`forbid_gap_mm` is OFF). The lens hole's edge
  and the pink region's outer edge are one line in the art, traced from two
  masks. Drag the hole edge alone and the pink underneath is either clipped
  or hidden; drag the pink alone and the white hides it. A seam has to move
  on both shapes at once to be seen to move.

The hand-drawn lane (`fieldNodeEdit.js`, 2026-09-29 spec) already has part
of what Kent asks for: a focused anchor, Delete removes it, a relative grab,
the placement-box hold. This design brings both lanes to one editor.

## 2. Constraints that are forced

1. **A shape's id does NOT move with a boundary edit.** `assign_shape_ids`
   derives the id from the AUTO-TRACED region (stage 0-4, bucketed centroid +
   thread) and `apply_shape_edits` lands the override by that id afterwards,
   so the same image at the same settings re-derives the same id however far
   its override has moved. (The 2026-08-13 test comment that a translated
   shape "gets a new centroid, and the centroid is what makes shape ids
   stable" described the auto-traced centroid, not the edited one; the 25%
   cap it justifies stays only as "a pull is a reshape, not a move".) A
   select-all drag is therefore safe and needs no warning sentence. What
   still changes every id at once is a new generation (crop, size, settings),
   and that risk is the same for every override today.
2. **`boundary_override` is at most 500 points** on both sides of the wire
   (`BOUNDARY_MAX_POINTS`, `_MAX_BOUNDARY_POINTS`), and `outlineFull` is
   already every-nth thinned to 500 by `thinOutline`. A dense photo ring
   arrives at 500 points regardless of its true count. Section 5's simplify
   is how a user gets it down to something editable; nothing may push it up.
   The same bounds apply per hole ring (section 6).
3. **Validation stays on both sides.** `boundaryIssues` (client, live) and
   `apply_shape_edits` (server, authoritative) both hold a ring to simple +
   the sewability floor (0.16 mm², 2.2 mm). Holes extend both; the server
   keeps the last word.
4. **No new readout text that is a warning** (Kent's 2026-10-02 ruling,
   memory `no-warnings-reaches-readouts`). A mm delta beside the pointer and
   the mode strip are instruments, not warnings; a refused edit keeps using
   `shapeEditError` as today.
5. **The existing e2e contracts stay green**: `field-node-edit.spec.js`
   (a)-(h), `field-shape-popover.spec.js`'s "a drag that starts inside a
   shape moves the element and opens nothing", `manual-cutout.spec.js`'s
   hold-at-containment. Outside Reshape mode nothing about a bare drag
   changes; inside it the marquee is the one new meaning of a bare drag.
6. **Model rule for the build** (Kent 2026-11-02): worker sessions run on
   Sonnet. Each PR in section 8 is a Sonnet brief.

## 3. The drag rule (ruling 1)

**One node moves.** `pullRing`'s radius drops the drag-distance term:

    radius = min( PULL_RADIUS_MM (3 mm), 25% of perimeter )

A vertex within 3 mm of arc from the grabbed one takes a raised-cosine
share; at 5 mm spacing that is nobody, at 1.3 mm spacing it is one neighbour
each side at ~0.6 and the next at ~0.04. The dense-outline case still gets a
sewable base (about 5 mm wide, 12 fill rows at 0.4 mm) and the logo case gets
exactly the point it grabbed.

**Alt-drag keeps the old soft pull** (2x drag distance, same cap) for the
photo case the 2026-08 fix was for. Alt already means "unconstrained" on the
canvas (free rotate, snapping off), so it is the natural key. Named once in
the popover's hint line, no toggle in the UI.

**Edge drag** (`moveEdge`) follows the same rule: both endpoints take the
delta, the 3 mm neighbourhood a share.

**Nearest node wins** in `hitOverlay`: among nodes within `NODE_GRAB_PX`,
the closest to the pointer, ties to the lower index. Edges unchanged.

What this costs: at a 6 mm pull on the owl's body the 2026-08 sweep put 31
stitches in the bulge at 2x and 11 at 1x; 3 mm fixed is below 1x for drags
past 3 mm, so expect fewer than 11 on that one gesture unless Alt is held.
That is the trade Kent chose. Re-measure it in PR 1 with the same fixture
and quote the number.

## 4. Reshape mode (rulings 2, 4, 6)

**Hybrid.** A selected shape still drags one node straight away, as today,
under section 3. **"Edit points"** (already in the popover, today a no-op
that closes it) enters **Reshape mode** for that shape's ELEMENT; Escape, a
click on another element, or the popover's "Done" leaves it. A strip on the
canvas edge says `Editing points · Esc to finish` while it is on. Both lanes
(digitized and hand-drawn) get the mode in the same PR.

State, in `EmbroideryField.svelte` beside `selectedShapeId`:

    reshape = { elId, sel: Map<shapeId, Map<ring, Set<index>>> }
    // ring: "exterior" | hole index (digitized) | "anchors" (hand-drawn)

In Reshape mode:

- **Click a node** selects that one point. **Shift-click** toggles it.
  Selected nodes draw filled white inside the amber ring.
- **Bare drag from empty canvas or from inside a shape** is a **marquee**;
  on release, every node of EVERY shape and hole ring of the element inside
  the box is the selection (Shift held: added). A seam is moved by boxing it
  (section 1, last finding). Outside the mode a bare drag still moves the
  element (constraint 5).
- **Drag any selected node**: every selected node takes the same delta.
  Digitized rings: the 3 mm neighbourhood applies around each seed, weights
  taking the max where neighbourhoods overlap (`pullRing` already does this
  for `moveEdge`'s two seeds; `seeds` becomes the selection on that ring).
  Hand-drawn anchors move as anchors do today, each through `applyAnchorDrag`,
  the whole candidate shape held at the last good position by the existing
  cut-out containment guard. Dragging an unselected node first makes it the
  selection.
- **Arrow keys** nudge the selection 0.1 mm, Shift 1 mm, in field mm; each
  press is one undo step. Outside the mode arrows keep nudging the element
  (`onCanvasKey`, 1 / 10 mm).
- **Delete / Backspace** removes the selected points, per ring, refusing at
  the three-point floor with the hand-drawn lane's wording and removing
  nothing on that ring. With no point selected it does what it does today.
- **Escape**: Reshape mode first, then focused anchor, popover, tool menu.
- **Right-click on a node** puts "Delete point", "Select all points" and
  "Simplify points" (section 5) at the top of the field's context menu.
- **Readout while dragging**: `dx, dy mm` beside the pointer in the rotate
  badge's style, gone on release.
- **Popover** gains a read-only `Points: N` line (digitized) and the
  "Simplify points" action; "Edit points" now enters the mode and "Done"
  replaces it while the mode is on.

**Commit.** One gesture = one patch = one undo step, however many shapes it
touched: digitized shapes get a `boundary_override` (and `holes_override`,
section 6) each, hand-drawn shapes go through `commitNodeEdit`'s re-fit rule
with every edited shape in one `elupdate`. `boundaryIssues` runs per ring
before the patch; a refusal on any ring drops the whole gesture and names the
ring, the shapes snap back, nothing is half-applied.

**Retire `DigitizePanel`'s SVG boundary editor** in the same PR (ruling 7):
`startBoundaryEdit` / `saveBoundaryEdit`, the Layers-row pencil and the small
SVG go; `digitize-boundary-edit.spec.js` is re-pointed at the hoop canvas.
Two editors for one override is how they drift, and it would be the one
writer that never learns holes or the 3 mm rule.

## 5. Fewer points (ruling 5)

A dense ring is unpleasant to edit however good the drag rule is: 500 points
on a 200 mm ring is a node every 0.4 mm. Done explicitly, never silently:

- Popover action **Simplify points** with tolerance choices 0.2 mm, 0.5 mm,
  1 mm; Undo is the way back. A closed-ring Douglas-Peucker in
  `shapeOverlay.js` (pure module; the engine's `Geometry.simplify` is a
  browser global the Studio lib cannot import, 20 lines are duplicated rather
  than coupled), committed as a `boundary_override` (+ `holes_override` when
  the shape has holes: they simplify with the shell at the same tolerance).
- It rides the popover's existing **"Apply to all similar shapes (N)"** tick
  (`similarShapes.js`), so a photo's many regions simplify in one patch.
- The popover shows `Points: 500 -> 87` after.
- Never below the three-point floor, never above the current count, and the
  committed rings still pass `boundaryIssues`.
- Digitized lane only; a hand-drawn shape's anchors are authored.

Not auto-applied on first edit: a geometry change the user did not ask for
changes the stitches under them, and Kent judges edges by eye
(memory `instagram-gradient-lane-edges-2026-09-30`).

## 6. Holes (ruling 3)

Today the white ring's lens is invisible and unmovable on the canvas, and an
outer edit that crosses it is refused. Contract change **v1.9, additive**:

- **Review payload**: `holes_mm` already ships. `reviewFromJob` reads it into
  `holesFull: [[[x, y], ...], ...]` (deduped and thinned per hole to the 500
  cap; a hole under 3 points is dropped as the server would).
- **Drawing**: each hole is its own amber ring with its own nodes when the
  shape is selected, same chrome as the shell. `hitOverlay` reports
  `ring: "exterior" | k`.
- **Editing**: every rule in sections 3-5 applies to a hole ring.
- **Wire**: a new `shape_overrides[sid].holes_override`:
  `[[[x, y], ...], ...]` in the same design-centre y-down mm space as
  `boundary_override`. Present: it REPLACES the shape's holes (an empty list
  makes the shape solid). Absent: holes carried over from the shape's own
  geometry, exactly today's behaviour. `boundary_override` is unchanged. Same
  "absent key = default" rule as `stitched` (v1.1), `sew_order` (v1.2),
  `stitch_width_mm` (v1.8). `_OVERRIDE_KEYS` and `EDIT_KEYS` gain the key.
- **Server**: `digitizer_service/app.py` pre-checks each hole ring the way it
  pre-checks the shell (list of finite pairs, 3..500 points, simple);
  `regions.apply_shape_edits` builds `Polygon(shell, holes)` from
  `boundary_override` if present else the current exterior, and
  `holes_override` if present else the current interiors, then the existing
  `is_valid` + floor checks (a hole outside the shell or crossing another is
  already a named refusal). `r.meta["holes_override"]` is recorded beside
  `boundary_override`; `content_key` already folds every override into the
  job key.
- **Client**: `canonicalShapeEdits` emits `holes_override` only when a hole
  was edited, so an exterior-only edit stays byte-identical on the wire to
  today (the request-contract fixture pins this). `boundaryIssues` gains a
  holes argument: each hole simple, every hole vertex inside the shell, no
  hole crossing the shell or another hole. The comment that says the client
  cannot check containment goes.

Order: the service PR lands first, so the Studio never sends what a running
service refuses. A Studio against an older service never emits the key
unless a hole was edited; that older service drops it with
`SHAPE_EDIT_UNKNOWN`-style validation (a 400 naming the key), acceptable on
Kent's single machine.

## 7. Tests

Unit (vitest):
- `shapeOverlay.spec.js`: the 2x-drag tests become Alt/soft tests (same
  assertions, soft flag on); new: a 5 mm-spaced ring moves one vertex at any
  drag distance; a 1.3 mm ring moves a sewable stretch; the far side never
  moves (kept); nearest-node hit (two nodes 6 px apart, pointer 2 px from
  the second, the second returns); multi-seed move (three selected vertices
  each take the full delta); `removeNodes` refuses under three and keeps
  winding; closed-ring simplify keeps every original vertex within tolerance
  of the new ring, a square stays a square.
- `fieldNodeEdit.spec.js`: multi-anchor drag through the re-fit rule; the
  containment guard holds the whole gesture; multi-anchor delete at the floor.
- `digitizer.spec.js`: `boundaryIssues(points, holes)` names hole-outside,
  hole-crossing-shell, hole-crossing-hole; a clean donut passes;
  `canonicalShapeEdits` emits `holes_override` only on a hole edit; the
  request-contract fixture is unchanged.
- `shapePopover.spec.js`: Edit points / Done, Points: N, Simplify rows.

Python (`digitizer/tests`): `apply_shape_edits` with `holes_override`:
replaces holes, `[]` makes a solid, hole outside shell raises with the
existing message family, absent key carries holes over byte-identically;
wire validation 400s a bad hole at submit time; `test_service` round-trips
the key.

e2e (Playwright, real service; `two-squares.png`, a hand-drawn rectangle,
and a donut fixture for holes, new if `trace-holes-and-colors.png` does not
digitize to a holed shape): (a) one node drag moves that node only, stitches
follow; (b) Edit points, marquee over a seam between the two squares' edges,
ArrowRight x3, both edges moved 0.3 mm, three undo steps; (c) Delete removes
a selected point, refuses at three; (d) Simplify 0.5 mm drops the count and
restitches; (e) a hole's node drags and the restitch shows the moved inner
edge; (f) outside the mode a bare drag inside the shape still moves the
element; (g) hand-drawn: marquee two anchors, drag, the caption changes and
the neighbour's stitches stay (field-node-edit (e)'s invariance, kept).

Render the before/after of (a) on the Instagram icon: when the claim is
about geometry, show the picture (DST axis lesson, CLAUDE.md footgun 1).

## 8. Build order

Four PRs, each ready-for-review with auto-merge armed, each a Sonnet brief:

1. **Drag rule + nearest node** (section 3): `shapeOverlay.js`, its spec,
   `EmbroideryField` Alt handling, the owl re-measure quoted in the PR body,
   scope doc + DOCTRINE line. This spec and its memory note ride this PR.
   Half a day. **Starts now.**
2. **Reshape mode, both lanes** (section 4): state, chrome, strip, marquee,
   cross-shape multi-drag, arrows, Delete, Escape order, context-menu rows,
   readout, popover rows; `fieldNodeEdit` multi-anchor ops; retire the panel
   SVG editor; the e2e file. 2-3 days. May land as two PRs back to back
   (digitized, then hand-drawn parity) if the diff gets unwieldy, the second
   before anyone is pointed at the first.
3. **Simplify** (section 5): RDP, popover action, rides similar, tests.
   Half a day.
4. **Holes** (section 6): service PR, then Studio PR. 1-2 days.

## 9. Rulings — seven closed in the grilling, 2026-11-03

1. **Drag rule: fixed 3 mm neighbourhood** (over "one node, never
   neighbours" and "radius = adjacent spacing"). Alt-drag = old soft pull.
2. **Interaction: hybrid.** Quick single-node drag on a selected shape stays;
   "Edit points" enters Reshape mode (bare-drag marquee, arrows nudge points,
   Delete removes points, on-canvas strip). Over mode-only and
   modifiers-only.
3. **Holes wire: new key `holes_override`**, additive, `boundary_override`
   untouched. Over an object form on `boundary_override`, and over leaving
   holes out.
4. **Seams: the marquee crosses shapes** and hole rings of the element; one
   gesture moves both sides of a seam; one patch, one undo step. Over
   selected-shape-only and over welded coincident nodes.
5. **Simplify: per shape, 0.2 / 0.5 / 1 mm, rides "Apply to all similar
   shapes"**. Over a single 0.5 mm action and over element-wide.
6. **Both lanes in PR 2.** Over digitized-only and over a later parity PR.
7. **Retire `DigitizePanel`'s SVG boundary editor in PR 2.** Over keeping it.

Correction recorded during the grilling: a boundary edit never changes a
shape's id (constraint 1), so the spec's earlier one-time warning sentence on
a select-all drag is dropped.

## 10. Out of scope, named

- Curve handles on digitized rings. The service outline is a polygon; a
  bezier representation would be a new contract and a new flattening on the
  server. The hand-drawn lane has handles already and they stay single-drag.
- Whole-shape drag as a gesture of its own (requirement 5 of 2026-08-12,
  withdrawn). Select-all + drag does it when asked for by name.
- Snapping a dragged node to a neighbouring shape's boundary, and welding
  coincident vertices (ruling 4's third option).
- Any change to `pullRing`'s raised-cosine falloff shape.
- `forbid_gap_mm` and anything else in stage 5; a seam the user leaves open
  sews as fabric, as the art would.
- Node editing on cap pieces (`isCapPieceId`) and group-highlighted similar
  shapes; both stay as they are.
