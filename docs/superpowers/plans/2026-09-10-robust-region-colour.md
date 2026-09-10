# A region's colour must be robust to its inclusions — `cfg.region_color`

**Status: BUILT 2026-09-10, DEFAULT `"mean"` (the shipped engine, byte for
byte). Kent's pick after #444.** The engine change is one seam plus two
estimators behind an arm; the decision this plan exists to serve is which arm
becomes the default, and that is Kent's on the numbers in §4 and the renders
in §5.

## 0. What already governs this — read before changing the plan

- **The defect is DOCTRINE, dated 2026-09-10, and it was found by the colour
  flip's own test run, not by this plan.** *"Stage 2 hands the palette a
  region's MEAN, and a big region full of inclusions has a mean no pixel
  carries."* Bridge Bar's yellow disc is (251, 235, 65) by its pixels, 1.0
  ΔE00 from `0501` Sun; the region the palette sees is (223, 220, 77), 12
  ΔE00 darker and greener, because the black lettering, the bird and the rope
  inside the disc contribute their anti-aliased edges and grey halos to
  `p.rgb[...].mean()`. The k-medoids palette then rightly picks `6031`
  Limelight, 7.0 ΔE00 away, for the colour it was handed.
- **`bind_resnap_all_classes` is Kent's ruling, ON since 2026-09-10, and this
  plan does not touch it.** For as long as the re-snap was unbound it read
  the SOURCE pixels and quietly corrected the disc back to Sun (double-loading
  Lemon beside it). The bind holds the palette's answer, so it EXPOSED this
  error rather than causing it, and DOCTRINE's second rule from that day —
  *"when a flag closes an escape, ask what the escape was correcting"* — is
  what this work is. The fix is upstream, where the wrong colour is chosen.
- **Gate 1 does not apply.** Every number here is an image-space tolerance in
  ΔE00 between pixels of the customer's own artwork. Nothing about cloth
  settles which pixels of a logo are that logo's colour, and no source that
  could answer it owns a machine — the test the gate's own 2026-09-08
  correction sets out.
- **Gate 4 applies to every claim below.** `THREAD_MATCH_POOR` grades per
  thread on its worst patch and twelve of the corpus's combos sit on a
  saturated 0, so a cone that moves can move a grade for reasons that have
  nothing to do with the design looking better. Cones, stops and the render
  come first here; the grade is reported beside them, never alone.
- **The instruments already exist, and one had to be built.**
  `tools/flip_sheet.py` prices arms end to end across the 26 corpus fixtures
  in stitches, trims, blocks, cones and grade — two arms were added to it
  (`rc_median`, `rc_modal`). What it cannot say is how BIG the affected
  population is, because it only reads outputs: that is
  `tools/region_color_census.py` (new), which records every colour step 6
  asks for and prices the three estimators against each other on the same
  regions of the same run.

## 1. The mechanism, reproduced independently

`stage2_photo_segment.segment` step 6 selects the palette over one Lab per
kept region. Before this change that line was, verbatim:

```python
region_labs = [
    rgb_to_lab(p.rgb[r.frame_slice()][r.crop]
               .reshape(-1, 3).mean(axis=0, keepdims=True))[0]
    for r in kept
]
```

The census run of `logo_bridge_bar.jpg` at the Studio's 6 colours, 80 mm,
finds the disc as one region of 18,804 px — **46.7% of the design's total
region area** — and the arms disagree about it exactly as DOCTRINE says:

```
        px  area%  share mean-modal mean ->                modal ->
     18804  46.7%   0.64        5.4 6031 Limelight         0501 Sun
```

`share` is the fraction of the region's own pixels within 5 ΔE00 of its
dominant colour: **64% of the disc is one colour**, and the mean is not it.
That is the signature this defect leaves, and the census counts every region
carrying it (§3).

## 2. The estimators — `cfg.region_color`

An arm, not a bool, because the three answers disagree only where a region
HAS a dominant colour. On a photo's ramp there is none and the mean is
defensible; the tests pin that all three land within 5 ΔE00 of each other
there.

