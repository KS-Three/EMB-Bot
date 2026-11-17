# keyline_fragment_drop, narrowed: every run it moves (2026-11-17)

Original | BEFORE (flag OFF) | AFTER (flag ON), same size and frame.

**Moved: 2 of 35 runs, both pictured, neither worse.** The 9 prime-grader pro
jobs (`tools.prime_grader.population()`, each at its own size and garment via
`tools.pro_pair.request`) and the 26 `tools.corpus_scorecard.FIXTURES` at the
Studio request (80 mm, `left_chest`), compared by md5 of `design["stitches"]`.
All 9 pro jobs are stitch-identical OFF vs ON, so no pro render is committed
(`tests/test_no_new_pro_renders`).

| picture | stitches OFF -> ON | read by eye |
|---|---|---|
| `fx_drone_render_pair.png`, spots 1-3 (`drone_render`, 80 mm) | 18,337 -> 18,267 | **Better, what Kent asked for.** The dark bars on the bottom of the P (two) and the R's leg are gone; everything else is the same. |
| `fx_drone_render_C_foot_with_merge_chroma_guard.png` | 20,759 -> 20,652 (guard ON both) | **Better.** The C's foot bar goes too when `merge_chroma_guard` is ON. |
| `fx_logo_bridge_bar_pair.png`, spot 1 (`logo_bridge_bar`) | 10,827 -> 10,813 | **No visible change at the size sewn; a stray black chip on the yellow, beside the teal lettering, is gone.** A 0.16 mm2 `dot_rung` speck. |

Worse: **none by eye.**

## What the rule now needs (all of it, on top of the built rule)

1. The band lies on its host's OUTER outline, not in a hole of it (more of its
   edge on the host's hole rings than on the rest: a drawn line inside a
   field). **To a T's speed lines** all hug the white fill's hole rings
   (41-55% of their outline, 0% on the outer ring): 6 were deleted by the built
   rule, 0 now.
2. It is not the design's darkest ink in its own art ink (`bevel_fold`'s own
   rule: the tee's shadow and outline are drawn). A rescued or cap-merged
   piece is not protected, as there.
3. It is darker than its host by more than `bevel_fold.DARKEST_L_TOL` (5 L*);
   a 2 L* "darker" sliver was Golden Tee's F.
4. It is a hairline IN THE ART: at most `HAIRLINE_SRC_PX` (3.0) source pixels
   wide. Measured: the Drone's remnants are 1.3-1.9 source px; Golden Tee's
   black bar under the F's arm is 0.53 mm = 15 px (rescued and cap-merged, so
   rule 2 alone left it dropped). The 3.0 sits between, a count of the art's
   pixels, not a fabric number (ROADMAP gate 1 does not apply).

Measured per case (built rule -> narrowed): Drone `drone_render` 4 bars -> 3
(P twice, R; the fourth, a band in a hole of a tree shape, stays); with the
guard ON the narrowed rule drops 4 (P twice, R, C); To a T hat 6 deleted -> 0; Golden Tee hat 3 -> 0;
`precision_drone` hat job: the narrowed rule drops nothing there (nor does it with the hairline bound removed), so stitch-identical.

The pro-job pictures of To a T and Golden Tee (before the narrowing) are not
committed; they are pro renders.

Not done, as ordered: the default is still OFF. See the PR body for the tests
run with the flag ON.

## Tests with the flag ON (default set True locally, then put back)

Every `digitizer/tests` file mentioning drone_render, golden_tee, goldentee,
toat, logo_bridge, bridge_bar, bridge_hat or bridge_lc (153 files by the wider
"bridge" match; 1,764 tests by the narrower match): **1,754 passed, 7 skipped,
5 xfailed, 6 xpassed, 1 failed** in 25m37s. The one failure is
`test_stage2_photo_segment::test_flat_and_gradient_lanes_still_match_golden_after_photo_dispatch[photo/enthusiast_logo.png]`:
a stage-2 snapshot of `enthusiast_logo` (stitch count 2337 vs golden 2351), one
of the three platform-numerics golden reds CI deselects by node ID.
(`enthusiast_logo` is not among the 2 movers, which were measured at the Studio
request; this snapshot runs another config, so the flag does reach it there.)
