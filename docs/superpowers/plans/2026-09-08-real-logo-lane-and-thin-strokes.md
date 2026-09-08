# Real logos: thin strokes kept as strokes, and a lane of their own — plan

**Date:** 2026-09-08
**Status:** decision document. Nothing built. Kent picked items 1 and 2 of
`docs/quality-review-2026-09-08.md` to start on, together; this is the
plan for both, in the order the evidence says they have to land.
**Instruments this plan proposes:** `tools/thin_strokes.py`,
`tools/legibility.py`, `tools/color_diversity.py`.

## 0. What already governs this — read before changing the plan

- **The stage-0 recalibration is DESIGNED and BLOCKED, not open.**
  `docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`
  was settled with Kent: the success criterion is scale invariance
  (asserted by `tests/test_classifier_scale_invariance.py`, 6 passed / 7
  xfailed strict), four approaches were measured and rejected (resampling
  to a fixed width, re-siting `GRAD_VAR_GRADIENT_MIN`, proportional windows,
  and any bare threshold move), and the replacement signal is written down
  in its §6: distinct 3-bit-per-channel colours needed to cover 90% of the
  foreground, invariant across a 14× resolution sweep. **What blocked it
  was positives**: one real gradient artwork (`drone`) against six flat,
  with a gap of two between `bridge` at 17 and `drone` at 19. ROADMAP gate 2
  bars synthetic substitutes. Nothing in this plan re-derives that.
