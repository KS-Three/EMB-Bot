# Pro-parity: the five lane reports (2026-08-14)

Self-reports from the five parallel lanes, verbatim. The judge independently
re-measured all five (see `pro-parity-judge-report-2026-08-14.md`) and confirmed
every number here reproduced — including the two honest negatives.

## APPROACH A — directional cross-section width

**Verdict: NO**  ·  commit `45fd79e`

### What was built

APPROACH A — directional cross-section width. Instrumented `_rail_points` station-by-station on real letters first, then implemented the strongest form of the assigned idea: (1) inside `_DIR_ZONE_HALFWIDTHS` (1.5) half-widths of an open stroke end, blend the cross NORMAL toward the angle at the far edge of that zone — the nearest station whose tangent is the stroke's own direction rather than a cap-corner fork or a junction-blob compromise — so the ray casts a true perpendicular cross-section instead of a slant; (2) hold those end stations to the stroke's own median half-width over the trusted (non-end) stations, times a 1.15 flare tolerance, so a perpendicular ray that escapes down the welded arm cannot report that arm's clearance as this stroke's width. Also built and measured a global variant (same clamp applied to the whole stroke, not just the ends) and a wider-zone variant (2.5 half-widths / 0.45 max fraction); both were measured and reverted.

### What the renders showed

I read the per-stroke rail renders (my own diagnostic, /tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/laneA/rails_*.png) and the harness side_by_side.png for three designs, before and after.

becker_lc_large — BEFORE (side_by_side.png): the BECKER wordmark shows two obvious radial sprays, one in the C/K area and one at the B's lower bowl, plus visible spikes at the E. AFTER: indistinguishable at those junctions. Same sprays, same places, same size (stitch count 12548 -> 12481). At the per-stroke level the "E" region (S0cdd6202) DID visibly tidy: the top-bar and middle-bar crosses that previously sprawled and rotated into their square caps now run parallel; but the E's bottom-left corner — where the merge welded the stem to the bottom bar — still shows a full fan radiating from one point, unchanged.

becker_lc_large "M" (S71df5d9d) — this is the clearest picture of the real mechanism and it is NOT what the lane brief describes. The welded through-stroke carries TWO textbook starbursts: one in the M's inner-left valley and one at its apex. In both, every cross pivots on a single common point on the inner side while the outer rail sweeps normally. Before and after my change these two fans are pixel-comparable. The only visible change is the M's right leg, whose crosses now stay horizontal instead of skewing toward the bottom cap.

becker_lc_large "R" (S6a8697e1) — a single massive fan radiating out of the bottom of the R's counter, every cross converging on one point. Unchanged by the fix.

