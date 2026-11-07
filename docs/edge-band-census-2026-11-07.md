# Edge-band census: do the cut blobs follow a width rule? 2026-11-07

**Question.** PR #1308 found the oracle-split gain is a same-colour edge band
the pro sews in the other stitch type, and that 13 regions carry the whole cut
term (`docs/c3-gain-attribution-2026-11-07.md`). For those 13 regions: how wide
is the band, is it a rim, what is the region's border tier? And does a simple
width-band predictor agree with the pro's satin/fill label on those bands?
**Measurement only.** `digitizer_core/` is untouched (empty diff). No flag, no
default.

**Every figure is chance-corrected kappa (ROADMAP gate 4), with its chance
floor in brackets beside it.** Intervals are cluster-bootstrap 95% intervals,
1,000 replicates, seed 1107.

## Done-test

1. **The table below covers all 13 regions** (36 blobs, 820 cells of 2 mm; the
   same 13 regions and 36 rims as #1308).
2. **The predictor does not clear chance.** Satin at or under 5.0 mm, fill over:
   kappa **0.099** (chance floor 0.51), region-cluster 95% interval
   **[0.00, 0.45]**.
3. **The 95% interval does not clear 0.** Its low end is 0.00. Kappa is clamped
   at 0, so a low end of exactly 0 means at least 2.5% of the replicates found
   no agreement above chance. The artwork-cluster interval (5 artworks) is
   [0.00, 0.65] and also does not clear 0.
4. **Not one threshold does.** No threshold from 2 to 8 mm clears 0 either (sweep
   below). The best point value is 0.10 at the pre-set 5 mm.

## Inputs

- Main `66964cc9` (after #1311), OFF arm, re-digitized from scratch for the 17
  jobs whose pro files are in `Embroidery Files.zip` (as #1308). Job kappas
  reproduce #1308's table to the digit (for example `becker_hat_small` 0.533,
  `hotel_fremont_patch` 0.545, `mfab_hat` 0.563). *(measured 2026-11-07,
  `python -m tools.satin_fill_census digitize` then `measure`)*
- Bridge and ProSeal were not re-run (same reason as #1308), and `tires_hat_3d`
  is degenerate. The 13 regions are the ones #1308's re-run found on the 17 jobs.
- The 36 blobs are #1308's: the pro's minority-type connected components of
  10 or more 2 mm cells inside one of our regions (`oracle_split`, floor 10).
  **The blobs are located by READING the pro's file**, so this tests only "given
  a band is there, does its width say its type". It does not test finding it.

## What is recorded

| field | how |
|---|---|
| band width, mm | twice the largest inscribed circle of the blob's cell mask, taken at quarter-cell resolution (the measure `border_by_size` reads a shape by). `strip_mm`, 2 x area / perimeter, is in `edge_bands.json` too. **A grid of 2 mm cells places a width to about 1 mm**: the widths come out on a ladder (1.5, 2.33, 3.5, 4.5, 5.5, 5.82 mm), and a one-cell strip reads about 1.5 to 2 mm. |
| rim | `blob_pattern`'s geometry from #1308: at least 80% of the blob within 2 cells of the region's outline (keyline), of one of our pieces (halo), or of both (band). |
| border tier | the region's smallest dimension (twice its largest inscribed circle, polygon in mm) against `machine.BORDER_BY_SIZE_WIDTH_MM`: 6+ mm gets a 2.1 mm ring, 4-6 mm a 1.5 mm ring, under 4 mm none. "ours" notes the tier our plan sewed the region in. |
| predictor | `band_predict`: **satin if width is at or under `BAND_SATIN_MAX_MM` = 5.0 mm, fill over.** 5.0 is the engine's own `SATIN_MAX_WIDTH_MM` (the pro's satin letters read 4.2-5.4 mm). It was fixed before any width was read. Nothing is fitted to these blobs. |

## The 13 regions

*(measured 2026-11-07, main `66964cc9`, `python -m tools.satin_fill_census edge-bands --runs OFF`; kappa (chance))*

| job | region | class | ours | region mm2 | min dim mm | border tier | band width mm (range) | blobs (rims) | pattern | pro's type in the bands | predictor agrees (cells) | kappa (chance) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hotel_fremont_patch | S78e6cd01 | ground | fill | 2170 | 12.4 | 6+ (2.1 ring) | 5.3 (3.5-5.8) | 4 (4) | 4 halo | 4 fill | 178/200 | 0.00 (0.89) |
| toat_machine_beanie | Sba572771 | ground | fill | 2514 | 13.0 | 6+ (2.1 ring) | 5.4 (4.5-5.5) | 2 (2) | 1 band, 1 halo | 2 satin | 10/115 | 0.00 (0.09) |
| toat_machine_hat | Sba572771 | piece | fill | 3082 | 14.3 | 6+ (2.1 ring) | 4.4 (2.3-5.5) | 5 (5) | 4 band, 1 halo | 5 satin | 46/103 | 0.00 (0.45) |
| toat_beanie | Sba572771 | piece | fill | 2426 | 12.6 | 6+ (2.1 ring) | 4.3 (1.5-5.5) | 4 (4) | 2 band, 2 halo | 4 satin | 28/82 | 0.00 (0.34) |
| mfab_hat | Sb250f949 | piece | fill | 1131 | 6.7 | 6+ (2.1 ring) | 3.6 (1.5-5.8) | 5 (5) | 5 band | 5 fill | 37/72 | 0.00 (0.51) |
| hotel_fremont_hat | S78e6cd01 | ground | fill | 2175 | 12.4 | 6+ (2.1 ring) | 3.1 (2.3-3.5) | 2 (2) | 2 halo | 2 satin | 58/58 | undefined (1.00) |
| becker_hat_large | S92f2350b | piece | satin | 1195 | 10.4 | 6+ (2.1 ring) | 3.6 (2.3-5.8) | 4 (4) | 3 keyline, 1 band | 4 fill | 19/54 | 0.00 (0.35) |
| mfab_lc | Sd6a15334 | piece | fill | 957 | 6.1 | 6+ (2.1 ring) | 3.2 (1.5-5.5) | 3 (3) | 3 band | 3 fill | 17/40 | 0.00 (0.42) |
| becker_lc_large | Sd86ce3cb | piece | satin | 1052 | 9.7 | 6+ (2.1 ring) | 4.0 (2.3-5.5) | 3 (3) | 2 keyline, 1 band | 3 fill | 14/35 | 0.00 (0.40) |
| becker_beanie | S10625c97 | piece | satin | 730 | 8.1 | 6+ (2.1 ring) | 2.3 (2.3-2.3) | 1 (1) | 1 keyline | 1 satin | 17/17 | undefined (1.00) |
| becker_beanie | S3a506002 | lettering | satin | 126 | 5.2 | 4+ (1.5 ring) | 3.5 (3.5-3.5) | 1 (1) | 1 keyline | 1 satin | 16/16 | undefined (1.00) |
| precision_drone | S00c2fb94 | lettering | fill | 800 | 6.7 | 6+ (2.1 ring) | 5.8 (5.8-5.8) | 1 (1) | 1 band | 1 fill | 14/14 | undefined (1.00) |
| toat_beanie | Sa0a15cc7 | piece | satin | 169 | 0.8 | under 4 (none) | 1.5 (1.5-1.5) | 1 (1) | 1 band | 1 fill | 0/14 | 0.00 (0.00) |

A per-region kappa has little to say: a region's bands are mostly one pro type,
so its chance floor is at or near 1 (undefined where the bands and the
predictor are all one class), and a clamped 0.00 here is "no agreement above
chance". The pooled figures are the ones to read.

## Findings

- **All 36 blobs are rims** (10 halo, 19 band, 7 keyline, as in #1308). The
  census is the same set.
- **Bands are narrow and every region but one is in the top border tier.** Widths
  run 1.5 to 5.8 mm (cell-weighted mean 4.4 mm). 12 of 13 regions are 6 mm or
  more across, so `border_by_size` rings them (2.1 mm). The thirteenth is a
  0.8 mm satin piece. **The border tier does not separate the carriers, because
  it is the same tier for 12 of them.**
- **Cells split about evenly by pro type: 391 satin, 429 fill, no run.** The
  type goes both ways, as in #1308.
- **The width ladder collapses the question.** Two artworks (the Toat jobs, the
  Fremont patch) have bands at 4.5-5.8 mm, right at the 5 mm ceiling. The pro
  sews the To a T bands as SATIN at 5.5 mm and the Fremont patch bands as FILL at
  a mean of 5.3 mm. A width cut cannot sort those two apart.

## Predictor against the pro's label

*(same run; cells of the 36 blobs, 2 mm; kappa (chance floor) [95%])*

| reading | kappa (chance) | 95% interval | clears 0? |
|---|---|---|---|
| **cells, 13 region clusters (primary)** | **0.099 (0.51)** | **[0.00, 0.45]** | **no** |
| cells, 5 artwork clusters | 0.099 (0.51) | [0.00, 0.65] | no |
| one unit per blob, 13 region clusters | 0.044 (0.48) | [0.00, 0.23] | no |

Raw agreement is 55.4% of cells; chance alone gives 51%.

**Threshold sweep** (region clusters; shown for sensitivity, **not** a pick, since
choosing the best of these on the same blobs would be fitting):

| satin up to | 2 mm | 3 mm | 4 mm | **5 mm** | 6 mm | 7 mm | 8 mm |
|---|---|---|---|---|---|---|---|
| kappa (chance) | 0.00 (0.52) | 0.00 (0.51) | 0.07 (0.51) | **0.10 (0.51)** | 0.00 (0.48) | 0.00 (0.48) | 0.00 (0.48) |
| 95% | [0.00, 0.04] | [0.00, 0.24] | [0.00, 0.45] | [0.00, 0.45] | [0.00, 0.00] | [0.00, 0.00] | [0.00, 0.00] |

- **Does the 95% interval clear 0? No.** At the pre-set 5 mm the low end is 0.00.
  At 6 mm and up the predictor says fill everywhere, which has no skill by
  construction.
- **The test is generous.** The bands are found by reading the pro, and the two
  classes are near even. It still does not clear 0. A rule that must also find
  the bands without the pro's file starts from this ceiling, not above it.
- **Caveats that lean toward a negative.** The widths are quantized to about 1 mm
  on a 2 mm grid, and the 4.5-5.8 mm ladder rungs sit on the 5 mm threshold.
  Thirteen regions in five artworks give wide intervals. A finer measurement
  (from the pro's stitch geometry, not cell masks) might move 0.10 up. It
  cannot pull the cluster count above 5 artworks.

## Decisions for Kent

**Whether to build an edge-band rule (a width or border-tier cut for the ring
the pro sews round a ground).**

1. **Close it: no edge-band rule from a width cut (my pick).** Cost: nothing.
   Catch: the +0.052 that #1308 measured on routing stays unbought. It is mostly
   the To a T field, which is one artwork. Evidence: a pre-set width rule scores
   kappa 0.10 against a 0.51 floor, interval [0.00, 0.45], and no threshold from
   2 to 8 mm clears 0.
2. **Re-measure the width from the pro's stitch geometry (column widths from
   `border_pro.columns`) before deciding.** Cost: one measurement session. Catch:
   this answers the 1 mm quantization only; 5 artworks still make the interval
   wide, and the To a T/Fremont conflict at 5.3-5.5 mm stays.
3. **Build a default-OFF edge-band stage anyway.** Cost: design and build plus two
   arms. Catch: the one measurement here finds nothing to build it from.

## Rebuild

From `digitizer/`, with `EMB_SCRATCH_KENT` set as in `tools/pro_baseline.py`:

```
python -m tools.satin_fill_census digitize --runs OFF --only <the 17 jobs>
python -m tools.satin_fill_census measure --runs OFF --only <the 17 jobs>
python -m tools.satin_fill_census edge-bands --runs OFF --only <the 17 jobs>   # ~2 min; writes OFF/edge_bands.json
```

The seed is fixed (`BOOT_SEED` 1107), so the intervals reproduce. Unit tests:
`digitizer/tests/test_satin_fill_census.py`.
