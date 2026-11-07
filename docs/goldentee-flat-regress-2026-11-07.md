# Golden Tee and Fremont on the flat lane: why #1301 made them worse (2026-11-07)

Diagnosis only. `digitizer_core/` is untouched and no default moves. The pinned
test is `digitizer/tests/test_goldentee_flat_regress.py`.

## Question

`stage0_scale_relative_grad` (ON, Kent, #1301) now sends goldentee_hat and
hotel_fremont_hat down the FLAT lane instead of the gradient lane. #1321 traced
these wrong-way tripwire rows to that switch alone. The tripwire ledger (#1316)
now holds the post-flip values as the floor.

| job | figure | pre-flip (gradient lane) | floor (flat lane) | pro |
|---|---|---|---|---|
| goldentee_hat | stitches | 11,018 | 13,509 | 5,973 |
| goldentee_hat | trims | 25 | 39 | 10 |
| goldentee_hat | hops | 42 | 68 | 15 |
| goldentee_hat | needle-up mm | 536.3 | 644.5 | 288.9 |
| hotel_fremont_hat | word cc, native | 0.903 | 0.605 | 1.00 |

This doc asks what the flat lane does differently, region by region and stage by stage.

## Method

- **Arms.** Each job runs twice: shipped defaults ("on"), and
  `stage0_scale_relative_grad` False ("off"). Both go through
  `tools.pro_pair.digitize`, the Studio request and the service parser, at the
  pro's width. This is the call `tools.tripwire.measure` makes. Jobs ran one at
  a time on main 896f70b2, on Kent's Windows laptop.
- **Reproduction.** The "on" arm gives 13,515 stitches for Golden Tee, against
  13,509 in the Linux ledger. Fremont's word cc reads 0.605 here and in the
  ledger.
- **Figures.** Every figure is the PLAN's count (`plan.stats`, plus each
  `StitchRun` grouped by `shape_id`). Trims and jumps here are plan trims and
  plan floats (on 46 / 23, off 34 / 9). The tripwire counts different things
  from the DST: 39 / 68 on and 25 / 42 off. Both views rise the same way.
- **Stage counts.** These come from wrapping the pipeline's `quantize` /
  `photo_segment`, `resolve_small_regions` and `vectorize` calls.
- **Word cc.** `tools.pro_baseline.words`, the tripwire's own reader
  (tesserocr 5.5.3).

## Golden Tee: stage by stage

| stage | gradient lane (off) | flat lane (on) |
|---|---|---|
| 0: class | gradient: `gradient_smoothness` 0.082, over 0.0015 | flat: `tonal_frac` 0.020, under 0.11 |
| 2: region former | `photo_segment` (SLIC + RAG, design ramp), 11 clusters | `quantize` (global k-means), 7 clusters |
| 3: masks in, then kept | 66, then 65 | **2,038, then 167** |
| 4: regions | 38 | 92 |
| regions under 5 mm2 | 8 | 55 |
| threads | White, Black, Pumpkin, Orange Peel, Silver, Cardinal | White, Black, Pumpkin, **Candlelight**, **Fieldstone**, **Burnt Orange** |

Stage 3 receives 2,038 masks because k-means has no notion of place. Every
bevel, the GOLF sweep from yellow to orange, and every anti-aliased step
between them become separate pixel islands. Stage 3 then keeps 167 of them,
not the ~84 its plain absorb would keep. Two rescues hold the rest:

| stage-3 arm | masks kept |
|---|---|
| default | 167 |
| chain rescue off (`_chained_small_regions`) | 129 |
| contrast rescue off (`keep_thin_strokes`) | 144 |
| both off | 84 |
| gradient lane, for reference | 65 |

Both rescues were built for the flat lane, and both work as designed:

- **The chain rescue** keeps "a gradient ring banded into arc slivers"
  (2026-08-17).
- **The contrast rescue** keeps Fremont's thin tan strokes "forced flat"
  (2026-09-08).

On a shaded artwork they keep every shading step as its own shape. The kept
specks measure 0.04 to 0.4 mm across. 60 of them are one working pixel wide
(23.3 px/mm).

## Golden Tee: per-region cause table

By kind of region. The plan totals are 13,515 / 46 / 23 on and 11,018 / 34 / 9 off.

| region kind | off: n / stitches / trims / jumps | on: n / stitches / trims / jumps | change in stitches / trims / jumps | cause |
|---|---|---|---|---|
| **rescued specks** (`rescued_small_shape`) | 2 / 46 / 2 / 0 | 39 / 997 / 14 / 8 | **+951 / +12 / +8** | stage 3's chain and contrast rescues keep k-means shading steps. 29 of the 39 are under 0.3 mm wide. Each sews as its own satin or run piece with its own entry, so each costs a trim or a float. |
| narrow non-lettering shapes (under 0.7 mm, not rescued) | 10 / 1,173 / 11 / 1 | 20 / 1,716 / 11 / 5 | +543 / 0 / +4 | the same banding one size up. The bevel and edge strokes split into two or three tone bands (Black and Burnt Orange, Fieldstone and White). |
| everything else | 26 / 9,746 / 21 / 7 | 33 / 10,757 / 20 / 10 | +1,011 / -1 / +3 | see the next two rows |
| of which, GOLF letters | Pumpkin x3 (66.0, 59.4, 31.1 mm2) + Orange Peel F (51.7) | Pumpkin x4 (30.3, 27.1, 16.8, 14.9) + **Candlelight x4** (23.7, 14.7, 14.1, 8.7) | | the yellow-to-orange sweep is cut into a yellow top band and an orange bottom band in each letter. On the gradient lane the design ramp keeps one region per letter. |
| of which, the white swoosh band (S866aa0bb) | 128 mm2, 699 st (1 long satin + 1 tail) | 128 mm2, 1,111 st (2 long satins + 16 short columns at its two ends) | +412 | same polygon area to 0.01 mm2, sectioned into many more columns. The likely input is the lane's shared row angle, which the gradient lane sets and the flat lane does not. Not traced further. |

The same rise, by place in the design (centroid zones, plan figures):

| zone | off: n (under 5 mm2) / stitches / trims / jumps | on | change in stitches |
|---|---|---|---|
| GOLF word + its shadow | 19 (6) / 4,081 / 15 / 5 | 60 (41) / 5,954 / 21 / 17 | **+1,873** |
| GT letters | 13 (1) / 4,860 / 13 / 3 | 26 (13) / 5,015 / 19 / 3 | +155 |
| swoosh and the G's white face | 2 (0) / 1,308 / 3 / 0 | 2 (0) / 1,855 / 2 / 1 | +547 |
| tee | 4 (1) / 716 / 3 / 0 | 4 (1) / 646 / 3 / 2 | -70 |

**Upper bound of the speck row.** Forcing both rescues off on the flat lane
gives 56 regions, 11,841 stitches, 36 plan trims and 13 plan jumps. That
removes 1,674 of the +2,497 stitches, 10 of the +12 trims and 10 of the +14
jumps. The rest is the band split and the swoosh re-sectioning. These are
measured, not a proposal. Both rescues also guard real content on other flat
jobs, which is why they exist.

## Fremont hat: why the words read worse

Stage 0 is RIGHT about Fremont: `tonal_frac` 0.000. The art is three flat inks:
white, black and tan. On the gradient lane it had been getting a lettering
treatment the flat lane does not have.

| stage | gradient lane (off) | flat lane (on) |
|---|---|---|
| 2 | `photo_segment` with the dark (lightness) population: dark-ink labels {2, 3}, the tan small text and the rope | `quantize`: 3 clusters, **no dark-ink labels** |
| after stage 4 | tan letters tagged `dark_ink`; `bean_dark_ink` (`cfg.dark_ink_bean`) gives each one bean spines along its skeleton | tan letters are `rescued_small_shape`. The tagger makes them a text cluster (`text_cluster_all_rescued`) |
| lettering | sewn as a bean along the stroke (13-45 stitches a letter, `run`) | `small_text_cap_mm` 4.0 re-set: enlarged x1.57, widened 0.32 mm, sewn as satin columns 0.95-1.16 mm wide at satin angle 0 (35-72 stitches a letter) |

Per word (native size, cc against the shuffled baseline):

| word | off | on |
|---|---|---|
| EST | +1.00 | **+0.32** |
| 1895 | +0.20 | **0.00** |
| EAT | +1.00 | **0.00** |
| STAY | +1.00 | **0.00** |
| THE, HOTEL, FREMONT, PLAY | +1.00 | +1.00 |
| job | 0.903 | 0.605 |

The whole drop is the tan small text. The black wordmark reads the same on
both lanes. Region counts and stitches barely move (166 and 166 regions;
15,899 and 15,791 stitches). The change is in HOW those letters are sewn, not
in how many shapes there are.

## Tried, measured, not built

- **Absorb seam flecks on the flat lane.** A sub-floor mask nine tenths ringed
  by full-size regions of at least two other colours, with its L\* strictly
  between theirs, is absorbed before the rescues. No new constant.
  - Golden Tee: 13,216 stitches, 37 trims, 63 hops, 528.1 mm needle-up,
    stitch-type kappa 0.877 (chance 0.615). Direction kappa went
    **0.311 -> 0.000**.
  - Fremont: word cc 0.605, unchanged.
  - Verdict: it catches about 18 of the 83 kept masks and turns one kappa the
    wrong way. Not shipped.
- **A Lab-chord test** (the speck's colour on the line between two
  neighbours'). It holds for 0 of Golden Tee's 111 kept sub-floor masks within
  8 dE: k-means centres of a metallic sweep are not collinear.
- **A width floor at the thread's width.** It would separate the two jobs
  only by about 0.03 mm. Golden Tee's specks measure up to 0.39 mm; Fremont's
  real tan strokes start at 0.33 mm (pixel widths at 23-27 px/mm). That is a
  new physical constant fitted to two jobs (ROADMAP gate 1). Not tried in code.
- **True-size bean tagger on Fremont, flat lane.** `small_text_cap_mm` None
  plus `bean_letter_max_stroke_mm` 0.5 gives word cc 0.576. The ink-read bean
  tagger is not the dark-ink bean: EST and 1895 still read 0. The gradient
  lane's legibility comes from the lightness carve's polygons, not from beaning
  as such.

## Conclusion

Neither regression is one local defect.

1. **Golden Tee: the flat lane quantizes a shaded artwork globally.**
   Stage 0's new read sees only 2% tonal pixels; the white faces dominate the
   foreground. The flat lane's own small-region rescues then keep every
   shading step as a sewn shape. Specks own about two thirds of the stitch rise
   and nearly all of the trim and float rise. Band splitting and one
   re-sectioned satin own the rest.
2. **Fremont: the flat lane has no lightness-ink path for light small text.**
   Without it, EST 1895 and EAT STAY PLAY go the small-text re-set (enlarged
   satin) and stop reading. On the gradient lane the dark-ink carve plus
   `dark_ink_bean` sewed them as beans, which read.

A fix for either is a lane feature, not a guard: a sweep-aware region former
for shaded flat art, or the lightness carve on the flat lane. Each would need
its own flag, sitting and flip.

## Decisions for Kent

1. **Accept the floor (no build).**
   - Delivers: nothing moves. The ledger already guards these values.
   - Cost: none.
   - Catch: Golden Tee stays at 2.3x the pro's stitches and Fremont's tagline
     stays unreadable at native size.
2. **Flat-lane dark-ink carve, behind a new OFF flag.** Run stage 2's lightness
   population (`find_dark_thin_ink`) on the flat lane, so light strokes on a
   ground get `dark_ink` + `dark_ink_bean` as on the gradient lane.
   - Delivers: the likely route back to Fremont word cc 0.903.
   - Cost: one engine lane, plus measurement across all 18 tripwire pairs.
   - Catch: the carve was tuned on the gradient lane only. `pipeline.py` gates
     the thin and dark populations to `class_ == "gradient"`. Every flat job's
     small text could move.
3. **Shaded-art region former on the flat lane.** When k-means shatters (masks
   per region far above the norm), re-form stage 2 with the gradient lane's
   SLIC + RAG.
   - Delivers: Golden Tee back toward 11,018 / 25 trims.
   - Cost: the largest of the three. It is a second stage-0 decision in disguise.
   - Catch: it overlaps what `stage0_scale_relative_grad` just ruled, and ROADMAP
     gate 2 applies to any threshold on "shatters".

**My pick: 2.** Fremont's tagline is lettering a customer reads, the mechanism
is clear (the same carve and bean already ship on the gradient lane), and it
does not reopen the stage-0 ruling. Golden Tee's over-stitching is real, but
the pro simplifies this art far more than either of our lanes (5,973 stitches
against 11,018 even before the flip). Kent ruled no build on that gap on
2026-10-27.

## Reproduce

Per arm: `tools.pro_pair.digitize(art, width, garment, {"stage0_scale_relative_grad": False})`
(or `{}`), then group `plan.iter_runs()` by `run.shape_id` against
`result.regions`. Word cc: `tools.pro_baseline.words` on the arm's `design.json`.
For stage counts, wrap `pipeline.quantize`, `pipeline.photo_segment`,
`pipeline.resolve_small_regions` and `pipeline.vectorize`. Each digitize took
50-77 s on the laptop, one at a time. The pinned test replays stages 0-3 in
about 40 s.