hotel_fremont_patch — "HOTEL" is marginally legible; "FREMONT" is a solid mass of overlapping fans with no recoverable letter shapes (pro's is clean). Identical before and after.

mfab_lc — the "4" and "P" of MF4B carry visible spray, and "AND WELDING INC" is garbled to the point of illegibility against the pro's clean tagline. Identical before and after.

So: a score-neutral change with the fan fully intact. By the protocol's own rule that is a FAILURE, and I am reporting it as one.

### Numbers

```
Baseline re-measured in my own lane at HEAD c91ab60 (matches the stated corpus baseline exactly, so the lanes are comparable):
  becker_lc_large 72.9 | becker_hat_large 69.7 | hotel_fremont_patch 57.7 | mfab_lc 71.5 | becker_chest_small 71.6   (mean 68.68)

AFTER (committed 45fd79e, end-zone directional width):
  becker_lc_large 72.8 | becker_hat_large 69.9 | hotel_fremont_patch 57.5 | mfab_lc 71.3 | becker_chest_small 71.5   (mean 68.60)
  Deltas: -0.1 / +0.2 / -0.2 / -0.2 / -0.1. A wash, slightly negative.

Variant measured then reverted — same clamp applied to the WHOLE stroke, not just ends:
  72.5 / 69.7 / 57.5 / 71.0 / 71.3 (mean 68.40). Worse.

Variant measured then reverted — wider end zone (2.5 half-widths, 0.45 max fraction):
  72.8 / 69.5 / 57.7 / 71.1 / 71.3 (mean 68.48). Worse.

Targeted fixtures (tests/test_satin.py + tests/test_textcluster.py): 71 passed, 0 failed. All four pinned over-correction fixtures (T_SHORT_STEM, T_SHAPE, Sf5200f3f, test_flat_lane_starburst_shapes_correctly_flip_to_fill) still pass.

FULL SUITE (one run, /tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/laneA/pytest_full_laneA.log): 14 failed, 1128 passed, 3 skipped in 21:44.
Baseline is 7 (confirmed against the prior iteration's logged failure list: 5 tesseract-dependent + 2 enthusiast_logo.png platform-mismatch goldens — all 7 also fail here).
=> 7 NEW FAILURES, all byte-identical golden guards:
  test_flat_lane_byte_identical [logo_alpha.png], [ribbon_curve.png]
  test_pushcomp flag-off byte-identical [logo_whitebg.png-towel], [ribbon_curve.png-hat_front], [ribbon_curve.png-left_chest]
  test_stage2_photo_segment golden [logo_alpha.png], [ribbon_curve.png]
The change alters rail geometry, so these break by construction. The protocol allows zero new failures, so the change fails the gate on top of failing visually.

Fan metric I built (a rail is "stalled" when it advances < 0.08 mm between stations — the needle re-entering its own hole, which is what a fan IS):
  becker_lc_large M stroke 0: 29/104 stalled BEFORE, 29/104 AFTER (global-clamp variant: 27/104).
  becker_lc_large R stroke 0: 28/112.
```

### Summary

Approach A does not work, and the instrumentation shows why: the premise it was built on does not hold in this code.

1. `field.half_at()` does not set satin widths at all. `_rail_points` already derives width from a PERPENDICULAR ray cast (`raw`, the nearer of the two boundary hits, median-filtered and smoothed). `half_at` enters only as the upper cap `floors[i] * 1.6 + 0.2`, and a full per-station dump of becker_lc_large's E (S0cdd6202, all 8 strokes, every station) shows final == smoothed EVERYWHERE — the cap never binds once. Making that reading directional is a no-op on the number it was supposed to correct.

2. The junction-anchored ends are not inflated. The E's three bars read 2.10-2.16 mm half-width at their anchors against a 1.75 mm shape half-width — that is the true crossbar cross-section, not a blob radius. There is no wedge from an inflated anchor to fix.

3. The starburst is INNER-RAIL COLLAPSE AT SPINE CURVATURE, not a width defect, and it is mid-stroke rather than at stroke ends. Where a welded through-stroke turns (M valley, M apex, R counter, E's stem-to-bottom-bar corner), the spine's radius of curvature R falls to about 1.2x the column half-width w, so the inner rail advances 0.02-0.08 mm per station while the outer sweeps 0.28-0.40 mm. Every cross pivots on one needle hole. That is the fan, verbatim.

4. The arithmetic closes the door on the whole lane. Inner-rail advance scales as (R - w)/(R + w). At R ~= 1.2w that is 0.09. To restore it to even 0.6 of the outer advance requires w <= 0.23R — a 1.4 mm column on a 4.2 mm letter. No width policy, directional or otherwise, can produce that and still cover the artwork.

What the committed code does buy: it visibly tidies END artefacts (the E's bars and the M's right leg stop skewing into their caps, because the normal near a cap is straightened to the stroke's own axis instead of following the surviving medial-axis fork). That is real but cosmetic, and it costs 7 byte-identical goldens for a -0.08 mean score change. Not shippable.

One genuinely new fact for the other lanes, measured as a by-product: becker_lc_large's M welded through-stroke pins to the 5.0 mm SATIN_MAX_WIDTH_MM ceiling for 40 CONSECUTIVE stations across its two diagonal junction blobs, against 4.0-4.4 mm legs — a real, sustained 20% flare over its own cross-section. Clamping it away (the global variant) removed the flare, moved the fan metric 29 -> 27 of 104, and cost score on four of five designs. So even the one place where the brief's "junction blob inflates the width" story IS true turns out not to be what makes the fan.

Where I would point the effort instead: the fan has to be attacked as spine geometry, not width. Either split/miter the column at the corner (`_split_sharp_corners`, currently demoted at _SPLIT_TURN_DEG = 90.0), or widen the turn radius in `_round_corners` — its window is k = round(half_mm / spacing), i.e. it spreads the turn over about ONE half-width, which is exactly what produces R ~= 1.2w. Spreading over ~3 half-widths would triple R and take the inner-advance ratio from 0.09 to roughly 0.56, which is the first number in this whole investigation large enough to matter. I did not implement that — it is outside this lane and it deforms the letterform corner, so it needs its own measurement.

### Risks the lane self-reported

- The committed change is NOT a fix and must not be merged as one — it breaks 7 byte-identical golden tests for a -0.08 mean score change and leaves the defect fully visible. It is committed only so a judge can retrieve the evidence and the instrumentation.
- My claim that `field.half_at` never binds is measured exhaustively on one region (becker_lc_large's E, all 8 strokes, all stations) and spot-checked on the M and R. It is possible some other letterform or a much smaller design does hit that cap; the claim is strong for these proof designs, not proven corpus-wide.
- The rail-stall threshold (0.08 mm advance) is my own metric, invented for this investigation and not validated against the professional corpus. It matches the visible fans on the M and R by eye, but it is a diagnostic, not a calibrated quality score.
- The R ~= 1.2w curvature figure is inferred from the observed inner/outer advance ratio rather than fitted directly to the spine, so the 0.23R arithmetic is order-of-magnitude, not precise. The conclusion it supports (no width policy can restore inner-rail advance at these radii) is robust to a factor of two either way, but the exact number is not.
- The `_round_corners` widening I suggest as the promising direction is UNMEASURED. It would change every corner in the corpus, would distort letterform corners, and could easily be its own wash — treat it as a lead, not a recommendation.
- The end-normal straightening does help end artefacts and passes all 71 targeted fixture tests including the four pinned over-correction guards. If some other lane finds the real fix, that piece may be worth re-testing as an independent small improvement once the goldens are regenerated — but only then, and only on its own evidence.

---

## APPROACH B

**Verdict: PARTIAL**  ·  commit `3897895`

### What was built

APPROACH B, refined to "never build a column on a CORNER FORK".

Diagnosis first (station-by-station on real letters, `_skeleton_edges` output before welding): the junction stubs that wedge are not arbitrary short arms — they are a specific, identifiable skeleton object. Thinning a bold corner forks the medial axis and runs a branch into the corner POINT where the DT is 0. `_prune_spurs` (1.6 half-widths) removes the short ones; a bold stroke's corner reaches ~1.4 half-widths past the node, so the rest survive as full edges. Two things then go wrong, and the second is bigger than the brief's framing: (1) the fork becomes its own stroke — anchored in the blob, pinched to zero = the wedge; (2) the fork is the BEST WELD CANDIDATE at that node (its tangent is the most anti-aligned thing a bar's end can pair with), so a real bar welds to it and the bar's own column hooks 45 deg into the cap corner and sprays there. becker_lc_large's "E" does this on both its top and bottom bar; its "A" apex was one 12 mm sunburst built exactly this way.

Implementation (all in stage6_satin.py):
1. `_corner_forks()` — classifies an edge as a fork from geometry alone: exactly one free end whose corridor is ~0 (a point, not a cap: measured 0.08-0.14 of the shape half-width vs 0.56+ for real free ends); length <= 1.7x the DT at its node (a fork into a wedge of half-angle T reaches node/sin(T): 1.41 at a right angle, 2.0 at a 60-degree V — past 1.7 the vertex is ACUTE and the fork is the only skeleton the letter's point has); and no plateau anywhere from node to tip over a 0.8 mm probe window (a plateau is a ribbon, and a ribbon is a stroke — the "R"'s leg holds 2.17 mm flat for 3 mm before it tapers, so it survives).
2. Forks are removed BEFORE welding, so nothing can weld to one. Guard: if the forks are the longest edges in the shape, the classification does not apply and every edge stands (logo_alpha's Sf5200f3f glyph apex is 4 forks + a 1.2 mm crumb; without this it sewed as nothing).
3. Coverage half — the part that makes deletion safe: a node left with < 3 arms is not a junction. ONE arm (the wider measured corridor, not the longer spine) is re-flagged FREE and runs out to the artwork edge, covering the corner square with its own column; the other tucks under it clearing that arm's MEASURED corridor instead of the omnidirectional blob reading (new `Stroke.tuck_under_*`). Letting both extend was tried and rejected — it double-sews ~1/3 of a bold E.
4. Weld direction is measured over one stroke width instead of 5 pixels (corner-aware path only), because at a corner the 5-px reading is already bending toward the fork and welds a 90-degree corner into a U.
5. Two cap fixes, both scoped strictly to corner ends so every byte-identical golden still holds: the cap extension aims over one stroke width, and stops 0.03 mm short of the edge so the terminal cross keeps both rails.

### What the renders showed

I rendered every letter of becker_lc_large at 30-60 px/mm with BEFORE and AFTER side by side (old module loaded alongside the new one, same region polygons), plus full-design ours_render/side_by_side for 4 designs.

becker_lc_large "E" (S0cdd6202): BEFORE — the top and bottom bars each hook into their right cap corner and their last ~8 crosses splay through 45 deg; loose X's of thread sit in the top-left and bottom-left corners; large bare patches mid-letter. AFTER — stem plus three bars, each a clean parallel column, crosses square to their own spine end to end. Every fan and every stray X is gone. This is the clearest single result in the lane.

becker_lc_large "A" (Sb689919f): BEFORE — one enormous starburst radiating out of the flat-top apex across the whole upper letter (~60 spokes, 8-12 mm each). AFTER — the flat top is a clean dense column and that starburst is GONE. A residual fan remains at the bottom-right inner corner of the counter: that is a genuine 3+-arm junction blob, which this approach deliberately does not touch.

becker_lc_large "M" (S71df5d9d) and "I" (S83a99d89): "I" BEFORE had crossing X's at both ends, AFTER is a clean column. "M" BEFORE had a big sunburst at the inner V plus X's at both top corners; AFTER the top and left stem are regular columns and the V fan is much smaller but NOT gone — the fork into that acute vertex is deliberately kept (dropping it sews bare fabric).

becker_chest_small (full render): stray spikes outside the letters of MARINE and BECKER are visibly reduced; letters read as more solid. "R" (Sae70d21d) at letter zoom: the sunburst around its counter and the fan in its foot are both gone, replaced by parallel columns.

mfab_lc (full render): the outer border and MF4B are visibly less spiky. IMPORTANT counter-example found here and acted on: at _FORK_NODE_MULT = 2.0 the "W" of the tagline lost the whole lower half of one diagonal to bare fabric, because at an ACUTE vertex the fork IS the letter's point. That is what set the 1.7 bound.

hotel_fremont_patch: BEFORE and AFTER both garbled. FREMONT is not a satin problem on this design — the reconstructed art merges the letters into blobs upstream, so neither version produces letterforms. Slightly more solid after, no visible fan change.

Verdict on the eye test: the corner-fork family of the fan is genuinely eliminated, not merely reduced. Two other families are untouched — 3+-arm junction blobs (A's counter, R's bowl) and acute vertices — and the pro's own file fans around the R's bowl too, so not all of the remainder is defect.

### Numbers

```
Per design, baseline -> after (own out dir /tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/lanes/B-absorb-stubs, same scorecard):
  becker_lc_large      72.9 -> 72.4  (-0.5)
  becker_hat_large     69.7 -> 69.4  (-0.3)
  hotel_fremont_patch  57.7 -> 57.4  (-0.3)
  mfab_lc              71.5 -> 72.0  (+0.5)
  becker_chest_small   71.6 -> 71.3  (-0.3)
  mean                 68.68 -> 68.50 (-0.18)
The loss is almost entirely the `und` (underlay economy) sub-score: columns that now run to the artwork edge carry proportionally more centre-run underlay. `cov` is flat or +0.01 everywhere.

Because the scorecard does not measure the defect, I added two direct measurements (both computed old-module vs new-module on identical regions):
  TOTAL CROSS ROTATION (degrees of cross-direction swing summed over the design — the fan's own signature), before -> after:
    becker_lc_large 6038 -> 5029 (-17%), becker_hat_large 5911 -> 4879 (-17%),
    hotel_fremont_patch 7875 -> 7305 (-7%), mfab_lc 7204 -> 6443 (-11%),
    becker_chest_small 5634 -> 4870 (-14%). Crosses swinging >= 8 deg fell in 5/5.
  BARE FABRIC (region area not within 0.2 mm of a satin stitch), before -> after:
    becker_lc_large 8.9% -> 8.5%, becker_hat_large 9.2% -> 8.2%,
    becker_chest_small 10.4% -> 9.6%, mfab_lc 4.6% -> 4.8%.
  So the letters fan less AND cover more, on 3 of 4; mfab is +0.2 pt of bare.

FULL SUITE (one run, at the end): 8 failed, 1134 passed, 3 skipped.
I also ran the full suite on the pristine baseline in this same worktree to get the true pre-existing set: 7 failed, 1135 passed (5 tesseract-dependent + `test_flat_lane_byte_identical[photo/enthusiast_logo.png]` + `test_stage2_photo_segment[photo/enthusiast_logo.png]` x2 — note COOKBOOK's list of which goldens are red is stale).
EXACTLY ONE NEW FAILURE: `test_chaining.py::test_chaining_cuts_the_benchmark_fixtures_trim_rate` — 4.55 trims/1k against a 4.1 ceiling (baseline 3.4). Concretely 12 trims instead of 9 on enthusiast_logo @82mm: columns that end at the artwork edge instead of tucked inside a blob give stage 7 fewer short in-shape hops to link.
Targeted fixtures: tests/test_satin.py + tests/test_textcluster.py 71/71 pass, including all four pinned fixtures named in the brief (T_SHORT_STEM, T_SHAPE, Sf5200f3f, test_flat_lane_starburst_shapes_correctly_flip_to_fill). textcluster is byte-identical by construction (it calls `_merge_through_junctions` without the DT argument and gets the old code path).
```

### Summary

Approach B works on the family of fans it can reach, and I can show it: the corner fork is a real, geometrically identifiable skeleton object, it is both the wedge stroke AND the thing bars weld into, and removing it before welding (while handing the corner to one named arm) removes the starburst from becker's E, A, I and the small text outright. Objectively: total cross rotation down 7-17% per design, bare fabric down on 3 of 4 designs, scorecard flat (-0.18 mean).

It is not the whole defect. Two other fan families survive untouched: 3+-arm junction blobs (the A's counter, the R's bowl — where the pro file also radiates, so part of that is correct technique) and acute vertices, where I deliberately KEEP the fork because it is the only skeleton the letter's point has (dropping it at the 2.0 bound blanked half a diagonal of mfab's "W"; that measurement set the 1.7 bound).

Two findings other lanes should have:
1. The brief's framing ("the remaining arm becomes its own short stroke") is only half the mechanism. The louder half is that the fork WELDS to a real arm and drags a full-width column 45 deg into a cap corner. Any fix that only filters emitted strokes leaves that untouched — which is consistent with the prior iteration's report that dropping naked twigs did not fix the render.
2. `_merge_through_junctions`'s 5-pixel arm-direction reading is not trustworthy at a corner. On the E fixture the stem and bottom bar read dot -0.55 over 5 px (welds a right angle into a U) and -0.20 over one stroke width.

Deployment caveat: `tests/test_flat_lane_byte_identical.py` pins every stitch coordinate of the flat lane and its docstring says "if this test goes red, the change under review is wrong". Any real fix to this defect moves letterform stitches. I got all of those green ONLY by scoping the two cap-geometry fixes to corner ends; the fork removal itself happens to leave those particular fixtures' satin unchanged. A more aggressive lane will need a deliberate golden re-capture, which the repo treats as Kent's call.

### Risks the lane self-reported

- ONE NEW TEST FAILURE, not papered over: test_chaining_cuts_the_benchmark_fixtures_trim_rate reads 4.55 trims/1k vs a 4.1 corpus ceiling (baseline 3.4) = 3 extra trims (~9 s machine time) on enthusiast_logo. Cause is structural, not a bug: capped corner columns end at the artwork edge, so stage 7 has fewer short in-shape hops to chain. Fixing it means re-tuning chaining/ordering, which I did not attempt.
- I edited a pinned test's stem SELECTOR (test_a_stem_crossing_three_junctions_welds_into_one_stroke): it identified the stem as the longest spine, and the stem's spine is now 5.25 mm vs the bottom bar's 5.32 because its two corner forks are no longer welded into it. Every assertion is unchanged and all still pass; it now picks the stroke that spans the glyph's height. A judge should confirm they accept that, since it is a pinned fixture.
- The 1.7 x node-DT length bound is the load-bearing constant and it sits between measured populations that are close at small letter sizes: corner forks run 1.10-1.63 on the big MARINE letters but 1.25-1.89 on the 1.8 mm-wide mfab tagline, where real acute-vertex forks start at 1.78. At sub-2 mm stroke widths the two populations touch and the rule will occasionally drop a point or keep a wedge.
- mfab_lc bare fabric rose 4.6% -> 4.8%. The remaining loss is concentrated in tagline-scale lettering, where a dropped fork is a large fraction of a tiny letter.
- The corner-owner choice (wider measured corridor wins, longer spine breaks ties) is decided on a median over one stroke width. On a corner where both arms are the same width — common in a monoline font — the tie-break is the spine length, which is arbitrary; the loser tucks and the corner is still covered, but WHICH column owns the corner can flip between near-identical shapes.
- Stroke gained four fields (capped_start/end, tuck_under_start/end) that must be propagated by any future code that builds or splits Strokes. _split_sharp_corners is handled; a new splitter that forgets them would silently lose the corner treatment.
- Everything here is measured on the raster medial axis at 6 px/mm. Every constant (_FORK_TIP_FRAC, _FORK_FLAT_MM, the 0.8 mm plateau window) assumes that pitch; changing _RASTER_PX_PER_MM would need them re-derived.
- hotel_fremont_patch is unaffected in substance — its FREMONT problem is upstream art reconstruction, not satin. Anyone scoring this lane on that design is measuring something else.

---

## APPROACH C — sew the junction as its own patch

**Verdict: PARTIAL**  ·  commit `b58c39c3522efd82eecc2cc0480192d18b5bd3ac`

### What was built

APPROACH C — sew the junction as its own patch. All changes in digitizer/digitizer_core/stage6_satin.py, keyed off a new _junction_blobs() that clusters 3+-degree skeleton node pixels into JUNCTIONS (clustering matters: a stem crossing a bar leaves a 4-pixel tie-break diamond that per-pixel reads as four separate 3-arm nodes) and measures each one's inradius from the distance transform. Three parts followed.

(1) ARM DIRECTION IS READ OUTSIDE THE LUMP. _merge_through_junctions's arm_dir used to read an arm's direction over 5 skeleton pixels (0.83 mm) from the node — entirely inside a 2.5 mm-radius blob, where the medial axis has already curved toward the lump's centre and every arm looks anti-aligned with every other. It now stands off by the blob radius and measures over an equally long baseline. This was the highest-value change: on becker_lc_large's M the stem and the diagonal genuinely leave 105 deg apart but scored as a through-pair, so one welded column pivoted ~75 deg over two millimetres — the inner rail collapses to a point and ~40 crosses radiate off it. That is the starburst mechanism I could actually see in the renders.

(2) CORNER TWIGS ARE NOT ARMS. The corridor test satin_stroke already used to refuse to SEW a corner twig (_junction_entry_mm returns None, plus the length guard) now runs BEFORE welding, so a twig can no longer be handed to a real arm and drag it into the corner. Gated to junctions with >=4 arms or >=2 dead ends, because a 3-arm/1-twig junction is a stroke ENDING (E_LETTERFORM's stem cap reaching a flush corner) and must keep its weld.

(3) THE RESIDUAL IS THE PATCH. _junction_patches unions the lump discs plus the folded twigs' corridors, clips to the artwork, then SUBTRACTS the ribbons actually emitted (_ribbon_of, read back through strip_splits). What survives is what no arm covered; it is sewn as a small tatami fill via stage6_fill.stitch_shape under its own "<shape>-junction" id, immediately after the column it sits against. Because it is a residual, no ribbon is ever shortened to make room for a patch, and a clean crossing produces no patch at all.

Two design decisions I reversed after measuring, both worth recording. First, I tried gating "is this a lump" on radius/arm-half-width ratio; that cannot work — a right-angle meeting of two equal ribbons has an inradius up to sqrt(2) times the half-width no matter how clean it is (pinned T_SHAPE measures 1.35, real bold corners 1.3-1.8), so no threshold separates them. Coverage, not size, is the discriminator. Second, I tried trimming arms back to the blob boundary to make room for the patch; that only moved which cases broke, so the shipped version leaves every arm's reach exactly as it was.

### What the renders showed

I read renders at every stage, both whole-design PNGs and my own per-region stroke overlays (/tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/lanes/C-junction-cap/render_shape.py, render_region.py).

WHAT THE DEFECT ACTUALLY LOOKS LIKE (baseline, per-region overlay of becker_lc_large's M, S71df5d9d): two textbook starbursts, each ~40 crosses emanating from ONE point on the concave side of a spine corner. The pivot centre is not on the spine — it is where the inner rail collapses as the column turns. Confirmed numerically: on becker's E, one welded column's cross angle sweeps from -39.5 deg to -121.1 deg, an 82 deg pivot over ~10 mm. So at these junctions the fan is a WELDED COLUMN PIVOTING, at least as much as it is a stub tapering off an inflated anchor width.

AFTER, becker_lc_large (final2_becker.png vs cmp_base.png): the large gray starburst filling the C's counter is GONE, replaced by even cross-hatch. The black fan in the C/K gap is gone. The inter-letter gray is even hatching instead of radial spikes. B-E-C-K-E-R all read as letters where before the C and K were fused by fan. Per-region: the M's two starbursts are gone (its stem, vee and right leg are now three separate near-straight columns); the E's top bar goes from a 75 deg pivot to 1.4 deg and its bottom bar to 4.2 deg. NOT fixed on this design: the gray outer silhouette still radiates spikes all round (that is the outer border's cap fan, a different mechanism), and the E's stem still turns 54 deg into its bottom-left corner because that junction has only one dead end and my gate acquits it.

AFTER, mfab_lc (final2_mfab.png): the P's bowl and the 4's crotch lose most of their spiky wedge and read as even hatch; modest but visible. Residual fan at the P's bowl tip.

AFTER, hotel_fremont_patch (final2_fremont.png): essentially UNCHANGED. FREMONT's E still shows a violent starburst radiating in all directions from its counter; the word is still barely legible. Small text is not helped at all — at that size the lump and the arms are the same size, so there is no decomposition to make.

AFTER, becker_chest_small (zoom_becker_chest_small.png): essentially UNCHANGED. The gray starburst in and around the C is still plainly there.

So: fan genuinely eliminated at the junctions of the LARGE letterforms on two of five designs; untouched on the two small-text designs.

### Numbers

```
Scorecard (tools/pro_parity/scorecard.py), baseline -> after, all rendered into PRO_PARITY_OUT=/tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/lanes/C-junction-cap:

  becker_lc_large      72.9 -> 73.4   (cov 0.91->0.92, dir 0.60->0.61, typ 0.55->0.57)
  becker_hat_large     69.7 -> 69.7   (unchanged)
  hotel_fremont_patch  57.7 -> 57.3   (REGRESSION, -0.4)
  mfab_lc              71.5 -> 72.2   (dir 0.58, und 0.72->0.81)
  becker_chest_small   71.6 -> 72.0
  mean                 68.68 -> 68.92 (+0.24)

Stitch cost: slightly CHEAPER than baseline, not dearer — becker_lc_large 12548 -> 12451, mfab_lc 11180 -> 10918. The patches add stitches but the twigs and pivoting welds they replace removed more.

Full suite (ONE run, digitizer/.venv/bin/python -m pytest -q > run.log): 7 failed, 1137 passed, 3 skipped in 17m13s. The 7 are exactly the documented baseline — 5 tesseract/OCR (test_ocr_gate, test_ocr_suggest x2, test_pipeline OCR fields, test_service OCR payload) and 2 platform-mismatch goldens (test_flat_lane_byte_identical[enthusiast_logo], test_stage2_photo_segment[enthusiast_logo]). ZERO new failures. Log at /tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/lanes/C-junction-cap/run.log.

Getting to zero took two real fixes found by an intermediate full-suite run that showed 10 failures: (a) junction patches are FILL runs inside a satin shape, and carrying the parent shape_id made them count as gradient fill fragments (test_stage6_blend angle instrument) and as fill on a forced-satin shape (test_shape_overrides) — fixed by the "<shape>-junction" suffix; (b) batching all patches up front cost trims, pushing the chaining benchmark to 4.12 trims/1k against a 4.1 ceiling — fixed by sewing each patch immediately after its neighbouring column, plus dropping residual slivers narrower than MIN_FILL_WIDTH_MM that a fill cannot sew anyway.

Two new pinned tests added in tests/test_satin.py: test_a_clean_crossing_is_left_alone_and_gets_no_patch (T_SHAPE and T_SHORT_STEM must emit zero fill runs) and test_a_junction_is_one_lump_not_one_node_pixel (E_LETTERFORM must measure 3 junctions, not one per diamond pixel). Targeted set (test_satin.py + test_textcluster.py) is green.
```

### Summary

Approach C works structurally and is visible, but it is not a fix for the defect as a whole — it is a real improvement on large bold letterforms and a no-op on small text.

The most useful thing this lane produced is a corrected root cause. The brief said the fan is a remnant stub tapering from an inflated field.half_at() anchor. Instrumented on real letters, the dominant visible starbursts are something adjacent: a THROUGH-WELDED COLUMN PIVOTING at a junction, because _merge_through_junctions read each arm's direction over 5 skeleton pixels — a distance that is entirely inside the junction blob on any bold letter. Two arms that genuinely leave 105 deg apart scored as a straight-through pair, and the column that welded them collapsed its inner rail to a point with ~40 crosses radiating off it. Reading direction from outside the blob fixes those welds and, on becker_lc_large, removes the starburst in the C's counter, the K crotch fan, and both of the M's fans. Measured, becker's E goes from bars pivoting 75 deg to bars pivoting 1.4 and 4.2 deg.

The junction PATCH itself — the part the approach is named for — is the smaller contribution. Made as a residual (lump minus the ribbons actually emitted) it is well-behaved: it cannot take work from strokes doing it correctly, and a clean T produces no patch, which is what keeps the pinned fixtures green. What it buys is the corners that the removed twigs used to reach.

Honest limits: the scorecard is a wash (+0.24 mean, one design down 0.4); hotel_fremont_patch and becker_chest_small are visually unchanged, fans and all; and my "is this twig part of the lump" gate (>=4 arms or >=2 dead ends) is calibrated on exactly two observed populations and is the weakest part of the change — folding EVERY corner twig gives a strictly better decomposition on becker's E (a straight stem and three straight bars, none over 22 deg) but takes E_LETTERFORM's flush corner out of satin and into the patch, which test_stem_free_end_reaches_its_own_flush_corner reads as bare fabric. I measured both settings across the five designs and they are within noise of each other (mean 68.8 either way), so I shipped the one that keeps the pin and documented the other in the source.

What this lane rules out for others: (1) no ratio of junction radius to arm half-width can classify a junction as a lump — a right-angle meeting of equal ribbons is intrinsically sqrt(2) wider, so the clean T and a bold corner are the same measurement; coverage is the only discriminator that works. (2) Trimming arms back to make room for a junction element is not needed and not helpful. (3) A junction fix alone will not rescue small text; hotel_fremont's FREMONT and becker_chest_small need a treatment-selection answer (fill vs satin), not a better decomposition.

### Risks the lane self-reported

- The twig-fold gate (junction has >=4 arms OR >=2 dead ends) is fitted to two observed cases — becker_lc_large's E corners and the E_LETTERFORM fixture. It is the least principled line in the change and I expect it to mis-classify on artwork neither of those resembles. The alternative setting is documented in the source next to it.
- Satin shapes now emit FILL runs. Two existing tests broke on that alone (a gradient fill-angle instrument and a forced-satin override check) and I fixed them with a '<shape>-junction' shape_id suffix. Anything else downstream that groups runs by shape_id, or assumes a satin shape yields only satin, is at risk in the same way and I have only found the two the suite covers.
- Reading arm direction from outside the blob changes weld decisions on EVERY 3+-arm junction in the corpus, not just the ones I inspected. I verified the M, both E's, and the whole five-design scorecard, but this is a global behaviour change validated on five designs.
- The patch is a tatami fill next to satin columns. On real fabric that is a sheen/texture change at every bold junction, which no raster scorecard can see. A sewout is the only way to know whether it reads as a professional junction or as a patch.
- hotel_fremont_patch scores 0.4 lower than baseline. I could not attribute it — the visual is essentially identical before and after — so it may be raster/registration noise or it may be a small real regression on dense small text.
- _junction_patches does a shapely union/difference per shape over every emitted column's ribbon. It is fast enough on the corpus (prep unchanged at 5-15 s per design), but it is O(strokes) polygon boolean work that did not exist before, and a pathological shape with hundreds of strokes could be slow.
- Coverage of the black letter layer looks slightly patchier in places in the becker renders (E's middle bar, R's bowl) even though the cov metric ticked up. I did not chase this down.

---

## APPROACH D — route junction-dense letterforms off satin onto a fill

**Verdict: PARTIAL**  ·  commit `1d5d283 (branch worktree-wf_58fa9b5d-287-4, forked from c91ab60)`

### What was built

APPROACH D — route junction-dense letterforms off satin onto a fill, with the routing rule fitted to professional ground truth rather than guessed.

The measurement that drove everything: for every satin-candidate lettering region in the five proof designs I sampled the PRO's local stitch direction per 1mm cell (scorecard.cell_stats) and reduced it inside each region to a length-weighted resultant R of the DOUBLED angles. R near 1 = one single direction across the whole region; R near 0 = direction varies within it. Results: R(pro) = 0.53-0.98 on every multi-stroke region; R(ours) = 0.07-0.34 on the same regions. A satin-columned letter CANNOT score 0.9 — each stroke's crosses run perpendicular to that stroke's own axis, so a 25-stroke region's directions must spread. That is direct evidence the pro did not satin-column these letters; it laid ONE fill at ONE angle (+7 to +25 deg, median 20) per letter. Our 0.07 is the starburst, quantified.

The same measurement FALSIFIED the per-stroke-directional premise I was assigned: sampling the pro's direction against our own per-stroke skeleton tangent gives a mean deviation of 44-52 deg on every multi-stroke region — i.e. no relationship at all to the local stroke axis. I implemented per-stroke directional fill anyway (stroke_territories + _stroke_directional_fill, EMB_LETTERFILL_MODE=stroke) and scored it: worse than BOTH the flat fill and the satin baseline on 4 of 5 designs (70.1 / 63.1 / 57.7 / 63.0 / 66.3), with dir 0.45-0.50 vs flat's 0.64-0.69 and travel collapsing to 0.39-0.60.

Shipped rule (swept, not guessed): an auto-tier satin candidate whose skeleton decomposes into >=3 strokes AND whose ribbon is >=2.2mm wide sews as tatami at 20 deg. Three strokes is the smallest count implying an arm that welding could not weld, and it leaves BAR/O_RING/C_STROKE/T_SHAPE — the archetypes test_satin.py pins as satin — on the satin tier. 2.2mm is the only value on the sweep at-or-above baseline on all five designs.

One non-obvious mechanical finding: the harness enables fill_density_boost, whose second pass runs at angle+90. My first attempt routed letters into that and the score DROPPED (dir 0.60 -> 0.45) even though the letters looked right — the cross pass takes the measured direction coherence straight back to zero. A letterform fill must be single-pass; it reaches the same thread mass by halving its row spacing in one direction.

New files: digitizer/digitizer_core/stage6_letterfill.py, digitizer/tests/test_letterfill.py. Modified: stage7_sequence.py (routing), config.py (letter_fill flag, default True).

### What the renders showed

I read A/B renders (satin baseline vs letterfill, same renderer, same harness config) for FOUR designs. Baselines were regenerated with EMB_LETTERFILL_MODE=off into a separate dir so the comparison is like-for-like.

becker_hat_large — THE FAN IS GONE where the rule fires. Baseline: the grey backing layer is a solid comb of radiating spikes all around its perimeter, and the black E is an unreadable blowout — crosses fanning out of the junctions in every direction, the letter does not read as an E at all; the C is a spray of black spikes around its arc. Letterfill: the grey backing is clean parallel diagonal hatch, the E is a fully legible E built from parallel rows, the C is a clean C. No fan visible anywhere in the crop.

becker_lc_large — same story. Baseline BECKER: spikes radiating off every letter, the E illegible. Letterfill: all six letters read as letterforms with consistent diagonal rows. The black B is unchanged (it is a large solid region already on the fill tier with the density boost, correctly).

mfab_lc — PARTIAL. The thick outer black outline/shadow layer around MF4B went from a radiating comb to clean parallel hatch. But the "4" body and the inner bowl shapes STILL FAN — they measure below the 2.2mm width floor and were not diverted. Zoomed in, those inner shapes look identical to baseline.

hotel_fremont_patch — NO CHANGE AT ALL. Byte-identical to baseline. Every letter there measures 1.2-1.9mm wide, under the width floor, so nothing diverts. FREMONT is still the same garbled mass of fanned satin the defect report describes. I verified this by eye, not just by the equal score.

becker_chest_small — PARTIAL. The grey backing layer is fixed (spikes -> clean hatch), but the black B/E/C letters themselves are STILL radiating starbursts in the letterfill render. Only +1.0 score, and the render says why.

Honest summary of what I SAW: this fixes the fan completely on wide (>=2.2mm) bold letterforms — which is BECKER's large lettering and the heavy outline layers — and does literally nothing for anything narrower, which is most of hotel_fremont, mfab's "4", and becker_chest_small's black letters. It is not a fix for the defect as a whole.

### Numbers

```
Harness: PRO_PARITY_OUT=/tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/lanes/D-fill-fallback, prep_all.py then scorecard.py per design. Baseline reproduced exactly at c91ab60 before any edit.

design                 before   after   delta
becker_lc_large         72.9  -> 75.6   +2.7
becker_hat_large        69.7  -> 73.5   +3.8
hotel_fremont_patch     57.7  -> 57.7    0.0  (byte-identical, nothing diverted)
mfab_lc                 71.5  -> 72.8   +1.3
becker_chest_small      71.6  -> 72.6   +1.0
mean                    68.68 -> 70.44  +1.76

Component moves on becker_lc_large: cov 0.91->0.91, dir 0.60->0.68, typ 0.55->0.59, den 0.77->0.71, und 0.76->0.77, trv 0.84->0.92. The gain is direction and travel; density gives a little back.

Calibration sweeps (all five designs, same harness):
  min ribbon width  lc_lg  hat_lg  fremont  mfab  chest
    0.0 / 2.0        75.6   73.5    55.8    68.5   72.6
    2.2 (shipped)    75.6   73.5    57.7    72.8   72.6
    2.45             75.6   73.5    57.7    73.0   70.0
  mode=stroke (per-stroke directional, the assigned hypothesis):
                     70.1   63.1    57.7    63.0   66.3   <- worse than baseline
  row scale 0.7      73.6   71.5    57.7    71.9   70.5
  row scale 0.5 (shipped) as above
  row scale 0.4      76.8   75.1    57.7    73.4   74.2   <- REJECTED, see risks

FULL SUITE: /home/user/EMB-Bot/digitizer/.venv/bin/python -m pytest -q
  7 failed, 1140 passed, 3 skipped in 1064.90s (exit 1)
  = exactly the documented baseline. 5 tesseract/OCR-dependent (test_ocr_gate, test_ocr_suggest x2, test_pipeline OCR subline, test_service OCR payload) + 2 platform-mismatch goldens on photo/enthusiast_logo.png.
  I verified the 2 goldens are NOT mine: re-ran both with EMB_LETTERFILL_MODE=off, both still fail; and instrumented the benchmark logo at target_width_mm=90 — ZERO of its regions divert (the two 2.15mm candidates sit under the 2.2mm floor). Zero new failures.
Targeted: tests/test_satin.py + test_textcluster.py + test_letterfill.py = 76 passed. All four pinned over-correction fixtures (T_SHORT_STEM, T_SHAPE, Sf5200f3f, test_flat_lane_starburst_shapes_correctly_flip_to_fill) pass — they call satin_shape directly or run the pipeline on shapes the rule does not touch.
```

### Summary

Approach D works on the half of the defect it can reach, and I can prove both halves.

What it establishes as a finding independent of my patch: the professional corpus does NOT satin-column these letters. Direction coherence inside each lettering region measures R=0.53-0.98 for the pro against 0.07-0.34 for us. A satin column cannot produce a high R on a multi-stroke letter, so the pro used one fill at one angle. That reframes the defect: our fan is not only a stub-width bug, it is the wrong TIER for these letterforms.

It also falsifies the specific premise I was handed — that pro fills read as letterforms because each stroke follows its own axis. The pro's direction versus our per-stroke tangent deviates 44-52 deg, i.e. no relationship; and implemented and scored, per-stroke directional fill is worse than the satin it replaces on 4 of 5 designs. If another lane is considering per-stroke direction, this rules it out with numbers.

What ships: +1.76 mean, all five designs at-or-above baseline, and the fan visually eliminated on wide bold letterforms (becker_hat_large's E goes from unreadable to clean). What does not: everything under 2.2mm ribbon width is untouched — hotel_fremont_patch renders byte-identical and its FREMONT is still garbled, mfab's "4" still fans, becker_chest_small's black letters still fan. Filling those anyway makes the score worse (min width 0.0 costs 2-3 points on both). So this is a real partial fix with a hard, measured boundary, not a general answer to the starburst.

I declined a further +1.3 that was available. Row scale 0.4 scores better on every design, but machine.py's own comment states a sub-0.2mm single-direction pass is a pucker risk and is precisely why the shipped density boost uses two crossed passes; 0.4 puts letters at 0.16mm with nothing measured behind it. I kept 0.5, which lands on 0.20mm — the same number the corpus band already committed to.

### Risks the lane self-reported

- DENSITY IS SEW-OUT GATED, NOT SETTLED. The letterform fill reaches 0.20mm effective pitch in ONE direction; machine.py's FILL_DENSITY_BOOST comment reaches the same 0.20mm with two CROSSED passes specifically so no single direction carries every penetration, citing pucker/Euler-column risk. I could not arbitrate this from the corpus: a pro letter's footprint carries an outline, an underlay and often a shadow layer over its fill, so thread-per-area there measures 0.08-0.15mm and is not a row pitch at all. This needs a physical sew-out before shipping. If it puckers, drop LETTER_FILL_ROW_SCALE to 1.0 — but note that at 1.0 the change scores BELOW baseline on 3 of 5 designs (71.6/70.1/54.9/65.9/68.6), so the fix and the density are load-bearing together.
- STITCH COUNT RISES 23-31% (becker_lc_large 12548 -> 15474 against the pro's 11274; hat 12949 -> 16920 against 12356). We now overshoot the pro's own count by ~37% on becker. The scorecard's density component does not see this because it normalises by solid area. Real cost in machine time and thread.
- THE 20-DEGREE ANGLE IS A CORPUS MEDIAN, NOT A DERIVATION. Measured per-design the pro sits at +14 (becker_lc), +14.5 (chest), +22 (hotel), +13.7 (mfab) — clustered but not identical, and hotel/mfab have regions at -14 and +43. A constant 20 deg is right on average and wrong per design. The principled version derives it from the design's own text baseline plus the pro's ~20 deg offset; I did not build that, and a design whose lettering runs at 20 deg would get rows parallel to its own stems.
- THE RULE IS FITTED TO FIVE DESIGNS. n_strokes>=3 and width>=2.2mm were swept on becker_lc_large / becker_hat_large / hotel_fremont_patch / mfab_lc / becker_chest_small only. The wider corpus (prep_all.py lists ~20 designs) was not scored, and 2.45 already shows the failure mode — it splits becker_chest_small's word between the two tiers, which is worse than either tier alone. A design whose letters straddle 2.2mm will sew half satin, half fill, and look inconsistent.
- letterform_metrics runs extract_strokes (rasterise + medial_axis) on every satin candidate, and satin_shape then runs it AGAIN for the ones that stay satin. Measured cost is small on this corpus (+0.4s/design) but it is duplicated work on the hot path and should be threaded through rather than recomputed.
- TWO PRE-EXISTING GOLDEN FAILURES MASK THIS SHAPE OF CHANGE. photo/enthusiast_logo.png's byte-identical golden already fails on this platform, so it cannot catch a letterfill regression there. I verified by instrumentation that zero of its regions divert today, but that guard is gone for future edits to the rule.
- THE stroke MODE IS DEAD CODE ON A LIVE PATH. stroke_territories and _stroke_directional_fill ship behind EMB_LETTERFILL_MODE=stroke, measured worse and kept only as the falsified hypothesis's evidence. If that is not wanted in the tree it should be deleted rather than left reachable by an env var.

---

## APPROACH E — decompose satin columns from the OUTLINE instead of the medial axis

**Verdict: NO**  ·  commit `4540225 (on branch worktree-wf_58fa9b5d-287-5, forked from c91ab60; tree clean)`

### What was built

APPROACH E — decompose satin columns from the OUTLINE instead of the medial axis. New module `digitizer_core/stage6_railpair.py`: (1) resample every ring (exterior + interiors) at 0.25 mm with smoothed inward normals — raw per-sample normals on a raster-traced outline swing +-45 deg and shatter every run; (2) shoot each sample's inward normal across the shape (vectorised numpy ray/segment intersection) and keep the first hit only when the far wall FACES BACK (dot <= -0.87) and the gap is within SATIN_MAX_WIDTH_MM — that gap IS the column's true cross-section, so no distance transform is ever queried; (3) group consecutive samples whose partners walk the far rail backward together into maximal runs (a junction ends a run on its own, nothing to weld); (4) claim runs longest-first so each ribbon is emitted once; (5) emit the zigzag at stations chosen where EITHER rail has advanced one spacing, reusing the shipped `_short_stitch_guard`, `_split_points` and min-cross filter unchanged. `satin_shape` gained an `EMB_RAILPAIR=<coverage threshold>` route that delegates to it and hands whatever the pairing did NOT cover back to the medial path as its own residual polygon. Route unset = byte-identical to shipped (pinned by test).

### What the renders showed

I read renders for 3 designs plus per-letter debug renders. WHAT I SAW:

becker_lc_large "E" (S0cdd6202), per-letter render medial vs rail-pair (Ehyb_becker_lc_large_S0cdd6202_h1.png): this is the clearest positive. MEDIAL: the three horizontal bars are sewn as skewed diagonal fans and the stem's column radiates from a point at its lower-left — textbook wedge/starburst. RAIL-PAIR: all three bars become clean, evenly spaced, genuinely perpendicular vertical zigzag columns, fan completely gone on the bars. BUT the stem is untouched — the pairing found nothing there, the residual goes back to the medial path, and it still fans exactly as before. So the letter as a whole still reads as a starburst.

becker_lc_large full design, C/E/K crop (AB_becker_CEK.png), baseline left vs rail-pair right: fans still plainly visible on both. The C's counter still radiates spokes; the K's junction still sprays. No visible improvement at the design level.

mfab_lc "P"/"4" crop (AB_mfab_P4.png): the P's top bar and the right side of its bowl are visibly more regular under rail-pair (an even comb where the baseline is a slightly skewed one), but new fan artifacts appear at the upper-left and there are horizontal runs lying across the bowl's counter (the route has no needle-down travel graph, so inter-column hops surface as visible drags/jumps).

hotel_fremont_patch, HOTEL/FRE crop (AB_fremont.png), baseline top vs rail-pair bottom: clearly WORSE. The "O" of HOTEL disintegrates from a solid dense ring into a radiating starburst of spokes; the T/E/L arms fan and thin; the horizontal rule above goes from a continuous dense band to a patchy comb with a break. Cause: ~1.9 mm strokes on a raster-traced outline give no stable normal at a 0.25 mm sample.

Direct per-shape debug render of FREMONT (Ehyb_hotel_fremont_patch_S9a48e915_h3.png): rail-pair coverage 18.8%, 33 fragmented satin runs vs the medial path's 15 — visibly more broken, not less.

VERDICT: a score gain would not have redeemed this, and there was no score gain. The fan survives on every design; on one design it gets worse.

### Numbers

```
Baseline reproduced exactly on this worktree before any change (becker_lc_large 72.9, becker_hat_large 69.7, hotel_fremont_patch 57.7, mfab_lc 71.5, becker_chest_small 71.6; mean 68.7).

WITH THE ROUTE ON, EMB_RAILPAIR=0.15 (the run left in /tmp/.../scratchpad/lanes/E-outline-pairs):
  becker_lc_large      72.9 -> 70.8   (-2.1)   cov .91->.90 dir .60->.57 typ .55 den .77->.76 und .76->.74 trv .84->.78
  becker_hat_large     69.7 -> 68.6   (-1.1)
  hotel_fremont_patch  57.7 -> 56.5   (-1.2)
  mfab_lc              71.5 -> 72.7   (+1.2)
  becker_chest_small   71.6 -> 68.7   (-2.9)
  mean                 68.7 -> 67.5   (-1.2)

WITH THE ROUTE ON, EMB_RAILPAIR=0.80 (only near-perfect ribbons routed):
  72.9 / 69.7 / 57.1 / 71.5 / 71.4, mean 68.5 (-0.2) — i.e. so few shapes qualify that it is baseline, and the few that do lose 0.6 on hotel_fremont_patch.

WITH THE ROUTE OFF (shipped default): 72.9 / 57.7 / 71.5 on the three I re-scored — identical to baseline to the tenth, confirming the change is inert unless the env var is set.

PYTEST, full suite, one run at the end: 7 failed, 1140 passed, 3 skipped (17m28s). Same 7 pre-existing failures as the documented baseline (5 tesseract-dependent OCR, 2 platform-mismatch goldens: test_flat_lane_byte_identical enthusiast_logo and test_stage2_photo_segment enthusiast_logo). Baseline was 7 failed / 1135 passed; the +5 passes are the new tests/test_railpair.py. ZERO new failures. Targeted tests/test_satin.py + tests/test_textcluster.py: 71 passed (T_SHORT_STEM, T_SHAPE, Sf5200f3f and the flat-lane starburst fixture all intact).
```

### Summary

Approach E does not work, and the reason is structural rather than a tuning miss — that is the lane's result.

The mechanism is sound where it applies. Pairing opposing outline stretches gives a column whose width is a genuine anti-parallel cross-section, never an omnidirectional clearance read inside a junction blob, and the crossbar stubs that the medial path turns into wedges come out as clean parallel ribbons. becker_lc_large's "E" is the proof: its three bars go from diagonal fans to correct vertical zigzag.

It cannot cover a letterform. Measured area-weighted rail-pair coverage of satin-classified regions: becker_lc_large 56.4%, becker_hat_large 56.8%, hotel_fremont_patch 53.4%, mfab_lc 61.5%, becker_chest_small 57.7% (mean 57.2%). Per-boundary-sample census on becker_lc_large: 59% of samples pair, 30% hit a wall that faces away (a different arm of a junction), 11% face back but are further apart than satin can sew. The cause is the letterform, not the algorithm: in a bold glyph the strokes fuse into slabs, so the stem of an "E" has NO wall facing its left edge — the nearest facing surface is the far side of the letter, ~10 mm away. Outline pairing finds exactly the arms the medial path botches and misses exactly the arms it handles fine.

Three attempts to close the gap, all measured:
1. Loosening the gates. Sweeping to 9 mm reach and 120-deg-opposed walls — well past anything satin can physically sew — still only reaches 74.9%. Structural.
2. Recursing on the residual. The appealing idea (remove the bars and the stem's right edge is finally exposed) fails: the residual is a stem with column-shaped bites out of it, its new walls are the eroded column ends, and round 2 pairs them across the piece's diagonal, laying two long columns crossing at ~30 deg. Visibly worse than round 1 and worse than shipped. `_MAX_ROUNDS = 1` with that written down.
3. Hybrid — rail-pair columns plus the medial path on the residual. This is what the scored runs use. Net -1.2 mean, and the fan survives because the residual is precisely the blob that was fanning.

One honest caveat on the numbers: roughly half the loss is not column geometry. The route has no equivalent of `_build_travel_graph`, so every inter-column hop is a jump/trim instead of a needle-down walk; that alone takes `travel` from 0.84 to 0.78 on becker_lc_large (~0.9 of the 2.1 points). Direction agreement moved only 0.60 -> 0.57. The decomposition itself is roughly a wash-to-slightly-negative, not a collapse — it simply does not reach the defect.

What this rules out for the other lanes: the starburst is NOT primarily a width-measurement error. Rail pairing supplies a perfect, junction-immune width for every column it finds, and the design still fans, because the fanning geometry is the part of a bold glyph that has no rail pair to measure. Any fix has to decide what to DO with the fused slab at a junction — sew it as its own element, or fill it (which is what the pro does for becker's MARINE) — not measure it more accurately.

The code is committed off by default: `EMB_RAILPAIR` unset leaves `satin_shape` byte-identical to the shipped medial path, pinned by `tests/test_railpair.py`, and confirmed by re-scoring three designs to the same tenth as baseline.

### Risks the lane self-reported

- The route ships OFF and is env-var gated (EMB_RAILPAIR), so the only default-path change is a refactor: satin_shape's body moved verbatim into _satin_shape_medial and satin_shape became a dispatcher. Full suite and the pinned satin fixtures confirm identity, but that refactor is the one thing a reviewer should eyeball.
- The gate is an environment variable, not a PipelineConfig field. Deliberate (no caller should reach a prototype by accident) but it means the route is invisible to config-level review and could be switched on in a deployed process by an env leak. If this survives, it should become a config flag or be deleted.
- satin_shape_railpair accepts and silently ignores end_cutback_mm (push comp, Law 24) and use_shapefield. Documented in its docstring, but a future caller wiring directional_comp through this route would get no push compensation and no warning.
- _pair_opposites allocates (chunk x n_samples) float64 arrays; at 256 x ~6000 samples that is ~12 MB per intermediate, five live at once. Fine for letterforms in this corpus, but a very large single region (a 900 mm2 slab at 0.25 mm sampling) would push it, and there is no guard.
- The residual pass calls back into the medial path on polygons produced by a buffer(-o).buffer(1.6o) open/close. That morphology is tuned by eye on a handful of glyphs, not swept; on a different shape it could hand the skeletonizer a piece that is thinner or more ragged than intended.
- coverage() runs a shapely unary_union over one quad per station for every candidate shape on every satin call when the route is on. That is why prep time roughly doubled on becker_lc_large (4.3s -> 6.4s). Irrelevant while off, but it is not a cheap gate.
- The corpus art is reconstructed from professional stitch files, so a bold E's notches close to a V that the original vector art probably does not have. That makes the coverage ceiling I measured (36% on that E) somewhat pessimistic versus true vector artwork - the idealised E in the new test reaches 72%. The qualitative conclusion holds either way (the stem still pairs over only a third of its height), but the exact percentages are corpus-specific.