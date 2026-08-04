# Gradient tier: angle fragmentation + enclosed-white-icon drop

Status: **Defect 1 (angle fragmentation) FIXED 2026-08-03**, same-day
follow-up session. Defect 2 (enclosed-white-icon drop) re-diagnosed with a
corrected root-cause location, still not built — see "Defect 2 update"
below. Filed 2026-08-03 after Kent ran a real gradient logo (Instagram icon:
diagonal purple→pink→orange gradient, white camera-icon linework) through
Studio the morning after the classifier + blend tier shipped, and the output
worksheet showed two distinct, confirmed defects. This is a regression
against the founding complaint the gradient tier exists to fix, not a minor
polish item — prioritize reading this before picking steps 5+ of
`docs/photo-digitizing-plan-2026-07-31.md` back up.

## Evidence

Kent's original file isn't available to reproduce from directly (uploaded
inline, not saved to disk), but a structurally equivalent repro —
`digitizer/testdata/photo/repro_gradient_white_icon.png` (diagonal
purple/magenta/orange gradient, white ring + circle + dot, all fully
enclosed by gradient on every side) — reproduces both defects exactly
through the real pipeline, `cfg.forced_class` not needed (classifies
`gradient` on its own, confidence 1.0). Keep this fixture; it's the
regression case for whoever fixes this.

```
classified as: gradient, confidence 1.0
regions: 23
warnings: CLASSIFIED_GRADIENT, BACKGROUND_UNCERTAIN, BACKGROUND_ENCLOSED
```

`stage1_bg.png` (debug output) shows the white icon linework fully intact
after background detection — stage 1 does not think it's background. The
final `stage6_stitches.png` render shows both defects directly: the white
ring/circle/dot are unstitched gaps, and the gradient body is a patchwork
of ~6+ differently-angled wedges instead of one flowing diagonal sweep.

## Defect 1 — gradient designs still fragment before blend treatment

**Root cause, confirmed via the region dump above:** `pipeline.py`'s
dispatch only routes `photo_subject`/`photo_scene` classes to the new
`stage2_photo_segment.segment()` (SLIC+RAG). `gradient` class still falls
through to the *original* `stage2_quantize.quantize()` — plain k-means —
for its stage-2 segmentation, exactly the "dithers gradients into
ordered bands" behavior the whole photo-digitizing effort exists to fix.
On the repro fixture this produced **23 separate regions** out of what a
person would call one continuous diagonal gradient.

`stage6_blend.py`'s "one shared fill angle" invariant is real, but scoped
one level too narrow: `blend_fill(region, ...)` computes
`principal_angle_deg(region.polygon)` **per region**, and each of those 23
k-means fragments has a different polygon shape — so each ramp-detected
fragment picks its own, independently-computed angle. The invariant holds
*within* one `blend_fill` call (all N shade layers of one region share one
angle) but not *across* the many regions that together make up what should
read as a single gradient. That's the patchwork.

**This was a real scope gap in the steps 1–2 plan, not an implementation
bug** — that plan explicitly deferred the SLIC/RAG region-former to step 4
and scoped step 4 to `photo_subject`/`photo_scene` only, on the reasoning
that "gradient" designs were closer to the flat lane. That reasoning turns
out to be wrong: a gradient's own stage-2 segmentation needs the same fix
photo-class segmentation needed, for the same underlying reason.

### Fix directions (not yet built, needs its own plan)

Two shapes worth weighing before picking one:

