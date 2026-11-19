# Tangle fault reader, 2026-11-19: pre-registration

**Status: PRE-REGISTERED.** Everything above "Result" was committed before
the reader was run on any real design. The result is appended below it and
nothing above it changes.

## Why this fault

The first two-reader prime-grader card (`docs/prime-grader/scorecard-2026-11-19.md`,
tree `f8373d58`) lists 36 faults both readers placed. By kind: mushed 9,
letter_shape 7, jagged 6, stray 5, gap 3, direction 2, blob 2, wavy 1,
colour 1. Edges (jagged) already have a measured reader (not shown,
`docs/edge-fault-reader-2026-11-10.md`), and closed letters two (letter
topology, negative space). What the readers keep describing inside "mushed",
"stray" and "blob" is not the letter's outline but the STITCHES: "a tangle of
fanned stitches", "crossover stitch bars pile up", "collapsed into dense
crossing stitches". Kent wrote the same fault in his own words on sitting 1
(`docs/defect-marks-2026-11-10/marks.json`): "Random Cross over stitch
shouldn't be here" (four pins on Becker), "Hard to tell what the stitches are
doing here", "No flow here in the stitching". No computed number reads stitch
direction disorder: preflight has none, and the five fault readers read
outlines, letter topology, spaces, in-fill and sibling treatment.

## The pins (fixed by rule, `fault_reader_harness.tangle_reason`)

1. A pin of an edge kind (jagged, wavy, lumpy_curve) is the edge reader's and
   never this one's.
2. Otherwise a pin whose note matches `TANGLE_RE` (tangle, pile, crossing /
   crossed, cross-over, cross stitch, fan / fanned, radial, jumble, mush,
   random stitch, stitch angle / direction, angles, flow, "what the stitches
   are doing", overlapping stitches).
3. Otherwise a bare pin (no note) of kind pen_flow or direction.

One rule for both sets. Each pin weighs one.

- **Set G (primary): the grader's agreed faults**, scorecard-2026-11-19 (faults
  both readers placed; one-reader faults left out): **10 pins on 6 designs**
  (Becker 1, Fremont 1, MFab 1, Golden Tee 3, Toat machine 3, Toat beanie 1).
  Stitches: a fresh `prime_grader capture` at `f8373d58`, the card's tree.
- **Set K (secondary): Kent's sitting-1 pins**: **13 pins on 4 designs**
  (Becker 7, MFab 4, Toat machine 1, Toat beanie 1). Stitches: a fresh capture
  at `950855bf`, the sitting's tree; a design whose re-captured stitch count
  differs from `docs/defect-marks-2026-11-10/kit.json` is refused and named.

## The reader (`digitizer/tools/tangle_fault_reader.py`, constants frozen)

Stitches only. Each penetration segment of at least 0.3 mm is drawn in sewing
order 0.4 mm wide at 12 px/mm carrying its axial angle (10 degree bins), later
over earlier, so a pixel holds the top thread's direction. Within 1.0 mm of
each pixel, the bins' shares, smoothed round the circle (Gaussian, sigma one
bin), give `D = exp(entropy) / exp(entropy of one direction)`: about 1 in a
fill or straight satin, about 2 on a seam of two columns. Judged where at
least half the disc is thread. **Flags: local maxima with D >= 2.5**, strongest
first, none within 2.0 mm of another; strength D. **Candidates: the same spread
over every judged pixel**, whatever its D.

## The verdict (fixed)

Scored by `python -m tools.fault_reader_harness score --fault tangle`, radius
**3.0 mm**, 2.0 and 5.0 reported beside it, never the verdict.

- **Null:** the stricter of `chance_area` (random points on thread) and
  `chance_pick` (random candidate anchors) at 3.0 mm, pooled over items.
- **Shown** on a set iff its pooled hit rate beats that null AND the 95%
  item-bootstrap interval on (hit - null) excludes 0. Kappa is
  `(hit - null) / (1 - null)`; no raw hit rate is reported without its null
  (ROADMAP gate 4).
- **Set G decides.** Set K is reported beside it, and the pooled G+K read
  (items do not repeat across sets: K's renders are an older tree, so they
  are scored as separate items, `K:` prefix) is a secondary.
- Strength AUC (pin's local D against random thread points) and
  leave-one-design-out are reported, not verdicts.
- **No constant is re-tuned on these pins.** A miss is reported as a miss. A
  shown result licenses a reporting tool only: not a preflight metric, not a
  gate, no flag, and replication on a fresh card before anything else.

## Result

Run once, 2026-11-19, after the pre-registration commit `a633ca70`. Both
captures ran on Kent's desktop (`prime_grader capture` at `f8373d58`; the same
capture driven against a `950855bf` checkout for set K). The `f8373d58`
capture reproduces the card: all 9 preflight grades and scores equal the
card's. On `950855bf`, MFab re-captured 20,801 stitches against the kit's
20,557 and was **refused** by the rule, so set K is 9 pins on 3 designs (the
other 8 designs matched). Numbers: `tangle-fault-reader-2026-11-19/score.json`;
the script that made them: `score_run.py` beside it.

**Set G (decides): NOT SHOWN.** Hit 6 of 10 at 3.0 mm against the stricter
null, `chance_area` 0.363 (`chance_pick` 0.361): kappa **+0.37**, item-bootstrap
95% CI on (hit - null) **[-0.02, +0.46]**, 10 pins on 6 designs. The interval
touches 0, so the pre-registered rule says not shown. Leaving one design out:
the lower bound stays above 0 only without Becker or without Fremont (the two
misses); dropping any of MFab, Golden Tee, Toat machine or Toat beanie takes
it below 0. At 2.0 mm kappa +0.24 [-0.11, +0.45]; at 5.0 mm +0.75 [+0.03, +0.43]
(sensitivity, not the verdict). Mean strength AUC 0.63.

**Set K (secondary): above chance, three designs.** Hit 5 of 9 against 0.237
(`chance_area`; `chance_pick` 0.236): kappa **+0.42**, CI **[+0.21, +0.73]**,
mean strength AUC 0.84. Becker carries 7 of the 9 pins (3 hit; two of his
"Random cross over stitch" pins are 8.4 and 12.0 mm from any flag); Toat
machine 1 of 1, Toat beanie 1 of 1. A three-design bootstrap is not a
replication.

**Pooled G + K (secondary):** 11 of 19 against 0.303, kappa +0.40, CI
[+0.14, +0.47], 9 items (the two sets' renders are different trees, scored as
separate items).

**Reading it.** The direction spread of the top thread lands nearer the
tangles both readers place than random thread does, on every set and radius,
but on the set the pre-registration chose to decide, 10 pins on 6 designs do
not exclude chance, and the margin rests on four designs. The reader flags
37-97 places per design (Tires 3): it also fires on legitimate junctions where
three columns meet, which is where most tangles are, so it does not separate
a pile-up from a clean three-way join. The misses: Becker's R counter
(a letter-shape fault whose note mentions a fan, nearest flag 28.9 mm) and the
Fremont rope end (3.35 mm). **No constant is changed on these pins.** The
reader ships as a reporting tool only. Its next test is the next two-reader
card (Monday), frozen as is.
