# Fine detail on low-resolution artwork: it was the tracer's grid, not the file

Kent, 2026-09-30: *"an issue with the Bridge Bar logo, the 'restaurant' is
completely missing — figure out why, what prevents it from doing fine detail,
and make a fix for it."*

Renders: `docs/renders/fine-detail-work-grid-2026-09-30/`. Instrument:
`digitizer/tools/lowres_detail.py`. Flag: `cfg.work_px_per_mm` — built OFF on
2026-09-30 and **ON at 8.0 since Kent's flip on 2026-10-01** (None is the
engine before it, byte for byte); every "traced at 8" number below is with
it set to 8.0. *Why it was built OFF* and *Kent's verdict* are the two
sections to read before touching it.

## What was already on the record, and what it got wrong

Two entries from earlier the same day (scope-history, DOCTRINE "Below the
floor is a diagnosis to earn"):

1. *The teal words are 1.6 mm lettering below the sewable floor.* Corrected
   the same day: they are 3.25–4.5 mm tall.
2. *They are a segmentation loss at 3.5 px/mm … a resolution fact no stitch
   rule moves; the levers are the source or the size.* Half right. The loss
   IS at segmentation. It is not a fact about the file.

The second entry's own evidence said so and was not followed: **the same
400 px file digitized at 140 mm brings the words back.** A bigger design
adds no information to a JPEG. What it changes is how many pixels of the
engine's working raster a letter is spread across — stage 1 enlarges a
sub-floor source to `min_px_per_mm` = 4 whatever the design size, so at
140 mm a letter is 28 grid pixels and at 80 mm it is 13–18. The artwork
was never the limit; the grid was.

## Where the words die — traced, stage by stage

`logo_bridge_bar.jpg` at 80 mm, `left_chest`, six colours. Teal ink read
strictly off the engine's own raster (blue-dominant pixels): **81 mm²**.
Followed through stage 2 of the gradient lane
(`bridge-stage2-trace-4-vs-8.jpg`):

| step | traced at 4 px/mm (shipped) | traced at 8 px/mm |
|---|---|---|
| teal ink in the raster | 80.9 mm² | 80.7 mm² |
| taken by the thin-ink population | 0.0 | 24.9 |
| in teal-majority SEEDS superpixels | **67.1** | 46.9 (+24.9 thin) |
| in teal-majority regions after the RAG merge | **39.2** | 45.8 (+24.9 thin) |
| after the small-region floor | 38.0 | 45.8 (+24.9 thin) |
| teal regions reaching stage 4 / sewn | 6 blobs, 46.6 mm² | 11 letter groups, 118.8 mm² |

The letters are readable in the 4 px/mm raster, separable by colour alone
(second panel of the trace), and the oversegmentation HOLDS them: 67 of 81
mm² sits in superpixels that are mostly teal. **The merge is what loses
them.** A 0.7–1.4 mm stroke is 3–5 pixels there against a superpixel about
7 px across, so every superpixel on the lettering band holds ink and ground
both. `merge_hierarchical` compares MEAN colours at 26 dE00, and the eight
merges that swallow teal read:

    teal side  purity 0.50–0.84, mean Lab ≈ (59, −26, 0)      73–194 px
    other side a 1,300–1,500 px mush of letter edges and gaps, mean Lab ≈ (71, −28, 27)
    weight     19–23 dE00 — under the 26 threshold
    boundary   17–19 Lab across the shared edge — a drawn edge by the lane's own 6.0 rule

Both merge protections that exist are size-gated — area ratio at 1,000 px
on the small side, boundary contrast at 1,000 px AND 9% of the design — so
neither ever sees a letter (80–250 px here). At 7 px/mm the same merge has
two cross merges instead of eight.

The grid, swept on the same file (teal in teal-majority regions after the
merge, of 81; then the finished design):

| grid px/mm | after merge mm² | teal regions | teal mm² | regions | stitches | trims |
|---|---|---|---|---|---|---|
| 4 (shipped) | 39.2 | 6 | 46.6 | 80 | 16,175 | 101 |
| 5 | 67.0 | 11 | 119.6 | 58 | 16,053 | 75 |
| 6 | 65.3 | 9 | 130.0 | 57 | 16,219 | 75 |
| 7 | 64.4 (+4.4 thin) | 13 | 123.3 | 56 | 15,648 | 70 |
| 8 | 45.8 (+24.9 thin) | 11 | 118.8 | 61 | 15,382 | 83 |
| 10 | — | 44 | 163.2 | 65 | 14,228 | 83 |

Every grid from 5 up keeps the words, and the design gets CHEAPER, not
dearer (the mush regions the 4 px/mm merge leaves behind were being sewn).
At 10 the thin-ink population takes the JPEG's halo as strokes and teal
specks appear on the ring (`bridge-grid-sweep-4-to-10.jpg`).

## Is it one logo? No — and that is the finding

Bridge is the corpus's only gradient-lane logo under 5 px/mm, so nothing
could say whether this was bridge's defect or the engine's. Every other
real logo here is 9–31 px/mm; a customer's file is whatever their website
serves. `tools/lowres_detail.py` makes the missing fixtures: each logo
downsampled to a chosen source density, digitized, and scored against the
SAME logo digitized from its full-resolution file — `fine` is the share of
the reference's ink under 1.5 mm wide that the arm sews in the same colour.

**Source 5 px/mm (a 400 px logo at 80 mm), traced at 4 / 6 / 7 / 8:**

| logo | fine @4 | @6 | @7 | **@8** | trims @4 → @8 (full-res file) |
|---|---|---|---|---|---|
| ENTHUSIAST | 0.25 | 0.59 | 0.57 | **0.90** | 8 → 15 (15) |
| screenshot (Golke) | 0.66 | 0.69 | 0.72 | **0.83** | 66 → 80 (73) |
| golden_tee | 0.66 | 0.75 | 0.80 | **0.78** | 56 → 60 (41) |
| Fremont | 0.86 | 0.85 | 0.88 | **0.90** | 31 → 38 (38) |
| drone | 0.78 | 0.73 | 0.75 | **0.78** | 92 → 140 (122) |
| **mean** | **0.64** | 0.72 | 0.74 | **0.84** | |
| mean `agree` (all sewn area) | 0.85 | 0.89 | 0.90 | **0.93** | |

Three logos get lettering back that today's engine does not sew at all from
a 5 px/mm file: ENTHUSIAST's tagline "ENTERPRISES INC" (`lowres-enthusiast.jpg`),
Fremont's "THE" (`lowres-fremont.jpg`), and Golke's "SNOW PLOWING DIVISION",
which today sews in the wrong grey (`lowres-screenshot.jpg`).

**Source 4.2 px/mm, traced at 4 → 7:** ENTHUSIAST 0.22 → 0.83, screenshot
0.57 → 0.79, Fremont 0.81 → 0.87, golden_tee 0.72 → 0.64; mean 0.58 → 0.78.

**Source 6.5 px/mm, traced as delivered → at 8:** drone 0.62 → 0.76,
screenshot 0.76 → 0.81, ENTHUSIAST 0.75 → 0.78, golden_tee 0.80 → 0.77,
Fremont 0.94 → 0.90; mean 0.77 → 0.80, two of five down. The gain is in the
files under about 6 px/mm; by 6.5 it is inside the noise of a segmenter
whose superpixel count jumps with the raster (803 / 1,207 / 500 / 659 / 833
on bridge at 4 / 5 / 6 / 7 / 8).

That is what sets the number. 8 is the best mean at 5 px/mm, monotone above
6 and 7; it is also 8.4's neighbour — the lowest density any fixture the
lanes' constants were tuned on was traced at (`logo_whitebg`, `logo_alpha`;
drone 9.6). Under it the engine was running outside the regime it was
measured in, on exactly the files with the least to spare.

