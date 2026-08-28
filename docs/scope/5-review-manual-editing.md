# Area 5 — Stitch-out review & manual editing tools

**Part of [`MASTER_SCOPE.md`](../../MASTER_SCOPE.md)** — this is the detail
for one capability area. The live one-line verdict (Status / Confidence /
what is next) is in MASTER_SCOPE; this file is the supporting record.

**Claim discipline:** a claim here should carry a `(verb date — source)`
pointer — `confirmed` = checked against code or a passing test, `measured` =
a number was produced, `suspected` = neither. Much of this file predates that
rule and is **not yet annotated**; anything unannotated is unverified until
someone checks it. Test counts, stitch counts and corpus grades written here
were snapshots when written — do not quote one as a current baseline.
Dated narrative belongs in [`../scope-history.md`](../scope-history.md).

---

The professional-quality refinement toolkit: can a user take auto-digitized
output and manually fix/improve it — delete, recolor, re-tier, adjust angle,
reorder layers — distinct from whether auto-digitizing itself is good
(area 1) or whether the wizard is easy to navigate (area 3).

**Status:** Implemented, narrow scope. Landed 2026-08-02 in two same-day
commits: the review-screen shape-edit plumbing (`c390e9f`) and the Studio
Layers panel UI (`ce8f021`).

