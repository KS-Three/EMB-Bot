# Build plan: text-cluster detection + regularized lettering fallback

Spec: `docs/superpowers/specs/2026-08-05-text-cluster-detection-design.md`.
Follow this project's standing process: build in a worktree, TDD each step,
multi-lens review before merge. Every step is additive/back-compat — no
existing golden fixture should move unless a step's own note says so.

## Step 0 — Locate the run-tier stitch-width call site (spike, no code change)

The spec flags this as unresolved research, not a guess. Read
`stage7_sequence.py`'s run/bean-tier dispatch and whichever module actually
emits run-tier stitches (grep for `RUN_MIN_AREA_MM2`/`RUN_MIN_LOOP_MM`
consumers already found in `machine.py`, `stage7_sequence.py`, `config.py`,
`regions.py`, `stage6_border.py`, `stage6_detail.py`, `stage4_vectorize.py`,
`stage6_applique.py`, `stage3_segment.py` — but the actual STITCH GENERATOR
for the run tier wasn't pinned by the initial research pass). Output: a
one-paragraph note (can live as a code comment at the Step 5 call site, no
separate doc needed) citing the exact function and how it currently derives
stitch width for a run-tier shape. This unblocks Step 5's estimate — if the
width is already parameterizable per-shape, Step 5 is small; if it's a global
constant, Step 5 needs its own small plumbing change and should be re-scoped
before starting.

Acceptance: a precise file:line citation, no code changed yet.

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

## Step 5 — Regularization: shared stroke width per cluster

Using Step 0's citation, change the run-tier width computation so that when
a region carries `meta["text_cluster_id"]`, it uses that cluster's median
stroke width (computed in Step 2, either recomputed here or threaded through
`Region.meta` — prefer storing it once in Step 2's tagging pass as
`meta["text_cluster_stroke_mm"]` to avoid a second `build_shape_field` call
per shape).

Tests:
- Before/after stroke-width variance across a tagged cluster's members,
  measured from real emitted stitch coordinates on `enthusiast_logo.png` (not
  from the test's own assertions) — variance must drop, not just "test
  passes."
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
