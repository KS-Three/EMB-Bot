# Does the yardstick agree with Kent's eye? Pooled over every labelled sitting - 2026-10-11

ROADMAP phase 1 exits on *"the metric's ranking agrees with Kent's visual
ranking, and nothing he judges better ever scores worse."* The last attempt
(`docs/yardstick-vs-kents-eye-2026-08-28.md`) had six verdicts, no pairs, and
could not be settled. Since then Kent has labelled 144 before | after pairs
over nine sittings. This pools them. Gate 4 holds throughout: **no raw
agreement figure appears below or is computed by the tool** - only Cohen's
kappa, its bootstrap interval, and the n it rests on.

## The answer

**Not met, and the evidence we have points away from "agrees" for the
fidelity yardstick; it does not settle the question either way.** Of 144
judged pairs, 115 are in scope (Kent's own call took `screenshot` and
`gaulke` off the comparison; 7 logos remain). On 49 of those he chose a side
(34 after, 15 before), on 43 he saw no difference and on 23 he called both
bad. Only **26 of the 115 pairs (16 where he chose a side) carry a fidelity
reading the scorecard itself accepts**, and 20 of those 26 are becker or
enthusiast: the instrument refuses 33 more (every drone, bridge, fremont and
golden_tee pair that has a reading: gradient-route logos, ink ambiguous), and
the other 56 have only price-table figures or nothing (21 of the 144 have no
instrument row at all). On those 26, no fidelity instrument clears chance on
both intervals: `lost_frac` +0.00 [-0.33, +0.29] on the 16 pairs where he
chose a side, -0.08 [-0.31, +0.16] with ties counted (n = 26); `lost_elements`,
`ragged_mm` and `uncovered_ink_frac` the same. The second clause fails
outright: **every instrument that has data
scores Kent's pick *worse* on 3 to 10 pairs** (24 for stitch count), and on
both 10-07 Becker lettering pairs seven fidelity instruments do it at once
(list below, with margins). The one family that lands above chance is the
**trim count** (`trims` +0.28 [+0.12, +0.43], n = 90; `trims_per_1000` and the
trims on changed shapes the same, n = 53) - a price column, not part of the
scorecard's fidelity score, and consistent with the trim and border notes in
Kent's own words. Read the intervals as wide: 7 logos, mostly lettering
changes, 26 fidelity pairs. The 2026-08-28 finding that element COUNT tracks
his judgement does not replicate on pairs (`lost_elements` -0.08 [-0.36,
+0.23], n = 20). No phase advance rests on this; that call is Kent's.

## 1. Inventory - every labelled sitting on main

`before` / `after` are the page's LEFT / RIGHT: shipped / flag for every arm
except the two old-engine arms (`ref_0827`, `ref_0930am`), where `before` is
the OLD engine. `same` is Kent's "no difference", `both_bad` his "both bad";
the pool maps both to a tie ("neither side preferred") and the sensitivity
table below drops `both_bad` instead. Nothing recorded as null is pooled.

| sitting | date | judged | after | before | same | both_bad | arms | pairs with instrument rows |
|---|---|---|---|---|---|---|---|---|
| `flags-0918-0928` | 2026-09-18..2026-09-28 | 77 | 16 | 8 | 30 | 23 | `area_weighted`, `design_angle`, `directional_comp`, `lettering_column`, `patch_junctions`, `per_stroke`, `phantom_dissolve`, `polygon_axis`, `rail_comp`, `rails_follow_edge`, `ref_0827`, `wide_columns` | 63 |
| `envelope-0930` | 2026-09-30 | 7 | 2 | 0 | 2 | 3 | `rail_envelope` | 7 |
| `evening-0930` | 2026-09-30 | 13 | 1 | 3 | 5 | 4 | `phantom_dissolve`, `ref_0930am` | 13 |
| `texture-0930` | 2026-10-01 | 7 | 0 | 1 | 6 | 0 | `rails_symmetric`, `split_7mm` | 7 |
| `off-flags-1003` | 2026-10-03 | 19 | 2 | 5 | 8 | 4 | `bean_letters`, `cap_recentre`, `split_off` | 19 |
| `density-1007` | 2026-10-07 | 6 | 2 | 1 | 0 | 3 | `lettering_columns` | 6 |
| `letterform-1007` | 2026-10-07 | 2 | 1 | 0 | 0 | 1 | `letterform_priors` | 2 |
| `columns-flip-1008` | 2026-10-08 | 6 | 5 | 0 | 0 | 1 | `columns_words` | 6 |
| `full-density-1008` | 2026-10-08 | 7 | 6 | 0 | 0 | 1 | `lettering_columns` | 0 |