## The price

- **Trims and stitches rise toward what the full-resolution file costs**
  (table above), because the detail that comes back is sewn. ENTHUSIAST 8 →
  15 trims against its reference's 15; drone 92 → 140 against 122.
- **One loser, synthetic:** `logo_whitebg` at 5 px/mm goes 12 → 21 trims
  and splits its red disc in two (`lowres-whitebg.jpg`). It is misread as a
  gradient at either grid — the full-resolution file is flat — so this is
  stage 0 on a blurred vector shape, bought more expensively.
- **Becker** (the other sub-floor fixture, flat lane, 1.45–1.81 px/mm so the
  4× cap bounds it at 5.8–7.25): 100 mm 9,321 → 9,662 stitches and 50 → 57
  trims; 80 mm 6,492 → 6,410 and 41 → 31. Same 17 regions; by eye a wash
  (`becker-100-and-80mm.jpg`).
- **Runtime:** not separable from machine load here. The merge works on
  superpixels, whose count is fixed, and planning works in millimetres, so
  nothing scales with the raster but the pixel passes; bridge end to end
  read 255 s traced at 4 and 215 s at 8 on the same loaded box, two thirds
  of either in `plan_stitches`. Not timed on a quiet machine.
- **`alpha_edge_extend`'s reach widens with it**, on purpose: its gate is
  "will the enlargement run" (`alpha_edge.upscale_expected`), and the
  enlargement now runs up to the working grid. The 2026-09-22 addendum to
  `docs/classifier-cliff-is-input-resolution-2026-09-16.md` says anyone
  moving the floor must price that half: it is in every `@8` number above
  (ENTHUSIAST, Fremont and drone are alpha cutouts), not a separate bill.

## Kent's verdict, and the flip (2026-10-01)

