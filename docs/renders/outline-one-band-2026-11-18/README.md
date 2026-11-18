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
| becker_hat_large | 16287 -> 16289 | 164 -> 246 | 20 -> 21 | 20 -> 21 | satin 5 -> ~56, travel 8 -> ~35, underlay 7 -> 7, fill 4 -> 4, run 0 -> 1 |
| fx_becker_marine_logo (80 mm) | 10855 -> 10500 | 137 -> 183 | 14 -> 20 | 14 -> 20 | satin 5 -> ~37, travel 7 -> ~14, fill 2 -> 2 |

What is new: ONE satin loop on the band's outer ring (last), one satin column per stem
(the B/E stem is one 20 mm column, the E/R stem another, a third at the lower-right), the
hole loops cut to the strips neither covers (split into arcs: that is where the run
count and the trims come from), and travel inside the band under the outer loop.

## By eye

Better: the border passes the dip as one band, the stem is one column, no pile of two
loops (before: two columns side by side down the stem, both fanning into the V). The
E/R join is the same. **Worse:**
* **Trims +1 on Becker large (20 -> 21, jumps 20 -> 21); +6 at 80 mm (14 -> 20).**
  First build: +12 on Becker large. The needle walks between the pieces inside the band
  (`travel_path` along the band moved in 0.35 mm, else along the outer loop's centre line,
  never over a finished stem), under the outer loop sewn last; stems nearest-first; the
  outer loop is entered where the loops it replaces would have ended. What is left: a stem's
  tail sewn as a run, a far hole arc or two, and the 80 mm design's extra arcs.
* A few thin black strips (0.5-1 mm satin arcs) along the face edge where the band is a
  little thicker than the outer loop reaches; they read as lines at print size.
* A tiny white slit beside the B/E stem's lower column (closeup 3) and at the E/R
  stem's bottom turn.
* At the V the outer loop's crosses still turn with the band's normal (they bunch in the
  notch); the pro's stay near-square to the band. Closer than before, not the pro's.

## Related tests with the flag forced ON (227 files, final build)

3,985 passed, 4 failed. With the flag OFF (the default) all pass. The 4:
* `test_flat_lane_byte_identical[enthusiast_logo]`: the known golden red (CI deselects it).
* `test_outline_one_band::test_field_defaults_off`: the default forced for the run.
* `test_silhouette_underfill_panels` (2): md5 pins of Becker / MFab stitch bytes (a flip
  would re-pin them).
Two guard figures moved the wrong way in earlier builds and are now back:
* `test_wide_columns` fold-guard test: `coverage_max` on Becker 114 mm was 6.14 OFF, 6.71 ON
  (warn line 6.667): the outline's exit point had re-ordered MARINE's letters. The band now
  ends where the loops it replaces would have ended: the order is the same, **6.14 OFF, 6.39
  ON**, no cell over the line (`outline_band._loops_exit`).
* `test_border_from_outline` thin-ring test: an outer-loop cross grazed a face corner; the far
  end is now pulled back to the face's edge (`_keep_out_of_faces`, own test).
* `test_run_spans` design-cap test: with the flag ON the cap has no satin-arc (BORDER-kind)
  stitch, the outer loop sews that edge; the test asserts the emitter only with the flag OFF
  (its role assertion holds either way); bare area is not worse (below).

**The design cap with the flag ON** (director item 3): bare area is not worse, it
falls. Becker at 80 mm in that test's config: uncovered area 10.5 -> 3.1 mm2, worst patch
3.3 -> 1.8 mm2, 66 -> 119 small patches (all under 1.9 mm2). The cap keeps its bean and
loses its two satin arcs (the outer loop sews the edge): `design_cap_edge_OFF_ON.png`,
the B's left edge, flag OFF left, ON right. `test_run_spans` now asserts the satin-arc
emitter only when the flag is OFF; its role assertion (the contract) holds either way.
