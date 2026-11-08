# Calibrated judge, held-out result (2026-11-08): FAIL

**FAIL on both halves of the pre-registered bar.** On the 92 held-out pairs the
calibrated judge scores **kappa +0.33** (3-way linear-weighted, ties in,
against Kent's original picks). The 95% CI over pairs is **[+0.18, +0.47]**,
and over designs **[+0.21, +0.43]**. The bar needed kappa >= +0.55 AND a
pair-CI lower bound > +0.34. It got +0.33 and +0.18. The old, uncalibrated
judges score **+0.34 [+0.18, +0.50]** on the same 92 pairs through the same
function, and the 11-06 judge scored +0.34 on its own 99. **The rubric moved
where the judge goes wrong. It did not make the judge agree with Kent more.**

Per `PRE-REGISTRATION.md` ("What a result licenses"), the failure is the
result. There is no re-run, no re-tuned rubric and no subset chosen
afterwards. Nothing here goes to `vlm-prescreen`, and nothing flips.

## How it was run

- **The rubric.** `RUBRIC.md` was frozen at sha256 `16836a48…1b243`
  (Amendment 1), with `vlm_judge.PROMPT` unchanged (`24acb296…095a`). Every
  one of the 99 rows in `heldout-verdicts.jsonl` carries that `rubric_sha256`.
  None was unscored.
- **The judges.** Fresh agents saw only the frozen prompt and rubric and each
  pair's pictures: LEFT, RIGHT, the art, and both 3x crops, under blind ids
  H001 to H099. That is 92 held-out pairs and 7 identical controls in one
  seeded shuffle. They gave one verdict per pair, in order A.
- **The key.** The sealed key was built by `heldout-kit` and kept outside the
  judges' folder. After the run it was copied here as `heldout-key.json`, so
  the score re-runs from the repo alone. The verdicts' L / R map to before /
  after through each pair's `base_side`. `vlm_judge.to_label` on the kit's own
  sealed row must give the same label, and it did for all 92.
- **The score.** Run `python -m tools.eye_pairs.judge_calibration score`. It
  wraps the repo's `vlm_judge._kappas` (the path behind both
  `vlm-judge*/analysis.json`), with bootstrap seed 20261104, and writes
  `heldout-analysis.json`. `test_the_committed_heldout_score_is_the_one_the_code_makes`
  re-derives it.

## The 3x3 table (Kent rows, judge columns, n 92)

| Kent \ judge | before (base) | tie | after (arm) | total |
|---|---:|---:|---:|---:|
| **before** | 11 | 1 | 4 | 16 |
| **tie** | 20 | 14 | 15 | 49 |
| **after** | 4 | 3 | 20 | 27 |
| total | 35 | 18 | 39 | 92 |

The old judges on the same 92 pairs:

| Kent \ old judge | before | tie | after |
|---|---:|---:|---:|
| **before** | 11 | 5 | 0 |
| **tie** | 9 | 35 | 5 |
| **after** | 4 | 15 | 8 |

## Where it still disagrees

The rubric fixed the failure it was built for, then overshot.

| Disagreement class | Old judges | Calibrated |
|---|---:|---:|
| Judge tie, Kent picked a side | 20 | **4** |
| Judge picked a side, Kent tie | 14 | **35** |
| Opposite sides | 4 | **8** |

- **The big hole: Kent's ties.** Kent called a tie on 49 of the 92 held-out
  pairs. The calibrated judge called a tie on 14 of those. It picked a side on
  35, about evenly (20 base, 15 arm), so these are not one consistent
  preference Kent missed. 22 of the 35 were at confidence 1 or 2. Their
  reasons read "damn near the same" followed by a single letter detail: a
  notch, a foot, a kink. The rubric's "lettering first" made the judge hunt
  for a letter-level difference, and on near-identical pairs it always found
  one. The 7 identical controls were all called ties, so the judge does see
  "no difference" when there is truly none. What it cannot do is call a small
  visible difference not worth choosing.
- **Opposite sides: 8 pairs, mostly confident reads of small strokes.** Two
  are tires (one at confidence 1: "black on black hides direction"). The
  others are one each of bridge, drone, fremont, proseal, jakarta and
  dot_music. In 3 of the 8 the judge decided on stray crossover stitches, not
  on letter shape (H072 drone, H086 dot_music, H095 tires). In the other 5 it
  decided on one stroke's edge or turn.
- **By kind of design.** The Kent-tie misses cluster on the dense
  block-lettering logos, where a pair of renders differs in a few letter
  details:

  | design | n | agree | judge side, Kent tie | opposite | judge tie, Kent side |
  |---|---:|---:|---:|---:|---:|
  | drone | 10 | 3 | 6 | 1 | 0 |
  | becker | 10 | 5 | 5 | 0 | 0 |
  | golden_tee | 10 | 4 | 5 | 0 | 1 |
  | mfab | 6 | 2 | 3 | 0 | 1 |
  | bridge | 11 | 7 | 3 | 1 | 0 |
  | fremont | 8 | 4 | 3 | 1 | 0 |
  | tires | 9 | 5 | 2 | 2 | 0 |
  | proseal | 6 | 3 | 2 | 1 | 0 |
  | the other 10 designs | 22 | 12 | 6 | 2 | 2 |

  Drone, becker and golden_tee hold 16 of the 35 Kent-tie misses.

## Secondaries (reported, promoted to nothing)

- **Sides only** (the 39 pairs both decided): kappa +0.57, CI over pairs
  [+0.28, +0.82], over designs [+0.35, +0.78]. The old judges on their 23
  decided pairs: +0.66 [+0.37, +0.91]. When both sides commit, the calibrated
  judge mostly agrees with Kent. It just commits far more often than he does.
- **By set.** 11-04 (n 34): calibrated +0.35 [+0.09, +0.58] against old
  +0.47 [+0.23, +0.69]. 11-06 (n 58): calibrated +0.31 [+0.14, +0.49]
  against old +0.26 [+0.05, +0.45]. It is worse on the 11-04 sitting and
  slightly better on 11-06. Both intervals overlap heavily.
- **Controls.** 7 of 7 identical pairs were called a tie. Side balance on
  live pairs: 41 L, 33 R, 18 tie. Mean confidence 2.79.
- **Exploratory, post hoc, licenses nothing.** Reading the judge's
  low-confidence sides as ties does not rescue it. Confidence <= 1 read as a
  tie gives +0.37 [+0.22, +0.52]. Confidence <= 2 gives +0.36 [+0.18, +0.53].
  Both still fail the bar. This was computed after the result and is not the
  pre-registered statistic.

## Known limits (from the pre-registration, still true)

- Kent's own repeat agreement on the 11-02 sitting was 1 of 4, so his ceiling
  is unmeasured and may sit near or below the +0.55 bar.
- Kent labelled the 11-06 pairs on the 09-18 to 10-08 renders. The judge saw
  re-drawn pictures.
- The 92 pairs are spent on this rubric freeze. A new rubric needs a new
  pre-registration and newly labelled pairs.
