# `outline_one_band` OFF vs ON — 2026-11-18

Fault: `L_becker_hat_large`, the outline where it dips between the B and the E (pin
x 21.0 y 8.5 mm) and the E/R join (x 78-81, y 4-5). Design and the pro's construction
(numbers and words only): `docs/outline-one-band-2026-11-18.md`. Flag built OFF.

## The 35 runs (md5 of `design["stitches"]`, flag OFF vs ON)

9 committed pro jobs at their own size + 26 `corpus_scorecard.FIXTURES` at the Studio
request (80 mm, `left_chest`): **2 of 35 moved, 33 byte-identical.** OFF equals the
earlier OFF baseline (same tree minus this flag) on all 35. **Both movers are pictured**
(`<run>.png` = ORIGINAL | BEFORE | AFTER; `<run>_closeup.png` = BEFORE left, AFTER right,
the B/E dip, the E/R join, the lower B/E stem).

MFab hat, Hotel Fremont, Gaulke, Tires, Toat and the other 28 do not move: the gate
(two or more bodies and at least one stem) is not met, or no stem survives the tests.

## What changed in the plan (read from the plan, not only the picture)

Shapes: the same shape ids in both arms, none retagged, merged or dropped. Only the
outline shape (`S92f2350b`: 1201 mm2, 5 face holes at 102 mm) is sewn differently.

| | stitches | runs | trims | jumps | outline runs by kind OFF -> ON |
|---|---|---|---|---|---|
| becker_hat_large | 16265 -> 16195 | 182 -> 268 | 19 -> 20 | 20 -> 20 | satin 5 -> ~56, travel 8 -> ~35, underlay 7 -> 7, fill 4 -> 4, run 0 -> 1 |
| fx_becker_marine_logo (80 mm) | 10672 -> 10403 | 156 -> 195 | 15 -> 19 | 16 -> 22 | satin 5 -> ~37, travel 7 -> ~14, fill 2 -> 2 |

What is new: ONE satin loop on the band's outer ring (last), one satin column per stem
(the B/E stem is one 20 mm column, the E/R stem another, a third at the lower-right), the
hole loops cut to the strips neither covers (split into arcs: that is where the run
count and the trims come from), and travel inside the band under the outer loop.

## By eye

Better: the border passes the dip as one band, the stem is one column, no pile of two
loops (before: two columns side by side down the stem, both fanning into the V). The
E/R join is the same. **Worse:**
* **Trims 19 -> 20 on Becker large (jumps 20 -> 20), 15 -> 19 at 80 mm (jumps 16 -> 22).**
  First build: 19 -> 31. The needle now walks between the pieces inside the band
  (`travel_path` along the band moved in 0.35 mm, else along the outer loop's centre
  line), under the outer loop sewn last, and the stems go nearest-first. What is left:
  the first hole arc (as OFF), two far hole arcs in the E/R stem, a stem's tail sewn as
  a run, and the 80 mm design's extra arcs.
* A few thin black strips (0.5-1 mm satin arcs) along the face edge where the band is a
  little thicker than the outer loop reaches; they read as lines at print size.
* A tiny white slit beside the B/E stem's lower column (closeup 3) and at the E/R
  stem's bottom turn.
* At the V the outer loop's crosses still turn with the band's normal (they bunch in the
  notch); the pro's stay near-square to the band. Closer than before, not the pro's.

## Related tests with the flag forced ON (227 files)

3,978 passed, 7 failed. With the flag OFF (the default) all pass.
* `test_flat_lane_byte_identical[enthusiast_logo]`: the known golden red.
* `test_outline_one_band::test_field_defaults_off`: the default forced for the run.
* `test_silhouette_underfill_panels` (2): md5 pins of Becker / MFab stitch bytes.
* `test_wide_columns::test_the_fold_guard_keeps_a_wide_column_on_a_bend_under_the_warn_line`:
  `coverage_max` 6.14 -> 6.71 against the 6.667 warn line, at ONE cell on a MARINE letter
  (`S3747f7f5`, one hole: the flag does not sew it differently; its entry point moves, so its
  column is re-phased).
* `test_run_spans::test_the_design_cap_keeps_its_own_role_through_the_border_emitter`:
  the Becker fixture's design cap has no BORDER-kind stitch with the flag ON (the outer
  loop covers the edge the cap would have sewn).
No test was pinned OFF; the director has both guard figures.

**The design cap with the flag ON** (director item 3): bare area is not worse, it
falls. Becker at 80 mm in that test's config: uncovered area 10.5 -> 3.1 mm2, worst patch
3.3 -> 1.8 mm2, 66 -> 119 small patches (all under 1.9 mm2). The cap keeps its bean and
loses its two satin arcs (the outer loop sews the edge): `design_cap_edge_OFF_ON.png`,
the B's left edge, flag OFF left, ON right. `test_run_spans` now asserts the satin-arc
emitter only when the flag is OFF; its role assertion (the contract) holds either way.
