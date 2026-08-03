# Gradient tier: angle fragmentation + enclosed-white-icon drop

Status: DIAGNOSIS + planned fix, not yet built. Filed 2026-08-03 after Kent
ran a real gradient logo (Instagram icon: diagonal purple→pink→orange
gradient, white camera-icon linework) through Studio the morning after the
classifier + blend tier shipped, and the output worksheet showed two
distinct, confirmed defects. This is a regression against the founding
complaint the gradient tier exists to fix, not a minor polish item —
prioritize reading this before picking steps 5+ of
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

## Priority note

Both defects sit on the exact lane (`gradient` classification) that steps
1–2 shipped tonight specifically to fix. Recommend treating this as the
next work item ahead of step 5 (direction fields) — a customer who feeds
in a gradient logo right now gets a worse-looking result than before the
classifier existed, on the flat lane's own honest terms, dropped content
and inconsistent hatching being strictly worse than the old flat-quantize
mush this was meant to replace.
