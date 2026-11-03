# pro-lettering-1102: the sitting, 2026-11-03

Kent sat all 64 pairs (56 live, 4 identical, 4 repeat) on 2026-11-03,
08:39 to 08:48 (-06:00): `picks.jsonl` holds 64 lines, 64 distinct pairs, no
undo rows. `analyse` ran once against the sealed kit; its full output is
`analysis.txt`, the inputs it read are `sitting-inputs.json`, the sealed key
(`arms.json`) and the manipulation deltas (`manipulation.json`) are committed now
that the sitting is over, as `PRE-REGISTRATION.md` said. **This file judges and
flips nothing.** Kappa is chance-corrected throughout; no raw agreement figure
exists here (ROADMAP gate 4).

## What the registered reads say

- **The trims control did not replicate** (`trims_per_1000` on the trims-stratum
  arm). Per the pre-registration: *read nothing else in the table as a finding.*
  The primary table has no pair of intervals clear of zero on both resamplings.
- On the 51 pairs where trims were held, `trims_per_1000` reads **below chance**
  (kappa sides -0.41, designs CI [-0.63, -0.10]): when the arm did not change
  cuts, Kent's side tended to be the one with MORE trims per 1000. That is a read
  of what he weighed against a metric the arm did not move, not evidence that he
  likes trims; with the control failed it stays a lead.
- Distance to the pro (population A, 29 pairs): cuts +0.12, hops +0.00 (n 8),
  needle-up mm -0.02, every interval spanning zero, "no evidence either way".
  His pick was farther from the pro's cut count on 6 of 10 decided pairs, hops 3
  of 8, needle-up mm 6 of 14 (counts, not a rate to quote).
- The registered expected picks against his: kappa +0.07 [-0.24, +0.37], "no
  evidence either way".

## Controls: how much to trust the picks

- Identical pairs called a tie: **4 of 4** (good).
- Repeats answered differently: **3 of 4** (bad: the same pair got a different
  answer three times of four).
- Sides: 23 left, 7 right among the 30 pairs he chose a side on. The pre-registered
  note says a lopsided count is a side habit; the shuffle put the base on the left
  in 28 of 56 live pairs, so this is his, not the kit's.
- 26 of 56 live pairs were called a tie.

Together: many ties, a side lean, and unstable repeats. The sitting is a weak
instrument for the narrow reads; it does not support or refute the trim family.

## Per arm (counts; n is far too small for a kappa per arm)

`before` = the base side, `after` = the arm (flag turned OFF). The last column is
whether his label equals the kit's `expected_label` (ties count when the
expected label is a tie); the pre-registration's table says "base" for every arm,
but the stored expected label also follows the metric movement, so treat the
column as the kit's own scoring, not the table's.

| arm | manipulation check | live pairs | chose arm side | chose base side | tie | label equals expected |
|---|---|---|---|---|---|---|
| `corner_fold_off` | pass | 8 | 0 | 3 | 5 | 2 of 8 |
| `italic_lean_off` | **advisory (fail)** | 2 | 0 | 0 | 2 | 0 of 2 |
| `text_lean_off` | pass | 10 | 1 | 5 | 4 | 4 of 10 |
| `inside_stagger_off` | pass | 11 | 2 | 4 | 5 | 1 of 11 |
| `script_strokes_off` | **advisory (fail)** | 1 | 1 | 0 | 0 | 0 of 1 |
| `fold_slivers_off` | **advisory (fail)** | 1 | 0 | 1 | 0 | 0 of 1 |
| `lane_off` | **advisory (fail)** | 11 | 2 | 6 | 3 | 8 of 11 |
| `exit_next_off` | **advisory (fail)** | 12 | 1 | 4 | 7 | 1 of 12 |

**Advisory means not a pre-registered read.** Five arms failed the manipulation
check and Kent ruled 2026-11-03 "Sit as built": `italic_lean_off`,
`script_strokes_off`, `fold_slivers_off` (under `min_live_logos` after the
amendment's drop), `lane_off` and `exit_next_off` (moved and held on too few
logos). Their pairs are in every all-pairs row above, as the pre-registration
said, and absent from the passing-arms-alone table. Read them as counts only.
Across the three passing arms he chose the base side 12 times, the arm side 3,
and tied 14: the older construction (flag OFF) was not preferred, which is the
direction "base" predicted, on counts too small for an interval.

## What did not go as pre-registered

- The trims control failed to replicate, so the registered reading stops there.
- Five of eight arms fell to advisory (three of them from the budget drop in
  Amendment 1, which removed the logos where they had effect).
- Repeat stability (1 of 4 same) is a result about the sitting, not a registered
  control threshold; the pre-registration set no cut-off for it.
- No flag is flipped by this sitting: `lane_off` and `exit_next_off` are
  FABRIC-classified (ROADMAP gate 1) and nothing here would settle them.