| sitting | labels | instrument rows |
|---|---|---|
| `flags-0918-0928` | `docs/eye-pairs-2026-09-28/kent-notes.json` (the 34 first-sitting docs and the rebuilt 77-pair page's, ids folded) | the 2026-09-18 render directory, gitignored on Kent's laptop; `lost_frac` halves and `uncovered_ink_frac` recomputed from its 96 stored designs (no digitize; `lost_frac` reproduces the stored value to 4 dp on all 96) |
| `envelope-0930` | `docs/eye-pairs-2026-09-30/kent-notes.json` | `rail-envelope-corpus.json` (stitches, trims, bare satin) |
| `evening-0930` | same file, `third_sitting` | `three-changes-corpus.json`, `dissolve-corpus.json` (stitches, trims) |
| `texture-0930` | same file, `fourth_sitting` | `texture-corpus.json` (stitches only) |
| `off-flags-1003` | `docs/eye-pairs-2026-10-03/kent-notes.json` | `price-tables.json` (stitches, trims) |
| `density-1007` | `docs/eye-pairs-2026-10-07/kent-notes.json`, `columns_sitting` | the `columns-sitting` worktree's render directory (gitignored) |
| `letterform-1007` | same file, `pairs` | the `letterform-priors` worktree's render directory (gitignored) |
| `columns-flip-1008` | `docs/eye-pairs-2026-10-11/kent-notes-store-export.json` (**new: in the page's store, on no earlier export**) | `docs/eye-pairs-2026-10-08/flip/price-tables.json` |
| `full-density-1008` | same new export | none found |

**Labelled but not pooled.** `words-1008` (5 pairs drawn, no verdict recorded
anywhere). `words-columns-1008` (3 pairs, one chat verdict over all three,
*"After is better"* - no per-pair labels exist, so no pair is invented from
it). `pro-1001` (1 pair, Kent: the pro's Becker is better; a different
digitizer's file against ours, not a same-engine comparison - for the record
the pro's file has more trims, 57 against 49, and more stitches). The
2026-08-27 and 09-03 reviews are design-level verdicts, not pairs. The
2026-09-11 agreement study's "eye" was Claude's, not Kent's. Two sittings
whose labels are pooled but whose instruments are not: `full-density-1008`
(no render directory for that page survives: the `columns-density` worktree
holds the six-pair `density-1007` redraw, which has no golden_tee, and he
labelled seven) and the 14 `flags-0918-0928` pairs in the inventory's
"pairs with instrument rows" gap (nine `rails_follow_edge` pairs - the arm is
not in the 09-18 directory - and five tires pairs judged after the cutout
rebuild, which that directory does not hold).

**What changed in the labels' own store.** The only difference between the
Flag Before After store and the exports on main is `split_7mm` / screenshot
(main: verdict null; store: `same`), and screenshot is out of scope anyway.

## 2. The method

Tool: `digitizer/tools/eye_pairs/pooled.py` (`python -m tools.eye_pairs.pooled
report --markdown`); inputs `docs/eye-pairs-2026-10-11/pooled-inputs.json`,
built once by `pooled_build.py`. Tests: `tests/test_eye_pairs_pooled.py`
(kappa on a hand-made 10-row table against its hand-computed value; the pool
refuses a label vocabulary it does not know).

- **Kent's pick** per pair is `before`, `after`, or tie (`same` and
  `both_bad`). **An instrument's pick** is the side it scores better, or tie
  when the two values are equal at stored precision. Direction follows
  `analysis.METRICS`; the price columns have none there and are read as COST
  (fewer stitches, fewer trims better) as a stated hypothesis.
- **Sides only (2x2, unweighted kappa)**: pairs where Kent chose a side AND the
  instrument did. This is the exit clause read directly. Pairs where the
  instrument was silent are counted in their own column, not hidden.
- **Ties in (3x3, linear-weighted kappa, before < tie < after)**: every
  judged pair, so an instrument is charged for preferring a side where Kent
  saw nothing, and credited for silence where he was silent.
- **Chance** is the expected agreement of each table's own marginals, so a
  mix that is mostly ties cannot flatter anything.
- **Intervals**: percentile bootstrap, 10,000 resamples, seed fixed. Two
  are shown: resampling PAIRS, and resampling whole FIXTURES (pairs from one
  logo are not independent). A reading of *above chance* or *below chance*
  needs both to clear zero, and nothing is read under 10 pairs.
- **Refusals**: a pair whose side the scorecard refused on (`refusal_for`)
  is left out of that instrument and counted, the default `analysis.py` uses.
  The sensitivity table shows what ignoring the refusals does.
- **Fan census** is not computed: it needs a live plan (text-tagged letters,
  pull compensation) that stored designs do not carry, and re-digitizing
  would score today's engine, not the one Kent looked at. n = 0, stated.

## 3. Kappa per instrument

Scope: 115 pairs after removing `screenshot` and `gaulke`.

| instrument | n scored | refused, left out | n Kent chose a side | instrument silent there | kappa, sides only (2x2) | 95% CI pairs | 95% CI fixtures | kappa, ties in (3-way, weighted) | 95% CI pairs | 95% CI fixtures | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **fidelity (the scorecard's own)** | | | | | | | | | | | |
| `lost_frac` | 26 | 33 | 16 | 0 | +0.00 | [-0.33, +0.29] | [-0.28, +0.33] | -0.08 | [-0.31, +0.16] | [-0.35, +0.18] | sides: no evidence either way; with ties: no evidence either way |
| `unsewn_frac` | 20 | 33 | 6 | 5 | +0.18 | [+0.00, +0.67] | [+0.12, +0.18] | +0.13 | [-0.18, +0.47] | [+0.00, +0.25] | sides: n too small (<10); with ties: no evidence either way |
| `overshoot_frac` | 20 | 33 | 11 | 0 | +0.29 | [-0.26, +0.81] | [-0.36, +0.70] | +0.15 | [-0.16, +0.45] | [-0.15, +0.50] | sides: no evidence either way; with ties: no evidence either way |
| `uncovered_ink_frac` | 26 | 33 | 13 | 3 | +0.04 | [-0.34, +0.43] | [+0.00, +0.25] | -0.04 | [-0.29, +0.23] | [-0.36, +0.13] | sides: no evidence either way; with ties: no evidence either way |
| `uncovered_total_mm2` | 47 | 0 | 2 | 15 | n/a | n/a | n/a | +0.15 | [-0.04, +0.37] | [-0.05, +0.41] | sides: n too small (<10); with ties: no evidence either way |
| `lost_elements` | 20 | 33 | 10 | 1 | -0.03 | [-0.54, +0.44] | [-0.67, +0.29] | -0.08 | [-0.36, +0.23] | [-0.39, +0.22] | sides: no evidence either way; with ties: no evidence either way |
| `ragged_mm` | 26 | 33 | 14 | 2 | +0.03 | [-0.35, +0.43] | [-0.08, +0.18] | -0.04 | [-0.31, +0.25] | [-0.12, +0.18] | sides: no evidence either way; with ties: no evidence either way |
| `hausdorff_mm` | 20 | 33 | 9 | 2 | +0.40 | [+0.00, +0.78] | [+0.00, +0.72] | +0.20 | [-0.14, +0.54] | [-0.14, +0.50] | sides: n too small (<10); with ties: no evidence either way |
| `artfid` | 18 | 29 | 8 | 1 | +0.25 | [-0.43, +0.75] | [-0.67, +1.00] | +0.22 | [-0.20, +0.58] | [-0.24, +0.71] | sides: n too small (<10); with ties: no evidence either way |
| **price (the eye-pairs price table; cost reading, lower is better)** | | | | | | | | | | | |
| `stitches` | 97 | 0 | 39 | 0 | -0.30 | [-0.55, +0.01] | [-0.44, -0.05] | -0.10 | [-0.23, +0.03] | [-0.18, -0.02] | sides: no evidence either way; with ties: no evidence either way |
| `trims` | 90 | 0 | 31 | 7 | +0.37 | [+0.04, +0.68] | [+0.18, +0.62] | +0.28 | [+0.12, +0.43] | [+0.12, +0.41] | sides: above chance; with ties: above chance |
| `trims_per_1000` | 53 | 0 | 22 | 0 | +0.53 | [+0.15, +0.83] | [+0.21, +0.89] | +0.28 | [+0.11, +0.44] | [+0.10, +0.46] | sides: above chance; with ties: above chance |
| `changed_trims` | 53 | 0 | 18 | 4 | +0.56 | [-0.08, +1.00] | [+0.16, +0.86] | +0.27 | [+0.08, +0.44] | [+0.04, +0.44] | sides: no evidence either way; with ties: above chance |
| **arm-specific / not computed** | | | | | | | | | | | |
| `bare_satin_pct` | 5 | 0 | 2 | 0 | n/a | n/a | n/a | +0.00 | [+0.00, +0.00] | [+0.00, +0.00] | sides: n too small (<10); with ties: n too small (<10) |
| `fan_census` | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | not computed (see below) |

Sensitivity - the same statistics under three alternative rules:

| variant | instrument | n scored | n Kent chose a side | kappa, sides only | kappa, ties in (3-way) |
|---|---|---|---|---|---|
| screenshot and gaulke put back | `lost_frac` | 26 | 16 | +0.00 [-0.33, +0.29] | -0.08 [-0.31, +0.16] |
| screenshot and gaulke put back | `unsewn_frac` | 20 | 6 | +0.18 [+0.00, +0.67] | +0.13 [-0.18, +0.47] |
| screenshot and gaulke put back | `overshoot_frac` | 20 | 11 | +0.29 [-0.26, +0.81] | +0.15 [-0.16, +0.45] |
| screenshot and gaulke put back | `uncovered_ink_frac` | 26 | 13 | +0.04 [-0.34, +0.43] | -0.04 [-0.29, +0.23] |
| screenshot and gaulke put back | `lost_elements` | 20 | 10 | -0.03 [-0.54, +0.44] | -0.08 [-0.36, +0.23] |
| screenshot and gaulke put back | `ragged_mm` | 26 | 14 | +0.03 [-0.35, +0.43] | -0.04 [-0.31, +0.25] |
| screenshot and gaulke put back | `hausdorff_mm` | 20 | 9 | +0.40 [+0.00, +0.78] | +0.20 [-0.14, +0.54] |
| screenshot and gaulke put back | `artfid` | 18 | 8 | +0.25 [-0.43, +0.75] | +0.22 [-0.20, +0.58] |
| screenshot and gaulke put back | `stitches` | 123 | 43 | -0.24 [-0.50, +0.05] | -0.06 [-0.17, +0.05] |
| screenshot and gaulke put back | `trims` | 116 | 35 | +0.47 [+0.17, +0.75] | +0.29 [+0.15, +0.42] |
| `both_bad` pairs dropped, not folded into the tie | `lost_frac` | 21 | 16 | +0.00 [-0.33, +0.30] | -0.06 [-0.33, +0.22] |
| `both_bad` pairs dropped, not folded into the tie | `unsewn_frac` | 16 | 6 | +0.18 [+0.00, +0.67] | +0.10 [-0.22, +0.46] |
| `both_bad` pairs dropped, not folded into the tie | `overshoot_frac` | 16 | 11 | +0.29 [-0.26, +0.81] | +0.21 [-0.17, +0.56] |
| `both_bad` pairs dropped, not folded into the tie | `uncovered_ink_frac` | 21 | 13 | +0.04 [-0.34, +0.43] | -0.08 [-0.38, +0.25] |
| `both_bad` pairs dropped, not folded into the tie | `lost_elements` | 16 | 10 | -0.03 [-0.54, +0.44] | -0.11 [-0.44, +0.24] |
| `both_bad` pairs dropped, not folded into the tie | `ragged_mm` | 21 | 14 | +0.03 [-0.34, +0.43] | -0.03 [-0.31, +0.26] |
| `both_bad` pairs dropped, not folded into the tie | `hausdorff_mm` | 16 | 9 | +0.40 [+0.00, +1.00] | +0.25 [-0.14, +0.63] |
| `both_bad` pairs dropped, not folded into the tie | `artfid` | 14 | 8 | +0.25 [-0.43, +0.75] | +0.28 [-0.19, +0.70] |
| `both_bad` pairs dropped, not folded into the tie | `stitches` | 75 | 39 | -0.30 [-0.55, +0.00] | -0.14 [-0.30, +0.03] |
| `both_bad` pairs dropped, not folded into the tie | `trims` | 68 | 31 | +0.37 [+0.04, +0.68] | +0.34 [+0.14, +0.53] |
| the scorecard's refusals ignored | `lost_frac` | 59 | 26 | -0.05 [-0.32, +0.18] | -0.12 [-0.28, +0.04] |
| the scorecard's refusals ignored | `unsewn_frac` | 53 | 10 | +0.14 [+0.00, +0.55] | +0.18 [-0.02, +0.41] |
| the scorecard's refusals ignored | `overshoot_frac` | 53 | 17 | +0.27 [-0.15, +0.67] | +0.10 [-0.09, +0.29] |
| the scorecard's refusals ignored | `uncovered_ink_frac` | 59 | 20 | +0.04 [-0.25, +0.30] | +0.03 [-0.13, +0.19] |
| the scorecard's refusals ignored | `lost_elements` | 53 | 20 | -0.04 [-0.39, +0.27] | -0.03 [-0.20, +0.15] |
| the scorecard's refusals ignored | `ragged_mm` | 59 | 22 | +0.05 [-0.19, +0.30] | +0.01 [-0.16, +0.18] |
| the scorecard's refusals ignored | `hausdorff_mm` | 53 | 18 | +0.51 [+0.05, +0.88] | +0.29 [+0.08, +0.48] |
| the scorecard's refusals ignored | `artfid` | 47 | 12 | +0.03 [-0.50, +0.53] | +0.06 [-0.15, +0.29] |
| the scorecard's refusals ignored | `stitches` | 97 | 39 | -0.30 [-0.55, +0.01] | -0.10 [-0.23, +0.03] |
| the scorecard's refusals ignored | `trims` | 90 | 31 | +0.37 [+0.04, +0.68] | +0.28 [+0.12, +0.43] |

How to read it, in four sentences. The fidelity family shows nothing in
either direction at this n; where a point estimate is positive
(`hausdorff_mm` sides-only +0.40 on 9 pairs, `overshoot_frac` +0.29 on 11)
its interval spans zero or the pair count is under the reading floor. The
trim columns are the only ones that clear chance on both intervals, and their
pair interval stays clear of zero in all three sensitivity variants. Stitch
count leans *below* chance (the fixture interval excludes zero, the pair
interval only just includes it): when Kent chooses a side he tends to choose
the denser one, so a cost reading of stitches points the wrong way and
nothing here supports treating it as a quality signal.
Ignoring the refusals widens `lost_frac` to 59 pairs and moves it to -0.05
sides-only and -0.12 ties-in, still no evidence of agreement. The one
fidelity reading that does clear zero on that last rule is `hausdorff_mm`
(+0.51 [+0.05, +0.88] sides-only on 18 pairs, +0.29 [+0.08, +0.48] with ties on
53) - on rows the scorecard itself marks as not an engine result, so it is a
lead to re-test on accepted pairs, not a finding.

## 4. Pairs where Kent's pick scores WORSE

Pairs where Kent chose a side, the instrument chose the other, and neither
side was refused. "Margin" is how much worse his pick scored, in the
instrument's own units (so ordered within an instrument, not across). Pair ids
are `sitting:arm:fixture`; the pictures are on the Flag Before After page and
in `docs/eye-pairs-2026-*/`.

**Open these first - pairs that fail on several fidelity instruments at once:**

| pair | Kent | fidelity instruments that score his pick worse |
|---|---|---|
| `density-1007:lettering_columns:becker` | after | 7: `lost_frac`, `unsewn_frac`, `uncovered_ink_frac`, `lost_elements`, `ragged_mm`, `hausdorff_mm`, `artfid` |
| `letterform-1007:letterform_priors:becker` | after | 7: `lost_frac`, `unsewn_frac`, `overshoot_frac`, `uncovered_ink_frac`, `lost_elements`, `ragged_mm`, `artfid` |
| `flags-0918-0928:rail_comp:enthusiast` | after | 4: `uncovered_ink_frac`, `lost_elements`, `ragged_mm`, `hausdorff_mm` |
| `flags-0918-0928:ref_0827:enthusiast` | after | 4: `lost_frac`, `overshoot_frac`, `ragged_mm`, `hausdorff_mm` |
| `columns-flip-1008:columns_words:becker` | after | 3: `lost_frac`, `uncovered_ink_frac`, `ragged_mm` |
| `columns-flip-1008:columns_words:golden_tee` | after | 3: `lost_frac`, `uncovered_ink_frac`, `ragged_mm` |
| `flags-0918-0928:rail_comp:becker` | after | 3: `lost_frac`, `unsewn_frac`, `uncovered_ink_frac` |
| `flags-0918-0928:ref_0827:becker` | after | 3: `overshoot_frac`, `lost_elements`, `ragged_mm` |
| `flags-0918-0928:design_angle:tires` | before | 2: `lost_elements`, `artfid` |
| `flags-0918-0928:lettering_column:enthusiast` | before | 2: `uncovered_ink_frac`, `ragged_mm` |
| `flags-0918-0928:wide_columns:becker` | before | 2: `lost_frac`, `overshoot_frac` |
| `columns-flip-1008:columns_words:bridge` | after | 1: `lost_frac` |
| `columns-flip-1008:columns_words:enthusiast` | after | 1: `lost_frac` |
| `columns-flip-1008:columns_words:fremont` | after | 1: `lost_frac` |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 1: `lost_elements` |

Both 10-07 Becker lettering pairs are Kent's *after*, and each carries a note
about something the fidelity instruments do not read: on `density-1007` *"the
stitch columns did its job but the stitch density is VERy different... the
before stitch density is better"* (the page was later ruled needs-work on
density), on `letterform-1007` *"the N was better before - everything else
was better after"* (the N is MASTER_SCOPE defect 59). The `ref_0827` pairs are
the old engine against today's, where the old engine sewed fewer stitches
(becker 6,702 against 17,700), so every cost-read price column scores today's
engine - which Kent picked on 7 of 9 logos - as worse.


### `lost_frac` (10 pairs) - dropped_elements lost_frac (unsewn + overshoot, summed)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:enthusiast` | after | 0.2459 | 0.2933 | 0.0474 |
| `columns-flip-1008:columns_words:enthusiast` | after | 0.2771 | 0.311 | 0.0339 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.4501 | 0.4698 | 0.0197 |
| `columns-flip-1008:columns_words:becker` | after | 0.0236 | 0.0381 | 0.0145 |
| `letterform-1007:letterform_priors:becker` | after | 0.023 | 0.0319 | 0.0089 |
| `density-1007:lettering_columns:becker` | after | 0.0327 | 0.0399 | 0.0072 |
| `columns-flip-1008:columns_words:bridge` | after | 0.2213 | 0.2283 | 0.007 |
| `flags-0918-0928:wide_columns:becker` | before | 0.0575 | 0.0541 | 0.0034 |
| `columns-flip-1008:columns_words:fremont` | after | 0.0302 | 0.0325 | 0.0023 |
| `flags-0918-0928:rail_comp:becker` | after | 0.0575 | 0.0597 | 0.0022 |

### `unsewn_frac` (3 pairs) - lost_frac half: artwork the stitch-out never covered

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 0.0192 | 0.0291 | 0.0099 |
| `letterform-1007:letterform_priors:becker` | after | 0.0135 | 0.018 | 0.0045 |
| `flags-0918-0928:rail_comp:becker` | after | 0.0033 | 0.0057 | 0.0024 |

### `overshoot_frac` (4 pairs) - lost_frac half: thread standing on cloth the artwork leaves bare

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:enthusiast` | after | 0.2378 | 0.2933 | 0.0555 |
| `flags-0918-0928:ref_0827:becker` | after | 0.0141 | 0.0542 | 0.0401 |
| `flags-0918-0928:wide_columns:becker` | before | 0.0542 | 0.0395 | 0.0147 |
| `letterform-1007:letterform_priors:becker` | after | 0.0094 | 0.0139 | 0.0045 |

### `uncovered_ink_frac` (7 pairs) - colour-free uncovered ink share

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 0.0629 | 0.0914 | 0.0285 |
| `letterform-1007:letterform_priors:becker` | after | 0.0584 | 0.0632 | 0.0048 |
| `columns-flip-1008:columns_words:becker` | after | 0.06 | 0.0629 | 0.0029 |
| `flags-0918-0928:rail_comp:enthusiast` | after | 0.0145 | 0.0172 | 0.0027 |
| `flags-0918-0928:rail_comp:becker` | after | 0.0305 | 0.0317 | 0.0012 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.0018 | 0.002 | 0.0002 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 0.0145 | 0.0144 | 0.0001 |

### `lost_elements` (6 pairs) - count of artwork elements lost

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:becker` | after | 42 | 63 | 21 |
| `letterform-1007:letterform_priors:becker` | after | 35 | 49 | 14 |
| `flags-0918-0928:design_angle:tires` | before | 31 | 27 | 4 |
| `flags-0918-0928:rail_comp:enthusiast` | after | 30 | 33 | 3 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 30 | 31 | 1 |
| `density-1007:lettering_columns:becker` | after | 49 | 50 | 1 |

### `ragged_mm` (8 pairs) - edge_smoothness ragged_mm

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 0.186 | 0.257 | 0.071 |
| `letterform-1007:letterform_priors:becker` | after | 0.176 | 0.187 | 0.011 |
| `flags-0918-0928:rail_comp:enthusiast` | after | 0.2 | 0.207 | 0.007 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 0.195 | 0.2 | 0.005 |
| `columns-flip-1008:columns_words:golden_tee` | after | 0.166 | 0.17 | 0.004 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 0.2 | 0.197 | 0.003 |
| `columns-flip-1008:columns_words:becker` | after | 0.18 | 0.183 | 0.003 |
| `flags-0918-0928:ref_0827:becker` | after | 0.197 | 0.199 | 0.002 |

### `hausdorff_mm` (3 pairs) - edge_smoothness hausdorff_mm

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:enthusiast` | after | 1.43 | 2.24 | 0.81 |
| `flags-0918-0928:rail_comp:enthusiast` | after | 2.24 | 2.4 | 0.16 |
| `density-1007:lettering_columns:becker` | after | 4 | 4.16 | 0.16 |

### `artfid` (3 pairs) - ARTFID composite (fidelity, not a quality percentage)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `density-1007:lettering_columns:becker` | after | 89.2 | 86.6 | 2.6 |
| `letterform-1007:letterform_priors:becker` | after | 89.6 | 89.2 | 0.4 |
| `flags-0918-0928:design_angle:tires` | before | 85.7 | 85.8 | 0.1 |

### `stitches` (24 pairs) - PRICE: stitch count (cost reading, hypothesis)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:becker` | after | 6702 | 17700 | 10998 |
| `flags-0918-0928:ref_0827:fremont` | after | 10363 | 19885 | 9522 |
| `flags-0918-0928:ref_0827:drone` | after | 9485 | 18558 | 9073 |
| `flags-0918-0928:ref_0827:bridge` | after | 11118 | 14608 | 3490 |
| `flags-0918-0928:wide_columns:becker` | before | 17700 | 15148 | 2552 |
| `off-flags-1003:bean_letters:fremont` | before | 20023 | 19173 | 850 |
| `density-1007:lettering_columns:fremont` | before | 20177 | 19471 | 706 |
| `envelope-0930:rail_envelope:becker` | after | 8297 | 8900 | 603 |
| `letterform-1007:letterform_priors:becker` | after | 9702 | 10217 | 515 |
| `off-flags-1003:bean_letters:enthusiast` | before | 2486 | 2234 | 252 |
| `flags-0918-0928:lettering_column:fremont` | before | 19885 | 19634 | 251 |
| `flags-0918-0928:directional_comp:drone` | after | 18558 | 18802 | 244 |
| `envelope-0930:rail_envelope:golden_tee` | after | 7966 | 8072 | 106 |
| `evening-0930:phantom_dissolve:golden_tee` | before | 8659 | 8554 | 105 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 2393 | 2492 | 99 |
| `flags-0918-0928:rail_comp:fremont` | after | 19885 | 19977 | 92 |
| `flags-0918-0928:lettering_column:enthusiast` | before | 2492 | 2426 | 66 |
| `columns-flip-1008:columns_words:bridge` | after | 18837 | 18870 | 33 |
| `off-flags-1003:bean_letters:golden_tee` | before | 8476 | 8468 | 8 |
| `flags-0918-0928:design_angle:tires` | before | 2345 | 2339 | 6 |
| `flags-0918-0928:directional_comp:enthusiast` | before | 2492 | 2486 | 6 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 2492 | 2496 | 4 |
| `texture-0930:rails_symmetric:golden_tee` | before | 8575 | 8573 | 2 |
| `off-flags-1003:cap_recentre:tires` | after | 2851 | 2853 | 2 |

### `trims` (9 pairs) - PRICE: trim count (cost reading, hypothesis)

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:drone` | after | 82 | 139 | 57 |
| `flags-0918-0928:ref_0827:bridge` | after | 105 | 123 | 18 |
| `flags-0918-0928:directional_comp:drone` | after | 139 | 153 | 14 |
| `flags-0918-0928:directional_comp:fremont` | before | 75 | 69 | 6 |
| `flags-0918-0928:ref_0827:becker` | after | 34 | 40 | 6 |
| `off-flags-1003:bean_letters:fremont` | before | 57 | 53 | 4 |
| `flags-0918-0928:ref_0827:enthusiast` | after | 21 | 24 | 3 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 24 | 25 | 1 |
| `envelope-0930:rail_envelope:becker` | after | 48 | 49 | 1 |

### `trims_per_1000` (5 pairs) - trims per 1000 stitches

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:enthusiast` | after | 8.78 | 9.63 | 0.85 |
| `flags-0918-0928:directional_comp:drone` | after | 7.49 | 8.14 | 0.65 |
| `density-1007:lettering_columns:drone` | after | 7.13 | 7.75 | 0.62 |
| `flags-0918-0928:directional_comp:fremont` | before | 3.77 | 3.32 | 0.45 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 9.63 | 10.02 | 0.39 |

### `changed_trims` (3 pairs) - PRICE: trims landing on the shapes the arm changed

| pair | Kent | before | after | margin (Kent's pick worse by) |
|---|---|---|---|---|
| `flags-0918-0928:directional_comp:drone` | after | 127 | 141 | 14 |
| `flags-0918-0928:directional_comp:fremont` | before | 62 | 56 | 6 |
| `flags-0918-0928:patch_junctions:enthusiast` | after | 2 | 3 | 1 |

## 5. Caveats that bound every figure above

1. **The 77-pair flags sitting is a proxy render.** Kent judged it on a
   cloud-rendered page (from 09-20) that was not kept; the instrument rows
   come from his laptop's 09-18 render of the same arms, which matches the
   cloud one to platform rounding (becker 17,700 against 17,701 stitches,
   bridge 14,608 against 14,607; fremont, drone, enthusiast, gaulke exact),
   not byte for byte. Tires is left unscored after 09-18 for exactly this
   reason (the cutout).
2. **Seven logos.** Pairs from one logo share its ink, its refusals and
   its artwork; the fixture interval is the honest one, and it is wide.
3. **Most labels are on lettering changes.** Kent's notes name density,
   flow, trims, borders and letters in place. The fidelity instruments read
   coverage and edge, not flow or density, so a weak result is partly a
   statement about what they measure.
4. **`both_bad` is not `same`.** The pool folds both into a tie; the
   sensitivity table drops `both_bad`. Neither changes a conclusion.
5. **Kappa moves with prevalence too**, which is why the ties-in and
   sides-only figures are both shown and neither is a quality percentage.
6. **Nothing here flips a flag, moves a gate, or proposes a phase advance.**

## What would move it

More pairs on logos the refusal classes accept (a sitting that is not
lettering-only), a labelled sitting on new fixtures so blinding is not spent
(`second-sitting-eleven-flags-2026-09-28` already notes the nine logos are
seen), and an instrument for what he actually writes - flow and stitch
density - since the trim family is the only thing that tracks his picks so far.

*(measured 2026-10-11 - `digitizer/tools/eye_pairs/pooled.py` over
`docs/eye-pairs-2026-10-11/pooled-inputs.json`; Windows, python 3.12; labels
read back from the Flag Before After store the same day)*
