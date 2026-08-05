# Build plan: text-cluster detection + regularized lettering fallback

Spec: `docs/superpowers/specs/2026-08-05-text-cluster-detection-design.md`.
Follow this project's standing process: build in a worktree, TDD each step,
multi-lens review before merge. Every step is additive/back-compat — no
existing golden fixture should move unless a step's own note says so.

## Step 0 — Locate the run-tier stitch-width call site (spike, no code change) — DONE

**Finding (corrects the spec's first draft, see spec §3.3):** the run tier's
generator, `run_outline` (`stage6_border.py:621-685`, dispatched from
`stage7_sequence.py:653-659`), has **no per-shape stitch-width parameter at
all** — it traces each shape's own polygon ring exactly, at the fixed global
constants `machine.BEAN_STITCH_MM`/`BEAN_PASSES`. A rescued letter's apparent
stroke weight is a pure property of its traced polygon. There is nothing to
feed a cluster median into at the stitch-generation layer.

Consequence for Step 5: regularization must operate on the **Region's
polygon itself** (a geometry replacement, same category of operation
`boundary_override` already legitimizes), computed in the same
post-vectorization pass as detection, before stage 7 ever calls
`run_outline`. Step 5 below is rewritten accordingly.

## Step 1 — Mark rescued shapes in `Region.meta`

`stage4_vectorize.py`: at the `Region(...)` construction, set
`meta["rescued_small_shape"] = True` when `sub_detail` was true for that
shape (zero behavior change otherwise).

Test: extend `tests/test_stages.py` (or wherever `vectorize` is already
covered) — a sub-detail shape's resulting `Region.meta` carries the flag; an
ordinary shape's does not. Confirm every existing `vectorize`/golden test
still passes untouched (the flag is additive metadata, not geometry).

## Step 2 — `digitizer_core/textcluster.py`: detection module

New module, `detect_text_clusters(regions, p) -> None`, per spec §3.2:
stroke-width stats via `build_shape_field` (reuse, don't modify
`shapefield.py`), spatial/size/stroke-width clustering over
`rescued_small_shape` candidates, deterministic `text_cluster_id` (blake2s
digest of sorted member shape_ids, same pattern as `_merge_shape_id` in
`regions.py` — copy the pattern, don't import private helpers across
modules).

Tests (`tests/test_textcluster.py`, new file):
- Synthetic row of N similarly-sized/spaced rescued shapes → all tagged with
  one shared `text_cluster_id`.
- A single isolated rescued shape → untagged (below minimum member count).
- Two clusters, clearly separated or clearly different in scale → two
  distinct `text_cluster_id`s, not one.
- A borderline/ambiguous case → untagged (fails open, per spec §3.2.5).
- Determinism: same input regions (any order) → same `text_cluster_id`s.

Acceptance: all new tests pass; no existing test touched yet (module isn't
wired into the pipeline until Step 3).

## Step 3 — Wire into `pipeline.py`

Call `detect_text_clusters(regions, p)` immediately after
`tag_enclosed_background(regions, p)` (`pipeline.py:269`), same ordering
rationale already documented there (computed fact, before shape edits).

Tests:
- `tests/test_pipeline.py` (or nearest equivalent): running the full pipeline
  on `testdata/photo/enthusiast_logo.png` at its documented benchmark size
  (90mm) produces at least one tagged text cluster covering (most of) the
  subline's rescued shape_ids — checked by shape_id, not just "a warning
  exists."
- Full byte-identical-golden suite re-run: must be unchanged (this step adds
  metadata only, no geometry change yet).

## Step 4 — Expose in the review payload

`digitizer_service/app.py::_review_payload` gains `text_candidate` (bool) and
`text_cluster_id` (str|None) per shape, read straight off `Region.meta`. No
`_OVERRIDE_KEYS` entry, no `regions.py` validation — this is server-computed,
same category as `layer`/`enclosed_background`.

Tests: extend the existing service contract test file (whichever covers
`stitched`/`underlay_style` today) with a request against the
`enthusiast_logo.png` fixture asserting the new fields appear and are
consistent with Step 3's tagging.

## Step 5 — Regularization: redraw each cluster member at a shared skeleton-buffer width

Per Step 0's finding, this is a geometry change, not a stitch-parameter
change. In the same post-vectorization pass as Step 2/3 (or a function called
immediately after `detect_text_clusters`, still in `textcluster.py`), for
every region carrying `meta["text_cluster_id"]`:

1. Take the cluster's target half-width = median of member
   `meta["text_cluster_stroke_mm"]` (stored once during Step 2's tagging, per
   its own note, to avoid a second `build_shape_field` call).
2. Buffer that shape's own skeleton (`ShapeField.skel`, already computed in
   Step 2) by the target half-width, producing a new polygon of uniform
   stroke width along the same medial path.
