# A density and flow instrument built from Kent's own notes - 2026-10-12

PR #842 pooled every labelled eye-pairs sitting (115 judged pairs in scope,
7 logos) and found that no fidelity instrument clears chance against Kent's
eye; only the trim counts do (`trims` +0.28 [+0.12, +0.43], n = 90). It also
noted that he tends to pick the side with more stitches, and that his own
notes talk about density, flow and trims, which nothing measured. Kent's
ruling the same day: build a density and flow instrument from his labelled
notes. This is that instrument and its first scoring. **It is an instrument,
not an engine change: nothing here flips a flag or moves a gate.** ROADMAP
gate 4 holds throughout: no raw agreement figure is computed or printed, only
Cohen's kappa, its bootstrap interval, and the n it rests on.

## The answer

**No new candidate clears chance on both statistics and both intervals. The
one that does is a restatement of trims.** `jumps_per_1000` (needle-up moves
per 1000 stitches) reads +0.53 [+0.19, +0.81] sides only and +0.30
[+0.15, +0.43] with ties in (n = 76, 33 where Kent chose a side), the same
as the recomputed `trims_per_1000` control (+0.55, +0.30), and its picks agree
with the trim picks at kappa +0.72 over 72 pairs: on these designs nearly
every jump is a trim's jump.

**Density, read as thread per area, does not track his picks; the hypothesis
"he picks the denser side" is not supported.** `thread_density` on the shapes
the arm changed reads -0.11 [-0.40, +0.18] sides only (n = 76, 33 decided),
the whole design +0.04 [-0.26, +0.33], and the gap to the professional's own
file +0.10 [-0.30, +0.50] (n = 47, 20 decided). #842's "denser side" was
STITCH COUNT, which is not density. The lean against density comes from the
Column lane: its `after` side sews the letters sparser (rails at 0.80 mm on
density-1007) and he picked it on becker and drone there and on 5 of 6
columns-flip pairs, even where his note says the other side's density is
better (density-1007 becker: *"the before stitch density is better"*, pick
`after`, 4.29 mm/mm^2 against 10.32 on the letters). The sitting that would
separate density from construction, the equal-pitch redraw `full-density`
(7 pairs, 6 `after`), has no stored designs anywhere, so it cannot be scored.

**Two independent leads, neither a finding.**

- `flow_circvar` (the spread of stitch direction within a shape) reads +0.16
  [+0.02, +0.30] with ties in, fixtures [+0.09, +0.25]: above chance; sides
  only +0.35 [+0.00, +0.65], fixtures [+0.18, +0.56], whose pair interval
  touches zero. Its picks are independent of the trim picks (kappa +0.04, n =
  72), so it is not a trims restatement. **But it is one sitting's result:**
  +0.26 [+0.09, +0.41] on the 09-18..09-28 flags sitting, +0.01 [-0.23,
  +0.26] on the 30 pairs judged since, and it leans on the old-engine arm
  (`ref_0827`, where today's engine sews its letters in far fewer directions
  and Kent picked today on 7 of 9).
- `longest_jump_mm` reads +0.24 [+0.06, +0.41] with ties in (fixtures
  [+0.09, +0.35]), sides only +0.26 [-0.04, +0.58]; independent of trims
  (+0.09, n = 38). Same pattern: the flags sitting carries it.

**One hypothesis came out reversed.** His note on the professional's Becker
("each stitch crosses the whole stroke in one go") was coded as "more long
stitches is better". `long_share` (stitches over 4 mm) reads **below chance**
on both statistics: -0.38 [-0.69, -0.09] sides only, -0.19 [-0.32, -0.06]
with ties in, both fixture intervals also below zero. He picks the side with
FEWER long stitches. That is not licensed as a quality signal by flipping it
after the fact (its direction was written down before the table, in commit
`ab4563b5`, and the table is reported as written); it is a hypothesis for
the next sitting to test with the direction stated in advance. It is also
partly the trims again (against the trim picks: -0.32, n = 64) and, like the
two leads, carried by the flags sitting (-0.08 [-0.31, +0.16] since).

**"Both bad" is not predicted by any level.** Neither the four bare-fabric
instruments already pooled (reused, not rebuilt) nor the new density and
flow levels separate the pairs he called both bad (all six: kappa between
-0.20 and +0.08, every interval spanning zero).

Read every interval as wide: 14 candidates x 2 statistics is 28 readings, so
about one false "above chance" is expected by chance alone, and the 76 pairs
are 7 logos. **The phase-1 exit is not met against this instrument either**
(section 8). No phase advance is proposed.

## 1. His words, coded

Every verbatim note in `docs/eye-pairs-2026-09-28/`, `-09-30/`, `-10-03/`,
`-10-07/` and `-10-11/kent-notes-store-export.json` was read, with the four
memory notes the brief cites (`six-flags-invisible-at-viewing-size-2026-09-18`,
`second-sitting-eleven-flags-2026-09-28`, `sewout-five-points-2026-09-03`,
`fill-row-ruling-2026-09-03`). His vocabulary falls into five families; each
became a candidate that can be read from the stitch records alone.

| family | his words (short, verbatim) | sitting | candidate |
|---|---|---|---|
| density | "the stitch density is VERy different ... the before stitch density is better" | density-1007 becker | `thread_density` (higher) |
| density | "the stitch density looks better on the before" | density-1007 | `thread_density` |
| density | "just trying to fill a void" | envelope-0930 becker | `thread_density`, `flow_circvar` |
| density, pro | the 0.14-0.17 mm rows of the pro's fills (sew-out, 09-03) | sew-out | `density_pro_gap` (lower) |
| flow | "the lettering needs to be smooth and have flow" | envelope-0930 becker | `flow_circvar`, `turns_per_100mm` |
| flow | "the lettering does not flow, satin stitching is not smooth and structured pattern" | evening-0930 becker | `flow_circvar`, `turns_per_100mm` |
| flow | "inconsistant and not uniform stitch patterning" | off-flags-1003 drone | `flow_circvar` |
| flow | "One direction per stroke, no mid-column holes" (picked in chat) | pro-1001 | `flow_circvar` |
| stitch length | "Each stitch crosses the whole stroke in one go" (picked in chat) | pro-1001 | `stitch_median_mm` (higher), `long_share` (higher), `short_share` (lower) |
| stitch length | "very thin", "to skinny", "aren't thick enough", "little worms" | off-flags-1003 bean_letters | `stitch_median_mm` |
| breaks | "the satin border is jumpy, its on off on off" | envelope-0930 bridge | `runs_per_shape` (lower) |
| breaks | "edges are nice, and clean the don't randomly break" | evening-0930 tires | `runs_per_shape` |
| trims / travel | "The Red logo trim is much cleaner", "back stitching looks cleaner" | flags ref_0827 | `jumps_per_1000`, `longest_jump_mm` (lower); `trims_per_1000` is #842's control |
| back stitching | "The back stitching helps support the top threading so it has structure and support" | pro-1001 | `back_share_thread`, `top_support` (higher), reused from `tools/underlay_cover.py` |
| both bad | "four logos bad under every setting" (gaulke, golden_tee, screenshot, drone) | flags 09-28 | level of the bare-fabric instruments already pooled (reused) |

