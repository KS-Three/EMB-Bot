# Rail dents — defect 23, FIXED, and what the defect actually was (2026-09-03)

Kent picked this after PR #328 from four options (rail dents, the curve-flip
round, a small-lettering tier, the Wisconsin outline). The option text
promised "one whole rail 15% short on every rotated column, in every satin
golden". That was the synthetic-bar reading of the defect; the real-art
reading turned out different, and both are recorded here.

## 1. The claim, and how much of it survived measurement

MASTER_SCOPE defect 23 (recorded 2026-09-03 under the stitch-angle work):
`_rail_points`' `place` puts each rail at the smoothed half-width and shrinks
it to 0.85× when `poly.covers` fails; on a stock 3 mm bar rotated 25° one
whole rail sat at 1.22–1.27 mm against the other's 1.44–1.46. "In every
satin golden."

**Synthetic bars — true.** `tests/test_satin.py::test_rails_of_a_rotated_bar_reach_the_artwork_edge` and its zero-tolerance twin: a 30 × 3 mm bar
at 10/25/45° with an exact centre spine. A rail cast to the measured
half-width lands ON the boundary, and `covers` on a point an ulp outside it
is a coin flip: 29–54% of interior stations dented to 0.85× (one rail at
1.232 vs 1.450 mm at 10° with the spine 0.05 mm off-centre). A micron of
tolerance on the containment check alone: 0% dented, everywhere.

