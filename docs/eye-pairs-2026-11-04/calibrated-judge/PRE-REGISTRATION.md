# A calibrated vision judge (`calibrated-judge`): pre-registration, 2026-11-07

**Committed before any picture was opened.** Kent, 2026-11-07, verbatim: "The
quality scorer is on you, my human eye works just fine, why don't we develop
a new yard stick that develops you into reviewing these like a human? Maybe a
side by side camparison of ambiguous photos that can point you in the right
direction."

The two session judges so far track Kent above chance: +0.34 (n 99, 11-06)
and +0.36 (n 54, 11-04). Both fail on the same thing. They call a tie where
Kent picks a side, and the 11-06 judge never picked the arm where Kent picked
the base. This experiment teaches a judge from Kent's own reasons on a
CALIBRATION part of his labelled pairs. It then scores that judge ONCE, blind,
on a HELD-OUT part it never saw.

The twin of this file is `digitizer/tools/eye_pairs/judge_calibration.py`.
`digitizer/tests/test_judge_calibration.py` fails if the seed, fraction, bar
or manifest drift from what is written here. **This file judges nothing about
the engine and flips nothing.** Kappa is chance-corrected throughout. No raw
agreement figure is computed (ROADMAP gate 4).

## What was run before this was written

- **Committed analysis files.** This session read `vlm-judge/analysis.json`,
  `vlm-judge-100/analysis.json` and `RESULTS.md`. That includes their
  per-pair opposite-side rows: four 11-06 pairs and three 11-04 pairs, with
  fixture, arm and the judge's reason. No picture of any pair was opened.
- **The pool and split.** `judge_calibration.pool()` and `split()` were run,
  so Kent's labels for all 153 pairs were read by code to stratify. What was
  printed was the per-stratum counts (calibration / held-out), with no pair
  id beside a label.
- **Calibration counts.** The disagreement classes were counted on
  CALIBRATION only: 22 pairs. 11 are judge tie vs Kent side, 8 are judge side
  vs Kent tie, and 3 are opposite sides.
- **The 11-06 kit's sealed key, rebuilt.** That kit's `arms.json` and
  pictures are gone, so the key was rebuilt from the committed inputs with
  `vlm_judge.pro100_sealed` (the same shuffle, factored out of
  `kit_pro100`). It was verified against the committed results. Rescoring
  the committed verdicts through it gives the analysis table exactly
  (`[[8, 4, 0], [9, 43, 7], [4, 14, 10]]`). It also names the same four
  opposite-side pairs (P026 / P037 / P097 / P099, same fixture and arm), and
  its four identical pairs are the four the judge tied.

## The pool

- **11-04 (`vlm-judge`).** The `pro-lettering-1102` sitting has 56 live
  pairs. Minus Amendment 1's exclusions (P001, P003; P002 is an identical
  control) that leaves **54**. Kent's pick comes from
  `docs/eye-pairs-2026-11-02/pro-size-lettering/picks.jsonl`, through the
  sealed key. The design is the manifest's `design` (12 designs, 14 fixtures).
- **11-06 (`vlm-judge-100`).** **99** live pairs. Kent's label comes from
  `pooled-inputs.json` (`pooled.VOCABULARY`). The design is the fixture
  (6 designs).
- **De-duplicated** by (sitting, fixture, arm), keeping the first set's
  copy. The two sets come from disjoint sittings (11-02 against 09-18 to
  10-08), so **0 pairs** fall out. The pool is **153**.
- **Pair ids.** A pool id is `<set>:<kit pair id>`, for example
  `vlm-judge-100:P045`. That is the id the judge saw, so the manifest names
  no arm, side or label.

## The split

