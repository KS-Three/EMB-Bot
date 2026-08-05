# Text-cluster detection + regularized lettering fallback — design

## 1. Goal

Auto-digitizing quality has no owner for one specific, real, cited case: small
lettering in a logo (a wordmark subline, a tagline) currently digitizes as
generic small-shape geometry, not as letters. `stage3_segment.py`'s
`small_shape_rescue` path already exists precisely because this case was
observed on the benchmark fixture (`enthusiast_logo.png`'s "ENTERPRISES INC."
subline) — it stops the letters from being silently dropped, but it treats
each glyph as an independent noisy blob, not as a member of a word. The result
sews (it no longer disappears), but nine independently-simplified/rescued
letter shapes don't read as one consistent typeface the way real satin
lettering does.

This spec adds:
1. **Detection** — a classical-CV pass that flags "this cluster of small
   shapes looks like text" (size/proximity/stroke-uniformity heuristics, no
   OCR, no character recognition).
2. **Regularization** — the default, always-on treatment for a flagged
   cluster: stitch its members at one consistent stroke width (the cluster's
   own median, not each glyph's independently noisy measurement) so a
   detected-but-unconverted wordmark still reads as one coherent line of type
   instead of a decision to be made instead of nine unrelated stitch quirks.
3. **An opt-in shortcut, not a substitution** — Studio surfaces a "looks like
   text" badge and a "Convert to text" action per cluster. The action creates
   a real `type: "text"` project element (Studio already has one, entirely
   separate from the digitized-image path) seeded with the cluster's
   position/size/color, and the user types the actual word and picks a font
   themselves. The original traced shapes are hidden (`stitched: false`, an
   override key that already exists), not deleted, so "Undo" is a clean
   revert.

The explicit design goal of (3) is that nothing is ever auto-substituted:
detection can be wrong, and there is no font that will visually match an
arbitrary logo's typeface by guessing. The fallback (regularization) is what
ships by default and always looks like the source image; converting to real
lettering is a deliberate, per-cluster user action, never automatic. This is
the direct answer to the concern that drove this spec: a text detector with
no matching font available must never make a design look worse than doing
nothing.

## 2. What already exists (researched this session, not assumed)

- **`shapefield.py`** (`ShapeField` / `build_shape_field`): mask, medial-axis
  skeleton, exact EDT, computed on demand per-polygon — not cached per-Region
  anywhere in the pipeline. `field.dist[field.skel]` gives stroke half-width
  in px at every skeletal pixel; `shape_lens.py` already computes the
  equivalent mean/std/percentile stats (`DTStats`) as an independent
  instrument. This detector reuses `build_shape_field`, called fresh per
  candidate region — the same pattern `stage6_satin.extract_strokes` already
  uses behind its own opt-in flag (`stage6_satin.py:640-641`,
  `stage7_sequence.py:566`) — but does **not** wire into that flag or into
  `shape_lens.py`'s instrument; both of those are deliberately kept
  independent per `shapefield.py`'s own module docstring, and this is a third,
  equally independent consumer.
- **`stage3_segment.resolve_small_regions`** (`stage3_segment.py:89-206`):
  absorbs small regions into neighbors where possible; when a small region
  has no absorbing neighbor and clears `machine.RUN_MIN_AREA_MM2` / a loop
  floor, it's pushed onto `rescued` (line 162) instead of dropped — the
  isolated-small-text case, by the module's own comment (154-158).
- **`stage4_vectorize.vectorize`** (`stage4_vectorize.py:38-165`): gives a
  rescued/sub-detail shape a 0.5px de-staircase-only simplify floor (`eps =
  0.5`, lines 99-101) instead of the normal tolerance, and a second,
  authoritative rescue check on real geometry (138-147). **The `sub_detail`
  flag is a local loop variable — never written to `Region.meta`.** Nothing
  downstream can currently tell "this Region survived via the rescue path"
  after `vectorize` returns.
- **The override-key contract** (`regions.py`, `apply_shape_edits`): every
  user-editable key is validated against a closed vocabulary, written into
  `Region.meta[key]`, mirrored in `digitizer_service/app.py`'s
  `_OVERRIDE_KEYS`/`_canonicalize_shape_edits`, and explicitly listed in
  `match_shape_ids`'s carry-forward tuple (`regions.py:157-158`) or it
  silently evaporates on re-digitize. Current keys: `thread_index`,
  `fill_angle_deg`, `tier`, `border`, `layer`, `sew_order`, `stitched`,
  `underlay_style`, `boundary_override` (v1.4), `merge_shape_ids`/
  `split_shapes` (v1.5).
- **`stitched` (v1.1)**: already means "computed, tagged, but not sewn" —
  exactly the mechanism needed to hide a cluster's original traced shapes
  once the user converts it to a real text element, with a clean undo path
  (the enclosed-background feature already built the Studio-side restore UI
  for this exact key).
- **`_review_payload`** (`digitizer_service/app.py:476-522`): per-shape
  response already includes `outline_mm`, `layer`, `tier`, `stitched`, etc.
  No stroke-width or classification field exists today — this spec adds one.
- **Studio's element model already has a separate `text` element type**
  (`app/src/lib/project.js:213-216`, `defaultTextElement`, `fontKey` +
  position/size), composed alongside `digitized` elements in `ContentStep.svelte`.
  `src/satinfont.js`/`src/satinplay.js` render text from **authored** glyph
  rails+rungs — no auto-tracing, by design. This is the exact reason "convert
  to lettering" can mean "create a new text element," not "trace this glyph's
  outline with satin machinery."
- **UI toggle pattern** (`DigitizePanel.svelte`, using `underlay_style` as the
  template): `overrideX(row, ov)` reads current value → a control writes via
  `setShapeX(sid, v)` → `setOverride(sid, fields)` merges into
  `element.shapeOverrides` → `patch({ shapeOverrides })`. The merge/split
  provenance pattern (`mergedFromInfo`/`undoMerge`, same file) is the template
  for the text-conversion undo control.

## 3. Proposed design

### 3.1 Mark rescued shapes so downstream code can find them

`stage4_vectorize.py`'s `Region(...)` construction (currently line ~150-159)
gains `meta["rescued_small_shape"] = True` whenever `sub_detail` was true for
that shape. Zero behavior change on its own — purely a marker so the detector
in 3.2 doesn't have to re-derive "was this shape sub-detail" from scratch.

### 3.2 New module: `digitizer_core/textcluster.py`

Mirrors the shape of `barecircle.py`/`shapefield.py` — a small, focused
instrument, not folded into an existing stage file.

`detect_text_clusters(regions: list[Region], p: Prep) -> None` — a
post-vectorization tagging pass, same shape as `tag_enclosed_background`:

1. Candidate filter: regions with `meta.get("rescued_small_shape")`, plus (a
   build-time decision, see Open questions) possibly any region under
   `cfg.min_detail_mm` regardless of rescue path, to catch a small logo detail
   that happened to have an absorbing neighbor.
2. Per candidate: `build_shape_field(region.polygon)` → stroke-width stats
   (mean/std of `dist` at `skel`, reusing the exact `DTStats`-style
   computation `shape_lens.py` already has, as its own independent copy per
   `shapefield.py`'s stated design).
3. Spatial/similarity grouping over candidates: cluster by proximity (within
   N mm of a shared baseline) and similarity of both bbox height and
   stroke-width mean — deliberately simple, geometry-only, no character
   recognition. A group is only tagged if it clears a minimum member count
   (letters come in groups; one isolated small shape is not "text").
4. Tag every member of a passing group: `meta["text_candidate"] = True`,
   `meta["text_cluster_id"] = <deterministic id, same blake2s-digest pattern
   as `_merge_shape_id`/`_split_shape_id` in `regions.py`, hashed from the
   sorted member shape_ids>`.
5. Like `tag_enclosed_background`, an ambiguous case fails open: untagged,
   sewn by the existing rescue-path treatment exactly as today. A tagger that
   silently hides a shape is worse than a missed tag.

Called from `pipeline.py` right after `tag_enclosed_background(regions, p)`
(line 269) — same "computed fact, before shape edits" ordering rationale
already documented there.

### 3.3 Regularization: consistent stroke width per tagged cluster

**Corrected during Step 0's spike (superseding the first draft of this
section) — the run tier has no stitch-width parameter to feed a median
into.** `run_outline` (`stage6_border.py:621-685`) traces each shape's own
polygon ring exactly, at a fixed global stitch spacing
(`machine.BEAN_STITCH_MM`/`BEAN_PASSES`) — by its own docstring, "the outline
IS the artwork." A rescued letter's apparent stroke weight is entirely a
property of its traced polygon, set back at vectorization; there is no
per-shape width input to `run_outline` to adjust.

The actual lever, therefore, is geometric, not a stitch parameter: for every
region carrying `meta["text_cluster_id"]`, **redraw its polygon** as a
fixed-radius buffer around its own skeleton — both already computed by
`build_shape_field` in 3.2 — sized to the cluster's target half-width (the
median of the cluster's per-member `text_cluster_stroke_mm`, also computed in
3.2). This replaces `region.polygon` for tagged members with a
visually-regularized version before stage 7 ever calls `run_outline` on it —
the same "replace this shape's geometry" shape `boundary_override` already
establishes as a legitimate operation on a `Region`, just computed by the
pipeline instead of hand-edited by a user.