**Confidence: High** — unusually, both the wire-protocol plumbing *and* the
user-facing UI are confirmed with matching evidence (not "backend exists, no
UI" or vice versa). The service round-trips `deleted_shape_ids` and
per-shape `shape_overrides` (recolor, tier, fill angle, border, sew layer);
`DigitizePanel.svelte`'s Layers list exposes recolor, tier, fill-angle,
reorder, delete/restore. The landing commit reports live-browser
measurements against the real service confirming all of the above plus
undo/redo and offline-queued edits.

Since this section was last written, the Layers panel gained one more
control of this same kind — restoring a `BACKGROUND_ENCLOSED`-excluded
shape (merged, PR #10) — described under area 1 above rather than
duplicated here, per this doc's own "documented once" convention for
cross-cutting features.

#### Kent's direct-manipulation request (2026-08-12) — the target shape of this area

Captured verbatim from Kent's annotations on an owl-photo digitize, because
the sub-requirements *are* the spec and a summary loses them. This is a
**product direction for this area, not a defect list.** It supersedes the
current Layers-panel-only model as the destination; it does not invalidate
what shipped.

The red annotation: **remove `+ Shape` and `+ Draw shapes`.** They are to be
replaced by the behaviour below, not supplemented by it. **RESOLVED
2026-08-13 (PR #138), with a same-day amendment from Kent: not removed but
RELOCATED** — "instead of dropping it completely, let's make drawing shapes a
tool that opens up with a right click." Both now live in a right-click menu
on the design canvas (`EmbroideryField`'s `.fieldmenu`); the Content step's
tile row is down to **Text · Artwork · Design file**, where `+ Artwork` is
the merged upload path replacing `+ Image` and `+ Auto-digitize` (routes on
service health in `App.onAddElement`: service up → digitized element, down →
the browser flatten lane). Element types, panels and tests for shapes/manual
drawing are untouched — only the way in moved.

The blue annotation, on how `+ Image` / auto-digitizing should behave:

> Instead of having the +Shape and +Shape & Draw, i would like the +Image
> (the autodigitizing to act in the following manner)
> - Upload Image
> - Auto Digitize
> - Populate Lines around the recognized shapes with nodes [Let's have them
>   "pulse" for the first few seconds]
> - These lines and nodes capture the recognized digitized shape/feature
> - I want the ability to manually move the nodes or lines to manually edit
>   the auto digitized shape/feature (add nodes, move lines, or even select
>   the ENTIRE shape and drag it around wherever i please (or even delete it
>   if possible. (each outline shape/feature should be treated like it's own
>   entity

Broken out, each is independently testable:

1. Every recognized shape gets a visible outline with visible nodes, drawn
   over the result automatically after digitizing.
2. Those outlines **pulse for the first few seconds** — an attention cue that
   the app found these shapes, not a permanent decoration.
3. The outline is the *shape's own boundary*, not a bounding box — it
   "captures the recognized digitized shape/feature".
4. Nodes are draggable. Lines are draggable. Nodes can be **added**.
5. ~~A whole shape can be selected and dragged anywhere.~~ **WITHDRAWN by
   Kent same-day — see the ruling below. Kept numbered so 6 and 7 keep their
   references.**
6. A whole shape can be deleted.
7. **Each outline shape/feature is its own entity** — the organizing
   principle behind all of the above.

**What already exists toward this** (more than it looks): shapes carry
stable `shape_id`s; the shape-layers contract v1 (`deleted_shape_ids`,
`shape_overrides`) and v1.5 (`merge_shape_ids`, `split_shapes`) are
round-tripped by the service and spoken by the Studio; `Icon.svelte:119`
already reserves a per-shape "edit this shape's boundary" ✎ affordance.

**The gap — corrected 2026-08-12, this paragraph used to be wrong.** It read
"nothing today can move a node or a line," citing the *boundary-reshape gap*
in `stage2_photo_segment.py` / `warnings_codes.py`'s v1.5 comments. That
contradicted this same document's own "**Boundary reshaping — CLOSED
2026-08-05**" entry a few screens below, and the CLOSED entry is the correct
one: contract **v1.4's `boundary_override`** ships end to end — service
validation, `regions.apply_shape_edits`, carry-forward on `assign_shape_ids`'
stable content-derived id (**not** via `match_shape_ids`, which is unwired — see
the `shape_id` allocation entry below), and a working editor in `DigitizePanel.svelte`
(`startBoundaryEdit`/`saveBoundaryEdit`: drag a vertex, click an edge
midpoint to add one, right-click to remove). Node-level editing needs **no**
new contract work.

What was actually missing is *where and when*: that editor works on ONE
shape at a time, on a small SVG of its own, reachable only by finding a row
in the Layers panel and clicking a pencil. Nothing drew a shape on the
design canvas at all.

Status against Kent's list, re-measured against the code 2026-08-13:

| req | | state |
|---|---|---|
| 1 | outlines + nodes, automatic after digitize | **shipped** — canvas overlay, `lib/shapeOverlay.js` |
| 2 | pulse for the first few seconds | **shipped** — fires on a NEW result, not on load |
| 3 | the shape's own boundary, not a bbox | shipped (`outlineFull`, contract v1.4) |
| 4 | drag nodes / add nodes | **shipped on the canvas** (PR #130) — and the drag now moves stitches, see below |
| 4b | drag **lines** | **shipped on the canvas** (PR #130) |
| 6 | delete a whole shape | built (`deleted_shape_ids`) — canvas Delete key too |
| 7 | each shape its own entity | built (`shape_id`) |

The rows for 4 and 4b said "not yet on the canvas" until this pass; they have
been on the canvas since PR #130 (2026-08-12) and the stitches restitch on
their own since PR #134 (2026-08-13). What was still missing was neither of
those — see immediately below.

**A node drag now moves the STITCHES, not just the outline — 2026-08-13.**
Kent, testing the canvas editor on his owl: *"i can move the nodes, but the
stitch fill in fill STILL isn't working."* Nothing in the edit path was
broken. The **vertex density of an auto-traced outline** was:
`owl_kent.jpg`'s body region carries **346 vertices around a 458 mm
perimeter — one node every 1.3 mm**, so dragging one moved 2.6 mm of
boundary and added a needle. Measured against the real pipeline: a 6 mm
single-vertex pull grew the polygon by exactly the 7 mm² it asked for and
put **0 stitches** in the added area. Every layer downstream did its job;
the geometry it was given was too thin for a fill row to occupy, while the
overlay drew a large, obvious spike over unchanged stitching.

- **Why it hid.** On line art the same code was always right:
  `two-squares.png`'s shapes are 4-vertex squares with 25 mm sides, so one
  vertex owns a quarter of the shape. A corner drag there restitched
  correctly (2,153 → 3,107 stitches) both before and after this fix — the
  browser run is byte-identical, because the pull radius never reaches a
  neighbour that far away.
- **The fix** (`shapeOverlay.js`, `pullRing`): a drag carries the
  neighbouring boundary with it, weighted by **arc length** (never vertex
  index — one index step is 1.3 mm on a photo outline and 25 mm on a traced
  square), falling off on a raised cosine over a radius of **2× the drag
  distance**, floored at 3 mm and capped at a quarter of the ring's
  perimeter. Radius swept against the pipeline at a 6 mm pull on the owl:
  1× → 11 stitches in the new area, **2× → 31**, 3× → 27 (wider but
  shallower starts losing rows again).
- **The cap is what keeps requirement 5 out of scope.** Without it a large
  pull on a small shape reaches every vertex and the shape *translates* —
  which changes its centroid, which changes its `shape_id`, which is what
  makes edits survive a re-digitize. Pinned by a test that drags a node
  500 mm and asserts the far side of the ring has not moved at all.
- **Confirmed in a real browser on the real service**, not just in
  measurement: the same owl drag that produced an empty spike now fills the
  bulge it makes (7,698 → 7,810 stitches, and the stitching visibly reaches
  the dragged outline).
- **Sharp edge found on the way, NOT fixed (recorded so it isn't rediscovered
  as a mystery):** `boundary_override` carries only a shape's EXTERIOR ring,
  and `apply_shape_edits` re-attaches that shape's original holes to it. A
  shape with holes therefore rejects any edit that pulls the shell across one
  — `ValueError: ... Hole lies outside shell ...`, a 400, and the restitch
  fails rather than degrading. On the owl exactly one region has holes (the
  body, 10 of them) and it is also the largest and most tempting to edit, so
  this is reachable. It is not silent — `DigitizePanel` renders the message
  (`.dgp-error`, `role="alert"`) — and the wider pull radius makes it a bit
  easier to reach than a single-vertex drag did. Fixing it properly means
  deciding what a hole *means* under a hand edit (drop it? clip it? move it
  with the shell?), which is a product call, not a bug fix.
- **The restitch is DEBOUNCED at 2s idle, and that number has a reason.**
  When this was written, a restitch was a full stage 0-7 service run with no
  useful cache — `jobs.content_key` folds `shape_overrides` into the config,
  so every geometry edit was a guaranteed miss. Measured 0.65s on line art,
  ~10s on a real photograph. Firing per drag would queue a 10s run behind
  every nudge; waiting for the user to stop means ten adjustments cost one
  run. **The full-rerun half of that reasoning is closed by the stage 0-4
  cache below (2026-08-22); the debounce itself stays — even the cached
  finish + re-plan is seconds on a photo, not per-keystroke cheap.**
- **Where the 10 seconds actually goes — measured 2026-08-13, and it decides
  whether a cache is worth funding** (Kent asked for the number first):

  | fixture | stages 0-4 (cacheable across a boundary edit) | stages 5-7 (must re-run) |
  |---|---|---|
  | `owl_kent.jpg` | 7.58s (53%) | **6.63s (47%)** |
  | `photo/enthusiast_logo.png` | 5.92s (81%) | **1.38s (19%)** |
  | `asym_source.png` | 0.30s | 0.35s |

  So caching stages 0-4 and re-running only `plan_stitches` would take LOGO
  art from ~7.3s to ~1.4s, but a real photo only from ~14s to ~6.6s — nearly
  half a photo's cost is stitch planning, which a boundary edit invalidates
  by definition. **Worth building for logo work; not a route to "instant" on
  photos.** (Absolute figures were taken under heavy machine load — the
  RATIO is the finding, not the wall-clock.)
  **BUILT 2026-08-22 — Kent funded it in that session's workload answer.**
  The split lands exactly at the seam the table predicted: `pipeline.
  build_generation` (stages 0-4, edit-independent — verified none of it
  reads the four review-edit keys) / `pipeline.finish_generation` (edits +
  palette), with `run_stages` recomposed so every other caller is untouched.
  The service (`digitizer_service.jobs.GenerationCache`, LRU of 4) keys
  generations on sha256(image) + config-minus-edit-keys and finishes every
  request from a `Generation.fork()` — Region objects are mutated in place
  by `apply_shape_edits`, so the fork (fresh Region/meta, shared immutable
  polygons and rasters) is what keeps the cached original pristine; the
  cold path forks too, since its generation goes into the cache. The
  property the tests pin, rather than a speedup number: **a cache-served
  edit is byte-for-byte the design a cold run of the same request
  produces** (core: `tests/test_generation_cache.py`; wire:
  `test_service.py`'s generation-cache round trips, including a
  fork-isolation case that runs two different edits off one generation).
  Jobs report `generation_cache: "hit"/"miss"` so the loop is observable.
  Measured over the service wire, idle cloud container: an edited
  `enthusiast_logo.png` re-run **3.59s → 0.99s (3.6x)**, an edited
  `owl_kent.jpg` re-run **12.10s → 7.11s (1.7x)** — the table's own
  logo-big/photo-modest shape, at slightly less than its predicted ratios
  because `finish_generation` (edits + palette + fork) now rides the paid
  tail. *(measured 2026-08-22 — `digitizer/tools/perf_stage_cache.py`,
  cold vs hit vs cache-cleared cold-edit over TestClient)*
- **OPEN: the restitch trigger only exists on the Content step.**
  `EmbroideryField` mounts on every step (`App.svelte`, outside the step
  conditional); `DigitizePanel`, which owns `runDigitize`, mounts only on
  `step === "content"`. A shape edited from Review/Create/Download saves and
  hatches as stale but does not restitch until the user returns to Content.
  Fixing it means lifting the digitize runner into `App.svelte` — a real
  refactor of a well-tested path, deliberately not done as a rider.
- **Deliberately NOT changed: `DigitizePanel`'s per-shape ✎ boundary
  editor**, which still moves exactly one vertex. It is the precision tool —
  one shape, alone, on its own magnified SVG, with vertex delete and
  keyboard nudge — and one-vertex semantics are the right ones there. The
  canvas is the direct-manipulation surface and the one Kent reported. Both
  still write the same `boundary_override` key, so nothing downstream can
  tell them apart.

**Kent ruled, 2026-08-12 — requirement 5 (dragging a whole shape) is OUT OF
SCOPE.** He first asked for it ("moved or dragged around, similar to how
clipart would work"), then withdrew it the same day once the cost surfaced.
Both halves are recorded because the reasoning is the useful part:

`regions._raw_id` derives every `shape_id` by bucketing **centroid + thread
number**. Moving a shape changes its centroid, which changes its id — and id
stability is exactly what the "sticky, ride every future re-digitize" edit
model depends on (`digitizer.js`'s comment on `deleted_shape_ids`). Free
translation and durable edits are in direct tension; dropping translation
resolves it without inventing a new identity scheme.

**What survives is requirements 1-4, 6 and 7:** outlines with visible nodes,
the pulse cue, node/line dragging, adding nodes, deleting a shape, and each
shape being its own entity. Reshaping a boundary still perturbs a centroid,
so the design must still show that edits survive a re-digitize — but the
perturbation is now bounded by `CENTROID_BUCKET_MM` rather than unbounded,
which is a far easier property to hold.

**Recommended posture — superseded 2026-08-12.** This used to call for a
written design before any code, answering (a) how node-level geometry is
represented — new contract version vs. an extension of v1.5's replayable
operation list. That question was already answered before it was asked:
`boundary_override` (v1.4) represents it, and has since 2026-08-05. Point
(b), the bounded-centroid-drift argument, still wants a worked case before
hand edits are *promised* to survive a re-digitize — but it does not block
building the canvas editing surface, which is now the actual remaining
work.

#### Note 6, from the same session — the render Kent marked "portions of the owl that shouldn't have been removed"

Partly answered, and it is **not** a deletion bug: segmentation found the
bird correctly (27 regions, clean silhouette). The body read as a flat mass
because region fill averages away the structure a photo carries in its
edges — the `detail_layer` finding in the top-of-file entry. Two genuinely
dropped shapes (`DROPPED_SMALL_SHAPES`) and two absorbed
(`ABSORBED_SMALL_SHAPES`) remain as a smaller, separate question about
threshold aggressiveness on pale subjects.

**Open issues:** of the five gaps the landing commit self-flagged, **four are
now closed** (all merged 2026-08-04, all confirmed against source this
pass — `digitizer_service/app.py`'s `_OVERRIDE_KEYS` now reads
`{thread_index, fill_angle_deg, tier, border, layer, sew_order, stitched,
underlay_style}`):
- ~~Per-shape border override is engine-supported but has no UI
  control.~~ **Closed, PR #21** — a Border select per Layers row.
- ~~The "stale/unmatched edit" recovery flow was never driven in a live
  browser.~~ **Closed, PR #21** — `app/e2e/digitize-stale-edits.spec.js`
  drives the real digitizer service through the real `DigitizePanel` in a
  real browser (Playwright), forces an edit stale via a width change, and
  asserts the unmatched-edit notice, clear, and re-apply all work.
- ~~Within-layer sew order is shown, not controllable.~~ **Closed, PR
  #26** — a `sew_order` shape-override key plus a second ▲/▼ control per
  Layers row for shapes sharing one color layer.
- ~~Backstitch/underlay adjustment is entirely engine-internal.~~
  **Closed, PR #28** — the fill/contour underlay-style knob
  (`PipelineConfig.underlay_style`, seven named styles) is now a per-shape
  override, following the border/tier/fill_angle_deg pattern exactly:
  validated at the service, applied in `regions.apply_shape_edits`, carried
  across re-digitize on the stable id `assign_shape_ids` re-derives, resolved per-shape in
  `stage7_sequence.sequence` ahead of both the tatami and contour emitters,
  and a Layers-panel dropdown next to the fill-angle control (shown only
  when a shape's tier is "fill", since satin ignores it). Deliberately does
  NOT touch satin's own underlay (`fabric.satin_underlay`) — a materially
  narrower, effectively-binary knob (spine run, or zigzag above
  `machine.SATIN_ZIGZAG_ABOVE_MM`) versus fill's seven styles, so it stays
  engine-internal on purpose. Backed by Python tests asserting the override
  actually changes emitted underlay stitch geometry (not just a config
  round-trip) and Studio vitest coverage of the wire contract. **The
  Layers-panel dropdown itself now has automated coverage too — CLOSED
  2026-08-07**, alongside tier/border/fill-angle and every other per-shape
  control: `DigitizePanel.testHarness.svelte` + `DigitizePanel.spec.js`
  (this doc's own top "Last updated" entry has the full writeup). No
  svelte-component test harness for this file existed anywhere in the
  repo before that pass.

**Boundary reshaping — CLOSED 2026-08-05** (worktree `agent-
a28de220d2af7ede5`, commits `298eae0` digitizer / `ac11163` studio): the
"no reshaping/redrawing outlines... no manual point editing" half of the
one gap above is closed, following the override-pattern playbook exactly —
new contract key, service validation, core application + carry-forward,
Layers-panel control, tests at every layer.

- **Contract key: `boundary_override`** (shape_overrides, v1.4) — a list of
  `[x, y]` mm points (design-center origin, y-down, the same space
  `outline_mm` already reports) replacing a shape's EXTERIOR ring only;
  holes ride forward unchanged from the shape's current geometry.
  `digitizer_service/app.py`'s `_canonicalize_shape_edits` validates point
  count (3..500, mirrored in `digitizer_core.regions`'s own copy),
  finiteness, and — the shell alone, since a request never carries the
  shape's holes — polygon validity plus the same sewability floor stage 4's
  own run-tier rescue already holds auto-digitized regions to
  (`machine.RUN_MIN_AREA_MM2` / `RUN_MIN_LOOP_MM`): a fast 400 on a
  self-intersecting drag or a pinched-shut shape. `digitizer_core/
  regions.py::apply_shape_edits` re-validates independently (defense in
  depth, same posture as every other key here) and ALSO checks hole
  containment against the shape's real polygon — the one check that can
  only run there. A rejected edit is always a clean `ValueError` (a 400 at
  submit, or a job-level error for the hole-containment case specifically,
  since that one needs the shape's real geometry to catch) — never a crash,
  never silently repaired geometry. `area_mm2` is recomputed on a
  successful edit; the key was added to `match_shape_ids`' carry-forward
  list alongside `border`/`tier`/`fill_angle_deg`/`sew_order`/
  `underlay_style` (that list is real, but the function is not wired — see the
  `shape_id` allocation entry below; production carry-forward is id stability).
- **Studio UI:** `DigitizePanel.svelte` gained an "Edit shape boundary" (✎)
  control per Layers row (shown wherever the other per-shape controls
  already are — not for hidden or not-sewn rows). It opens a small SVG
  editor in place of the layer list: draggable vertex handles, small
  midpoint dots that add a vertex on click/Enter, right-click or Delete to
  remove one (floor of 3, matching the server), arrow keys to nudge a
  focused point. `digitizer.js` gained the client-side mirror of the
  server's geometry checks (`boundaryIssues`/`ringArea`/`dedupeRing`) so an
  invalid shape shows its problem and disables Save immediately, before a
  wire round trip — the server stays the actual authority. `reviewFromJob`
  gained `outlineFull` (deduped, capped at the server's own 500-point
  ceiling) distinct from the thumbnail's hard-decimated `outline`, so
  opening the editor never silently reshapes a shape before a single drag
  happens. Save merges the result into `shapeOverrides` via the existing
  `setOverride` call — the identical "Apply layer changes" flow every
  other override here already uses; no new save/apply path.
- **Verification:** `digitizer/tests/test_shape_overrides.py` (core-level:
  valid reshape + recomputed area, hole preservation, an awkward-but-valid
  hand edit run through real stage5/stage7 with no degenerate stitches,
  rejection of a bowtie/sliver/too-few-points with a clear error, dedup of
  a closed ring, carry-forward via `match_shape_ids`, a stateless
  re-digitize round trip proving the override survives on the SAME stable
  id) and `digitizer/tests/test_service.py` (HTTP-level: the round trip,
  cache-key participation, bad-geometry 400s, and the one check that can
  only fail at job-run time — a shrunk shell that pokes a real hole
  outside it). Studio: `digitizer.spec.js` unit coverage for the new pure
  helpers and wire contract, plus a new Playwright e2e spec
  (`app/e2e/digitize-boundary-edit.spec.js`) driving the real digitizer
  service end to end. Also manually verified live via Playwright MCP
  against the real service — drag-to-move, click-to-add, right-click-to-
  remove, and the invalid-shape (self-intersecting) rejection path all
  confirmed working, screenshotted.

**Shape splitting and merging — CLOSED 2026-08-05** (worktree
`agent-a095c5eea8b6320fb`, branch `shape-split-merge`): the "other half of
the original shape-recognition gap" this doc tracked as fully open is now
built, following the same override-pattern playbook `boundary_override`
established — new contract keys, service validation, core application, a
Layers-panel control, tests at every layer — with one structural difference
called out up front because it drives every design choice below: merge and
split change the SET of shapes, not one shape's geometry, so neither rides
`shape_overrides` (which is keyed to ONE existing shape_id that survives the
edit) — both are new top-level config keys, siblings of `deleted_shape_ids`.

- **Contract keys (v1.5): `merge_shape_ids` / `split_shapes`.**
  `merge_shape_ids: [[shape_id, shape_id, ...], ...]` — each inner list at
  least 2 distinct ids to union into one new shape. `split_shapes:
  {shape_id: [[x0,y0],[x1,y1]]}` — a straight cut line (extended internally
  past the shape's own bounding box, so the caller sends only the two
  dragged endpoints) dividing one shape into exactly two. Both are validated
  service-side for shape/type (`digitizer_service/app.py`'s
  `_canonicalize_shape_edits`, mirrored bounds in
  `digitizer_core.regions`'s own copy) and re-validated independently at the
  core layer (`regions.apply_shape_merges` / `apply_shape_splits`, called
  from `pipeline.run_stages` BEFORE `apply_shape_edits` — ids are minted
  against the full stage-4 generation before deletions/overrides consume
  any of them, the same ordering reasoning `apply_shape_edits` already
  documents for itself). A stale/unknown id is a warning and that one
  merge/split is skipped (`SHAPE_EDIT_UNKNOWN_ID`, same posture
  `deleted_shape_ids` already has); a geometrically bad request (mixed
  threads, a present hole, a non-adjacent merge, a line that doesn't cross
  cleanly or crosses a hole, a piece under the sewability floor) is a clean
  `ValueError` — a 400 at submit for what the service can shallow-check, a
  failed job for what only the core's real Region geometry can (mirroring
  `boundary_override`'s own hole-containment asymmetry exactly).
- **`shape_id` allocation: brand new, deterministic ids hashed from the
  OPERATION's own inputs, never geometry.** Confirmed before relying on it:
  `match_shape_ids` is not wired into `pipeline.run_stages` at all today —
  it exists for a segmenter (SAM2, built and gated behind
  `cfg.photo_segment_sam2`, default `False` — see the auto-digitizing
  capability entry above) that would move centroids/areas
  slightly on a re-digitize of the SAME image, a different problem from a
  user *deliberately* replacing a shape's identity. So merge/split mint new
  ids instead of trying to carry one forward: `_merge_shape_id` hashes the
  sorted source ids ("SM" + blake2s), `_split_shape_id` hashes the source id
  + the cut line's own (canonicalized-order) endpoints + which of the two
  pieces ("SP" + blake2s, piece order fixed by centroid, never shapely's
  internal `split()` ordering). Both prefixes can never collide with an
  `assign_shape_ids` output (always `"S" + hex`). Being pure functions of
  the request rather than geometry means an identical resubmit is one
  stable cache key/one stable pair of new ids, and — as a documented but
  not yet UI-wired bonus — a caller that computes the same hash could layer
  a `shape_overrides` entry onto a shape a merge/split mints in the SAME
  request; the shipped Studio UI does not do this, it always waits for the
  fresh review payload before adding further overrides (two-step, not
  one-shot).
- **v1 scope, deliberately narrow — the honest trade-offs, not silently
  missing:**
  - **Merge requires the union to reduce to ONE polygon** (source shapes
    must already touch or overlap) — a hard architectural fact, not a
    style choice: `Region.polygon` is a single `shapely.Polygon` everywhere
    in stages 5-7, so a merge that can't produce one polygon has no legal
    result. **Worth stating plainly:** stage 3's connected-component
    labeling (`connectivity=8`) already fuses any two genuinely-touching
    same-color regions into one shape_id before assign_shape_ids ever
    runs, so in practice this restricts merge's usefulness on the flat/
    gradient lanes to shapes a SLIC/RAG photo-segment pass left adjacent
    but unmerged, or a future hand-authored/manual-digitizing workflow —
    not "any two same-color shapes a user points at," which would need a
    bridging/convex-hull strategy this pass does not build. Documented as
    a real, known narrowing, not glossed over.
  - **Merge requires every source shape to share one thread_number** (no
    cross-color merge — which color would the result take? a real product
    question, deferred) **and none of them may have a hole** (shapely's own
    union handles holes correctly; the deferral is which shape's hole
    semantics should win when two different shapes' holes overlap or one
    sits over the other's fill — genuinely ambiguous, sidestepped for v1
    rather than guessed at).
  - **Split is a single straight cut line, not an arbitrary polyline** —
    extended internally so the caller need only send the two dragged
    endpoints, producing exactly two pieces. A cut crossing one of the
    shape's own holes is rejected rather than silently turning the hole
    into a notch on both halves (shapely itself handles this case without
    erroring, so the rejection is a deliberate product choice, verified
    against real shapely behavior before writing the guard, not a
    limitation of the library).
  - Per-shape styling (`border`/`tier`/`fill_angle_deg`/`sew_order`/
    `underlay_style`) is seeded onto the result from the largest source
    shape (merge) or onto BOTH new pieces (split); `boundary_override` is
    never carried forward either way — it describes a hand-edited shell for
    a polygon that no longer exists once the identity changes.
- **Studio UI (`DigitizePanel.svelte`):** a merge-selection checkbox per
  Layers row (stitched, non-hidden shapes only) plus a "Merge N shapes" bar
  that live-validates the selection (`digitizer.js`'s `mergeGroupIssues` —
  at least 2 shapes, one thread) and disables the button until it passes; a
  "Split shape" (✂) control opening a small SVG editor sharing the boundary
  editor's scaffolding — a draggable 2-point cut line (defaulting to a
  horizontal line through the shape's own centroid, already valid for a
  convex shape) with live validation (`splitLineIssues`, counting crossings
  against the shape's own outline) disabling Save until the line crosses
  cleanly. Both save through the SAME `setOverride`-adjacent →
  `mergeGroups`/`splitLines` element fields → "Apply layer changes" flow
  every other override here uses; `canonicalShapeEdits`/`editsKey` fold both
  new fields into the existing pending-edit diff, so no new Apply-button
  wiring was needed. A merged/split result row's provenance (and its
  Undo-merge/Undo-split action) is read off the LAST APPLIED job's own
  `SHAPES_MERGED_BY_USER`/`SHAPE_SPLIT_BY_USER` warnings — the server
  already computed which source ids produced which result id, so the
  client never re-derives the hash.
- **Verification:** core-level (`digitizer/tests/test_shape_identity.py`,
  24 tests — the merge/split happy paths on synthetic adjacent Regions, every
  v1 guardrail as a real `ValueError`, the warn-vs-skip stale-id path, id
  determinism/stability regardless of argument or endpoint order, and two
  tests proving `cfg.merge_shape_ids`/`cfg.split_shapes` reach
  `apply_shape_merges`/`apply_shape_splits` from a REAL `digitize()` call
  against the same `logo_whitebg.png` fixture `test_shape_overrides.py`
  uses — the merge case using that fixture's own two real, non-adjacent
  "1305" regions to prove the adjacency guardrail fires on real geometry,
  not just synthetic squares) and service-level
  (`digitizer/tests/test_service.py` — parse/canonicalization including
  point/endpoint-order normalization for a stable cache key, 13 new bad-
  request 400 cases, the manual-digitizing field exclusion extended to both
  new keys, an HTTP round trip that actually cuts the fixture's real purple
  rectangle into two new shapes with the design's stitch count changing,
  and the merge-rejection round trip against the real orange pair). Studio:
  `digitizer.spec.js` gained unit coverage for the new canonicalization and
  the two pure validation helpers (7 tests); a new Playwright e2e spec
  (`app/e2e/digitize-shape-identity.spec.js`) drives the REAL digitizer
  service end to end for split (open the editor, save the default cut,
  Apply, confirm the one original row became two rows sharing its thread
  with a "split shape" badge and the design's stats changed, then Undo
  split restores the single shape) — **run live against the real service
  this pass, both tests green.**
  **One thing this pass deliberately did NOT verify live:** a full
  browser round trip of a SUCCESSFUL merge (select → Merge → Apply →
  one combined row). The reason is the same architectural fact above, not
  an oversight: `two-squares.png` (this repo's existing digitize-e2e
  fixture) has exactly two shapes, differently colored, so a live merge
  attempt on it can only ever demonstrate the SAME-COLOR validation
  rejecting a mixed selection (which the e2e spec does verify live,
  including the merge bar disabling itself) — not a genuine successful
  union, which needs two REAL same-thread, already-touching regions that,
  per the connected-component fact above, essentially never reach the
  review screen as two separate shapes in the first place. The successful-
  union code path itself is proven, just at the core level on synthetic
  Regions and the service level via the real-but-rejected orange pair, not
  through this particular browser harness.

**The underlay-style dropdown's live-browser check — CLOSED 2026-08-06.**
Verified live via Playwright MCP against a real running Studio + digitizer
service: an already-digitized `enthusiast_logo.png` project had two
fill-tier shapes carrying the "Underlay style" control this section used to
flag as unchecked. Set one (33.7 mm², `#0134`) from "Auto underlay" to
"None" and clicked "Apply layer changes" — the design's total stitch count
dropped 2,650 -> 2,016 (a real, substantial re-stitch through the actual
service, not a stale UI value), confirming the control's whole round trip:
dropdown -> `shape_overrides.underlay_style` -> real `/digitize` call ->
updated stitch plan -> updated Studio state. Screenshot on file
(`.playwright-mcp/underlay-style-applied.png` in that session's worktree).
This was the last of area 5's four `_OVERRIDE_KEYS` controls without its
own live-browser proof; border/tier/fill-angle/boundary/merge-selection/
split were already covered by e2e specs or prior live sessions.

**A genuinely SUCCESSFUL merge's live-browser proof remains open, and is
harder than this doc previously scoped it** — re-investigated 2026-08-06,
source-level, not by assumption. Two candidate fixes this doc floated
("a purpose-built fixture image" or "a bridging/convex-hull merge
strategy") were checked against the real code before attempting either:

- **The "just recolor one shape to match, then merge" shortcut does NOT
  work**, and is worth ruling out explicitly so a future pass doesn't
  re-try it: `pipeline.run_stages` calls `apply_shape_merges` BEFORE
  `apply_shape_edits` on every single pass, so a merge always validates
  against each shape's ORIGINAL `thread_number` from stage 4, never a
  `shape_overrides` recolor — recoloring first and merging second (even as
  two separate Apply steps) never changes what the merge check sees, since
  each fresh `digitize()` call re-derives colors from scratch before any
  override is applied within that same call.
- **The deeper reason a "purpose-built fixture" is hard, confirmed by
  reading `stage3_segment.py` directly:** its connected-component pass runs
  PER FINAL THREAD LAYER (`for layer in range(len(quant.thread_indices))`),
  after any SLIC/RAG merging in `stage2_photo_segment.py` has already
  happened — so two regions reaching that stage with the SAME final thread
  assignment are fused if they're pixel-adjacent, regardless of whether the
  photo segmenter's own ΔE00 merge threshold (`MERGE_DELTAE00_THRESH`)
  considered them "different clusters" upstream. This is not lane-specific
  (the doc's prior phrasing implied only the flat lane was affected) — it's
  the same connected-component step either way. The only geometrically
  possible opening left is a pair of regions that are NOT pixel-adjacent at
  stage 3 (so they survive as separate shapes) whose VECTORIZED polygons
  (stage 4) happen to end up touching or overlapping anyway — a subtle,
  not-yet-attempted fixture-engineering target, not a quick win.
- **The fixture WAS attempted, same day, follow-up — and empirically
  falsified with real numbers, not just theory.** A gradient-classified
  probe image (two identical bright-green squares on a smooth ramp, forcing
  the SLIC+RAG lane) swept the gap between the squares from 0 to 40px
  (0-2.4mm at the probe's 16.67 px/mm) and measured the resulting regions
  directly via `digitizer_core.run_stages` + shapely, not through the
  browser. Result: **there is no gap value that produces two separate
  same-thread shapes close enough to plausibly vectorize-touch.** Below
  ~10px (~0.5mm) the two squares fuse into ONE region every time (SLIC's
  own superpixel averaging blends them before RAG ever runs — the
  superpixel diameter at `SLIC_N_SEGMENTS=1200` over a 1000x650px image is
  ~23px, comparable to or larger than the probe's own square size at small
  gaps). At >=12px (~0.7mm) they separate into two same-thread regions —
  but the measured shapely distance between them is **already 0.71-0.73mm
  at the very first gap where separation happens at all**, roughly
  constant across a wide range of further gap increases (SLIC's boundary
  quantizes to its own superpixel grid, so several different raw pixel
  gaps alias to byte-identical vectorized output) before finally growing
  with gap size at 40px (1.37mm). There is no intermediate regime: it's
  "one fused shape" or "two shapes >=0.7mm apart," never "two shapes
  touching." That floor is roughly three orders of magnitude past
  `simplify_tol_mm`'s ~0.03-0.12mm-scale vectorization tolerance (the
  mechanism a 2026-08-06 pass earlier speculated MIGHT close a small gap),
  so no fixture built from ordinary artwork through the normal SLIC/RAG
  pipeline can reach the "touching" state `apply_shape_merges` requires.
  This is now a settled, evidence-backed conclusion for this codebase's
  CURRENT segmentation parameters (`SLIC_N_SEGMENTS`, `MERGE_DELTAE00_
  THRESH`, `simplify_tol_mm`) — not "not yet tried."
- **What's left is genuinely a product decision, not more fixture-hunting:**
  a bridging/convex-hull merge strategy for non-adjacent shapes (changing
  `apply_shape_merges`'s own semantics to connect two shapes that don't
  touch, not just union ones that already do) is the only path left to a
  live successful-merge proof, and it changes what "merge" means for every
  user, not just this test case — Kent's call on whether it's wanted at
  all, not something to build unilaterally to satisfy a test-coverage gap.
  Not attempted this pass.

**Convert-to-text (text-cluster detection) — merged 2026-08-05** (PR #63
Steps 6a/6b, PR #64 Step 7 e2e): a new kind of manual-editing action,
distinct from every prior one in this area — instead of editing a shape's
own geometry/style, it REPLACES a whole detected cluster of shapes with a
different kind of project element entirely (area 1 above has the detection/
regularization side).

- **`DigitizePanel.svelte`:** a "looks like text" badge per candidate row
  (honest tooltip: "no character recognition — it can be wrong"), and a
  per-CLUSTER action bar (one per unique `text_cluster_id` visible, reusing
  the merge-selection bar's `.dgp-mergebar` markup) rather than a per-row
  control — deliberately, since a converted cluster's member rows move into
  this file's existing `unstitched` row branch, which renders no per-row
  badges or buttons at all; a per-row button would vanish exactly when Undo
  needs to be reachable.
- **New coordination logic with no prior precedent in this codebase:**
  every other override here (`tier`/`border`/`underlay_style`/
  `boundary_override`/merge/split) edits or replaces state on ONE existing
  element. "Convert to text" instead creates a brand-new `type: "text"`
  project element (via a new `addSeededTextElement`, sibling to `addElement`
  in `project.js`, seeded from the cluster's bbox/color — deliberately with
  an EMPTY `text` and `fontKey: null`, so nothing is ever auto-filled that
  could be silently wrong) AND, in the same user action, patches the
  ORIGINATING digitized element (`stitched: false` per member shape via the
  existing override plumbing, plus a new `textConversions` map recording
  which cluster produced which text element — pure Studio-side provenance,
  never sent to the server, unlike the wire-bound `mergeGroups`/
  `splitLines`). `App.svelte`'s new `onConvertClusterToText` is the
  coordination point; a new `converttotext` event carries the seed up from
  `DigitizePanel` through `ContentStep`, mirroring the existing `addelement`
  event's bubbling exactly.
- **Undo** mirrors `undoMerge`/`undoSplit`'s button-swap, with one real
  difference: merge/split provenance is re-derived from the last APPLIED
  job's own warnings (because the SERVER executed those edits); a text
  conversion's provenance lives entirely in `element.textConversions`
  already, since nothing about it was ever server-executed — no round trip
  needed to know what to undo.
- **A real bug the e2e test caught, not a test-authoring mistake:**
  `ContentStep.svelte` forwarded `DigitizePanel`'s `converttotext` event up
  to `App.svelte` but never wired the same forwarding for `removeelement`
  — Svelte component events don't bubble automatically, each parent must
  forward explicitly. `undoTextConversion` dispatches `removeelement` from
  inside `DigitizePanel`; with no forward, that event had nowhere to go, so
  undo silently never removed the created text element (no crash, no
  error — just a dropped event). Fixed with the missing one-line forward;
  the real e2e run (against the live service and browser, not a mock)
  failed before the fix and passed after.
- **Verification:** `project.spec.js` (3 new tests for the seed-element
  function), `digitizer.spec.js` (5 new tests for the wire-field mapping and
  the cluster/seed pure helpers), full Studio suite 426/426 (421 pre-existing
  + 5 new, baseline re-verified via `git stash` before trusting the delta).
  `app/e2e/text-cluster-convert.spec.js` (new, sibling to
  `digitize-boundary-edit.spec.js`) drives the real service end to end:
  upload the real benchmark fixture → badge appears on >=10 shapes →
  Convert to text → lands in an empty `TextStep` with no font picked → type
  real text, pick a font → navigate back → Undo → original shapes resume
  stitching, text element gone — **run for real, 1 passed**, after the
  `removeelement` fix above. Also manually verified live via Playwright MCP
  against a running dev session on the real benchmark fixture, screenshotted.
- **Out of scope, on purpose, AS OF THE 2026-08-05 MERGE:** real character
  recognition. **Superseded 2026-08-07 by the OCR-suggested-text entry
  immediately below** — this bullet is kept, not deleted, as an honest
  record of what shipped at the time; it no longer describes current
  behavior. Auto font selection/matching to the source typeface and any
  change to the satin/fill classifier remain out of scope, unchanged.

**OCR-suggested text (2026-08-07, not yet merged — draft PR against
`main`).** UX-safety-critical, not a convenience shortcut: automation-bias
research on prefilled-vs-empty form fields found people catch errors in a
confident-looking WRONG suggestion only ~30% of the time, vs. ~75% when the
system visibly hedges — so "Convert to text" prefilling an OCR guess is only
safe if it (a) is gated on real confidence and (b) never looks like
user-authored text until a human has actually looked at it. Both are now
true:

- **The gate** (`digitizer.js`'s new `textClusterSeed` logic,
  `OCR_SUGGESTION_MIN_CONFIDENCE = 55`, Studio-side — the service reports a
  raw per-member confidence and takes no position on "good enough," see area
  1 above): the cluster's suggested text is the MINIMUM confidence across
  its own members, not a mean (a word is only as trustworthy as its worst-
  read letter; a mean would let one badly-misread character hide inside an
  otherwise-confident average — verified by a dedicated test using real
  numbers where mean and min disagree). Threshold calibrated on real
  Tesseract measurements, not assumed: every genuinely-wrong real/synthetic
  cluster measured had a MIN confidence <=7.0 (the real benchmark fixture's
  own "ENTERPRISES INC." subline, which has two real misreads, measures
  0.0); every genuinely-correct synthetic control word measured had a MIN
  >=70.0. 55 sits centered in that gap. Below the floor — including a
  pre-OCR service sending neither field at all — behavior is byte-identical
  to before this feature existed: `text: ""`, `fontKey: null`.
  `fontKey` is NEVER auto-picked regardless of confidence — OCR gives
  characters, never a typeface match, exactly as the superseded bullet
  above already established, just no longer contingent on OCR being absent
  entirely.
- **Provenance + the "unconfirmed suggestion" treatment:** a gated seed also
  carries `textSource: "ocr-suggested"` through to the new text element.
  `TextStep.svelte` renders one small, non-blocking advisory badge ("Suggested
  from image — verify before saving") above the textarea while that flag is
  set, reusing `DigitizePanel.svelte`'s existing "looks like text" badge's
  visual convention (`.dgp-lbadge`'s pill shape) plus the `--warn-text` color
  this codebase already uses elsewhere for "needs a look" states — not new
  styling invented for this one badge. The flag (and badge) clear the
  instant the user edits the textarea, in the SAME patch as the edit itself
  (`text`/`textSource` set together, one dispatch) — an unconfirmed guess
  stops being unconfirmed the moment a human has touched it, whatever they
  changed it to.
- **Verification:** `digitizer.spec.js` (new tests for the wire-field
  mapping and the gate — fills/clears at the exact threshold boundary,
  min-not-mean aggregation, missing-data-is-no-signal, left-to-right
  ordering by bbox), `test_ocr_suggest.py`/pipeline/service tests on the
  Python side (area 1). First Svelte component spec for a NON-canvas panel
  (`ManualPanel.spec.js` was the only precedent, canvas-only): a new
  `TextStep.spec.js` + `TextStep.testHarness.svelte` (same "wrap in a real
  parent to observe Svelte 5's un-exposed component-event dispatch" pattern
  ManualPanel's own harness established) covers the badge appearing,
  disappearing on edit, and never appearing for ordinary user-typed text.
  Full Studio suite green (see "Running things" for the count this pass
  observed).

## Review & manual-editing detail moved from MASTER_SCOPE (2026-08-27)

Moved verbatim under the 800-line budget rule; MASTER_SCOPE keeps the verdict
and the two invariants. Nothing here was edited in the move.

**Copy/paste (Ctrl+C/V), Duplicate (Ctrl+D), and a per-shape Dim slider.** The
clipboard holds a shape *snapshot*, not an id, so a paste after the original was
edited or deleted still pastes what was copied. Dim is view-only and never
reaches the stitch plan or the `.embproj`. Both shipped with defects that a
pure-logic test could not see and a later review caught: `duplicateShape`
landed the copy exactly on the original for any shape flush to the canvas edge
(every traced outline, since `traceFitRect` letterboxes to the edges), and the
Dim slider froze at whatever value the shape had when it was selected, because
Svelte's legacy `$:` dependency list only sees what a statement *textually*
names — a read inside a called function is invisible to it. Both fixed, both
now pinned by tests proven to fail against the old code.
*(confirmed 2026-08-26 — `manualShapes.spec.js` + `ManualPanel.spec.js`, mutation-checked)*

**Driven in a real browser 2026-08-26** — right-click curved nodes, the tracing
backdrop, Duplicate, and the Dim slider, all exercised by hand rather than only
by tests. Two things were wrong that no test could see. The drawing canvas
opened mostly below the fold on a short viewport (14% visible at 1280x720, 92%
at 1440x900, 100% at 1080p — which is why it never showed on a desktop); it now
scrolls itself in **only when measurably clipped**, so a tall screen is
untouched. And the trace panel's file picker was a bare `<input type="file">`
rendering as raw OS chrome that read "No file chosen" even after a file loaded
(`onFile` clears the input's value so re-picking the same file still fires);
it now uses the same styled-label pattern as `DigitizePanel`'s `.dgp-upload`.
Confirmed working and NOT broken: the traced outline lands exactly on the
backdrop artwork, and the dropped-hole warning does show — before you accept
the shapes, which is the moment it matters.
*(confirmed 2026-08-26 — Playwright browser session, measured at three viewports)*

**The flat and realistic views now agree about sew order.** A colour that
recurs later in the sequence is its own block in both, not merged back into its
first appearance. The lit path was fixed for this on 2026-08-25; the flat path
kept the bug for another day, on the one view you switch to specifically to
judge coverage. Pinned as an invariant — the two views must produce the *same*
block sequence — rather than as two independent expectations.
*(confirmed 2026-08-26 — `preview.spec.js`, mutation-checked)*

**Eight more defects fixed by sweeping for the bug SHAPES, not the instances.**
PR #264 fixed nine defects in this area, and three of them existed for one
reason: a fix applied to one code path was never applied to its siblings. PR
#269 swept the repo for the shapes instead. What a user would have hit:

- **Manual shapes did not sew in draw order.** `digitize.js` sequences
  light-to-dark by default and the manual branch never opted out, so a cream
  circle drawn on top of a navy rectangle sewed cream-then-navy and the navy
  buried it. `ManualPanel` paints later-over-earlier and hit-tests
  back-to-front to match, and offers no reorder control — the stacking the user
  drew was simply unreachable. Now `darkOnTop: false` on the manual and
  preset-shape branches **only**; image mode keeps the heuristic, correctly,
  because nothing in a raster says which colour the artist meant on top.
  **This changes what already-saved manual designs sew**, which is the point.
- **A thread override landed on the wrong colour and EXPORTED that way.**
  `blockColors` is keyed by palette index, the service re-derives the whole
  palette on every run, and nothing remapped it: set "red → navy", re-digitize
  4 colours down to 3, and the override is now on white. `remapBlockColors`
  matches on the colour the override was chosen *for*, so it follows a thread
  that moved and is dropped with one the palette removed. Storage stays
  index-keyed — no `.embproj` migration.
- **A stale undo button deleted an innocent element.** Element ids are recycled
  (`nextElementId` is `max+1` over the survivors) and `textConversions` kept
  naming a deleted one, so a new element taking the freed id could be destroyed
  by the old cluster bar's "Undo". Pruned in `removeElement`, which every
  removal path funnels through. Monotonic ids were considered and rejected:
  schema change plus a migration for every existing save.
- **A bulk edit looked like it did nothing.** `sharedColor`/`sharedWeight`/
  `sharedFont` named only `multi`, a boolean — once multi-select is entered it
  is `true` and stays `true`, and `safe_not_equal(true, true)` is false, so all
  three readouts froze. The edits really applied; the panel just kept saying
  "mixed".
- **A stale cluster member count** (`{@const}` inside an `each` keyed by a
  string that never changes), and **a new template inheriting the last design's
  artwork** (`pickTemplate` replaced the project but never cleared the
  element-keyed `runtime`; `enterProject` has always cleared it — the unfixed
  sibling again).

Two of the guards pin RULES rather than call sites, which is the actual lesson
of the sweep: `ContentStep.reactivity.spec.js` asserts on compiled Svelte
dependency lists, and `App.projectReplacement.spec.js` asserts that every
whole-project-replacement path clears `runtime`. Twelve mutations were applied
and reverted, including faithful reproductions of each original bug — and one
test was caught passing for the WRONG reason (a `blockColors` fixture that never
actually collided two blocks onto one index) and its fixture corrected until the
mutation killed it. *(fixed 2026-08-26 — PR #269, mutation-checked)*