- **The Studio already has the override.** The reading row states what the
  art was read as and offers a one-click correction (`DigitizePanel.svelte`:
  *"Read as shaded artwork, so it's sewing in blended thread shades. If it's
  really a…"*), which sends `forced_class`. Forcing flat is therefore
  reachable by a customer today, and what it does to Fremont is the point
  of §2.
- **Forcing flat on Fremont is "cleaner ground, more lost"**
  (`docs/kent-review-2026-09-03.md`): 3 colours, counters intact, and the
  rope and EST 1895 dropped outright by `DROPPED_SMALL_SHAPES`. That is
  item 2's defect showing on the flat lane, and it is the reason the lane
  decision cannot be measured until item 2 lands.
- **Chain rescue on the photo lane is a measured negative**
  (`docs/shape-fidelity-findings-2026-08-17.md`): on `summit_badge` it
  moved stage 2 from 34 regions / 12 threads to 46 / 15 and tripled the
  palette's worst excess (2.453 → 7.763), so `stage2_photo_segment.segment`
  calls `resolve_small_regions` with `chain_rescue=False`. Any small-shape
  change on that lane must re-run summit.
- **`k-means shatters texture`** (scope-history 08-15): forcing flat on
  textured art makes it worse. The flat lane is for flat-colour art.
- **DOCTRINE negatives that are adjacent and not reopened:** smoothing
  region polygons (item 3's plan covers edges), the DT-first classifier
  swap, and raising the satin cap as a number.

## 1. The gap, in numbers

| what | figure | source |
|---|---|---|
| committed real customer logos routed `gradient` | 6 of 7 | MASTER_SCOPE, area 1 |
| pro-parity logos routed `gradient` at confidence 1.00 | 10 of 15 | `docs/classifier-misroutes-real-logos-2026-08-15.md` |
| forced-flat gain, chance-corrected, mean per design | +4.85, better on 8 of 10, corpus +3.2 | same |
| Fremont on the gradient lane | 945 superpixels → 50 regions, 10 details under 1.5 mm absorbed; tagline = 5 tan regions of 0.9–8.6 mm² | `docs/kent-review-2026-09-03.md` |
| Fremont's small text in the art at 27 px/mm | 3.4–5.0 mm tall, 0.38–0.56 mm strokes; THE 3.1 mm, 0.24–0.28 mm | same |
| the pro's Fremont file at the same 92.5 mm | THE, EST 1895 and EAT STAY PLAY legible as 0.82–0.90 mm satin columns | same |
| Bridge Bar's grey halo cones | 6 cones, 29% of stitches, 50% of trims on JPEG artefacts | same |
| Kent's "whole elements missing" theme | 7 of 14 designs | `docs/kent-review-2026-08-27.md` |
| `dropped_elements` on Fremont | 0.2% lost | `.claude/memory/pro-files-refute-scale-limit-2026-09-03.md` |

## 2. Order: item 2 first, then the lane

Three reasons, each measured rather than preferred:

1. **Half the corpus is on the flat lane already** (Becker, enthusiast,
   whitebg, alpha, ribbon, bg_uncertain), and the Studio override sends any
   logo there. Thin-stroke loss on the flat lane is a defect on its own.
2. **The evidence against routing real logos flat IS item 2's defect.**
   Fremont forced flat keeps HOTEL FREMONT and THE and loses the rope and
   EST 1895 to the small-shape floor. With item 2 in, the lane question is
   measured against a flat lane that can hold a 0.4 mm stroke, which is a
   different question from the one the 08-15 numbers answered.
3. **Item 1's blocker is data, and gathering it runs in parallel** (§5).

## 3. Where thin strokes are lost today

Three mechanisms, in pipeline order, each with the line that owns it.

1. **The flat lane's small-shape policy absorbs by adjacency, not by
   colour.** `stage3_segment.resolve_small_regions`: a region under
   `(min_detail_mm · px/mm)²` (2.25 mm² at the default 1.5 mm) that shares
   any boundary with a larger region is unioned into whichever neighbour
   shares the longest halo, whatever colour either is. Only an ISOLATED
   small region is rescued for the run tier, and only when it clears
   `RUN_MIN_AREA_MM2` (0.16) and the loop proxy `2·max(box) ≥
   RUN_MIN_LOOP_MM` (2.2). A tan glyph sitting on a white ground touches the
   ground, so it is absorbed. The chain rescue
   (`_chained_small_regions`) keeps fragments of one structure that clear
   the floor together; it does not help a lone small glyph on a ground.
2. **The photo lane's superpixels cannot hold a stroke thinner than a
   block.** `_seeds_superpixels` requests ~1,200 superpixels over the
   foreground, so a block is roughly √(foreground px / 1200) on a side —
   about 47 px, 1.7 mm, on Fremont. A 0.4 mm stroke is a quarter of a
   block; SEEDS assigns its pixels to a block whose mean colour is the
   ground, the RAG merge then compares MEANS, and the stroke is gone before
   any floor is consulted. The min-area floor runs after, with
   `chain_rescue=False`.
3. **What survives sews thin.** `stage6_satin` drops any cross under
   `SATIN_MIN_CROSS_MM` (0.5) and sews a hairline stretch as a 3-pass bean
   along the spine (`_hairline_stretches`, defect 24's mechanism). The pro
   widens the same strokes to a column two to three times the art's width.

And the instrument that should have seen it cannot:
`tools/dropped_elements.py` opens the disagreement mask by `HALO_OPEN_PX`
= 5 at its 10 px/mm, i.e. 0.5 mm, so a lost 0.4 mm stroke is erased from
the instrument before it is counted. That is why Fremont reads 0.2%.

## 4. The design for item 2

### 4a. Instruments first (PR 1) — no engine change

**`tools/thin_strokes.py` — thin-stroke recall, read on the stitches.**
For each stage-2 label on the prepped raster, skeletonise the label's ink
mask, read the distance transform on the skeleton (a HALF-width: the same
`dist/scale` radius `textcluster.py`'s docstring warns about), and keep
skeleton runs whose full width is under `cfg.min_detail_mm` and whose
length clears `RUN_MIN_LOOP_MM / 2` (the same constant applied to an open
stroke, which the bean run walks there and back). Then measure the fraction
of that skeleton length lying within `COVERAGE_THREAD_W_MM / 2` of any
emitted needle-down segment of a thread within `TEXT_CLUSTER_DELTA_E_MAX`
of the label's colour. Report per design: thin-stroke length, recall, the
longest lost stroke and where it is. **No opening** — the defect is exactly
what an opening deletes. Calibration: `ribbon_curve` (2.2 mm, no thin
strokes, recall n/a), Becker (none), a generated 0.4 mm-stroke fixture
(`tools/make_hard_cases.py` has the pattern), Fremont at 92.5 mm (expected
low). This is also the instrument for item 2's photo-lane half, where the
loss happens before any region exists.

**`tools/legibility.py` — OCR on the RENDER, per text cluster.** For each
`text_cluster_id` group (fallback: each stage-1 connected component the
letter door would admit), crop the artwork and `stitchviz.render_design`'s
output at 12 px/mm, run tesseract on both, and report the normalised edit
distance between the two readings; design-level is length-weighted. Needs
the `tesseract` binary — CI has it, this container does not, the OCR tests
already skip with a reason and this tool does the same. Calibration:
Becker (BECKER MARINE reads on both sides), Fremont (HOTEL FREMONT reads;
the tagline reads on the art and not on the render). This is the
phase-1 exit instrument for "lost" that no existing tool has, and it is
G4-clean: a per-cluster edit distance is not an agreement rate.

### 4b. Flat lane: absorb by colour, not by adjacency (PR 2)

Behind `cfg.keep_thin_strokes` (default OFF, byte-identical off). In
`resolve_small_regions`, a sub-floor region that has a neighbour is
absorbed today; with the flag, it is absorbed only when it is plausibly a
sliver OF that neighbour — its label colour within `cfg.merge_delta_e`
(6.0, the flat lane's own merge tolerance; no new number) of the
absorber's. A contrasting small region that clears the run-tier floors is
treated exactly as an isolated one is today: rescued, tagged
`rescued_small_shape`, which is door 1 of the text cluster. Fremont's EST
1895 and the rope chevrons are tan on white and pass; anti-alias slivers
sit within the tolerance and are absorbed as before.

Predicted on the primary golden: `logo_whitebg`'s 1 mm teal patch on the
red circle differs in colour but fails the loop proxy (2 mm against 2.2),
so it is absorbed as today and the golden holds. The orange 1 mm dot is
isolated and drops as today. State this as a test, not a comment.

### 4c. Photo lane: thin strokes as a third population (PR 3)

Same flag. The precedent is already in the code: enclosed-background
pixels are excluded from SEEDS and quantised as their own population by
`stage2_quantize._quantize_population`, then appended after the base
labels (`stage2_quantize.quantize`, `combined[enc_valid] = enc_labels +
base_k`). Thin strokes get the same treatment:

1. Before SEEDS, find thin ink on the prepped raster: run the flat lane's
   own k-means over `base_valid` (one pass, seconds), take each label's
   connected components, and keep those whose median DT width is under
   `cfg.min_detail_mm` and whose skeleton length clears `RUN_MIN_LOOP_MM
   / 2`. That union is the thin mask.
2. Exclude the thin mask from `base_valid` for SEEDS and the RAG merge, so
   no superpixel straddles a stroke.
3. Quantise the thin mask as its own population through
   `_quantize_population`, which brings the flat lane's majority filter
   and phantom-blend dissolve with it — the halo pass the gradient lane
   never got (defect 27) runs on exactly the population where JPEG ringing
   lives. Append its labels after the SEEDS regions.

Two risks, both measured before the flag ships: JPEG halos are thin
structures (Bridge Bar) — the dissolve inside the population is the
answer, and `tools/halo_spools.py` bills it; and photo fragments are
"mutually adjacent everywhere" (the summit negative) — the length gate is
what separates a stroke from a fragment, and the population must come back
EMPTY on the pure photographs (meadow, sunset, grass, the portraits) with
the photo goldens byte-identical.

### 4d. Widen lettering strokes to a sewable column (PR 4)

`textcluster.regularize_text_clusters` already redraws every door-1
cluster member as a fixed-radius buffer around its own skeleton, at the
cluster's median half-width. The widening is one line of policy on top:
target radius = max(cluster median, floor / 2), behind
`cfg.lettering_min_column_mm` (default None = today's behaviour). The
target is the SEWN column, so the artwork radius is the floor minus the
fabric's pull (stage 5 adds it back), never narrower than the art. Door-2
ordinary lettering stays untouched, as that function's own docstring
argues; the hairline bean tier stays as the fallback for whatever still
falls under 0.5 mm. Measured on the stitches with `tools/satin_columns.py`
(the second row) and `tools/legibility.py`.

**The number is gate 1's.** Three candidates, all with a provenance:
`PHOTO_MIN_SATIN_WIDTH_MM` 1.0 (Law 31, an existing constant), `2 ×
SATIN_MIN_CROSS_MM` 1.0 (also existing), and the pro's 0.82–0.90 mm
measured on the Fremont file that was sewn on a patch — the evidence class
that settled `FILL_ROW_MM`. The mechanism is identical whichever Kent picks.

## 5. The design for item 1 — the lane

### 5a. Re-measure the spec's signal on the real tonal artwork that exists now (PR 5)

`tools/color_diversity.py` implements the 08-15 spec's §6 statistic and
prints it across the resolution sweep for every real artwork reachable:
flat — Becker, tires, Fremont, Bridge Bar, Gaulke, Golden Tee, enthusiast,
and MFab on Kent's box; tonal — drone, Kent's Instagram icon (the
ORIGINAL, on his box — the committed repro is synthetic and barred), the
owl, and the four portraits in `testdata/photo/acceptance/` (gitignored,
re-attached per session). The spec asked for four or five real tonal
artworks; five real photographs plus two gradient logos is more than it
had, and whether photographs may serve as positives for a flat/gradient
boundary is a question for Kent (§8). The tool reports the flat max, the
tonal min, and the margin. Two outcomes:

- **It sites with margin.** PR 6a implements the replacement signal for the
  flat/gradient gate per the spec's §4 and §6 — one change, and the
  photo gate follows the same construction — deletes the strict xfail
  markers as they turn green, and presents the golden churn (ten designs
  change lane) for Kent's approval in CI, never on Windows.
- **It does not.** PR 6b routes by consequence instead of by statistic:
  when `design_ramp.fit_design_ramp` REFUSES a gradient-class design and
  `is_photographic` is false (declared, or detected per review item 13),
  segment with `stage2_quantize.quantize` while keeping the gradient class
  for reporting. Kent's 09-03 ruling already makes the ramp gate the
  arbiter of "this is a sweep"; a design it refuses is, by that ruling,
  not one. The known risk is `drone_render`, which the gate refuses and
  whose glow halos k-means may band — it is A/B'd explicitly on the
  stitches, and if it regresses the customer's mitigation is the reading
  row, set the other way. Whether an evidence-based lane change sits
  inside gate 2's letter is Kent's ruling (§8).

Either way the `CLASSIFIED_GRADIENT` copy and the reading row stay honest
about which lane sewed the design.

### 5b. What the lane change is measured on

All seven real logos plus drone, at the Studio's defaults, three arms
(gradient lane today, forced flat with item 2, the new route), read on the
stitches: cones and stops (`tools/color_cap.py`), trims per 1k and their
locality (`tools/trim_locality.py`), thin-stroke recall and legibility
(§4a), `dropped_elements`, `tools/edge_smoothness.py`, and the per-shape
tier diff (`tools/curve_tiers.py`'s construction, paired by centroid).
Renders in every PR body — Kent's 2026-09-04 rule.

## 6. What must not regress, with its fixture

| invariant | pinned by |
|---|---|
| flags OFF are byte-identical | `test_flat_lane_byte_identical.py`, `test_photo_lane_byte_identical.py` |
| the thin population is EMPTY on photographs | new test over meadow, sunset, grass, the portraits |
| summit's chain-rescue negative does not return | region count and `max_excess_de00` on `summit_badge`, flag ON |
| enthusiast's "A" counter (2.08 mm²) stays protected | `resolve_small_regions`' enclosed guard, existing tests |
| `logo_whitebg`'s teal patch still absorbs, the orange dot still drops | `test_stages.py` + a new case asserting the loop-proxy reason |
| trim ceiling 4.1/1k | `tests/test_chaining.py` — rescued strokes add shapes, so measure |
| scale-invariance xfails | PR 6a deletes them as they pass; PR 6b leaves them, honestly |
| convert-to-text per-cluster e2e | `digitize-auto-start.spec.js` and the textcluster suite |
| no new threshold without a stability read | `tools/ribbon_stability.py` on any rescued shape that reaches the DT gates |

## 7. Size and staging

| PR | content | size | gate |
|---|---|---|---|
| 1 | `thin_strokes.py`, `legibility.py`, tests, baseline numbers on the ten real-art fixtures | ~400 lines | none |
| 2 | `cfg.keep_thin_strokes` on the flat lane | ~80 + tests | none; goldens predicted unmoved |
| 3 | the thin population on the photo lane, same flag | ~200 + tests | none; photo goldens byte-identical OFF, empty population ON for photographs |
| 4 | `cfg.lettering_min_column_mm` | ~60 + tests | G1 on the number |
| 5 | `color_diversity.py` + the decision doc with the margin | ~150 | G2 — reports, changes nothing |
| 6a or 6b | the lane | ~150 / ~60 | G2 (6a) or Kent's ruling on its letter (6b); golden churn for approval |

## 8. Decisions for Kent

1. The order — item 2 before the lane (§2).
2. The widen-to number: 1.0 mm (an existing constant) or the pro's 0.82
   (measured on a sewn file), or wait for card block 5.
3. Whether real photographs count as tonal positives for the flat/gradient
   boundary, or only gradient logos do.
4. Supply the Instagram icon's original artwork and any customer artwork
   with genuine tonal content (airbrushed or shaded logos, photo patches,
   badges with real ramps).
5. If the boundary does not site: route by consequence (6b) with drone as
   the accepted risk, or hold the lane until the artwork arrives.