This is applied in the same post-vectorization pass as tagging (3.2), not as
a separate stage7 change — geometry is settled before sequencing runs, same
ordering rationale `tag_enclosed_background`/`detect_text_clusters` already
follow.

### 3.4 Wire contract: one new read-only review field, no new override key

Deliberately **not** a `shape_overrides`/`_OVERRIDE_KEYS` entry — the tag is
server-computed from geometry, never client-submitted, so it doesn't need
`regions.py` validation, an `app.py` mirror, or a `match_shape_ids`
carry-forward — it's re-derived every generation, same category as `layer`
and `enclosed_background`.

`_review_payload` (`app.py:476-522`) gains, per shape:
```json
{
  "text_candidate": false,
  "text_cluster_id": null
}
```

### 3.5 Studio side (scoped, not detailed — Python-side design is this spec's
focus, same convention `enclosed-background-restore-design.md` used)

- `DigitizePanel.svelte`: a row with `text_candidate: true` gets a small badge
  ("looks like text") and, once per unique `text_cluster_id` visible, a
  "Convert to text" action.
- The action: opens the existing text-element creation flow (`TextStep`'s
  underlying data shape), pre-seeded with the cluster's combined bounding
  box, dominant thread color, and a rotation guess from the cluster's
  baseline — but an **empty** text field the user must fill in themselves,
  and the existing font picker with no font pre-selected. Nothing is
  auto-filled that could be silently wrong.