The pairs went on a page — bridge and Becker as uploaded, and ENTHUSIAST,
Fremont, golden_tee and drone each shrunk to a 400 px wide file, sewn by the
old grid and by this one beside the same logo digitized from its full-size
file (`https://claude.ai/artifact/531Ng39BhiUdgnBaEXEqaU`; `screenshot` left
off, his standing call). His ranking, the same on every logo:

1. **the full-size file**,
2. **the finer grid from the small file**,
3. **today's engine from the small file.**

Two rulings in that. The finer grid beats the old one to his eye, so
`work_px_per_mm` is **ON at 8.0**. And the source beats both — "full size
was better across the board" — so the grid is what the engine can do about a
small file, not a substitute for a larger one. `INPUT_LOW_RESOLUTION` still
fires only under 4 px/mm; every small file on that page was 5 and lost to
its full-size self without the customer being told. Whether the warning's
line should move is open, and his.

What the flip costs in the suite: 43 tests whose numbers were read on the
old grid hold it — a digitize of their own through
`tests/conftest.py::source_line_grid`, a shared run through
`work_px_per_mm=None` or `held_on_source_line`. Most are pins on a 3.5–7.5
px/mm fixture. The ones that are real costs on synthetics, not moved pins:

| fixture | old grid | at 8 |
|---|---|---|
| `gradient_ramp_radial` (6.4 px/mm) | 1 region | 2 |
| face-local threshold fixture | 2 regions | 4 |
| edge ladder, 400 px `logo_whitebg` ring | 0.14 mm off its edge | 0.40 |
| edge ladder, 400 px ribbon | 1 region | 6 |
| `region_blobs` (7.15 px/mm) | its photo-lane golden | moves |

## What CI found on the flip, and the ring (2026-10-02)

The flip's PR went red on three tests the local list of 46 did not hold.

**One stated the old grid's truth.** `test_preflight`'s bridge test asserted
the "lost in tracing" note on `LETTERING_TOO_SMALL`. On the working grid the
smallest flagged lettering has 20 grid pixels or more, so it was traced and
the finding carries no note — the behaviour the section below already
describes. The test now says so; the note is still held on the source line
by its own test.

**Two were a real regression, in the Studio's own request.** The Studio
asks for six colours. `app/e2e/fixtures/two-squares.png` — a black and a red
square on white, 2.0 px/mm at 80 mm — sewed THREE shapes at 8: the red
square's resampling ramp, a ring 0.125 mm wide and 14.9 mm² in a pink thread
of its own. At the engine's default of twelve colours the same file sews
two (measured; why twelve escapes it was not traced).

The cause is the space the phantom-blend test reads. A cluster that is all
edge pixels is dissolved only if its colour sits BETWEEN two others, within
`merge_delta_e` of the chord — in Lab. A resize mixes in RGB, and a
saturated colour running to a light ground is a curve in Lab: the ramp's
middle, (222, 91, 91), is 11.7 dE off the Lab chord from the red to the
ground's edge colour and 4.7 off the RGB one (14.2 and 0.1 against true
white). On the source line the quantizer names that third thread too — the
ring is half as many pixels wide there and stage 3 absorbs it as a sliver.

**The fix** (`stage2_quantize._quantize_population`, `enlarged_past_line`):
for a raster the working grid enlarged past the source line, the same
betweenness test is also read along the RGB segment, the residual still
judged in Lab against `merge_delta_e`. No new constant. A source on or over
the line, one held on it, and a hand-built `Prep` are byte-identical — the
flag is down. It is the flat lane's `quantize()` only: `thin_ink` and the
enclosed-population call in the gradient lane pass no flag, so everything
Kent ranked on the pairs page down that lane is unchanged.

The 5 px/mm regime at 8, `main` → with the fix (`tools/lowres_detail.py
--src 5 --grids 8`, Windows, same machine both arms):

| logo | lane | regions | stitches | trims | agree | fine |
|---|---|---|---|---|---|---|
| ENTHUSIAST | flat | 33 → 34 | 2,411 → 2,424 | 15 → 15 | 0.994 → 0.995 | 0.895 → 0.918 |
| Fremont, golden_tee, screenshot, drone, whitebg, tires | gradient | identical | identical | identical | identical | identical |

Not measured: a flat-lane logo with a real 1–2 pixel feature whose colour
happens to lie between two others. At 8 px/mm that is 0.125–0.25 mm, under
anything a stitch can hold, so the rule's reach stops below the sewable
floor — an argument, not a measurement.

## Why it was built OFF

Two things measured on 2026-10-01, after the tables above.

**The result is sensitive to half a pixel of foreground.** Enlarging the
background mask the way the picture is enlarged (bilinear, cut at one half)
instead of NEAREST cleans a synthetic's edge — the edge ladder's 400 px
ribbon traces as 6 regions on the grid and 1 with the smooth mask — and
moves the real logos the wrong way at a 5 px/mm source:

