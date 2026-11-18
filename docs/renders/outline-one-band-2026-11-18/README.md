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

## ALL 18 tripwire jobs (every placement) + the 26 fixtures, OFF vs ON (round 2, 2026-11-18)

44 runs by stitch md5: **6 moved, 38 byte-identical** (OFF = `origin/main`'s output; round 2 changes the ON arm only).
Needle-up = the straight gap the needle flies at each lift (`pro_baseline.needle_up`'s rule, from the stitch list).

| run | stitches | trims | jumps | needle-up mm |
|---|---|---|---|---|
| becker_hat_large | 16,246 -> 16,154 | 19 -> 23 | 20 -> 24 | 489.6 -> 706.8 |
| becker_lc_large | 14,802 -> 14,432 | 13 -> 24 | 14 -> 25 | 213.8 -> **574.8** |
| becker_hat_small | 10,319 -> 9,766 | 10 -> 21 | 14 -> 25 | 306.3 -> 357.9 |
| becker_chest_small | 10,156 -> 9,627 | 9 -> 18 | 13 -> 22 | 303.5 -> 291.4 |
| becker_beanie | 13,653 -> 13,121 | 13 -> 22 | 15 -> 24 | 385.0 -> 391.4 |
| fx_becker_marine_logo (80 mm) | 10,826 -> 10,282 | 13 -> 21 | 14 -> 22 | 380.4 -> 364.9 |

mfab_lc, which moved in round 1, does not move now (its stem test no longer passes at that placement). Pictures:
`<run>.png`, `<run>_closeup.png` for the six.

### What round 2 changed (director's list, 11-18 06:33)
1. **Stray line.** The diagonal line near the K/E/R lower area was a TRAVEL run of 25 mm that ran through the
   E's white face (the walk along the band's inset ring cut across a face corner); a travel that runs more than a
   third of a millimetre through a face is no longer sewn, the needle lifts (`_scrub_face_travel`). No thread now
   crosses a white face in the Becker large render.
2. **Stems edge to edge.** A stem is grown 0.3 mm so it reaches both faces; the C/K and K/E stems are NOT thinner
   than the art: the art's band between those letters is 0.55-1.1 mm (measured, `faces 2-3 min gap 0.55`), a satin
   column of that width reads as a hairline in both arms; OFF's two overlapping loops make it look heavier.
3. **The V.** The outer loop's cross direction is read over three times the stretch (`TANGENT_SCALE`), so the
   crosses stay near-square to the band through the notch instead of fanning; the stem butts the band's lower edge.
4. **E/R flare** and a wider outer reach (3.6 mm, to absorb the face-edge strips) were tried and dropped: both
   broke the stems into pieces (visible gaps) and raised trims.
5. **Trims (target +2 at 80 mm): NOT met** (80 mm: 14 -> 22). The cost is structural: the stems and the outer loop
   cut each face's loop into 20-30 arcs, and each far arc is a lift. Filling those wedges instead was tried and
   made it worse (27 trims).

### Whole-word read at print size, ON vs OFF (Becker 102 mm, 76 mm)
102 mm: the outer contour is one smooth band (OFF scallops where each letter's loop ends), stems and the V are
cleaner; the stems between C/K and K/E read as thin as the art's hairline gaps. 76 mm: a rougher band edge and a
small white notch at the top of the K remain. **Not clearly better than OFF across the placements, and it
costs 4-11 trims and up to +361 mm of needle-up: leave OFF as built.**

## Related tests with the flag forced ON (227 files, round 2)

With the flag OFF (default) all pass. ON: 1 NEW guard failure, plus the known ones.
* **NEW: `test_underfill_small_size::test_mfab_hat_size_sweep_order_and_grade[30.0-default]`: MFab hat at 30 mm
  (default class) grade B -> C (floor B).** The flag moves MFab at 30 mm, a size the tripwire jobs do not cover:
  stitches 2,989 -> 2,573, trims 12 -> 17, `satin_short_fraction` 0.263 -> 0.444, raw score 76 -> 64. So
  "MFab is untouched" holds at its tripwire size (105 mm) and not at 30 mm.
* Known/expected: the enthusiast golden, `test_field_defaults_off` (the forced default), and the two
  `test_silhouette_underfill_panels` md5 pins.
* Passing ON now (they failed in earlier builds): `test_wide_columns` fold guard (coverage_max 6.14 OFF,
  6.39 ON), `test_border_from_outline` thin-ring test, `test_run_spans` (asserts the satin-arc emitter only
  with the flag OFF).

**The design cap with the flag ON** (director item 3): bare area is not worse, it
falls. Becker at 80 mm in that test's config: uncovered area 10.5 -> 3.1 mm2, worst patch
3.3 -> 1.8 mm2, 66 -> 119 small patches (all under 1.9 mm2). The cap keeps its bean and
loses its two satin arcs (the outer loop sews the edge): `design_cap_edge_OFF_ON.png`,
the B's left edge, flag OFF left, ON right. `test_run_spans` now asserts the satin-arc
emitter only when the flag is OFF; its role assertion (the contract) holds either way.