1. **Extend `stage2_photo_segment`'s dispatch to `gradient` too.** Cheapest
   change (one line in `pipeline.py`), reuses already-shipped, already-
   tested code. Open question: SLIC+RAG was tuned (`MERGE_DELTAE00_THRESH
   =10.0`) against `region_blobs.png`'s *shade* structure, not validated
   against a real linear/diagonal ramp — would need its own measurement
   pass before trusting it here, and the region-former was scoped
   deliberately "not customer-facing photo quality yet" (see its own plan
   doc's non-goals). Fragmenting a gradient into fewer, larger, still-
   independently-angled regions narrows the defect but may not eliminate
   it — it's a fragmentation-COUNT fix, not necessarily an angle-
   CONSISTENCY fix, unless paired with #3 below.
2. **A dedicated whole-image ramp detector at stage 2**, distinct from the
   photo region-former: when `classification.class_ == "gradient"`, fit
   ONE ramp model (linear or radial — `stage6_blend.detect_ramp`'s own
   fitting logic already does exactly this, just currently invoked per-
   region during stitch planning, one stage too late) against the WHOLE
   foreground *before* any per-color segmentation happens, and pass that
   single fitted model's angle down to every blend group so they all sew
   the same direction regardless of how many color bands the ramp gets cut
   into downstream. This directly targets the actual defect (angle
   consistency) rather than the proxy (region count).
3. **Whichever of the above wins, the shared angle needs to be threaded
   as data, not re-derived.** `stage6_blend.blend_fill` would need an
   optional `forced_angle_deg` (or similar) parameter, and `pipeline.py`/
   `stage7_sequence.py` would need to compute it once per design (not per
   region) and pass it through — mirrors how `cfg.fill_angle_deg` already
   works as a global override for ordinary tatami, just needs the same
   plumbing for the blend tier.

Recommend direction 2 (or 2+3 together) over 1 alone — it targets the
actual reported symptom (inconsistent angles) rather than a correlated
proxy (fragment count), and reuses `detect_ramp`'s existing, already-
verified fitting code rather than asking the photo region-former to do a
job (gradient consistency) it was never tuned or tested for.

### Defect 1 update — RESOLVED 2026-08-03 (same-day follow-up session)

Built, tested, and confirmed against the repro fixture end to end
(`digitizer/tests/test_stage6_blend.py::test_gradient_fragments_share_one_fill_angle_end_to_end`,
plus 3 supporting unit tests). Landed as direction 2+3 above, but the actual
mechanism differs from what this doc originally proposed, for a reason worth
recording:

**What actually needed fixing was not the true-ramp path.** The plan above
assumed `blend_fill`'s per-region `detect_ramp` was firing per-fragment and
picking a different direction each time. Measured instead: on the repro
fixture, **every one of the 23 k-means fragments falls through to the
ordinary-tatami fallback** (`detect_ramp` returns `None` for all 23) —
because `stage2_quantize.quantize()` has already flattened each fragment to
one near-uniform color band, so a fragment's own pre-quantize sample rarely
carries enough residual gradient to clear `RAMP_R2_MIN`. The "patchwork of
differently angled wedges" Kent saw was 23 independent calls to
`stage6_fill.principal_angle_deg` on 23 small, irregular fragment
silhouettes — the FALLBACK branch's hardcoded `angle_deg=None`, not the ramp
branch. The fix is threaded through both branches, but the fallback one is
what the repro actually exercises.

**Also different from the plan: lightness alone doesn't carry this ramp.**
A whole-design ramp detector modeled directly on `detect_ramp` (fit
lightness `L*` vs. position) was tried first and measured to fail on the
real repro: `L*` vs. position r2 = 0.003. The repro's purple→pink→orange
sweep is a **hue rotation**, not a lightness slope — `b*` (blue-yellow)
carries it instead, at r2 0.45. `detect_design_ramp_angle`
(`digitizer_core/stage6_blend.py`) fits **L, a, and b independently** and
takes whichever of the 6 (channel × linear/radial) fits explains the most
variance, gated at `DESIGN_RAMP_R2_MIN = 0.4` (a separate, lower constant
than `RAMP_R2_MIN`, justified in that constant's own comment). A radial
winner declines to produce an angle (no single line direction fits
concentric bands) and per-region behavior is untouched for those — that gap
is real and intentionally not closed here, see "Still open" below.

**What shipped, concretely:**
- `SourcePixels.design_row_angle_deg: float | None` — set once per design in
  `pipeline.run_stages`, from `detect_design_ramp_angle(p)` against the
  whole foreground, before stage 2 fragments it.
- `blend_fill`'s fallback branch (`model is None`) now passes
  `angle_deg=source_pixels.design_row_angle_deg` instead of hardcoded
  `None`.
- `blend_fill`'s true-ramp branch also prefers the shared angle when this
  region's own model is linear-kind (for whatever design DOES produce a
  single un-fragmented ramp region, or a future fix to defect 2/region-count
  that changes how much fragmentation survives to this stage).

**Verified:** ran the real repro fixture through `run_stages` +
`plan_stitches` end to end; every fragment's FILL runs now share one
dominant angle (measured from emitted stitch geometry, not from any
parameter) within 0.55° of each other, where before the fix they were up to
64° apart. Full digitizer test suite re-run clean apart from 3 failures
confirmed pre-existing on `main` before this change (unrelated golden
mismatches, environment-sensitive — not investigated further, out of
scope).

**Still open, not this fix's job:**
- **Fragment COUNT is unchanged** — still 23 regions on the repro. This fix
  makes every fragment sew the same DIRECTION; it does not merge them into
  fewer, larger regions. Direction 1 from this doc (routing `gradient` class
  through `stage2_photo_segment`'s SLIC+RAG instead of plain k-means) is
  still open and would address fragment count, if wanted, as a separate
  follow-up — worth re-measuring visual quality before assuming it's needed
  now that direction is fixed.
- **Radial ramps get no shared angle**, documented gap, see above.
- **Color/shade continuity across fragment boundaries** was not
  independently re-measured here (this fix targeted angle only, per the
  measured defect) — worth a look if a future sew-out or render review
  flags a residual shade-mismatch seam between adjacent fragments.

## Defect 2 — enclosed white design elements get dropped as holes

**Root cause, confirmed by the warning list:** `BACKGROUND_ENCLOSED` fired.
Per `warnings_codes.py`: *"enclosed bg-colored region treated as hole
(review-toggleable)"* — some stage between 1 and 3 decided the white icon
linework's color matches the design's detected background reference
closely enough to treat it as a hole rather than stitchable content, even
though `stage1_bg.png` shows the region survives background detection
itself intact. The enclosed-hole logic runs later (stage 3) and is
color-based, not connectivity-to-the-canvas-border-based — an enclosed
region that happens to share (or nearly share) the detected background
color gets excluded regardless of whether it's touching the real image
border.

This is **not new tonight** — `BACKGROUND_ENCLOSED` and its "review-
toggleable" framing predate the classifier/blend/region-former work
entirely (it's a stage-1/3 mechanism, general to the whole pipeline). What
tonight's real-world test exposed is that it's a live, customer-visible
defect on exactly the kind of art (gradient logo + white icon linework)
the gradient tier is supposed to make usable. Every white-on-color logo
(not just gradients) is a plausible victim of the same defect — flat-art
designs with white linework should be checked too, not assumed safe just
because they're a different classifier lane.

### Fix directions (not yet built, needs its own plan)

1. **Stop keying "is this a hole" purely on color match.** A real hole
   (fabric showing through, like the inside of a letter O) is *touching or
   reachable from* the true background — either the image border itself,
   or a region already confirmed background by stage 1's border-flood.
   `BACKGROUND_ENCLOSED`'s existing name suggests it may already intend
   this ("enclosed" implies a containment check happened) — needs reading
   `stage3_segment.py`'s actual implementation closely before assuming
   what it currently does vs. what its docstring/warning text implies;
   this diagnosis session didn't get that far.
2. **Respect real transparency over color heuristics when it exists.** If
   the source PNG carries an alpha channel, alpha is ground truth for
   "background" and should not be overridden by a same-color heuristic
   for enclosed opaque pixels — worth checking whether Kent's actual
   upload had alpha and whether that channel was honored end to end.
3. **The "review-toggleable" framing already implies a per-region override
   exists somewhere in Studio's review screen** (shape-layers contract —
   `apply_shape_edits`/`region.meta` machinery already shipped this
   session's earlier work touches). If so, the honest near-term mitigation
   might be smaller than a detection-logic rewrite: surface
   `BACKGROUND_ENCLOSED` findings more visibly in the worksheet/warnings
   Kent actually sees, so this is a one-click fix in Studio today rather
   than a silent drop discovered only by reading a stitch-count anomaly.
   Worth checking whether that path already works before assuming a
   bigger fix is required.

### Defect 2 update — root cause CORRECTED 2026-08-03, still not built

Direction 1 above asked to read `stage3_segment.py`'s enclosed-hole
implementation closely before picking a fix; that reading has now happened,
and it was the wrong file. **The actual logic lives in
`stage1_prep.py::prep`**, not stage 3: `enclosed = close & ~border_bg` (no-
alpha branch), then `bg = border_bg | enclosed`. `stage3_segment.py` never
sees enclosed pixels at all by the time it runs — they're already folded
into `bg`/excluded from `fg` at stage 1, before quantize, before
segmentation, before vectorization.

**2026-08-04 update: a full design pass now exists** —
`docs/superpowers/plans/2026-08-04-enclosed-background-restore-design.md`.
It grounds the "recommended shape" sketch below in the actual current
Studio delete/restore UX and service contract (researched fresh, not
assumed) and turns it into a concrete, buildable plan: enclosed pixels join
`fg` instead of `bg`, resulting regions get tagged
`meta["enclosed_background"]` by a post-vectorization overlap test against
a new `Prep.enclosed_mask`, a new `stitched` shape-override key (same shape
as the existing `border`/`tier` keys) restores one, and the exclusion from
stitching happens at `plan_stitches` — never from `PipelineResult.regions`,
so the review payload keeps listing it. Still not built; the design doc has
open questions (overlap-threshold tuning, stage-5 interaction) flagged for
whoever picks up the build.

That single fact resolves direction 3's open question too: **the "review
can toggle them back on" promise in the warning text and the
`stage1_prep.py` module docstring is currently FALSE.** Because enclosed
pixels are excluded from `fg` before `stage4_vectorize` ever runs,
they never become a `Region`, never get a `shape_id`, and so can never
appear in `apply_shape_edits`'s `shape_overrides`/`deleted_shape_ids`
round-trip — there is no shape for a user to toggle. `regions.py`'s
existing "deleted → hidden, undo restores it client-side" mechanism (used
by Studio's Layers panel delete/restore control, confirmed shipped per
`MASTER_SCOPE.md` area 5) is the closest existing precedent for what
"toggleable" would need to mean here, but it assumes the shape existed in
the FIRST generation the client saw — which an enclosed region currently
never does.

**Confirmed via the repro fixture:** `repro_gradient_white_icon.png` has no
alpha channel (checked directly, 3-channel PNG), so this is squarely the
no-alpha color-heuristic path, and direction 2 (alpha as ground truth)
would not have helped Kent's actual repro even if built — it's a real
improvement for images that DO carry alpha, but a separate, narrower fix
than what this repro needs.

**Why this wasn't built alongside defect 1 this session:** unlike defect
1, this is not a contained, single-function fix. A real fix needs enclosed
pixels to flow through as genuine foreground (so they get quantized,
segmented, and vectorized into real `Region`s with real `shape_id`s, tagged
e.g. `region.meta["enclosed_background"] = True`), PLUS a new mechanism —
distinct from today's `deleted_shape_ids` — for "this shape exists, is
excluded from stitching by default, and is restorable," PLUS the
`digitizer_service/app.py` contract validation for whatever new
override key that needs, PLUS a Studio-side (`DigitizePanel.svelte`/
`digitizer.js`) affordance for the user to actually flip it. That is a
cross-cutting, multi-file feature on the scale of the DT-first M0/M1 slices
(`docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`), not a
"next small step" — it needs its own brainstorm/spec/plan pass, the same
discipline this project already applies to work that size, rather than a
partial build rushed into an unrelated session.

**Recommended shape for that future plan**, based on this session's
reading (not yet built, still open for a dedicated pass to design
properly):
1. Stage 1 keeps computing `enclosed` exactly as today (for the
   `BACKGROUND_ENCLOSED` warning), but stops folding it into `bg` — it joins
   `fg` instead, flowing through quantize/segment/vectorize like any other
   foreground content.
2. Whatever `Region`(s) result get tagged from the original `enclosed` pixel
   mask (an overlap test between each vectorized region's rasterized
   footprint and stage 1's `enclosed` mask, done once after stage 4).
3. A tagged region is excluded from `plan_stitches` by default — not
   deleted from `PipelineResult.regions` — so the client's first-generation
   response already lists it (Layers panel can show it in a distinct
   "hidden — enclosed background" state) with a real `shape_id` to act on.
4. A new override (e.g. `shape_overrides[sid] = {"stitched": true}`, or a
   sibling list to `deleted_shape_ids`) restores it on a re-digitize call —
   symmetric with, and reusing as much of, the existing shape-edits
   round-trip as possible.
5. The existing "ring hole" case (`tests/test_stages.py::
   test_ring_hole_is_reported_as_enclosed_background`) must keep defaulting
   to unstitched — this is additive (a real restore path), not a change to
   the default behavior for genuine holes.

## Priority note

Both defects sit on the exact lane (`gradient` classification) that steps
1–2 shipped tonight specifically to fix. Defect 1 (angle fragmentation) is
now FIXED — see the update above. Defect 2 (enclosed-white-icon drop)
remains open, root-caused to `stage1_prep.py`, and needs its own
brainstorm/spec/plan pass before building (see the update above) — a
customer who feeds in a gradient logo with white linework right now still
loses that linework silently, `BACKGROUND_ENCLOSED`'s "toggle it back on in
review" promise notwithstanding.