- **Seed 20261107, fraction 0.40.**
- **Strata.** The strata are (design, Kent's class before / tie / after).
  Taken in sorted order, each stratum's ids are sorted and then shuffled
  under the seed, and the lists are concatenated. One `u` is drawn from the
  seed. Position `i` goes to CALIBRATION when
  `floor(0.4*(i+1)+u) > floor(0.4*i+u)`, and to HELD-OUT otherwise.
- **What that guarantees.** Every stratum gets its 40% to within one pair.
- **Result: CALIBRATION 61** (20 from 11-04, 41 from 11-06), **HELD-OUT 92**
  (34 and 58).
- **Manifest.** `split-calibration.json` and `split-held-out.json` hold pair
  ids only, plus seed, fraction and `pool_sha256`
  `bc0f78c8253e52b2ad96ae7f1d6895804fb7eac6508f213d425c474fe1951376`.
  `judge_calibration split --check` recomputes both files, and the test does
  the same. The split is made once: `split` refuses to overwrite a different
  file.

## Phase A (this lane): the calibration kit

- **Selection.** From CALIBRATION only: every pair where the committed
  verdict and Kent disagree, in the three classes above, up to 25. With 22
  on file, all 22 enter. Over 25, it would be a seeded round-robin across the
  classes. No new judging is done.
- **The held-out manifest is never read here.** The kit builder opens
  `split-calibration.json` and no other manifest file. A guard refuses the
  held-out name, and a test spies on every file the builder opens.
- **11-04 pictures.** These are copied from the surviving
  `digitizer/eye_pairs_out/pro-lettering-1102/img/`, the files Kent and the
  judge saw.
- **11-06 pictures.** Those are gone, so only the designs of the calibration
  pairs in the kit are re-drawn. They use the 11-06 rule: the sitting's
  tree, `pro_pooled_build.sitting_size`, the sitting's base flags,
  `stitchviz.render_design` at 14 px/mm, and JPEG 92.
- **The page.** Each pair shows LEFT and RIGHT at one scale, padded to one
  canvas, as the judge saw them. It also shows a 3x crop of the window where
  the two differ most, Kent's original pick in that frame, the old judge's
  pick and reason, and a one-line reason box. The page is a local HTML file
  in a gitignored folder.
- **Reasons.** Through `judge_calibration serve`, each reason is written to
  `<kit>/reasons.json`. Opened from disk, the page keeps reasons in the
  browser and downloads the same JSON. Phase B reads that file.

## Phase B (a later lane): the rubric, then one blind run

- **The rubric.** It is written from CALIBRATION only: the kit, Kent's
  reasons, and the calibration pairs' pictures and verdicts. It lives in
  `RUBRIC.md` here, as plain text appended to the unchanged `vlm_judge.PROMPT`
  (sha256 `24acb29674ecca4b045c176cbb00ac971512ef510d4a7bea69233ce1c928095a`).
- **Frozen before held-out judging.** The rubric's sha256 is recorded in a
  commit (`RUBRIC-FREEZE.md`) that comes before the first held-out picture is
  opened. Every held-out verdict row carries `rubric_sha256`. A row with any
  other value is not scored. A rubric changed after that commit is a
  different experiment, with its own pre-registration and newly labelled
  pairs. These 92 are spent on the first freeze.
- **The judge.** It is a fresh Claude Code session that sees only
  `pairs.json`, the three pictures per pair, PROMPT and RUBRIC. It never sees
  a pair id's history, an arm, a flag, Kent's pick, or any file under
  `vlm-judge*/` (verdicts, analysis, RESULTS) or this folder's split files.
- **How it judges.** It works in order A only, with one verdict per pair,
  appended in batches before the next pair is opened, and never overwritten.
- **Controls.** The seven identical pairs of the two kits (11-04: 3, P002
  out; 11-06: 4) are shuffled in as controls and are not scored.
- **11-06 held-out pictures.** These are re-drawn by phase B under the same
  rule.

## The primary

- **The statistic.** It is computed on the **92 HELD-OUT pairs only**. It is
  the 3-way linear-weighted Cohen's kappa against Kent, **ties in**, through
  the repo's existing `analyse` path, `vlm_judge._kappas` (wrapped by
  `judge_calibration.primary`).
- **Intervals.** 95% percentile bootstrap over pairs and over designs (18
  design clusters), with bootstrap seed 20261104. `pooled.reading` is
  reported beside it.
- **Pass bar: kappa >= +0.55 AND the lower bound of the pair-bootstrap CI >
  +0.34.** Both must hold. +0.34 is the 11-06 uncalibrated judge on 99. The
  design interval is reported and is not part of the bar.

## Secondaries (reported whatever the primary says, promoted to nothing)

- Sides-only kappa (2x2 on the pairs both decided), with both intervals.
- The primary split by set (11-04 / 11-06).
- The Kent x judge 3x3 table, and the count of judge-tie-on-Kent-side.
- The **baseline**: the old judges' committed verdicts on the same 92 pairs,
  through the same function. This is computed only in phase B's analysis,
  after the freeze, and never before.
- The identical controls (all seven should be ties), L / R balance, and mean
  confidence.

## What a result licenses

- **Pass.** A PROPOSAL to Kent that the calibrated judge replace the
  uncalibrated one as the display-only pre-screen instrument
  (`vlm-prescreen`). No flag flip, no gate or routing use, no quality claim,
  and no pooling with Kent's labels.
- **Fail.** The failure is the result, and it is reported with the same
  figures. There is one held-out run, with no re-run, no re-tuned rubric and
  no subset chosen afterwards.

## Known limits, stated now

- **Shared designs.** The held-out pairs share designs, and often the base
  design itself, with the calibration pairs (stratifying by design does
  that). A pass generalises over pairs of these 18 designs, not to new
  artwork.
- **Kent saw other pictures for the 11-06 labels.** He labelled those pairs
  on the 09-18 to 10-08 renders (the flags sitting on a cloud render). The
  re-drawn pictures are the ones the judge sees. The `density-1007` tree broke
  ties from OS entropy, so its arm is a sample of that engine.
- **Kent's own ceiling is unmeasured.** His repeat agreement on the 11-02
  sitting was 1 of 4, so the bar may sit near or above it.
- **This session is contaminated.** The session that wrote this file read
  per-pair rows of both analyses (see the top of this file). It opens
  calibration pictures only and does not judge.