- On save: a new `type: "text"` element is added to the project, and every
  shape in that `text_cluster_id` gets `stitched: false` via the existing
  override plumbing (same mechanism the enclosed-background restore UI
  already uses in reverse).
- Undo: mirrors `undoMerge`/`undoSplit` — remove the text element, clear the
  `stitched: false` overrides for that cluster's shape ids. Provenance stored
  the same way merge/split provenance already is (a `textConversions` map,
  sibling to `mergeGroups`/`splitLines`, keyed by `text_cluster_id`).

## 4. Known quality limits (documented, not hidden)

- The detector is geometry-only: it cannot read characters, cannot tell a
  three-letter word from three unrelated small circles that happen to be
  similarly sized and spaced. False positives get an ignorable badge (no
  behavior change); false negatives get today's existing rescue treatment
  (no regression). Neither failure mode changes what gets stitched by
  default.
- Regularizing stroke width to a cluster median is itself an approximation —
  it improves visual consistency, it does not make traced-glyph run-stitch
  lettering look like real satin lettering. That gap is exactly what the
  "Convert to text" action exists to close, on the user's explicit say-so.
- No OCR anywhere in this slice, on purpose — this project's stack has no
  tesseract dependency today, and adding one was explicitly deferred by the
  process that scoped this spec (classical-CV heuristic chosen over OCR).

## 5. Out of scope

- **General shape-primitive recognition** (classifying arbitrary shapes as
  circle/rounded-rect/star for a "snap to clean primitive" manual-edit
  assist, or to strengthen the satin-vs-fill classifier). This is a related
  but separate, already-tracked thread — the DT-first classifier migration
  (`docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`, M0/M1 landed,
  M2/M3 blocked on the 37-file corpus). Do not conflate the two; this spec's
  detector answers "is this a text cluster," not "what primitive is this
  shape."
- Real character recognition / auto-filled text content.
- Auto font selection or auto font matching to the source typeface.
- Any change to the satin/fill classifier or to `is_satin_candidate`.

## 6. Test plan sketch

- Unit: `textcluster.py` on synthetic fixtures — a row of N similarly-sized
  rescued shapes clusters and tags; a single isolated rescued shape does not;
  two differently-sized/spaced groups don't merge into one cluster; ambiguous
  geometry fails open (untagged).
- Fixture-level: `testdata/photo/enthusiast_logo.png`'s subline — the
  documented real-world case — must produce a tagged cluster covering (most
  of) its rescued letter shapes, checked directly against emitted `shape_id`s,
  not just "a warning fired."
- Regularization: before/after stroke-width variance across a tagged
  cluster's members on the same fixture, same measurement discipline as the
  chaining/coverage fixes elsewhere in this doc's history (measure from real
  emitted stitch geometry, not from the shipped test's own assertions).
- Byte-identical golden safety: every existing golden fixture that is NOT
  text-cluster-tagged must be untouched — this is purely additive, same
  convention as every prior override-key slice.
- Service: request/response contract test for the new `text_candidate`/
  `text_cluster_id` review fields, following the existing `stitched`/
  `underlay_style` contract test pattern.
- Studio: unit tests for the badge/convert/undo UI logic (mirroring the
  merge/split spec files already in `app/src/lib/*.spec.js`), plus a
  Playwright e2e covering detect → convert → confirm the design actually
  gains a text element and the source shapes stop stitching → undo.

## 7. Risks

- **Threshold tuning on one fixture.** Like every classical-CV heuristic in
  this codebase, cluster thresholds (min member count, proximity, size/
  stroke-width similarity tolerance) will be tuned against
  `enthusiast_logo.png` first and may not generalize — flag this explicitly
  in the PR rather than claim broad coverage, same discipline the gradient-
  fragmentation fixes already modeled.
- **Regularization changes real geometry, not just metadata.** Unlike
  detection (informational tagging only), redrawing a tagged shape's polygon
  to a shared skeleton-buffer width is a genuine geometry change — it will
  move `enthusiast_logo.png`'s golden (expected and to be regenerated
  deliberately, per plan Step 5), and needs its own careful review pass
  distinct from the additive detection steps.
- **Scope creep toward general shape recognition.** Explicitly fenced off in
  §5 — worth restating in review, since "shape/outline recognition" as a
  phrase invites conflating this with the DT-first classifier thread.
