# Sparse smooth nodes on digitized rings — design

Status: rulings closed in Kent's grilling, 2026-11-04 evening (section 9).
Build order in section 8. Nothing built at the time of writing. Follows the
2026-11-03 spec (`2026-11-03-digitized-node-reshape-design.md`) and its
ruling 8 (PR #1237: bare drag exact, Done / Discard).

## 0. Where this starts

Kent, 2026-11-04, after PR #1237 merged: "It's better, but it's still not
perfect." He asked for Ember Design's way of editing and drawing nodes on
photo shapes. The director drove Ember's editor and pixel-diffed it (memory
`ember-reshape-measured-2026-11-04`, behaviour only, nothing of Ember's is
copied). Four things made Ember's editor precise:

1. one point moves, nothing else — shipped in #1237;
2. **few points, because the edge between two points is a curve** — this spec;
3. **click the path to insert a point; double-click a point to make it sharp or
   smooth** — this spec;
4. an accept / reject session — shipped in #1237.

## 1. What a digitized shape's node is today

Every vertex of the shape's `outlineFull` (deduped, thinned to the 500-point
cap) is drawn as a node when the shape is selected, and the same picture is
Reshape mode's. A one-vertex exact move on a ring traced at 0.4-1.3 mm
spacing (owl, any photo) is a spike 1-2 mm wide; on a logo at ~5 mm spacing it
is a usable edit. Simplify (popover, 0.2 / 0.5 / 1 mm) is the only way to
fewer points, and it rewrites the polygon itself.

## 2. The model (rulings 1, 2)

**Every node is a polygon vertex.** A digitized shape carries, in the Studio
only:

    shapeOverrides[sid].nodes = {
      shell: [{ i, kind }, ...],          // ascending i; kind "smooth" | "corner"
      holes: [[{ i, kind }, ...], ...],   // one list per hole ring, same shape
    }

`i` indexes the ring the Studio shows for that shape: `boundary_override` when
present, else `outlineFull`; per hole `holes_override[k]` else `holesFull[k]`.
Nodes are NOT on the wire: `canonicalShapeEdits` never emits the key (a test
pins this; the request-contract fixture is unchanged). They live beside
`boundary_override` so they travel with it under the same shape id, are
covered by Reshape's `RESHAPE_KEYS` snapshot (Discard restores them), and
undo like any override.

**Validity.** A `nodes` entry is valid when every `i` is in range of its ring,
indices are strictly ascending, and each ring has at least 3 nodes. An
invalid entry is ignored and re-seeded on the next show (section 3). Any
writer of `boundary_override` / `holes_override` other than the node editor
(Simplify today; anything later) deletes `nodes` from that entry.

**Curve.** Between consecutive nodes runs a uniform Catmull-Rom cubic: as a
Bezier, the controls are `P_i + (P_{i+1} - P_{i-1}) / 6` leaving node i and
`P_{i+1} - (P_{i+2} - P_i) / 6` arriving at node i+1, each control offset
clamped to half its span's chord. A **corner** node's tangent on each side is
that side's chord, so a span between two corners is a straight line (a logo's
square stays a square) and a corner next to a smooth node leaves it straight
and arrives curved. A **smooth** node takes the central-difference tangent.
This is the model Ember uses for its own vectorized (photo) shapes; its
drawn-shape solver (spline-research) is out of scope (section 10).

**Spans.** A ring with N nodes has N spans; span k is the polygon's vertices
from node k to node k+1 inclusive, wrapping. A span's interior vertices are
either the original trace vertices (untouched) or a flattening of the curve
(rebuilt, section 5). Nothing records which: a span IS its vertices.

## 3. Seeding (ruling 4)

