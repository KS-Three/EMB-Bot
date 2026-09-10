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

`.venv/Scripts/python -m tools.region_color_census --colors 6 --mm 80`, whole
corpus, 2026-09-10. The column that decides things is **agreed**: regions where
BOTH robust arms name one thread and the mean names a different one — the mean
is the odd answer out there, whichever estimator you prefer.

| fixture | regions | agreed | agreed area | worst mean-modal |
|---|---:|---:|---:|---:|
| `screenshot_phone_ui_golke` | 92 | 46 | **63.1%** | 14.5 |
| `logo_bridge_bar` | 50 | 10 | **56.3%** | 7.1 |
| `logo_golden_tee` | 35 | 14 | **25.2%** | 15.4 |
| `repro_gradient_white_icon` | 8 | 3 | 16.3% | 28.6 |
| `drone_render` | 58 | 22 | 9.5% | 23.2 |
| `logo_hotel_fremont` | 49 | 8 | 2.9% | 8.9 |
| `photo_dof_meadow` | 16 | 2 | 2.1% | 5.9 |
| `logo_gaulke_roofing` | 18 | 12 | 1.6% | 9.9 |
| `summit_badge` | 34 | 7 | 0.5% | 10.1 |
| `fur_ramp`, `grass_macro`, `gradient_ramp_linear`, `logo_script_tires`, `photo_owl_pale`, `photo_subject_stub`, `region_blobs` | — | **0** | 0.0% | ≤ 8.9 |

Two facts fall out of it. **The population is real customer logo art**: the
three logos and the phone screenshot carry a quarter to two thirds of their
own area in regions the mean gets wrong, and the flat-lane fixtures carry
none at all (they have no SLIC+RAG regions — the census says so per fixture).
**The true photo fixtures are mostly untouched**: no dominant colour, no
disagreement, which is the claim §2 makes about the ramp.

## 3b. The sheet — what it costs end to end

`tools/flip_sheet.py run --max-colors 6 --arm off --arm rc_median --arm
rc_modal` (26 fixtures, 80 mm, `left_chest`, the Studio's colour budget).
**Read this sheet and not the 12-colour one**: `--max-colors` was a no-op on
this box until it was fixed on this branch (DOCTRINE 2026-09-10, "a worker
pool is not a global's scope").

| arm | moved | stitches | trims | blocks | cones | stops |
|---|---:|---:|---:|---:|---:|---:|
| `rc_median` | 10 / 26 | +2,974 | +24 | **−2** | +1 | **−2** |
| `rc_modal` | 10 / 26 | +2,269 | 0 | +1 | +1 | +1 |

Per fixture, where it matters (OFF → median → modal):

| fixture | blocks | stitches | trims |
|---|---|---|---|
| `logo_bridge_bar` | 7 → **6** → **6** | 14,589 → 14,576 → **13,821** | 124 → 126 → **96** |
| `drone_render` | 8 → **6** → 7 | 16,101 → 16,250 → 16,169 | 91 → **83** → 89 |
| `logo_golden_tee` | 7 → 7 → **9** | 6,546 → 6,793 → 6,833 | 62 → 59 → **58** |
| `photo_scene_stub` | 4 → 5 → 5 | 16,083 → **19,464** → **19,464** | 44 → **73** → **73** |
| `photo_dof_meadow` | 5 → 5 → 5 | 19,892 → 19,412 → 19,412 | 34 → 41 → 41 |
| `repro_gradient_white_icon` | 5 → 5 → 5 | 22,361 → 22,078 → 22,078 | 24 → **19** → **19** |
| `logo_hotel_fremont`, `becker_marine`, every flat fixture | — | byte-identical | byte-identical |

**The cost is one synthetic photo fixture.** `photo_scene_stub` pays +3,381
stitches and +29 trims under either arm — a generated scene, not client
artwork, and the lane where §2 says the estimator has least to offer.
**The gain is on the logos**, and the two arms buy different things: `modal`
takes 28 trims and a block off Bridge Bar (the disc sewing `0501` Sun again
instead of `6031` Limelight), `median` takes two blocks off `drone_render`
and never adds a stop anywhere; `modal` adds two on Golden Tee, which is two
re-threads on a single-needle machine.

Grades move once, on the saturated floor (`logo_bridge_bar` score 0 → 4 under
`median`), which per gate 4 is not evidence either way.

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

## 5. The decision for Kent — measured, three live answers

Both robust arms put Bridge Bar's disc back on `0501` Sun and neither
changes a flat-lane fixture, Fremont or Becker at all. They differ on which
logo they help:

- **`"median"`.** Parameter-free and cheapest. Corpus net at 6 colours:
  **−2 blocks, −2 stops**, +2,974 stitches, +24 trims, and it adds a stop on
  nothing. Takes two blocks off `drone_render`. Its failure mode is a colour
  no pixel has (three independent channel medians), which is the defect's own
  shape in miniature — it did not bite anywhere in this corpus.
- **`"modal"`.** The estimator that matches the mechanism, and the best answer
  on the design the defect was found on: Bridge Bar **−768 stitches, −28
  trims, −1 block**. Corpus net: +2,269 stitches, trims flat, **+1 block /
  +1 stop** — that stop is Golden Tee going 7 → 9 blocks, two extra
  re-threads on a single-needle machine.
- **Leave `"mean"` and keep the arm parked.** Honest if the renders say the
  colours it moves are not better: the whole gain is on four gradient-lane
  designs, and one synthetic photo fixture pays +3,381 stitches either way.

**The renders** (artwork beside all three arms, captioned with cones, blocks,
stitches and trims — `tools/region_color_renders.py`, gitignored output):
Bridge Bar's disc reads olive under the mean and yellow under both robust
arms; Hotel Fremont is byte-identical across the three; Golden Tee's GT
letters carry their gold under the robust arms and read pale under the mean,
which is the pair to look at before ruling, because Golden Tee is also where
`modal` spends its two stops.

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
