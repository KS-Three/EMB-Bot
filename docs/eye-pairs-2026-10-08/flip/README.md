# Eye pairs, 2026-10-08: the Column lane's flip sitting (`columns-flip-1008`)

Kent picked this page on 2026-10-08, after PR #814 put the lane's design
trims under shipped on the last logo where they were over (drone). It shows
what a flip of the Column lane would turn on: `lettering_columns` and
`lettering_words` together. BEFORE is shipped, AFTER is both flags.

- **Both flags stay OFF.** Nothing here is a verdict; the sitting is Kent's.
- **Nothing here is sewn.**
- The arm is `columns_words` in `tools/eye_pairs/pairs.py`.

The engine is `main` at d17c5f7e plus PR #814 (f08f49e4). Six logos at the
Studio's defaults: `REAL_ART` less `screenshot` and `gaulke`, which Kent
excluded from comparisons. Tires has no lettering and is identical. Drawn on
Kent's Windows laptop in a worktree with no `rembg_isolated/venv`; tires is
the one logo that would read it, on both sides.

## The price (`price-tables.json`)

Counted by `tools/eye_pairs_price.py` from the designs that drew the pairs.

| fixture | stitches | trims | changed shapes | their trims | uncovered ink | lost_frac |
|---|---|---|---|---|---|---|
| becker | 10,969 → 8,708 | 59 → 27 | 6 | 38 → 6 | 6.00 → 6.29% | 0.0236 → 0.0381 |
| bridge | 18,837 → 18,870 | 101 → 98 | 8 | 8 → 5 | 0.17% | 0.2213 → 0.2283 |
| drone | 19,644 → 19,191 | 132 → 134 | 28 | 24 → 26 | 0.33 → 0.45% | 0.1003 → 0.1060 |
| enthusiast | 2,602 → 2,365 | 14 → 7 | 15 | 11 → 4 | 1.80 → 0.59% | 0.2771 → 0.3110 |
| fremont | 20,819 → 20,727 | 63 → 59 | 91 | 20 → 16 | 0.00% | 0.0302 → 0.0325 |
| golden_tee | 8,950 → 8,398 | 44 → 43 | 14 | 19 → 18 | 0.18 → 0.20% | 0.4501 → 0.4698 |
| tires | 2,864 | 6 | 0 | 0 | 0.01% | 0.1074 |

Colour changes and cones do not move anywhere.

## What the table says, without grading it

- **Trims fall on five of six logos; drone rises by two.** With
  `lettering_columns` alone drone is under shipped (132 against 133, PR
  #814). The word tagger sends THERMAL's M, A and L into the lane, which
  both old taggers missed, and those cost the difference.
- **lost_frac rises on all six.** It sums two opposite defects (ink lost and
  overshoot), so its size is not a quality figure; the direction is the same
  on every logo and the picture is the judge.
- **enthusiast reads 0.3110**, over the bar
  `tests/test_lettering_coverage_regression.py` holds near 0.29. A flip has
  to re-read that test against this picture.
- **Stitches fall on five of six** (bridge +33): no zigzag underlay under a
  column, and no junction sewn twice.

## How it was built

```
cd digitizer
python -m tools.eye_pairs --render --out <lane1> --fixtures becker,tires,golden_tee --arms columns_words
python -m tools.eye_pairs --render --out <lane2> --fixtures enthusiast,fremont     --arms columns_words
python -m tools.eye_pairs --render --out <lane3> --fixtures bridge,drone           --arms columns_words
python -m tools.eye_pairs.merge <merged> <lane1> <lane2> <lane3>
python -m tools.eye_pairs_price <merged> columns_words --out ../docs/eye-pairs-2026-10-08/flip/price-tables.json
python -m tools.eye_pairs_gallery --labelled --src <merged> --out <gallery> \
    --tables ../docs/eye-pairs-2026-10-08/flip/price-tables.json --sitting columns-flip-1008
```

**Result:** 14 arm-runs, none failed; 6 pairs, 1 identical. Published to the
Flag Before After page as version 14. *(measured 2026-10-08, Windows,
python 3.12)*