3. Replace `region.polygon` with the buffered result — guard with the same
   sewability floor `boundary_override`/merge/split already enforce
   (`machine.RUN_MIN_AREA_MM2`/`RUN_MIN_LOOP_MM`, `regions.py`'s
   `_check_sewable`): if the buffered shape fails the floor, or the buffer
   operation degenerates (empty/invalid polygon — a real risk when a
   skeleton has short spurs), leave the original polygon untouched and mark
   `meta["text_cluster_regularize_skipped"] = True` rather than risk
   producing bad geometry. Fail open, same discipline as every other tagger
   in this codebase.

Tests:
- Before/after stroke-width variance across a tagged cluster's members,
  measured from the REGION POLYGONS directly (half-width sampled along each
  member's own skeleton, same measurement `build_shape_field` gives you) on
  `enthusiast_logo.png` — variance must drop, not just "test passes."
- A degenerate-skeleton synthetic fixture (e.g. a shape whose medial axis has
  a short spur that would buffer into a self-intersecting or sub-floor
  polygon): confirm the fail-open path leaves the original polygon and sets
  `text_cluster_regularize_skipped`, does not crash, does not silently ship
  bad geometry.
- Every fixture with NO tagged cluster: byte-identical to pre-Step-5 output.
  `enthusiast_logo.png`'s own golden (if one exists) is expected to move —
  regenerate deliberately and note why in the commit, same convention as
  every prior corpus-law/golden update in this project's history.

## Step 6 — Studio UI: badge, convert action, undo

`DigitizePanel.svelte`, following the `underlay_style`/merge-split patterns
exactly (per spec §3.5 and §5's Studio pattern citations):
- Badge on rows where `text_candidate` is true.
- "Convert to text" action, once per unique `text_cluster_id` present among
  visible rows: seeds a new `type: "text"` element (bbox, dominant color,
  baseline rotation from the cluster) with an EMPTY text field and no
  pre-selected font; on save, sets `stitched: false` on every member shape via
  the existing override plumbing; records provenance in a new
  `textConversions` map (sibling to `mergeGroups`/`splitLines` in the element
  shape, keyed by `text_cluster_id` → the new text element's id).
- Undo: mirrors `undoMerge`/`undoSplit` — remove the text element, clear the
  `stitched: false` overrides for that cluster's shape ids, delete the
  `textConversions` entry.

Tests: `app/src/lib/*.spec.js` unit coverage for the new pure-logic helpers
(cluster grouping for the "one action per cluster" UI rule, provenance
lookup/undo), mirroring how `mergeGroupIssues`/`splitLineIssues` are already
tested.

## Step 7 — End-to-end verification

Playwright e2e (new spec file, sibling to
`app/e2e/digitize-boundary-edit.spec.js`): digitize a fixture with a known
text cluster (the subline case) → confirm the badge appears → convert →
type real text, pick a font → confirm the design updates (source shapes
stop stitching, new lettering appears) → undo → confirm the original
digitized shapes return. Screenshot the flow, same verification discipline
the boundary-editor slice used.

## Step 8 — Docs

Per the user's explicit call: do **not** touch `MASTER_SCOPE.md` mid-build.
Once this lands (all steps above merged, full suite green), run the
`update-master-scope` skill once to fold this into area 1/area 5 as
appropriate, and use that pass to also correct the record on the external
critique's inaccurate claims (color quantization, segmentation, background
removal, and small-detail culling all already existed before this feature) —
per the earlier conversation, not as a standalone doc-only commit before
that.

## Sizing

Steps 0–4 are the detection half — small, additive, no existing behavior
changes, safe to land first and independently review. Step 5
(regularization) is the one step with real golden-fixture impact and needs
its own explicit callout in review. Steps 6–7 are Studio-side and can proceed
in parallel with 5 once Step 4's contract is stable. Consistent with this
project's "medium" workflow-size convention, this is right-sized for
sequential PRs (roughly one per step, 2-4 steps could combine if small) via
`subagent-driven-development`, not a single mega-PR.
