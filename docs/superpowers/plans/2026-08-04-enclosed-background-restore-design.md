# Design pass: making `BACKGROUND_ENCLOSED` regions real, restorable shapes

Status: DESIGN ONLY, not built. Follow-up to Defect 2 in
`docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`
("Defect 2 update" section), which root-caused the bug to `stage1_prep.py`
and sketched a 5-point recommended shape. This doc grounds that sketch in
the ACTUAL current service contract and Studio UI (researched fresh this
session, see below) and turns it into something buildable.

## The bug, one sentence

`stage1_prep.py::prep`'s no-alpha branch folds `enclosed` (background-
colored pixels not reachable from the true image border) into `bg`, so
those pixels are excluded from `fg` before stage 3, vectorization, or
`assign_shape_ids` ever run — they never become a `Region`, never get a
`shape_id`, and so can never be named by a `shape_overrides`/
`deleted_shape_ids` edit. The warning's own copy — *"toggle them on in
review if they should sew"* — describes a control that does not exist.

## What Studio already has (researched this session, not assumed)

This matters because the fix should reuse this, not invent something
parallel to it:

- Studio keeps a **full remembered shape list** client-side (`project.js`'s
  `review`), not just ids. Deleting a shape is *only* adding its id to
  `deletedShapeIds` (`DigitizePanel.svelte:388-391`) — nothing is discarded.
  `digitizer.js::reconcileReview` (`:204-220`) carries a deleted shape's
  last-known row forward from the client's own cached `review` into each
  fresh response, which is why it keeps rendering (struck through) even
  though the server stops returning it.
- The Layers panel (`DigitizePanel.svelte:567-697`) already renders exactly
  the visual state we want: a dimmed, struck-through row labeled "hidden"
  with a single **Restore** button. Edits are staged and only take effect on
  an explicit "Apply layer changes" click, which re-invokes `runDigitize`.
- **Why this can't be reused as-is:** that whole mechanism depends on the
  shape having existed in a PRIOR response the client already cached. An
  enclosed region has never been in ANY response before this feature exists
  — generation 1 has no prior `review` to carry it forward from. The
  client can't pre-populate `deletedShapeIds` with an id it has never seen.
- `region.meta`/the wire payload has **no existing visibility concept** —
  confirmed by grep, only `layer`/`tier`/`fill_angle_deg`/`border`/
  `applique`. `_review_payload` (`digitizer_service/app.py:256-292`) sends
  `shape_id, thread_index, thread_number, area_mm2, source, layer,
  sew_index, sew_block, tier, outline_mm, holes_mm` per shape — nothing
  about default visibility.
- `shape_overrides` is validated in TWO places kept in lockstep by
  convention: `app.py::_OVERRIDE_KEYS`/`_canonicalize_shape_edits` and
  `regions.py::apply_shape_edits`. Adding a key means touching both, the
  same as every existing key (`border`, `tier`, etc.) already does.

**Conclusion: this needs a genuine new mechanism, not a client-side trick
riding `deleted_shape_ids`.** The design below adds one new override key
(`stitched`) rather than a parallel "inverse deleted list," because that's
the smallest addition consistent with the existing contract's own shape.

## Proposed design

### 1. Stage 1 — stop excluding, start tagging

`stage1_prep.py::prep`, no-alpha branch: `enclosed` still gets computed
exactly as today (nothing about detecting it changes), but instead of
`bg = border_bg | enclosed`, it becomes `bg = border_bg` and `enclosed`
joins `fg` — full stop, same warning, same count, same
`BACKGROUND_ENCLOSED` code. New field on `Prep`: `enclosed_mask:
np.ndarray | None` (mirrors how `bg_outline_px`/`bg_edge_rgb` already ride
along as extras), so later stages can find it without re-deriving it.

Symmetric change needed in the alpha branch (`enclosed = bg & ~border_bg`
where `bg = alpha < 128`) for the rarer case of an enclosed *transparent*
region — same treatment, same new field.

**Why this is safe for every design that has no enclosed regions:** when
`enclosed.any()` is `False` (the common case), `bg` is bit-for-bit what it
was before this change, so `fg`/`art_bbox`/everything downstream is
untouched. Byte-identical output on every existing golden without an
enclosed region is a hard requirement here — same bar M1 of the DT-first
migration already holds itself to, and worth pinning as an explicit test
(diff `logo_whitebg`/`logo_alpha` before/after: neither has an enclosed
region, so both must be byte-identical).

### 2. Post-vectorization — tag the resulting Region(s)

After stage 4 (`vectorize`), for each `Region`, test overlap between its
rasterized footprint and `Prep.enclosed_mask` (same px<->mm mapping stage 4
already uses). A region whose footprint substantially coincides with the
enclosed mask (both directions — region mostly covered by the mask AND
mask mostly covered by the region, not just "any overlap") gets
`region.meta["enclosed_background"] = True`.

**Open question for build, not resolved here:** the exact overlap
threshold. Stage 1's `enclosed` mask is computed from raw color+
connectivity BEFORE quantization; stage 2/3 re-cluster and re-segment
independently, so there's no structural guarantee of a clean 1:1 match
between one `enclosed` connected component and one final `Region`. Needs
tuning against the ring-hole fixture (`tests/test_stages.py`'s `whitebg`
case) and `repro_gradient_white_icon.png`, and an explicit "ambiguous ->
fail open (don't tag, keep today's stitched-if-foreground behavior)" rule
— silently hiding something the tagger got wrong is worse than the status
quo bug.