Words with no stream reading, and so no candidate: "more detail on the woods
imagery", "letters look like the actual letters", "the N was better before",
"lettering recognition / outline" - those are about the artwork read back,
which is the fidelity family #842 already scored.

## 2. The candidates, one sentence each

All are read from the stored design's stitch records (`x`, `y` in 0.1 mm,
`type`, and the `runs` table's kind and shape), never by re-digitizing (#842
explains why: a re-digitize scores today's engine, not the one he saw). The
direction column is the HYPOTHESIS taken from his words, written into
`CANDIDATES` in commit `ab4563b5` before any pair was measured; a negative
kappa is reported as a reversed hypothesis, never flipped.

| candidate | definition | better is |
|---|---|---|
| `thread_density` | needle-down thread length (mm) per mm^2 of sewn footprint, the footprint being the exact union of every stitch drawn as a round-capped 0.4 mm thread, over the shapes whose runs differ between the two sides (the whole design when none do) | higher |
| `thread_density_whole` | the same over the whole design | higher |
| `density_pro_gap` | the absolute gap between the whole-design density and the professional's own file of the same logo (becker 9.04, fremont 12.16, drone 11.55, golden_tee 9.08 mm/mm^2; tires' file is 3D puff and is not used) | lower |
| `flow_circvar` | thread-weighted mean over fill and satin shapes of the circular variance of stitch direction (axial: the doubled angle, so a satin's back-and-forth is one direction) for stitches of 1 mm or more | lower |
| `turns_per_100mm` | consecutive stitches of 1 mm or more inside one fill or satin run whose direction changes by more than 30 degrees, per 100 mm of that thread | lower |
| `stitch_median_mm` | median needle-down stitch length on the changed shapes | higher |
| `short_share` | share of those stitches under 1 mm | lower |
| `long_share` | share of those stitches over 4 mm | higher |
| `jumps_per_1000` | needle-up moves (a stretch of jump records between two stitches) per 1000 stitches | lower |
| `longest_jump_mm` | the longest such move | lower |
| `runs_per_shape` | sewn runs (fill, satin, run) per changed shape: how many pieces a shape is sewn in | lower |
| `back_share_thread` | **reused** from `tools/underlay_cover.py`: back stitching as a share of thread, whole design | higher |
| `top_support` | **reused** from `tools/underlay_cover.py`: share of the top thread laid on thread already sewn | higher |
| `trims_per_1000` | trims per 1000 stitches, recomputed from the same records: #842's one passing instrument, the control | lower |

Each measurement is tested on a synthetic design whose answer is known and
lands within 2% (`tests/test_eye_pairs_density_flow.py`, 19 tests): a fill at
0.15 and 0.30 mm pitch against its analytic thread-per-footprint (and the
ratio of the two within 2% of one half, rotation-free), isolated rows against
one over the thread width, the circular variance of one, two orthogonal and
two 45-degree directions, one turn in 120 mm, a 10/20/10 length mix for the
median and both shares, two moves of 30 and 10 mm, and runs per shape. The
same file pins that the pooling refuses an unknown label (#842's vocabulary
guard, reused through `pooled.pooled_pairs`), that a design whose stitch count
is not the judged page's is refused, and that the committed inputs relabel
nothing.

## 3. What could be scored

The labels are #842's `pooled-inputs.json`, pair for pair. A pair is scored
only when both stored designs of the page he judged were found AND their
stitch counts equal the counts the sitting itself recorded (its price table
or features). Every one of the 96 measured pairs passed that check; none was
measured on a look-alike.

| sitting | judged pairs | in scope | measured, in scope | stored designs |
|---|---|---|---|---|
| `flags-0918-0928` | 77 | 58 | 46 | the 09-18 render directory (same source as #842; its proxy caveat applies) |
| `envelope-0930` | 7 | 5 | 0 | none found |
| `evening-0930` | 13 | 9 | 0 | none found |
| `texture-0930` | 7 | 7 | 0 | none found |
| `off-flags-1003` | 19 | 17 | 17 | **new**: the sitting's merged render in a session scratchpad, stitches and trims equal to `docs/eye-pairs-2026-10-03/price-tables.json` on all 8 fixtures |
| `density-1007` | 6 | 5 | 5 | the columns-sitting render directory (as #842) |
| `letterform-1007` | 2 | 2 | 2 | the letterform-priors render directory (as #842) |
| `columns-flip-1008` | 6 | 6 | 6 | **new**: the sitting's merged render in a session scratchpad, equal to `docs/eye-pairs-2026-10-08/flip/price-tables.json` on all 7 fixtures |
| `full-density-1008` | 7 | 6 | 0 | none found (as #842) |
| **total** | 144 | 115 | **76** | |

So 76 of the 115 in-scope pairs carry every candidate (33 where Kent chose a
side: 22 `after`, 11 `before`; 23 `same`, 20 `both_bad`), against 26 for
#842's fidelity instruments. Fixtures: bridge 13, drone 13, becker 12,
enthusiast 12, fremont 11, golden_tee 11, tires 4. `density_pro_gap` is on
the four logos with a professional file (47 pairs, 20 decided). Inputs:
`docs/eye-pairs-2026-10-12/density-flow-inputs.json`, built once by
`digitizer/tools/eye_pairs/density_flow_build.py` (the render directories are
gitignored or scratch and hold client logos, so only numbers are committed).

## 4. Kappa per candidate (scope: 115 pairs, 76 measured)

The statistics are `pooled.py`'s, unchanged: sides only = 2x2 unweighted
kappa over pairs where Kent and the candidate both chose a side; ties in = 3x3
linear-weighted kappa over every judged pair (`same` and `both_bad` a tie);
percentile bootstrap, 10,000 resamples, seed fixed, over pairs and over whole
fixtures; a reading needs both intervals clear of zero and 10 pairs. The last
column asks whether a candidate restates trims: the kappa between its picks
and `trims_per_1000`'s, over pairs where both chose a side (no label in it).

| candidate | better is | n scored | n Kent chose a side | silent there | kappa, sides only (2x2) | 95% CI pairs | 95% CI fixtures | kappa, ties in (3-way, weighted) | 95% CI pairs | 95% CI fixtures | reading | sign matches his notes | Kent's pick worse on | kappa vs `trims_per_1000` picks (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **density** | | | | | | | | | | | | | | |
| `thread_density` | higher | 76 | 33 | 0 | -0.11 | [-0.40, +0.18] | [-0.42, +0.04] | -0.06 | [-0.19, +0.08] | [-0.15, +0.01] | sides: no evidence either way; ties in: no evidence either way | no, reversed (sign) | 20 | +0.10 (72) |
| `thread_density_whole` | higher | 76 | 33 | 0 | +0.04 | [-0.26, +0.33] | [-0.22, +0.22] | +0.01 | [-0.12, +0.15] | [-0.09, +0.10] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 17 | +0.23 (72) |
| `density_pro_gap` | lower | 47 | 20 | 0 | +0.10 | [-0.30, +0.50] | [-0.29, +0.36] | +0.05 | [-0.13, +0.23] | [-0.02, +0.20] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 9 | +0.15 (45) |
| **flow** | | | | | | | | | | | | | | |
| `flow_circvar` | lower | 76 | 33 | 0 | +0.35 | [+0.00, +0.65] | [+0.18, +0.56] | +0.16 | [+0.02, +0.30] | [+0.09, +0.25] | sides: no evidence either way; ties in: above chance | yes (sign) | 10 | +0.04 (72) |
| `turns_per_100mm` | lower | 76 | 33 | 2 | +0.08 | [-0.25, +0.41] | [-0.28, +0.39] | +0.08 | [-0.06, +0.22] | [-0.06, +0.20] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 12 | +0.08 (69) |
| `runs_per_shape` | lower | 70 | 28 | 4 | +0.15 | [-0.25, +0.51] | [-0.27, +0.57] | +0.14 | [-0.04, +0.32] | [-0.04, +0.32] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 10 | +0.27 (49) |
| **stitch length** | | | | | | | | | | | | | | |
| `stitch_median_mm` | higher | 76 | 33 | 4 | +0.13 | [-0.24, +0.48] | [-0.15, +0.45] | +0.08 | [-0.09, +0.24] | [-0.08, +0.24] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 12 | +0.22 (59) |
| `short_share` | lower | 76 | 33 | 0 | +0.17 | [-0.16, +0.49] | [-0.08, +0.42] | +0.11 | [-0.04, +0.25] | [-0.02, +0.23] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 13 | +0.30 (72) |
| `long_share` | higher | 76 | 33 | 3 | -0.38 | [-0.69, -0.09] | [-0.85, -0.06] | -0.19 | [-0.32, -0.06] | [-0.37, -0.05] | sides: below chance; ties in: below chance | no, reversed (sign) | 24 | -0.32 (64) |
| **travel** | | | | | | | | | | | | | | |
| `jumps_per_1000` | lower | 76 | 33 | 0 | +0.53 | [+0.19, +0.81] | [+0.31, +0.79] | +0.30 | [+0.15, +0.43] | [+0.15, +0.42] | sides: above chance; ties in: above chance | yes (sign) | 7 | +0.72 (72) |
| `longest_jump_mm` | lower | 76 | 33 | 10 | +0.26 | [-0.04, +0.58] | [+0.11, +0.51] | +0.24 | [+0.06, +0.41] | [+0.09, +0.35] | sides: no evidence either way; ties in: above chance | yes (sign) | 9 | +0.09 (38) |
| `trims_per_1000` | lower | 76 | 33 | 0 | +0.55 | [+0.24, +0.82] | [+0.32, +0.79] | +0.30 | [+0.15, +0.43] | [+0.15, +0.42] | sides: above chance; ties in: above chance | yes (sign) | 7 | - |
| **back stitching (reused)** | | | | | | | | | | | | | | |
| `back_share_thread` | higher | 76 | 33 | 0 | +0.18 | [-0.08, +0.44] | [-0.05, +0.41] | +0.09 | [-0.05, +0.23] | [-0.04, +0.25] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 15 | +0.04 (70) |
| `top_support` | higher | 76 | 33 | 0 | +0.20 | [-0.11, +0.52] | [-0.08, +0.34] | +0.13 | [-0.03, +0.28] | [+0.01, +0.23] | sides: no evidence either way; ties in: no evidence either way | yes (sign) | 13 | +0.01 (68) |

## 5. Is it one sitting's? The splits

The flags sitting is 46 of the 76 measured pairs, and its `ref_0827` arm
compares whole engines (08-27 against 09-18), not one flag. The same
statistics on three subsets, and with `both_bad` dropped instead of folded
into the tie:

| candidate | split | n scored | n decided | kappa, sides only | 95% CI pairs | 95% CI fixtures | kappa, ties in | 95% CI pairs | 95% CI fixtures |
|---|---|---|---|---|---|---|---|---|---|
| `thread_density` | no old engine arms | 70 | 28 | -0.24 | [-0.55, +0.06] | [-0.56, -0.06] | -0.11 | [-0.24, +0.02] | [-0.20, -0.05] |
| `thread_density` | flags sitting only | 46 | 18 | +0.00 | [-0.42, +0.44] | [-0.29, +0.29] | +0.01 | [-0.16, +0.18] | [-0.11, +0.12] |
| `thread_density` | later sittings only | 30 | 15 | -0.22 | [-0.62, +0.11] | [-0.74, +0.08] | -0.14 | [-0.34, +0.04] | [-0.31, +0.01] |
| `thread_density` | both_bad dropped | 56 | 33 | -0.11 | [-0.41, +0.17] | - | -0.07 | [-0.25, +0.11] | - |
| `thread_density_whole` | no old engine arms | 70 | 28 | -0.06 | [-0.39, +0.24] | [-0.32, +0.09] | -0.03 | [-0.17, +0.10] | [-0.13, +0.04] |
| `thread_density_whole` | flags sitting only | 46 | 18 | +0.08 | [-0.35, +0.53] | [-0.25, +0.42] | +0.04 | [-0.13, +0.22] | [-0.09, +0.16] |
| `thread_density_whole` | later sittings only | 30 | 15 | +0.00 | [-0.34, +0.31] | [-0.40, +0.27] | -0.02 | [-0.20, +0.17] | [-0.19, +0.10] |
| `thread_density_whole` | both_bad dropped | 56 | 33 | +0.04 | [-0.26, +0.32] | - | +0.02 | [-0.16, +0.20] | - |
| `density_pro_gap` | no old engine arms | 43 | 17 | -0.03 | [-0.46, +0.41] | [-0.36, +0.25] | -0.02 | [-0.19, +0.17] | [-0.08, +0.12] |
| `density_pro_gap` | flags sitting only | 29 | 9 | +0.50 | [-0.20, +1.00] | [+0.40, +0.60] | +0.17 | [-0.02, +0.35] | [+0.07, +0.24] |
| `density_pro_gap` | later sittings only | 18 | 11 | -0.18 | [-0.68, +0.29] | [-0.67, +0.14] | -0.15 | [-0.46, +0.18] | [-0.32, +0.15] |
| `density_pro_gap` | both_bad dropped | 36 | 20 | +0.10 | [-0.30, +0.50] | - | +0.06 | [-0.18, +0.29] | - |
| `flow_circvar` | no old engine arms | 70 | 28 | +0.27 | [-0.09, +0.62] | [+0.06, +0.52] | +0.11 | [-0.03, +0.26] | [+0.03, +0.21] |
| `flow_circvar` | flags sitting only | 46 | 18 | +0.64 | [+0.20, +1.00] | [+0.50, +0.83] | +0.26 | [+0.09, +0.41] | [+0.15, +0.35] |
| `flow_circvar` | later sittings only | 30 | 15 | -0.00 | [-0.47, +0.47] | [-0.43, +0.30] | +0.01 | [-0.23, +0.26] | [-0.19, +0.16] |
| `flow_circvar` | both_bad dropped | 56 | 33 | +0.35 | [+0.00, +0.65] | - | +0.21 | [+0.02, +0.40] | - |
| `turns_per_100mm` | no old engine arms | 70 | 26 | +0.01 | [-0.34, +0.37] | [-0.36, +0.32] | +0.02 | [-0.13, +0.17] | [-0.12, +0.15] |
| `turns_per_100mm` | flags sitting only | 46 | 17 | +0.16 | [-0.29, +0.61] | [-0.25, +0.60] | +0.11 | [-0.07, +0.28] | [-0.07, +0.25] |
| `turns_per_100mm` | later sittings only | 30 | 14 | -0.02 | [-0.43, +0.47] | [-0.47, +0.33] | +0.04 | [-0.20, +0.26] | [-0.15, +0.19] |
| `turns_per_100mm` | both_bad dropped | 56 | 31 | +0.08 | [-0.25, +0.43] | - | +0.10 | [-0.09, +0.29] | - |
| `stitch_median_mm` | no old engine arms | 70 | 24 | +0.22 | [-0.19, +0.58] | [-0.06, +0.47] | +0.10 | [-0.06, +0.26] | [-0.02, +0.23] |
| `stitch_median_mm` | flags sitting only | 46 | 16 | +0.03 | [-0.42, +0.50] | [-0.57, +0.57] | +0.07 | [-0.12, +0.27] | [-0.17, +0.30] |
| `stitch_median_mm` | later sittings only | 30 | 13 | +0.22 | [-0.31, +0.70] | [-0.08, +0.40] | +0.08 | [-0.22, +0.36] | [-0.06, +0.20] |
| `stitch_median_mm` | both_bad dropped | 56 | 29 | +0.13 | [-0.24, +0.48] | - | +0.07 | [-0.14, +0.28] | - |
| `short_share` | no old engine arms | 70 | 28 | +0.32 | [-0.06, +0.65] | [+0.01, +0.56] | +0.15 | [+0.01, +0.30] | [+0.02, +0.29] |
| `short_share` | flags sitting only | 46 | 18 | -0.15 | [-0.56, +0.29] | [-0.65, +0.21] | -0.03 | [-0.20, +0.14] | [-0.23, +0.15] |
| `short_share` | later sittings only | 30 | 15 | +0.57 | [+0.07, +1.00] | [+0.09, +0.88] | +0.33 | [+0.10, +0.55] | [+0.07, +0.62] |
| `short_share` | both_bad dropped | 56 | 33 | +0.17 | [-0.18, +0.50] | - | +0.13 | [-0.06, +0.32] | - |
| `long_share` | no old engine arms | 70 | 25 | -0.42 | [-0.74, -0.07] | [-0.88, -0.06] | -0.16 | [-0.30, -0.02] | [-0.34, -0.01] |
| `long_share` | flags sitting only | 46 | 16 | -0.58 | [-0.97, -0.13] | [-0.98, -0.12] | -0.27 | [-0.41, -0.13] | [-0.43, -0.13] |
| `long_share` | later sittings only | 30 | 14 | -0.15 | [-0.57, +0.26] | [-0.77, +0.19] | -0.08 | [-0.31, +0.16] | [-0.38, +0.15] |
| `long_share` | both_bad dropped | 56 | 30 | -0.38 | [-0.67, -0.09] | - | -0.27 | [-0.43, -0.09] | - |
| `jumps_per_1000` | no old engine arms | 70 | 28 | +0.55 | [+0.20, +0.85] | [+0.24, +0.82] | +0.27 | [+0.12, +0.41] | [+0.11, +0.42] |
| `jumps_per_1000` | flags sitting only | 46 | 18 | +0.35 | [-0.17, +0.77] | [-0.04, +0.83] | +0.19 | [+0.01, +0.36] | [+0.06, +0.34] |
| `jumps_per_1000` | later sittings only | 30 | 15 | +0.73 | [+0.36, +1.00] | [+0.38, +1.00] | +0.47 | [+0.26, +0.67] | [+0.22, +0.70] |
| `jumps_per_1000` | both_bad dropped | 56 | 33 | +0.53 | [+0.19, +0.81] | - | +0.38 | [+0.19, +0.54] | - |
| `longest_jump_mm` | no old engine arms | 70 | 18 | +0.16 | [-0.21, +0.56] | [-0.19, +0.53] | +0.21 | [+0.03, +0.39] | [+0.06, +0.35] |
| `longest_jump_mm` | flags sitting only | 46 | 16 | +0.33 | [+0.06, +0.67] | [+0.10, +0.70] | +0.27 | [+0.07, +0.48] | [+0.08, +0.49] |
| `longest_jump_mm` | later sittings only | 30 | 7 | +0.09 | [-0.52, +0.72] | [-0.50, +0.75] | +0.20 | [-0.08, +0.48] | [-0.09, +0.52] |
| `longest_jump_mm` | both_bad dropped | 56 | 23 | +0.26 | [-0.04, +0.58] | - | +0.28 | [+0.10, +0.47] | - |
| `runs_per_shape` | no old engine arms | 70 | 24 | +0.15 | [-0.25, +0.51] | [-0.27, +0.57] | +0.14 | [-0.04, +0.32] | [-0.04, +0.32] |
| `runs_per_shape` | flags sitting only | 40 | 10 | +0.00 | [-0.60, +0.60] | [-0.43, +0.57] | +0.00 | [-0.18, +0.20] | [-0.12, +0.14] |
| `runs_per_shape` | later sittings only | 30 | 14 | +0.26 | [-0.29, +0.71] | [-0.30, +0.67] | +0.34 | [+0.03, +0.63] | [+0.02, +0.62] |
| `runs_per_shape` | both_bad dropped | 51 | 24 | +0.15 | [-0.25, +0.50] | - | +0.18 | [-0.05, +0.40] | - |
| `back_share_thread` | no old engine arms | 70 | 28 | +0.10 | [-0.19, +0.38] | [-0.15, +0.31] | +0.05 | [-0.09, +0.18] | [-0.08, +0.19] |
| `back_share_thread` | flags sitting only | 46 | 18 | +0.36 | [-0.04, +0.77] | [-0.03, +0.88] | +0.15 | [-0.03, +0.31] | [-0.04, +0.38] |
| `back_share_thread` | later sittings only | 30 | 15 | +0.00 | [-0.34, +0.31] | [-0.24, +0.09] | +0.01 | [-0.19, +0.22] | [-0.11, +0.13] |
| `back_share_thread` | both_bad dropped | 56 | 33 | +0.18 | [-0.07, +0.44] | - | +0.13 | [-0.05, +0.31] | - |
| `top_support` | no old engine arms | 70 | 28 | +0.16 | [-0.20, +0.50] | [-0.17, +0.35] | +0.10 | [-0.06, +0.26] | [-0.01, +0.20] |
| `top_support` | flags sitting only | 46 | 18 | +0.77 | [+0.44, +1.00] | [+0.49, +1.00] | +0.32 | [+0.15, +0.48] | [+0.18, +0.47] |
| `top_support` | later sittings only | 30 | 15 | -0.43 | [-0.76, +0.01] | [-0.86, +0.00] | -0.17 | [-0.40, +0.09] | [-0.41, +0.03] |
| `top_support` | both_bad dropped | 56 | 33 | +0.20 | [-0.12, +0.52] | - | +0.18 | [-0.03, +0.38] | - |
| `trims_per_1000` | no old engine arms | 70 | 28 | +0.56 | [+0.22, +0.85] | [+0.24, +0.83] | +0.27 | [+0.12, +0.41] | [+0.10, +0.42] |
| `trims_per_1000` | flags sitting only | 46 | 18 | +0.54 | [+0.11, +0.89] | [+0.30, +0.86] | +0.23 | [+0.06, +0.40] | [+0.11, +0.35] |
| `trims_per_1000` | later sittings only | 30 | 15 | +0.57 | [+0.07, +1.00] | [+0.25, +0.84] | +0.40 | [+0.16, +0.62] | [+0.19, +0.56] |
| `trims_per_1000` | both_bad dropped | 56 | 33 | +0.55 | [+0.24, +0.82] | - | +0.37 | [+0.19, +0.54] | - |

Read across the rows, the pattern is the warning: **the trim family is the
only one whose sign and size hold in every split** (`trims_per_1000` and
`jumps_per_1000` above zero on the flags sitting, on the later sittings and
without the old-engine arm). Every other candidate that leans one way on the
flags sitting leans the other way, or nowhere, on the 30 pairs since:
`flow_circvar` +0.26 then +0.01, `top_support` +0.32 then -0.17,
`short_share` -0.03 then +0.33, `long_share` -0.27 then -0.08. A signal that
changes sign between sittings is what 28 readings on 7 logos produce by
chance, and what a sitting-specific mix of arms produces; neither is an
instrument that agrees with his eye.


## 6. Both bad: does a level flag it?

A different question: is a pair he called **both bad** one where the design
is bad on BOTH sides by some level? Level = the mean of the two sides; the
instrument flags a pair when the level is on its bad side of the pooled
median (a split fixed before looking at the labels, not tuned to them);
kappa against his `both_bad`, pairs the scorecard refused on are left out.
The four bare-fabric instruments are #842's pooled values, reused; the two
new levels are this module's.

| level instrument | source | bad side | n | n both bad | split (pooled median) | n flagged | kappa (2x2) | 95% CI pairs | 95% CI fixtures | reading |
|---|---|---|---|---|---|---|---|---|---|---|
| `unsewn_frac` | pooled | above | 20 | 4 | 0.00125 | 10 | -0.20 | [-0.52, +0.14] | [-0.30, +0.07] | no evidence either way |
| `uncovered_ink_frac` | pooled | above | 26 | 5 | 0.0173 | 13 | -0.08 | [-0.37, +0.23] | [-0.23, +0.19] | no evidence either way |
| `uncovered_total_mm2` | pooled | above | 47 | 15 | 0 | 3 | +0.01 | [-0.16, +0.22] | [-0.18, +0.23] | no evidence either way |
| `lost_frac` | pooled | above | 26 | 5 | 0.1215 | 13 | +0.08 | [-0.23, +0.38] | [-0.47, +0.18] | no evidence either way |
| `thread_density_whole` | candidate | below | 76 | 20 | 8.055 | 38 | -0.05 | [-0.25, +0.14] | [-0.30, +0.23] | no evidence either way |
| `flow_circvar` | candidate | above | 76 | 20 | 0.4861 | 38 | -0.05 | [-0.25, +0.15] | [-0.22, +0.08] | no evidence either way |

Nothing separates them. His `both_bad` calls sit mostly on four logos
(drone, golden_tee, gaulke, screenshot, the last two out of scope) and are
about what a logo IS under every setting, which a level averaged over both
sides of one flag does not see at this n.


## 7. Pairs where Kent's pick scores WORSE, per candidate

Pairs where he chose a side, the candidate chose the other, ordered by the
margin in the candidate's own units. Pair ids are `sitting:arm:fixture`.
The second exit clause ("nothing he judges better ever scores worse") fails
on every candidate: from 7 pairs (`jumps_per_1000`, `trims_per_1000`) to 24
(`long_share`). The density pairs at the top are the Column lane's (see The answer); the `long_share` pairs at the top are the same two Becker
Column pairs, whose `after` side sews fewer long crosses.

#### `thread_density` (20 pairs) - thread mm per mm^2 of sewn footprint, changed shapes

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 10.32 | 4.288 | 6.03 |
| `columns-flip-1008:columns_words:becker` | after | 10.27 | 6.203 | 4.07 |
| `density-1007:lettering_columns:drone` | after | 6.973 | 5.004 | 1.97 |
| `columns-flip-1008:columns_words:golden_tee` | after | 8.632 | 7.622 | 1.01 |
| `flags-0918-0928:rail_comp:bridge` | after | 8.313 | 7.342 | 0.971 |
| `columns-flip-1008:columns_words:enthusiast` | after | 7.147 | 6.293 | 0.855 |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 8.589 | 7.946 | 0.643 |
| `off-flags-1003:bean_letters:golden_tee` | before | 7.475 | 8.062 | 0.586 |
| `columns-flip-1008:columns_words:bridge` | after | 7.26 | 6.856 | 0.404 |
| `flags-0918-0928:rail_comp:fremont` | after | 5.859 | 5.653 | 0.207 |
| `flags-0918-0928:design_angle:tires` | before | 6.831 | 6.987 | 0.156 |
| `off-flags-1003:bean_letters:drone` | before | 7.873 | 8.021 | 0.148 |
| `flags-0918-0928:directional_comp:fremont` | before | 8.056 | 8.153 | 0.0962 |
| `flags-0918-0928:directional_comp:enthusiast` | before | 6.529 | 6.607 | 0.0785 |
| `columns-flip-1008:columns_words:fremont` | after | 6.754 | 6.702 | 0.0523 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 5.578 | 5.544 | 0.0343 |
| `flags-0918-0928:rail_comp:becker` | after | 7.335 | 7.314 | 0.0214 |
| `off-flags-1003:cap_recentre:becker` | after | 7.307 | 7.293 | 0.0135 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 6.745 | 6.735 | 0.00993 |
| `off-flags-1003:cap_recentre:tires` | after | 7.082 | 7.075 | 0.00633 |

#### `thread_density_whole` (17 pairs) - thread mm per mm^2 of sewn footprint, whole design

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 8.838 | 6.379 | 2.46 |
| `columns-flip-1008:columns_words:becker` | after | 8.816 | 7.014 | 1.8 |
| `columns-flip-1008:columns_words:golden_tee` | after | 11.62 | 10.38 | 1.24 |
| `columns-flip-1008:columns_words:enthusiast` | after | 7.617 | 6.991 | 0.627 |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 9.017 | 8.413 | 0.604 |
| `flags-0918-0928:rail_comp:bridge` | after | 9.017 | 8.463 | 0.554 |
| `density-1007:lettering_columns:drone` | after | 8.725 | 8.297 | 0.428 |
| `off-flags-1003:bean_letters:drone` | before | 8.597 | 8.778 | 0.181 |
| `flags-0918-0928:design_angle:tires` | before | 6.831 | 6.987 | 0.156 |
| `flags-0918-0928:directional_comp:fremont` | before | 8.875 | 8.978 | 0.102 |
| `flags-0918-0928:directional_comp:enthusiast` | before | 6.735 | 6.818 | 0.0828 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 6.735 | 6.723 | 0.0119 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 6.745 | 6.735 | 0.00993 |
| `off-flags-1003:cap_recentre:becker` | after | 7.738 | 7.729 | 0.00964 |
| `columns-flip-1008:columns_words:fremont` | after | 9.693 | 9.688 | 0.00469 |
| `flags-0918-0928:rail_comp:becker` | after | 8.022 | 8.018 | 0.00428 |
| `off-flags-1003:cap_recentre:tires` | after | 7.547 | 7.545 | 0.00222 |

#### `density_pro_gap` (9 pairs) - |whole-design density - the pro file's|, pro logos only

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 0.197 | 2.656 | 2.46 |
| `columns-flip-1008:columns_words:becker` | after | 0.2196 | 2.021 | 1.8 |
| `density-1007:lettering_columns:drone` | after | 2.827 | 3.255 | 0.428 |
| `off-flags-1003:bean_letters:drone` | before | 2.955 | 2.774 | 0.181 |
| `off-flags-1003:bean_letters:golden_tee` | before | 1.859 | 1.723 | 0.136 |
| `flags-0918-0928:directional_comp:fremont` | before | 3.281 | 3.178 | 0.102 |
| `off-flags-1003:cap_recentre:becker` | after | 1.297 | 1.306 | 0.00964 |
| `columns-flip-1008:columns_words:fremont` | after | 2.464 | 2.468 | 0.00469 |
| `flags-0918-0928:rail_comp:becker` | after | 1.013 | 1.018 | 0.00428 |

#### `flow_circvar` (10 pairs) - circular variance of stitch direction within fill/satin shapes

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:lettering_column:enthusiast` | before | 0.826 | 0.6007 | 0.225 |
| `flags-0918-0928:rail_comp:fremont` | after | 0.2328 | 0.4103 | 0.177 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.498 | 0.6635 | 0.166 |
| `columns-flip-1008:columns_words:fremont` | after | 0.4718 | 0.6059 | 0.134 |
| `columns-flip-1008:columns_words:enthusiast` | after | 0.5003 | 0.597 | 0.0968 |
| `off-flags-1003:bean_letters:drone` | before | 0.09005 | 0.01982 | 0.0702 |
| `off-flags-1003:bean_letters:fremont` | before | 0.06112 | 0.01566 | 0.0455 |
| `letterform-1007:letterform_priors:becker` | after | 0.6056 | 0.6114 | 0.00581 |
| `off-flags-1003:bean_letters:enthusiast` | before | 0.4474 | 0.4459 | 0.00154 |
| `flags-0918-0928:rail_comp:becker` | after | 0.003972 | 0.004035 | 6.3e-05 |

#### `turns_per_100mm` (12 pairs) - >30 deg direction changes per 100 mm of fill/satin thread

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:drone` | after | 0.5718 | 4.443 | 3.87 |
| `flags-0918-0928:rail_comp:fremont` | after | 0.2431 | 0.574 | 0.331 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 0.7903 | 0.5357 | 0.255 |
| `off-flags-1003:bean_letters:fremont` | before | 0.3843 | 0.1436 | 0.241 |
| `flags-0918-0928:directional_comp:enthusiast` | before | 0.7896 | 0.6341 | 0.156 |
| `off-flags-1003:bean_letters:enthusiast` | before | 0.9545 | 0.811 | 0.144 |
| `off-flags-1003:bean_letters:golden_tee` | before | 0.8211 | 0.7075 | 0.114 |
| `off-flags-1003:bean_letters:drone` | before | 0.4877 | 0.4305 | 0.0572 |
| `flags-0918-0928:design_angle:tires` | before | 0.1803 | 0.1363 | 0.044 |
| `flags-0918-0928:wide_columns:becker` | before | 0.1227 | 0.09639 | 0.0263 |
| `flags-0918-0928:rail_comp:enthusiast` | after | 0.7956 | 0.8135 | 0.0179 |
| `letterform-1007:letterform_priors:becker` | after | 0.07238 | 0.08698 | 0.0146 |

#### `stitch_median_mm` (12 pairs) - median stitch length, changed shapes

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:becker` | after | 1.942 | 0.8 | 1.14 |
| `off-flags-1003:bean_letters:enthusiast` | before | 0.9434 | 1.612 | 0.669 |
| `density-1007:lettering_columns:drone` | after | 1.603 | 1.404 | 0.2 |
| `columns-flip-1008:columns_words:golden_tee` | after | 1.664 | 1.487 | 0.178 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 1.616 | 1.5 | 0.116 |
| `flags-0918-0928:ref_0827:drone` | after | 1.6 | 1.5 | 0.1 |
| `off-flags-1003:bean_letters:fremont` | before | 1.5 | 1.6 | 0.1 |
| `flags-0918-0928:directional_comp:drone` | after | 1.6 | 1.53 | 0.0703 |
| `flags-0918-0928:design_angle:tires` | before | 3.106 | 3.14 | 0.0336 |
| `letterform-1007:letterform_priors:becker` | after | 2.36 | 2.335 | 0.0256 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 0.7 | 0.7071 | 0.00711 |
| `flags-0918-0928:wide_columns:becker` | before | 0.8 | 0.8062 | 0.00623 |

#### `short_share` (13 pairs) - share of stitches under 1 mm, changed shapes

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:becker` | after | 0.1986 | 0.5267 | 0.328 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 0.8763 | 0.7765 | 0.0998 |
| `off-flags-1003:bean_letters:enthusiast` | before | 0.5035 | 0.4077 | 0.0958 |
| `density-1007:lettering_columns:drone` | after | 0.3257 | 0.3914 | 0.0656 |
| `flags-0918-0928:ref_0827:drone` | after | 0.3173 | 0.3693 | 0.0521 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.2333 | 0.2792 | 0.0458 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 0.3874 | 0.424 | 0.0366 |
| `flags-0918-0928:lettering_column:fremont` | before | 0.3307 | 0.3028 | 0.0279 |
| `flags-0918-0928:wide_columns:becker` | before | 0.5279 | 0.5071 | 0.0208 |
| `flags-0918-0928:directional_comp:drone` | after | 0.3477 | 0.3538 | 0.0061 |
| `flags-0918-0928:design_angle:tires` | before | 0.1724 | 0.1715 | 0.000845 |
| `flags-0918-0928:rail_comp:becker` | after | 0.9778 | 0.978 | 0.000208 |
| `flags-0918-0928:ref_0827:fremont` | after | 0.5075 | 0.5077 | 0.000196 |

#### `long_share` (24 pairs) - share of stitches over 4 mm, changed shapes

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 0.05566 | 0.01144 | 0.0442 |
| `columns-flip-1008:columns_words:becker` | after | 0.05573 | 0.01208 | 0.0437 |
| `flags-0918-0928:design_angle:tires` | before | 0.03688 | 0.07223 | 0.0353 |
| `flags-0918-0928:wide_columns:becker` | before | 0.001544 | 0.02803 | 0.0265 |
| `flags-0918-0928:ref_0827:becker` | after | 0.0186 | 0.00153 | 0.0171 |
| `flags-0918-0928:ref_0827:drone` | after | 0.01482 | 0.000545 | 0.0143 |
| `flags-0918-0928:rail_comp:bridge` | after | 0.02875 | 0.02024 | 0.00851 |
| `columns-flip-1008:columns_words:bridge` | after | 0.003876 | 0 | 0.00388 |
| `flags-0918-0928:ref_0827:bridge` | after | 0.01801 | 0.01495 | 0.00306 |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 0.0162 | 0.01366 | 0.00254 |
| `flags-0918-0928:rail_comp:enthusiast` | after | 0.003106 | 0.000902 | 0.0022 |
| `density-1007:lettering_columns:drone` | after | 0.002156 | 0 | 0.00216 |
| `columns-flip-1008:columns_words:enthusiast` | after | 0.001269 | 0 | 0.00127 |
| `flags-0918-0928:directional_comp:enthusiast` | before | 0.003561 | 0.004604 | 0.00104 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 0.003823 | 0.002859 | 0.000964 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.005072 | 0.004587 | 0.000485 |
| `flags-0918-0928:rail_comp:becker` | after | 0.004187 | 0.003739 | 0.000448 |
| `flags-0918-0928:ref_0827:fremont` | after | 0.000591 | 0.000153 | 0.000438 |
| `columns-flip-1008:columns_words:fremont` | after | 0.000374 | 0 | 0.000374 |
| `flags-0918-0928:rail_comp:fremont` | after | 0.000527 | 0.000173 | 0.000354 |
| `off-flags-1003:bean_letters:enthusiast` | before | 0.001259 | 0.001502 | 0.000243 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 0.001742 | 0.001961 | 0.000219 |
| `flags-0918-0928:directional_comp:drone` | after | 0.000567 | 0.000504 | 6.3e-05 |
| `off-flags-1003:bean_letters:golden_tee` | before | 0.001267 | 0.001272 | 5e-06 |

#### `jumps_per_1000` (7 pairs) - needle-up moves per 1000 stitches

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:directional_comp:drone` | after | 9.538 | 11.17 | 1.63 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 15.88 | 17.26 | 1.38 |
| `density-1007:lettering_columns:drone` | after | 9.509 | 10.5 | 0.996 |
| `flags-0918-0928:directional_comp:fremont` | before | 11.06 | 10.57 | 0.493 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 17.26 | 16.9 | 0.355 |
| `flags-0918-0928:lettering_column:fremont` | before | 11.06 | 10.85 | 0.215 |
| `columns-flip-1008:columns_words:golden_tee` | after | 5.81 | 5.954 | 0.144 |

#### `longest_jump_mm` (9 pairs) - longest needle-up move, mm

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `off-flags-1003:bean_letters:fremont` | before | 75.95 | 40.88 | 35.1 |
| `columns-flip-1008:columns_words:enthusiast` | after | 24.01 | 38.31 | 14.3 |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 52.35 | 62.59 | 10.2 |
| `density-1007:lettering_columns:drone` | after | 62.05 | 72.24 | 10.2 |
| `flags-0918-0928:rail_comp:bridge` | after | 52.35 | 61.92 | 9.57 |
| `flags-0918-0928:ref_0827:becker` | after | 72.54 | 78.57 | 6.04 |
| `flags-0918-0928:ref_0827:drone` | after | 66.58 | 71.5 | 4.92 |
| `flags-0918-0928:rail_comp:enthusiast` | after | 20.21 | 24.01 | 3.8 |
| `flags-0918-0928:rail_comp:becker` | after | 78.57 | 78.59 | 0.0135 |

#### `runs_per_shape` (10 pairs) - sewn runs per changed shape (pieces a shape is sewn in)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:directional_comp:drone` | after | 8.817 | 15.04 | 6.22 |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 6.031 | 11.4 | 5.37 |
| `off-flags-1003:bean_letters:fremont` | before | 5.193 | 4.053 | 1.14 |
| `density-1007:lettering_columns:drone` | after | 2.258 | 2.677 | 0.419 |
| `flags-0918-0928:wide_columns:becker` | before | 9.8 | 9.6 | 0.2 |
| `columns-flip-1008:columns_words:fremont` | after | 1.538 | 1.703 | 0.165 |
| `columns-flip-1008:columns_words:bridge` | after | 2.25 | 2.375 | 0.125 |
| `flags-0918-0928:lettering_column:fremont` | before | 9.292 | 9.208 | 0.0833 |
| `off-flags-1003:bean_letters:golden_tee` | before | 7.25 | 7.167 | 0.0833 |
| `flags-0918-0928:rail_comp:fremont` | after | 1.447 | 1.458 | 0.0108 |

#### `back_share_thread` (15 pairs) - underlay_cover: back stitching, share of thread (reused)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `columns-flip-1008:columns_words:becker` | after | 0.3916 | 0.252 | 0.14 |
| `density-1007:lettering_columns:becker` | after | 0.3884 | 0.2846 | 0.104 |
| `columns-flip-1008:columns_words:enthusiast` | after | 0.3779 | 0.2867 | 0.0912 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.5889 | 0.5083 | 0.0806 |
| `off-flags-1003:bean_letters:drone` | before | 0.5953 | 0.6216 | 0.0263 |
| `flags-0918-0928:directional_comp:drone` | after | 0.5653 | 0.5506 | 0.0147 |
| `flags-0918-0928:rail_comp:bridge` | after | 0.4961 | 0.4821 | 0.014 |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 0.4961 | 0.4883 | 0.0078 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 0.2498 | 0.2441 | 0.0057 |
| `columns-flip-1008:columns_words:fremont` | after | 0.6807 | 0.6766 | 0.0041 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 0.2441 | 0.2408 | 0.0033 |
| `off-flags-1003:cap_recentre:becker` | after | 0.3629 | 0.3606 | 0.0023 |
| `flags-0918-0928:directional_comp:enthusiast` | before | 0.2441 | 0.246 | 0.0019 |
| `columns-flip-1008:columns_words:bridge` | after | 0.6013 | 0.6002 | 0.0011 |
| `off-flags-1003:cap_recentre:tires` | after | 0.3736 | 0.3731 | 0.0005 |

#### `top_support` (13 pairs) - underlay_cover: top thread laid on thread (reused)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `columns-flip-1008:columns_words:enthusiast` | after | 0.229 | 0.1556 | 0.0734 |
| `columns-flip-1008:columns_words:becker` | after | 0.1997 | 0.1319 | 0.0678 |
| `density-1007:lettering_columns:becker` | after | 0.2002 | 0.1577 | 0.0425 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.2782 | 0.2386 | 0.0396 |
| `off-flags-1003:bean_letters:drone` | before | 0.3714 | 0.3959 | 0.0245 |
| `off-flags-1003:bean_letters:golden_tee` | before | 0.2987 | 0.3191 | 0.0204 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 0.1792 | 0.1638 | 0.0154 |
| `off-flags-1003:bean_letters:fremont` | before | 0.4184 | 0.4248 | 0.0064 |
| `density-1007:lettering_columns:fremont` | before | 0.4142 | 0.4202 | 0.006 |
| `columns-flip-1008:columns_words:fremont` | after | 0.4328 | 0.4277 | 0.0051 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 0.1638 | 0.1613 | 0.0025 |
| `off-flags-1003:cap_recentre:tires` | after | 0.2911 | 0.2905 | 0.0006 |
| `columns-flip-1008:columns_words:bridge` | after | 0.3335 | 0.3331 | 0.0004 |

#### `trims_per_1000` (7 pairs) - trims per 1000 stitches (recomputed here; the #842 control)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:enthusiast` | after | 8.776 | 9.631 | 0.855 |
| `flags-0918-0928:directional_comp:drone` | after | 7.49 | 8.137 | 0.647 |
| `density-1007:lettering_columns:drone` | after | 7.131 | 7.752 | 0.621 |
| `flags-0918-0928:directional_comp:fremont` | before | 3.772 | 3.315 | 0.456 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 9.631 | 10.02 | 0.385 |
| `columns-flip-1008:columns_words:golden_tee` | after | 4.916 | 5.12 | 0.204 |
| `off-flags-1003:bean_letters:fremont` | before | 2.847 | 2.764 | 0.0824 |

## 8. A new fact, or trims again?

| candidate | clears chance on both statistics, both intervals | restates trims (kappa vs trim picks, n) | holds in every split | verdict |
|---|---|---|---|---|
| `jumps_per_1000` | yes | yes, +0.72 (72) | yes | trims again: almost every move here is a trim's |
| `trims_per_1000` (control) | yes | - | yes | #842's finding, reproduced on 76 pairs from the stitch records |
| `flow_circvar` | ties in only | no, +0.04 (72) | no (+0.26 flags, +0.01 since) | a lead, one sitting's |
| `longest_jump_mm` | ties in only | no, +0.09 (38) | no (later sittings span zero) | a lead, travel family |
| `long_share` | below chance, reversed | partly, -0.32 (64) | no (-0.08 since) | hypothesis reversed; retest the reverse |
| every other candidate | no | - | - | no evidence either way |

**So: no new fact.** The one candidate that clears every bar restates the
trims. Density read as thread per area does not track his picks at all, and
leans the other way on the Column lane's pairs, where he took the sparser
side; flow, read as direction spread, is a one-sitting lead.

## 9. What bounds every figure here

1. **Calibrated on the same 7 logos and the same sittings that suggested the
   vocabulary.** The words came from these notes; the pairs are these pairs.
   That is the circularity a fresh sitting has to break (section 10).
2. **Multiple comparisons.** 14 candidates x 2 statistics = 28 readings;
   at 95% intervals about one false pass is expected. Only a reading that
   holds in every split is worth carrying forward, and only the trims do.
3. **Changed-shape scope.** Most arms change a few letters; the
   changed-shape candidates read only those (the whole design when nothing
   changed, both sides then tie). On the old-engine arm every shape differs,
   so changed = whole.
4. **The flags sitting is a proxy render** (#842 caveat 1: Kent judged a
   cloud render that was not kept; the 09-18 laptop render matches it to
   platform rounding). 46 of the 76 pairs rest on it.
5. **The professional's files** are at their own sizes (becker 101.9 mm,
   fremont 92.6, drone 62.6, golden_tee 74.9) against ours at the corpus
   sizes; thread per area is size-free to first order, not exactly.
6. **The thread width (0.4 mm) is the renderer's**, the same constant
   `underlay_cover.py` uses; a different width moves every density by the
   same factor near the edges and does not change a pick on a big shape.
7. **Nothing here flips a flag, moves a gate, or proposes a phase advance.**

## 10. The fresh sitting this needs (proposed, Kent's call)

The leads cannot be tested on these pairs again. A sitting that can:

- **New logos, 8 to 10, not lettering-only.** Blinding is spent on the nine
  `REAL_ART` logos (`second-sitting-eleven-flags-2026-09-28`), and #842 found
  33 of its fidelity rows refused on gradient-route logos, so pick flat-art
  logos the scorecard accepts.
- **Sides randomised and the arm name hidden** on the page: until now LEFT was
  always the shipped engine, so a lean toward `after` and a lean toward "the
  new thing" cannot be told apart.
- **Arms chosen to separate the leads from trims:** two that move stitch
  direction without moving trims much (the `design_angle` and `per_stroke` arms),
  two that move trims and density together (the Column lane `lettering_columns`
  and `columns_words`), the equal-pitch Column redraw that `full-density` was
  meant to be (density held, construction changed), and `split_satin_above_mm`
  7.0 (long crosses). Six arms x 8 to 10 logos = **48 to 60 pairs**, plus the
  render directory KEPT and the stitch counts written into the export, so
  every pair is scorable (a third of the pairs here were not).
- **Directions written down before the sitting:** `flow_circvar` lower,
  `longest_jump_mm` lower, `long_share` LOWER (the reverse of this doc's
  hypothesis, as this data suggests), `trims_per_1000` lower,
  `thread_density` higher. He chose a side on 43% of pairs here, so 60 pairs
  should give about 25 decided; that is the least that puts a sides-only
  interval near +/-0.3.

## 11. The ROADMAP phase-1 exit, restated against this instrument

*Exit: "on real customer designs, the metric's ranking agrees with Kent's
visual ranking, and nothing he judges better ever scores worse."*

- **Clause 1 (agrees):** not met. On the 76 measured pairs the only readings
  that clear chance on both statistics and both intervals are the trim
  family, which is a price column, not a fidelity or a construction score.
  The density and flow candidates built from his own words do not, except
  `flow_circvar` with ties in, which is one sitting's.
- **Clause 2 (never scores his pick worse):** fails on every candidate (7 to
  24 pairs each, section 7).
- **What changed since #842:** the n under the construction-side readings went
  from 26 (fidelity) to 76, and the question "is it density?" has an answer
  at this n: not density per area. **What did not change:** the trims are
  still the one thing that tracks his picks.

No phase advance is proposed; that call is Kent's.

*(measured 2026-10-12 - `digitizer/tools/eye_pairs/density_flow.py report
--markdown` over `docs/eye-pairs-2026-10-12/density-flow-inputs.json`;
Windows, python 3.12; labels from `docs/eye-pairs-2026-10-11/pooled-inputs.json`)*