| arm | what it takes | property |
|---|---|---|
| `"mean"` | the region's mean RGB — **the default, byte-identical to the shipped engine** | moves with every inclusion, in proportion to its share |
| `"median"` | per-channel median of the region's RGB | parameter-free, cheap; a minority cannot move it. Three independent channel medians need not be a colour any pixel has |
| `"modal"` | the geometric median in Lab (Weiszfeld, seeded from the per-channel median), then the mean of the pixels within 5 ΔE00 of it | respects colour geometry; degrades to ≈ the mean where there is no mode |

`_REGION_MODAL_DE00 = 5.0` is `stage6_blend.SHADE_STEP_DELTAE / 2` — half a
shade step, so one shade of a ramp stays whole while an inclusion's halo (12
ΔE00 out on Bridge Bar) is refused. No new physical constant.

**One trap, paid for while writing the tests.** The textbook Weiszfeld dodge
for the singularity — drop the points sitting ON the estimate — is exactly
wrong here: a flat region's own colour IS a pile of identical pixels, and
dropping them hands the estimate to the halo. With 91% of a synthetic disc at
its field colour, the drop-them form put the estimate **9.75 ΔE00** off that
colour; the distance-floor form lands on it. `_geometric_median` carries the
measurement in its own comment.

## 3. The census — how big the population is

`.venv/Scripts/python -m tools.region_color_census --colors 6 --mm 80`

*(filled in from the run — see §3 table in the PR body / scope-history entry)*

## 4. What must be measured before any flip

1. **`flip_sheet` arms `rc_median` and `rc_modal` against `off`**, at the
   Studio's 6 colours AND the engine's 12: stitches, trims, blocks, cones,
   stops, grade per fixture. A cone count that moves is the reading; the
   grade is context.
2. **Bridge Bar specifically** — `test_bridge_bar_keeps_its_artwork` is the
   test that caught this, and the disc sewing `0501` Sun again is the
   single fact that says the fix works.
3. **Renders on the three review logos** (Fremont, Becker hat large, Bridge
   Bar LC), because this is a colour change and DOCTRINE's standing rule is
   that a claim about what something LOOKS like is settled by a picture.
4. **The full digitizer suite**, with the three known platform reds and
   nothing else, plus whether any golden moves. The default arm is the
   shipped expression, so nothing should move at all — a golden that moves
   on `"mean"` is a bug in this change, not a recapture.

## 5. The decision for Kent

Three live answers, and the sheet has to say which:

- **`"modal"` as the default.** The estimator that matches the mechanism:
  it finds the region's own colour and averages only that. Costs a
  Weiszfeld iteration per region (bounded at 32, converges in far fewer).
- **`"median"` as the default.** Cheaper and parameter-free, and on flat
  logo art it lands on the same answer; its failure mode is a colour no
  pixel has, which is the defect's own shape in miniature.
- **Leave the default `"mean"` and ship the arm parked.** The honest option
  if the sheet shows cones moving on photo fixtures for no visible gain —
  the population is real but the cure would then be trading one lane's
  correctness for another's.

## 6. Risks

- **It moves the palette, so it can move cones anywhere on the gradient
  lane**, including fixtures nobody was complaining about. That is what the
  sheet is for; a fixture that loses a cone it needed shows up as a
  `THREAD_MATCH_POOR` block, not as a grade wobble.
- **Photo regions have no mode and the ball then holds nearly every pixel**,
  so `"modal"` ≈ the mean there by construction — verified in the tests, and
  the sheet's photo rows are the check that it holds on real fixtures.
- **Cost.** Both robust arms convert a region's pixels to Lab (the mean arm
  converts one triple). On the corpus's largest regions that is hundreds of
  thousands of conversions per design; the sheet's wall-clock column is the
  reading, and if it is material the modal arm can sample the way
  `_shade_demand_points` already does (seeded, ≤2500 px) rather than being
  abandoned.