This is a computed FACT re-derived every generation, not a review-screen
decision — like `layer`, and unlike `border`/`tier`/`fill_angle_deg`, it
does **not** need `match_shape_ids`' carry-forward treatment.

### 3. One new override key: `stitched`

`shape_overrides[sid] = {"stitched": true}` restores a tagged region. Same
shape as every other override — validated as a plain bool in
`app.py::_canonicalize_shape_edits` (add `"stitched"` to `_OVERRIDE_KEYS`),
applied in `regions.py::apply_shape_edits` by setting
`r.meta["stitched"] = bool(ov["stitched"])` when present, same pattern as
`border`.

Default resolution (no override present): a normal region's effective
`stitched` is `True`; an `enclosed_background`-tagged region's is `False`.
One line, right after `apply_shape_edits` runs (which is where every other
override already lands in `region.meta`):

```python
for r in regions:
    if "stitched" not in r.meta:
        r.meta["stitched"] = not r.meta.get("enclosed_background", False)
```

### 4. Where the exclusion actually happens

**Regions stay in `PipelineResult.regions` — always.** `_review_payload`
needs to list a `stitched: false` shape so Studio can show it and offer the
restore control; `apply_shape_edits`'s existing hard-delete path
(`deleted_shape_ids`) remains the only thing that actually removes a shape
from the list.

The exclusion is from **stitching**, at `plan_stitches` — filter regions
with `meta["stitched"] is False` out of what reaches `resolve_overlaps`/
`sequence` (stage 5-7), while `result.regions` (and therefore the review
payload) keeps every one of them.

**Open question for build:** does removing an unstitched region BEFORE
`resolve_overlaps` change the pull-compensation/underlap math for
NEIGHBORING real shapes that would otherwise have overlapped it? Plausible
answer is "no, because an enclosed region is by definition not touching
anything except the one shape that encloses it, and that shape's own
polygon already has this area as a hole in its topology" — but that's a
hypothesis to verify against real geometry, not an assumption to ship on.

### 5. The wire contract

`_review_payload`: add `"stitched": r.meta.get("stitched", True)` per
shape. Studio's `reviewFromJob` picks it up alongside the existing fields.

### 6. Studio side (scoped, not detailed — this is the Python-side design
pass; the JS side needs its own look before building)

- `DigitizePanel.svelte`'s Layers row needs a new visual state for
  "auto-hidden, review-toggleable" — almost certainly the SAME dimmed/
  struck-through/Restore-button treatment the delete flow already has
  (reuse, don't reinvent), but the Restore action here sets
  `shapeOverrides[sid] = {stitched: true}` instead of touching
  `deletedShapeIds`. Worth a UI label distinguishing "you hid this" from
  "the digitizer thinks this might be a hole, sew it?" — conflating the two
  risks a user not realizing which action they're taking.
- `project.js`/`digitizer.js`: `stitched` needs to persist across sessions
  the same way `shapeOverrides` already does (it already will, structurally
  — this rides the existing overrides object, no new persistence layer).
- `canonicalShapeEdits` (`digitizer.js:120-142`) needs `stitched` added to
  whatever it currently whitelists/canonicalizes for `shape_overrides`
  entries, mirroring the server's `_OVERRIDE_KEYS`.

## Test plan sketch

- `stage1_prep.py`: enclosed pixels now in `fg`; `bg_mask` unchanged when
  `enclosed` is empty (byte-identical on `logo_whitebg`/`logo_alpha`); new
  `Prep.enclosed_mask` populated correctly on the ring-hole and repro
  fixtures.
- Post-vectorization tagging: a new unit test asserting the ring-hole
  fixture's donut-hole region (and the repro fixture's icon regions) get
  `meta["enclosed_background"] = True`, and that an ordinary same-colored-
  as-background-but-NOT-enclosed shape does not.
- `regions.py::apply_shape_edits`: `stitched` override round-trips exactly
  like `border` does; default resolution rule covered directly.
- `app.py`: `_canonicalize_shape_edits` accepts/validates `stitched`
  exactly like the four existing keys; a bad value 400s.
- Full pipeline integration: `run_stages` + `plan_stitches` on
  `repro_gradient_white_icon.png` — icon regions exist in `result.regions`,
  are absent from the stitch plan by default, and restoring via
  `shape_overrides` makes them sew.
- `tests/test_stages.py::test_ring_hole_is_reported_as_enclosed_background`
  — **outcome preserved** (still unstitched by default, warning still
  fires), but the assertion needs updating to the new mechanism: a real
  `Region` now exists, tagged, with `meta["stitched"] == False`, rather
  than the mask having simply excluded it from `fg` entirely.

## Sizing

Bigger than DT-first M0+M1 (~3 days, pure Python, no contract change) —
this touches three layers (pipeline internals, service contract, Studio
UI) and a genuinely new default-visibility concept. Rough shape: stage 1 +
tagging + Python tests is a self-contained day-or-two slice that could land
alone (regions become real and correctly excluded, verified via
`result.regions`/`plan_stitches` directly, no service or UI change yet);
the service contract addition is small once the Python side is solid; the
Studio UI slice is its own separate pass and the one this doc is least
confident about sizing, since it wasn't researched to the same depth as
the read-only investigation above (that covered EXISTING UX, not design of
new UX).