| logo | fine, traced at 4 | at 8 | at 8, smooth mask |
|---|---|---|---|
| ENTHUSIAST | 0.25 | 0.90 | 0.70 |
| golden_tee | 0.66 | 0.78 | 0.58 |
| Fremont | 0.86 | 0.90 | 0.90 |

and on bridge itself the words stay as shapes but snap to a grey-green cone
(58 regions, 84 trims, no teal thread). The mask variant is rejected — but
the lesson is that part of every "at 8" gain is where the superpixel grid
happens to land. (A reboot ended that run; drone, screenshot and whitebg
were not measured with the smooth mask.)

**ON at 8 it moves about 45 existing tests.** Full suite, knob ON: 49 failed,
2,968 passed (this box's baseline is itself not clean). Most are pins on
fixtures at 6–7.5 px/mm that are now enlarged; several are real regressions
on synthetics: `gradient_ramp_radial` sews 2 regions for 1, the face-local
threshold test 4 for 2, `region_blobs`' photo-lane golden moves, the edge
ladder's 400 px rung reads a ring 0.40 mm off its edge for 0.14.

So: the cause is established, the cure works on bridge and on the low-res
regime on average, and it is not clean enough to turn on unseen.

**And the baseline moved under it.** Merged onto `main` of 2026-10-01 (72
commits on), bridge with the knob OFF reads 7 teal regions / 76.5 mm² / 103
trims where every table above reads 6 / 46.6 / 101; at 8 it reads 11 /
125.4 / 98. The gap is still there (+49 mm², four more letter groups) and
smaller than measured. The regime, re-run on that tree at a 5 px/mm source
(fine ink, OFF → 8): ENTHUSIAST 0.25 → 0.90, golden_tee 0.63 → 0.72 (trims
71 → 55), Fremont 0.87 → 0.90 (34 → 30), drone 0.80 → 0.78 (98 → 154, its
full-resolution file 139); mean of four 0.64 → 0.82. Drone is the one that
pays without gaining fine ink — its area agreement rises 0.82 → 0.92.

## What is deliberately not moved

- **`min_px_per_mm` stays 4** and still owns `INPUT_LOW_RESOLUTION`. A
  6 px/mm file is enlarged for the tracer's sake and is not a file the
  customer needs to replace; the warning would otherwise fire on most
  uploads.
- **Photographs keep the source line** (`config.work_grid_px_per_mm`): the
  two photo classes, and anything declared photographic. The defect is a
  stroke averaged into its ground; a photograph has none, and its lane was
  never measured on an enlarged raster.
- **A pixel budget** (`stage1_prep.WORK_GRID_MAX_SIDE_PX` = 2,800, the
  service's own decode ceiling): 8 px/mm of a 400 mm design is 3,200 px a
  side, past the size that has run a job out of memory.

## Measured and rejected

| candidate | result |
|---|---|
| 4× the superpixels at 4 px/mm (`SEEDS_TARGET_FG_SUPERPIXELS` 4,800) | works on bridge (65.1 mm² after merge) — and moves every gradient and photo design at every resolution, against thresholds tuned at 1,200 |
| count `thin_ink`'s 3 px floor in SOURCE pixels on an enlarged raster | bridge at 8: 61 → 65 regions, 83 → 93 trims; `logo_whitebg` unchanged. Not the cause of the halo slivers |
| cubic / linear instead of Lanczos for the enlargement | bridge at 8: 83 → 108 / 90 trims; golden_tee agree 0.86 → 0.84 / 0.85; whitebg 21 → 17 / 18 trims. No arm wins twice |
| forcing bridge down the flat lane | keeps the teal (12 regions, 117 mm²) and sews an olive halo round every letter; 109 regions, 123 trims. Stage 0 is not this defect's |

## What this does NOT fix

The words reach the stitch tier now. They are still 3.25–4.5 mm letters
with 0.7 mm strokes, and each one sews as a single satin bar across the
whole letter (`bridge-restaurant-zoom-grid8.jpg`): "BAR & RESTAURANT" reads
as lettering at arm's length and not letter by letter. That is the
physical-size question `LETTERING_TOO_SMALL` already asks the customer, and
its size chip is still the lever — but it is now a question about thread,
where before the letters were gone before any stitch rule ran. Preflight's
"lost in tracing" sentence follows the grid: it no longer fires on lettering
the working grid gives 20 pixels.

*(measured 2026-09-30 — scratch probes over `stage2_photo_segment.segment`
for the trace and the merge log; `tools/lowres_detail.py` for the regime
table, `docs/renders/fine-detail-work-grid-2026-09-30/lowres-scores.json`;
`tests/test_work_grid.py`)*