When a digitized shape is shown with no valid `nodes` (first selection, after
Simplify, after a re-digitize that changed the ring): closed-ring
Douglas-Peucker at **0.5 mm** over the current ring (the split-at-the-two-
farthest-vertices scheme `simplifyRing` already uses, returning kept INDICES
rather than points), every kept vertex becomes a node. A node is a **corner**
when the turn between its two chords (to the previous and next node) exceeds
**35 degrees**, else smooth. A ring with 3 or fewer vertices makes every vertex
a node. Seeding writes nothing: seeds live in component state until the first
node edit commits them, in the same patch as the polygon. Seeding is a pure
function of the ring, so re-deriving gives the same seeds.

Expected counts, to be measured in PR 1 and quoted in its body: red-disc's
64-point disc seeds roughly 8-16 smooth nodes and no corner; a traced square
seeds 4 corners; the 52 mm Instagram rounded square about 20.

## 4. Gestures (rulings 5, 6)

**One picture.** A selected digitized shape shows its NODES, in the quick
single-node drag outside Reshape mode and inside it. The dense vertices are
not drawn and not grabbable. Smooth nodes draw as the existing disc
(`NODE_R`), corner nodes as a square of the same size; colours and the
selected (filled white) state stay as they are.

- **Drag a node** (quick drag or Reshape, one or several selected): exact move
  (#1237), the two spans at each moved node rebuild live, commit per gesture
  as today (one `elupdate`, `discrete`), `nodes` re-indexed in the same entry.
- **Alt-drag**: the 11-04 soft pull on the polygon's vertices, unchanged, no
  rebuild; nodes ride along since they are indices.
- **Edge drag** (`moveEdge`): both end nodes take the delta, exact; their
  outer spans rebuild, the dragged span itself rebuilds too (both its ends
  moved).
- **Click the path** (Reshape mode; pointer-up within 3 px of pointer-down on
  an edge hit, `EDGE_GRAB_PX`): inserts a **corner** node at the pointer's
  projection onto the nearest polygon edge. The node is a new collinear
  polygon vertex; nodes after it re-index; one undo step; geometry is
  unchanged (area and perimeter equal within floating point). Outside the mode
  the existing double-click-an-edge insert stays and now inserts a corner node
  the same way. Ember: a click 4 px off the stroke inserts nothing; ours uses
  the 6 px edge grab.
- **Double-click a node** (wherever nodes show): toggles corner / smooth; its
  two spans rebuild; one undo step.
- **Delete / Backspace**: removes the selected nodes per ring; each merged
  span rebuilds; refuses at the 3-node floor with the existing wording and
  removes nothing on that ring.
- **Arrows**: nudge the selected nodes 0.1 mm, Shift 1 mm, exact; spans
  rebuild; one undo step per press.
- Marquee, Shift-click, right-click rows, strip, Done / Discard, Enter,
  Escape: as shipped on 11-03 / 11-04, now over nodes. "Select all points"
  selects all nodes.

## 5. Rebuild and commit (rulings 3, 7)

**Which spans rebuild.** A span rebuilds when one of its own two END nodes
moved (drag, edge drag, nudge), was toggled, or is the merged span of a
delete. An insert alone rebuilds nothing. A moved node also changes the
tangent at its neighbours, which would change the spans beyond them; those
spans are NOT rebuilt and keep their vertices. The join at an untouched node
is C0 (the curve passes through every node); the small tangent kink at that
join is accepted (Kent, Q3).

**How.** The span's curve is built from the CURRENT node positions and kinds
(its two ends and their outer neighbours for tangents), then flattened by
adaptive subdivision to vertices with **chord error at most 0.05 mm** and
**spacing between 0.3 and 1.0 mm** (split while the error is over 0.05 mm or
the spacing over 1.0 mm, never below 0.3 mm). Fill rows are 0.4 mm apart;
0.05 mm is invisible. The span's old interior vertices are replaced; its end
nodes stay.

**The 500-point cap.** If a ring would exceed `BOUNDARY_MAX_POINTS` (500)
after a rebuild, the rebuilt spans alone are re-flattened with both spacing
bounds doubled (0.6-2.0, then 1.2-4.0 mm) until the ring fits. Original
spans are never thinned. (The original spans are a subset of a ring that
already fit, so the loop terminates.)

**Commit.** The same path as today: `commitRingEdits` builds one
`boundary_override` (and `holes_override` when a hole ring changed) per
touched shape plus the re-indexed `nodes`, one `elupdate` with `discrete`;
`boundaryIssues` runs per ring before the patch and a refusal snaps the
gesture back and names the ring. Restitch follows the commit as it does for
every override today; Done ends the session (#1237), it does not batch
commits.

**Invariants, each a test:**

- I1 enter Reshape and Done without an edit: no patch, no `nodes` written.
- I2 one node moved: every vertex outside its two spans is byte-identical
  (deep-equal) before and after; the node itself moved by the delta.
- I3 every node is a vertex: `ring[nodes[k].i]` is the node's position.
- I4 `nodes` never reaches the wire (`canonicalShapeEdits`, request-contract
  fixture).
- I5 a span between two corner nodes flattens to its chord: a traced square
  with a dragged corner is a quadrilateral with 4 vertices.
- I6 insert leaves area and perimeter unchanged and adds exactly one vertex.
- I7 the ring never exceeds 500 after any rebuild; original spans are
  untouched by the cap loop.

## 6. Simplify, holes, re-digitize

- **Simplify** rewrites the polygon and deletes `nodes`; the next show
  re-seeds. `Points: N -> M` keeps counting polygon vertices.
- **Holes**: the same model per hole ring (`nodes.holes[k]`); a rebuild on a
  hole ring writes `holes_override` under the 11-03 ruling 3 rules
  (exterior-only edits still emit no `holes_override`).
- **Re-digitize**: `boundary_override` and `nodes` carry over by shape id as
  overrides do today; if the ring changed under them the validity check
  (section 2) drops `nodes` and re-seeds.

## 7. Tests

**PR 1, unit (vitest, `app/test/sparseNodes.spec.js`)** against synthetic
rings (a 64-point circle, a 4- and 8-point square, a 52 mm rounded square at
~5 mm spacing, a 500-point ring):

- seeding: circle -> 8..16 nodes all smooth; square -> 4 corners; rounded
  square -> corners only where the turn is over 35 degrees; every seed is an
  index into the ring; a 3-vertex ring seeds 3; seeding is deterministic.
- curve: passes through every node; corner-corner span is its chord;
  controls clamped at half chord on a very uneven spacing.
- flatten: every flattened vertex within 0.05 mm of the curve, spacing within
  0.3-1.0 mm, ends are the nodes.
- rebuild: I2 (deep-equal outside the two spans), toggle rebuilds exactly two
  spans, delete rebuilds the merged span and refuses at 3 nodes, insert I6
  and re-indexes the later nodes.
- cap: a 500-point ring with one rebuilt span stays at or under 500 with the
  original spans deep-equal (I7).
- validator: out-of-range, unsorted, duplicate and under-3 entries rejected.
- `digitizer.spec.js`: `canonicalShapeEdits` ignores `nodes` (I4), fixture
  unchanged.

**PR 2, Studio.** vitest: node drawing picks disc / square by kind; Simplify
deletes `nodes`; `RESHAPE_KEYS` snapshot restores `nodes` on Discard.
e2e (Playwright, real service, `app/e2e/field-reshape-mode.spec.js`):

- (s1) red-disc: select, node count (a `data-reshape-nodes` attribute) at or
  under 16; drag one node 3 mm outward; `boundary_override` deep-equals the
  original outside the two spans, restitch happens. Render before / after
  (the picture rule, CLAUDE.md footgun 1).
- (s2) two-squares: 4 corner nodes; drag a corner -> 4-vertex quadrilateral
  (I5; replaces (a)'s "same point count"); Edit points, click the top edge's
  midpoint -> 5 nodes, `boundary_override` has one more vertex, area equal
  (I6); double-click the new node -> smooth, its two spans now carry
  flattened vertices; Delete it -> 4 nodes; Discard -> original.
- (s3) the holed fixture: a hole's node drags, `holes_override` differs only
  within two spans, shell untouched (adapts (e)); (e2)-(e4) adapted to nodes.
- (s4) enter Reshape, Done -> no override at all (I1).
- (b), (c), (d), (f), (g), (h), (i) adapted to nodes where they counted
  vertices; (g) the hand-drawn case is unchanged.

## 8. Build order (ruling 9)

Two PRs, each a Sonnet brief, own worktree, ready-for-review with auto-merge
armed while `mergeable_state` is `blocked`; merging is Kent's.

1. **Lib**: `app/src/lib/sparseNodes.js` — `seedNodes`, `isValidNodes`,
   `spanCurve`, `flattenSpan`, `rebuildSpans`, `insertNodeOnPath`,
   `toggleNode`, `deleteNodes`, `capRing`, constants `SEED_TOL_MM = 0.5`,
   `CORNER_DEG = 35`, `FLATTEN_ERR_MM = 0.05`, `FLATTEN_MIN_MM = 0.3`,
   `FLATTEN_MAX_MM = 1.0` — pure, ring-agnostic (shell and hole alike), no
   Svelte. Its spec file, the `canonicalShapeEdits` test, this document and
   its memory note. About a day.
2. **Studio** (after PR 1 merges): drawing, quick drag and Reshape on the node
   model, persistence in `shapeOverrides[sid].nodes`, insert / toggle /
   delete gestures, Simplify deletes nodes, the e2e above, DOCTRINE line,
   MASTER_SCOPE / `docs/scope/` update. Two days.

A third item, ruled the same evening and NOT part of this spec: **add-hole**
(draw a polygon inside a digitized shape, it is appended to `holes_override`),
Studio only, after PR 2. Knife (split one shape into two) stays a non-goal;
both are recorded in `PRODUCT.md`.

## 9. Rulings — nine closed in the grilling, 2026-11-04

1. **Nodes live Studio-side** in `shapeOverrides[sid].nodes`; Done flattens
   to the polygon the service already takes. Over derive-every-time (nodes
   jump between sessions) and over a new wire key (a Python flattener that
   must match the preview).
2. **Catmull-Rom through the nodes**, corner = tangent break. Over the
   spline-research solver (global re-solve fights the local rule) and over
   reusing the hand-drawn quadratics (cannot stay smooth through a node).
3. **Untouched spans keep their original vertices**; only a span whose end
   node changed is rebuilt. Over whole-ring re-flatten (always, or after the
   first edit).
4. **Seed by Douglas-Peucker 0.5 mm, corner over 35 degrees.** Over
   curve-aware refinement and over all-smooth.
5. **Sparse nodes everywhere**, the dense view is gone; a vertex between
   nodes is reached by inserting a node there. Over mode-only sparse and over
   a "show all points" tick.
6. **Insert is free (a corner on the outline, nothing moves); toggle and
   delete rebuild.** Over inserting smooth and over Ember-literal rebuild on
   insert.
7. **Flatten at 0.05 mm chord error, 0.3-1.0 mm spacing; over 500 points,
   coarsen the rebuilt spans only.** Over fixed spacing with whole-ring
   thinning and over refusing the commit.
8. **Digitized rings only**; the hand-drawn lane keeps anchors + handles.
   Over adding the two gestures there and over moving it onto this model.
9. **Two PRs, lib then Studio.** Over one PR and over three.

Scope ruling the same evening, outside this spec: **add-hole in, Knife out.**

## 10. Out of scope, named

- The spline-research solver, or any curvature-continuous re-solve of the
  whole ring.
- Nodes on the wire; the service keeps taking polygons (contract v1.9).
- The hand-drawn lane (ruling 8) and its curve handles.
- Knife (split a shape along a drawn path): non-goal, Kent 2026-11-04.
- Add-hole: in scope, its own PR after PR 2, not in this spec.
- Seeding density that follows zoom, or automatic re-seeding on an edit.
- Snapping an inserted or dragged node to another shape's edge.
- Cap pieces (`isCapPieceId`) and group-highlighted similar shapes: unchanged.