**Real fixtures — the micron alone did almost nothing.** Rail points measured
against the artwork edge (`tools/rail_edge.py`, the signed distance of every
satin penetration to its shape's boundary):

| fixture | stitches | penetrations > 0.1 mm inside the art |
|---|---|---|
| Fremont | 5789 → 5793 | 8.5% → 8.5% |
| drone | 8670 → 8674 | 17.1% → 17.0% |
| ribbon_curve | 1001 → 1003 | 0.4% → 0.8% |
| Becker, ENTHUSIAST, alpha, whitebg, gaulke | unchanged | unchanged |

On a raster skeleton the smoothed width equals the local ray hit to the ulp
almost nowhere, so the coin flip almost never comes up. **The "in every
golden" was extrapolated from the bar** — a measured negative, recorded in
DOCTRINE.

**What real art actually does at those stations.** A census of every
containment miss inside `_rail_points` on the pre-change tree
(`tools/rail_edge.py --ladders`): how far outside the art the rail at the
smoothed width sat on its FIRST miss, and which ladder step it then took.

| fixture | ladders | < 1 µm | < 10 µm | < 50 µm | < 100 µm | < 250 µm | ≥ 250 µm | took the 0.85× step |
|---|---|---|---|---|---|---|---|---|
| Fremont (31 px/mm) | 615 | 10.9% | 42.4% | 32.7% | 8.0% | 5.0% | 1.0% | 76% |
| ENTHUSIAST (11 px/mm) | 498 | 3.2% | 24.9% | 32.1% | 15.7% | 13.7% | 10.4% | 78% |
| drone | 1004 | 5.4% | 21.0% | 32.2% | 15.0% | 14.8% | 11.6% | 68% |
| Becker (4 px/mm) | 744 | 2.0% | 13.3% | 32.4% | 22.2% | 21.9% | 8.2% | 75% |
| ribbon_curve | 254 | 0.8% | 49.2% | 43.3% | 3.5% | 1.6% | 1.6% | 97% |

So per design 250–1000 rail placements overshoot the edge, 70–90% of them by
under 50 µm — at most one pixel — and three quarters of them then retreated
by 15% of the half-width: a 0.15–0.25 mm dent for an overshoot of a few
microns. **That is the real defect 23**: not the ulp, the ladder's first
step being 15% no matter how small the overshoot.

## 2. The fix

`stage6_satin._rail_points` (`_COVERS_TOL_MM` = 1e-6):

- **Containment carries a micron.** `inside = poly.buffer(_COVERS_TOL_MM)`,
  built once per call, is what `place` and the no-hit `fallback` test
  against. Same trap and the same cure as `stitches.SPLIT_TOLERANCE_MM`
  (defect 25, PR #328).
- **An overshooting rail goes ON the edge, along its own normal.** On a
  miss at the smoothed width, `place` intersects the segment from the
  station to the overshooting point with the boundary and takes the nearest
  crossing, skipping anything within 0.05 mm of the station exactly as
  `hit` does (the terminal station sits on the cap). The discrete ladder
  (0.85, 0.7, 0.5, 0.3) is what remains for a ray that finds no crossing.
- **Scoped to the column body.** Taper zones and the terminal stations keep
  the old ladder against the bare artwork, and the refinement's
  interpolated stations inherit their interval's `in_taper`. First measured
  without the scoping: the ribbon's tapered head gained an inserted cross
  whose rail landed 0.157 mm from its neighbour, the short-stitch guard
  pulled it 0.6 mm, and `test_a_satin_free_end_does_not_fan_into_a_starburst`
  read a 1.005 mm same-rail interval at cross 3 — rails placed exactly on a
  converging edge spread by 1/cos(taper) and hand the guard a bunched
  station. The tip's width cap, refinement floor and guard are calibrated to
  the ladder; with the scoping the head is byte-identical to before. **The
  tip is its own question**, below.

Not a physical constant (a micron is under any raster or machine quantum;
the crossing is the artwork's own edge), not a stage-0 change, gates 1–3
clean.

## 3. Measured

Rail points against the artwork edge, pre-change tree (main at 70df648)
against the fixed tree, no pull compensation except ENTHUSIAST's
`left_chest`:

| fixture | stitches | median rail-to-edge (− = outside) | p90 inside | > 0.1 mm inside | max outside | bare fabric |
|---|---|---|---|---|---|---|
| Fremont | 5789 → 5795 | +0.016 → **−0.004** | 0.086 → 0.086 | 8.5% → 8.5% | 0.075 → 0.075 | 4.7 → 4.7 mm |
| ENTHUSIAST @ 93 | 2959 → 2955 | −0.162 → −0.218 | 0.370 → 0.314 | 19.9% → 19.7% | 0.300 → 0.300 | 0.1 → 0.1 |
| drone | 8670 → 8666 | −0.147 → −0.173 | 0.241 → 0.239 | 17.1% → 16.5% | 0.534 → 0.534 | 6.3 → 6.3 |
| Becker | 4421 → **4340** | −0.145 → −0.171 | 0.472 → 0.451 | 24.0% → 22.8% | 0.300 → 0.300 | 0.6 → 0.7 |
| ribbon_curve | 1001 → 999 | −0.237 → −0.279 | −0.079 → −0.200 | 0.4% → 0.2% | 0.300 → 0.300 | 0.0 → 0.0 |
| alpha | 1968 → 1968 | −0.216 → −0.300 | | 0% → 0% | 0.300 | 0.2 |
| whitebg, gaulke | unchanged | | | | | |

The median rail moves 0.02–0.08 mm outward, onto the edge; nothing moves
further outside the art than before (`max outside` is the pull compensation,
unchanged); trims unchanged everywhere. Becker's −81 stitches are spread over
its 29 columns (2–8 penetrations each) with the median cross WIDER on every
one (1.572 → 1.612, 2.263 → 2.304, 4.281 → 4.488 mm) and the satin thread
length flat (3532 → 3510 mm): a rail that alternated between the full width
and 0.85× read as an over-wide interval to the outer-rail refinement, which
inserted stations to fill a zig-zag that is now gone.

Rail smoothness on the emitted satin runs (`tools/rail_edge.py`;
jitter = each rail point's distance from the chord of its two neighbours,
holes = same-rail intervals over 0.8 mm, the starburst test's metric):

| fixture | crosses | median cross | satin thread | rail jitter p50 | same-rail holes |
|---|---|---|---|---|---|
| Fremont | 1149 → 1152 | 0.781 → 0.810 mm | 878 → 902 mm | 0.0120 → **0.0045** | 11 → **5** |
| ENTHUSIAST @ 93 | 687 → 683 | 2.379 → 2.431 | 1510 → 1542 | 0.0421 → **0.0241** | 46 → 41 |
| drone | 1597 → 1594 | 1.465 → 1.488 | 2594 → 2636 | 0.0404 → **0.0258** | 71 → 69 |
| Becker | 1510 → 1471 | 2.045 → 2.053 | 3519 → 3496 | 0.0612 → **0.0378** | 72 → 63 |
| ribbon_curve | 236 → 235 | 2.932 → 3.016 | 677 → 700 | 0.0161 → **0.0071** | 0 → 0 |

The rail jitter halves or better on every fixture — the zig-zag between the
full width and 0.85× was most of it — and the crosses are wider because
they reach the edge.

Time: one boundary intersection per overshoot, 250–1000 per design, against
the two the width measurement already casts per station — Fremont 13.9 →
13.2 s, Becker 2.30 → 2.35 s (best of two, noise).

**What did NOT move, and why.** 8–24% of rail points still sit more than
0.1 mm inside the art on the lettering fixtures, and the fix touched at most
1.2 points of it. Those come from the rail model itself, not the ladder: the
rails are symmetric offsets of the spine at a SMOOTHED half-width, so where
one side's edge is further than the smoothed width the rail sits inside by
the difference (by design — per-station boundary following is the "spray"
the model was built to stop), plus the short-stitch guard's pulls on bends
and the corridor caps at junctions. A "rails follow the edge" model is a
different construction with coverage and pull-comp consequences; recorded as
the open half of defect 23, Kent's call.

## 4. Goldens re-pinned (pre-change-tree discipline)

`tools/recapture_flat_lane_key.py <key> --pre-change-tree <main at 70df648>
--control logo_whitebg.png`: machine OK and control OK on both keys.
`logo_alpha.png` keeps 1968 stitches with its rails ~0.08 mm further out;
`ribbon_curve.png` 1001 → 999. `tests/test_pushcomp.GOLDEN_FLAG_OFF`: both
ribbon entries (1001 → 999 and 1005 → 1001) after the pre-change tree
reproduced all three old tuples on this machine; whitebg byte-identical (its
one column never overshoots). Nothing else in `test_satin`, `test_pushcomp`,
`test_flat_lane_byte_identical`, `test_stages`, `test_textcluster`,
`test_preflight` moved (266 passed, the two platform reds deselected).

## 5. Tests

`tests/test_satin.py`: `test_rails_of_a_rotated_bar_reach_the_artwork_edge`
(10/25/45°: every interior rail point within 0.01 mm of the edge) and
`test_the_micron_is_what_closes_the_dent` (with `_COVERS_TOL_MM` forced to
zero the same bar dents ≥ 20% of its stations — the guard cannot pass
vacuously). The starburst test pins the tip unchanged.

## 6. Open

- **Tips.** Exact-edge rails at a converging tip bunch on the pinched side
  and spread on the open side; the tip machinery (taper cap, refinement
  floor, guard) is calibrated to the ladder. Whether the tip should get the
  clamp with a re-tuned guard is a sew-out question (tip density).
- **The rail model's inside gaps** (section 3) — the larger half of what a
  digitizer would call "the satin doesn't reach the edge".
